from __future__ import annotations

import html
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional, Tuple

import astropy.units as u
import numpy as np
from astropy.coordinates import AltAz, SkyCoord, get_body, get_sun
from astropy.time import Time

from .astronomy import J2000_FRAME, source_coord
from .catalog import Source
from .config import DISPLAY_COORDINATE_FRAMES, LACT_TELESCOPE, TelescopeConfig
from .schemas import ConstraintSet
from .status import sky_snapshot, sky_trajectory_snapshot

STATUS_CLASS = {"GREEN": "green", "YELLOW": "yellow", "RED": "red"}
MAP_LABELS = {
    "en": {"horizon": "Horizon", "north": "N", "east": "E", "south": "S", "west": "W", "sun": "Sun", "moon": "Moon", "radius": "radius", "extension_outside": "extension exceeds local-map range"},
    "zh": {"horizon": "地平线", "north": "北", "east": "东", "south": "南", "west": "西", "sun": "太阳", "moon": "月亮", "radius": "半径", "extension_outside": "extension 超出局部图显示范围"},
}


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _labels(language: str) -> dict:
    return MAP_LABELS["zh" if language == "zh" else "en"]


def _normalise_display_frame(value: str) -> str:
    return value if value in DISPLAY_COORDINATE_FRAMES else "altaz"


def _display_label(value: str) -> str:
    return DISPLAY_COORDINATE_FRAMES[_normalise_display_frame(value)]


def _altaz(at_time: datetime, telescope: TelescopeConfig) -> AltAz:
    return AltAz(obstime=Time(_utc(at_time)), location=telescope.location, pressure=0 * u.hPa)


def _zenith_coordinate(at_time: datetime, telescope: TelescopeConfig) -> SkyCoord:
    return SkyCoord(az=0 * u.deg, alt=90 * u.deg, frame=_altaz(at_time, telescope))


def _frame(key: str, at_time: datetime, telescope: TelescopeConfig):
    return _altaz(at_time, telescope) if key == "altaz" else J2000_FRAME if key == "j2000" else "galactic"


@dataclass
class _Projection:
    """Azimuthal equidistant projection; every overlay shares this transform.

    Longitude increases to the right, latitude up at the centre. At the AltAz
    zenith the limiting convention is azimuth 0 up and azimuth 90 right.
    Coordinates outside the domain are NOT clamped onto its boundary.
    """

    center: SkyCoord
    cx: float
    cy: float
    radius: float
    angular_radius: float
    zenith_altaz: bool = False

    @property
    def scale(self) -> float:
        return self.radius / self.angular_radius

    def project(self, coordinates: SkyCoord):
        coordinates = coordinates.transform_to(self.center.frame)
        if self.zenith_altaz:
            separation = 90.0 - np.asarray(coordinates.alt.deg)
            angle = np.asarray(coordinates.az.rad)
        else:
            separation = np.asarray(self.center.separation(coordinates).deg)
            angle = np.asarray(self.center.position_angle(coordinates).rad)
        radial = separation * self.scale
        return self.cx + radial * np.sin(angle), self.cy - radial * np.cos(angle), separation

    def path(self, coordinates: SkyCoord) -> str:
        x, y, separation = self.project(coordinates)
        return _path_segments(x, y, separation < 179.0, self.radius)


def _path_segments(x, y, valid, radius: float) -> str:
    """Break invalid/antipodal jumps; SVG clipping handles the domain edge.

    Paths are deliberately open: clipping must not draw artificial chords
    between disconnected arcs at a horizon or a coordinate wrap.
    """
    parts = []
    previous = None
    for px, py, ok in zip(np.atleast_1d(x), np.atleast_1d(y), np.atleast_1d(valid)):
        if not ok or not math.isfinite(float(px)) or not math.isfinite(float(py)):
            previous = None
            continue
        move = previous is None or math.hypot(px - previous[0], py - previous[1]) > radius * 0.4
        parts.append(f'{"M" if move else "L"}{px:.9f},{py:.9f}')
        previous = (px, py)
    return " ".join(parts)


def _polar(altitude: float, azimuth: float, cx: float, cy: float, radius: float) -> Tuple[float, float, bool]:
    radial = radius * (90.0 - altitude) / 90.0
    angle = math.radians(azimuth)
    return cx + radial * math.sin(angle), cy - radial * math.cos(angle), altitude >= 0.0


