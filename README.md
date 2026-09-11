# Skyward | 天文观测辅助平台

[English guide](docs/en/user-and-deployment-guide.md) | [中文手册](docs/zh/使用与部署手册.md)

Skyward 是一个 Python-first、只读、无账号的局域网 FastAPI 原型，面向可扩展的天文观测辅助场景。当前已完成 LACT/LHAASO 站点适配，载入 `data/2LHAASO.txt` 的 190 个源，计算目标、太阳和月亮的几何位置，并根据可选约束生成中心窗口和完整 extension 窗口。

> 结果只表示几何候选窗口，不是正式观测批准。当前版本仅供受控局域网访问；天气、实时设备状态、机械限位、跟踪误差、实际灵敏度和联合观测条件均未评估。

## 显示与语言

Skyward 使用黑、白与品牌蓝 `#3333FF` 的仪器化视觉系统；绿色、黄色和红色只保留给源状态。主页面顶部右侧支持：

- **语言**：中文 / English；
- **主题**：自动 / 亮色 / 暗色；
- **时区**：默认北京 `UTC+8`，可切换 UTC；所有网页日期、时钟、窗口表和后续生成的图表统一按所选时区显示；
- **全新暂态目标**：默认“添加新目标”，填写 RA、Dec、半径；名称空白时生成 `TMP JHHMM±DDMM`，不写入 2LHAASO 源表；
- **观测计划 TXT**：完整源窗口可加入本地计划并下载，不在服务器存储；

设置保存在每台客户端浏览器的 `localStorage`，不在服务端持久化、不需要账号；计算时为生成对应 SVG 图表会随该次请求传递显示设置。完整操作说明见中英双语手册。

## 已实现范围

- 站点：`100°01′36″ E`、`29°21′27″ N`、海拔 `4410 m`；
- 当前 LACT 适配：FoV 直径 `8.3°`、半径 `4.15°`，理想圆形硬边界；
- 2LHAASO 源：190 条，RA/Dec 按 FK5 J2000 处理；源名排序、检索和临时 CSV 源表导入；
- 可选参数：太阳最大高度、月亮最小角距、目标天顶角范围、最短连续窗口；
- GREEN/YELLOW/RED 当前几何状态；
- 当前 LACT 适配下的地平坐标全天图、固定天顶的实时 FoV 圆、小型橙色太阳/月亮图标、实时/指定时刻切换和可点击源标记；支持 AltAz/Horizon、J2000 赤道和银道显示坐标系；
- 选定源的 8.3°局部 FoV、extension 空心圆、附近源、太阳/月亮方向；Gaia DR3 定标星可按需在线查询并以星形叠加；
- 完整源窗口本地观测计划编辑与 TXT 下载（仅当窗口内存在两个有效整秒时提供）；
- 秒级候选扫描和亚秒边界细化；单次窗口请求最多 1 天；
- HTML 页面及 `/api/v1` JSON API；
- 多源表选择与叠加；
- IERS 在线优先、超时、用户缓存和项目内置文件回退；Gaia 查询失败时保留基础源表天图；

## 软件要求

- Linux；
- Python 3.9 或更新版本；
- 项目运行目录可读；
- 推荐至少 2 GB 内存。

当前已验证环境为 Python 3.9.21。依赖版本固定在 `requirements.txt`；特别是 Astropy 6.0.1 搭配 NumPy 1.26.4，避免系统级 NumPy 2.x 的兼容问题。

> 推荐按 [`docs/zh/使用与部署手册.md`](docs/zh/使用与部署手册.md) 或 [`docs/en/user-and-deployment-guide.md`](docs/en/user-and-deployment-guide.md) 中的 Conda 流程部署，以隔离服务器全局 Python、ROOT 和其他科学软件。

## 首次安装

```bash
cd /home/lact/wz/lact-window-planner
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

不应直接使用服务器全局 Python 环境。

## 直接启动

仅本机检查：

```bash
cd /home/lact/wz/lact-window-planner
MPLCONFIGDIR=/tmp/lact-matplotlib \
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

局域网访问（必须再用防火墙限制允许网段）：

```bash
cd /home/lact/wz/lact-window-planner
MPLCONFIGDIR=/tmp/lact-matplotlib \
  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

服务器当前内网地址若仍为 `10.2.101.152`，同网段浏览器访问：

```text
http://10.2.101.152:8000/
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## systemd 部署

1. 检查 `deploy/lact-window-planner.service` 的用户、组、目录和端口；
2. 由有管理员权限的人员复制并启用：

