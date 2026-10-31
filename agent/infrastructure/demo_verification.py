"""Type-only observation for an authenticated local management caller."""
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from agent.application.boundary import ApplicationBoundary
from agent.application.identity import IdentityAuthority
from agent.application.dispatcher import CommandDispatcher
from agent.application.mt5_read_commands import build_demo_status_handler
from agent.contracts.models import Command
from agent.contracts.transport import ExecutionContext
from agent.infrastructure.account_snapshot import ReadRequest


class DemoVerifier:
    def __init__(self, adapter):
        dispatcher = CommandDispatcher()
        dispatcher.register("mt5.get_account_demo_status", build_demo_status_handler(adapter))
        self._token = secrets.token_urlsafe(32)
        authority = IdentityAuthority()
        authority.enroll("local-management-demo-verifier", self._token,
                         {"command:mt5.get_account_demo_status"})
        self.boundary = ApplicationBoundary(dispatcher, authority, authority)

    def observe(self):
        correlation = str(uuid4())
        command = Command(str(uuid4()), "mt5.get_account_demo_status", "1", correlation,
                          datetime.now(timezone.utc).isoformat(), {})
        response = self.boundary.handle(ReadRequest(
            ExecutionContext(str(uuid4()), correlation, {}), command, self._token))
        if response.success and isinstance(response.data, dict):
            result = response.data.get("result")
            if isinstance(result, dict):
                value = result.get("demo_verified")
                if type(value) is bool or value == "unknown":
                    return {"demo_verified": value}
        return {"demo_verified": "unknown"}
