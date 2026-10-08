"""Read-only Management Pipe probe for isolated Windows Phase 5 validation."""

from __future__ import annotations

import json
import os
import statistics
import time
import uuid
import math

if os.name != "nt":
    raise SystemExit("Windows only")

import win32api
import win32con
import win32file
import win32pipe
import win32security


PIPE = r"\\.\pipe\MT5Agent.Management.v1"


def caller_sid() -> str:
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        return win32security.ConvertSidToStringSid(
            win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        )
    finally:
        win32api.CloseHandle(token)


def request(operation: str = "status.get") -> tuple[dict[str, object], float]:
    started = time.perf_counter()
    request_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    envelope = {
        "protocol_version": 1,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "operation": operation,
        "deadline_utc": "2099-01-01T00:00:00Z",
        "payload": {"limit": 10, "severity": "ALL"} if operation == "logs.query" else {},
    }
    deadline = time.monotonic() + 2.0
    while True:
        try:
            handle = win32file.CreateFile(
                PIPE, win32con.GENERIC_READ | win32con.GENERIC_WRITE, 0, None,
                win32con.OPEN_EXISTING, 0, None,
            )
            break
        except Exception as exc:
            if getattr(exc, "winerror", None) not in (2, 231) or time.monotonic() >= deadline:
                raise
            time.sleep(0.05)
    try:
        win32pipe.SetNamedPipeHandleState(
            handle, win32pipe.PIPE_READMODE_MESSAGE, None, None
        )
        win32file.WriteFile(handle, json.dumps(envelope, separators=(",", ":")).encode("utf-8"))
        _, raw = win32file.ReadFile(handle, 65_537)
        response = json.loads(raw.decode("utf-8"))
        ack = json.dumps({"ack": response.get("request_id", "")}, separators=(",", ":")).encode("utf-8")
        win32file.WriteFile(handle, ack)
        return response, (time.perf_counter() - started) * 1000
    finally:
        win32api.CloseHandle(handle)


if __name__ == "__main__":
    result = {"caller_sid": caller_sid()}
    try:
        status_times = []
        final_status = None
        successful = 0
        for _ in range(30):
            final_status, elapsed = request()
            status_times.append(elapsed)
            successful += final_status.get("result") == "ok"
            time.sleep(0.05)
        log_times = []
        final_logs = None
        for _ in range(10):
            final_logs, elapsed = request("logs.query")
            log_times.append(elapsed)
            time.sleep(0.05)

        def summary(samples: list[float]) -> dict[str, float | int]:
            ordered = sorted(samples)
            p95 = ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]
            return {"n": len(ordered), "median_ms": round(statistics.median(ordered), 2),
                    "p95_ms": round(p95, 2), "min_ms": round(min(ordered), 2),
                    "max_ms": round(max(ordered), 2)}

        result["status_response"] = final_status
        result["logs_response"] = final_logs
        result["status_round_trip"] = summary(status_times)
        result["status_success_count"] = successful
        result["logs_query_round_trip"] = summary(log_times)
        result["outcome"] = "response_received"
    except Exception as exc:
        result["outcome"] = "connection_rejected"
        result["winerror"] = getattr(exc, "winerror", None)
        result["error_type"] = type(exc).__name__
    print(json.dumps(result, indent=2, sort_keys=True))
