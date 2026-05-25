# API Monitor 浏览器扩展（方案 B）

在无法修改 `base_url` 的 Web 应用中，通过注入 `fetch` 钩子将 LLM API 响应上报到本地 API Monitor。

## 安装（开发者模式）

1. 启动本地服务：`api-monitor serve`
2. Chrome → `chrome://extensions` → 开启「开发者模式」
3. 「加载已解压的扩展程序」→ 选择本目录 `extension/`
4. 打开使用 OpenAI / Anthropic / Gemini API 的网页

## 配置

默认上报地址：`http://127.0.0.1:8080/api/ingest`

修改 `content.js` 中的 `INGEST_URL` 可更换端口或主机。

## 限制

- 仅捕获页面内 JavaScript 发起的 `fetch` 请求
- 无法捕获原生应用或非 fetch 流量（此类场景请使用方案 A 透明代理）
- 跨域上报依赖 API Monitor 的 CORS（`SENTINEL_ENABLE_CORS=true`）
