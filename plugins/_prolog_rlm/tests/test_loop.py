from __future__ import annotations

import os
import shutil
from types import SimpleNamespace
from pathlib import Path

import pytest

from plugins._prolog_rlm.helpers.loop import (
    DIRECT,
    SYMBOLIC,
    SYMBOLIC_RECURSIVE,
    PrologRLMModel,
    compile_context_request,
    completion_budget,
    context_budget_tokens,
    wrap_chat_model,
)


class HarnessStub:
    def __init__(self, payload=None, direct_payload=None):
        self.payload = payload if payload is not None else {"value": "runtime text"}
        self.direct_payload = (
            direct_payload if direct_payload is not None else {"value": "direct text"}
        )
        self.calls = []
        self.compiles = []
        self.compile_error = None

    async def compile(self, request, timeout=None):
        self.compiles.append(request)
        if self.compile_error is not None:
            raise self.compile_error
        from plugins._prolog_rlm.helpers.harness import RunResult

        names = [str(unit.get("name") or "") for unit in request.get("units", [])]
        return RunResult(
            run_id="0" * 32,
            action="context_compile",
            payload={"text": "compiled:" + "|".join(names)},
            elapsed_seconds=0.01,
        )

    async def direct(self, query, context="", budget=None, timeout=None):
        self.calls.append(
            {
                "action": "direct",
                "query": query,
                "context": context,
                "budget": budget,
                "timeout": timeout,
            }
        )
        from plugins._prolog_rlm.helpers.harness import RunResult

        return RunResult(
            run_id="0" * 32, action="direct", payload=self.direct_payload,
            elapsed_seconds=0.01,
        )

    async def complete(self, query, context, budget=None, timeout=None):
        self.calls.append(
            {"query": query, "context": context, "budget": budget, "timeout": timeout}
        )
        from plugins._prolog_rlm.helpers.harness import RunResult

        return RunResult(
            run_id="0" * 32, action="complete", payload=self.payload,
            elapsed_seconds=0.01,
        )


class InnerModel:
    model_name = "test/model"
    kwargs = {}
    a0_model_conf = SimpleNamespace(ctx_length=100_000)

    def __init__(self):
        self.calls = []

    async def unified_turn(self, **kwargs):
        self.calls.append(kwargs)
        from helpers.llm_result import LLMResult

        return LLMResult(response="native text", mode="responses")


def messages(*texts):
    return [SimpleNamespace(content=text) for text in texts]


class TestContextBudget:
    def test_percent_of_ctx_length(self):
        assert context_budget_tokens(100_000, 30) == 30_000
        assert context_budget_tokens(10_000, 30) == 3_000

    def test_unknown_window_gives_zero(self):
        assert context_budget_tokens(0, 30) == 0

    def test_budget_shape_per_mode(self):
        assert completion_budget(30_000, DIRECT) == {
            "context_budget_tokens": 30_000,
            "max_recursion_depth": 1,
        }
        assert completion_budget(30_000, SYMBOLIC)["max_recursion_depth"] == 1
        assert completion_budget(30_000, SYMBOLIC_RECURSIVE)["max_recursion_depth"] == 3
        assert "max_recursion_depth" not in completion_budget(30_000, "auto")


class TestCompileContextRequest:
    def test_system_message_is_a_permanent_instruction_unit(self):
        request = compile_context_request("q", [], "SYS", 0)
        assert request["message"] == "q"
        assert request["units"] == [
            {
                "kind": "instruction",
                "format": "agent_zero_context",
                "name": "chat_system_000",
                "description": "Agent Zero system prompt",
                "content": "SYS",
                "permanent": True,
            }
        ]

    def test_prior_messages_become_bounded_resource_units(self):
        prior = messages("ctx one", "ctx two")
        request = compile_context_request("q", prior, "", 8_000)
        assert [unit["name"] for unit in request["units"]] == [
            "chat_turn_0000_message",
            "chat_turn_0001_message",
        ]
        assert request["max_context_tokens"] == 8_000

    def test_unknown_budget_omits_the_limit(self):
        request = compile_context_request("q", [], "", 0)
        assert "max_context_tokens" not in request


