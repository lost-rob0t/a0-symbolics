from __future__ import annotations

from typing import Any, Callable

from helpers import litellm_transport


ALL_REASONING_EFFORTS = frozenset(
    {
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    }
)

# OpenRouter documents automatic provider prompt caching for OpenAI GPT-5.6+
# models. These models do not need cache_control markers to receive cached-input
# pricing, so native Agent Zero tool turns can stay on Responses without giving
# up prompt caching.
OPENROUTER_AUTOMATIC_CACHE_MODEL_PREFIXES = (
    "openrouter/openai/gpt-5.6",
)

_PATCH_MARKER = "_a0_model_config_transport_compat"


def install_transport_compat() -> None:
    """Install model-config transport compatibility fixes once per process."""
    litellm_transport.RESPONSES_REASONING_EFFORTS.update(ALL_REASONING_EFFORTS)

    # String "none" is a real reasoning effort level. Python None / empty / off
    # still mean that the effort field should be omitted.
    litellm_transport.NO_REASONING_EFFORT_ALIASES.discard("none")

    transport_cls = litellm_transport.LiteLLMTransport
    current = transport_cls.__post_init__
    if getattr(current, _PATCH_MARKER, False):
        return

    original: Callable[[Any], None] = current

    def patched_post_init(self) -> None:
        kwargs = dict(self.kwargs)
        explicit_caching = litellm_transport._coerce_bool(
            kwargs.get("a0_explicit_prompt_caching", False),
            default=False,
        )
        has_a0_function_tools = litellm_transport._has_tools(
            kwargs.get("a0_responses_function_tools")
        )
        automatic_prompt_cache = _uses_openrouter_automatic_prompt_cache(self.model)

        # cache_control markers intentionally route OpenRouter through Chat
        # Completions. On GPT-5.6+ the provider already performs automatic
        # prompt caching, so adding those markers only sacrifices the stronger
        # native Responses function-call contract. Skip the markers for these
        # native tool turns while keeping A0's explicit-caching intent visible.
        if explicit_caching and has_a0_function_tools and automatic_prompt_cache:
            kwargs["a0_explicit_prompt_caching"] = False
            self.kwargs = kwargs
            original(self)
            self.explicit_prompt_caching = True
            return

        original(self)

    setattr(patched_post_init, _PATCH_MARKER, True)
    transport_cls.__post_init__ = patched_post_init


def _uses_openrouter_automatic_prompt_cache(model: str) -> bool:
    normalized = str(model or "").strip().lower()
    return normalized.startswith(OPENROUTER_AUTOMATIC_CACHE_MODEL_PREFIXES)
