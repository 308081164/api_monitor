# API Monitor

API 中转站被动式模型真实性持续监控系统。

基于**方案 A：透明代理**（主）与**方案 B：浏览器扩展**（Web 场景），记录 API 响应并在闲时离线分析，检测模型是否被替换或掺水。

## Windows 一键安装（推荐普通用户）

在 [Releases](https://github.com/308081164/api_monitor/releases) 下载 **`{版本号}_windows-set-up.exe`**（例如 `0.4.0_windows-set-up.exe`）：

1. 运行安装程序，可**自选安装目录**
2. 勾选是否**创建桌面快捷方式**、是否**固定到开始菜单**
3. 从开始菜单或桌面打开 **API Monitor** → 自动启动服务并打开仪表板
4. 关闭窗口即**自动停止后台服务**；卸载时也会**自动清理进程**

数据保存在 `%APPDATA%\API Monitor\`。配置中转站请设置环境变量 `SENTINEL_UPSTREAM_URL`。

## 快速开始（开发者 / Python）

```bash
pip install -e ".[analyze,dev]"
export SENTINEL_UPSTREAM_URL="https://你的中转站.example.com"
api-monitor serve
```

- 代理：`http://127.0.0.1:8080/v1`
- 仪表板：http://127.0.0.1:8080/dashboard
- 扩展上报：http://127.0.0.1:8080/api/ingest

```bash
export OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
api-monitor analyze -o report.md
api-monitor analyze --format json -o report.json
api-monitor baseline-refresh
```

## Phase 3+ 能力

| 能力 | 说明 |
|------|------|
| **系统桌面通知** | 分析发现告警时推送 OS 通知（可选 `plyer`） |
| **Webhook 告警** | 仪表板或 `user-settings.json` 配置 |
| **首次使用引导** | 仪表板内配置上游、对照 API、分析模式 |
| **高精度分析** | `SENTINEL_ANALYSIS_MODE=precise`（MPNet） |
| **对照验证** | `SENTINEL_REFERENCE_UPSTREAM_URL` 对比官方 API 样本 |
| **基线 EMA / 告警平滑 / Logprobs** | 见 [docs/OPERATIONS.md](docs/OPERATIONS.md) |

安装增强通知：`pip install 'api-monitor[alerts]'`（Linux 需 `libnotify`）

## 方案 B：浏览器扩展

见 [extension/README.md](extension/README.md)。适用于网页端无法改 `base_url` 的场景。

## Docker

```bash
cd deploy && SENTINEL_UPSTREAM_URL=https://relay.example.com docker compose up -d
```

## 文档

- [完整技术方案](docs/API中转站被动监控系统-完整技术方案.md)
- [可行性报告](docs/API中转站被动式模型真实性持续监控系统-技术规划与可行性报告.md)
- [开发任务清单](docs/MVP-开发任务.md)
- [生产运维手册](docs/OPERATIONS.md)

## 许可证

[MPL-2.0](LICENSE)
