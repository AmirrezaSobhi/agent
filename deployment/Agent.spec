from pathlib import Path
from runpy import run_path

project_root = Path(SPECPATH).resolve().parent
version = run_path(str(project_root / "agent" / "__init__.py"))["__version__"]
icon_path = project_root / "deployment" / "MT5Agent.ico"

analysis = Analysis(
    [str(project_root / "agent" / "__main__.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[
        "MetaTrader5",
        "numpy",
        "agent.adapters.mt5_adapter",
        "agent.infrastructure.interactive_mt5_worker",
        "agent.infrastructure.terminal_inspection",
    ], noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, analysis.binaries, analysis.datas, [],
    name=f"MT5Agent-v{version}", icon=str(icon_path), debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=True,
)
