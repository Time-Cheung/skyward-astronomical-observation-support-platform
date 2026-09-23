# Skyward IT 部署手册（中文）

[English](DEPLOYMENT.en.md) · [用户手册](README.zh-CN.md) · [开发文档](DEVELOPMENT.zh-CN.md)

## 1. 安全边界与发布物

当前 V0 没有账号、租户隔离或授权，禁止直接暴露公网。优先只监听回环地址；局域网部署必须由管理员限制可信源 CIDR，并验证未批准网络不可连接。只有服务器安装 Python 依赖，客户端只需要浏览器。

以下 /opt/skyward、skyward 用户、192.168.50.10、192.168.50.0/24 和端口 8000 都是需替换示例。已验证基线为 Python 3.9.x、NumPy 1.26.4、Astropy 6.0.1；以 requirements.txt 为准。发布内容必须包含代码、data、deploy、docs、scripts、tests、依赖清单和 provenance。

正式源码包只在用户明确发布新版本后生成，命名为 skyward-v<主版本.小版本>.zip。例如完整版本 1.6.20260919 对应 skyward-v1.6.zip。文件名不含日期，但包内记录完整版本、日期、Git 状态、清单和哈希。本次正式发布的完整版本为 2.1.20260924，源码包为 skyward-v2.1.zip。

## 2. 安装与门禁

~~~bash
cd /opt/skyward
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -c 'import sys,numpy,astropy; print(sys.version); print(numpy.__version__,astropy.__version__)'
mkdir -p .runtime/matplotlib .runtime/cache
export MPLCONFIGDIR="$PWD/.runtime/matplotlib"
export SKYWARD_CACHE_DIR="$PWD/.runtime/cache"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q
node --check app/static/app.js
git diff --check
~~~

任一命令失败都停止部署。不要混入全局 NumPy 2.x，也不要使用 sudo pip。

## 3. 本机与受控 LAN

推荐本机模式：

~~~bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:8000/api/v1/config
ss -ltnp | grep ':8000'
~~~

LAN 模式先由管理员确认真实服务器 IP、接口、可信客户端 CIDR、VLAN/ACL 和防火墙系统，再只允许批准网段访问 TCP 8000。优先绑定具体内网 IP：

~~~bash
.venv/bin/python -m uvicorn app.main:app --host 192.168.50.10 --port 8000
~~~

客户端访问服务器真实地址，例如 http://192.168.50.10:8000/。0.0.0.0 是监听地址，不是浏览器地址；客户端 127.0.0.1 也不是服务器。不得以关闭防火墙排错。

## 4. systemd

审阅并二选一：deploy/skyward-local.service 或 deploy/skyward-lan.service。替换用户、组、工作目录、Python 绝对路径、缓存目录和 LAN IP；不要让两套 unit 抢同一端口。

~~~bash
sudo install -d -o skyward -g skyward -m 0750 /var/cache/skyward
sudo install -d -o skyward -g skyward -m 0750 /var/cache/skyward/matplotlib /var/cache/skyward/data
sudo install -m 0644 deploy/skyward-local.service /etc/systemd/system/skyward.service
sudo systemctl daemon-reload
sudo systemctl enable --now skyward.service
systemctl status skyward.service --no-pager
journalctl -u skyward.service -n 100 --no-pager
curl -fsS http://127.0.0.1:8000/api/v1/health
~~~

## 5. 离线与出站策略

在与目标架构/Python ABI 匹配的联网维护机准备 wheelhouse：

