# Skyward 部署文档入口 / Deployment documentation

## 专业人员快速选择 / Operator routing

1. 先按完整手册首次 `git clone REPOSITORY_URL /opt/skyward`（地址/路径需替换），或检查并保留本地修改后对干净副本执行 `git pull --ff-only`；离线用受控版本包。在服务器创建项目 `.venv`，Python **3.9.21 为已验证版本**，不是唯一可部署补丁版本；其他兼容版本需重新验证。保持原 `requirements.txt` 固定依赖（NumPy **1.26.4**、Astropy **6.0.1**），执行完整 pytest。
2. **A 仅本机**：监听 `127.0.0.1`，仅服务器本机访问；模板 `deploy/skyward-local.service`。
3. **B 受控 LAN**：优先监听服务器真实内网 IP；仅在防火墙限制受信 CIDR 后才允许 `0.0.0.0`。客户端 URL 始终使用**服务器真实内网 IP**，不能用 `0.0.0.0` 或客户端回环；模板 `deploy/skyward-lan.service`。

All example paths, users, IPs, CIDRs and service names require replacement. No accounts; no public exposure. Only the server installs dependencies and needs optional external-service access. Documentation changes do not install services or change the existing deployment.

## 新手完整教程 / Complete beginner guides

两种语言均按“专业人员最简操作 → 新手共同准备 → 独立 A/B 完整部署与排错验收 → 使用 → 健康 → 升级回滚”排列：

- [中文使用与部署手册](zh/使用与部署手册.md)
- [English user and deployment guide](en/user-and-deployment-guide.md)
- [离线部署补充 / Offline supplement](offline-deployment.md)
- [开发者说明 / Developer notes](developer-notes.md)
- [TeVCat 采集依据 / TeVCat acquisition provenance](tevcat-acquisition.md)

## 本轮范围与验收状态 / Scope and acceptance

当前 LACT、geometry-only。已接入：2LHAASO **190**、FL16Y **7224**、3FHL **1556**、TeVCat **361**（cutoff **2026-09-16**，ID **`tevcat`**，含候选分组，不是全部 confirmed）。保留 units/provenance 与未知 footprint；TeVCat `unverified_excerpts` 不是测量，与 2LHAASO **0 verified、186 候选**，不向其复制参数。Gaia 通过 **`GET /api/v1/gaia`** 按需有限范围查询：浏览器异步等待 HTTP 响应，**不是服务端 job 轮询**；检查 `count/drawn_count/cached/error/zero/limit/truncated`，HTTP 200 不能替代业务状态。Gaia 默认 **5° / 500 行 / G≤18**，无 `ORDER BY`，`selection=bounded_unordered_subset`，不是最亮 N 或代表性抽样；独立查询采用 **20 秒**有限超时（非整条 HTTP 请求严格总耗时保证）。**1000× 仅显示缩放，不提高物理分辨率。** 观测计划下载为 **ZIP（TXT + 选配 SVG）**。

当前待最终发布审查；本指南未宣称已部署、已推送或全量测试/浏览器/网络/服务安装验收全部通过。IERS `online_cache` 不证明本次联网，需看 `last_success/last_error`；7 天缓存新鲜度不是定时刷新承诺。完整命令、Gaia 参数/响应结构和检查清单见上述双语手册。
