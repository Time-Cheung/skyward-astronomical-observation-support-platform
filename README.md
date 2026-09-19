# Skyward | 天文观测辅助平台

[中文完整手册](docs/zh/使用与部署手册.md) · [English guide](docs/en/user-and-deployment-guide.md) · [离线安装 / Offline](docs/offline-deployment.md)

## 专业人员最简操作 / Operator quick start

默认使用项目 **`.venv`**，已验证环境为 Linux + **Python 3.9.21、NumPy 1.26.4、Astropy 6.0.1**。下方解释器路径用于复现已验证环境，不表示 Python 3.9.21 是唯一可部署补丁版本；其他兼容版本需在保留固定依赖的前提下重新运行完整测试。固定依赖以未改动的 `requirements.txt` 为准；不要混入全局 NumPy 2.x。Conda 仅作为完整手册中的可选替代。

**以下所有路径、用户、IP、CIDR、服务名均为需要替换的示例，不是当前机器信息。** 示例项目 `/opt/skyward`、用户/组 `skyward`、Python `/opt/python-3.9.21/bin/python3`、服务器 IP `192.168.50.10`、批准网段 `192.168.50.0/24`。Only the server installs dependencies and needs optional IERS/Gaia egress; clients need only a browser and access to the server.

先获取代码，以下二选一。`REPOSITORY_URL` 必须替换为维护者确认的仓库地址；目标父目录需由管理员授权部署用户写入。已有生产副本的更新应在维护窗口按完整手册进行，优先独立候选目录；**先备份本地修改，有修改就停止，不自动 stash、reset 或覆盖**。

First acquire the checkout; choose one branch below. Replace `REPOSITORY_URL` with the maintainer-approved URL. Preserve local changes, and use the maintenance procedure for an existing production checkout.

```bash
# 首次获取 / First checkout (destination must not already exist)
git clone REPOSITORY_URL /opt/skyward
```

```bash
# 已有副本 / Existing checkout: inspect before updating
cd /opt/skyward
git status --short
# 有输出就停止并先备份/人工处理；仅干净副本允许快进
# Stop and preserve edits if status is nonempty; do not merge divergent history
if [ -z "$(git status --porcelain)" ]; then git pull --ff-only; else echo 'STOP: preserve local changes first'; fi
```

仅获取/更新成功后继续；离线服务器改用受控传输的版本包。Continue only after success; use an approved transferred release on an offline server.

```bash
# 共同准备 / Common preparation: on the server, as project owner
cd /opt/skyward
/opt/python-3.9.21/bin/python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -c 'import sys,numpy,astropy; print(sys.version); assert numpy.__version__=="1.26.4"; assert astropy.__version__=="6.0.1"; print(sys.executable)'
mkdir -p .runtime/matplotlib .runtime/cache
export MPLCONFIGDIR="$PWD/.runtime/matplotlib" SKYWARD_CACHE_DIR="$PWD/.runtime/cache"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q
```

选择以下一条，不同时运行 / Choose one:

**A — 仅服务器本机 / Server-local only**

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# 第二个服务器终端 / Second server terminal
curl -fsS http://127.0.0.1:8000/api/v1/health
```

仅服务器本机浏览器访问 `http://127.0.0.1:8000/`，不开放 LAN 防火墙端口。Service template: [`deploy/skyward-local.service`](deploy/skyward-local.service).

**B — 受控局域网 / Controlled LAN**

先确认真实服务器内网 IP，按完整手册配置**只允许受信 CIDR、拒绝其他来源**的防火墙，再运行：

```bash
.venv/bin/python -m uvicorn app.main:app --host 192.168.50.10 --port 8000
# 服务器和授权客户端 / Server and authorized client
curl -fsS http://192.168.50.10:8000/api/v1/health
```

客户端浏览器使用 `http://192.168.50.10:8000/`，替换为**服务器真实内网 IP**，不能用 `0.0.0.0` 或客户端的 `127.0.0.1`。优先具体内网 IP；只有可信网段防火墙已验证时，监听才可选 `0.0.0.0`。Service template: [`deploy/skyward-lan.service`](deploy/skyward-lan.service).

完整手册各含共同准备、独立完整 A/B 手工和 systemd 流程、监听/防火墙/VLAN 排错及验收。先手工验证，再由管理员审阅模板并安装；**本次文档修改没有安装服务、修改防火墙或改变现有部署**。旧 `deploy/lact-window-planner.service` 模板默认已改为 `127.0.0.1`，不是对已安装服务的修改。

## 安全与科学边界 / Boundaries

Skyward 是无账号、无授权隔离的天文观测辅助原型。**不允许公网暴露、全网放行或端口映射。** 能连接端口的客户端可访问全部页面/API；仅绑定私有 IP 不能替代防火墙。

当前适配 LACT/LHAASO 站点（东经 `100.0266666667°`、北纬 `29.3575°`、海拔 `4410 m`），理想圆形 FoV 直径 `8.3°`，遥测接入前固定天顶参考。结果是 **geometry-only 几何候选**，未评估天气、实时设备状态、机械限位、跟踪误差、真实灵敏度和联合观测条件，不能作为正式观测批准。