~~~bash
python3 -m venv .venv-wheelbuild
.venv-wheelbuild/bin/python -m pip download --only-binary=:all: -r requirements.txt -d wheelhouse
sha256sum requirements.txt wheelhouse/* > wheelhouse.sha256
~~~

通过受控介质传输发布物、wheelhouse、哈希、数据和来源信息。目标机先执行 sha256sum -c wheelhouse.sha256，再用 pip install --no-index --find-links ./wheelhouse -r requirements.txt。不要跨平台复制 .venv。

静态资源、本地目录及 IERS 覆盖内几何可离线运行。新 Gaia 查询需要批准的服务器 DNS/TLS 出站，网页只在结果页局部图调用。Gaia 默认半径 1°、10 行、G≤10，可配置为半径 0.1–5°、1–500 行、G≤5–22；上限为 2 并发、2 MiB 响应和 32 个精确参数进程缓存查询。默认及更小查询使用 30 秒同步 TAP；任一参数超过默认值的大查询先查缓存，未命中则使用总预算 30 秒的异步 TAP。同步超时后最多尝试五个半径为原查询一半的有界子锥，总预算 50 秒；同步超时降级结果仍可能不完整，但在返回前按目标角距离排序。错误不能当作成功零行。

IERS 启动时选择新鲜缓存或 bundled 表并尝试有界后台更新。auto_download=False 不禁止应用自己的启动刷新；7 天是缓存新鲜度，不是定时器。检查健康 JSON 的 source_kind、first_mjd/last_mjd、covers_current_time、last_attempt、last_success 和 last_error。超覆盖规划可返回 422。

## 6. 功能与网络验收

- /api/v1/health 的 IERS 覆盖可接受；不能只看 HTTP 200。
- /api/v1/catalogues 是当前已安装源表标识和记录数的唯一来源；Gaia 的 selection_scope 为 result_local_fov_only。
- 首页和结果全天图没有 Gaia 选项、图层、图例或 current Gaia 请求。
- 结果局部图显示直径 10° 和独立 8.3° LACT 虚线 FoV；全天图与局部图共享实时/观测窗口/指定时间和紫色跟踪轮廓。当前无可信实时指向，因此状态计算不使用当前 FoV 约束。
- 启用 Gaia 按界面筛选条件发送 local-fov 查询（默认 1°、G≤10、10 颗；超过上限时按目标角距离选择最近源），Gaia 候选按共享状态以加粗红/绿色十字绘制，状态区显示红绿数量，普通源保持；关闭只移除 Gaia。
- 完成短窗口计算，检查地图、曲线状态和多个完整源窗口；每个可用窗口应有默认勾选框，窗口列表底部只应出现一组“加入观测计划”“预览当前观测计划”“下载观测计划”按钮。取消一个窗口后加入，预览应显示同一条计划中的其余窗口；每个窗口的备选源筛选状态应独立显示。ZIP 应含可由办公软件打开的 XLSX：表头为实心黑色，每个目标窗口一行黄色目标行，其后为绿色备选源行；勾选图像时每条计划应含局部视场与观测窗口两张 SVG。
- 在结果页切换模式、缩放、Gaia 和曲线后进入数据说明/API，再点击“天区与规划”；应直接恢复当前 DOM，不应产生窗口计算或两张地图请求。结果页当前目标源详情不应显示“填入观测规划”，其他普通源详情应保留该操作。
- LAN 模式从批准和未批准网络分别验证，并确认无公网转发。

## 7. 升级与回滚

不要覆盖脏的生产副本。优先在独立候选目录构建和测试；原地更新只允许干净副本 git pull --ff-only。记录当前提交、unit、依赖、数据哈希和可恢复备份。所有门禁通过后，才在授权维护窗口重启实际服务，并让客户端 Ctrl+Shift+R。

回滚须成套恢复代码、数据、固定依赖、unit 和来源。Git 不恢复未跟踪数据、缓存或 .venv；不要用破坏性清理销毁修改。恢复后重新执行 pip check、完整 pytest、健康检查和网络验收。

## 版权与开发者

Copyright © 2026 Wei Zhang. 版权所有，保留所有权利。

开发者：**张炜（Wei Zhang）**，中国科学院高能物理研究所（IHEP-CAS）博士后研究员。机构信息仅用于身份说明，不表示机构对本软件拥有版权或作出背书。
