API Monitor — Windows 安装版快速上手
=====================================

1. 安装时可选：
   - 自定义安装目录
   - 创建桌面快捷方式
   - 固定到开始菜单

2. 首次使用：
   - 从开始菜单或桌面打开「API Monitor」
   - 会自动启动本地服务并打开仪表板 (http://127.0.0.1:8080/dashboard)
   - 在系统环境或中转站客户端中，将 API 地址改为：
     http://127.0.0.1:8080/v1

3. 配置上游中转站（二选一）：
   - 安装目录下新建文本，设置用户环境变量 SENTINEL_UPSTREAM_URL
   - 或在仪表板说明中按 docs\OPERATIONS.md 操作

4. 退出：
   - 关闭「API Monitor」窗口即可自动停止服务并释放后台进程

5. 卸载：
   - 系统「应用和功能」中卸载，会自动清理相关进程

数据目录：%APPDATA%\API Monitor\

项目主页：https://github.com/308081164/api_monitor
