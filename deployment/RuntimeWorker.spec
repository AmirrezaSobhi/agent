from pathlib import Path
from runpy import run_path
from PyInstaller.utils.hooks import copy_metadata

project_root = Path(SPECPATH).resolve().parent
version = run_path(str(project_root / "agent" / "__init__.py"))["__version__"]
icon_path = project_root / "deployment" / "MT5Agent.ico"

# Keep the MT5 API and its native dependencies confined to this separately
# launched interactive-session executable. The Agent service bundle excludes
# both packages by design.
analysis = Analysis(
    [str(project_root / "agent" / "infrastructure" / "interactive_mt5_worker.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=copy_metadata("MetaTrader5"),
    hiddenimports=[
        "MetaTrader5", "numpy", "win32timezone", "win32api", "win32con",
        "win32file", "win32pipe", "win32security", "win32process", "win32event", "win32ts",
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=[], noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, analysis.binaries, analysis.datas, [],
    name=f"MT5AgentWorker-v{version}", icon=str(icon_path), debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False,
)
