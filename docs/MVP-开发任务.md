# 方案 A（透明代理）MVP 开发任务

> 对应完整技术方案 **Phase 1**，实现记录-分析分离架构的第一阶段交付。

## 已完成（本迭代）

| 任务 | 模块 | 状态 |
|------|------|------|
| FastAPI 透明反向代理 | `api_monitor.proxy` | ✅ |
| SQLite 零计算响应记录 | `api_monitor.storage` | ✅ |
| OpenAI / Anthropic 响应解析 | `api_monitor.proxy.extract` | ✅ |
| SSE 流式响应合并记录 | `api_monitor.proxy` | ✅ |
| MiniLM 离线家族分类 | `api_monitor.analyzer` | ✅ |
| 可解释词汇证据 | `api_monitor.analyzer.lexicon` | ✅ |
| Markdown 分析报告 | `api_monitor.analyzer.report` | ✅ |
| CLI：`serve` / `analyze` / `status` | `api_monitor.cli` | ✅ |
| 单元测试 | `tests/` | ✅ |

## Phase 2 待办

- [ ] 时序特征（TTFT / ITT）漂移检测
- [ ] 基线自动建立与动态阈值
- [ ] Web 仪表板
- [ ] 多协议完善（Gemini 原生路径等）
- [ ] Docker / systemd 部署模板

## Phase 3 待办

- [ ] 基线自动更新与误报优化
- [ ] HTML 报告导出
- [ ] 生产级 7×24 运维文档

## 验收标准（M1）

- [x] 代理可配置上游并记录响应
- [x] 闲时 `api-monitor analyze` 生成 Markdown 报告
- [x] 跨家族替换可产生 HIGH 告警与证据列表
