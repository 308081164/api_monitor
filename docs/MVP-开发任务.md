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

| 任务 | 模块 | 状态 |
|------|------|------|
| ITT / TTFT 时序采集与 KS 漂移检测 | `analyzer/drift.py`, `proxy/extract.py` | ✅ |
| 基线自动建立与动态阈值 | `analyzer/baseline_builder.py`, `storage/baseline.py` | ✅ |
| 多信号融合决策 | `analyzer/fusion.py` | ✅ |
| Web 仪表板 | `dashboard/` | ✅ |
| HTML 报告导出 | `analyzer/report.py`, `analyze --format html` | ✅ |
| Gemini 多协议解析 | `proxy/extract.py` | ✅ |
| Docker / systemd 部署 | `deploy/` | ✅ |

## Phase 3 待办

- [ ] 基线自动更新与误报优化（历史平滑）
- [ ] Logprobs 采集（可选信号）
- [ ] 浏览器插件（方案 B）
- [ ] 生产级 7×24 运维文档

## 验收标准（M2）

- [x] 支持 OpenAI / Claude / Gemini 响应解析
- [x] 时序 + 文本 + 元数据多信号融合告警
- [x] Web 仪表板可查看记录并触发分析
- [x] Docker Compose 一键部署
