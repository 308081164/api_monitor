# API Monitor

API 中转站被动式模型真实性持续监控系统。

基于透明代理（方案 A）拦截用户软件与中转站之间的 API 流量，本地记录响应并在闲时离线分析，检测模型是否被替换或掺水。

## 状态

本项目处于**方案与仓库初始化阶段**，核心功能尚未开发。技术方案见 [`docs/`](docs/) 目录。

## 方案 A：透明代理

将客户端 API Base URL 或环境变量指向本地代理：

```bash
export OPENAI_BASE_URL="http://localhost:8080/v1"
export ANTHROPIC_BASE_URL="http://localhost:8080/v1"
```

## 下载

预构建产物见 [Releases](https://github.com/308081164/api_monitor/releases)。

## 许可证

本项目采用 [Mozilla Public License 2.0](LICENSE)（MPL-2.0）开源，修改后的文件须以相同许可证发布。

## 文档

- [完整技术方案](docs/API中转站被动监控系统-完整技术方案.md)
- [技术规划与可行性报告](docs/API中转站被动式模型真实性持续监控系统-技术规划与可行性报告.md)
