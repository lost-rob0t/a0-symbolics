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
    assert "durable_effects" in status["surfaces"]
    assert "supervised_agents" in status["surfaces"]


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
def test_runtime_bridge_loads_production_external_pack_without_executing_host():
    declaration = {
        "format": "agent_zero_tool",
        "kind": "tool",
        "category": "process",
        "name": "exec",
        "description": "Execute source through Agent Zero",
        "content": "### exec",
        "schema": {
            "type": "object",
            "required": ["lang", "source_code"],
            "additionalProperties": False,
            "properties": {
                "lang": {"type": "string"},
                "source_code": {"type": "string"},
            },
        },
        "effect": "process",
        "permanent": True,
    }
    bridge = PrologRuntimeBridge(
        {
            "prolog_rlm_root": str(PROLOG_RLM_ROOT),
            "request_timeout_seconds": 3.0,
        }
    )
    try:
        catalog = bridge.call("tool_pack_catalog", {"declarations": [declaration]})
    finally:
        bridge.close()

    assert catalog["categories"] == ["process"]
    manifest = catalog["manifests"][0]
    assert manifest["outcome"]["status"] == "loaded"
    assert [schema["name"] for schema in manifest["schemas"]] == ["exec"]


@pytest.mark.skipif(
    shutil.which("swipl") is None or not PROLOG_RLM_AVAILABLE,
    reason="SWI-Prolog or PROLOG_RLM_TEST_ROOT is unavailable",
)
def test_runtime_bridge_reports_request_errors_with_reason_and_detail():
    """Runtime request rejections must surface the real reason: never the
    opaque "Unknown message: ..." rendering of message_to_string/2."""
    from plugins._prolog_rlm.helpers.bridge import PrologRuntimeBridgeError

    bridge = PrologRuntimeBridge(
        {
            "prolog_rlm_root": str(PROLOG_RLM_ROOT),
            "request_timeout_seconds": 3.0,
        }
    )
    try:
        with pytest.raises(PrologRuntimeBridgeError) as excinfo:
            bridge.call("complete", {"query": "", "context": ""})
    finally:
        bridge.close()

    assert "runtime_request_error" in str(excinfo.value)
    assert "Unknown message" not in str(excinfo.value)
    assert "required_text(query)" in excinfo.value.detail
