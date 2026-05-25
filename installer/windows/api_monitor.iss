; Inno Setup script — API Monitor Windows installer
; Build on CI: iscc /DAppVersion=0.4.0 api_monitor.iss

#ifndef AppVersion
  #define AppVersion "0.4.0"
#endif

#define MyAppName "API Monitor"
#define MyAppPublisher "API Monitor Project"
#define MyAppURL "https://github.com/308081164/api_monitor"
#define MyAppExeName "APIMonitor.exe"

[Setup]
AppId={{A7B3C9E1-4F2D-4A8B-9C1E-APIMONITOR2026}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
AllowNoIcons=yes
OutputDir=..\..\dist\installer
OutputBaseFilename={#AppVersion}_windows-set-up
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes
ShowLanguageDialog=auto

[Languages]
; 仓库内嵌简体中文（choco/GitHub Actions 的 Inno Setup 默认不含 ChineseSimplified.isl）
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项："; Flags: unchecked
Name: "startmenu"; Description: "固定到开始菜单"; GroupDescription: "附加选项："; Flags: checkedonce

[Files]
Source: "..\..\dist\APIMonitor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "stop-apimonitor.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "README-INSTALL.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\docs\OPERATIONS.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\stop-apimonitor.ps1"" -InstallDir ""{app}"""; Flags: runhidden waituntilterminated

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  { 安装前停止可能残留的旧版本进程 }
  Exec('powershell.exe',
    '-NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match ''api_monitor|APIMonitor|uvicorn'' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;
