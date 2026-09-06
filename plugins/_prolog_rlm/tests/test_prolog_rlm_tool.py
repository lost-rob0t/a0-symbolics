from __future__ import annotations

from types import SimpleNamespace

import pytest

from plugins._prolog_rlm.tools import prolog_rlm as prolog_rlm_tool


class FakeHarness:
    def __init__(self):
        self.calls = []
        self.payloads = {}

    async def call(self, action, arguments, timeout=None):
        self.calls.append((action, arguments, timeout))
        return SimpleNamespace(
            run_id="0" * 32,
            action=action,
            payload=self.payloads.get(action, {"ready": True}),
            elapsed_seconds=0.01,
        )

    async def compile(self, request, timeout=None):
        return await self.call("context_compile", {"request": request}, timeout)


def make_tool(args: dict):
    agent = SimpleNamespace(loop_data=SimpleNamespace(user_message=None))
    return prolog_rlm_tool.PrologRLM(agent, "prolog_rlm", None, args, "", None), args


def patch_configs(monkeypatch, compiler_enabled: bool, projection: str):
    def get_plugin_config(name, agent=None):
        if name == "_prolog_context_compiler":
            return {"enabled": "true"} if compiler_enabled else {}
        return {}

    monkeypatch.setattr(
        prolog_rlm_tool.plugins, "get_plugin_config", get_plugin_config
    )
    monkeypatch.setattr(
        prolog_rlm_tool,
        "compiler_enabled",
        lambda config=None, agent=None: compiler_enabled,
    )
    monkeypatch.setattr(
        prolog_rlm_tool, "build_compile_request",
        lambda agent, prompt, loop_data, config: {"units": [{"name": "u"}]},
    )


def actions_of(harness: FakeHarness):
    return [call[0] for call in harness.calls]


@pytest.mark.asyncio
async def test_direct_compiles_context(monkeypatch):
    harness = FakeHarness()
    harness.payloads["context_compile"] = {"text": "compiled projection"}
    harness.payloads["direct"] = {"value": "the answer"}
    monkeypatch.setattr(prolog_rlm_tool, "shared_harness", lambda config: harness)
    patch_configs(monkeypatch, compiler_enabled=True, projection="x")

    tool, args = make_tool({"action": "direct", "prompt": "summarize"})
    result = await tool.execute(**args)

    assert actions_of(harness) == ["context_compile", "direct"]
    direct_args = harness.calls[1][1]
    assert direct_args["prompt"] == "summarize"
    assert direct_args["context"] == "compiled projection"
    assert "the answer" in result.message


@pytest.mark.asyncio
async def test_complete_merges_projection_with_explicit_context(monkeypatch):
    harness = FakeHarness()
    harness.payloads["context_compile"] = {"text": "projection"}
    monkeypatch.setattr(prolog_rlm_tool, "shared_harness", lambda config: harness)
    patch_configs(monkeypatch, compiler_enabled=True, projection="projection")

    tool, args = make_tool(
        {"action": "complete", "query": "q", "context": "explicit"}
    )
    await tool.execute(**args)

    assert actions_of(harness) == ["context_compile", "complete"]
    complete_args = harness.calls[1][1]
    assert complete_args["context"] == "projection\nexplicit"


@pytest.mark.asyncio
async def test_disabled_compiler_keeps_legacy_arguments(monkeypatch):
    harness = FakeHarness()
    monkeypatch.setattr(prolog_rlm_tool, "shared_harness", lambda config: harness)
    patch_configs(monkeypatch, compiler_enabled=False, projection="")

    tool, args = make_tool(
        {"action": "complete", "query": "q", "context": "raw ctx"}
    )
    await tool.execute(**args)

    assert actions_of(harness) == ["complete"]
    complete_args = harness.calls[0][1]
    assert complete_args["context"] == "raw ctx"
