# Skyward UI refinement — 2026-09-19

## Delivered / 已实现

- All-sky grids default to 60-degree longitude / 30-degree latitude spacing in AltAz, J2000 and Galactic frames. Local/deep-zoom views retain sparse adaptive true coordinate curves. Tick labels are lighter.
- Catalogue selection lives in the all-sky panel. Checkbox changes are drafts; Confirm & load applies them to maps and homepage target search. Cancel, Escape and outside clicks restore applied choices. Empty selection is explicit. Result targets remain stable.
- Dynamic target options use stable source keys. Source hit regions are invisible; ordinary sources have one hollow symbol, with known physical extension separately shown as a faint dashed boundary.
- Removed obsolete homepage single-catalogue copy. Data notes now include usage instructions, platform introduction and a five-catalogue single-select description. Data/API headings share the homepage V0 title style. Chinese/English and mobile layouts are retained.

## Validation / 验证

- Complete Python run: 185 passed, 17 skipped, 1 failed. The sole failure was an obsolete upload-immediately-load string assertion; it was migrated to confirmation semantics and independently rerun: 1 passed. No production code was changed for that failure. This is not reported as a single all-green full-suite run.
- Final frontend suite using the separate Playwright interpreter: 27 passed, no skips (new confirmation tests, existing frontend protection tests and data-note tests).
- Sparse-grid/marker tests: 24 passed.
- node --check (app.js, about.js), pip check and git diff --check passed.
- No production requirements, installed service or firewall changes. Browser tooling remains outside the repository.

完整回归唯一失败来自旧交互的字符串断言，更新为“上传进入草稿、确认后加载”后单独复验通过；浏览器组合套件27项全过。已取消源表不会替换已计算目标，真实延展范围没有被删除或当成点击热区。
