# TeVCat snapshot acquisition / TeVCat 快照采集

## Scope / 范围

This procedure acquires public TeVCat data into a **staging directory**. It does not register a catalogue in the running Skyward application and does not certify every scientific measurement. Keep staging outside the Git repository. Do not publish unreviewed site prose or paper text.

本流程把 TeVCat 公开数据采集到**中间目录**，不代表已在 Skyward 运行界面注册源表，也不代表独立核验了每项科学测量。中间目录应位于 Git 仓库之外，未经审查的网站说明和论文全文不进入公开提交。

## Commands / 命令

Use the existing project environment and its pinned requirements. No new production package is required. The scripts explicitly use the certifi trusted certificate-authority bundle (an existing httpx dependency), retain certificate and hostname verification, and do not modify system trust configuration. Never use insecure TLS switches to work around a certificate error.

使用现有项目环境和固定版本依赖，无需新增生产依赖。脚本显式使用 certifi 可信根证书库（httpx 的既有依赖），保留证书链与主机名校验，不修改系统信任库。不要以关闭 TLS 校验的方式绕过证书错误。

From the repository root / 在仓库根目录执行：

~~~bash
# 361 was independently observed on 2026-09-16. Recheck the official list
# before a future acquisition; do not silently reuse this count forever.
# 361 为 2026-09-16 实测数量，今后采集必须先重新检查官方完整列表。
.venv/bin/python scripts/fetch_tevcat.py \
  --output ../skyward-data-staging/tevcat-20260916 \
  --expected-count 361
.venv/bin/python scripts/validate_tevcat.py \
  ../skyward-data-staging/tevcat-20260916
.venv/bin/python -m pytest -o addopts='' -q tests/test_tevcat_acquisition.py
~~~

Use the same directory only to resume the same acquisition. Start a fresh directory for a new dated snapshot, otherwise cached records retain their original retrieval timestamps. An expected-count mismatch must be investigated, not bypassed by accepting whatever number the API returned.

同一目录仅用于同一次采集的断点恢复；新日期快照使用新目录，否则缓存条目保留原采集时间。预期数量不符时应调查分页、目录变更或异常，不能自动接受接口返回的任意数量。

## Normalized application snapshot / 应用规范化快照

After validating staging, rebuild the reviewed, limited application snapshot:

~~~bash
.venv/bin/python scripts/build_tevcat_catalogue.py \
  --staging ../skyward-data-staging/tevcat-20260916
.venv/bin/python -m pytest -o addopts= -q tests/test_tevcat_normalization.py
~~~

The bundled 2026-09-16 snapshot uses normalization version 4 and contains 361 sources and 4005 bibliographic records. It publishes structured catalogue values and short parameter excerpts with attribution, not complete site HTML or paper text. `notes.measurements` contains 1828 candidate facts with locally resolved reference links and a rendering check; this is **not independent verification of the paper measurements**. `notes.unverified_excerpts` contains 2262 excerpts, including 429 with unresolved mathematical rendering. These excerpts must not feed scientific calculations, automatic fitting or confirmed associations. All 361 hard footprints remain unknown. The 186 positional 2LHAASO candidate edges remain `candidate_only`; there are no verified associations and no copied physical parameters.

在中间目录验证通过后，用以上命令重建应用快照。附带快照是规范化 v4 的**候选事实快照**，不是最终权威测量集。仅发布结构化数值、带来源的短参数摘录和书目信息，不发布完整网页或论文正文。1828 条候选事实通过局部引用解析和表达式检查，但不等于逐项核验论文数值；2262 条未核验摘录中有 429 条数学表达式渲染未核验，均不得用于科学计算、自动拟合或正式关联。361 个源的硬边界均未知；186 条与 2LHAASO 的位置候选不能升级为已确认关联，也不复制物理参数。

## Public endpoints / 公开入口

- Site: https://tevcat2.tevcat.org/
- Catalogue groups: /api/catalogs
- Source listing: /api/sources
- Source detail: /api/sources/<official-id>
- Main source bibliography: /api/sources/<official-id>/citations
- Parameter-specific references: /api/citations/<citation-id>
- Type and instrument lookup: /api/sourcetypes and /api/observatories

Endpoints were located in the site's own public frontend. No login, private editor data, or access-control bypass is used. Main bibliographies do not always include references attached to individual position, morphology, flux or distance fields; these must be fetched separately. Null/empty reference identifiers are upstream missing values, not resolvable citations.

接口来自官网公开前端，不使用登录、私有编辑器数据或访问控制绕过。主文献列表不一定包含位置、形态、通量和距离字段附带的引用，必须单独补采。null/空引用是上游缺失值，不能伪造文献。

## Scientific safeguards / 科学边界

- Preserve all four categories: Default Catalog, Newly Announced, Source Candidates and Other Sources; do not call every record a confirmed source.
- Keep original source IDs, coordinate authority, epoch, units, discovery instrument and subsequent instruments distinct.
- Do not turn unspecified distance, uncertainty or flux into zero. Some upstream numeric zeros are placeholders.
- Do not equate morphology containment scales, Gaussian widths or position errors with a physical hard boundary.
- Preserve multiple measurements and their citations; do not interpret Crab fractions without the stated energy threshold and reference spectrum.
- A textual mention or positional neighbour does not establish a 2LHAASO association.

保留四种官网分类、稳定源 ID、原始坐标依据、历元及单位；发现设备与后续观测设备分开。缺失距离、误差和通量不能补零；形态包容尺度、高斯宽度、位置误差不能当成完整源硬边界。多测量及对应引用均应保留，Crab 比例须结合能阈与参考谱解释。文本提及或位置邻近不能直接建立 2LHAASO 关联。

## Provenance and completion / 来源与完成判定

Every saved public payload records its endpoint, retrieval time, original-response SHA-256 and sanitized-payload SHA-256. Private fields are excluded. Resumed checkpoints are revalidated against the current whitelist and schema. The collector is serial, bounded, rate-limited and retried only a finite number of times.

每个公开载荷记录接口、采集时间、原响应及脱敏载荷 SHA-256；排除私有字段，恢复时重新验证白名单、结构和哈希。采集为串行、有界、限速及有限重试。

Only a matching independently checked total, an unchanged final source listing, successful detail/bibliography fetches and resolved parameter-reference IDs permit acquisition completion. The audit separately reports field presence, missing science information and verified retrieval coverage. The display cutoff date is the actual completion date in Asia/Shanghai, not a claim that every source was updated that day.

只有独立核对的数量匹配、采集前后列表一致、详情/文献抓取成功且参数引用无悬空时，才标记采集完整。审计分开报告字段存在、科学信息缺失及抓取覆盖。源表截止日期取上海时区实际完成采集之日，不代表所有条目当天更新。

Attribution requested by the official About page: **Wakely, S. P. & Horan, D. (2008), “TeVCat: An online catalog for Very High Energy Gamma-Ray Astronomy”, ICRC 3, 1341–1344**, ADS bibcode **2008ICRC....3.1341W**. Site contents retain their original authorship. No separate redistribution licence was established by this acquisition; review publication scope before GitHub delivery.

官网 About 页面要求引用以上论文。数据和说明保留原作者署名；本次采集没有确认单独的数据再分发许可证，GitHub 发布前须审查范围，不将取得公开访问权限等同于任意转载授权。
