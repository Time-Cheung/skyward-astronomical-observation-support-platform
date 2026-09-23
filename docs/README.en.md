# Skyward User Guide (English)

[中文](README.zh-CN.md) · [Deployment](DEPLOYMENT.en.md) · [Development](DEVELOPMENT.en.md)

## 1. Overview and goals

Skyward is an observing-support platform for observatories and telescopes. The current LACT/LHAASO adapter uses explainable geometry to show where a target is, whether it passes selected constraints, and which candidate windows exist.

The long-term goal is to combine catalogues, sky geometry, telemetry, weather and atmospheric quality, trajectory feasibility, and multi-facility coordination. The formal current release is **V0 / v2.1 (full version 2.1.20260924)**; it sends no device commands and does not replace schedulers, operators, or safety interlocks.

## 2. Current features

- Home and result all-sky maps in AltAz, FK5 J2000, or Galactic coordinates, with a sparse 60° longitude / 30° latitude default grid.
- Draft-and-confirm ordinary catalogue selection: installed row counts are reported dynamically by the catalogue API, plus temporary CSV uploads.
- Every result local map covers a target-centred 10° diameter. The LACT 8.3° hard FoV remains a separate blue dashed circle.
- Gaia DR3 is available only through **Load Gaia DR3** on the result local map and never appears in an all-sky picker/layer or as a planning target. Users can choose a 0.1–5° radius around the target, a faintest G magnitude from 5–22, and 1–500 sources; defaults are 1°, G≤10, and 10 sources; when more sources qualify, the nearest N sources by angular distance to the target are selected.
- Gaia candidates are red/green cross symbols; catalogue sources remain red/yellow/green stars. Exact-parameter cache entries are reused first; queries broader, deeper, or larger than the defaults use asynchronous TAP. Results are ordered by angular distance to the target within the requested cone and truncated to the nearest N sources; they are not a complete catalogue.
- Up to 30 days per request, with one-second candidate scanning in bounded chunks, cross-chunk merging, and bounded/downsampled display series.
- Source details, Chinese/English, automatic/light/dark themes, Beijing/UTC, display zoom, and an observing plan accumulated for the lifetime of the browser tab. Full-footprint windows are separate rows selected by default, while Preview, Add, and Download appear only once. One addition creates one target plan containing all checked windows; each window gets its own zero-to-three alternative search: candidates are coarsely ranked by overlap, gap, duration difference and stable source key, then exactly validated; users may upload a dedicated CSV alternative directory, which becomes the exclusive candidate pool for that plan, otherwise the selected ordinary catalogues are used. Each window can be edited separately in preview. The exported `skyward-observing-plan.xlsx` writes one yellow target row per selected window followed by its green alternative rows, with a solid black header, window number, ranking metrics, stage, and warnings. Optional local-FoV and observing-window SVGs remain separately named per target plan under `plots/`; observing-window SVGs include comparison-curve legends, while local-FoV SVGs use a light background, target ID 1, and a source-name legend.

## 3. Scientific and safety boundaries

The default LACT site is 100.0266666667° E, 29.3575° N, altitude 4410 m, with an ideal 8.3° circular FoV. This release has no authoritative live telescope pointing, so no map mode or source-observability decision applies a “currently inside the FoV” constraint. The blue FoV circle is geometry around the selected target only.

The planner can evaluate Sun altitude, Moon separation, target zenith angle, nominal footprint, and minimum duration. A source with an unknown extension is evaluated using a zero-radius point-source fallback; the result retains an explicit warning and does not prove the real extended footprint. It excludes weather, clouds, aerosols, equipment health, mechanical limits, tracking error, true response/sensitivity, priority, and formal joint-observation approval. Green states and returned windows are not authorization. One-second scanning does not guarantee every sub-second event.

The TeVCat public snapshot is dated 2026-09-19. Its 223 upstream “Extended: No” rows are known zero-radius point sources; 140 “Extended: Yes” rows lack a verified hard-boundary radius and retain an unknown footprint. Cross-catalogue proximity is candidate evidence only, not identity, and does not copy physical parameters.

Gaia notes may include IDs, ICRS/J2000 coordinates, G/BP/RP magnitudes, parallax, simple inverse-parallax distance, proper motion, RUWE, visibility periods, and provenance. The simple distance has no prior or uncertainty correction. J2016.0 directions are transformed to FK5 J2000 without proper-motion propagation.

## 4. Workflow

1. Open **Select catalogues** on the home all-sky map, edit ordinary catalogue choices, and choose **Confirm & load**. Cancel, Escape, and outside clicks do not apply the draft; empty is valid.
2. Select a catalogue target or enter a temporary name, RA, Dec, and radius.
3. Choose at most 30 days and the Sun, Moon, zenith-angle, and minimum-window constraints, then calculate.
4. Inspect target status, the all-sky map, target-centred 10° local map, plot, and windows. The two maps share Real-time, Observation window, and Specified time modes, ordinary-source colours, and purple tracked-FoV outlines during an observation window. Specified time accepts a point or a range of no more than 24 hours. Display-layer changes do not replace the target. The current target's details omit **Use for planning**, while other ordinary sources retain it and can be recalculated as the new target.
5. When local candidates are needed, set the radius (0.1–5°), faintest G magnitude, and maximum source count, then choose **Load Gaia DR3**. Defaults are 1°, G≤10, and 10 sources; when more qualify, the nearest N by angular distance to the target are selected; ordinary markers remain. Gaia observability follows the shared Real-time / Observation window / Specified time state and is drawn as a thicker green or red cross. Status reports observable/unavailable counts and distinguishes pending, cache, successful zero, truncation, and failure. Disabling removes only Gaia.
6. Open an ordinary marker on either map for coordinates, provenance, notes, and geometry. A non-target ordinary source can be added to the Zenith-Time comparison; progress and outcome appear below the map that initiated it. Keep or clear the default check on each full-footprint-window row, then use the single action group below the list to add, preview, or download. One addition creates one target plan containing every checked window; preview edits each interval separately and also supports notes, deletion, and clearing the plan.

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