def _project_coordinate(coordinate: SkyCoord, center: SkyCoord, cx: float, cy: float, radius: float, visible: bool):
    x, y, separation = _Projection(center, cx, cy, radius, 90).project(coordinate)
    return float(x), float(y), visible and float(separation) <= 90.0, float(center.position_angle(coordinate).deg)


def _project_source(source: Source, geometry: dict, at_time: datetime, telescope: TelescopeConfig, frame_key: str, cx: float, cy: float, radius: float):
    if frame_key == "altaz":
        x, y, visible = _polar(float(geometry["target_altitude_deg"]), float(geometry["target_azimuth_deg"]), cx, cy, radius)
        return x, y, visible, float(geometry["target_azimuth_deg"])
    center = _zenith_coordinate(at_time, telescope).transform_to(_frame(frame_key, at_time, telescope))
    return _project_coordinate(source_coord(source), center, cx, cy, radius, float(geometry["target_altitude_deg"]) >= 0.0)


def _project_body(altitude: float, azimuth: float, at_time: datetime, telescope: TelescopeConfig, frame_key: str, cx: float, cy: float, radius: float):
    if frame_key == "altaz":
        x, y, visible = _polar(altitude, azimuth, cx, cy, radius)
        return x, y, visible, azimuth
    coordinate = SkyCoord(az=azimuth * u.deg, alt=altitude * u.deg, frame=_altaz(at_time, telescope))
    center = _zenith_coordinate(at_time, telescope).transform_to(_frame(frame_key, at_time, telescope))
    return _project_coordinate(coordinate, center, cx, cy, radius, altitude >= 0.0)


def _star_points(x: float, y: float, outer: float = 7.0, inner: float = 3.0) -> str:
    return " ".join(
        f"{x + (outer if index % 2 == 0 else inner) * math.cos(math.radians(-90 + index * 36)):.9f},{y + (outer if index % 2 == 0 else inner) * math.sin(math.radians(-90 + index * 36)):.9f}"
        for index in range(10)
    )


def _viewbox(width, height, cx, cy, zoom, bounds):
    zoom = float(zoom)
    if not math.isfinite(zoom) or not 1.0 <= zoom <= 1000.0:
        raise ValueError("zoom must be finite and between 1 and 1000")
    if bounds is not None:
        if len(bounds) != 4 or not all(math.isfinite(float(v)) for v in bounds) or bounds[2] <= 0 or bounds[3] <= 0:
            raise ValueError("bounds must be a finite SVG viewBox (x, y, width, height)")
        view = tuple(float(v) for v in bounds)
        zoom = max(width / view[2], height / view[3], 1.0)
    else:
        view = (0.0, 0.0, width, height) if zoom == 1 else (cx - width / zoom / 2, cy - height / zoom / 2, width / zoom, height / zoom)
    return " ".join(f"{v:.9f}" for v in view), zoom, view


def _nice_step(span: float) -> float:
    target = max(span / 6, 1e-6)
    power = 10 ** math.floor(math.log10(target))
    return next((value * power for value in (1, 2, 5, 10) if value * power >= target), 10 * power)


def _lonlat(lon, lat, frame):
    return SkyCoord(lon * u.deg, lat * u.deg, frame=frame)


