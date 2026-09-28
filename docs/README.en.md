# Skyward User Guide (English)

**Current version: V2.2 (full version 2.2.20260924).** The current tree includes catalogue icons, batch target lists, tracked-FoV curves, sorted windows, and plan-preview sorting.

**Date and time-zone convention:** the `YYYYMMDD` component of a full version is the Beijing calendar date (UTC+8). TeVCat `snapshot_date` also uses the Beijing calendar date, while `retrieved_at_*` timestamps use UTC. Specific observing times in the web interface always show the time zone selected in the page header; an ISO 8601 timestamp ending in `Z` is UTC.

[中文](README.zh-CN.md) · [Deployment](DEPLOYMENT.en.md) · [Development](DEVELOPMENT.en.md)

## 1. Overview and goals

Skyward is an observing-support platform for observatories and telescopes. The current LACT/LHAASO adapter uses explainable geometry to show where a target is, whether it passes selected constraints, and which candidate windows exist.

The long-term goal is to combine catalogues, sky geometry, telemetry, weather and atmospheric quality, trajectory feasibility, and multi-facility coordination. The current adapter uses explainable geometry for LACT/LHAASO. The formal release is **V2.2 (full version 2.2.20260924)**; it sends no device commands and does not replace schedulers, operators, or safety interlocks.

## 2. Current features

- Home and result all-sky maps in AltAz, FK5 J2000, or Galactic coordinates, with a sparse 60° longitude / 30° latitude default grid. Each non-Gaia catalogue row has a selectable marker icon (star, diamond, triangle, square, or circle) saved in this browser and shared by the home and result maps; Gaia remains a fixed cross and extensions remain cyan hollow rings.
- Draft-and-confirm ordinary catalogue selection: installed row counts are reported dynamically by the catalogue API, with temporary XLSX uploads. Skyward reads the first worksheet and requires headers in row 1. Source catalogues require `name,ra,dec` in J2000 degrees; optional extension/uncertainty fields and examples for all three upload types are documented on the Data notes page.
- Every result local map covers a target-centred 10° diameter. The LACT 8.3° hard FoV remains a separate blue dashed circle.
- Gaia DR3 is available only through **Load Gaia DR3** on the result local map and never appears in an all-sky picker/layer or as a planning target. In Observation-window mode, the result all-sky map can add every tracked-FoV source to Zenith-Time curves at once; the geometry/full-footprint panel lists target and curve-source full windows sorted by start time. The home planner also accepts a batch target XLSX with required `name,ra,dec,ext` and optional per-row constraint columns; omitted constraints inherit the planner fields, valid windows are added to the browser observing plan, and local/plot SVGs are saved by default. Preview sorting supports Added time, Total window duration, and Window start. Users can choose a 0.1–5° radius around the target, a faintest G magnitude from 5–22, and 1–500 sources; defaults are 1°, G≤10, and 10 sources; when more sources qualify, the nearest N sources by angular distance to the target are selected.
- Gaia candidates are red/green cross symbols; catalogue sources remain red/yellow/green stars. Exact-parameter cache entries are reused first; queries broader, deeper, or larger than the defaults use asynchronous TAP. Results are ordered by angular distance to the target within the requested cone and truncated to the nearest N sources; they are not a complete catalogue.
- Up to 30 days per request, with one-second candidate scanning in bounded chunks, cross-chunk merging, and bounded/downsampled display series.
- Source details, Chinese/English, automatic/light/dark themes, Beijing/UTC, display zoom, and an observing plan accumulated for the lifetime of the browser tab. Full-footprint windows are separate rows selected by default; each window can be edited separately in preview. Users may upload a dedicated XLSX alternative directory, which becomes the exclusive candidate pool for that plan; otherwise the selected ordinary catalogues are used. Preview supports sorting by added time, total window duration, and window start. Optional local-FoV and observing-window plots can be saved with each plan.

## 3. Scientific and safety boundaries

The default LACT site is 100.0266666667° E, 29.3575° N, altitude 4410 m, with an ideal 8.3° circular FoV. This release has no authoritative live telescope pointing, so no map mode or source-observability decision applies a “currently inside the FoV” constraint. The blue FoV circle is geometry around the selected target only.

The planner can evaluate Sun altitude, Moon separation, target zenith angle, nominal footprint, and minimum duration. A source with an unknown extension is evaluated using a zero-radius point-source fallback; the result retains an explicit warning and does not prove the real extended footprint. It excludes weather, clouds, aerosols, equipment health, mechanical limits, tracking error, true response/sensitivity, priority, and formal joint-observation approval. Green states and returned windows are not authorization. One-second scanning does not guarantee every sub-second event.

