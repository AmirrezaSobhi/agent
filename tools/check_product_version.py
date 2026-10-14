"""Validate metadata mirrors against agent.__version__, the release authority."""
from pathlib import Path
import ast
import re
import sys


def product_version(root: Path) -> str:
    tree = ast.parse((root / 'agent/__init__.py').read_text(encoding='utf-8'))
    values = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == '__version__' for t in node.targets)
              and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)]
    if len(values) != 1 or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', values[0], re.ASCII):
        raise ValueError('Canonical release version must be one stable semantic version')
    return values[0]


def validate(root: Path) -> str:
    version = product_version(root)
    contracts = {
        'deployment/service/Program.cs': [f'AgentExecutableName = "MT5Agent-v{version}.exe"'],
        'deployment/service.tests/Program.cs': [f'AgentName = "MT5Agent-v{version}.exe"'],
        'deployment/service/AssemblyInfo.cs': [f'AssemblyVersion("{version}.0")', f'AssemblyFileVersion("{version}.0")'],
        'deployment/Register-PackagedMT5Worker.ps1': [f"Worker\\MT5AgentWorker-v{version}.exe"],
        'src/desktop/MT5Agent.Desktop/Properties/AssemblyInfo.cs': [f'AssemblyVersion("{version}.0")', f'AssemblyFileVersion("{version}.0")'],
        'src/desktop/MT5Agent.Desktop/Properties/app.manifest': [f'assemblyIdentity version="{version}.0"'],
        '.gitlab-ci.yml': [f'MT5Agent-Setup-v{version}-windows-x64.exe',f'MT5Agent-Desktop-v{version}-windows-x64.zip'],
    }
    for path, expected in contracts.items():
        text = (root / path).read_text(encoding='utf-8')
        if any(value not in text for value in expected):
            raise ValueError(f'Release version/path contract drift: {path}')
    return version


if __name__ == '__main__':
    try:
        print(validate(Path(__file__).resolve().parents[1]))
    except (OSError, SyntaxError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
