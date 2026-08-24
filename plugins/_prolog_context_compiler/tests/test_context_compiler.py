from __future__ import annotations

import shutil
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from plugins._prolog_context_compiler.helpers.bridge import (
    PrologContextBridge,
    PrologContextBridgeError,
    close_shared_bridge,
    compiler_enabled,
    compiler_root,
)
from plugins._prolog_context_compiler.helpers.projection import (
    ACTIVE_CONTEXT_KEY,
    filter_native_tools,
)


PROLOG_RLM_ROOT = Path(os.environ.get("PROLOG_RLM_TEST_ROOT", ""))
PROLOG_RLM_AVAILABLE = bool(
    os.environ.get("PROLOG_RLM_TEST_ROOT")
    and (PROLOG_RLM_ROOT / "prolog" / "rlm_prompt_compiler.pl").is_file()
)


def _request(message: str) -> dict:
    return {
        "message": message,
        "max_context_tokens": 4096,
        "units": [
            {
                "kind": "instruction",
                "name": "core",
                "description": "Core Agent Zero behavior",
                "content": "Always answer accurately.",
                "mandatory": True,
            },
            {
                "kind": "tool",
                "name": "response",
                "description": "Return the final answer",
                "content": "### response\nReturn the final answer.",
                "schema": {"type": "object", "properties": {}},
                "mandatory": True,
            },
            {
                "kind": "tool",
                "name": "text_editor",
                "description": "Read and edit text files",
                "content": "### text_editor\nRead and edit text files.",
                "schema": {"type": "object", "properties": {}},
            },
            {
                "kind": "tool",
                "name": "browser",
                "description": "Browse web pages and websites",
                "content": "### browser\nBrowse websites.",
                "schema": {"type": "object", "properties": {}},
            },
        ],
    }


@pytest.mark.skipif(
    shutil.which("swipl") is None or not PROLOG_RLM_AVAILABLE,
    reason="SWI-Prolog or PROLOG_RLM_TEST_ROOT is unavailable",
)
def test_bridge_selects_relevant_tool_and_keeps_mandatory_response():
    bridge = PrologContextBridge(prolog_rlm_root=PROLOG_RLM_ROOT, timeout=3.0)
    try:
        result = bridge.compile(_request("Please edit the text file"))
    finally:
        bridge.close()

    assert result["ok"] is True
    assert result["active_tools"] == ["response", "text_editor"]
    assert "Read and edit text files" in result["text"]
    assert "### browser" not in result["text"]
    assert result["fingerprint"]
    assert result["token_ledger"]


@pytest.mark.skipif(
    shutil.which("swipl") is None or not PROLOG_RLM_AVAILABLE,
    reason="SWI-Prolog or PROLOG_RLM_TEST_ROOT is unavailable",
)
def test_bridge_restarts_after_worker_crash_without_hanging():
    bridge = PrologContextBridge(prolog_rlm_root=PROLOG_RLM_ROOT, timeout=3.0)
    try:
        first = bridge.compile(_request("edit the file"))
        assert bridge._process is not None
        bridge._process.kill()
        bridge._process.wait(timeout=1)
        second = bridge.compile(_request("edit the file"))
    finally:
        bridge.close()

    assert first["fingerprint"] == second["fingerprint"]
    assert first["active_tools"] == second["active_tools"]


@pytest.mark.asyncio
@pytest.mark.skipif(
    shutil.which("swipl") is None or not PROLOG_RLM_AVAILABLE,
    reason="SWI-Prolog or PROLOG_RLM_TEST_ROOT is unavailable",
)
async def test_real_prompt_compilation_unloads_irrelevant_catalogs(monkeypatch):
    from agent import AgentConfig, AgentContext, AgentContextType, LoopData
    from helpers import history, runtime

    monkeypatch.setenv("PROLOG_RLM_ROOT", str(PROLOG_RLM_ROOT))
    close_shared_bridge()
    old_args = dict(runtime.args)
    runtime.args.clear()
    runtime.args["dockerized"] = "true"
    context = AgentContext(
        config=AgentConfig(
            profile="agent0",
            knowledge_subdirs=["custom", "default"],
            mcp_servers='{"mcpServers": {}}',
        ),
        type=AgentContextType.USER,
        set_current=False,
    )
    try:
        loop_data = LoopData(
            user_message=history.Message(
                ai=False,
                content="Please edit the configuration file and return the result.",
            )
        )
        context.agent0.loop_data = loop_data
        system = await context.agent0.get_system_prompt(loop_data)
        rendered = "\n\n".join(system)
        projection = context.agent0.get_data(ACTIVE_CONTEXT_KEY)

        assert projection["active_tools"]
        assert "response" in projection["active_tools"]
        assert "text_editor" in projection["active_tools"]
        assert "exec" in projection["active_tools"]
        assert "git" in projection["active_tools"]
        assert "patch" in projection["active_tools"]
        assert "prolog_rlm" in projection["active_tools"]
        assert "browser" not in projection["active_tools"]
        assert "### browser" not in rendered
        assert len(system) == 1
    finally:
        AgentContext.remove(context.id)
        runtime.args.clear()
        runtime.args.update(old_args)
        close_shared_bridge()


def test_native_schema_projection_only_removes_and_never_grants_authority():
    agent = SimpleNamespace(
        data={ACTIVE_CONTEXT_KEY: {"active_tools": ["response", "text_editor"]}},
        get_data=lambda key: agent.data.get(key),
    )
    schemas = [
        {"type": "function", "name": "response"},
        {"type": "function", "name": "text_editor"},
        {"type": "function", "name": "browser"},
    ]

    filtered = filter_native_tools(agent, schemas, {})

    assert [tool["name"] for tool in filtered] == ["response", "text_editor"]
    assert all(tool in schemas for tool in filtered)


def test_malformed_worker_result_is_an_explicit_failure(monkeypatch):
    bridge = PrologContextBridge(prolog_rlm_root=PROLOG_RLM_ROOT, timeout=0.1)
    monkeypatch.setattr(
        bridge,
        "_exchange",
        lambda request: {"ok": True, "request_id": request["request_id"]},
    )

    with pytest.raises(PrologContextBridgeError, match="missing"):
        bridge.compile(_request("edit"))


def test_compiler_requires_explicit_runtime_configuration(monkeypatch):
    monkeypatch.delenv("PROLOG_RLM_ROOT", raising=False)
    monkeypatch.delenv("PROLOG_RLM_ENABLED", raising=False)
    assert compiler_root({}) == ""
    assert compiler_enabled(config={}) is False
    monkeypatch.setenv("PROLOG_RLM_ROOT", "/nix/store/prolog-rlm")
    assert compiler_root({}) == "/nix/store/prolog-rlm"
    assert compiler_enabled(config={}) is True
    assert compiler_root({"prolog_rlm_root": "/configured"}) == "/configured"
    monkeypatch.delenv("PROLOG_RLM_ROOT")
    monkeypatch.setenv("PROLOG_RLM_ENABLED", "true")
    assert compiler_enabled(config={}) is True
