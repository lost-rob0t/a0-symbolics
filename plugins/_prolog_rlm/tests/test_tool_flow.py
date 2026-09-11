from __future__ import annotations

import json
import sys
import textwrap
import uuid
from types import SimpleNamespace

import pytest

from plugins._prolog_context_compiler.helpers.transport import PrologJsonWorker
from plugins._prolog_rlm.helpers.loop import (
    DIRECT,
    PrologRLMModel,
    collect_tool_declarations,
    _select_active_declarations,
)

from plugins._prolog_rlm.helpers.harness import RunResult


FAKE_CALLBACK_WORKER = textwrap.dedent(
    """
    import json, sys
    request = json.loads(sys.stdin.readline())
    session = request.get("arguments", {}).get("session", "")
    print(json.dumps({
        "callback": "tool",
        "call_id": "call-1",
        "token": session,
        "name": "exec",
        "arguments": {"lang": "terminal", "code": "echo hi"},
    }), flush=True)
    reply = json.loads(sys.stdin.readline())
    print(json.dumps({
        "ok": True,
        "request_id": request.get("request_id"),
        "result": {"value": reply.get("result", {}).get("value", ""), "tool_calls": 1},
    }), flush=True)
    """
)


class _HarnessStub:
    def __init__(self, compile_payload, direct_payload):
        self._compile_payload = compile_payload
        self._direct_payload = direct_payload
        self.direct_calls: list[dict] = []
        self.registered: dict[str, object] = {}
        self.unregistered: list[str] = []

    async def compile(self, request):
        self.compile_request = request
        return RunResult(run_id="c", action="context_compile",
                         payload=self._compile_payload, elapsed_seconds=0.0)

    async def direct(self, query, context="", budget=None, timeout=None,
                     declarations=None, session=""):
        self.direct_calls.append(
            {"query": query, "declarations": declarations, "session": session}
        )
        return RunResult(run_id="d", action="direct",
                         payload=self._direct_payload, elapsed_seconds=0.0)

    def register_tool_handler(self, token, handler):
        self.registered[token] = handler

    def unregister_tool_handler(self, token):
        self.unregistered.append(token)


class _ToolStub:
    def __init__(self, message):
        self.message = message
        self.calls: list[str] = []

    async def before_execution(self, **kwargs):
        self.calls.append("before")

    async def execute(self, **kwargs):
        self.calls.append("execute")
        return SimpleNamespace(message=self.message)

    async def after_execution(self, response):
        self.calls.append("after")


class _AgentStub:
    def __init__(self):
        self.loop_data = SimpleNamespace(current_tool=None)
        self.config = SimpleNamespace(profile="none")
        self.context = SimpleNamespace(
            get_data=lambda _key: {}, streaming_agent=None, data={}
        )
        self.get_data = lambda _key: {}
        self.number = 0
        self.tools: dict[str, _ToolStub] = {}

    def get_tool(self, name, method, args, message, loop_data):
        return self.tools[name]


def _declaration(name: str, effect: str = "read") -> dict:
    return {
        "kind": "tool",
        "format": "agent_zero_tool",
        "name": name,
        "description": f"{name} tool",
        "content": f"### {name}",
        "schema": {"type": "object", "properties": {}},
        "effect": effect,
        "category": "agent_zero",
        "permanent": False,
    }


def test_select_active_declarations_filters_by_compile_outcome():
    declarations = [_declaration("exec"), _declaration("memory_load"), _declaration("response")]
    selected = _select_active_declarations(["exec", "response"], declarations)
    assert [d["name"] for d in selected] == ["exec"]

    assert _select_active_declarations([], declarations) == []


