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
        provider = litellm_transport._normalized_provider(self.model, kwargs)

        # OpenRouter cache_control markers intentionally route through Chat
        # Completions. For Agent Zero native-tool turns that loses the stronger
        # Responses function-call contract and some models emit textual
        # pseudo-tool syntax instead. Keep those turns on Responses while
        # preserving the existing cache behavior for ordinary OpenRouter calls.
        if explicit_caching and has_a0_function_tools and provider == "openrouter":
            kwargs["a0_explicit_prompt_caching"] = False
            self.kwargs = kwargs
            original(self)
            self.explicit_prompt_caching = True
            return

        original(self)

    setattr(patched_post_init, _PATCH_MARKER, True)
    transport_cls.__post_init__ = patched_post_init
