# Skyward Development Guide (English)

[中文](DEVELOPMENT.zh-CN.md) · [User guide](README.en.md) · [Deployment](DEPLOYMENT.en.md)

## 1. Architecture and layout

- app/main.py: FastAPI pages, JSON APIs, bounded queries, and error contracts.
- app/catalog.py and app/gaia.py: local catalogues, temporary uploads, and independent online Gaia.
- app/sky_map.py: spherical projection, true coordinate grids, symbols, and local/all-sky SVG.
- app/windows.py and app/constraints.py: geometry constraints, one-second candidates, boundaries, and windows.
- app/static and app/templates: bilingual, CDN-free frontend.
- data: catalogues, provenance, bundled IERS; scripts: acquisition/normalization; tests: unit, API, contract, and browser coverage.

Ordinary catalogue status comes from /api/v1/sky/current and /api/v1/sky/local-fov. Gaia does not enter catalog_tokens, /api/v1/sources, or planning targets. The web UI requests /api/v1/gaia?map_kind=local-fov with the radius, magnitude, and row filters only when the user presses the result-local Gaia loader button. Backend map_kind=current remains for API compatibility only.

## 2. Geometry and display contracts

All-sky maps use true AltAz/J2000/Galactic curves, with 60° longitude and 30° latitude defaults and sparse adaptive deep-zoom steps. An ordinary source has one hollow star; transparent hit targets must not acquire strokes; known extension is a separate faint dashed outline. A tracked-FoV source receives a purple star outline, never a second hollow circle.

Every local map has a target-centred 5° display radius (10° diameter) and exposes data-display-radius-deg=5. The telescope hard FoV is separate and exposed as data-fov-radius-deg; LACT defaults to 4.15°, so its dashed blue radius is 4.15/5 of the map radius. Oversized custom FoVs may be clipped.

Catalogue colours are red for centre failure, yellow for centre pass/known-edge failure, and green for centre plus footprint pass. If a catalogue says a source is extended but provides no valid extension radius, observability is deliberately evaluated with a zero-radius point-source fallback. The original provenance remains `footprint_known=false` and `planning_radius_deg=null`; APIs, details, and window results carry `point_source_fallback`, so this assumption must never be reported as validation of the real extended footprint. Gaia has known ext=0, uses red/green cross symbols, and never gets yellow or an extension outline.

## 3. Thirty-day window scanning

Requests may span 30 days. Scientific discovery still uses one-second candidates, processed in bounded 600-second chunks. Adjacent chunks share/de-duplicate boundary seconds and cross-chunk intervals merge. Signed-margin transitions receive refined boundaries. Plot series are bounded to 12,001 points and downsampled without changing decisions.

minimum_window_seconds=0 only disables duration filtering. A short event containing a passing sampled second can be found; a wholly sub-second event with no passing integer second is not guaranteed. Browser plans are stricter and require at least two independently revalidated whole seconds.

## 4. Frontend/backend state contracts

Catalogue checks edit a draft; confirmation alone changes catalog_tokens, maps, and the home target picker. Cancel, Escape, and outside clicks restore applied choices. Result targets always retain stable source_key identity.

The result all-sky and local maps share one state selector: real-time, calculated observation window, or specified time. Specified time can be one instant or an interval of at most 24 hours; an interval uses trajectory-style classification and draws all positions at its start. The local map has no independent live/fixed state and uses the same source colours, selected-target outline, and tracked-FoV outline as the all-sky map; trajectory mode must send the same highlight_indexes to both map endpoints. Result source details are read-only and target selection remains in the home planner; the internal one-shot pending map state is retained only for compatibility with existing result rebuild flows and must not affect a fresh home calculation. There is no authoritative live pointing, so sky_snapshot and all result maps use enforce_current_pointing=false. The FoV circle and purple tracked-FoV markers express target-centred geometry, not device pointing.

