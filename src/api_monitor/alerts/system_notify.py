"""Cross-platform desktop notifications (stdlib-first, optional plyer)."""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def send_system_notification(
    title: str,
    message: str,
    *,
    timeout: int = 12,
) -> bool:
    """Show a desktop notification. Returns True if a backend likely succeeded."""
    title = (title or "API Monitor")[:128]
    message = (message or "")[:512]

    if _try_plyer(title, message, timeout=timeout):
        return True
    system = platform.system()
    if system == "Darwin":
        return _notify_macos(title, message)
    if system == "Linux":
        return _notify_linux(title, message)
    if system == "Windows":
        return _notify_windows(title, message)
    return False


def _try_plyer(title: str, message: str, *, timeout: int) -> bool:
    try:
        from plyer import notification  # type: ignore[import-untyped]
    except ImportError:
        return False
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="API Monitor",
            timeout=timeout,
        )
        return True
    except Exception as exc:
        logger.debug("plyer notification failed: %s", exc)
        return False


def _notify_linux(title: str, message: str) -> bool:
    if not shutil.which("notify-send"):
        return False
    try:
        subprocess.run(
            ["notify-send", title, message, "-a", "API Monitor"],
            check=False,
            timeout=10,
        )
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("notify-send failed: %s", exc)
        return False


def _notify_macos(title: str, message: str) -> bool:
    safe_t = title.replace("\\", "\\\\").replace('"', '\\"')
    safe_m = message.replace("\\", "\\\\").replace('"', '\\"')
    script = f'display notification "{safe_m}" with title "{safe_t}"'
    try:
        subprocess.run(["osascript", "-e", script], check=False, timeout=10)
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("osascript failed: %s", exc)
        return False


def _notify_windows(title: str, message: str) -> bool:
    """Tray balloon tip via PowerShell (no extra Python deps)."""
    safe_t = title.replace("'", "''")
    safe_m = message.replace("'", "''").replace("`", "``")
    try:
        ps_balloon = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Warning
$n.Visible = $true
$n.BalloonTipTitle = '{safe_t}'
$n.BalloonTipText = '{safe_m}'
$n.ShowBalloonTip(10000)
Start-Sleep -Seconds 4
$n.Visible = $false
$n.Dispose()
"""
        creationflags: Optional[int] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_balloon],
            check=False,
            timeout=15,
            creationflags=creationflags,
        )
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("windows notify failed: %s", exc)
        return False