def _grid(projection: _Projection, key: str, zoom: float, bounds, grid_step_deg: Optional[float]) -> tuple[str, float]:
    """True meridians/parallels, sampled near the view as well as globally.

    View-centre inversion selects fine-grid ranges even after off-centre pan;
    spherical longitude offsets avoid a discontinuity at 0/360 degrees.
    """
    p = projection
    vx, vy, vw, vh = bounds
    dx, dy = vx + vw / 2 - p.cx, p.cy - (vy + vh / 2)
    distance = math.hypot(dx, dy) / p.scale
    if p.zenith_altaz:
        view_center = _lonlat(math.degrees(math.atan2(dx, dy)) % 360, 90 - min(distance, 179), p.center.frame)
    else:
        view_center = p.center.directional_offset_by(math.atan2(dx, dy) * u.rad, min(distance, 179) * u.deg)
    lon0, lat0 = float(view_center.spherical.lon.deg), float(view_center.spherical.lat.deg)
    extent = min(180.0, math.hypot(vw, vh) / (2 * p.scale))
    step = float(grid_step_deg) if grid_step_deg is not None else _nice_step(min(60.0, extent * 1.2))
    if not math.isfinite(step) or step <= 0 or step > 90:
        raise ValueError("grid_step_deg must be finite and in (0, 90]")
    lo, hi = max(-90.0, lat0 - extent), min(90.0, lat0 + extent)
    longitude_extent = 180.0 if abs(lat0) + extent >= 89.999 else min(180.0, extent / max(math.cos(math.radians(abs(lat0) + extent)), 1e-6))
    # A polar cap contains all meridians: retain bounded density without losing
    # fine latitude ticks. A tiny caller-provided step cannot allocate millions.
    lon_step = max(step, 360 / 72 if longitude_extent >= 179 else longitude_extent * 2 / 72)
    lat_step = max(step, (hi - lo) / 72)
    lons = np.arange(math.ceil((lon0 - longitude_extent) / lon_step) * lon_step, lon0 + longitude_extent + lon_step * .01, lon_step)
    lats = np.arange(math.ceil(lo / lat_step) * lat_step, hi + lat_step * .01, lat_step)
    pieces = []
    occupied = []
    axes = ("Az", "Alt") if key == "altaz" else ("RA", "Dec") if key == "j2000" else ("l", "b")
    for axis, values in enumerate((lons, lats)):
        for value in values:
            if axis == 1 and abs(value) >= 89.999999:
                continue
            # Include a local high-resolution interval for deep zoom and a
            # coarse global curve for client-side viewBox navigation.
            samples = np.unique(np.concatenate((np.linspace(-90, 90, 361), np.linspace(lo, hi, 161)))) if axis == 0 else np.unique(np.concatenate((np.linspace(lon0 - 180, lon0 + 180, 721), np.linspace(lon0 - longitude_extent, lon0 + longitude_extent, 161))))
            coordinates = _lonlat(np.full_like(samples, value % 360), samples, p.center.frame) if axis == 0 else _lonlat(samples, np.full_like(samples, value), p.center.frame)
            x, y, separation = p.project(coordinates)
            d = _path_segments(x, y, separation < 179, p.radius)
            pieces.append(f'<path class="sky-grid coordinate-grid" data-axis="{axes[axis]}" data-coordinate-deg="{value % 360 if axis == 0 else value:.9f}" d="{d}" />')
            valid = (separation < p.angular_radius * .95) & (x > vx + vw * .045) & (x < vx + vw * .94) & (y > vy + vh * .05) & (y < vy + vh * .95)
            indexes = np.flatnonzero(valid)
            if len(indexes):
                # Prefer the viewport middle, but avoid piling labels on top
                # of one another near poles and meridian intersections.
                ranks = indexes[np.argsort(np.abs((y[indexes] - vy) / vh - .7) if axis == 0 else np.abs((x[indexes] - vx) / vw - .72))]
                for index in ranks:
                    px, py = float(x[index]), float(y[index])
                    if all(abs(px - ox) > 54 / zoom or abs(py - oy) > 17 / zoom for ox, oy in occupied):
                        occupied.append((px, py))
                        number = value % 360 if axis == 0 else value
                        precision = max(0, min(6, int(-math.floor(math.log10(step))) + 1))
                        label = f"{axes[axis]} {number:.{precision}f}°"
                        pieces.append(f'<text class="ring-label coordinate-tick" data-axis="{axes[axis]}" data-coordinate-deg="{number:.9f}" x="{px + 3 / zoom:.9f}" y="{py - 3 / zoom:.9f}">{label}</text>')
                        break
    return "".join(pieces), step


