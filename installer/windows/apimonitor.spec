# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for API Monitor Windows bundle."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

root = Path(SPECPATH).resolve().parent.parent
src_static = root / "src" / "api_monitor" / "dashboard" / "static"

block_cipher = None

hiddenimports = collect_submodules("api_monitor")
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("fastapi")
hiddenimports += [
    "click",
    "httpx",
    "sklearn.utils._typedefs",
    "sklearn.neighbors._partition_nodes",
]

datas = [(str(src_static), "api_monitor/dashboard/static")]
binaries = []

for pkg in ("uvicorn", "fastapi", "sentence_transformers", "sklearn"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(
    [str(Path(SPECPATH) / "launcher.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="APIMonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="APIMonitor",
)
