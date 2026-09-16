# Skyward 离线部署补充 / Offline deployment supplement

## 专业人员最简操作 / Operator quick path

默认项目 `.venv`，已验证环境：**Python 3.9.21、NumPy 1.26.4、Astropy 6.0.1**，不改 `requirements.txt`，不混全局 NumPy 2.x。Python 3.9.21 用于复现已验证环境，不是唯一可部署补丁版本；其他兼容版本须保持依赖固定并在目标机完整测试。以下路径、用户名、IP、CIDR、服务名均为**需替换的示例**，不是当前机器信息。项目示例 `/opt/skyward`、部署用户/组 `skyward`、内网服务器 `192.168.50.10`、批准 CIDR `192.168.50.0/24`。

Only the server needs Python/dependencies and optional external access. Clients need only a browser and server connectivity. Choose A (loopback only) or B (trusted LAN); never expose this unauthenticated geometry-only prototype publicly.

```bash
# 在隔离服务器：管理员已提供 Python 3.9.21、项目数据和兼容 wheelhouse
# On the isolated server, after approved transfer of interpreter, project and wheels
cd /opt/skyward
/opt/python-3.9.21/bin/python3 -m venv .venv
.venv/bin/python -m pip install --no-index --find-links ./wheelhouse -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -c 'import sys,numpy,astropy; print(sys.version); assert numpy.__version__=="1.26.4"; assert astropy.__version__=="6.0.1"; print(sys.executable)'
mkdir -p .runtime/matplotlib .runtime/cache
export MPLCONFIGDIR="$PWD/.runtime/matplotlib" SKYWARD_CACHE_DIR="$PWD/.runtime/cache"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q
```

启动与常驻、A/B 独立排错验收请按完整手册：

- [中文：共同准备、A 仅本机、B 局域网](zh/使用与部署手册.md)
- [English: common preparation, A local, B LAN](en/user-and-deployment-guide.md)

This document is an operator procedure, not a record of service installation. No existing service or firewall was changed for this documentation update, and full deployment acceptance is not claimed.

## 新手详细教程 / Detailed preparation

### 1. 在批准的联网维护机准备 / Prepare on an approved connected maintenance host

维护机应与服务器的 Linux 架构、所选 Python（已验证 **3.9.21**）、ABI 和系统 wheel 兼容性一致；最好用同类机器/容器。wheelhouse 不包含 Python 解释器或操作系统共享库，须另外通过管理员提供。不要从不同平台随意复制 `.venv`。

Use matching architecture, chosen Python and operating-system wheel compatibility. Python 3.9.21 is the validated reproduction environment, not the only permitted patch version; retest alternatives with unchanged pins. The wheelhouse does not supply the interpreter or OS libraries. Do not copy a virtual environment blindly between platforms.

联网维护机先按双语完整手册的专业快速步骤，首次 `git clone REPOSITORY_URL /opt/skyward`（替换 URL/路径），或在备份/检查本地修改后仅对干净副本执行 `git pull --ff-only`；失败或存在修改就停止，不自动覆盖。隔离服务器不执行在线 clone/pull，而是接收下面的受控发布包。

On the connected maintenance host, follow the full guides' first-clone or clean-checkout fast-forward procedure. Preserve local edits and stop on failure. The isolated server receives the controlled release below instead of contacting a Git remote.

```bash
# Example maintenance checkout; replace this path and Python path
cd /opt/skyward
/opt/python-3.9.21/bin/python3 -m venv .venv-wheelbuild
.venv-wheelbuild/bin/python -m pip download --only-binary=:all: \
  -r requirements.txt -d wheelhouse
sha256sum requirements.txt wheelhouse/* > wheelhouse.sha256
```

若任一固定版本没有兼容 wheel，停止并在匹配环境准备/审核构建产物；不要放松固定版本、改 requirements 或安装全局 NumPy 来绕过错误。`pip download` 成功也不证明目标机能导入，必须在目标服务器安装验证。

If a compatible pinned wheel is unavailable, prepare reviewed build artifacts in a matching environment; do not loosen pins. Successful download alone is not target-host validation.

