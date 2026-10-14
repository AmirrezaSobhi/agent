import ctypes
import os
import socket
import subprocess
from pathlib import Path

import pytest
import win32api
import win32con
import win32security
import win32ts

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows launcher")

from agent.infrastructure.windows_worker_launcher import (
    ControlledWorkerLauncher,
    DiscoveredSession,
    WorkerSessionPolicy,
    discover_sessions,
    interactive_startup_info,
    select_worker_session,
)
from agent.infrastructure.windows_interactive_acl_harness import (
    DescriptorSnapshot,
    RollbackVerificationError,
    append_allow_ace,
    restore_exact,
    run_acl_launch_experiment,
    selected_logon_sid,
)


def test_launcher_tracks_owned_current_session_process_and_rejects_duplicate():
    launcher = ControlledWorkerLauncher(Path(__file__).parent / "fixtures" / "worker_sleeper.py")
    worker = launcher.start()
    try:
        current = ctypes.c_uint32()
        assert ctypes.windll.kernel32.ProcessIdToSessionId(
            os.getpid(), ctypes.byref(current)
        )
        assert worker.pid > 0
        assert worker.session_id == current.value
        with pytest.raises(RuntimeError, match="ALREADY"):
            launcher.start()
    finally:
        assert launcher.stop()


def test_session_selection_rejects_missing_or_wrong_local_principal_without_token_call():
    policy = WorkerSessionPolicy("MANI-PC\\Administrator")
    with pytest.raises(RuntimeError, match="SESSION_NOT_FOUND"):
        select_worker_session(policy, ())
    wrong_principal = DiscoveredSession(
        session_id=2,
        state="ACTIVE",
        session_name="Console",
        principal="MANI-PC\\OtherUser",
        is_session_zero=False,
        candidate=True,
        rejection_reason=None,
    )
    with pytest.raises(RuntimeError, match="SESSION_PRINCIPAL_MISMATCH"):
        select_worker_session(policy, (wrong_principal,))


def test_interactive_startup_targets_the_default_user_desktop():
    assert interactive_startup_info().lpDesktop == r"winsta0\default"


def test_acl_ace_is_additive_and_rejects_broad_principals(monkeypatch):
    snapshot = DescriptorSnapshot("default", "D:(A;;0x1;;;S-1-5-21-1)", "digest")
    monkeypatch.setattr(win32security, "ConvertSidToStringSid", lambda _: "S-1-5-5-1-2")
    assert append_allow_ace(snapshot, object(), 0x42).endswith("(A;;0x42;;;S-1-5-5-1-2)")
    monkeypatch.setattr(win32security, "ConvertSidToStringSid", lambda _: "S-1-1-0")
    with pytest.raises(RuntimeError, match="BROAD_PRINCIPAL"):
        append_allow_ace(snapshot, object(), 0x42)


def test_restore_exact_verifies_the_captured_descriptor(monkeypatch):
    snapshot = DescriptorSnapshot("default", "D:(A;;0x1;;;S-1-5-21-1)", "digest")
    monkeypatch.setattr("agent.infrastructure.windows_interactive_acl_harness.win32security.SetUserObjectSecurity", lambda *_: None)
    monkeypatch.setattr("agent.infrastructure.windows_interactive_acl_harness.DescriptorSnapshot.capture", lambda *_: snapshot)
    restore_exact(object(), snapshot)
    monkeypatch.setattr("agent.infrastructure.windows_interactive_acl_harness.DescriptorSnapshot.capture", lambda *_: DescriptorSnapshot("default", "D:(A;;0x2;;;S-1-5-21-1)", "other"))
    with pytest.raises(RollbackVerificationError, match="ROLLBACK"):
        restore_exact(object(), snapshot)


def test_selected_logon_sid_uses_verified_interactive_process_token(monkeypatch):
    expected_sid = object()
    token = type("Token", (), {"Close": lambda self: None})()
    monkeypatch.setattr(
        "agent.infrastructure.windows_interactive_acl_harness._process_session_id",
        lambda _pid: 7,
    )
    monkeypatch.setattr(win32api, "GetCurrentProcess", lambda: 123)
    monkeypatch.setattr(win32security, "OpenProcessToken", lambda *_: token)
    monkeypatch.setattr(
        win32security,
        "GetTokenInformation",
        lambda _token, token_class: (
            ("user-sid",)
            if token_class == win32security.TokenUser
            else (("ordinary-group", 0), (expected_sid, win32con.SE_GROUP_LOGON_ID))
        ),
    )
    monkeypatch.setattr(
        win32security,
        "LookupAccountSid",
        lambda *_: ("Administrator", "window10-test", 0),
    )

    assert selected_logon_sid(7, "window10-test\\Administrator") is expected_sid


def _runner_service_identity() -> str:
    """Read the service account without changing Runner configuration."""
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "(Get-CimInstance Win32_Service -Filter \"Name='gitlab-runner'\").StartName",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_authorized_window10_test_session_zero_prerequisites():
    """Fail closed before any future Window Station/Desktop ACL experiment."""
    if os.environ.get("MT5_AGENT_ACL_EXPERIMENT") != "1":
        pytest.skip("dedicated ACL experiment gate only")
    assert socket.gethostname().casefold() == "window10-test"
    assert _runner_service_identity().casefold() == "localsystem"

    current_session = ctypes.c_uint32()
    assert ctypes.windll.kernel32.ProcessIdToSessionId(
        os.getpid(), ctypes.byref(current_session)
    )
    assert current_session.value == 0

    process = win32api.GetCurrentProcess()
    process_token = win32security.OpenProcessToken(process, win32security.TOKEN_QUERY)
    try:
        caller_sid = win32security.GetTokenInformation(
            process_token, win32security.TokenUser
        )[0]
        caller_name, caller_domain, _ = win32security.LookupAccountSid(None, caller_sid)
    finally:
        process_token.Close()
    assert f"{caller_domain}\\{caller_name}".casefold() == "nt authority\\system"

    policy = WorkerSessionPolicy.from_environment()
    assert policy.principal.casefold() == "window10-test\\administrator"
    selected = select_worker_session(policy, discover_sessions())
    assert selected.session_id != 0
    assert selected.state == "ACTIVE"

    target_token = win32ts.WTSQueryUserToken(selected.session_id)
    try:
        target_sid = win32security.GetTokenInformation(
            target_token, win32security.TokenUser
        )[0]
        target_name, target_domain, _ = win32security.LookupAccountSid(None, target_sid)
    finally:
        target_token.Close()
    assert f"{target_domain}\\{target_name}".casefold() == policy.principal.casefold()
    print(
        "ACL_PRECHECK passed "
        f"host=WINDOW10-TEST caller=LocalSystem session=0 "
        f"target_session={selected.session_id} target_principal={policy.principal} "
        "target_sid_resolved=true"
    )


def test_session_zero_can_launch_owned_worker_in_designated_interactive_session():
    if os.environ.get("MT5_AGENT_ACL_EXPERIMENT") != "1":
        pytest.skip("dedicated ACL experiment gate only")
    current = ctypes.c_uint32()
    ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(current))
    if current.value != 0:
        pytest.skip("cross-session evidence runs from service/session 0 only")
    policy = WorkerSessionPolicy.from_environment()
    result = run_acl_launch_experiment(
        Path(__file__).parent / "fixtures" / "worker_sleeper.py",
        Path("reports") / "interactive-acl-launch.json",
    )
    assert result["worker"]["session_id"] != 0
    assert result["worker"]["duplicate_rejected"] is True
    assert result["worker_cleanup"] is True
    assert result["acl"]["rollback_verified"] is True
