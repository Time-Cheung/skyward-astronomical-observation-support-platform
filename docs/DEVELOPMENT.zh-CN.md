# Skyward 开发文档（中文）

**当前版本：V2.2（2.2.20260924）。** 当前代码树包含浏览器共享的源表图标、批量目标列表、跟踪视场曲线、观测窗口排序和计划预览排序。

[English](DEVELOPMENT.en.md) · [用户手册](README.zh-CN.md) · [部署手册](DEPLOYMENT.zh-CN.md)

## 1. 架构与目录

- app/main.py：FastAPI 页面、JSON API、查询边界和错误契约。
- app/catalog.py、app/gaia.py：本地目录、临时上传和独立在线 Gaia。
- app/sky_map.py：球面投影、真实坐标网格、源符号、局部/全天 SVG。
- app/windows.py、app/constraints.py：几何约束、逐秒候选扫描、边界和窗口。
- app/static、app/templates：无外部 CDN 的双语前端。
- data：源表、provenance 和 bundled IERS；scripts：采集/规范化；tests：单元、API、契约及浏览器测试。

## CSV 用户上传契约与示例

用户 CSV 源表和专用备选源目录均为带表头的 UTF-8 CSV，必需列 `name,ra,dec`（接受别名 `source_name,ra_deg,dec_deg`），坐标为 J2000 度；可选列 `ext,ext_err,p_err(95%),l,b`，其中 `extension_deg` 可作 `ext` 别名。单文件最多 1,000 行、512 KiB；名称唯一且 1–80 字符；名称不得含控制字符，坐标有限且 RA∈[0,360)、Dec∈[-90,90]，扩展/不确定度非负。

## 2. 几何与显示契约

全天图采用真实 AltAz/J2000/Galactic 球面经纬线；默认经度 60°、纬度 30°，深缩放使用自适应稀疏步长。普通源为一个空心星形；透明 hit target 不得获得描边；已知 extension 用独立淡虚线。跟踪视场内源以紫色星形轮廓标记，不能加第二个空心圆。

所有局部图固定显示目标中心半径 5°（直径 10°），SVG 根暴露 data-display-radius-deg=5。望远镜硬 FoV 是独立几何，暴露 data-fov-radius-deg；LACT 默认半径 4.15°，蓝色虚线框相对图半径的比例为 4.15/5。自定义 FoV 超出显示边界时允许裁切。

普通目录状态：红=中心失败，黄=中心通过但 footprint 边缘失败，绿=中心与 footprint 通过。如果源表声明源可能扩展、但没有有效 extension 半径，可观测性明确采用零半径点源回退计算；原始事实仍保留为 `footprint_known=false`、`planning_radius_deg=null`，API、详情和窗口结果均返回 `point_source_fallback`，不能把该假设描述为真实扩展范围已验证。Gaia 是 ext=0 已知点源，使用红/绿色十字符号，不产生黄色或 extension。

## 3. 30 天窗口扫描

请求最长 30 天。科学发现仍基于每秒候选点，但按 600 秒有界块处理；相邻块共用并去重边界秒，跨块有效区间合并。采样状态变化后对有符号 margin 做边界细化。绘图序列限制为 12,001 点并有界下采样，不能反向改变窗口判定。

minimum_window_seconds=0 只表示不按持续时间过滤。含至少一个采样通过秒的短窗口可被发现；没有通过整秒的纯亚秒事件不保证发现。浏览器计划更严格，要求区间内至少两个经独立复核有效的整秒。

## 4. 前后端状态契约

源表勾选只修改草稿，确认后才改变 catalog_tokens、地图和首页目标源。取消、Esc、外部点击恢复已应用选择；结果目标始终使用稳定 source_key。

结果页全天图和局部图共享一个状态选择器：实时、已计算观测窗口或指定时间。指定时间可为时间点，也可为最长 24 小时的时间段；时间段采用 trajectory-style 分类，所有位置统一绘制在区间起点。局部图不再有独立 live/fixed 状态，并与全天图使用相同的源颜色、已选目标轮廓和跟踪视场轮廓；trajectory 模式必须向两个地图端点发送同一组 highlight_indexes。结果页源详情为只读，目标选择留在首页规划器；内部保留的一次性 pending map state 只用于兼容既有结果重建流程，不应影响首页新计算。当前没有可信实时指向，sky_snapshot 和所有结果地图均使用 enforce_current_pointing=false；FoV 圆与紫色“跟踪视场内源”只表达目标中心几何，不能描述设备实时指向。

结果页导航状态契约：离开结果页前由 `snapshotResultPage()` 保存当前完整 DOM（包括已渲染 SVG、模式/指定时间控件、Gaia overlay、相机缩放、Zenith-Time overlay 和状态文本）到版本化 `skyward.result-page-cache.v1` sessionStorage。数据说明/API 页的规划链接先验证同源 /result URL，再通过 `restoreCachedResultPage()` 写回快照并跳过 `initialiseResultMaps()` 的首次 refresh/refreshLocal；因此返回不触发窗口计算或地图请求。快照写入失败时不阻断导航，回退到原有 GET /result 重建；直接刷新和跨标签页不承诺无计算。结果页 source dialog 只对当前目标源隐藏 `dialog-use-source`；其他普通源仍可通过保留的结果表单替换目标，Gaia 源不提供该操作。局部图缩放控件位于局部标题行，窄屏通过媒体查询恢复换行。

