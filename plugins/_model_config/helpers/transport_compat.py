from __future__ import annotations

from enum import Enum
import re
from typing import Any, Callable

from helpers import context as context_helper
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


class OpenRouterPromptCacheMode(str, Enum):
    """How Agent Zero should ask OpenRouter to cache a model's prompt."""

    AUTOMATIC = "automatic"
    EXPLICIT_BLOCK = "explicit_block"
    PASSIVE = "passive"


# These authors are documented by OpenRouter as using provider-side automatic
# prompt caching. Do not add Anthropic-style cache_control blocks to them: those
# blocks are unnecessary and can force Agent Zero away from Responses.
OPENROUTER_AUTOMATIC_MODEL_PREFIXES = (
    "openai/",
    "x-ai/",
    "moonshotai/",
    "deepseek/",
    "z-ai/",
)

# Alibaba caching is explicit and model-specific. DeepSeek V3.2 is also listed
# by OpenRouter as supported by Alibaba's explicit cache, but DeepSeek itself is
# documented as automatic. Prefer the automatic path so OpenRouter can keep its
# full provider pool and Agent Zero can retain native Responses tool calls.
OPENROUTER_EXPLICIT_BLOCK_MODELS = frozenset(
    {
        "qwen/qwen3-max",
        "qwen/qwen-plus",
        "qwen/qwen3.6-plus",
        "qwen/qwen3-coder-plus",
        "qwen/qwen3-coder-flash",
    }
)

_GEMINI_VERSION = re.compile(r"^google/gemini-(\d+)(?:\.(\d+))?")
_PATCH_MARKER = "_a0_model_config_transport_compat"
_UNSET = object()


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
        if not _is_openrouter_request(self.model, kwargs):
            self.kwargs = kwargs
            original(self)
            return

        slug = _openrouter_model_slug(self.model, kwargs)
        mode = openrouter_prompt_cache_mode(self.model, kwargs)
        explicit_caching = litellm_transport._coerce_bool(
            kwargs.get("a0_explicit_prompt_caching", False),
            default=False,
        )

        # OpenRouter recommends a stable session_id for multi-turn agents. It
        # activates sticky provider routing after the first successful request,
        # before the first cache hit, and therefore keeps the provider-side KV
        # cache warm even when Agent Zero's opening messages evolve.
        session_id = _prepare_openrouter_session(kwargs)

        # Keep OpenAI's cache-affinity parameters in extra_body. LiteLLM 1.88.x
        # can drop OpenRouter-only top-level parameters on some Chat paths, while
        # extra_body is forwarded verbatim by the OpenAI-compatible transport.
        if slug.startswith("openai/"):
            _prepare_openrouter_openai_cache_params(
                kwargs,
                messages=self.messages,
                model=self.model,
                session_id=session_id,
            )

        # A caller-supplied top-level cache_control is an explicit override. It
        # is currently documented by OpenRouter for Anthropic automatic caching
        # and intentionally constrains routing to Anthropic's direct provider.
        # Preserve it verbatim and do not also inject per-block breakpoints.
        manual_top_level_cache = _move_top_level_cache_control(kwargs)

        if explicit_caching and not manual_top_level_cache:
            if mode is OpenRouterPromptCacheMode.EXPLICIT_BLOCK:
                # Anthropic defaults to explicit breakpoints so OpenRouter can
                # keep Bedrock/Vertex fallbacks. The documented Qwen models also
                # require this mode. Core A0 already owns safe marker placement.
                self.kwargs = kwargs
                original(self)
                return

            # Automatic-cache and passive/unknown models must not receive
            # Anthropic-style cache_control markers. The former cache without
            # them; the latter are safer left untouched than forced onto an
            # unsupported caching dialect. Suppressing the markers also keeps
            # native tool turns on Responses when the endpoint supports it.
            kwargs["a0_explicit_prompt_caching"] = False
        elif manual_top_level_cache:
            kwargs["a0_explicit_prompt_caching"] = False

        self.kwargs = kwargs
        original(self)

    setattr(patched_post_init, _PATCH_MARKER, True)
    transport_cls.__post_init__ = patched_post_init


def openrouter_prompt_cache_mode(
    model: str,
    kwargs: dict[str, Any] | None = None,
) -> OpenRouterPromptCacheMode:
    """Return the documented/default prompt-cache strategy for OpenRouter."""
    slug = _openrouter_model_slug(model, kwargs or {})
    if not slug:
        return OpenRouterPromptCacheMode.PASSIVE

    # Anthropic explicit breakpoints work across Anthropic, Bedrock, and Vertex.
    # Top-level automatic cache_control is opt-in via the caller because it
    # currently restricts OpenRouter routing to Anthropic's direct provider.
    if slug.startswith("anthropic/"):
        return OpenRouterPromptCacheMode.EXPLICIT_BLOCK

    # DeepSeek is automatic even though Alibaba also documents an explicit cache
    # path for one DeepSeek model. Automatic wins to preserve provider diversity.
    if slug.startswith("deepseek/"):
        return OpenRouterPromptCacheMode.AUTOMATIC

    if slug in OPENROUTER_EXPLICIT_BLOCK_MODELS:
        return OpenRouterPromptCacheMode.EXPLICIT_BLOCK

    if slug.startswith("google/gemini-"):
        return (
            OpenRouterPromptCacheMode.AUTOMATIC
            if _gemini_uses_implicit_cache(slug)
            else OpenRouterPromptCacheMode.PASSIVE
        )

    if slug.startswith(OPENROUTER_AUTOMATIC_MODEL_PREFIXES):
        return OpenRouterPromptCacheMode.AUTOMATIC

    # OpenRouter says most providers may cache implicitly, but only the families
    # above have a documented contract we can safely encode. Unknown models get
    # no synthetic markers; provider-side implicit caching can still work.
    return OpenRouterPromptCacheMode.PASSIVE


