# API Monitor

API 中转站被动式模型真实性持续监控系统。

基于**方案 A：透明代理**，在用户软件与中转站 API 之间插入本地代理，**使用时仅记录**响应到 SQLite，**闲时离线分析**（MiniLM + 多信号融合）检测模型家族是否漂移。

## 快速开始

### 安装

```bash
pip install -e ".[analyze,dev]"
```

### 1. 配置上游并启动代理

```bash
export SENTINEL_UPSTREAM_URL="https://你的中转站.example.com"
api-monitor serve --port 8080
```

浏览器打开仪表板：**http://127.0.0.1:8080/dashboard**

### 2. 将客户端指向本地代理

```bash
export OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
export ANTHROPIC_BASE_URL="http://127.0.0.1:8080/v1"
```

### 3. 离线分析

```bash
api-monitor analyze -o report.md
api-monitor analyze --format html -o report.html
```

或在仪表板点击「运行离线分析」。

## Phase 2 能力

| 能力 | 说明 |
|------|------|
| **ITT / TTFT 时序漂移** | 流式 SSE 记录 token 间隔，KS 检验对比基线 |
| **基线自动建立** | 每个 `model_requested` 前 N 条样本建立动态阈值 |
| **多信号融合** | 文本 + 元数据 + 时序加权决策 |
| **Web 仪表板** | `/dashboard` 实时查看记录与告警 |
| **Gemini 协议** | 支持 `candidates[].content.parts` 解析 |
| **Docker / systemd** | 见 `deploy/` 目录 |

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `SENTINEL_UPSTREAM_URL` | 中转站 API 根地址 | （必填） |
| `SENTINEL_HOST` / `SENTINEL_PORT` | 代理监听 | `127.0.0.1:8080` |
| `SENTINEL_DB_PATH` | SQLite 路径 | `responses.db` |
| `SENTINEL_BASELINE_MIN_SAMPLES` | 基线最少样本数 | `20` |
| `SENTINEL_TIMING_PVALUE` | 时序 KS 检验 p 阈值 | `0.05` |
| `SENTINEL_ENABLE_DASHBOARD` | 启用 Web 仪表板 | `true` |

## Docker

```bash
cd deploy
SENTINEL_UPSTREAM_URL=https://your-relay.example.com docker compose up -d
```

## 文档

- [完整技术方案](docs/API中转站被动监控系统-完整技术方案.md)
- [技术规划与可行性报告](docs/API中转站被动式模型真实性持续监控系统-技术规划与可行性报告.md)
- [MVP 开发任务清单](docs/MVP-开发任务.md)

## 许可证

[MPL-2.0](LICENSE)