局部 Gaia 加载按钮默认不执行查询。点击后保留普通局部图，再按共享模式参数独立叠加 data-gaia-layer；坐标、目标、望远镜和约束来自当前结果上下文。Gaia ext=0 状态与普通源使用同一几何时刻/时间段分类，但只输出红或绿；SVG 的 gaia-cross 必须以 currentColor 描边并由 status-red/status-green 强制覆盖主题色，接口同时返回每行 status 和 status_counts。再次加载时 abort 在途请求并只替换 Gaia overlay，不得删除普通 marker。代次号和 AbortController 防止旧响应覆盖新图。查询状态区分 pending、cache、success zero、truncated 和 error，并显示筛选条件、查询策略、返回/绘制数量、红绿计数及真实失败原因。默认或更小查询的同步请求超时时，最多尝试五个仍位于原圆锥内的半径减半子锥；结果按 source_id 本地裁切、去重，并明确标为可能不完整；最终仍按目标角距离排序。任一筛选参数超过默认值时使用异步 TAP，不进入同步子锥降级。

观测计划保持在版本化 sessionStorage 中，可跨多个结果页累计并预览。其隔离边界是“同源 + 浏览器会话 + 标签页”：不同电脑、浏览器、浏览器配置文件和独立隐私会话不共享；当前版本没有账号、租户或服务器端权限隔离，不能把 sessionStorage 当作账号级安全边界。计划不得写入服务器数据库，也不得改用 localStorage 扩大同一浏览器配置文件内的共享范围。

计划生命周期契约如下：刷新标签页、同一标签页从结果页进入数据说明/API再返回、浏览器前进和后退均必须保留计划；点击“清空当前观测计划”必须清空；关闭标签页或整个浏览器后重新打开按新会话处理并清空；清理网站数据和隐私模式会话结束时清空。实现不得使用 `beforeunload` 或 `pagehide` 主动清理，因为这些事件也会在刷新时触发。应用存储容器从 `skyward.observation-plan.v2` 升级到 `v3` 时不迁移旧计划。浏览器恢复上次会话或重新打开已关闭标签页可能恢复 sessionStorage，这是浏览器相关例外，不能由纯前端逻辑在所有浏览器中强制区分。

每个计划窗口分别异步调用 alternatives 接口；候选源先粗筛排序（窗口重叠降序、间隔升序、时长差升序、候选时长降序、稳定源键升序），再对 shortlist 精确验证，最多返回 3 个。用户上传的临时 CSV 仅作为候选源池，不改变目标源目录；未上传时使用当前已加载普通源表。当前页“完整源窗口”区域仅在请求期间显示“源 + 窗口序号”的筛选状态。计划条目以 `windows[]` 保存全部勾选窗口，每个窗口保存自己的计划起止时间、备选源、筛选状态、指标和警告。下载 ZIP 内的 `skyward-observing-plan.xlsx` 是浏览器本地生成的无宏 OOXML 工作簿：同一条计划可有多条目标行，每个所选窗口一行，随后是该窗口的绿色备选源行；表头为实心黑色、目标行为黄色。不得依赖 CDN。勾选图像时，每条计划分别捕获观测窗口 SVG 与导出增强后的局部视场 SVG，以三位计划序号命名，防止同名目标覆盖；局部图导出副本强制亮背景、目标编号 1 并附源名图例，窗口图由 Matplotlib 直接写入曲线图例。

## 5. 数据维护与 TeVCat

默认 1LHAASO 目录由 `scripts/build_1lhaaso_catalogue.py` 从公开论文 Table 2 的机器表生成：

~~~bash
.venv/bin/python scripts/build_1lhaaso_catalogue.py \
  --table /secure/input/table.csv \
  --output data/catalogues/1lhaaso.json
~~~

构建器要求审计过的输入 SHA-256，验证 90 个唯一源、180 个组件和字段模式，并记录论文 DOI、论文 PDF/机器表哈希、单位与 Astropy 版本。双组件源按有坐标组件中 TS 最高者选代表坐标；每个组件的原始字段、缺失值和上限都保存在 `notes.components`。`r39` 仅是二维高斯 39% containment radius：测得扩展的误差是 1σ 统计误差，点源上限为 95% 置信上限；不得写入 `planning_radius_deg` 或用作硬边界。Table 2 关联项只表示论文按位置搜索得到的初步已知 TeV 对应体，不是 Skyward 核验身份。机器表中 `N0=0` 且误差列有值的未探测分量按论文定义规范化为 upper limit。`1lhaaso` 是默认且唯一的 LHAASO 运行目录；`2lhaaso` 不得出现在 `BUILTIN_CATALOGUES`、页面选择器、API 示例、发布树或源码包中，临时上传也必须拒绝 2LHAASO 保留名。TeVCat 重建审计同时保留 1LHAASO 文本关联检查，并把任何 2LHAASO 文本列为发布失败。关于 2LHAASO 的文档文字只能用于解释“尚未公开、未随包提供”的发布边界。

