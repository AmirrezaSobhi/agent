from dataclasses import dataclass
import os

from agent.adapters.http_transport import HTTPTransportAdapter
from agent.application.app import build_dispatcher
from agent.application.boundary import ApplicationBoundary
from agent.application.dispatcher import CommandDispatcher
from agent.application.host import ApplicationHost
from agent.application.registry.capability import InMemoryCapabilityRegistry
from agent.contracts.configuration import AgentConfig
from agent.contracts.runtime_information import RuntimeInformationContract
from agent.contracts.operational_observability import OperationalObservabilityPort
from agent.contracts.ports import AuthenticationPort, AuthorizationPort, HostingPort, MT5Port, ObservabilityPort
from agent.core.agent import Agent
from agent.infrastructure.http_server_host import HTTPServerHost
from agent.infrastructure.logging_observability import LoggingOperationalObservability
from agent.infrastructure.composite_host import CompositeHostingPort
from agent.infrastructure.management_named_pipe import ManagementNamedPipeServer, build_status


@dataclass(frozen=True)
class AgentComposition:
    config: AgentConfig
    agent: Agent
    dispatcher: CommandDispatcher
    application: ApplicationBoundary
    http_transport: HTTPTransportAdapter
    hosting: HostingPort
    management_pipe: ManagementNamedPipeServer
    host: ApplicationHost


def compose_agent(
    config: AgentConfig,
    mt5: MT5Port | None = None,
    authenticator: AuthenticationPort | None = None,
    authorizer: AuthorizationPort | None = None,
    observability: ObservabilityPort | None = None,
    hosting: HostingPort | None = None,
    operational_observability: OperationalObservabilityPort | None = None,
) -> AgentComposition:
    """Single composition root for concrete application dependencies."""
    selected_mt5 = mt5 if mt5 is not None else _default_mt5_adapter()
    agent = Agent(selected_mt5)

    capability_registry = InMemoryCapabilityRegistry(
        (),
        lambda: RuntimeInformationContract(
            agent_name=agent.identity.app_name,
            agent_version=agent.identity.version,
            schema_version="1",
            lifecycle_state=agent.state.value,
            capabilities=capability_registry.get_capabilities(),
        ),
    )
    dispatcher = build_dispatcher(agent, capability_provider=capability_registry, mt5_read_adapter=agent.mt5)

    application = ApplicationBoundary(dispatcher, authenticator, authorizer, observability)
    transport = HTTPTransportAdapter(application, max_request_bytes=config.http.max_request_bytes)
    http_hosting = hosting or HTTPServerHost(
        lambda: transport.create_server(config.http.host, config.http.port)
    )
    management_pipe = ManagementNamedPipeServer(
        lambda: build_status(agent), config.management.allowed_user_sids
    )
    concrete_hosting = (http_hosting if hosting is not None else
                        CompositeHostingPort(http_hosting, management_pipe))
    host = ApplicationHost(
        agent,
        concrete_hosting,
        operational_observability=(operational_observability if operational_observability is not None
                                   else LoggingOperationalObservability()),
    )
    return AgentComposition(config, agent, dispatcher, application, transport, concrete_hosting,
                            management_pipe, host)


def _default_mt5_adapter() -> MT5Port:
    """Select the split-session adapter for Windows production control planes."""
    if os.name == "nt":
        from agent.adapters.runtime_worker_mt5_adapter import PIPE_NAME, RuntimeWorkerMT5Adapter

        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\MT5Agent\Runtime") as key:
                principal = str(winreg.QueryValueEx(key, "RuntimePrincipal")[0]).strip()
                try:
                    pipe_name = str(winreg.QueryValueEx(key, "PipeName")[0]).strip()
                except FileNotFoundError:
                    pipe_name = PIPE_NAME
            if not principal:
                raise ValueError("RuntimePrincipal is empty")
            return RuntimeWorkerMT5Adapter(
                pipe_name=pipe_name,
                expected_worker_principal=principal,
                require_session_zero=True,
            )
        except Exception:
            # Missing machine configuration is a degraded runtime, not a reason
            # to terminate the Session 0 Agent before it can report health.
            return RuntimeWorkerMT5Adapter(
                configuration_error="RUNTIME_CONFIGURATION_UNAVAILABLE",
                require_session_zero=True,
            )
    # Direct in-process integration remains available for explicit local
    # development and non-Windows compatibility; it is never the Windows default.
    from agent.adapters.mt5_adapter import MT5Adapter

    return MT5Adapter()