The default catalogue is a normalized snapshot of Table 2 from the public paper *The First LHAASO Catalog of Gamma-Ray Sources* (DOI `10.3847/1538-4355/acfd29`), containing 90 named 1LHAASO sources and 180 WCDA/KM2A components. For a two-component source, the position comes from the coordinate-bearing component with the higher TS, following the paper note. Component coordinates, 95% statistical position error, r39, TS, N0, photon index, TS100, associations, missing values, and limits remain in provenance. In Table 2 column six, `value ± error` identifies an extended component with a 1-sigma statistical error; `<value>` identifies a pointlike component and its 95% statistical upper limit. For the displayed extension, Skyward selects the larger measured r39 among extended KM2A/WCDA components. If the other component is pointlike, its upper limit is excluded even when numerically larger. Source details state the chosen component, uncertainty, rule, and DOI/Table 2 provenance. r39 is not a verified physical hard boundary. Consequently, 1LHAASO `planning_radius_deg` remains unknown and geometry uses the explicit warned point-source fallback. Table 2 associations are preliminary known-TeV counterparts from the paper's positional search, not Skyward-verified source identities. Explicit public TeVCat name, alias, or note matches are separately recorded with the 2026-09-25 Beijing time (UTC+8) snapshot provenance; positional proximity alone remains candidate evidence. N0 units are `10^-13` and `10^-16 cm^-2 s^-1 TeV^-1` for WCDA and KM2A, with reference energies 3 and 50 TeV. Zero-coded nondetections in the machine table are retained as upper limits, not scientific zeroes. The unpublished 2LHAASO source catalogue is not shipped with V2.2 and is not installed, named, or served as a catalogue through the UI or API. Temporary user uploads remain operator-provided data, but the 2LHAASO label is reserved and rejected. Documentation retains only this release-boundary explanation.

The TeVCat public snapshot is dated 2026-09-25 Beijing time (UTC+8). Its 223 upstream “Extended: No” rows are known zero-radius point sources; 140 “Extended: Yes” rows lack a verified hard-boundary radius and retain an unknown footprint. Cross-catalogue proximity is candidate evidence only, not identity, and does not copy physical parameters. Source details use catalogue unit metadata: TeVCat flux is shown in Crab, threshold in GeV, size in deg, and distance as kpc or dimensionless redshift z; Fermi raw fields use their catalogue-provided units.

Gaia notes may include IDs, ICRS/J2000 coordinates, G/BP/RP magnitudes, parallax, simple inverse-parallax distance, proper motion, RUWE, visibility periods, and provenance. The simple distance has no prior or uncertainty correction. J2016.0 directions are transformed to FK5 J2000 without proper-motion propagation.

## 4. Workflow

1. Open **Select catalogues** on the home all-sky map, edit ordinary catalogue choices, and choose **Confirm & load**. Cancel, Escape, and outside clicks do not apply the draft; empty is valid.
2. Select a catalogue target or enter a temporary name, RA, Dec, and radius.
3. Choose at most 30 days and the Sun, Moon, zenith-angle, and minimum-window constraints, then calculate.
4. Inspect target status, the all-sky map, target-centred 10° local map, plot, and windows. The two maps share Real-time, Observation window, and Specified time modes, ordinary-source colours, and purple tracked-FoV outlines during an observation window. Specified time accepts a point or a range of no more than 24 hours. Display-layer changes do not replace the target. The current target's details omit **Use for planning**, while other ordinary sources retain it and can be recalculated as the new target.
5. When local candidates are needed, set the radius (0.1–5°), faintest G magnitude, and maximum source count, then choose **Load Gaia DR3**. Defaults are 1°, G≤10, and 10 sources; when more qualify, the nearest N by angular distance to the target are selected; ordinary markers remain. Gaia observability follows the shared Real-time / Observation window / Specified time state and is drawn as a thicker green or red cross. Status reports observable/unavailable counts and distinguishes pending, cache, successful zero, truncation, and failure. Disabling removes only Gaia.
- When the result all-sky map is in Observation-window mode, click **Add all tracked-FoV source curves** to add every tracked source; the geometry/full-footprint panel lists all target and comparison-source windows by start time. The home planner also accepts a batch target XLSX with required `name,ra,dec,ext` and optional per-row constraint columns; omitted constraints inherit the planner fields, and valid windows are added to the browser observing plan with local/plot SVGs enabled by default. The preview supports Added time, Total window duration, and Window start sorting.

