; Inno Setup script for Break-Time.
;
; Version is injected via the BREAKTIME_VERSION environment variable (set by
; .github/workflows/release.yml before invoking iscc), falling back to a dev version for
; local builds. Installs per-user (PrivilegesRequired=lowest, no admin/UAC prompt needed)
; -- consistent with auto-start using the per-user HKCU Registry Run key, not HKLM.

#define MyAppName "Break-Time"
#define MyAppVersion GetEnv("BREAKTIME_VERSION")
#if MyAppVersion == ""
  #define MyAppVersion "0.0.0-dev"
#endif
#define MyAppPublisher "Break-Time Contributors"

[Setup]
AppId={{B3EA9B3E-6C1F-4C2E-9C1A-2F6B7B8D6E10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=BreakTimeSetup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\breaktime.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\breaktime\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\breaktime.exe"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\breaktime.exe"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent
