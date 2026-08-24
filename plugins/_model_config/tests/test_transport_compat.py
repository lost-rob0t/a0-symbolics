from __future__ import annotations

from helpers import litellm_transport
from plugins._model_config.helpers import transport_compat as compat


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


def _transport(
    model: str,
    *,
    kwargs: dict | None = None,
    messages: list[dict] | None = None,
):
    compat.install_transport_compat()
    return litellm_transport.LiteLLMTransport(
        model=model,
        messages=messages
        or [
            {"role": "system", "content": "stable system prompt"},
            {"role": "user", "content": "do the task"},
        ],
        kwargs=kwargs or {},
    )


def test_all_reasoning_efforts_pass_through_unchanged():
    compat.install_transport_compat()

    assert compat.ALL_REASONING_EFFORTS == {
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    }

    for effort in compat.ALL_REASONING_EFFORTS:
        transport = _transport(
            "openrouter/openai/gpt-5.6-luna",
            kwargs={"reasoning_effort": effort},
        )
        request = transport._responses_request(stream=False)
        assert request["reasoning"] == {"effort": effort}

    assert litellm_transport._normalize_reasoning_effort("none") is None
    assert litellm_transport._normalize_reasoning_effort("xhigh") == "high"


def test_empty_and_disabled_reasoning_values_still_omit_effort():
    compat.install_transport_compat()

    for value in (None, "", "off", "disabled", "false"):
        assert litellm_transport._normalize_reasoning_effort(value) is None


def test_openrouter_prompt_cache_policy_matrix():
    automatic = compat.OpenRouterPromptCacheMode.AUTOMATIC
    block = compat.OpenRouterPromptCacheMode.EXPLICIT_BLOCK
    passive = compat.OpenRouterPromptCacheMode.PASSIVE

    for model in (
        "openrouter/openai/gpt-5.6-luna",
        "openrouter/openai/gpt-4o",
        "openrouter/x-ai/grok-4",
        "openrouter/moonshotai/kimi-k2.6",
        "openrouter/deepseek/deepseek-v4-flash-0731",
        "openrouter/deepseek/deepseek-v3.2",
        "openrouter/z-ai/glm-5.3",
        "openrouter/google/gemini-2.5-flash",
        "openrouter/google/gemini-3.1-flash-lite",
    ):
        assert compat.openrouter_prompt_cache_mode(model) is automatic

    for model in (
        "openrouter/anthropic/claude-fable-5",
        "openrouter/qwen/qwen3-max",
        "openrouter/qwen/qwen-plus",
        "openrouter/qwen/qwen3.6-plus",
        "openrouter/qwen/qwen3-coder-plus",
        "openrouter/qwen/qwen3-coder-flash:nitro",
    ):
        assert compat.openrouter_prompt_cache_mode(model) is block

    for model in (
        "openrouter/qwen/qwen3.5-plus-02-15",
        "openrouter/qwen/qwen3.5-flash-02-23",
        "openrouter/google/gemini-1.5-pro",
        "openrouter/meta-llama/llama-4-maverick",
        "openrouter/auto",
    ):
        assert compat.openrouter_prompt_cache_mode(model) is passive


def test_automatic_openrouter_models_keep_native_responses_without_markers(monkeypatch):
    monkeypatch.setattr(
        compat.context_helper,
        "get_context_data",
        lambda key, default="": "chat123" if key == "agent_context_id" else default,
    )

    for model in (
        "openrouter/openai/gpt-5.6-luna",
        "openrouter/z-ai/glm-5.3",
        "openrouter/deepseek/deepseek-v4-flash-0731",
        "openrouter/google/gemini-3.1-flash-lite",
    ):
        transport = _transport(
            model,
            kwargs={
                "a0_explicit_prompt_caching": True,
                "a0_responses_function_tools": [_response_tool()],
            },
        )

        assert transport.policy.mode is litellm_transport.TransportMode.RESPONSES
        assert transport.explicit_prompt_caching is False
        assert not litellm_transport._has_cache_control(transport.messages)

        request = transport._responses_request(stream=False)
        assert request["tool_choice"] == "required"
        assert request["parallel_tool_calls"] is False
        assert request["extra_body"]["session_id"] == "a0-chat123"


def test_openai_automatic_cache_gets_stable_prompt_key_and_configurable_effort(monkeypatch):
    current_context = {"id": "chat-one"}
    monkeypatch.setattr(
        compat.context_helper,
        "get_context_data",
        lambda key, default="": current_context["id"]
        if key == "agent_context_id"
        else default,
    )

    first = _transport(
        "openrouter/openai/gpt-5.6-luna",
        kwargs={
            "a0_explicit_prompt_caching": True,
            "a0_responses_function_tools": [_response_tool()],
            "reasoning_effort": "max",
        },
    )
    first_request = first._responses_request(stream=False)

    current_context["id"] = "chat-two"
    second = _transport(
        "openrouter/openai/gpt-5.6-luna",
        kwargs={
            "a0_explicit_prompt_caching": True,
            "a0_responses_function_tools": [_response_tool()],
            "reasoning_effort": "max",
        },
    )
    second_request = second._responses_request(stream=False)

    assert first_request["reasoning"] == {"effort": "max"}
    assert first_request["extra_body"]["session_id"] == "a0-chat-one"
    assert second_request["extra_body"]["session_id"] == "a0-chat-two"

    # Cache affinity is derived from stable prompt/tool material, not the chat id,
    # allowing independent chats with the same prefix to reuse upstream affinity.
    assert first_request["extra_body"]["prompt_cache_key"]
    assert (
        first_request["extra_body"]["prompt_cache_key"]
        == second_request["extra_body"]["prompt_cache_key"]
    )


def test_manual_session_and_openai_cache_controls_are_preserved(monkeypatch):
    monkeypatch.setattr(
        compat.context_helper,
        "get_context_data",
        lambda key, default="": "generated-chat",
    )

    transport = _transport(
        "openrouter/openai/gpt-5.6-sol",
        kwargs={
            "a0_explicit_prompt_caching": True,
            "session_id": "manual-session",
            "prompt_cache_key": "manual-cache-key",
            "prompt_cache_options": {"ttl": "30m"},
            "a0_responses_function_tools": [_response_tool()],
        },
    )
    request = transport._responses_request(stream=False)
    body = request["extra_body"]

    assert body["session_id"] == "manual-session"
    assert body["prompt_cache_key"] == "manual-cache-key"
    assert body["prompt_cache_options"] == {"ttl": "30m"}


def test_extra_body_session_id_is_not_overwritten(monkeypatch):
    monkeypatch.setattr(
        compat.context_helper,
        "get_context_data",
        lambda key, default="": "generated-chat",
    )

    transport = _transport(
        "openrouter/z-ai/glm-5.3",
        kwargs={
            "a0_explicit_prompt_caching": True,
            "extra_body": {"session_id": "body-session", "custom": True},
            "a0_responses_function_tools": [_response_tool()],
        },
    )
    request = transport._responses_request(stream=False)

    assert request["extra_body"]["session_id"] == "body-session"
    assert request["extra_body"]["custom"] is True


def test_anthropic_defaults_to_cross_provider_explicit_breakpoints(monkeypatch):
    monkeypatch.setattr(
        compat.context_helper,
        "get_context_data",
        lambda key, default="": "claude-chat",
    )

    transport = _transport(
        "openrouter/anthropic/claude-fable-5",
        kwargs={
            "a0_explicit_prompt_caching": True,
            "a0_responses_function_tools": [_response_tool()],
        },
    )

    # Explicit Anthropic breakpoints work across Anthropic, Bedrock and Vertex,
    # while OpenRouter's top-level automatic cache currently pins direct Anthropic.
    assert transport.policy.mode is litellm_transport.TransportMode.CHAT_COMPLETIONS
    assert transport.explicit_prompt_caching is True
    assert litellm_transport._has_cache_control(transport.messages)

    request = transport._chat_request(stream=False)
    assert request["extra_body"]["session_id"] == "a0-claude-chat"


def test_anthropic_top_level_cache_control_is_a_user_opt_in(monkeypatch):
    monkeypatch.setattr(
        compat.context_helper,
        "get_context_data",
        lambda key, default="": "claude-chat",
    )

    control = {"type": "ephemeral", "ttl": "1h"}
    transport = _transport(
        "openrouter/anthropic/claude-fable-5",
        kwargs={
            "a0_explicit_prompt_caching": True,
            "cache_control": control,
            "a0_responses_function_tools": [_response_tool()],
        },
    )

    assert transport.policy.mode is litellm_transport.TransportMode.RESPONSES
    assert transport.explicit_prompt_caching is False
    assert not litellm_transport._has_cache_control(transport.messages)

    request = transport._responses_request(stream=False)
    assert request["extra_body"]["cache_control"] == control
    assert request["extra_body"]["session_id"] == "a0-claude-chat"


def test_supported_qwen_uses_explicit_blocks_but_snapshot_does_not(monkeypatch):
    monkeypatch.setattr(
        compat.context_helper,
        "get_context_data",
        lambda key, default="": "qwen-chat",
    )

    supported = _transport(
        "openrouter/qwen/qwen3-coder-plus",
        kwargs={
            "a0_explicit_prompt_caching": True,
            "a0_responses_function_tools": [_response_tool()],
        },
    )
    assert supported.policy.mode is litellm_transport.TransportMode.CHAT_COMPLETIONS
    assert litellm_transport._has_cache_control(supported.messages)

    snapshot = _transport(
        "openrouter/qwen/qwen3.5-plus-02-15",
        kwargs={
            "a0_explicit_prompt_caching": True,
            "a0_responses_function_tools": [_response_tool()],
        },
    )
    assert snapshot.policy.mode is litellm_transport.TransportMode.RESPONSES
    assert snapshot.explicit_prompt_caching is False
    assert not litellm_transport._has_cache_control(snapshot.messages)


def test_unknown_openrouter_models_are_not_forced_onto_cache_control(monkeypatch):
    monkeypatch.setattr(
        compat.context_helper,
        "get_context_data",
        lambda key, default="": "unknown-chat",
    )

    transport = _transport(
        "openrouter/meta-llama/llama-4-maverick",
        kwargs={
            "a0_explicit_prompt_caching": True,
            "a0_responses_function_tools": [_response_tool()],
        },
    )

    assert transport.policy.mode is litellm_transport.TransportMode.RESPONSES
    assert transport.explicit_prompt_caching is False
    assert not litellm_transport._has_cache_control(transport.messages)
    assert transport._responses_request(stream=False)["extra_body"]["session_id"] == (
        "a0-unknown-chat"
    )


def test_response_caching_is_never_enabled_implicitly(monkeypatch):
    monkeypatch.setattr(
        compat.context_helper,
        "get_context_data",
        lambda key, default="": "chat123",
    )

    transport = _transport(
        "openrouter/openai/gpt-5.6-luna",
        kwargs={
            "a0_explicit_prompt_caching": True,
            "a0_responses_function_tools": [_response_tool()],
        },
    )
    request = transport._responses_request(stream=False)

    headers = request.get("extra_headers") or {}
    assert "X-OpenRouter-Cache" not in headers
    assert "x-openrouter-cache" not in {str(key).lower() for key in headers}
