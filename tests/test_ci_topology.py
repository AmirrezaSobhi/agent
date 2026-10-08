"""Guard the three-lane release topology and artifact provenance edges."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _job_block(source: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^{re.escape(name)}:\n(.*?)(?=^[A-Za-z0-9_.:-]+:|\Z)",
        source,
    )
    assert match, f"Missing CI job {name}"
    return match.group(1)


def test_linux_source_job_isolated_and_excludes_windows_worker_module():
    source = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    job = _job_block(source, "test:linux")
    assert re.search(r"(?m)^  tags:\n    - linux-source-unit\s*$", job)
    assert "requirements-dev.txt" in job
    assert "--ignore=tests/test_windows_worker_launcher.py" in job
    assert "MetaTrader5" in job and "numpy" in job


def test_windows_jobs_use_distinct_control_and_runtime_runners():
    source = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    for name in ("build:windows", "smoke:invalid-configuration", "smoke:control-plane", "package:windows"):
        assert re.search(r"(?m)^  tags:\n    - windows-self-hosted-no-mt5\s*$", _job_block(source, name))
    runtime = _job_block(source, "smoke:mt5-runtime")
    assert re.search(r"(?m)^  tags:\n    - windows-self-hosted-mt5\s*$", runtime)
    assert "smoke:control-plane" in runtime


def test_release_edges_preserve_one_artifact_and_drop_acl_experiment_dependency():
    source = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    build = _job_block(source, "build:windows")
    package = _job_block(source, "package:windows")
    assert "test:linux" in build and "test:windows" in build
    assert "smoke:mt5-runtime" in package
    assert "reports/release-evidence.json" in package
    assert "test:interactive-acl-launch" not in source
    assert "smoke:inspect-terminal" not in source
    assert "smoke:terminal-unavailable" not in source
    assert "probe:mt5-runtime" not in source


def test_desktop_package_is_built_once_and_verified_as_the_tested_artifact():
    source = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    assert "  - desktop_build\n  - test" in source
    build = _job_block(source, "desktop:build-package")
    tests = _job_block(source, "test:wpf-management")
    verify = _job_block(source, "desktop:package-verify")
    assert build.count("/t:Rebuild") == 1
    assert "New-DesktopPackage.ps1" in build
    assert "job: desktop:build-package\n      artifacts: true" in tests
    assert "MT5Agent.Desktop.sln" not in tests
    assert "/t:Rebuild" not in tests
    assert "job: desktop:build-package\n      artifacts: true" in verify
    assert "Test-DesktopPackage.ps1" in verify
    assert "ExpectedCommit $env:CI_COMMIT_SHA" in verify
    assert "ExpectedPipelineId $env:CI_PIPELINE_ID" in verify
    assert "Desktop build omitted required output" in build
    assert "packageReport.package_sha256" in build
    package_builder = (ROOT / "deployment/desktop/New-DesktopPackage.ps1").read_text(encoding="utf-8")
    package_verifier = (ROOT / "deployment/desktop/Test-DesktopPackage.ps1").read_text(encoding="utf-8")
    assert "$workingDirectory = (Get-Location).ProviderPath" in package_builder
    assert "$workingDirectory = (Get-Location).ProviderPath" in package_verifier
    assert "Join-Path $workingDirectory $OutputDirectory" in package_builder
    assert "Join-Path $workingDirectory $ExtractionDirectory" in package_verifier


def test_workflow_branch_and_tag_rules_remain_intact():
    source = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    assert "CI_COMMIT_TAG =~ /^v" in source
    assert "CI_PIPELINE_SOURCE == \"merge_request_event\"" in source
    assert "develop|staging|main" in source
