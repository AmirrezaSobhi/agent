"""Exercise release evidence checks in isolated repositories; never launch MT5."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from agent import __version__


ROOT = Path(__file__).resolve().parents[1]
PWSH = shutil.which("pwsh")
requires_ci_tools = pytest.mark.skipif(
    not PWSH or not shutil.which("git"), reason="Requires pwsh and git"
)


def _archive_forbidden_patterns():
    """Read the exact matcher patterns used against pyi-archive_viewer output."""
    script = (ROOT / "deployment/ci.ps1").read_text(encoding="utf-8")
    block = re.search(r"\$forbiddenPatterns\s*=\s*@\((.*?)\n\s*\)", script, re.S)
    assert block, "Archive matcher pattern list is missing"
    patterns = re.findall(r"^\s*'([^']+)'\s*,?\s*$", block.group(1), re.M)
    assert len(patterns) == 5
    return [re.compile(pattern) for pattern in patterns]


def test_clean_pyinstaller_archive_listing_has_no_forbidden_modules():
    patterns = _archive_forbidden_patterns()
    listing = """Contents of 'MT5Agent.exe' (PKG/CArchive):
 0, 100, 100, 1, 'm', 'agent.adapters.runtime_worker_mt5_adapter'
 1, 200, 200, 1, 'm', 'agent.application.diagnostics'
 2, 300, 300, 1, 'm', 'agent.infrastructure.windows_named_pipe'
