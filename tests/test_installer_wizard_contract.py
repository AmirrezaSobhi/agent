from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "deployment" / "installer" / "MT5Agent.iss"
WIZARD_INCLUDE = ROOT / "deployment" / "installer" / "MT5AgentWizard.issinc"
SMOKE_SETUP = ROOT / "deployment" / "installer" / "tests" / "WizardSmoke.iss"


def test_product_installer_uses_shared_wizard_contract():
    installer = INSTALLER.read_text(encoding="utf-8")
    assert '#include "MT5AgentWizard.issinc"' in installer


def test_input_directory_page_adds_item_before_indexed_values_access():
    wizard = WIZARD_INCLUDE.read_text(encoding="utf-8")
    add_index = wizard.index("Mt5Page.Add(")
    first_value_access = wizard.index("Mt5Page.Values[0]")
    assert add_index < first_value_access
    assert wizard.index("if WizardSilent then begin") < wizard.index("CreateInputDirPage(")
    click_validation = wizard[wizard.index("function NextButtonClick"):]
    assert "if not WizardSilent then begin" in click_validation
    assert "if CurPageID = Mt5Page.ID then begin" in click_validation
    assert "if WizardSilent then begin" in wizard[wizard.index("function GetTerminalPath"):]


def test_shared_wizard_preserves_optional_terminal_detection_and_validation():
    wizard = WIZARD_INCLUDE.read_text(encoding="utf-8")
    assert "FileExists(AddBackslash(Candidate) + 'terminal64.exe')" in wizard
    assert "FileExists(AddBackslash(Mt5Page.Values[0]) + 'terminal64.exe')" in wizard
    assert "function GetTerminalPath(Param: string): string;" in wizard
    assert "function NextButtonClick(CurPageID: Integer): Boolean;" in wizard


def test_product_installer_keeps_expected_install_root_and_bundled_component_paths():
    installer = INSTALLER.read_text(encoding="utf-8")
    assert "DefaultDirName={autopf}\\MT5Agent" in installer
    for component in ("Service", "Agent", "Worker", "Desktop"):
        assert f"\\stage\\{component}\\*" in installer
        assert f'DestDir: "{{app}}\\{component}"' in installer


def test_windows_runtime_smoke_uses_same_wizard_include_and_both_silent_modes():
    smoke = SMOKE_SETUP.read_text(encoding="utf-8")
    runner = (ROOT / "deployment" / "installer" / "Test-WizardInitialization.ps1").read_text(encoding="utf-8")
    assert '#include "..\\MT5AgentWizard.issinc"' in smoke
    assert "@('/SILENT','/VERYSILENT')" in runner
    assert "MT5AgentWizard\\.InitializeWizard completed \\(silent\\)" in runner
    assert "GetTerminalPath completed:" in runner
    build = (ROOT / "deployment" / "installer" / "New-UnifiedInstaller.ps1").read_text(encoding="utf-8")
    assert "Test-WizardInitialization.ps1" in build
