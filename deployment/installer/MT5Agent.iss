#ifndef SourceRoot
  #define SourceRoot "..\.."
#endif
#ifndef ProductVersion
  #define ProductVersion "0.1.5"
#endif
#ifndef OutputRoot
  #define OutputRoot "..\..\dist\installer"
#endif

[Setup]
AppId={{645A0027-56AC-4ED1-9D6D-65A68B5D0155}
AppName=MT5Agent
AppVersion={#ProductVersion}
AppVerName=MT5Agent {#ProductVersion}
AppPublisher=MT5Agent Internal
DefaultDirName={autopf}\MT5Agent
DisableDirPage=yes
DefaultGroupName=MT5Agent
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
OutputDir={#OutputRoot}
OutputBaseFilename=MT5Agent-Setup-v{#ProductVersion}-windows-x64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
Uninstallable=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\Desktop\MT5Agent.Desktop.exe
VersionInfoVersion=0.1.5.0
VersionInfoProductVersion={#ProductVersion}
VersionInfoDescription=MT5Agent unified Windows setup
VersionInfoProductName=MT5Agent

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Dirs]
Name: "{commonappdata}\MT5Agent\Logs"; Permissions: system-full admins-full

[Files]
Source: "{#SourceRoot}\deployment\installer\stage\Service\*"; DestDir: "{app}\Service"; Flags: ignoreversion recursesubdirs createallsubdirs; BeforeInstall: StopExistingService
Source: "{#SourceRoot}\deployment\installer\stage\Agent\*"; DestDir: "{app}\Agent"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\deployment\installer\stage\Worker\*"; DestDir: "{app}\Worker"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\deployment\installer\stage\Desktop\*"; DestDir: "{app}\Desktop"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\deployment\installer\stage\Support\*"; DestDir: "{app}\maintenance"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\MT5Agent\MT5Agent Desktop"; Filename: "{app}\Desktop\MT5Agent.Desktop.exe"; WorkingDir: "{app}\Desktop"
Name: "{autodesktop}\MT5Agent Desktop"; Filename: "{app}\Desktop\MT5Agent.Desktop.exe"; WorkingDir: "{app}\Desktop"; Tasks: desktopicon

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\maintenance\Install-MT5AgentService.ps1"" -Action Install -InstallRoot ""{app}"""; Flags: runhidden waituntilterminated; StatusMsg: "Installing the MT5Agent Windows Service..."
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\Worker\Register-PackagedMT5Worker.ps1"" -InstallRoot ""{app}"""; Flags: runhidden waituntilterminated; StatusMsg: "Registering the preconfigured interactive Worker..."; Check: HasRuntimeProvisioning
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\maintenance\Save-MT5AgentUserSettings.ps1"" -InstallPath ""{app}"" -TerminalPath ""{code:GetTerminalPath}"""; Flags: runasoriginaluser runhidden waituntilterminated; StatusMsg: "Saving Desktop settings for the current Windows user..."

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\Worker\Unregister-PackagedMT5Worker.ps1"" -InstallRoot ""{app}"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveMT5AgentWorkerTask"
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\maintenance\Install-MT5AgentService.ps1"" -Action Uninstall -InstallRoot ""{app}"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveMT5AgentService"

[Code]
var Mt5Page: TInputDirWizardPage;
#include "MT5AgentWizard.issinc"

function HasRuntimeProvisioning: Boolean;
var RuntimePrincipal, TerminalPath, ProfilePath, WorkerInstallPath: string;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\MT5Agent\Runtime', 'RuntimePrincipal', RuntimePrincipal) and
    RegQueryStringValue(HKLM, 'SOFTWARE\MT5Agent\Runtime', 'TerminalPath', TerminalPath) and
    RegQueryStringValue(HKLM, 'SOFTWARE\MT5Agent\Runtime', 'ProfilePath', ProfilePath) and
    RegQueryStringValue(HKLM, 'SOFTWARE\MT5Agent\Runtime', 'WorkerInstallPath', WorkerInstallPath) and
    (CompareText(ExpandConstant('{app}\Worker'), WorkerInstallPath) = 0) and
    FileExists(TerminalPath) and DirExists(ProfilePath);
end;

function InitializeSetup: Boolean;
var Release: Cardinal;
begin
  Result := True;
  if not RegQueryDWordValue(HKLM, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full', 'Release', Release) or (Release < 528040) then begin
    MsgBox('MT5Agent Desktop requires Microsoft .NET Framework 4.8 or later. Install it from Microsoft, then rerun setup.', mbError, MB_OK);
    Result := False;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    WizardForm.FinishedLabel.Caption := 'MT5Agent Desktop and the Python Agent Service are installed. The bundled Python Worker runs only after a separate standard interactive Runtime Principal and matching MT5 profile have been configured.';
end;

procedure StopExistingService;
var ResultCode: Integer;
    Script, Args: string;
begin
  Script := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Args := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\maintenance\Install-MT5AgentService.ps1') + '" -Action Stop -InstallRoot "' + ExpandConstant('{app}') + '"';
  if FileExists(ExpandConstant('{app}\maintenance\Install-MT5AgentService.ps1')) then begin
    if not Exec(Script, Args, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      RaiseException('Unable to stop the existing MT5Agent service for upgrade.');
    if ResultCode <> 0 then
      RaiseException('The existing MT5Agent service could not be stopped safely. Setup has not replaced its binaries.');
  end;
end;
