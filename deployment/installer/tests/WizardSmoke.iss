#ifndef OutputRoot
  #define OutputRoot "."
#endif

[Setup]
AppId={{F847A4A7-746D-4D28-93B2-2B38A9C70EBF}
AppName=MT5Agent Wizard Initialization Smoke Test
AppVersion=0.0.0
DefaultDirName={tmp}\MT5Agent-Wizard-Smoke
DisableDirPage=yes
PrivilegesRequired=lowest
Uninstallable=no
OutputDir={#OutputRoot}
OutputBaseFilename=MT5Agent-Wizard-Smoke
SetupLogging=yes

[Code]
var Mt5Page: TInputDirWizardPage;

#include "..\MT5AgentWizard.issinc"
