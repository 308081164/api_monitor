# Windows 安装包构建说明

## 产物

- `{version}_windows-set-up.exe` — Inno Setup 安装程序
- 安装后包含 `APIMonitor.exe` 图形启动器（非程序员友好）

## 安装程序功能

| 功能 | 实现 |
|------|------|
| 自选安装目录 | Inno Setup 默认目录页 `{autopf}\API Monitor` |
| 桌面快捷方式 | 安装任务 `desktopicon`（默认不勾选） |
| 开始菜单 | 安装任务 `startmenu`（默认勾选） |
| 退出释放进程 | `launcher.py` 关闭窗口时终止子进程 + `stop-apimonitor.ps1` |
| 卸载清理 | `[UninstallRun]` 调用 `stop-apimonitor.ps1` |

## 安装程序语言

简体中文翻译文件已内嵌在 `languages/ChineseSimplified.isl`（来自 [Inno Setup 社区翻译](https://github.com/jrsoftware/issrc/tree/main/Files/Languages/Unofficial)）。CI 通过 `choco install innosetup` 安装的 Inno Setup **不包含**该文件，因此不能依赖 `compiler:Languages\ChineseSimplified.isl`。

## 本地构建（需 Windows）

```powershell
choco install innosetup -y
pip install ".[analyze]"
pip install pyinstaller>=6.0
.\installer\windows\build-windows.ps1
```

输出：`dist\installer\0.4.0_windows-set-up.exe`

## CI

`main` 分支推送后，`.github/workflows/release.yml` 的 `build-windows-installer` 任务自动构建并上传到 GitHub Release。
