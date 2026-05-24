# 方案 A（透明代理）开发任务

## Phase 1（已完成）

| 任务 | 状态 |
|------|------|
| FastAPI 透明反向代理 | ✅ |
| SQLite 零计算响应记录 | ✅ |
| OpenAI / Anthropic 响应解析 | ✅ |
| MiniLM 离线家族分类 | ✅ |
| CLI：`serve` / `analyze` / `status` | ✅ |

## Phase 2（已完成）

| 任务 | 状态 |
|------|------|
| ITT / TTFT 时序漂移 | ✅ |
| 基线自动建立与动态阈值 | ✅ |
| 多信号融合 | ✅ |
| Web 仪表板 | ✅ |
| Gemini 协议 | ✅ |
| Docker / systemd | ✅ |

## Phase 3（已完成）

| 任务 | 模块 | 状态 |
|------|------|------|
| 基线 EMA 自动更新 | `analyzer/baseline_updater.py` | ✅ |
| 告警历史平滑（降误报） | `analyzer/smoothing.py` | ✅ |
| Logprobs 采集与漂移 | `analyzer/logprobs.py` | ✅ |
| 浏览器扩展（方案 B） | `extension/` | ✅ |
| Ingest API | `POST /api/ingest` | ✅ |
| JSON 报告导出 | `analyze --format json` | ✅ |
| 生产运维文档 | `docs/OPERATIONS.md` | ✅ |
| `baseline-refresh` CLI | `api-monitor baseline-refresh` | ✅ |

## 验收标准（M3）

- [x] 低风险样本自动 EMA 更新基线
- [x] 孤立尖峰告警经平滑窗口抑制
- [x] 支持 logprobs 可选信号
- [x] 浏览器扩展 + 本地 ingest
- [x] 7×24 运维手册（备份/升级/排障）
