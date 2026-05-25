# Stop API Monitor background processes (uninstall / launcher exit).
param(
    [string]$InstallDir = ""
)

$ErrorActionPreference = "SilentlyContinue"

$patterns = @(
    "api_monitor",
    "api-monitor",
    "APIMonitor",
    "uvicorn"
)

Get-CimInstance Win32_Process | ForEach-Object {
    $cmd = $_.CommandLine
    if (-not $cmd) { return }
    foreach ($pat in $patterns) {
        if ($cmd -like "*$pat*") {
            Stop-Process -Id $_.ProcessId -Force
            break
        }
    }
}

if ($InstallDir -and (Test-Path $InstallDir)) {
    Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and ($_.ExecutablePath -like "$InstallDir*")
    } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
}
