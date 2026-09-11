"""Core-loop model proxy: route Agent Zero chat turns through Prolog-RLM.

The proxy replaces the chat model object during the main loop
(``chat_model_call_before``). Every routed turn first compiles its context
through the Prolog context compiler (via the runtime ``context_compile``
surface), then dispatches to the runtime: direct mode runs the bounded
provider-native direct agent loop, symbolic modes run the symbolic
completion. The runtime owns mode policy, recursion depth, and context
budget enforcement. No host-side effect admission happens here.
"""

from __future__ import annotations

import asyncio
import uuid
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
    if mode in (DIRECT, SYMBOLIC):
        budget["max_recursion_depth"] = 1
    elif mode == SYMBOLIC_RECURSIVE:
        budget["max_recursion_depth"] = 3
    return budget


def mode_budget_tokens(ctx_length: int, percent: int, mode: str) -> dict[str, Any]:
    return completion_budget(context_budget_tokens(ctx_length, percent), mode)


_MAX_COMPILED_UNITS = 192
_MAX_COMPILED_UNIT_CHARS = 12_000
_MAX_SYSTEM_UNIT_CHARS = 30_000
_MAX_TOOL_DECLARATIONS = 64
_RUNTIME_NATIVE_TOOLS = {"response"}


def _split_system_text(system_text: str) -> list[str]:
    """Split the rendered system prompt into compiler-bounded sections.

    The prompt compiler rejects any single input text above 32768 chars
    (``input_too_large``); split on paragraph boundaries so the full prompt
    survives as multiple permanent instruction units.
    """
    if len(system_text) <= _MAX_SYSTEM_UNIT_CHARS:
        return [system_text]
    sections: list[str] = []
    current = ""
    for part in system_text.split("\n\n"):
        candidate = f"{current}\n\n{part}" if current else part
        if len(candidate) > _MAX_SYSTEM_UNIT_CHARS and current:
            sections.append(current)
            current = part
        else:
            current = candidate
    if current:
        sections.append(current)
    return sections