Result-navigation contract: before leaving a result page, `snapshotResultPage()` stores the rendered DOM (including SVG maps, mode/specified-time controls, Gaia overlay, camera zoom, Zenith-Time overlays, and status text) in versioned `skyward.result-page-cache.v1` sessionStorage. The Data notes/API planner link validates a same-origin /result URL, then `restoreCachedResultPage()` writes the snapshot back and marks `initialiseResultMaps()` to skip its first refresh/refreshLocal; returning therefore does not recalculate windows or request maps. A storage failure never blocks navigation and falls back to the existing GET /result rebuild; direct refreshes and other tabs are not guaranteed to be compute-free. The result source dialog hides `dialog-use-source` only for the current target; other ordinary sources may replace the target through the preserved result form, while Gaia sources remain display-only. Local zoom controls share the local heading row and wrap again on narrow screens.

The local Gaia loader button is idle by default and does not query until pressed. Pressing it keeps the ordinary local map and overlays data-gaia-layer using the shared mode parameters, frame, target, telescope, and constraints. Known ext=0 Gaia rows use the same instant/range classification as ordinary sources but only red or green. The SVG gaia-cross uses currentColor and status-red/status-green rules override theme colour; the endpoint returns per-row status plus status_counts. A new load aborts the previous request and replaces only the Gaia overlay without deleting catalogue markers. Generation counters plus AbortController prevent stale replacement. Status distinguishes pending, cache, successful zero, truncation, and error and shows filters, query strategy, returned/drawn counts, red/green counts, and the real failure reason. If a synchronous default-or-smaller request times out, at most five half-radius subcones remain inside the original cone; rows are locally clipped/deduplicated by source_id and fallback output is explicitly incomplete and unordered. A request with any filter above its default uses asynchronous TAP and does not enter the synchronous subcone fallback.

The observing plan remains in versioned sessionStorage, accumulates across result pages, and is previewable. Its isolation boundary is **same origin + browser session + tab**: different computers, browsers, browser profiles, and independent private sessions do not share plans. The current release has no account, tenant, or server-side authorization isolation; sessionStorage must not be treated as an account-level security boundary. Plans must not be written to a server database or moved to localStorage, because that would widen sharing within a browser profile.

The plan lifecycle contract is: refreshes, same-tab result → Data notes/API → result navigation, and browser forward/back preserve the plan; **Clear current observing plan** clears it; closing and reopening a tab or the browser starts a new session and clears it; clearing site data and ending a private session clear it. Do not use `beforeunload` or `pagehide` to clear storage, because those events also occur during refresh. Upgrading the application storage container from `skyward.observation-plan.v2` to `v3` does not migrate old plans. A browser’s restore-previous-session or reopen-closed-tab feature may restore sessionStorage; this browser-dependent exception cannot be forcibly distinguished from a new session by pure frontend logic.

Each selected plan window starts its own asynchronous alternatives request. Candidates are coarsely ranked by overlap descending, gap ascending, duration difference ascending, candidate duration descending, and stable source key ascending, then exactly validated; at most three are returned. An uploaded temporary CSV is used only as the candidate pool and never changes target resolution; without it, the selected ordinary catalogues remain the pool. only the current page's full-footprint-window section shows the active source and window number. A plan entry stores all selected windows in `windows[]`, with per-window planned times, alternatives, screening state, metrics, and warnings. The downloaded ZIP contains a browser-generated, macro-free `skyward-observing-plan.xlsx` OOXML workbook: one plan may produce multiple target rows, one per selected window, followed by that window's green alternative rows. The header is a solid black fill and target rows are yellow; no CDN is permitted. When plots are selected, every entry captures the observing-window SVG and an export-enhanced local-FoV SVG with a three-digit plan sequence so duplicate target names cannot overwrite files. The local copy forces a light background, target ID 1 and a source-name legend; Matplotlib writes the observing-window curve legend directly into the SVG.

## 5. Data maintenance and TeVCat

Fermi builds use scripts/build_fermi_catalogues.py, preserve FITS fields/units/version, and never interpret localization error as physical extension. Display names remove duplicated catalogue prefixes.

Reproducible TeVCat www acquisition:

~~~bash
.venv/bin/python scripts/fetch_tevcat_www.py --output /secure/staging/tevcat-www-YYYYMMDD
.venv/bin/python scripts/build_tevcat_www_catalogue.py --staging /secure/staging/tevcat-www-YYYYMMDD
.venv/bin/python scripts/validate_tevcat_www.py
~~~

