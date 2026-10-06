import builtins
import importlib.abc
import sys

import pytest


class _RejectMetaTrader5(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "MetaTrader5" or fullname.startswith("MetaTrader5."):
            raise ModuleNotFoundError("MetaTrader5 intentionally unavailable in Agent test")
        return None


@pytest.fixture
def mt5_unavailable(monkeypatch):
    saved = sys.modules.pop("MetaTrader5", None)
    finder = _RejectMetaTrader5()
    sys.meta_path.insert(0, finder)
    yield
    sys.meta_path.remove(finder)
    if saved is not None:
        sys.modules["MetaTrader5"] = saved


def test_production_composition_starts_degraded_without_meta_package(monkeypatch, mt5_unavailable):
    import agent.composition as composition
    from agent.contracts.configuration import AgentConfig
    from agent.adapters.runtime_worker_mt5_adapter import RuntimeWorkerMT5Adapter

    monkeypatch.setattr(composition.os, "name", "nt")
    composed = composition.compose_agent(AgentConfig())

    assert isinstance(composed.agent.mt5, RuntimeWorkerMT5Adapter)
    started = composed.agent.start()
    assert started.ok and started.code == "started_degraded"
    health = composed.agent.health()
    assert health.ok is False
    assert health.runtime_state == "RUNTIME_UNAVAILABLE"
    assert "MetaTrader5" not in sys.modules


def test_runtime_adapter_imports_without_meta_package(mt5_unavailable):
    from agent.adapters.runtime_worker_mt5_adapter import RuntimeWorkerMT5Adapter

    assert RuntimeWorkerMT5Adapter.__doc__
    assert "MetaTrader5" not in sys.modules


def test_worker_reports_missing_required_mt5_package_clearly(monkeypatch, tmp_path, mt5_unavailable):
    from agent.application.runtime_worker import WorkerIdentity
    from agent.infrastructure.interactive_mt5_worker import ReadOnlyMTRuntime, RuntimeSettings

    runtime = ReadOnlyMTRuntime(
        RuntimeSettings("HOST\\MT5RuntimeUser", "HOST\\Agent", tmp_path / "terminal64.exe", tmp_path),
        WorkerIdentity("worker", 10, 1, "HOST\\MT5RuntimeUser", "now", "S-1-5-21-1"),
    )
    with pytest.raises(RuntimeError, match="MT5_PYTHON_PACKAGE_UNAVAILABLE"):
        runtime._api()


def test_legacy_adapter_import_is_optional_and_failure_is_contained(mt5_unavailable, monkeypatch):
    from agent.adapters.mt5_adapter import MT5Adapter

    def unavailable(name):
        if name == "MetaTrader5":
            raise ModuleNotFoundError(name)
        raise AssertionError(name)

    monkeypatch.setattr("agent.adapters.mt5_adapter.importlib.import_module", unavailable)
    adapter = MT5Adapter(module=None, inspector=lambda: None)
    assert adapter.connect() is False


def test_agent_and_worker_dependency_sets_are_separate():
    from pathlib import Path

    root = Path(__file__).parents[1]
    agent_requirements = (root / "requirements.txt").read_text(encoding="utf-8")
    worker_requirements = (root / "requirements-mt5-worker.txt").read_text(encoding="utf-8")
    legacy_requirements = (root / "requirements-legacy-mt5.txt").read_text(encoding="utf-8")
    assert "MetaTrader5" not in agent_requirements
    assert "numpy" not in agent_requirements.casefold()
    assert "MetaTrader5==5.0.6231" in worker_requirements
    assert "MetaTrader5==5.0.6231" in legacy_requirements


def test_release_spec_excludes_mt5_and_worker_modules():
    from pathlib import Path

    spec = (Path(__file__).parents[1] / "deployment" / "Agent.spec").read_text(encoding="utf-8")
    assert '"MetaTrader5"' not in spec.split("hiddenimports=")[1].split("hookspath=")[0]
    assert '"MetaTrader5"' in spec.split("excludes=[")[1]
    assert '"agent.infrastructure.interactive_mt5_worker"' in spec