User source catalogues, batch target lists, and dedicated alternative catalogues all use `.xlsx` workbooks. Skyward reads the first worksheet and requires non-empty, unique headers in row 1; coordinates are J2000 degrees. Source and alternative catalogues require `name,ra,dec` and may include `ext,ext_err,p_err(95%),l,b`. Batch target lists require `name,ra,dec,ext` and may include `sun_max_altitude_deg,moon_min_separation_deg,target_min_zenith_deg,target_max_zenith_deg,minimum_window_seconds`; omitted planning constraints inherit the current page settings. Download the [source-catalogue XLSX example](../app/static/examples/user-source-catalogue.xlsx), [target-list XLSX example](../app/static/examples/target-source-list.xlsx), and [alternative-catalogue XLSX example](../app/static/examples/alternative-source-catalogue.xlsx). Limits are 1,000 rows and 512 KiB per workbook, with at most 8 MiB after decompression; names must be unique and 1–80 characters; RA/Dec must satisfy 0 ≤ RA < 360 and −90 ≤ Dec ≤ 90; negative extension or uncertainty values are rejected.

Before leaving a result page for Data notes or API, the current rendered view is saved in sessionStorage for the browser tab. Returning through “Sky map & planner” restores the maps, mode, times, Gaia layer, zoom, and comparison curves directly, without recalculating windows or requesting maps. A direct refresh, unavailable cache, or different browser tab falls back to the server-rendered result; this rule concerns the result-page view only, while the observing plan follows the lifecycle below. The result target's details do not offer “Use for planning”; other ordinary sources can still be filled into the planner from their details to replace the current target. Gaia candidates are display-only local-map layers. Local-map zoom controls share the heading row, while the status mode remains shared with the all-sky map.

### Observing-plan storage, isolation, and lifecycle

The observing plan is stored only in the same-origin browser `sessionStorage`; it is not written to a Skyward server database. The isolation boundary is **same origin + browser session + tab**: different computers, browsers, browser profiles, and independent private sessions do not share plans. The current release has no login, account, tenant, or server-side authorization isolation, so this is not account-level security isolation. People sharing one computer should use separate browser profiles or independent sessions and use **Clear current observing plan** before finishing.

Within one tab, the observing plan follows these rules:

| Operation | Plan state |
| --- | --- |
| Refresh the tab | Preserved |
| Leave the result page for Data notes/API and return | Preserved |
| Browser forward/back | Preserved |
| Choose **Clear current observing plan** | Cleared |
| Close and reopen the tab | Treated as a new session; cleared |
| Close and reopen the browser | Treated as a new session; cleared |
| Clear site data | Cleared |
| End a private/incognito session | Cleared |

When the application storage container is upgraded from `skyward.observation-plan.v2` to `v3`, old plans are not migrated. A browser’s **restore previous session** or **reopen closed tab** feature may restore `sessionStorage`; this is browser-dependent, so a restored old tab must not be assumed to be a new empty session.

## 5. Quick local installation

~~~bash
cd /path/to/skyward
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p .runtime/matplotlib .runtime/cache
export MPLCONFIGDIR="$PWD/.runtime/matplotlib"
export SKYWARD_CACHE_DIR="$PWD/.runtime/cache"
.venv/bin/python -m pytest -p no:cacheprovider -q
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

Open http://127.0.0.1:8000/ on the server. For LAN, systemd, offline wheels, upgrades, and rollback, use the [deployment guide](DEPLOYMENT.en.md). The unauthenticated service must not be exposed publicly.

## 6. FAQ

- Old UI after upgrade: restart the actual process, then Ctrl+Shift+R.
- No Gaia markers: Gaia exists only on the result local map; enable it and inspect status. Failure is not zero rows.
- Local catalogues work but Gaia fails: check server DNS, TLS, approved egress, and the finite timeout. Local geometry does not depend on Gaia.
- HTTP 422: check time order, 30-day ceiling, parameter bounds, and active IERS coverage.
- Does 1000× improve accuracy? No; it only magnifies the display.

## 7. Roadmap

Planned directions include pointing and equipment telemetry, weather/atmospheric quality, mechanical and trajectory safety, multi-telescope coordination, stronger extended-source evidence, and an authenticated, authorized, audited candidate-review-scheduling workflow.

## Copyright and developer

Copyright © 2026 Wei Zhang. All rights reserved.

Developer: **Wei Zhang (张炜)**, Postdoctoral Researcher at the Institute of High Energy Physics, Chinese Academy of Sciences (IHEP-CAS). The affiliation is provided for identification only and does not imply institutional ownership or endorsement.