Fermi 构建使用 scripts/build_fermi_catalogues.py，保留 FITS 字段、单位和版本；位置误差不是物理 extension；显示名去掉重复目录前缀。

TeVCat www 公共快照可复现流程：

~~~bash
.venv/bin/python scripts/fetch_tevcat_www.py --output /secure/staging/tevcat-www-YYYYMMDD
.venv/bin/python scripts/build_tevcat_www_catalogue.py --staging /secure/staging/tevcat-www-YYYYMMDD
.venv/bin/python scripts/validate_tevcat_www.py
~~~

抓取器在 TLS 证书校验下两次读取公开页，解析公开 dat；采集期间 ID 集合改变即停止。manifest 记录时间、快照日期、响应/载荷/ID 哈希、分组数和提取器版本；原始 HTML 不进入仓库。构建仅投影公开字段，删除 private、operator、ownership、token 等字段，不再分发长 HTML 备注或论文正文。

当前 363 条中，223 条明确 Extended: No 规范为 planning_radius_deg=0.0、footprint_known=true；140 条 Extended: Yes 但无可靠硬边界半径，保持 null/unknown。位置近邻只生成候选审计，不是 identity match，不复制参数。每次数据更新必须同步 provenance、哈希、数量和测试。

## 6. Gaia 与 IERS 维护

Gaia 边界：半径 0.1–5°，网页/API 端点最多 500 行、G 上限 5–22，局部默认 1°/10/G≤10，并按目标角距离升序截取最近 N 颗；2 并发、2 MiB 响应、32 个精确参数缓存项。默认或更小查询使用 30 秒同步 TAP；半径、行数或深度超过默认值的大查询先查缓存，未命中使用总预算 30 秒的异步 TAP。同步超时最多五个半径为原查询一半的有界子锥，总预算 50 秒。ADQL 使用按目标角距离的 ORDER BY，客户端再以 J2000 球面角距离排序，最终元数据声明 selection=nearest_by_angular_distance、ordering=angular_distance_asc。保留字段、单位和来源；逆视差距离不能写成精密距离，坐标系转换不能写成已传播自行。

IERS 启动选择新鲜缓存或 bundled 表，再有界后台刷新；失败保留活动表并记录错误。离线严格性由网络策略实现。更新 bundled 文件时保留旧文件和哈希，验证 Astropy 解析、覆盖与完整测试；注意新鲜缓存可优先于刚替换的 bundled 文件。

## 7. 测试矩阵

~~~bash
.venv/bin/python -m compileall -q app tests
node --check app/static/app.js
.venv/bin/python -m pytest -p no:cacheprovider -q
git diff --check
~~~

真实 Chromium 还应覆盖：源表草稿/确认/空选择、全天无 Gaia 请求、局部 Gaia 加载按钮和 1°/10/10 默认筛选、自定义筛选、普通源保留、取消/陈旧响应、三坐标、固定/实时、主题/语言、375 px 无溢出。数据测试覆盖 1LHAASO 90/180 数量、代表坐标、单位、上限、未知 footprint、2LHAASO 不可服务，TeVCat 点源/未知 footprint、Gaia 字段和 30 天块边界。浏览器工具不加入生产依赖。

## 8. 版本与发布

完整版本格式为 主版本.小版本.YYYYMMDD。主版本表示架构代际，小版本按功能里程碑递增，日期是里程碑确认日期。

- 1.1.20260901：初始窗口规划器、可扩展望远镜范围和仅几何边界。
- 1.2.20260911：源表 overlay 与多坐标显示。
- 1.3.20260916：多源表、可靠 Gaia 查询和部署体系。
- 1.4.20260919：确认式源表交互、稀疏网格和数据说明。
- 1.5.20260919：TeVCat/Gaia/30 天规划升级。
- 1.6.20260919：长时间范围展示内存有界修复。
- **2.1.20260924**：Gaia 收窄为结果局部 FoV，固定 10° 局部图，共享地图状态与无计算页面恢复，可编辑多窗口观测计划和 XLSX/SVG 导出，专用备选源目录，Zenith-Time 并发刷新修复；默认目录替换为公开论文 Table 2 的 1LHAASO，并从当前发布树移除未公开 2LHAASO 文件；同步完成文档重构。
- **2.2.20260924**：包含 Gaia DR3 兼容性和文档修复、浏览器共享的源表图标、带继承约束和默认图像保存的批量目标列表、一次添加所有跟踪视场内源的 Zenith-Time 曲线、目标/曲线源观测窗口按起始时间排序，以及观测计划预览排序；首页不再重复显示版本横幅。

源码包的通用命名模式为 `skyward-v<主版本.小版本>.zip`。

## 版权与开发者

Copyright © 2026 Wei Zhang. 版权所有，保留所有权利。

开发者：**张炜（Wei Zhang）**，中国科学院高能物理研究所（IHEP-CAS）博士后研究员。机构信息仅用于身份说明，不表示机构对本软件拥有版权或作出背书。
