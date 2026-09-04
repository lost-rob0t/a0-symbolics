from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from helpers.extract_tools import (
    extract_tool_request,
    is_misformatted_tool_request,
    json_parse_dirty,
    normalize_tool_request,
)
from helpers import parallel_tools


def test_normalize_tool_request_accepts_canonical_keys() -> None:
    assert normalize_tool_request({"tool_name": "response", "tool_args": {"text": "ok"}}) == (
        "response",
        {"text": "ok"},
    )


def test_normalize_tool_request_accepts_fallback_keys() -> None:
    assert normalize_tool_request({"tool": "response", "args": {"text": "ok"}}) == (
        "response",
        {"text": "ok"},
    )


def test_normalize_tool_request_uses_fallback_when_canonical_name_is_empty() -> None:
    assert normalize_tool_request(
        {"tool_name": "", "tool": "response", "args": {"text": "ok"}}
    ) == ("response", {"text": "ok"})


def test_normalize_tool_request_uses_fallback_when_canonical_args_are_invalid() -> None:
    assert normalize_tool_request(
        {"tool_name": "response", "tool_args": None, "args": {"text": "ok"}}
    ) == ("response", {"text": "ok"})


def test_normalize_tool_request_translates_method_suffix_to_action() -> None:
    assert normalize_tool_request(
        {"tool_name": "text_editor:read", "tool_args": {"path": "README.md"}}
    ) == ("text_editor", {"path": "README.md", "action": "read"})


def test_normalize_tool_request_translates_method_arg_to_action() -> None:
    assert normalize_tool_request(
        {"tool_name": "scheduler", "tool_args": {"method": "list_tasks"}}
    ) == ("scheduler", {"method": "list_tasks", "action": "list_tasks"})


def test_normalize_tool_request_preserves_explicit_action_over_method() -> None:
    assert normalize_tool_request(
        {
            "tool_name": "scheduler:delete_task",
            "tool_args": {"method": "list_tasks", "action": "show_task"},
        }
    ) == (
        "scheduler",
        {"method": "list_tasks", "action": "show_task"},
    )


def test_normalize_tool_request_rejects_missing_args() -> None:
    with pytest.raises(ValueError, match="tool_args"):
        normalize_tool_request({"tool_name": "response"})


def test_normalize_tool_request_accepts_native_function_format() -> None:
    request = {
        "type": "function",
        "name": "search_engine",
        "parameters": {"query": "latest Agent Zero release"},
    }

    assert json_parse_dirty(str(request)) == request
    assert normalize_tool_request(request) == (
        "search_engine",
        {"query": "latest Agent Zero release"},
    )


def test_normalize_tool_request_accepts_single_action_wrapper() -> None:
    request = {
        "thoughts": ["Read the requested file."],
        "actions": [
            {
                "tool_name": "text_editor",
                "tool_args": {"action": "read", "path": "README.md"},
            }
        ],
    }

    assert json_parse_dirty(str(request)) == request
    assert normalize_tool_request(request) == (
        "text_editor",
        {"action": "read", "path": "README.md"},
    )


def test_normalize_tool_request_rejects_multiple_wrapped_actions() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        normalize_tool_request(
            {
                "actions": [
                    {"tool_name": "response", "tool_args": {"text": "first"}},
                    {"tool_name": "response", "tool_args": {"text": "second"}},
                ]
            }
        )


def test_extract_tool_request_requires_a_complete_tool_message() -> None:
    request = '{"tool_name":"response","tool_args":{"text":"ok"}}'

    assert extract_tool_request(request) == {
        "tool_name": "response",
        "tool_args": {"text": "ok"},
    }
    assert extract_tool_request('{"status":"ok"}') is None
    assert extract_tool_request(f"Example: {request}") is None
    assert extract_tool_request(f"{request} trailing text") is None


def test_is_misformatted_tool_request_requires_agent_tool_envelope() -> None:
    request = '{"tool_name":"response","tool_args":{"text":"ok"}}'
    concatenated = (
        '{"thoughts":[],"headline":"Inspecting","tool_name":"code_execution_tool",'
        '"tool_args":{"code":"pwd"}}'
        '{"thoughts":[],"headline":"Answering","tool_name":"response",'
        '"tool_args":{"text":"done"}}'
    )
    malformed = (
        '{"thoughts":["Plan the work", "Run the tools", '
        '"headline":"Save results", "tool_name":"parallel", '
        '"tool_args":{"tool_calls":[{"tool_name":"memory_save",'
        '"tool_args":{"text":"ok"}}],"wait":true}}'
    )

    assert extract_tool_request(malformed) is None
    assert is_misformatted_tool_request(malformed) is True
    assert extract_tool_request(concatenated) is None
    assert is_misformatted_tool_request(concatenated) is True
    assert is_misformatted_tool_request(f"Intro\n```json\n{request}\n```") is True
    assert is_misformatted_tool_request('{"status":"planning"}') is False
    assert is_misformatted_tool_request(f"Example: {request}") is False
    assert is_misformatted_tool_request(
        malformed.replace('{"thoughts"', '{"status":"planning","thoughts"')
    ) is False


