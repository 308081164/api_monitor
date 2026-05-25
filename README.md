# API Monitor

API 中转站被动式模型真实性持续监控系统。

基于**方案 A：透明代理**，在用户软件与中转站 API 之间插入本地代理，**使用时仅记录**响应到 SQLite，**闲时离线分析**（MiniLM）检测模型家族是否漂移。

## 快速开始

### 安装

```bash
pip install -e ".[analyze,dev]"
```

仅代理（不安装分析模型）：

```bash
pip install -e .
```

### 1. 配置上游并启动代理

```bash
export SENTINEL_UPSTREAM_URL="https://你的中转站.example.com"
api-monitor serve --port 8080
```

### 2. 将客户端指向本地代理

```bash
export OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
export ANTHROPIC_BASE_URL="http://127.0.0.1:8080/v1"
```

或在代码中：

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8080/v1", api_key="your-key")
```

### 3. 正常使用 API 后，睡前离线分析

```bash
api-monitor status
api-monitor analyze -o report.md
```

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `SENTINEL_UPSTREAM_URL` | 中转站 API 根地址 | （必填） |
| `SENTINEL_HOST` / `SENTINEL_PORT` | 代理监听 | `127.0.0.1:8080` |
| `SENTINEL_DB_PATH` | SQLite 路径 | `responses.db` |
| `SENTINEL_MIN_TEXT_LENGTH` | 分析最小文本长度 | `32` |
| `SENTINEL_DRIFT_THRESHOLD` | 漂移告警阈值 | `0.15` |

也可在单次请求中通过请求头 `X-Sentinel-Upstream` 指定上游。

## 架构（记录-分析分离）

```
用户应用 → SentinelProxy (localhost) → 中转站 API
                ↓ 仅写入 SQLite
         闲时: api-monitor analyze → Markdown 报告
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `api-monitor serve` | 启动透明代理 |
| `api-monitor status` | 查看已记录条数 |
| `api-monitor analyze` | 离线 MiniLM 分析并生成报告 |

## 下载

预构建产物见 [Releases](https://github.com/308081164/api_monitor/releases)。

## 文档

- [完整技术方案](docs/API中转站被动监控系统-完整技术方案.md)
- [技术规划与可行性报告](docs/API中转站被动式模型真实性持续监控系统-技术规划与可行性报告.md)
- [MVP 开发任务清单](docs/MVP-开发任务.md)

## 许可证

本项目采用 [Mozilla Public License 2.0](LICENSE)（MPL-2.0）开源。
