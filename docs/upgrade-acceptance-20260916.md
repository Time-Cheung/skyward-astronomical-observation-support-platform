# Skyward upgrade acceptance — 2026-09-16

## Scope / 范围

This record covers the catalogue/UI upgrade, not production installation or LAN firewall acceptance. No existing service or firewall was changed. Production requirements are unchanged.

本记录覆盖源表与界面升级，不代表生产部署或局域网隔离验收；未修改已有服务和防火墙，生产依赖清单未新增包。

## Verified behaviour / 已验证行为

- Four installed catalogues: 2LHAASO 190, Fermi-LAT FL16Y 7224, Fermi-LAT 3FHL 1556, TeVCat 361 (cutoff 2026-09-16); 9331 records total.
- Stable source identities, paginated search, explicit empty layer selection, result target preserved when display catalogues change.
- Real Chromium: calculation feedback, real Crab window computation, three coordinate frames on both maps, 1000× redraw with stable symbol/text/hit-target sizes, Chinese/light and English/dark modes.
- Final 375 px retest: page width 375 px in both languages/themes; all header controls reachable.
- Real Gaia, no network mock: default 5° / 500 / G≤18; homepage and both Crab result maps return/draw 500 star polygons; subsequent requests report cached=true. Queries remain subject to upstream availability.
- Gaia returns a bounded unordered subset, not the brightest N or a representative sample; truncation and this selection policy are shown in the interface.
- Browser download: valid ZIP containing plan TXT and source-named geometry SVG.
- Frontend regression suite: 15 passed, including browser-gated cases, radius identity isolation, stale-response prevention and mobile layout.
- Final complete Python suite: **175 passed, 11 skipped, 17 warnings**, exit 0, 798.29 seconds. The 11 skips are browser-gated cases; the separate final frontend run executed all 15 frontend cases successfully. Warnings are dependency deprecations and documented astronomical edge-case normalization, not test failures.
- Syntax checks: Python compileall, node --check, git diff --check and pip check passed.

## Scientific boundaries / 科学边界

Fermi JSON outputs reproduce byte-for-byte from the supplied FITS. Localization uncertainty is not extension. FL16Y spectral-band index mapping remains unknown; 3FHL mapping is backed by documented official band definitions.

TeVCat normalization v4 passed focused independent review as a candidate-fact snapshot, not independently remeasured science. See [acquisition and normalization](tevcat-acquisition.md). There are 186 positional 2LHAASO candidate edges and zero verified associations; physical parameters are not copied across candidate associations. Unknown hard footprints never imply a zero-size confirmed source.

Gaia candidates are not certified calibration stars. Published J2016.0 directions are frame-transformed, not proper-motion propagated. 1000× is display magnification, not increased physical resolution. The planner remains geometry-only.

## Deployment / 部署

Use the bilingual guides for first installation or a clean fast-forward upgrade. Restart the actual installed application service after updating code/data, then hard-refresh browser assets. No package reinstall is required solely because of this upgrade if the existing environment already satisfies the pinned requirements; verify with pip check. LAN connectivity and access restrictions must be validated on the actual deployment network.