"""
    assert not [match.group(0) for pattern in patterns for match in pattern.finditer(listing)]


@pytest.mark.parametrize("entry", [
    " 0, 100, 100, 1, 'm', 'MetaTrader5'",
    " 0, 100, 100, 1, 'm', 'numpy.core.multiarray'",
    " 0, 100, 100, 1, 'm', 'agent.adapters.mt5_adapter'",
    " 0, 100, 100, 1, 'm', 'agent.infrastructure.interactive_mt5_worker'",
    " 0, 100, 100, 1, 'm', 'agent.infrastructure.terminal_inspection'",
])
def test_pyinstaller_archive_listing_rejects_each_prohibited_module(entry):
    patterns = _archive_forbidden_patterns()
    listing = f"Contents of 'MT5Agent.exe' (PKG/CArchive):\n{entry}\n"
    assert [match.group(0) for pattern in patterns for match in pattern.finditer(listing)]


def test_archive_gate_inspects_modules_inside_embedded_pyz(tmp_path):
    from PyInstaller.archive.writers import CArchiveWriter, ZlibArchiveWriter
    import sys

    # Prohibited pure-Python modules are stored inside PYZ, not the outer TOC.
    names = ["MetaTrader5", "numpy", "agent.adapters.mt5_adapter",
             "agent.infrastructure.interactive_mt5_worker",
             "agent.infrastructure.terminal_inspection"]
    source = tmp_path / "inert.py"
    source.write_text("pass\n")
    pyz = tmp_path / "PYZ.pyz"
    ZlibArchiveWriter(str(pyz), [(name, str(source), "PYMODULE") for name in names],
                      {name: compile("pass", str(source), "exec") for name in names})
    archive = tmp_path / "inert.pkg"
    CArchiveWriter(str(archive), [("PYZ.pyz", str(pyz), False, "z")], "python.dll")
    script = (ROOT / "deployment/ci.ps1").read_text(encoding="utf-8")
    options = re.search(r"& \$archiveViewer\s+([^$]+)\$exePath", script).group(1).split()
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller.utils.cliutils.archive_viewer", *options, str(archive)],
        text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    for pattern in _archive_forbidden_patterns():
        assert pattern.search(result.stdout), "Embedded prohibited module escaped archive inspection"


@pytest.fixture
def checkout(tmp_path):
    (tmp_path / "deployment").mkdir()
    (tmp_path / "agent").mkdir()
    (tmp_path / "dist").mkdir()
    (tmp_path / "reports").mkdir()
    shutil.copyfile(ROOT / "deployment/ci.ps1", tmp_path / "deployment/ci.ps1")
    shutil.copyfile(ROOT / "agent/__init__.py", tmp_path / "agent/__init__.py")

    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()

    git("init", "-q")
    git("add", ".")
    git("-c", "user.name=CI Test", "-c", "user.email=ci@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
    commit = git("rev-parse", "HEAD")
    filename = f"MT5Agent-v{__version__}.exe"
    binary = tmp_path / "dist" / filename
    binary.write_bytes(b"inert fixture, not an executable")
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    common = {
        "schema_version": "1",
        "pipeline_id": "123",
        "commit_sha": commit,
        "candidate_version": __version__,
        "candidate_filename": filename,
        "candidate_sha256": digest,
    }
    build = dict(
        common,
        source_commit=commit,
        executable=filename,
        version=__version__,
        sha256=digest,
        candidate_size=len(binary.read_bytes()),
        python_version="3.14.4",
        metatrader5_present_in_build_environment=False,
        numpy_present_in_build_environment=False,
        archive_inspection_success=True,
        archive_forbidden_module_matches=[],
    )
    (tmp_path / "reports/build.json").write_text(json.dumps(build))
    (tmp_path / "reports/control-plane.json").write_text(json.dumps(dict(
        common, test="control-plane-degraded-startup", status="PASS",
        health="AGENT_RUNNING_DEGRADED", runtime_state="RUNTIME_UNAVAILABLE", worker_available=False,
    )))
    (tmp_path / "reports/mt5-runtime.json").write_text(json.dumps(dict(
        common,
        status="PASS",
        candidate_sha256_after=digest,
        runtime_state="MT5_CONNECTED",
        final_health="AGENT_RUNNING + MT5_CONNECTED",
        symbols_total_success=True,
        terminal_version_success=True,
        account_information_success=True,
        account_information_field_count=8,
        agent={"session_id": 0},
        worker={"principal": "HOST\\MT5RuntimeUser", "sid": "S-1-5-21-1", "session_id": 1, "protocol_version": "1"},
        terminal={"principal": "HOST\\MT5RuntimeUser", "sid": "S-1-5-21-1", "session_id": 1},
    )))
    env = {k: v for k, v in os.environ.items() if not k.startswith("CI_") and k != "ARTIFACT_NAME"}
    env.update(CI_COMMIT_SHA=commit, CI_PIPELINE_ID="123")
    return tmp_path, env


def run_task(checkout, task, **variables):
    path, env = checkout
    return subprocess.run(
        [PWSH, "-NoProfile", "-File", str(path / "deployment/ci.ps1"), "-Task", task],
        env=dict(env, **variables),
        text=True,
        capture_output=True,
        timeout=30,
    )


@requires_ci_tools
def test_metadata_accepts_matching_tag(checkout):
    result = run_task(checkout, "metadata", CI_COMMIT_TAG=f"v{__version__}")
    assert result.returncode == 0, result.stderr
    assert f"MT5Agent-v{__version__}.exe" in result.stdout


@requires_ci_tools
@pytest.mark.parametrize("variables", [
    {"CI_COMMIT_TAG": "v9.9.9"}, {"CI_COMMIT_SHA": "0" * 40},
])
def test_metadata_rejects_wrong_tag_or_commit(checkout, variables):
    assert run_task(checkout, "metadata", **variables).returncode != 0


@requires_ci_tools
def test_package_preserves_single_validated_binary(checkout):
    path, _ = checkout
    binary = path / f"dist/MT5Agent-v{__version__}.exe"
    before = binary.read_bytes()
    result = run_task(checkout, "package")
    assert result.returncode == 0, result.stderr
    assert binary.read_bytes() == before
    digest = hashlib.sha256(before).hexdigest()
    assert (path / "sha256.txt").read_text(encoding="utf-8-sig").strip() == f"SHA256={digest}"
    release = json.loads((path / "reports/release-evidence.json").read_text(encoding="utf-8-sig"))
    assert release["candidate_sha256"] == digest
    assert release["build_once"] is True
    assert release["post_smoke_rebuild"] is False
    assert release["release_eligible"] is True


@requires_ci_tools
@pytest.mark.parametrize("receipt, field, value", [
    ("build", "commit_sha", "stale"),
    ("build", "pipeline_id", "other-pipeline"),
    ("build", "candidate_version", "0.0.0"),
    ("build", "candidate_sha256", "tampered"),
    ("build", "metatrader5_present_in_build_environment", True),
    ("build", "numpy_present_in_build_environment", True),
    ("build", "archive_forbidden_module_matches", ["numpy"]),
    ("control-plane", "candidate_sha256", "tampered"),
    ("control-plane", "status", "FAIL"),
    ("control-plane", "worker_available", True),
    ("mt5-runtime", "commit_sha", "stale"),
    ("mt5-runtime", "pipeline_id", "other-pipeline"),
    ("mt5-runtime", "candidate_sha256_after", "tampered"),
    ("mt5-runtime", "account_information_success", False),
    ("mt5-runtime", "terminal", {"principal": "HOST\\MT5RuntimeUser", "sid": "S-1-5-21-1", "session_id": 2}),
])
def test_package_rejects_mismatched_or_incomplete_evidence(checkout, receipt, field, value):
    path, _ = checkout
    name = "build.json" if receipt == "build" else f"{receipt}.json"
    receipt_path = path / "reports" / name
    evidence = json.loads(receipt_path.read_text())
    evidence[field] = value
    receipt_path.write_text(json.dumps(evidence))
    result = run_task(checkout, "package")
    assert result.returncode != 0
    assert not (path / "sha256.txt").exists()


@requires_ci_tools
@pytest.mark.parametrize("name", ["control-plane.json", "mt5-runtime.json"])
def test_package_requires_both_runtime_gates(checkout, name):
    path, _ = checkout
    (path / "sha256.txt").write_text("stale checksum")
    (path / "reports" / name).unlink()
    result = run_task(checkout, "package")
    assert result.returncode != 0
    assert not (path / "sha256.txt").exists()


@requires_ci_tools
@pytest.mark.skipif(os.name != "nt", reason="Windows principal SID translation")
@pytest.mark.parametrize("principal_form, logon_type, enabled, state, valid", [
    ("short", 3, True, "Running", True),
    ("qualified", 3, True, "Running", True),
    ("sid", 3, True, "Running", True),
    ("wrong_sid", 3, True, "Running", False),
    ("short", 4, True, "Running", False),
    ("short", 1, True, "Running", False),
    ("short", 3, False, "Running", False),
    ("short", 3, True, "Ready", False),
])
def test_worker_task_preflight_matches_sid_and_exact_interactive_logon(
    checkout, principal_form, logon_type, enabled, state, valid
):
    path, env = checkout
    script = path / "task-preflight.ps1"
    script.write_text(f"""