通过受控介质传输项目发布版本、wheelhouse、校验文件、所有随发布提供的源表与来源元数据、`data/iers/finals2000A.all`，以及需要保留的原始数据。记录来源、提交/版本、日期和哈希。不要传输个人缓存、密码、密钥或全局环境。

Transfer the release, wheels/checksums, shipped catalogues/provenance, bundled IERS and required raw data through controlled media. Record source, version, date and hashes; exclude secrets and unrelated personal caches.

### 2. 服务器校验、安装和测试 / Verify, install and test on the server

```bash
cd /opt/skyward
sha256sum -c wheelhouse.sha256
```

校验通过后执行本文开头全部命令。`--no-index` 防止 pip 请求在线索引；完整 pytest 仍需运行，保留输出与退出码。失败时不应直接安装生产服务。Conda 只能作为完整手册中说明的可选独立替代，离线 Conda 自身的 Python/环境安装包也需预先准备。

Run all quick-path commands after checksum verification. `--no-index` avoids online package-index access; retain the full pytest output and exit status. Do not deploy after failures. Conda is only an optional isolated alternative described in the full guides; provision its interpreter/environment artifacts separately for offline use.

### 3. 选择 A 或 B / Choose A or B

**A：仅本机 / Server-local**

```bash
cd /opt/skyward
export MPLCONFIGDIR="$PWD/.runtime/matplotlib" SKYWARD_CACHE_DIR="$PWD/.runtime/cache"
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# Second terminal on the SERVER
curl -fsS http://127.0.0.1:8000/api/v1/health
```

服务器本机浏览器 `http://127.0.0.1:8000/`；不开放 LAN 防火墙端口。常驻使用 `deploy/skyward-local.service`，按完整手册替换用户/路径并创建可写缓存后才安装。远端无法访问是 A 的预期结果。

Use a server-local browser; no LAN firewall opening. For persistence, review the local template and create writable caches as documented in the full guide. Remote failure is expected in A.

**B：受控 LAN / Controlled LAN**

先由管理员确认真实服务器内网 IP 与批准 CIDR，配置“受信源允许、其他拒绝”的防火墙和 VLAN ACL。仅加 accept 不会覆盖现有全网允许。不要关闭防火墙或开放所有网段。

First have the administrator confirm the real server LAN IP and trusted source CIDR, and restrict firewall/VLAN ACLs. An accept rule does not remove existing broad allowances.

```bash
cd /opt/skyward
export MPLCONFIGDIR="$PWD/.runtime/matplotlib" SKYWARD_CACHE_DIR="$PWD/.runtime/cache"
.venv/bin/python -m uvicorn app.main:app --host 192.168.50.10 --port 8000
# Server and approved client; replace with actual SERVER LAN IP
curl -fsS http://192.168.50.10:8000/api/v1/health
```

客户端浏览器 `http://192.168.50.10:8000/`，IP 必须替换。**不能用 `0.0.0.0` 或客户端 `127.0.0.1` 作为访问服务器地址。** 仅在防火墙验证后才可改成 `--host 0.0.0.0`，优先具体内网 IP。常驻使用 `deploy/skyward-lan.service`；A/B 不同时占用 8000。完整手册包含 B 的监听、服务器/客户端连通性、防火墙、VLAN 排错及未批准网络拒绝验收。

The client URL always uses the server's real LAN IP. `0.0.0.0` is a listener, not a destination; client loopback points to the client. Prefer a specific private IP, allowing wildcard binding only after firewall verification. Use the LAN service template and its separate acceptance procedure in the full guides.

## 离线能力、IERS 与健康 / Offline capabilities, IERS and health

网页静态资源由服务器提供，不依赖 CDN、在线字体或翻译服务。本地源表及 IERS 覆盖内的几何计算可以离线使用；Gaia 新查询不能保证离线可用。浏览器独立请求 `GET /api/v1/gaia` 并异步等待 HTTP 响应，**不是服务端 job 轮询**。参数含 `target_source_key`、`map_kind=current|local-fov`、`radius_deg/limit/max_mag`；成功返回 `sources/overlay_svg/gaia` 和 `count/drawn_count/cached/error/zero/limit/truncated`。错误响应可为 HTTP 200、`status="error"` 且省略叠加字段；不可把错误当成功零行。缓存为进程内缓存，不能承诺离线或重启后命中。Gaia 默认 **5° / 500 行 / G≤18**，不使用 `ORDER BY`；`selection=bounded_unordered_subset` 是有界无序子集，**不是最亮 N 或代表性抽样**。独立查询配置为 **20 秒**有限超时，不是所有环境下 HTTP 总耗时的硬保证；上限仍为 **2 并发 / 2 MiB 响应 / 32 个缓存查询**。