def _styles(zoom: float) -> str:
    # Inline styles are intentionally scoped to the SVG classes; physical
    # extensions never inherit the old CSS symbol-scale/hover transforms.
    css = f'''<style>
.sky-map-svg text,.fov-map-svg text{{font-size:calc({14.4 / zoom:.9f}px * var(--map-icon-scale,1));font-weight:650}}
.sky-map-svg .coordinate-grid,.fov-map-svg .coordinate-grid{{fill:none;stroke:var(--line-soft,#667085);stroke-width:1.4;vector-effect:non-scaling-stroke;stroke-dasharray:3 6}}
.sky-map-svg .source-marker,.fov-map-svg .source-marker{{color:var(--blue,#608fea);cursor:pointer}}
.sky-map-svg .status-green{{color:var(--green,#47a976)}} .sky-map-svg .status-yellow{{color:var(--yellow,#c9a200)}} .sky-map-svg .status-red{{color:var(--red,#d45962)}}
.sky-map-svg .trajectory-highlight{{color:#8b5cf6}}
.sky-map-svg .source-marker .source-symbol,.fov-map-svg .source-marker .source-symbol{{fill:none;stroke:currentColor;stroke-width:2;vector-effect:non-scaling-stroke;transform:scale(var(--map-icon-scale,1));transform-box:fill-box;transform-origin:center}}
.sky-map-svg .source-type-gaia polygon,.fov-map-svg .source-type-gaia polygon{{fill:currentColor;stroke:currentColor;stroke-width:1.5;vector-effect:non-scaling-stroke;transform:scale(var(--map-icon-scale,1));transform-box:fill-box;transform-origin:center}}
.sky-map-svg .extension-ring,.fov-map-svg .extension-ring{{fill:none;stroke:currentColor;stroke-width:2;vector-effect:non-scaling-stroke;transform:none;pointer-events:none}}
.sky-map-svg .source-hit-target,.fov-map-svg .source-hit-target{{fill:transparent;stroke:none;transform:scale(var(--map-icon-scale,1));transform-box:fill-box;transform-origin:center;pointer-events:all}}
.sky-map-svg .realtime-fov-ring,.fov-map-svg .fov-ring{{fill:none;stroke:var(--blue,#608fea);stroke-width:3;vector-effect:non-scaling-stroke;pointer-events:none}}
.sky-map-svg .coordinate-tick,.fov-map-svg .coordinate-tick{{fill:var(--muted,#8993a7);pointer-events:none;paint-order:stroke;stroke:var(--sky,#101827);stroke-width:{2 / zoom:.9f}px}}
.sky-map-svg .body-marker text,.fov-map-svg .body-marker text{{fill:#ee9b37}}
.sky-map-svg .body-marker text[dominant-baseline],.fov-map-svg .body-marker text[dominant-baseline]{{font-size:{27 / zoom:.9f}px}}
</style>'''
    # Multiple maps with different server zooms can coexist in one document.
    return css.replace('.sky-map-svg', f'.sky-map-svg[data-zoom="{zoom:.9f}"]').replace('.fov-map-svg', f'.fov-map-svg[data-zoom="{zoom:.9f}"]')


def _body_icon(x: float, y: float, kind: str, label: str, zoom: float = 1) -> str:
    glyph = "☀︎" if kind == "sun" else "☾"
    return (f'<g class="body-marker body-{kind}" role="img" aria-label="{_esc(label)}" tabindex="0"><title>{_esc(label)}</title>'
            f'<text class="{kind}-glyph" x="{x:.9f}" y="{y:.9f}" text-anchor="middle" dominant-baseline="central">{glyph}</text>'
            f'<text x="{x + 13 / zoom:.9f}" y="{y + 4 / zoom:.9f}">{_esc(label)}</text></g>')


def _boundary(coordinate: SkyCoord, radius_deg: float) -> SkyCoord:
    return coordinate.directional_offset_by(np.linspace(0, 360, 361) * u.deg, radius_deg * u.deg)


def _marker(source: Source, coordinate: Optional[SkyCoord], p: _Projection, zoom: float, extra: str = "", title: Optional[str] = None, below: bool = False, position=None) -> str:
    x, y, _ = p.project(coordinate) if position is None else position
    x, y = float(x), float(y)
    title = title or source.display_name
    key = source.source_key
    kind = "gaia" if source.source_type == "gaia" else "catalogue"
    candidate = " calibration-candidate" if kind == "gaia" else ""
    attrs = f'data-source-index="{source.index}" data-source-key="{_esc(key)}"'
    pieces = [f'<g class="source-marker source-type-{kind}{candidate}{extra}" {attrs} data-x="{x:.9f}" data-y="{y:.9f}" data-below-horizon="{str(below).lower()}" role="button" tabindex="0" aria-label="{_esc(title)}"><title>{_esc(title)}</title>']
    if source.ext > 0 and getattr(source, "footprint_known", True) and not below and kind != "gaia":
        # ext is an angular radius, not a marker or a hit-test radius.
        pieces.append(f'<path class="extension-ring" data-angular-radius-deg="{source.ext:.9f}" d="{p.path(_boundary(source_coord(source), source.ext))}" />')
    if kind == "gaia":
        pieces.append(f'<polygon points="{_star_points(x, y, 8 / zoom, 3.2 / zoom)}" />')
    else:
        pieces.append(f'<circle cx="{x:.9f}" cy="{y:.9f}" r="{3.5 / zoom:.9f}" class="source-symbol" data-symbol-only="true" />')
    pieces.append(f'<circle class="source-hit-target" cx="{x:.9f}" cy="{y:.9f}" r="{9 / zoom:.9f}" data-hit-target="true" /></g>')
    return "".join(pieces)


def _directions(p: _Projection, key: str, text: dict, zoom: float) -> str:
    labels = [text["north"], text["east"], text["south"], text["west"]] if p.zenith_altaz else (["Alt +", "Az +", "Alt −", "Az −"] if key == "altaz" else ["Dec +", "RA +", "Dec −", "RA −"] if key == "j2000" else ["b +", "l +", "b −", "l −"])
    return "".join(f'<text class="compass-label" x="{p.cx + (p.radius + 21 / zoom) * math.sin(i * math.pi / 2):.9f}" y="{p.cy - (p.radius + 21 / zoom) * math.cos(i * math.pi / 2) + 5 / zoom:.9f}" text-anchor="middle">{label}</text>' for i, label in enumerate(labels))


def render_all_sky_svg(
    sources: Iterable[Source], at_time: datetime, constraints: ConstraintSet,
    selected_index: Optional[int] = None, telescope: TelescopeConfig = LACT_TELESCOPE,
    language: str = "en", highlighted_indexes: Optional[Iterable[int]] = None,
    trajectory_end: Optional[datetime] = None,
    trajectory_enforce_current_pointing: bool = True,
    trajectory_ranges: Optional[Iterable[tuple[datetime, datetime]]] = None,
    trajectory_display_time: Optional[datetime] = None,
    display_frame: str = "altaz", zoom: float = 1.0,
    bounds: Optional[tuple[float, float, float, float]] = None,
    grid_step_deg: Optional[float] = None,
) -> tuple[str, dict]:
    """Zenith-centred hemisphere. bounds is SVG (x,y,width,height), not sky bounds.

    Zoom only changes the viewBox and annotation scale, never observing rules.
    All longitudes (including FK5 J2000 RA) are labelled in degrees.
    """
    display_frame = _normalise_display_frame(display_frame)
    sources = list(sources)
    highlighted = set(highlighted_indexes or ())
    text = _labels(language)
    snapshot = (sky_trajectory_snapshot(
        sources, at_time, trajectory_end, constraints, telescope,
        enforce_current_pointing=trajectory_enforce_current_pointing,
        time_ranges=list(trajectory_ranges) if trajectory_ranges is not None else None,
        display_time=trajectory_display_time,
    ) if trajectory_end is not None else sky_snapshot(sources, at_time, constraints, telescope))
    display_time = trajectory_display_time if trajectory_end is not None and trajectory_display_time is not None else at_time
    frame = _frame(display_frame, display_time, telescope)
    p = _Projection(_zenith_coordinate(display_time, telescope).transform_to(frame), 350, 335, 260, 90, display_frame == "altaz")
    viewbox, zoom, view = _viewbox(760, 700, p.cx, p.cy, zoom, bounds)
    grid, step = _grid(p, display_frame, zoom, view, grid_step_deg)
    clip = f'sky-clip-{display_frame}'
    lines = [f'<svg class="sky-map-svg" data-display-frame="{display_frame}" data-projection="azimuthal-equidistant" data-center="zenith" data-zoom="{zoom:.9f}" data-grid-step-deg="{step:.9f}" viewBox="{viewbox}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="{_esc(telescope.name)} {_esc(_display_label(display_frame))} map">',
             f'<title>{_esc(telescope.name)} {_esc(_display_label(display_frame))} map</title><desc>Zenith-centred 90 degree hemisphere; coordinates in degrees; symbols and hit areas are not angular extensions. Pressure=0 hPa.</desc>', _styles(zoom),
             f'<defs><clipPath id="{clip}"><circle cx="350" cy="335" r="260" /></clipPath></defs>',
             '<circle class="sky-surface" cx="350" cy="335" r="260" />',
             f'<g class="map-clipped" clip-path="url(#{clip})">', grid]
    pointing = SkyCoord(az=telescope.pointing_azimuth_deg * u.deg, alt=telescope.pointing_altitude_deg * u.deg, frame=_altaz(display_time, telescope))
    lines.append(f'<path class="realtime-fov-ring" d="{p.path(_boundary(pointing, telescope.fov_radius_deg))}" role="img" aria-label="{_esc(telescope.name)} FoV, diameter {telescope.fov_diameter_deg:.2f} degrees"><title>{_esc(telescope.name)} FoV: {telescope.fov_diameter_deg:.2f}° diameter</title></path>')
    px, py, _ = p.project(pointing)
    lines.append(f'<text class="realtime-fov-label" x="{px:.9f}" y="{py + 31 / zoom:.9f}" text-anchor="middle">{_esc(telescope.name)} FoV</text>')
    visible_count = below_count = 0
    source_by_key = {source.source_key: source for source in sources}
    source_by_index = {source.index: source for source in sources}
    # One vector transform for a full catalogue, rather than thousands of
    # independent frame/ephemeris constructions. Snapshot AltAz is already at
    # the common display instant and includes the solver's physical geometry.
    geometries = [item["geometry"] for item in snapshot["sources"]]
    projected = p.project(SkyCoord(
        az=np.array([g["target_azimuth_deg"] for g in geometries]) * u.deg,
        alt=np.maximum(0, np.array([g["target_altitude_deg"] for g in geometries])) * u.deg,
        frame=_altaz(display_time, telescope),
    )) if geometries else ([], [], [])
    for row, item in enumerate(snapshot["sources"]):
        geometry = item["geometry"]
        item_source = source_by_key.get(item.get("source_key")) or source_by_index[item["index"]]
        visible = float(geometry["target_altitude_deg"]) >= 0
        if visible:
            visible_count += 1
        else:
            below_count += 1
            if trajectory_end is None and item["index"] != selected_index:
                continue
        # Below-horizon selected/trajectory records are explicit boundary
        # indicators; no false angular extension is rendered at that location.
        position = tuple(values[row] for values in projected)
        extra = f' status-{STATUS_CLASS.get(item["status"], "red")}'
        extra += " selected-source" if item["index"] == selected_index else ""
        extra += " trajectory-highlight" if item["index"] in highlighted else ""
        title = f'{item["display_name"]} | {item["status"]}' + (" | below horizon (boundary indicator)" if not visible else "")
        lines.append(_marker(item_source, None, p, zoom, extra, title, not visible, position))
    if snapshot["sources"]:
        geometry = snapshot["sources"][0]["geometry"]
        for kind in ("sun", "moon"):
            altitude, azimuth = float(geometry[f"{kind}_altitude_deg"]), float(geometry[f"{kind}_azimuth_deg"])
            snapshot[kind] = {"altitude_deg": altitude, "azimuth_deg": azimuth}
            if altitude >= 0:
                coordinate = SkyCoord(az=azimuth * u.deg, alt=altitude * u.deg, frame=_altaz(display_time, telescope))
                x, y, _ = p.project(coordinate)
                lines.append(_body_icon(float(x), float(y), kind, text[kind], zoom))
    lines.extend(['</g>', _directions(p, display_frame, text, zoom), f'<text class="ring-label horizon-label" x="110" y="125">{text["horizon"]}</text>', '</svg>'])
    snapshot.update({"display_frame": display_frame, "display_frame_label": _display_label(display_frame), "visible_source_count": visible_count, "below_horizon_source_count": below_count, "lact_pointing": {"mode": telescope.pointing_mode, "altitude_deg": telescope.pointing_altitude_deg, "azimuth_deg": telescope.pointing_azimuth_deg, "fov_diameter_deg": telescope.fov_diameter_deg, "fov_radius_deg": telescope.fov_radius_deg}, "highlighted_source_indexes": sorted(highlighted), "map_display_time": _utc(display_time).isoformat(), "map_viewbox": list(view), "grid_step_deg": step})
    return "".join(lines), snapshot