. '{path / 'deployment/ci.ps1'}' -Task metadata
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = $identity.Name
$sid = $identity.User.Value
$short = ($principal -split '\\\\')[-1]
$taskUser = switch ('{principal_form}') {{
    'short' {{ $short }}
    'qualified' {{ $principal }}
    'sid' {{ $sid }}
    'wrong_sid' {{ if ($sid -eq 'S-1-5-18') {{ 'S-1-5-19' }} else {{ 'S-1-5-18' }} }}
}}
function Get-Process {{ [pscustomobject]@{{SessionId=0}} }}
function Get-ScheduledTask {{ [pscustomobject]@{{
    State='{state}'; Settings=[pscustomobject]@{{Enabled=${str(enabled).lower()}}}
    Principal=[pscustomobject]@{{UserId=$taskUser;LogonType={logon_type}}}
}} }}
$config = [pscustomobject]@{{RuntimePrincipal=$principal;ControlPrincipal=$principal}}
$inspection = [pscustomobject]@{{runtime=[pscustomobject]@{{
    worker_available=$true;protocol_version='1';control_session_id=0
    runtime_state='MT5_NOT_INITIALIZED'
    worker_identity=[pscustomobject]@{{account=$principal;sid=$sid;session_id=1;pid=10;protocol_version='1'}}
}}}}
try {{ $null=Assert-WorkerTaskAndPreflight -RuntimeConfiguration $config -Inspection $inspection }}
catch {{ Write-Output 'PRECONDITION_REJECTED'; exit 1 }}
Write-Output 'PRECONDITION_ACCEPTED'
""", encoding="utf-8")
    result = subprocess.run([PWSH, "-NoProfile", "-File", str(script)],
                            env=env, text=True, capture_output=True, timeout=30)
    assert (result.returncode == 0) == valid, result.stdout + result.stderr
    assert ("PRECONDITION_ACCEPTED" if valid else "PRECONDITION_REJECTED") in result.stdout


@requires_ci_tools
@pytest.mark.parametrize("payload, expected", [("{}", 0), ('{"field_one":null,"field_two":null}', 2)])
def test_runtime_account_field_count_handles_json_objects_under_strict_mode(tmp_path, payload, expected):
    script_source = (ROOT / "deployment/ci.ps1").read_text(encoding="utf-8")
    expression = re.search(r"\$accountFieldCount = (.*PSObject.Properties.*)", script_source).group(1)
    script = tmp_path / "field-count.ps1"
    script.write_text("Set-StrictMode -Version Latest\n" +
                      f"$account = [pscustomobject]@{{data=[pscustomobject]@{{result=('{payload}' | ConvertFrom-Json)}}}}\n" +
                      f"$accountFieldCount = {expression}\nWrite-Output $accountFieldCount\n", encoding="utf-8")
    result = subprocess.run([PWSH, "-NoProfile", "-File", str(script)],
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(expected)
