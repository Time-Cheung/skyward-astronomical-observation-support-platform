# Skyward 运维与离线部署说明

Skyward 提供黑、白和品牌蓝 `#3333FF` 的本地界面，并可由浏览器主页面切换中文/English 与自动/亮色/暗色主题。所有静态资源均从本机提供，不使用 CDN、在线字体或在线翻译服务。

- 完整中文使用与 Conda 部署手册：[`zh/使用与部署手册.md`](zh/使用与部署手册.md)
- Complete English user and Conda deployment guide: [`en/user-and-deployment-guide.md`](en/user-and-deployment-guide.md)

## Conda 快速部署

推荐使用独立的 Conda/Miniforge 环境，避免影响服务器的全局 Python、ROOT 或其他科学软件：

```bash
cd /home/lact/wz/lact-window-planner
source ~/miniforge3/etc/profile.d/conda.sh
mamba create -y -n skyward python=3.9 pip
conda activate skyward
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

若服务器没有 `mamba`，将该命令替换为 `conda create`。离线 wheelhouse、systemd 中 Conda 绝对路径配置和故障排查请使用上方完整手册。

## 启动前检查

```bash
cd /home/lact/wz/lact-window-planner
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q app
.venv/bin/python -c 'from app.main import app; print(app.title)'
```

确认：

- `data/2LHAASO.txt` 存在且 SHA-256 与 README 记录一致；
- `data/iers/finals2000A.all` 存在并覆盖计划计算日期；
- 服务端口只对批准的局域网开放；
- 未设置公网端口转发；
- 不需要任何外部网络资源、CDN 或运行时 TeVCat 请求。

## 手工烟雾测试

```bash
MPLCONFIGDIR=/tmp/lact-matplotlib \
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开终端：

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:8000/api/v1/config
curl -fsS 'http://127.0.0.1:8000/api/v1/sources?q=Geminga'
```

浏览器检查 `/`、`/about`、`/api/v1`，再提交一个窗口计算。点击全天图中的源星标，确认弹窗中的 index、名称和坐标与 API 一致。

## systemd 安装

unit 文件中的 `User=lact`、`Group=lact` 和项目路径是当前机器的默认值。若部署用户不同，先修改 unit 文件，再安装：

```bash
sudo install -d -o lact -g lact /var/cache/lact-window-planner/matplotlib
sudo install -m 0644 deploy/lact-window-planner.service /etc/systemd/system/lact-window-planner.service
sudo systemctl daemon-reload
sudo systemctl enable --now lact-window-planner.service
```

验证：

```bash
systemctl is-active lact-window-planner.service
curl -fsS http://127.0.0.1:8000/api/v1/health
journalctl -u lact-window-planner.service -n 100 --no-pager
```

## 网络边界

这是无认证的内网原型。应用自身不识别用户身份，也不提供授权隔离。访问控制由主机防火墙或网络隔离提供。请在正式投入使用前由网络管理员确认允许的源网段，并定期检查端口暴露情况：

```bash
ss -ltnp | grep ':8000'
```

## 维护 IERS 文件

在可联网的维护环境下载官方 `finals2000A.all`，通过受控介质放入 `data/iers/`，然后运行：

```bash
.venv/bin/python - <<'PY'
from astropy.time import Time
from astropy.utils import iers
path = "data/iers/finals2000A.all"
table = iers.IERS_A.open(path)
print("rows:", len(table))
print("range:", table["MJD"][0].value, table["MJD"][-1].value)
print("last:", Time(table["MJD"][-1].value, format="mjd").iso)
PY
.venv/bin/python -m pytest
```

更新完成后重启服务。若计划日期超过表格范围，健康检查应标记为 degraded，具体计算接口会拒绝该时间段并返回 422；不要在隔离环境中打开自动下载。