def _local_position(center, other) -> tuple[float, float]:
    return float(center.separation(other).to_value(u.deg)), float(center.position_angle(other).to_value(u.deg))


def render_local_fov_svg(
    source: Source, sources: Iterable[Source], at_time: datetime,
    selected_status: Optional[dict] = None, telescope: TelescopeConfig = LACT_TELESCOPE,
    language: str = "en", display_frame: str = "altaz", zoom: float = 1.0,
    bounds: Optional[tuple[float, float, float, float]] = None,
    grid_step_deg: Optional[float] = None,
) -> str:
    """Target-centred spherical map; API-compatible optional display settings."""
    del selected_status
    display_frame = _normalise_display_frame(display_frame)
    text = _labels(language)
    time = Time(_utc(at_time))
    frame = _frame(display_frame, at_time, telescope)
    center = source_coord(source).transform_to(frame)
    p = _Projection(center, 330, 300, 235, max(6.5, telescope.fov_radius_deg * 1.4))
    viewbox, zoom, view = _viewbox(680, 620, p.cx, p.cy, zoom, bounds)
    grid, step = _grid(p, display_frame, zoom, view, grid_step_deg)
    clip = f'local-clip-{display_frame}'
    lines = [f'<svg class="fov-map-svg" data-display-frame="{display_frame}" data-projection="azimuthal-equidistant" data-center="target" data-center-source-key="{_esc(source.source_key)}" data-zoom="{zoom:.9f}" data-grid-step-deg="{step:.9f}" viewBox="{viewbox}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Telescope local FoV map">',
             '<title>Telescope local FoV map</title>',
             f'<desc>Centre is selected source; circle is a {telescope.fov_diameter_deg:.2f} degree hard FoV. {_esc(_display_label(display_frame))}; coordinates in degrees. Source symbols and hit areas are not extensions.</desc>', _styles(zoom),
             f'<defs><clipPath id="{clip}"><circle cx="330" cy="300" r="235" /></clipPath></defs>',
             '<circle class="fov-surface" cx="330" cy="300" r="235" />',
             f'<g class="map-clipped" clip-path="url(#{clip})">', grid,
             f'<circle class="fov-ring" cx="330" cy="300" r="{telescope.fov_radius_deg * p.scale:.9f}" />',
             f'<text class="fov-ring-label" x="{330 + telescope.fov_radius_deg * p.scale + 8 / zoom:.9f}" y="{300 + 4 / zoom:.9f}">{text["radius"]} {telescope.fov_radius_deg:.2f}°</text>']
    candidates = [source if candidate.source_key == source.source_key else candidate for candidate in sources]
    if not any(candidate.source_key == source.source_key for candidate in candidates):
        candidates.append(source)
    coordinates = SkyCoord(ra=np.array([candidate.ra for candidate in candidates]) * u.deg,
                           dec=np.array([candidate.dec for candidate in candidates]) * u.deg, frame=J2000_FRAME)
    projected = p.project(coordinates)
    for row, candidate in enumerate(candidates):
        position = tuple(values[row] for values in projected)
        if position[2] > p.angular_radius + max(candidate.ext, 0):
            continue
        selected = candidate.source_key == source.source_key
        extra = " local-selected-star selected-source" if selected else " local-source-star"
        lines.append(_marker(candidate, None, p, zoom, extra, position=position))
    horizon_frame = _altaz(at_time, telescope)
    for body, kind in ((get_sun(time).transform_to(horizon_frame), "sun"), (get_body("moon", time, telescope.location).transform_to(horizon_frame), "moon")):
        if float(body.alt.deg) < 0:
            continue
        x, y, separation = p.project(body)
        if separation <= p.angular_radius:
            lines.append(_body_icon(float(x), float(y), kind, f'{text[kind]} {float(separation):.1f}°', zoom))
    lines.extend(['</g>', _directions(p, display_frame, text, zoom), f'<text class="selected-label" x="330" y="569" text-anchor="middle">{_esc(source.display_name)}</text>'])
    if source.ext > p.angular_radius:
        lines.append(f'<text class="warning-label" x="20" y="600">{text["extension_outside"]}: {source.ext:.3f}°</text>')
    lines.append('</svg>')
    return "".join(lines)
