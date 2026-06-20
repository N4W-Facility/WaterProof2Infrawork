#define AppName      "WaterProof2Infrawork"
#define AppVersion   "1.0.0"
#define AppPublisher "Autodesk / The Nature Conservancy"
#define AppExeName   "WaterProof2Infrawork.exe"
#define BuildDir     "compiler\WaterProof2Infrawork"

[Setup]
; IMPORTANT: never change AppId between releases — it identifies the app for upgrades
AppId={{E308955E-6F5D-49C7-A5B0-DD29B8C07AE7}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=compiler
OutputBaseFilename={#AppName}_v{#AppVersion}
SetupIconFile=ui\icons\Icon_WP_Autodesk.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Wipe old lib/ on upgrade so stale files don't accumulate
Type: filesandordirs; Name: "{app}\lib"

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files;         Name: "{app}\prefs.json"
Type: filesandordirs; Name: "{app}"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  PrefsPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    PrefsPath := ExpandConstant('{app}\prefs.json');
    if not FileExists(PrefsPath) then
      SaveStringToFile(PrefsPath, '{"project_dir": ""}', False);
  end;
end;