def test_collect_tool_declarations_uses_compiler_collector(monkeypatch):
    class _Agent:
        loop_data = SimpleNamespace()

    captured = {}

    def fake_build_compile_request(agent, system_prompt, loop_data, config):
        captured["agent"] = agent
        captured["system_prompt"] = system_prompt
        return {
            "units": [
                {"kind": "instruction", "name": "system_0", "format": "agent_zero_context"},
                {"kind": "tool", "name": "exec", "format": "agent_zero_tool"},
                {"kind": "tool", "name": "response", "format": "agent_zero_tool"},
                {"kind": "mcp_tool", "name": "mcp_query", "format": "agent_zero_tool"},
                {"kind": "resource", "name": "chat", "format": "agent_zero_context"},
            ]
        }

    import plugins._prolog_context_compiler.helpers.catalog as catalog
    monkeypatch.setattr(catalog, "build_compile_request", fake_build_compile_request)

    agent = _Agent()
    units = collect_tool_declarations(agent, {})

    assert captured["system_prompt"] == []
    assert captured["agent"] is agent
    assert [u["name"] for u in units] == ["exec", "mcp_query"]


@pytest.mark.asyncio
async def test_direct_turn_passes_active_declarations_and_registers_handler():
    harness = _HarnessStub(
        compile_payload={"text": "projection", "active_tools": ["exec"]},
        direct_payload={"value": "done"},
    )
    agent = _AgentStub()
    tool = _ToolStub("terminal output")
    agent.tools["exec"] = tool
    model = PrologRLMModel(
        object(),
        harness,
        reasoning_mode=DIRECT,
        agent=agent,
        declarations=[_declaration("exec", "process")],
    )

    result = await model.unified_turn(user_message="run echo hi")

    assert result.response == "done"
    assert len(harness.direct_calls) == 1
    call = harness.direct_calls[0]
    assert [d["name"] for d in call["declarations"]] == ["exec"]
    assert call["session"]
    # the registered handler ran a tool through the agent lifecycle; the
    # harness invokes it on a worker thread, so mimic that off the loop
    assert len(harness.registered) == 1
    (handler,) = harness.registered.values()
    import asyncio

    payload = await asyncio.get_running_loop().run_in_executor(
        None, lambda: handler("exec", {"lang": "terminal", "code": "echo hi"})
    )
    assert payload == {"value": "terminal output", "truncated": False}
    assert tool.calls == ["before", "execute", "after"]
    assert harness.unregistered == list(harness.registered.keys())


@pytest.mark.asyncio
async def test_direct_turn_without_active_tools_stays_tool_less():
    harness = _HarnessStub(
        compile_payload={"text": "projection", "active_tools": []},
        direct_payload={"value": "plain"},
    )
    model = PrologRLMModel(
        object(),
        harness,
        reasoning_mode=DIRECT,
        agent=_AgentStub(),
        declarations=[_declaration("exec")],
    )

    result = await model.unified_turn(user_message="hello")

    assert result.response == "plain"
    assert harness.direct_calls[0]["declarations"] == []
    assert harness.registered == {}


def test_transport_answers_tool_callback_frames(tmp_path):
    fake_worker = tmp_path / "fake_worker.py"
    fake_worker.write_text(FAKE_CALLBACK_WORKER)

    worker = PrologJsonWorker(
        fake_worker,
        command=[sys.executable, str(fake_worker)],
        timeout=5.0,
    )
    seen: dict[str, object] = {}

    def handler(name, args):
        seen["name"] = name
        seen["args"] = args
        return {"value": "callback-output", "truncated": False}

    token = uuid.uuid4().hex
    worker.register_tool_handler(token, handler)
    try:
        response = worker.request(
            {"action": "direct", "arguments": {"prompt": "hi", "session": token}}
        )
    finally:
        worker.close()

    assert response["ok"] is True
    assert response["result"]["value"] == "callback-output"
    assert seen["name"] == "exec"
    assert seen["args"] == {"lang": "terminal", "code": "echo hi"}


def test_transport_fails_closed_for_unknown_session_token(tmp_path):
    fake_worker = tmp_path / "fake_worker.py"
    fake_worker.write_text(FAKE_CALLBACK_WORKER)

    worker = PrologJsonWorker(
        fake_worker,
        command=[sys.executable, str(fake_worker)],
        timeout=5.0,
    )
    try:
        response = worker.request(
            {"action": "direct", "arguments": {"prompt": "hi", "session": "unknown"}}
        )
    finally:
        worker.close()

    assert response["ok"] is True
    assert response["result"]["value"] == ""
