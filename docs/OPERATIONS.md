# API Monitor 生产运维手册

> Phase 3 | 7×24 本地/容器部署参考

## 1. 部署拓扑

```
用户应用 / 浏览器扩展
        ↓
  SentinelProxy (:8080)
        ↓ 记录 SQLite
  闲时分析 / 仪表板
        ↓
  中转站 API
```

## 2. 推荐部署方式

### Docker Compose（推荐）

```bash
cd deploy
export SENTINEL_UPSTREAM_URL="https://your-relay.example.com"
docker compose up -d
```

数据卷 `api-monitor-data` 持久化 `/data/responses.db`。

### systemd（Linux 裸机）

1. `pip install 'api-monitor[analyze]'` 到 `/opt/api-monitor/venv`
2. 复制 `deploy/api-monitor.service` → `/etc/systemd/system/`
3. 创建 `/etc/api-monitor/env`：

```bash
SENTINEL_UPSTREAM_URL=https://your-relay.example.com
SENTINEL_DB_PATH=/var/lib/api-monitor/responses.db
SENTINEL_HOST=127.0.0.1
SENTINEL_PORT=8080
```

4. `systemctl enable --now api-monitor`

## 3. 健康检查

```bash
curl -s http://127.0.0.1:8080/health | jq
```

期望：`status=ok`，`records` 随使用增长。

## 4. 备份与恢复

| 资产 | 路径 | 建议 |
|------|------|------|
| SQLite 数据库 | `SENTINEL_DB_PATH` | 每日快照 |
| 基线表 | 同库 `baselines` | 随 DB 备份 |

```bash
sqlite3 responses.db ".backup backup-$(date +%F).db"
```

恢复：停止服务 → 替换 DB 文件 → 启动服务。

## 5. 例行运维

| 周期 | 操作 |
|------|------|
| 每日 | 查看 `/dashboard` 告警数 |
| 每周 | `api-monitor analyze -o weekly.md` |
| 模型升级后 | `api-monitor baseline-refresh` |
| 磁盘不足 | 归档旧记录或轮换 DB |

## 6. 环境变量速查

| 变量 | 默认 | 说明 |
|------|------|------|
| `SENTINEL_UPSTREAM_URL` | — | 上游中转站（必填） |
| `SENTINEL_BASELINE_AUTO_UPDATE` | true | 低风险样本 EMA 更新基线 |
| `SENTINEL_BASELINE_EMA_ALPHA` | 0.08 | EMA 学习率 |
| `SENTINEL_ALERT_SMOOTHING_WINDOW` | 3 | 告警历史平滑窗口 |
| `SENTINEL_LOGPROBS_PVALUE` | 0.01 | Logprobs 漂移阈值 |
| `SENTINEL_ENABLE_CORS` | true | 浏览器扩展跨域 |

## 7. 故障排查

### 代理返回 502 `upstream_not_configured`

未设置 `SENTINEL_UPSTREAM_URL` 或请求未带 `X-Sentinel-Upstream`。

### 分析报错缺少依赖

```bash
pip install 'api-monitor[analyze]'
```

### 浏览器扩展无法上报

1. 确认 `api-monitor serve` 已启动
2. 确认 `SENTINEL_ENABLE_CORS=true`
3. 检查扩展 `INGEST_URL` 端口一致

### 误报过多

- 增大 `SENTINEL_ALERT_SMOOTHING_WINDOW`（如 5）
- 运行 `api-monitor baseline-refresh` 重建基线
- 降低 `SENTINEL_BASELINE_EMA_ALPHA` 使基线更稳定

### 漏报增多

- 减小 `SENTINEL_DRIFT_THRESHOLD`
- 减小平滑窗口

## 8. 安全建议

- 代理默认绑定 `127.0.0.1`，勿暴露公网
- DB 含完整 API 响应文本，注意磁盘加密与访问控制
- 扩展仅应安装在可信环境

## 9. 升级

```bash
pip install -U api-monitor
api-monitor baseline-refresh
systemctl restart api-monitor   # 或 docker compose restart
```

SQLite 模式向前兼容，新版本会自动 `ALTER TABLE` 增加列。
