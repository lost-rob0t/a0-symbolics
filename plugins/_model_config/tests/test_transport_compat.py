from __future__ import annotations

from helpers import litellm_transport
from plugins._model_config.helpers.transport_compat import (
    ALL_REASONING_EFFORTS,
    _uses_openrouter_automatic_prompt_cache,
    install_transport_compat,
)


def _response_tool() -> dict:
    return {
        "type": "function",
        "name": "response",
        "description": "Return the final answer.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
    }


def test_all_reasoning_efforts_pass_through_unchanged():
    install_transport_compat()

    assert ALL_REASONING_EFFORTS == {
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    }

    for effort in ALL_REASONING_EFFORTS:
        assert litellm_transport._normalize_reasoning_effort(effort) == effort
        assert litellm_transport.ResponsesTransport.normalize_reasoning(effort) == {
            "effort": effort
        }


def test_empty_and_disabled_reasoning_values_still_omit_effort():
    install_transport_compat()

    for value in (None, "", "off", "disabled", "false"):
        assert litellm_transport._normalize_reasoning_effort(value) is None


def test_openrouter_gpt56_uses_automatic_prompt_cache_path():
    assert _uses_openrouter_automatic_prompt_cache(
        "openrouter/openai/gpt-5.6-luna"
    )
    assert _uses_openrouter_automatic_prompt_cache(
        "openrouter/openai/gpt-5.6-sol"
    )
    assert not _uses_openrouter_automatic_prompt_cache(
        "openrouter/anthropic/claude-fable-5"
    )


def test_openrouter_gpt56_native_tool_turn_stays_on_responses_with_caching_enabled():
    install_transport_compat()

    transport = litellm_transport.LiteLLMTransport(
        model="openrouter/openai/gpt-5.6-luna",
        messages=[{"role": "user", "content": "Use the response tool."}],
        kwargs={
            "a0_explicit_prompt_caching": True,
            "a0_responses_function_tools": [_response_tool()],
            "reasoning_effort": "max",
        },
    )

    # A0 still records caching as enabled. GPT-5.6's provider cache is automatic,
    # so no cache_control marker is required to get cached-input pricing.
    assert transport.explicit_prompt_caching is True
    assert transport.policy.mode is litellm_transport.TransportMode.RESPONSES
    assert not litellm_transport._has_cache_control(transport.messages)

    request = transport._responses_request(stream=False)
    assert request["reasoning"] == {"effort": "max"}
    assert request["tool_choice"] == "required"
    assert request["parallel_tool_calls"] is False
    assert [tool["name"] for tool in request["tools"]] == ["response"]


def test_other_openrouter_tool_models_keep_existing_explicit_cache_behavior():
    install_transport_compat()

    transport = litellm_transport.LiteLLMTransport(
        model="openrouter/anthropic/claude-fable-5",
        messages=[
            {"role": "system", "content": "stable system prompt"},
            {"role": "user", "content": "hello"},
        ],
        kwargs={
            "a0_explicit_prompt_caching": True,
            "a0_responses_function_tools": [_response_tool()],
        },
    )

    assert transport.explicit_prompt_caching is True
    assert transport.policy.mode is litellm_transport.TransportMode.CHAT_COMPLETIONS


def test_openrouter_non_tool_explicit_cache_behavior_is_unchanged():
    install_transport_compat()

    transport = litellm_transport.LiteLLMTransport(
        model="openrouter/openai/gpt-5.6-luna",
        messages=[
            {"role": "system", "content": "stable system prompt"},
            {"role": "user", "content": "hello"},
        ],
        kwargs={"a0_explicit_prompt_caching": True},
    )

    assert transport.explicit_prompt_caching is True
    assert transport.policy.mode is litellm_transport.TransportMode.CHAT_COMPLETIONS