## 已实现功能 / Implemented features

以下源表已实际接入，应用测试及浏览器验收结果见 [升级验收记录 / Acceptance record](docs/upgrade-acceptance-20260916.md)。该记录不代表生产安装或实际局域网隔离已验收：

| Catalogue | Records | Snapshot / caveat |
|---|---:|---|
| 2LHAASO | 190 | Preserve original field semantics |
| FL16Y | 7224 | Verify units and provenance |
| 3FHL | 1556 | Do not equate positional error with physical extension |
| TeVCat (`tevcat`) | 363 | Public `www.tevcat.org` snapshot **as of 2026-09-19**; four public catalogue groups; reported fields are not independently verified planning footprints |

- 源表备注保留 units/provenance、核验状态、版本/引用和缺失信息；未知 footprint/extension 不得假装为测量为零或已完整容纳。TeVCat 快照仅保留最小化公开结构化事实，不保存私有字段、原始网页备注或论文文本；当前全表 footprint 未知，与 2LHAASO 的近邻只作为候选，不复制参数或把近邻当同一天体。采集依据见 [TeVCat 说明](docs/tevcat-acquisition.md)。
- Gaia DR3 是**候选定标星**；浏览器独立请求 `GET /api/v1/gaia` 并异步等待 HTTP 响应，**不是服务端 job 轮询**。参数含 `target_source_key`、`map_kind=current|local-fov`、`radius_deg/limit/max_mag`；成功返回 `sources/overlay_svg/gaia` 及 `count/drawn_count/cached/error/zero/limit/truncated`。错误可能仍为 HTTP 200，需检查顶层 `status/error`；详情及缺省字段处理见完整手册。默认 **5° / 500 行 / G≤18** 不变；查询无 `ORDER BY`，`selection=bounded_unordered_subset`，**不是最亮 N 颗，也不是代表性抽样**。独立 Gaia 查询配置为 **20 秒**有限超时（不保证整条 HTTP 请求严格在 20 秒内结束），上限为 2 并发、2 MiB 响应、32 个进程缓存查询。
- 已支持 **1000× 缩放**，它不增加物理分辨率、角分辨率或定位精度，只是显示放大。
- 网页支持中/英、自动/亮/暗主题、北京 UTC+8/UTC、坐标显示切换、临时目标和本地观测计划；下载 **ZIP 内含 TXT + 选配 SVG**。设置/计划位于客户端浏览器，不是服务端账号数据。
- 单次窗口最多 30×24 小时，逐秒候选扫描与已发现边界细化不保证发现所有亚秒窗口；长范围仅下采样展示数据，窗口判定仍逐秒进行。完整源计划需至少两个几何复核有效整秒；未知 footprint 不能据此声称完整源通过。

## 健康、离线与验收 / Health and acceptance

`/api/v1/health` 的 HTTP 200 不代表部署、科学计算或在线查询全部正常。读取 JSON 的 `status` 与 IERS 覆盖；`source_kind=bundled` 表示活动回退表，`online_cache` 可能来自旧缓存，**不证明本次联网成功**，还要看 `last_attempt`、`last_success`、`last_error`。

`app/astronomy.py` 在启动时选择新鲜缓存或 bundled，并启动后台刷新。配置的 7 天是新鲜度/到期指标，**不是保证每周执行的定时任务**。`auto_download=False` 只关闭 Astropy 隐式下载，应用自己的启动刷新仍会尝试外联。严格离线由服务器出站策略控制；本地源表与覆盖内几何可用，新 Gaia 查询不能保证可用。IERS-A 未来部分是预测值，当前健康不代表任意未来日期覆盖。

发布前必须运行上方**完整 pytest**，并分别做 A/B 连通性/隔离验收、源表数量与 provenance/候选分组检查、Gaia 各状态、浏览器及窗口/ZIP 计划验收。这里仅提供命令和清单，不声明本次已完成全部验收。

升级使用 `git pull --ff-only`，检查固定依赖、`pip check`、完整 pytest 后才重启**实际使用的示例服务名**（A `skyward-local.service`，B `skyward-lan.service`；安装名不同则替换）。回滚需代码、数据、依赖和 unit 一起恢复；详见完整手册。升级后客户端硬刷新静态资源（Ctrl+Shift+R）。

## API 与目录 / API and layout

API reference `/api/v1`；schema `/openapi.json`；常用 `/api/v1/config`、`/api/v1/catalogues`、`/api/v1/sources`、`/api/v1/sky/current`、`GET /api/v1/gaia`、`POST /api/v1/windows/calculate`。Swagger/ReDoc 默认关闭，网页静态资源不使用外部 CDN。API 时间请带 `Z` 或明确 offset，计算必须在活动 IERS 表覆盖内。

```text
app/       Application, geometry and UI
data/      Catalogues, provenance and bundled IERS
scripts/   Maintenance tools
tests/     Automated tests
deploy/    Reviewed-before-install systemd examples
docs/      Bilingual deployment, usage and acquisition documentation
```
