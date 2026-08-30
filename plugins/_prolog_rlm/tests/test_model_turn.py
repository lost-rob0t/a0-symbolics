from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from langchain_core.messages import HumanMessage, SystemMessage

from plugins._prolog_rlm.helpers.model_turn import build_turn_request, route_model_turn


class FakeAgent:
    def __init__(self) -> None:
        self.loop_data = SimpleNamespace(user_message=None)
        self.data = {}

    def get_data(self, name):
        return self.data.get(name)

    def set_data(self, name, value):
        self.data[name] = value


class ModelTurnTests(unittest.IsolatedAsyncioTestCase):
    def test_turn_request_uses_native_agent_zero_tools_and_prolog_context_compile(self):
        agent = FakeAgent()
        native_tools = [
            {
                "type": "function",
                "name": "code_execution_tool",
                "description": "Run terminal, Python, or Node.js code.",
                "parameters": {
                    "type": "object",
                    "required": ["runtime"],
                    "additionalProperties": False,
                    "properties": {
                        "runtime": {
                            "type": "string",
                            "enum": ["terminal", "python", "nodejs", "output"],
                        },
                        "code": {"type": "string"},
                    },
                },
            },
            {
                "type": "function",
                "name": "response",
                "description": "Return the final response.",
                "parameters": {
                    "type": "object",
                    "required": ["text"],
                    "properties": {"text": {"type": "string"}},
                    "additionalProperties": False,
                },
            },
        ]

        with (
            patch(
                "plugins._prolog_rlm.helpers.model_turn.build_responses_function_tools",
                return_value=(
                    native_tools,
                    {tool["name"]: tool["name"] for tool in native_tools},
                ),
            ),
            patch(
                "plugins._prolog_rlm.helpers.model_turn.get_chat_model_config",
                return_value={
                    "provider": "openrouter",
                    "name": "openai/gpt-test",
                    "ctx_length": 200_000,
                },
            ),
        ):
            request = build_turn_request(
                agent,
                [
                    SystemMessage(content="System contract"),
                    HumanMessage(content="run pwd"),
                ],
                {"max_context_tokens": 32_768},
            )

        self.assertEqual(request["model"], "openai/gpt-test")
        self.assertEqual(request["context_window"], 200_000)
        self.assertEqual(request["compile_request"]["message"], "run pwd")
        self.assertEqual(request["compile_request"]["max_context_tokens"], 32_768)
        self.assertEqual(
            agent.get_data("responses_tool_name_map"),
            {
                "code_execution_tool": "code_execution_tool",
                "response": "response",
            },
        )
        tool_units = {
            unit["name"]: unit
            for unit in request["compile_request"]["units"]
            if unit["kind"] == "tool"
        }
        self.assertIs(tool_units["response"]["permanent"], True)
        self.assertEqual(
            tool_units["code_execution_tool"]["schema"]["required"],
            ["runtime"],
        )
        self.assertIs(
            request["tools"][0]["function"]["parameters"]["additionalProperties"],
            False,
        )

    async def test_prolog_turn_returns_native_tool_call_and_authoritative_usage(self):
        agent = FakeAgent()
        request = {
            "model": "openai/gpt-test",
            "context_window": 200_000,
            "messages": [],
            "tools": [],
            "compile_request": {"message": "run pwd", "units": []},
        }

        class Bridge:
            def call(self, action, arguments):
                self.action = action
                self.arguments = arguments
                return {
                    "text": "",
                    "reasoning": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "code_execution_tool",
                                "arguments": (
                                    '{"runtime":"terminal","code":"pwd"}'
                                ),
                            },
                        }
                    ],
                    "usage": {
                        "present": True,
                        "prompt_tokens": 11_115,
                        "completion_tokens": 17,
                        "total_tokens": 11_132,
                    },
                    "selected_model": "openai/gpt-test",
                    "projection": {"fingerprint": "ctx-1", "token_ledger": {}},
                }

        bridge = Bridge()
        with (
            patch(
                "plugins._prolog_rlm.helpers.model_turn.build_turn_request",
                return_value=request,
            ),
            patch(
                "plugins._prolog_rlm.helpers.model_turn.shared_runtime_bridge",
                return_value=bridge,
            ),
            patch(
                "plugins._prolog_rlm.helpers.model_turn.plugins.get_plugin_config",
                return_value={},
            ),
        ):
            result = await route_model_turn(
                agent,
                [
                    SystemMessage(content="System contract"),
                    HumanMessage(content="run pwd"),
                ],
            )

        self.assertEqual(bridge.action, "turn")
        self.assertEqual(bridge.arguments["model"], "openai/gpt-test")
        self.assertEqual(result.mode, "responses")
        self.assertEqual(result.function_calls[0].name, "code_execution_tool")
        self.assertEqual(
            result.function_calls[0].arguments,
            {"runtime": "terminal", "code": "pwd"},
        )
        self.assertEqual(agent.get_data("ctx_window")["tokens"], 11_115)
        self.assertEqual(
            agent.get_data("ctx_window")["source"],
            "prolog_rlm_provider_usage",
        )

    async def test_prolog_turn_plain_text_uses_responses_completion_path(self):
        agent = FakeAgent()
        request = {
            "model": "openai/gpt-test",
            "context_window": 200_000,
            "messages": [],
            "tools": [],
            "compile_request": {"message": "hello", "units": []},
        }

        class Bridge:
            def call(self, action, arguments):
                return {
                    "text": "Hello from Prolog-RLM.",
                    "reasoning": "",
                    "tool_calls": [],
                    "usage": {"present": False},
                    "selected_model": "openai/gpt-test",
                    "projection": {"fingerprint": "ctx-2", "token_ledger": {}},
                }

        chunks = []

        async def response_callback(chunk, full):
            chunks.append((chunk, full))

        with (
            patch(
                "plugins._prolog_rlm.helpers.model_turn.build_turn_request",
                return_value=request,
            ),
            patch(
                "plugins._prolog_rlm.helpers.model_turn.shared_runtime_bridge",
                return_value=Bridge(),
            ),
            patch(
                "plugins._prolog_rlm.helpers.model_turn.plugins.get_plugin_config",
                return_value={},
            ),
        ):
            result = await route_model_turn(
                agent,
                [
                    SystemMessage(content="System contract"),
                    HumanMessage(content="hello"),
                ],
                response_callback=response_callback,
            )

        self.assertEqual(result.response, "Hello from Prolog-RLM.")
        self.assertEqual(result.function_calls, [])
        self.assertEqual(
            chunks,
            [("Hello from Prolog-RLM.", "Hello from Prolog-RLM.")],
        )

    def test_standalone_context_compiler_plugin_is_removed(self):
        from pathlib import Path

        plugin_root = Path(__file__).resolve().parents[2]
        self.assertFalse((plugin_root / "_prolog_context_compiler").exists())

    def test_oversized_system_contract_is_split_into_bounded_permanent_units(self):
        agent = FakeAgent()
        with (
            patch(
                "plugins._prolog_rlm.helpers.model_turn.build_responses_function_tools",
                return_value=([], {}),
            ),
            patch(
                "plugins._prolog_rlm.helpers.model_turn.get_chat_model_config",
                return_value={
                    "provider": "openrouter",
                    "name": "openai/gpt-test",
                    "ctx_length": 200_000,
                },
            ),
        ):
            request = build_turn_request(
                agent,
                [SystemMessage(content="x" * 43_974), HumanMessage(content="test")],
            )

        system_units = [
            unit
            for unit in request["compile_request"]["units"]
            if unit["kind"] == "instruction"
        ]
        self.assertEqual(len(system_units), 2)
        self.assertEqual(sum(len(unit["content"]) for unit in system_units), 43_974)
        self.assertTrue(all(len(unit["content"]) <= 30_000 for unit in system_units))
        self.assertTrue(all(unit["permanent"] for unit in system_units))
