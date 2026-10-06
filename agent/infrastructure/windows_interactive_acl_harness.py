"""Fail-closed, reversible DACL experiment for ADR-001.

This module is deliberately not a general ACL editor.  Its public transaction
requires the existing local session policy and can only be invoked by the
dedicated CI gate.  It snapshots the *DACL security descriptor* before making
one additive ACE and restores that exact descriptor in ``finally``.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import win32api
import win32con
import win32event
import win32process
import win32security
import win32service
import win32ts

from agent.infrastructure.windows_worker_launcher import (
    ControlledWorkerLauncher,
    WorkerSessionPolicy,
    select_worker_session,
    discover_sessions,
)

_DACL = win32security.DACL_SECURITY_INFORMATION
_LOGON_SID = win32con.SE_GROUP_LOGON_ID
_BROAD_SIDS = {"S-1-1-0", "S-1-5-11", "S-1-5-32-544", "S-1-5-32-545"}
# These are the object-specific rights used by an interactive GUI client.  They
# intentionally exclude WRITE_DAC/WRITE_OWNER, station exit, hooks and journaling.
_WINSTA_LAUNCH_RIGHTS = (0x0001 | 0x0002 | 0x0004 | 0x0008 | 0x0010 | 0x0020 | 0x0100 | 0x0200)
_DESKTOP_LAUNCH_RIGHTS = (0x0001 | 0x0002 | 0x0004 | 0x0040 | 0x0080 | 0x0100)


class RollbackVerificationError(RuntimeError):
    """The target DACL was not restored byte-for-byte in its reported form."""


@dataclass(frozen=True)
class DescriptorSnapshot:
    object_name: str
    sddl: str
    sha256: str

    @classmethod
    def capture(cls, object_name: str, handle: Any) -> "DescriptorSnapshot":
        descriptor = win32security.GetUserObjectSecurity(handle, _DACL)
        sddl = win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(
            descriptor, 1, _DACL
        )
        return cls(object_name, sddl, hashlib.sha256(sddl.encode("utf-8")).hexdigest())

    def descriptor(self):
        return win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
            self.sddl, 1
        )


def selected_logon_sid(session_id: int):
    """Return only the exact logon SID for the selected WTS session token."""
    token = win32ts.WTSQueryUserToken(session_id)
    try:
        for sid, attributes in win32security.GetTokenInformation(token, win32security.TokenGroups):
            if attributes & _LOGON_SID == _LOGON_SID:
                return sid
    finally:
        token.Close()
    raise RuntimeError("TARGET_LOGON_SID_UNAVAILABLE")


def append_allow_ace(snapshot: DescriptorSnapshot, sid, rights: int) -> str:
    """Construct a single additive allow ACE without accepting broad identities."""
    sid_text = win32security.ConvertSidToStringSid(sid)
    if sid_text.upper() in _BROAD_SIDS:
        raise RuntimeError("BROAD_PRINCIPAL_GRANT_FORBIDDEN")
    if not snapshot.sddl.startswith("D:") or rights <= 0:
        raise RuntimeError("INVALID_DACL_OR_RIGHTS")
    return f"{snapshot.sddl}(A;;0x{rights:x};;;{sid_text})"


def apply_additive_ace(handle: Any, snapshot: DescriptorSnapshot, sid, rights: int) -> DescriptorSnapshot:
    updated = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
        append_allow_ace(snapshot, sid, rights), 1
    )
    win32security.SetUserObjectSecurity(handle, _DACL, updated)
    return DescriptorSnapshot.capture(snapshot.object_name, handle)


def restore_exact(handle: Any, original: DescriptorSnapshot) -> None:
    win32security.SetUserObjectSecurity(handle, _DACL, original.descriptor())
    restored = DescriptorSnapshot.capture(original.object_name, handle)
    if restored.sddl != original.sddl or restored.sha256 != original.sha256:
        raise RollbackVerificationError(f"ACL_ROLLBACK_VERIFICATION_FAILED:{original.object_name}")


def _assert_runner_context() -> None:
    if socket.gethostname().casefold() != "window10-test":
        raise RuntimeError("ACL_EXPERIMENT_HOST_NOT_AUTHORIZED")
    current = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        sid = win32security.GetTokenInformation(current, win32security.TokenUser)[0]
        name, domain, _ = win32security.LookupAccountSid(None, sid)
    finally:
        current.Close()
    if f"{domain}\\{name}".casefold() != "nt authority\\system":
        raise RuntimeError("ACL_EXPERIMENT_CALLER_NOT_LOCALSYSTEM")
    import ctypes
    session = ctypes.c_uint32()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(session)) or session.value != 0:
        raise RuntimeError("ACL_EXPERIMENT_CALLER_NOT_SESSION_ZERO")


def run_acl_launch_experiment(worker_entry: Path, evidence_path: Path) -> dict[str, object]:
    """Run the only permitted mutation transaction and always restore both DACLs.

    A LocalSystem process is in session zero and cannot safely name a user
    session's ``winsta0``.  It first starts an allowlisted helper *without an
    interactive desktop*.  That helper is created with the selected user token,
    so its object namespace is the selected session; it owns the DACL
    transaction.  The service remains the actor that performs the subsequent
    interactive ``CreateProcessAsUser`` gate.
    """
    _assert_runner_context()
    policy = WorkerSessionPolicy.from_environment()
    selected = select_worker_session(policy, discover_sessions())
    control = evidence_path.with_suffix(".control.json")
    ready = evidence_path.with_suffix(".ready.json")
    for path in (control, ready, evidence_path):
        path.unlink(missing_ok=True)
    token = win32ts.WTSQueryUserToken(selected.session_id)
    command = f'"{sys.executable}" -m agent.infrastructure.windows_interactive_acl_harness --helper "{evidence_path}" "{control}" "{ready}" {selected.session_id}'
    try:
        process, thread, _, _ = win32process.CreateProcessAsUser(
            token, None, command, None, None, False, win32con.CREATE_NO_WINDOW,
            None, str(Path(__file__).resolve().parents[2]), win32process.STARTUPINFO(),
        )
    finally:
        token.Close()
    try:
        deadline = time.monotonic() + 45
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        if not ready.exists():
            raise RuntimeError("ACL_HELPER_NOT_READY")
        ready_data = json.loads(ready.read_text(encoding="utf-8"))
        if ready_data.get("session_id") != selected.session_id or not ready_data.get("mutated"):
            raise RuntimeError("ACL_HELPER_SAFETY_FAILURE")
        launcher = ControlledWorkerLauncher(worker_entry)
        worker = launcher.start_for_local_policy(policy)
        try:
            import ctypes
            actual = ctypes.c_uint32()
            if not ctypes.windll.kernel32.ProcessIdToSessionId(worker.pid, ctypes.byref(actual)) or actual.value != selected.session_id:
                raise RuntimeError("WORKER_SESSION_MISMATCH")
            try:
                launcher.start_for_local_policy(policy)
            except RuntimeError as error:
                if "WORKER_ALREADY_RUNNING" not in str(error):
                    raise
            else:
                raise RuntimeError("DUPLICATE_WORKER_NOT_REJECTED")
            result = {"selected_session": selected.session_id, "worker": {"pid": worker.pid, "session_id": actual.value, "duplicate_rejected": True}}
        finally:
            result["worker_cleanup"] = launcher.stop()
        control.write_text(json.dumps({"complete": True}), encoding="utf-8")
    finally:
        thread.Close()
        win32event.WaitForSingleObject(process, 60000)
        process.Close()
    helper_result = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not helper_result.get("rollback_verified"):
        raise RollbackVerificationError("ACL_HELPER_ROLLBACK_NOT_VERIFIED")
    result["acl"] = helper_result
    return result


def _run_helper(evidence_path: Path, control: Path, ready: Path, expected_session: int) -> None:
    """Selected-session child: mutate only its own session's named objects."""
    import ctypes
    if socket.gethostname().casefold() != "window10-test":
        raise RuntimeError("ACL_HELPER_HOST_NOT_AUTHORIZED")
    current = ctypes.c_uint32()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(current)) or current.value != expected_session:
        raise RuntimeError("ACL_HELPER_SESSION_MISMATCH")
    policy = WorkerSessionPolicy.from_environment()
    if select_worker_session(policy, discover_sessions()).session_id != expected_session:
        raise RuntimeError("ACL_HELPER_POLICY_SESSION_MISMATCH")
    sid = selected_logon_sid(expected_session)
    winsta = win32service.OpenWindowStation("winsta0", False, win32con.READ_CONTROL | win32con.WRITE_DAC)
    desktop = win32service.OpenDesktop("default", 0, False, win32con.READ_CONTROL | win32con.WRITE_DAC | win32con.DESKTOP_READOBJECTS | win32con.DESKTOP_WRITEOBJECTS)
    originals: list[tuple[Any, DescriptorSnapshot]] = []
    result: dict[str, object] = {"session_id": expected_session, "mutated": False, "rollback_verified": False}
    try:
        originals = [(h, DescriptorSnapshot.capture(name, h)) for name, h in (("winsta0", winsta), ("default", desktop))]
        result["before"] = {s.object_name: s.sha256 for _, s in originals}
        result["after"] = {
            "winsta0": apply_additive_ace(winsta, originals[0][1], sid, _WINSTA_LAUNCH_RIGHTS).sha256,
            "default": apply_additive_ace(desktop, originals[1][1], sid, _DESKTOP_LAUNCH_RIGHTS).sha256,
        }
        result["mutated"] = True
        ready.write_text(json.dumps(result), encoding="utf-8")
        deadline = time.monotonic() + 60
        while not control.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        if not control.exists():
            raise RuntimeError("ACL_HELPER_CONTROL_TIMEOUT")
    finally:
        failures = []
        for handle, original in reversed(originals):
            try: restore_exact(handle, original)
            except Exception as error: failures.append(str(error))
        result["rollback_verified"] = not failures and len(originals) == 2
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(result, sort_keys=True, indent=2), encoding="utf-8")
        desktop.Close(); winsta.Close()
        if failures: raise RollbackVerificationError(";".join(failures))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--helper", action="store_true")
    parser.add_argument("evidence", type=Path)
    parser.add_argument("control", type=Path)
    parser.add_argument("ready", type=Path)
    parser.add_argument("session", type=int)
    args = parser.parse_args()
    if not args.helper: raise SystemExit("internal helper invocation required")
    _run_helper(args.evidence, args.control, args.ready, args.session)
