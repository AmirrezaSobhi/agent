#ifndef OutputRoot
  #define OutputRoot "."
#endif
#ifndef ExitCode
  #define ExitCode "0"
#endif

[Setup]
AppId={{6D176322-DF7D-4360-AF0F-A93D3516C976}
AppName=MT5Agent Required Operation Smoke Test
AppVersion=0.0.0
DefaultDirName={tmp}\MT5Agent-Required-Operation-Smoke
DisableDirPage=yes
PrivilegesRequired=lowest
Uninstallable=no
OutputDir={#OutputRoot}
OutputBaseFilename=MT5Agent-Required-Operation-Smoke
SetupLogging=yes

[Code]
#include "..\RequiredPowerShell.issinc"

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RunRequiredPowerShell('Synthetic failure probe', '-NoProfile -NonInteractive -Command "exit {#ExitCode}"', ExpandConstant('{tmp}'));
end;
