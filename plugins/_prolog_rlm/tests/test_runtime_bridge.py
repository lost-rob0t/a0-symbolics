from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from plugins._prolog_rlm.helpers.bridge import PrologRuntimeBridge


PROLOG_RLM_ROOT = Path(os.environ.get("PROLOG_RLM_TEST_ROOT", ""))
PROLOG_RLM_AVAILABLE = bool(
    os.environ.get("PROLOG_RLM_TEST_ROOT")
    and (PROLOG_RLM_ROOT / "prolog" / "rlm.pl").is_file()
)


def test_runtime_bridge_maps_agent_zero_openrouter_credential(monkeypatch):
    captured = {}

    def capture_init(self, worker, **kwargs):
        captured.update(kwargs.get("environment") or {})

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("API_KEY_OPENROUTER", "agent-zero-secret")
    monkeypatch.setattr(
        "plugins._prolog_rlm.helpers.bridge.PrologJsonWorker.__init__",
        capture_init,
    )

    PrologRuntimeBridge({})

    assert captured["OPENROUTER_API_KEY"] == "agent-zero-secret"


@pytest.mark.skipif(
    shutil.which("swipl") is None or not PROLOG_RLM_AVAILABLE,
    reason="SWI-Prolog or PROLOG_RLM_TEST_ROOT is unavailable",
)
def test_runtime_bridge_reports_full_stable_surface():
    bridge = PrologRuntimeBridge(
        {
            "prolog_rlm_root": str(PROLOG_RLM_ROOT),
            "request_timeout_seconds": 3.0,
        }
    )
    try:
        status = bridge.call("status")
    finally:
        bridge.close()

    assert status["ready"] is True
    assert status["policy_owner"] == "prolog"
    assert status["arbitrary_call"] is False
    assert "completion" in status["surfaces"]
    assert "direct" in status["surfaces"]
    assert "durable_effects" in status["surfaces"]
    assert "supervised_agents" in status["surfaces"]


@pytest.mark.skipif(
    shutil.which("swipl") is None or not PROLOG_RLM_AVAILABLE,
    reason="SWI-Prolog or PROLOG_RLM_TEST_ROOT is unavailable",
)
def test_runtime_bridge_catalog_exposes_the_closed_agent_action():
    bridge = PrologRuntimeBridge(
        {
            "prolog_rlm_root": str(PROLOG_RLM_ROOT),
            "request_timeout_seconds": 3.0,
        }
    )
    try:
        catalog = bridge.call("catalog")
    finally:
        bridge.close()

    operations = [operation["name"] for operation in catalog["operations"]]
    assert operations == [
        "status",
        "catalog",
        "demo",
        "context_compile",
        "turn",
        "direct",
        "agent",
        "complete",
    ]
    by_name = {operation["name"]: operation for operation in catalog["operations"]}
    assert by_name["agent"]["network"] is True
    assert by_name["status"]["network"] is False


@pytest.mark.skipif(
    shutil.which("swipl") is None or not PROLOG_RLM_AVAILABLE,
    reason="SWI-Prolog or PROLOG_RLM_TEST_ROOT is unavailable",
)
def test_runtime_bridge_agent_action_fails_closed_without_credentials(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY_OPENROUTER", raising=False)
    monkeypatch.setenv("OPENROUTER_TEST_MODEL", "test/model")
    bridge = PrologRuntimeBridge(
        {
            "prolog_rlm_root": str(PROLOG_RLM_ROOT),
            "request_timeout_seconds": 10.0,
        }
    )
    try:
        with pytest.raises(Exception, match="missing_credential"):
            bridge.call("agent", {"query": "unreachable"})
    finally:
        bridge.close()


@pytest.mark.skipif(
    shutil.which("swipl") is None or not PROLOG_RLM_AVAILABLE,
    reason="SWI-Prolog or PROLOG_RLM_TEST_ROOT is unavailable",
)
def test_runtime_bridge_rejects_unknown_operation_without_callable_escape():
    bridge = PrologRuntimeBridge(
        {
            "prolog_rlm_root": str(PROLOG_RLM_ROOT),
            "request_timeout_seconds": 3.0,
        }
    )
    try:
        with pytest.raises(Exception, match="unsupported_action"):
            bridge.call("call", {"goal": "halt"})
    finally:
        bridge.close()


@pytest.mark.skipif(
    shutil.which("swipl") is None or not PROLOG_RLM_AVAILABLE,
    reason="SWI-Prolog or PROLOG_RLM_TEST_ROOT is unavailable",
)
def test_runtime_worker_restarts_after_crash():
    bridge = PrologRuntimeBridge(
        {
            "prolog_rlm_root": str(PROLOG_RLM_ROOT),
            "request_timeout_seconds": 3.0,
        }
    )
    try:
        first = bridge.call("status")
        assert bridge._process is not None
        bridge._process.kill()
        bridge._process.wait(timeout=1)
        second = bridge.call("status")
    finally:
        bridge.close()

    assert first["version"] == second["version"]


@pytest.mark.skipif(
    shutil.which("swipl") is None or not PROLOG_RLM_AVAILABLE,
    reason="SWI-Prolog or PROLOG_RLM_TEST_ROOT is unavailable",
)
def test_runtime_bridge_compiles_context_through_the_canonical_worker():
    request = {
        "message": "Return the result",
        "max_context_tokens": 2048,
        "units": [
            {
                "format": "agent_zero_tool",
                "kind": "tool",
                "name": "response",
                "description": "Return the final answer",
                "content": "Return the final answer",
                "schema": {"type": "object", "properties": {}},
                "effect": "read",
                "permanent": True,
            }
        ],
    }
    bridge = PrologRuntimeBridge(
        {
            "prolog_rlm_root": str(PROLOG_RLM_ROOT),
            "request_timeout_seconds": 3.0,
        }
    )
    try:
        compiled = bridge.call("context_compile", {"request": request})
    finally:
        bridge.close()

    assert compiled["active_tools"] == ["response"]
    assert compiled["fingerprint"]
    assert compiled["token_ledger"]