def _gemini_uses_implicit_cache(slug: str) -> bool:
    match = _GEMINI_VERSION.match(slug)
    if not match:
        return False
    version = (int(match.group(1)), int(match.group(2) or 0))
    return version >= (2, 5)


def _is_openrouter_request(model: str, kwargs: dict[str, Any]) -> bool:
    normalized = str(model or "").strip().lower()
    if normalized.startswith("openrouter/"):
        return True
    api_base = str(kwargs.get("api_base") or "").strip().lower()
    return "openrouter.ai" in api_base


def _openrouter_model_slug(model: str, kwargs: dict[str, Any]) -> str:
    if not _is_openrouter_request(model, kwargs):
        return ""

    normalized = str(model or "").strip().lower()
    if normalized.startswith("openrouter/"):
        normalized = normalized[len("openrouter/") :]

    # OpenRouter routing suffixes such as :nitro/:exacto/:free do not change the
    # underlying model's prompt-cache capability.
    return normalized.split(":", 1)[0]


def _ensure_extra_body(kwargs: dict[str, Any]) -> dict[str, Any] | None:
    body = kwargs.get("extra_body")
    if body is None:
        body = {}
    elif not isinstance(body, dict):
        return None
    else:
        body = dict(body)
    kwargs["extra_body"] = body
    return body


def _prepare_openrouter_session(kwargs: dict[str, Any]) -> str:
    body = _ensure_extra_body(kwargs)
    if body is None:
        return ""

    explicit = kwargs.pop("session_id", _UNSET)
    if explicit is not _UNSET:
        body["session_id"] = explicit
    elif "session_id" not in body:
        context_id = str(
            context_helper.get_context_data("agent_context_id", "") or ""
        ).strip()
        if context_id:
            body["session_id"] = f"a0-{context_id}"[:256]

    value = body.get("session_id")
    return str(value) if value is not None else ""


def _prepare_openrouter_openai_cache_params(
    kwargs: dict[str, Any],
    *,
    messages: list[dict[str, Any]],
    model: str,
    session_id: str,
) -> None:
    body = _ensure_extra_body(kwargs)
    if body is None:
        return

    explicit_key = kwargs.pop("prompt_cache_key", _UNSET)
    if explicit_key is not _UNSET:
        body["prompt_cache_key"] = explicit_key
    elif "prompt_cache_key" not in body:
        # Match core Agent Zero's direct-OpenAI strategy: derive the key from the
        # reusable leading prompt and the *actual merged Responses tool catalog*,
        # not the chat id. This avoids steering unrelated tool surfaces onto the
        # same upstream cache-affinity key while still allowing chats with the
        # same stable prefix/tool set to share affinity.
        key_kwargs = dict(kwargs)
        extra_body = key_kwargs.get("extra_body")
        if isinstance(extra_body, dict):
            extra_body = dict(extra_body)
            extra_body.pop("session_id", None)
            extra_body.pop("prompt_cache_key", None)
            key_kwargs["extra_body"] = extra_body

        merged_tools = litellm_transport.ResponsesTransport.merge_response_tools(
            key_kwargs.get("tools"),
            response_function_tools=key_kwargs.get("a0_responses_function_tools"),
            response_builtin_tools=key_kwargs.get("responses_builtin_tools"),
        )
        if merged_tools:
            key_kwargs["tools"] = merged_tools

        cache_key = litellm_transport._default_prompt_cache_key(
            model,
            messages,
            key_kwargs,
        )
        if cache_key:
            body["prompt_cache_key"] = cache_key
        elif session_id:
            # Defensive fallback; generated A0 session ids are well below
            # OpenAI/OpenRouter cache-key limits.
            body["prompt_cache_key"] = session_id

    for key in ("prompt_cache_options", "prompt_cache_retention"):
        explicit = kwargs.pop(key, _UNSET)
        if explicit is not _UNSET:
            body[key] = explicit


def _move_top_level_cache_control(kwargs: dict[str, Any]) -> bool:
    body = _ensure_extra_body(kwargs)
    if body is None:
        return False

    explicit = kwargs.pop("cache_control", _UNSET)
    if explicit is not _UNSET:
        body["cache_control"] = explicit
    return "cache_control" in body
