"""Core-loop model proxy: route Agent Zero chat turns through Prolog-RLM.

The proxy replaces the chat model object during the main loop
(``chat_model_call_before``). It keeps the inner A0 model untouched for
direct mode and hands symbolic / symbolic-recursive / auto turns to the
Prolog-RLM runtime, which owns mode policy, recursion depth, and context
budget enforcement. No host-side effect admission happens here.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from plugins._prolog_rlm.helpers.harness import PrologRLM, shared_harness

REASONING_MODES = ("auto", "direct", "symbolic", "symbolic-recursive")
DIRECT = "direct"
SYMBOLIC = "symbolic"
SYMBOLIC_RECURSIVE = "symbolic-recursive"
AUTO = "auto"


def context_budget_tokens(ctx_length: int, percent: int) -> int:
    """Resolve the chat-visible context budget against the model window."""
    if ctx_length <= 0:
        return 0
    return max(0, int(int(ctx_length) * int(percent) / 100))


def completion_budget(
    context_budget_tokens: int, mode: str
) -> dict[str, Any]:
    budget: dict[str, Any] = {
        "context_budget_tokens": context_budget_tokens,
    }
    if mode == SYMBOLIC:
        budget["max_recursion_depth"] = 1
    elif mode == SYMBOLIC_RECURSIVE:
        budget["max_recursion_depth"] = 3
    return budget


def mode_budget_tokens(ctx_length: int, percent: int, mode: str) -> dict[str, Any]:
    return completion_budget(context_budget_tokens(ctx_length, percent), mode)


def _message_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content)


def _flatten_messages_text(messages: Any) -> str:
    parts = [_message_text(message) for message in messages or []]
    return "\n".join(part for part in parts if part)


class PrologRLMModel:
    """Model-object proxy that makes Prolog-RLM own main-loop turn policy."""

    def __init__(
        self,
        inner: Any,
        harness: PrologRLM,
        *,
        reasoning_mode: str = AUTO,
        context_budget_percent: int = 30,
        completion_timeout: float = 300.0,
    ) -> None:
        if reasoning_mode not in REASONING_MODES:
            raise ValueError(f"unsupported reasoning mode: {reasoning_mode}")
        self.inner = inner
        self.harness = harness
        self.reasoning_mode = reasoning_mode
        self.context_budget_percent = int(context_budget_percent)
        self.completion_timeout = float(completion_timeout)

    @property
    def model_name(self) -> str:
        return getattr(self.inner, "model_name", "")

    @property
    def kwargs(self) -> dict:
        return getattr(self.inner, "kwargs", {}) or {}

    @property
    def a0_model_conf(self):
        return getattr(self.inner, "a0_model_conf", None)

    async def unified_call(self, *args: Any, **kwargs: Any) -> tuple[str, str]:
        result = await self.unified_turn(*args, **kwargs)
        return result.response, result.reasoning

    async def unified_turn(
        self,
        system_message: str = "",
        user_message: str = "",
        messages: list | None = None,
        response_callback: Callable[[str, str], Awaitable[str | None]] | None = None,
        reasoning_callback: Callable[[str, str], Awaitable[None]] | None = None,
        tokens_callback: Callable[[str, int], Awaitable[None]] | None = None,
        rate_limiter_callback: Callable | None = None,
        explicit_caching: bool = False,
        **kwargs: Any,
    ):
        mode = self.reasoning_mode
        if mode == DIRECT:
            return await self.inner.unified_turn(
                system_message=system_message,
                user_message=user_message,
                messages=messages,
                response_callback=response_callback,
                reasoning_callback=reasoning_callback,
                tokens_callback=tokens_callback,
                rate_limiter_callback=rate_limiter_callback,
                explicit_caching=explicit_caching,
                **kwargs,
            )

        # The runtime completion contract requires non-empty query text
        # (runtime_worker.pl rejects empty queries). Tool-call-only
        # continuations arrive with an empty user_message and all content in
        # messages: derive the query from the newest message and keep the
        # rest as context so the turn still routes through the runtime.
        query = str(user_message or "").strip()
        prior = list(messages or [])
        if not query and prior:
            query = _message_text(prior[-1]).strip()
            prior = prior[:-1]
        context = _flatten_messages_text(prior)
        if system_message:
            context = f"{system_message}\n{context}"
        if not query:
            # Degenerate turn with no queryable text anywhere; the runtime
            # cannot route it, so fall through to the inner model exactly
            # like direct mode. This is not a runtime-failure downgrade.
            return await self.inner.unified_turn(
                system_message=system_message,
                user_message=user_message,
                messages=messages,
                response_callback=response_callback,
                reasoning_callback=reasoning_callback,
                tokens_callback=tokens_callback,
                rate_limiter_callback=rate_limiter_callback,
                explicit_caching=explicit_caching,
                **kwargs,
            )
        result = await self.harness.complete(
            query,
            context,
            budget=mode_budget_tokens(
                self._ctx_length(), self.context_budget_percent, mode
            ),
            timeout=self.completion_timeout,
        )
        text = _outcome_text(result.payload)
        if text and response_callback is not None:
            await response_callback(text, text)
        return _turn_result(self.inner, text, "")

    def _ctx_length(self) -> int:
        config = self.a0_model_conf
        ctx = getattr(config, "ctx_length", 0) if config is not None else 0
        try:
            return int(ctx or 0)
        except (TypeError, ValueError):
            return 0


def _turn_result(inner: Any, text: str, reasoning: str):
    from helpers.llm_result import LLMResult

    return LLMResult(
        response=text,
        reasoning=reasoning,
        mode="responses",
        state="runtime",
        capability={"runtime": "prolog-rlm"},
    )


def _outcome_text(payload: Any) -> str:
    if isinstance(payload, dict):
        value = payload.get("value")
        if isinstance(value, dict):
            for key in ("text", "response"):
                text = value.get(key)
                if isinstance(text, str) and text.strip():
                    return text
            response = value.get("response")
            if isinstance(response, dict):
                text = response.get("text")
                if isinstance(text, str) and text.strip():
                    return text
    return ""


def _config_bool(settings: dict[str, Any], key: str, default: bool) -> bool:
    value = settings.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def _config_number(settings: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(str(settings.get(key, default)).strip())
    except (TypeError, ValueError):
        return default


def wrap_chat_model(
    model: Any,
    config: dict[str, Any] | None = None,
    harness: PrologRLM | None = None,
) -> Any:
    """Wrap the chat model when the core-loop runtime policy is enabled."""
    settings = config or {}
    if not _config_bool(settings, "core_loop_enabled", False):
        return model
    mode = str(settings.get("reasoning_mode") or AUTO).strip().lower()
    harness = harness or shared_harness(settings)
    return PrologRLMModel(
        model,
        harness,
        reasoning_mode=mode,
        context_budget_percent=int(
            _config_number(settings, "context_budget_percent", 30.0)
        ),
        completion_timeout=_config_number(
            settings, "completion_timeout_seconds", 300.0
        ),
    )