class TestPrologRLMModel:
    def test_direct_mode_routes_through_runtime_with_recursion(self):
        inner = InnerModel()
        harness = HarnessStub()
        model = PrologRLMModel(inner, harness, reasoning_mode=DIRECT)
        import asyncio

        result = asyncio.run(model.unified_turn(user_message="hi"))
        assert result.response == "direct text"
        assert len(inner.calls) == 0
        call = harness.calls[0]
        assert call["query"] == "hi"
        assert call["budget"]["max_recursion_depth"] == 1

    def test_direct_mode_compiles_context_before_dispatch(self):
        harness = HarnessStub()
        model = PrologRLMModel(InnerModel(), harness, reasoning_mode=DIRECT)
        import asyncio

        asyncio.run(
            model.unified_turn(
                system_message="SYS", user_message="hi",
                messages=messages("ctx one"),
            )
        )
        request = harness.compiles[0]
        assert [unit["name"] for unit in request["units"]] == [
            "chat_system_000",
            "chat_turn_0000_message",
        ]
        assert harness.calls[0]["context"] == (
            "compiled:chat_system_000|chat_turn_0000_message"
        )

    def test_compile_failure_raises_instead_of_downgrading(self):
        harness = HarnessStub()
        harness.compile_error = RuntimeError("worker gone")
        model = PrologRLMModel(InnerModel(), harness, reasoning_mode=DIRECT)
        import asyncio

        with pytest.raises(RuntimeError, match="worker gone"):
            asyncio.run(model.unified_turn(user_message="hi"))

    def test_symbolic_mode_routes_through_runtime(self):
        import asyncio

        harness = HarnessStub()
        model = PrologRLMModel(
            InnerModel(), harness, reasoning_mode=SYMBOLIC,
            context_budget_percent=30,
        )
        result = asyncio.run(model.unified_turn(user_message="do the thing"))
        assert result.response == "runtime text"
        assert result.mode == "responses"
        assert result.capability["runtime"] == "prolog-rlm"
        call = harness.calls[0]
        assert call["query"] == "do the thing"
        assert call["budget"]["context_budget_tokens"] == 30_000
        assert call["budget"]["max_recursion_depth"] == 1

    def test_flattens_prompt_messages_into_compiled_context(self):
        import asyncio

        harness = HarnessStub()
        model = PrologRLMModel(InnerModel(), harness, reasoning_mode=SYMBOLIC)
        asyncio.run(
            model.unified_turn(
                system_message="SYS", user_message="USER",
                messages=messages("ctx one", "ctx two"),
            )
        )
        call = harness.calls[0]
        assert "chat_system_000" in call["context"]
        assert "chat_turn_0000_message" in call["context"]
        assert "chat_turn_0001_message" in call["context"]
        assert harness.calls[0]["query"] == "USER"

    def test_textless_user_message_derives_query_from_newest_message(self):
        import asyncio

        harness = HarnessStub()
        model = PrologRLMModel(InnerModel(), harness, reasoning_mode=SYMBOLIC)
        asyncio.run(
            model.unified_turn(
                user_message="",
                messages=messages("ctx one", "newest turn"),
            )
        )
        call = harness.calls[0]
        assert call["query"] == "newest turn"
        unit_contents = [
            unit["content"] for unit in harness.compiles[0]["units"]
        ]
        assert any("ctx one" in content for content in unit_contents)
        assert not any(
            "newest turn" in content for content in unit_contents
        )

    def test_tool_call_continuation_derives_query_from_structured_content(self):
        import asyncio

        harness = HarnessStub()
        model = PrologRLMModel(InnerModel(), harness, reasoning_mode=SYMBOLIC)
        tool_message = SimpleNamespace(
            content=[{"type": "tool_use", "name": "response"}]
        )
        asyncio.run(
            model.unified_turn(user_message="", messages=[tool_message])
        )
        assert harness.calls[0]["query"].strip() != ""

    def test_degenerate_textless_turn_falls_through_to_inner(self):
        import asyncio

        inner = InnerModel()
        harness = HarnessStub()
        model = PrologRLMModel(inner, harness, reasoning_mode=SYMBOLIC)
        result = asyncio.run(model.unified_turn(user_message="", messages=[]))
        assert result.response == "native text"
        assert len(inner.calls) == 1
        assert harness.calls == []
        assert harness.compiles == []

    def test_response_callback_gets_full_text_once(self):
        import asyncio

        seen = []

        async def response_callback(chunk, full):
            seen.append((chunk, full))
            return None

        model = PrologRLMModel(InnerModel(), HarnessStub(), reasoning_mode=SYMBOLIC)
        asyncio.run(
            model.unified_turn(
                user_message="hi", response_callback=response_callback
            )
        )
        assert seen == [("runtime text", "runtime text")]

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValueError):
            PrologRLMModel(InnerModel(), HarnessStub(), reasoning_mode="yolo")

    def test_proxy_exposes_inner_contract(self):
        inner = InnerModel()
        model = PrologRLMModel(inner, HarnessStub())
        assert model.model_name == inner.model_name
        assert model.a0_model_conf is inner.a0_model_conf
        assert model.kwargs == {}


