import json
import subprocess
import sys
from pathlib import Path
import pytest
from tools.check_product_version import product_version, validate
from agent import __version__

ROOT=Path(__file__).resolve().parents[1]


def test_product_version_cli_diagnostics_and_packaged_paths_agree():
    assert validate(ROOT)==__version__=='0.1.5'
    cli=subprocess.run([sys.executable,str(ROOT/'main.py'),'--version'],capture_output=True,text=True,timeout=10)
    assert cli.returncode==0 and cli.stdout.strip()==__version__
    diag=subprocess.run([sys.executable,str(ROOT/'main.py'),'--diagnose','--json'],capture_output=True,text=True,timeout=15)
    assert diag.returncode in (0,1)
    assert json.loads(diag.stdout)['agent_version']==__version__


@pytest.mark.parametrize('source',['__version__="01.1.5"','__version__="0.1.5-rc1"','__version__="0.1.5"\n__version__="0.1.3"'])
def test_invalid_or_ambiguous_canonical_version_rejected(tmp_path,source):
    (tmp_path/'agent').mkdir();(tmp_path/'agent/__init__.py').write_text(source)
    with pytest.raises(ValueError):product_version(tmp_path)