Static assets are server-local. Bundled catalogues and geometry within IERS coverage can run offline; new Gaia queries cannot be promised offline. Gaia provides candidates, not certified standards. The browser asynchronously awaits **`GET /api/v1/gaia`**, not a server job/polling protocol. Check the fields above and distinguish browser pending, cache, failure and successful zero rows; HTTP 200 alone is insufficient. Error responses may omit overlay fields. Process-local cache is not guaranteed offline or after restart; see the bilingual guides for the exact contract. Defaults remain **5° / 500 rows / G≤18**. Without `ORDER BY`, `selection=bounded_unordered_subset` is **neither the brightest N nor a representative sample**. The independent query uses a **20-second** finite timeout, not a universal hard bound on total HTTP latency; limits remain **2 concurrent queries / 2 MiB response / 32 cached queries**.

- `iers.source_kind=bundled`：活动回退表；`online_cache`：在线缓存，可能是旧下载，**不代表本次联网成功**。检查 `last_attempt`、`last_success`、`last_error`。
- `status=ok` 仅表示当前时刻覆盖，不保证规划日期覆盖，也不表示全部功能通过。核对 `first_mjd/last_mjd`、`covers_current_time`、预测标志和活动 `source`。
- 实现是在启动时选表并启动后台刷新；7 天新鲜度不是长期运行的定时刷新承诺。
- Astropy `auto_download=False` 不禁止应用自身的启动外联尝试。严格隔离由主机/上游出站策略控制；不要虚构不存在的“离线环境开关”。失败保留活动表并记录错误。

The same distinctions apply in English: cached data is not evidence of a successful network request in this process; inspect timestamps/errors and active coverage. Startup refresh is not a weekly scheduler. Astropy's auto-download flag does not disable Skyward's own network attempt. Enforce approved egress policy; no undocumented offline switch is assumed.

IERS-A 未来段可能是预测值，超覆盖计算可返回 422。受控更新见双语手册：先核验官方文件、哈希、解析、覆盖和完整 pytest，再按实际服务名重启并核对活动来源；新鲜缓存可能优先于刚替换的 bundled 文件。

## 已接入数据与验收 / Integrated data and acceptance

已接入 / integrated：2LHAASO **190**，FL16Y **7224**，3FHL **1556**，TeVCat **361**，cutoff **2026-09-16**，stable ID **`tevcat`**。TeVCat 包括候选分组，**不是全部 confirmed**。备注保留 units/provenance、引用、核验状态和未知 footprint；未知不等于物理半径为零。`unverified_excerpts` 不是测量，与 2LHAASO **0 verified、186 候选**，不复制参数。**1000× 只缩放显示，不提高物理分辨率。** 观测计划导出 **ZIP（TXT + 选配 SVG）**。当前适配 LACT、geometry-only、无账号，不评估天气/设备/联合观测批准。

发布前执行完整 pytest、浏览器功能、源表数量与语义、Gaia 正常/零行/缓存/失败，以及所选 A/B 网络隔离验收。当前待最终发布审查，本文未声称已部署、已推送或全部验收通过。升级/回滚按完整手册，使用 `git pull --ff-only`、固定版本核对和真实安装的示例服务名 `skyward-local.service` 或 `skyward-lan.service`（名称不同需替换）；升级后硬刷新浏览器静态资源。

Final release review remains pending; deployment, push and full acceptance are not claimed. TeVCat excerpts are not measurements; 0 verified/186 candidate associations must not be used to copy parameters into 2LHAASO. Plan exports are ZIP files containing TXT and optional SVG. Follow the full guides for fast-forward-only upgrades, pinned dependencies, complete rollback and service-specific restarts. Hard-refresh client assets after updates. No service installation or firewall change was performed by this documentation work.