def test_normalize_parallel_tool_calls_accepts_full_agent_reply_shape() -> None:
    calls = parallel_tools.normalize_parallel_tool_calls(
        [
            {
                "thoughts": ["This is independent and ready to run."],
                "headline": "Search Python release notes",
                "tool_name": "search_engine",
                "tool_args": {"query": "latest Python version changelog"},
            }
        ]
    )

    assert calls[0].tool_name == "search_engine"
    assert calls[0].tool_args == {"query": "latest Python version changelog"}


def test_parallel_prompt_encourages_mixed_independent_batches() -> None:
    prompt = (PROJECT_ROOT / "prompts" / "agent.system.tool.parallel.md").read_text(
        encoding="utf-8"
    )

    assert "same `tool_name` and `tool_args` shape as a top-level reply" in prompt
    assert "planning fields like `thoughts` or `headline` are ignored" in prompt
    assert "even when they use different tools" in prompt
    assert "Do not split by tool type" in prompt
    assert "Never include `document_query`" in prompt
    assert "Call `response` only as a top-level tool" in prompt


def test_extract_tool_request_parses_single_xml_invoke() -> None:
    message = (
        '<invoke name="code_execution_tool">\n'
        "<parameter name=\"runtime\">terminal</parameter>\n"
        "<parameter name=\"code\">print('hi')</parameter>\n"
        "</invoke>"
    )
    request = extract_tool_request(message)
    assert request == {
        "tool_name": "code_execution_tool",
        "tool_args": {"runtime": "terminal", "code": "print('hi')"},
    }


def test_extract_tool_request_parses_nested_parallel_xml_invoke() -> None:
    message = (
        '<invoke name="parallel_tool_calls">\n'
        '<invoke name="code_execution_tool">\n'
        "<parameter name=\"code\">ls /a0/usr/projects/hackmode/repos/</parameter>\n"
        "<parameter name=\"session\">0</parameter>\n"
        "</invoke>\n"
        "</invoke>"
    )
    request = extract_tool_request(message)
    assert request == {
        "tool_name": "parallel",
        "tool_args": {
            "calls": [
                {
                    "tool_name": "code_execution_tool",
                    "tool_args": {
                        "code": "ls /a0/usr/projects/hackmode/repos/",
                        "session": "0",
                    },
                }
            ]
        },
    }
    tool_name, tool_args = normalize_tool_request(request)
    assert tool_name == "parallel"
    assert parallel_tools.normalize_parallel_tool_calls(
        parallel_tools.extract_tool_calls(tool_args)
    )[0].tool_name == "code_execution_tool"


def test_extract_tool_request_parses_sibling_xml_invokes_as_parallel() -> None:
    message = (
        '<invoke name="code_execution_tool">\n'
        "<parameter name=\"code\">whoami</parameter>\n"
        "</invoke>\n"
        '<invoke name="code_execution_tool">\n'
        "<parameter name=\"code\">id</parameter>\n"
        "</invoke>"
    )
    request = extract_tool_request(message)
    assert request is not None
    tool_name, tool_args = normalize_tool_request(request)
    assert tool_name == "parallel"
    assert len(parallel_tools.extract_tool_calls(tool_args)) == 2


def test_extract_tool_request_parses_parallel_wrapper_with_calls_parameter() -> None:
    message = (
        '<invoke name="parallel_tool_calls">\n'
        "<parameter name=\"calls\">"
        '[{"tool_name": "response", "tool_args": {"text": "done"}}]'
        "</parameter>\n"
        "</invoke>"
    )
    request = extract_tool_request(message)
    assert request is not None
    tool_name, tool_args = normalize_tool_request(request)
    assert tool_name == "parallel"


def test_extract_xml_tool_request_rejects_prose_and_junk() -> None:
    assert extract_tool_request("Use <invoke name=\"response\"> like this") is None
    assert extract_tool_request("text before\n<invoke name=\"response\"></invoke>") is None
    assert extract_tool_request('<invoke name="response">no close') is None
    assert (
        extract_tool_request('<invoke name="response"></invoke> trailing text') is None
    )
    assert extract_tool_request("") is None


def test_extract_tool_request_still_prefers_json_requests() -> None:
    message = '{"tool_name": "response", "tool_args": {"text": "ok"}}'
    assert extract_tool_request(message) == {
        "tool_name": "response",
        "tool_args": {"text": "ok"},
    }


def test_xml_tool_request_is_not_misformatted() -> None:
    message = '<invoke name="code_execution_tool"><parameter name="code">x</parameter></invoke>'
    assert is_misformatted_tool_request(message) is False
