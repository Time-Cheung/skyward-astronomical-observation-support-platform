# Developer notes and known approximation boundaries

## Status look-ahead sampling

`source_status()` and the all-sky status view evaluate the current instant plus the requested minimum-window interval. The sample spacing is at most 60 seconds for ordinary intervals and is capped at 3,601 samples for very long intervals. This is a practical UI calculation bound, not a formal proof of continuity for arbitrary long windows; the authoritative window endpoint result comes from `calculate_windows()`.

## Window discovery

`calculate_windows()` evaluates every requested second, detects each sampled pass/fail transition, and then bisects the corresponding signed constraint margin to a sub-second boundary. This deliberately supersedes the former coarse-grid approach. The default `minimum_window_seconds=0` means that no duration filter is applied; it does not weaken the sampling cadence. A valid excursion containing at least one sampled second cannot disappear merely because it lies between former minute marks. A sub-second excursion that has no sampled passing second cannot be guaranteed without a higher-resolution physical/event solver.

The result may keep a scientifically valid sub-second interval, but the downloadable observing-plan action is deliberately stricter: it is offered only if the interval contains at least two independently re-evaluated, physically valid whole-second instants. The prefilled plan endpoints are rounded inward and verified so the browser’s second-precision input cannot move a plan across a constraint boundary.

For the legacy fixed-FoV compatibility route, `calculate_catalogue_windows()` transforms its candidate catalogue sources jointly in ten-minute batches. Sun and Moon are calculated once per batch; adjacent batches share and de-duplicate their boundary second. Batch results are regression-tested against the normal per-source calculator across a batch boundary. This improves throughput without changing the one-second discovery or sub-second-boundary contract.

To keep this guarantee usable on the LAN server, requests are limited to one day. A larger horizon requires a separately validated streaming or event-solver implementation rather than silently restoring a coarse grid. The model still excludes abrupt telescope, weather, and telemetry events because those inputs are outside this geometry-only release.

## Angular footprint

The source extension is treated as a nominal circular angular radius. `ext_err` and `p_err(95%)` are displayed but do not change the classification. This is a planning approximation, not a flux-containment or instrument-response calculation.