The fetcher performs two certificate-verified public-page reads, parses public dat, and stops if the ID set changes. The manifest records retrieval/snapshot times, response/payload/ID hashes, group counts, and extractor version. Raw HTML is not committed. The builder projects public fields only, removing private/operator/ownership/token data and not redistributing long HTML notes or papers.

Of 363 rows, 223 explicit Extended: No records become planning_radius_deg=0.0 and footprint_known=true; 140 Extended: Yes rows without verified hard radii remain null/unknown. Proximity yields candidate audit edges, never identity or copied physics. Every update refreshes provenance, hashes, counts, and tests.

## 6. Gaia and IERS maintenance

Gaia bounds are radius 0.1–5°, with the web/API endpoint capped at 500 rows and G limit 5–22; the local default is 1°/10/G≤10, with nearest-by-angular-distance selection, with two concurrent queries, 2 MiB responses, and 32 exact-parameter cache entries. Default or smaller requests use synchronous TAP with a 30-second timeout; requests broader, deeper, or larger than the defaults check cache first and use asynchronous TAP with a 30-second total budget on a miss. A synchronous timeout may use at most five half-radius bounded subcones with a 50-second total budget. ADQL orders by angular distance to the target and the client repeats a J2000 spherical-distance sort; metadata declares selection=nearest_by_angular_distance and ordering=angular_distance_asc. Preserve fields, units, and provenance. Do not present inverse parallax as precision distance or frame transformation as proper-motion propagation.

IERS startup selects a fresh cache or bundled table and then performs a bounded background refresh; failure retains the active table and records an error. Network policy provides strict offline behavior. Preserve the old file/hash for bundled updates and verify parsing, coverage, and the full suite; a fresh cache can override a newly replaced bundled file.

## 7. Test matrix

~~~bash
.venv/bin/python -m compileall -q app tests
node --check app/static/app.js
.venv/bin/python -m pytest -p no:cacheprovider -q
git diff --check
~~~

Real Chromium covers catalogue draft/confirm/empty state, no all-sky Gaia request, the local Gaia loader button with 1°/10/10 defaults and custom filters, ordinary-source preservation, cancellation/stale response, three frames, fixed/live time, themes/languages, and 375 px layout. Data tests cover TeVCat point/unknown semantics, Gaia fields, and 30-day chunk boundaries. Keep browser tools separate from production dependencies.

## 8. Versioning and release

Full versions use major.minor.YYYYMMDD. Major identifies an architecture generation; minor increments by functional milestone; the date is the milestone confirmation date.

- 1.1.20260901: initial planner, extensible telescope scope, and V0 boundary.
- 1.2.20260911: catalogue overlays and multiple display frames.
- 1.3.20260916: multiple catalogues, reliable Gaia queries, deployment system.
- 1.4.20260919: confirmable catalogue selection, sparse grids, data notes.
- 1.5.20260919: TeVCat/Gaia/30-day planning upgrade.
- 1.6.20260919: bounded-memory long-range display fix.
- **2.1.20260924**: result-local Gaia only, fixed 10° local map, shared map state and compute-free page restoration, editable multi-window observing plans with XLSX/SVG export, dedicated alternative-source catalogues, serialized Zenith-Time refreshes, and documentation consolidation.

Version 2.1.20260924 is the formal release explicitly requested by the user, packaged as skyward-v2.1.zip. Future versions still require an explicit user release request, a confirmed date, the full suite and available browser acceptance, and a skyward-v<major.minor>.zip archive from controlled clean source. Thus 1.6.20260919 maps to skyward-v1.6.zip. The filename omits the date, while the archive records the full version, date, Git state, manifest, and SHA-256. Exclude .venv, caches, credentials, personal files, and temporary artifacts. Ordinary development neither increments versions nor creates formal archives.

## Copyright and developer

Copyright © 2026 Wei Zhang. All rights reserved.

Developer: **Wei Zhang (张炜)**, Postdoctoral Researcher at the Institute of High Energy Physics, Chinese Academy of Sciences (IHEP-CAS). The affiliation is provided for identification only and does not imply institutional ownership or endorsement.
