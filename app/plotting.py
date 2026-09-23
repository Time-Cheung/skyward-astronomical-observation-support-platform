from __future__ import annotations

import io
from threading import Lock
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from .windows import WindowResult


@dataclass(frozen=True)
class PlotTheme:
    """Semantic Matplotlib colours for one Skyward display theme."""

    figure: str
    axes: str
    edge: str
    text: str
    tick: str
    grid: str
    target: str
    sun: str
    moon: str
    threshold: str
    window: str
    overlay: str


PLOT_RENDER_LOCK = Lock()

PLOT_THEMES = {
    "dark": PlotTheme(
        figure="#0c1117", axes="#111923", edge="#4c5a68", text="#e8eef4",
        tick="#b9c5d1", grid="#344250", target="#73b7ff", sun="#e4852f",
        moon="#d2d9e2", threshold="#d7a93c", window="#3fa86b", overlay="#ff8c42",
    ),
    "light": PlotTheme(
        figure="#f7f7f8", axes="#ffffff", edge="#9fa6b2", text="#151820",
        tick="#4f5865", grid="#d6dae1", target="#3333ff", sun="#c65d10",
        moon="#4e5968", threshold="#9a6500", window="#197447", overlay="#a33a14",
    ),
}


def render_window_plot(
    result: WindowResult, theme: str = "light", timezone_label: str = "UTC",
    timezone_offset_hours: float | None = None,
    zenith_overlays: Sequence[tuple[int, str, Sequence[float], str, str]] = (),
) -> str:
    """Thread-safe wrapper around process-global Matplotlib presentation state."""
    with PLOT_RENDER_LOCK:
        return _render_window_plot(result, theme, timezone_label, timezone_offset_hours, zenith_overlays)


def _render_window_plot(
    result: WindowResult, theme: str = "light", timezone_label: str = "UTC",
    timezone_offset_hours: float | None = None,
    zenith_overlays: Sequence[tuple[int, str, Sequence[float], str, str]] = (),
) -> str:
    """Render the three geometry curves with colours matching the page theme.

    Plot generation is server-side because geometry data never leaves the LAN.
    ``theme`` is a presentation preference only; it cannot affect numerical
    values, window boundaries or the source-selection calculation.
    """
    palette = PLOT_THEMES["dark" if theme == "dark" else "light"]
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            # Keep labels as SVG text for zero-compute presentation changes.
            "svg.fonttype": "none",
            "axes.unicode_minus": False,
            "figure.facecolor": palette.figure,
            "axes.facecolor": palette.axes,
            "axes.edgecolor": palette.edge,
            "axes.labelcolor": palette.text,
            "xtick.color": palette.tick,
            "ytick.color": palette.tick,
            "text.color": palette.text,
            "grid.color": palette.grid,
        }
    )
    times = result.sample_times
    series = result.series
    constraints = result.constraints
    def display_time(value: datetime) -> datetime:
        if timezone_label == "UTC":
            return value.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        if timezone_offset_hours is not None:
            return (value + timedelta(hours=float(timezone_offset_hours))).replace(tzinfo=None)
        if timezone_label == "Beijing UTC+8":
            return value.astimezone(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
        # Unknown labels cannot safely identify an IANA zone. Preserve UTC as a
        # conservative fallback instead of pretending the ticks are local.
        return value.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    plot_times = [display_time(value) for value in times]
    fig, axes = plt.subplots(3, 1, figsize=(11.5, 7.8), sharex=True)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.10, hspace=0.18)

    axes[0].plot(plot_times, series.target_zenith_deg, color=palette.target, linewidth=1.7, label="Target zenith")
    allowed_styles = {"solid": "-", "dotted": ":", "dashdot": "-."}
    for source_index, label, values, colour, line_style in zenith_overlays:
        # Curve colour and line style are explicit browser-managed presentation
        # choices. They never enter the numerical window calculation.
        curve, = axes[0].plot(
            plot_times, values, color=colour, linewidth=1.35,
            linestyle=allowed_styles.get(line_style, "-."), label=label,
        )
        curve.set_gid(f"zenith-overlay-{source_index}")
    if constraints.target_min_zenith_deg is not None:
        axes[0].axhline(constraints.target_min_zenith_deg, color=palette.threshold, linestyle="--", linewidth=1)
    if constraints.target_max_zenith_deg is not None:
        axes[0].axhline(constraints.target_max_zenith_deg, color=palette.threshold, linestyle="--", linewidth=1)
    axes[0].set_ylabel("Zenith (deg)")
    axes[0].invert_yaxis()
    # Keep the target and every optional comparison curve identifiable in the
    # saved SVG.  The legend is part of the exported scientific figure, not
    # only a browser-side decoration, so it remains available in ZIP copies.
    axes[0].legend(
        loc="upper left", fontsize=8, frameon=True, framealpha=0.88,
        facecolor=palette.axes, edgecolor=palette.edge,
    )

    axes[1].plot(plot_times, series.sun_altitude_deg, color=palette.sun, linewidth=1.6)
    if constraints.sun_max_altitude_deg is not None:
        axes[1].axhline(constraints.sun_max_altitude_deg, color=palette.threshold, linestyle="--", linewidth=1)
    axes[1].set_ylabel("Sun altitude (deg)")

    axes[2].plot(plot_times, series.moon_separation_deg, color=palette.moon, linewidth=1.6)
    if constraints.moon_min_separation_deg is not None:
        axes[2].axhline(constraints.moon_min_separation_deg, color=palette.threshold, linestyle="--", linewidth=1)
    axes[2].set_ylabel("Moon separation (deg)")
    axes[2].set_xlabel(timezone_label)

    for axis in axes:
        axis.grid(True, alpha=0.45, linewidth=0.6)
        for window in result.full_footprint_windows:
            axis.axvspan(
                display_time(window.start),
                display_time(window.end),
                color=palette.window, alpha=0.18,
            )
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M"))

    output = io.StringIO()
    fig.savefig(output, format="svg", transparent=False)
    plt.close(fig)
    svg = output.getvalue()
    start = svg.find("<svg")
    svg = svg[start:]
    # Matplotlib embeds a metadata link in SVG output by default. The plot is
    # rendered locally and must not advertise or depend on an external asset.
    svg = svg.replace("https://matplotlib.org/", "matplotlib")
    return svg