class TestWrapChatModel:
    def test_disabled_returns_inner(self):
        inner = InnerModel()
        assert wrap_chat_model(inner, {"core_loop_enabled": "false"}) is inner
        assert wrap_chat_model(inner, {}) is inner

    def test_enabled_wraps_with_settings(self):
        harness = HarnessStub()
        wrapped = wrap_chat_model(
            InnerModel(),
            {
                "core_loop_enabled": True,
                "reasoning_mode": "symbolic",
                "context_budget_percent": "45",
            },
            harness=harness,
        )
        assert isinstance(wrapped, PrologRLMModel)
        assert wrapped.reasoning_mode == "symbolic"
        assert wrapped.context_budget_percent == 45

    def test_percent_falls_back_on_garbage(self):
        wrapped = wrap_chat_model(
            InnerModel(),
            {"core_loop_enabled": True, "context_budget_percent": "abc"},
            harness=HarnessStub(),
        )
        assert wrapped.context_budget_percent == 30


PROLOG_RLM_ROOT = Path(os.environ.get("PROLOG_RLM_TEST_ROOT", ""))
PROLOG_RLM_AVAILABLE = bool(
    os.environ.get("PROLOG_RLM_TEST_ROOT")
    and (PROLOG_RLM_ROOT / "prolog" / "rlm.pl").is_file()
)


@pytest.mark.skipif(
    os.environ.get("PROLOG_RLM_TEST_ROOT") == "" or not PROLOG_RLM_ROOT.is_dir(),
    reason="PROLOG_RLM_TEST_ROOT unavailable",
)
class TestWorkerContextBytes:
    def test_worker_accepts_context_bytes_argument(self):
        """The vendored worker accepts context_bytes and forwards it as an
        option; verified by parsing the worker source for the plumbing."""
        source = (
            Path(__file__).resolve().parents[1] / "prolog" / "runtime_worker.pl"
        ).read_text()
        assert "context_bytes_option" in source
        assert "context_bytes(Bytes)" in source


class TestWorkerDirectContract:
    def test_direct_dispatch_uses_bounded_direct_loop_with_context(self):
        """Direct mode must run the provider-native direct agent loop over the
        optional compiled context (recursion included), not the one-shot
        llm_query primitive."""
        source = (
            Path(__file__).resolve().parents[1] / "prolog" / "runtime_worker.pl"
        ).read_text()
        assert "rlm:rlm_direct(Prompt, text(Context), Options, Outcome)" in source
        assert "optional_text(Arguments, context, \"\", Context)" in source
        assert "rlm:llm_query(" not in source

    def test_worker_unwraps_completion_outcomes(self):
        """ok(...) / error(...) outcomes must not leak $term envelopes: a
        fault surfaces as a failed envelope, success as the bare result."""
        source = (
            Path(__file__).resolve().parents[1] / "prolog" / "runtime_worker.pl"
        ).read_text()
        assert "runtime_result(ok(Result), Result) :- !." in source
        assert "runtime_request_error(runtime_fault(Safe))" in source
        assert "context_compile_rejected(Safe)" in source