def collect_tool_declarations(agent: Any, compiler_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect the agent's enabled tool declarations through the compiler.

    This is the context compiler's canonical collector (the same surface the
    ``validate_tools`` action uses); the runtime compiler stays the sole
    authority over which tools a turn actually gets.
    """
    if agent is None:
        return []
    try:
        from plugins._prolog_context_compiler.helpers.catalog import build_compile_request

        request = build_compile_request(agent, [], getattr(agent, "loop_data", None), compiler_config)
    except Exception:
        return []
    units = []
    for unit in request.get("units", []):
        if str(unit.get("kind") or "") not in {"tool", "mcp_tool"}:
            continue
        name = str(unit.get("name") or "")
        if not name or name in _RUNTIME_NATIVE_TOOLS:
            continue
        units.append(unit)
        if len(units) >= _MAX_TOOL_DECLARATIONS:
            break
    return units


def compile_context_request(
    query: str,
    prior: list | None,
    system_message: str = "",
    max_context_tokens: int = 0,
    tool_units: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a bounded inert compile request; selection remains in Prolog."""
    units: list[dict[str, Any]] = []
    system_text = str(system_message or "").strip()
    if system_text:
        for index, section in enumerate(_split_system_text(system_text)):
            if not section.strip():
                continue
            units.append(
                {
                    "kind": "instruction",
                    "format": "agent_zero_context",
                    "name": f"chat_system_{index:03d}",
                    "description": "Agent Zero system prompt",
                    "content": section,
                    "permanent": True,
                }
            )
    for unit in tool_units or []:
        units.append(dict(unit))
        if len(units) >= _MAX_COMPILED_UNITS:
            break
    for index, message in enumerate(prior):
        content = _message_text(message).strip()
        if not content:
            continue
        role = str(
            getattr(message, "role", "")
            or getattr(message, "type", "")
            or "message"
        )
        units.append(
            {
                "kind": "resource",
                "format": "agent_zero_context",
                "name": f"chat_turn_{index:04d}_{role}",
                "description": f"Prior Agent Zero {role} message",
                "content": content[:_MAX_COMPILED_UNIT_CHARS],
                "permanent": False,
            }
        )
        if len(units) >= _MAX_COMPILED_UNITS:
            break
    request: dict[str, Any] = {"message": query, "units": units}
    if max_context_tokens > 0:
        request["max_context_tokens"] = int(max_context_tokens)
    return request


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
        agent: Any = None,
        declarations: list[dict[str, Any]] | None = None,
    ) -> None:
        if reasoning_mode not in REASONING_MODES:
            raise ValueError(f"unsupported reasoning mode: {reasoning_mode}")
        self.inner = inner
        self.harness = harness
        self.reasoning_mode = reasoning_mode
        self.context_budget_percent = int(context_budget_percent)
        self.completion_timeout = float(completion_timeout)
        self.agent = agent
        self.declarations = list(declarations or [])
        self._loop: asyncio.AbstractEventLoop | None = None

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
        budget = mode_budget_tokens(
            self._ctx_length(), self.context_budget_percent, self.reasoning_mode
        )
        tool_units = list(self.declarations)
        context = await self._compiled_context(query, prior, system_message, tool_units)
        if self.reasoning_mode == DIRECT:
            session = uuid.uuid4().hex
            selected = _select_active_declarations(
                _active_tools(self._compiled_payload), tool_units
            )
            if selected:
                self._loop = asyncio.get_running_loop()
                self.harness.register_tool_handler(session, self._tool_callback)
            try:
                result = await self.harness.direct(
                    query,
                    context=context,
                    budget=budget,
                    declarations=selected,
                    session=session,
                    timeout=self.completion_timeout,
                )
            finally:
                if selected:
                    self.harness.unregister_tool_handler(session)
            text = _direct_text(result.payload)
        else:
            result = await self.harness.complete(
                query,
                context,
                budget=budget,
                timeout=self.completion_timeout,
            )
            text = _outcome_text(result.payload)
        if text and response_callback is not None:
            await response_callback(text, text)
        return _turn_result(self.inner, text, "")

    async def _compiled_context(
        self, query: str, prior: list, system_message: str,
        tool_units: list[dict[str, Any]] | None = None,
    ) -> str:
        request = compile_context_request(
            query,
            prior,
            system_message,
            context_budget_tokens(
                self._ctx_length(), self.context_budget_percent
            ),
            tool_units=tool_units,
        )
        result = await self.harness.compile(request)
        self._compiled_payload = (
            result.payload if isinstance(result.payload, dict) else {}
        )
        return _projection_text(result.payload)

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Run one tool call through the normal Agent Zero tool lifecycle."""
        from helpers import extension as ext

        agent = self.agent
        if agent is None:
            raise RuntimeError("no agent bound for runtime tool execution")
        safe_args = dict(args or {})
        tool = agent.get_tool(name, None, safe_args, "", getattr(agent, "loop_data", None))
        await tool.before_execution(**safe_args)
        await ext.call_extensions_async(
            "tool_execute_before", agent, tool_args=safe_args, tool_name=name
        )
        response = await tool.execute(**safe_args)
        await ext.call_extensions_async(
            "tool_execute_after", agent, response=response, tool_name=name
        )
        await tool.after_execution(response)
        value = getattr(response, "message", "") or ""
        return {"value": str(value), "truncated": False}

    def _tool_callback(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Trusted host handler invoked by the worker's callback frames.

        Runs on the harness's worker thread; the actual execution marshals
        back into the framework event loop that created this proxy.
        """
        future = asyncio.run_coroutine_threadsafe(
            self._execute_tool(name, args), self._loop
        )
        return future.result(timeout=self.completion_timeout)

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


def _projection_text(payload: Any) -> str:
    if isinstance(payload, dict):
        text = payload.get("text")
        if isinstance(text, str) and text.strip():
            return text
    return ""


def _direct_text(payload: Any) -> str:
    if isinstance(payload, dict):
        value = payload.get("value")
        if isinstance(value, str) and value.strip():
            return value
        text = payload.get("text")
        if isinstance(text, str) and text.strip():
            return text
    return ""


def _outcome_text(payload: Any) -> str:
    if isinstance(payload, dict):
        value = payload.get("value")
        if isinstance(value, str) and value.strip():
            return value
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


def _active_tools(payload: Any) -> list[str]:
    """Compiler-selected active tool names from a context_compile outcome."""
    if isinstance(payload, dict):
        value = payload.get("active_tools")
        if isinstance(value, list):
            return [str(item) for item in value if item]
    return []


def _select_active_declarations(
    active: list[str], declarations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Keep the declarations the runtime compiler activated for this turn.

    Selection is entirely Prolog-side: the compile outcome names the tools,
    this only projects the inert metadata the runtime already validated.
    """
    if not active:
        return []
    selected_names = set(active) - _RUNTIME_NATIVE_TOOLS
    return [
        unit
        for unit in declarations
        if str(unit.get("name") or "") in selected_names
    ]


def wrap_chat_model(
    model: Any,
    config: dict[str, Any] | None = None,
    harness: PrologRLM | None = None,
    agent: Any = None,
    declarations: list[dict[str, Any]] | None = None,
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
        agent=agent,
        declarations=declarations or [],
    )
