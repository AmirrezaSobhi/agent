"""Guardrails for the temporary LocalSystem CI runtime-smoke task."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
COORDINATOR = (ROOT / "deployment/Invoke-MT5RuntimeSmokeAsSystem.ps1").read_text(encoding="utf-8")
SYSTEM_TASK = (ROOT / "deployment/Run-MT5RuntimeSmokeSystem.ps1").read_text(encoding="utf-8")
CI = (ROOT / "deployment/ci.ps1").read_text(encoding="utf-8")
PIPELINE = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")


def test_ci_smoke_uses_a_serialized_scheduled_task_with_a_fixed_entrypoint():
    job = re.search(r"(?ms)^smoke:mt5-runtime:\n(?P<body>.*?)(?=^\S|\Z)", PIPELINE)
    assert job
    body = job.group("body")
    assert "resource_group: mt5-runtime-smoke" in body
    assert "New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount" in COORDINATOR
    assert "-Task smoke-mt5-runtime-system" in SYSTEM_TASK
    assert "-Task $" not in COORDINATOR
    assert "-Command" not in COORDINATOR


def test_system_task_fails_closed_on_identity_session_and_runtime_policy():
    assert "$callerSid -cne 'S-1-5-18'" in SYSTEM_TASK
    assert "$callerSessionId -ne 0" in SYSTEM_TASK
    assert "$controlSid -cne 'S-1-5-18'" in SYSTEM_TASK
    assert "$runtimeSid -eq $controlSid" in COORDINATOR
    assert "ControlPrincipal" in COORDINATOR
    assert "Set-ItemProperty" not in COORDINATOR


def test_privileged_payload_is_committed_hash_checked_and_acl_protected():
    assert "Get-GitBlobHash" in COORDINATOR
    assert "Assert-CommittedFile -Path $ciPath" in COORDINATOR
    assert "Assert-CommittedFile -Path $taskPayloadPath" in COORDINATOR
    assert "Set-ProtectedDirectory -Path $stagePath" in COORDINATOR
    assert all(value in COORDINATOR for value in ("S-1-5-18", "S-1-5-32-544"))
    assert all(value in COORDINATOR for value in ("S-1-5-11", "S-1-5-32-545"))
    assert "context_sha256" not in SYSTEM_TASK  # the external protected receipt avoids self-hash ambiguity
    assert "task-context.sha256" in SYSTEM_TASK
    assert "Get-FileHash -LiteralPath $payloadPath" in SYSTEM_TASK
    assert "Assert-FileInventory -Root $desktopTestsSource" in COORDINATOR
    assert "$context.desktop_smoke_files" in SYSTEM_TASK
    assert "Staged Management test payload integrity check failed" in SYSTEM_TASK
    assert "management-ipc-build.json" in PIPELINE


def test_stale_results_timeouts_failed_exit_and_owned_resource_cleanup_are_checked():
    assert "Test-Path -LiteralPath $stagePath" in COORDINATOR
    assert "Stale System smoke result" in SYSTEM_TASK
    assert "TimeoutSeconds = 660" in COORDINATOR
    assert "Stop-ScheduledTask -TaskName $taskName" in COORDINATOR
    assert "$taskInfo.LastTaskResult -ne 0" in COORDINATOR
    assert "$taskCreated" in COORDINATOR
    assert "Unregister-ScheduledTask -TaskName $taskName" in COORDINATOR
    assert "Remove-Item -LiteralPath $stagePath -Recurse -Force" in COORDINATOR
    assert "Global\\MT5Agent.v0.1.5.RuntimeSmoke" in COORDINATOR


def test_ci_preserves_health_provenance_and_requires_matching_live_session():
    assert "type(session_id) is not int" in (ROOT / "agent/adapters/runtime_worker_mt5_adapter.py").read_text(encoding="utf-8")
    assert "$finalHealth.runtime.worker_session_id -ne $worker.session_id" in CI
    assert "$runtime.worker_session_id -ne $runtime.worker.session_id" in CI
    assert "smoke-mt5-runtime-system" in CI
