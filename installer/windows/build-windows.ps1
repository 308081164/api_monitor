# Build API Monitor Windows installer on GitHub Actions or local Windows.
param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

if (-not $Version) {
    $Version = python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
}
Write-Host "Building API Monitor Windows installer v$Version"

python -m pip install --upgrade pip wheel
python -m pip install ".[analyze]"
python -m pip install pyinstaller>=6.0

if (Test-Path "dist\APIMonitor") { Remove-Item -Recurse -Force "dist\APIMonitor" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

pyinstaller --noconfirm --clean "installer\windows\apimonitor.spec"

New-Item -ItemType Directory -Force -Path "dist\installer" | Out-Null

$langFile = Join-Path $PSScriptRoot "languages\ChineseSimplified.isl"
if (-not (Test-Path $langFile)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $langFile) | Out-Null
    $langUrl = "https://raw.githubusercontent.com/jrsoftware/issrc/main/Files/Languages/Unofficial/ChineseSimplified.isl"
    Write-Host "Downloading ChineseSimplified.isl ..."
    Invoke-WebRequest -Uri $langUrl -OutFile $langFile -UseBasicParsing
}

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    $iscc = "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
}
if (-not (Test-Path $iscc)) {
    throw "Inno Setup 6 (ISCC.exe) not found. Install from https://jrsoftware.org/isinfo.php"
}

& $iscc "/DAppVersion=$Version" "installer\windows\api_monitor.iss"

$out = Join-Path $Root "dist\installer\${Version}_windows-set-up.exe"
if (-not (Test-Path $out)) {
    throw "Installer not produced: $out"
}
Write-Host "OK: $out"
Get-Item $out | Format-List Name, Length, FullName