```bash
sudo cp deploy/lact-window-planner.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lact-window-planner.service
sudo systemctl status lact-window-planner.service
```

实时日志：

```bash
journalctl -u lact-window-planner.service -f
```

本次交付只提供 unit 文件，不擅自修改系统服务或防火墙。

## 局域网与防火墙边界

应用没有认证。**任何能连接服务端口的客户端都能访问全部页面和 API。** 必须由服务器防火墙或上游网络设备将端口限制到可信内网 CIDR，不要做公网端口映射，不要配置公网域名。

以 firewalld 为例（将网段替换为实际批准的管理网段）：

```bash
sudo firewall-cmd --permanent \
  --add-rich-rule='rule family="ipv4" source address="10.2.0.0/16" port protocol="tcp" port="8000" accept'
sudo firewall-cmd --reload
```

在网络管理人员确认前，不建议盲目执行示例规则。

## API

- `GET /api/v1/health`
- `GET /api/v1/config`
- `GET /api/v1/catalogues`、`POST /api/v1/catalogues/upload`
- `GET /api/v1/sources?q=&limit=&catalog_tokens=`
- `GET /api/v1/sources/{index}`
- `GET /api/v1/sky/current`（支持显示坐标系、Gaia 和多源表参数）
- `POST /api/v1/windows/calculate`
- API 参考页：`GET /api/v1`；
- OpenAPI schema：`GET /openapi.json`。

交互式 Swagger/ReDoc 页面默认禁用，以保证浏览器端不尝试加载外部 CDN。

计算时间必须落在随部署提供的 IERS 表覆盖范围内；超出范围的计算接口返回 422。

窗口请求示例：

```json
{
  "source_index": 11,
  "start_time": "2026-12-15T10:00:00Z",
  "end_time": "2026-12-16T10:00:00Z",
  "constraints": {
    "sun_max_altitude_deg": -18,
    "moon_min_separation_deg": 30,
    "target_min_zenith_deg": null,
    "target_max_zenith_deg": 50,
    "minimum_window_seconds": 1800
  }
}
```

无时区的 HTML `datetime-local` 输入按 `Asia/Shanghai` 解释；API 最好显式传 `Z` 或 UTC offset。

## 测试

```bash
cd /home/lact/wz/lact-window-planner
MPLCONFIGDIR=/tmp/lact-mpl-test .venv/bin/python -m pytest
```

测试覆盖：源表/哈希、站点和 FoV、J2000 坐标、Astropy 向量化一致性、中天高度、IERS 覆盖、约束 margin、GREEN/YELLOW/RED、秒级边界、跨 10 分钟批次边界的目录批量窗口一致性、最短窗口、完整源窗口的物理有效整秒计划端点、Crab 代表场景、HTML/API 契约。

## 后续发展方向

当前版本已完成 LACT 适配和几何观测窗口计算，但平台定位不局限于单一望远镜或单一源表。后续可在受控局域网边界内逐步接入：

- 其他望远镜的实时运行状态和指向/运行轨迹；
- 更多源表、天体实时位置与站点天气信息；
- 基于天气、天体位置、望远镜轨迹和设备约束的综合观测时段判断；
- 面向多设施的可解释观测窗口与联合观测支持。

这些项目均属于后续能力，不能与当前几何计算结果混同。

## 数据更新

### 2LHAASO 源表

应用启动时严格检查 190 行、表头、连续 index、唯一名称和数值范围。当前文件 SHA-256：

```text
83bbd6bf48c9f5d95b94db6495688471dfbe644d3047f39d4baf12dfcab69842
```

替换源表后必须同步测试和版本记录，不能静默改变字段语义。

### IERS

运行时优先使用联网刷新得到的用户缓存；网络请求有明确短超时，失败时回退到用户缓存或项目内置 `data/iers/finals2000A.all`，不会阻塞首屏。`/api/v1/health` 会报告来源、覆盖区间、缓存年龄、更新周期和最近错误。IERS-A 的未来部分是预测值。

### TeVCat / 补充字段

`data/source_enrichment.json` 仅接受本地、可追溯的数据。未核验字段必须保持 `null`/空列表和 `verification_status: "unverified"`，不得按相近名字推测或在服务运行时联网补全。

## 项目结构

```text
app/                 FastAPI、计算、状态、图形和模板
data/                源表、enrichment、离线 IERS
scripts/             维护脚本
tests/               自动化测试
deploy/              systemd 模板
docs/                运维说明
```
