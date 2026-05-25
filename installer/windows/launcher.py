"""
API Monitor Windows 图形启动器。
关闭窗口时自动停止后台服务并释放进程资源。
"""

from __future__ import annotations

import multiprocessing
import os
import sys
import webbrowser
from pathlib import Path


def _data_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = Path(base) / "API Monitor"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_server() -> None:
    import uvicorn

    from api_monitor.config import Settings
    from api_monitor.proxy.app import create_app

    data = _data_dir()
    os.environ.setdefault("SENTINEL_DB_PATH", str(data / "responses.db"))
    os.environ.setdefault("SENTINEL_DATA_DIR", str(data))
    settings = Settings.from_env()
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


def _stop_processes() -> None:
    script = Path(__file__).resolve().parent / "stop-apimonitor.ps1"
    install_dir = Path(__file__).resolve().parent
    if script.is_file():
        os.system(
            f'powershell -NoProfile -ExecutionPolicy Bypass -File "{script}" '
            f'-InstallDir "{install_dir}"'
        )


def main() -> None:
    multiprocessing.freeze_support()

    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        _run_server()
        return

    host = os.environ.get("SENTINEL_HOST", "127.0.0.1")
    port = int(os.environ.get("SENTINEL_PORT", "8080"))
    dashboard = f"http://{host}:{port}/dashboard"

    server = multiprocessing.Process(target=_run_server, daemon=True)
    server.start()

    root = tk.Tk()
    root.title("API Monitor")
    root.geometry("420x220")
    root.resizable(False, False)

    tk.Label(
        root,
        text="API Monitor 正在运行",
        font=("Segoe UI", 12, "bold"),
    ).pack(pady=(16, 8))
    tk.Label(
        root,
        text=f"仪表板: {dashboard}\n关闭本窗口将自动停止服务并释放进程。",
        justify="center",
    ).pack(pady=8)

    def open_dashboard() -> None:
        webbrowser.open(dashboard)

    tk.Button(root, text="打开仪表板", command=open_dashboard, width=20).pack(pady=6)
    tk.Button(
        root,
        text="退出并停止服务",
        command=root.destroy,
        width=20,
    ).pack(pady=6)

    def on_close() -> None:
        if server.is_alive():
            server.terminate()
            server.join(timeout=8)
            if server.is_alive():
                server.kill()
        _stop_processes()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

    if server.is_alive():
        server.terminate()
        server.join(timeout=5)
    _stop_processes()


if __name__ == "__main__":
    main()
