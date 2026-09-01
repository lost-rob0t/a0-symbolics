from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

from langchain_core.messages import BaseMessage, SystemMessage

from helpers import plugins, skills, tokens
from helpers.llm_result import LLMResult, ResponseItem
from helpers.responses_tools import build_responses_function_tools
from plugins._model_config.helpers.model_config import get_chat_model_config
from plugins._prolog_rlm.helpers.bridge import (
    PrologRuntimeBridgeError,
    shared_runtime_bridge,
)


PLUGIN_NAME = "_prolog_rlm"
CTX_WINDOW_KEY = "ctx_window"
TOOL_NAME_MAP_KEY = "responses_tool_name_map"
MAX_CONTEXT_UNIT_CHARS = 30_000
# Keep the final-response surface and Agent Zero's skill discovery/loading surface
# permanently available. Prolog still decides which non-permanent tools and
# ordinary skill packages are relevant for each turn.
PERMANENT_TOOLS = {"response", "skills_tool"}
TOOL_EFFECTS = {
    "response": "read",
    "input": "read",
    "wait": "read",
    "notify_user": "read",
    "skills_tool": "read",
    "memory_load": "read",
    "text_editor": "write",
    "code_execution_tool": "process",
    "call_subordinate": "process",
    "parallel": "process",
    "browser": "network_write",
    "search_engine": "network_write",
    "scheduler": "write",
    "system_jobs": "process",
}


def build_turn_request(
    agent: Any,
    messages: list[BaseMessage],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = config or {}
    model_config = get_chat_model_config(agent)
    provider = str(model_config.get("provider") or "").strip().lower()
    if provider != "openrouter":
        raise PrologRuntimeBridgeError(
            "Prolog-RLM model routing currently requires an OpenRouter chat preset"
        )
    model = str(
        settings.get("openrouter_model") or model_config.get("name") or ""
    ).strip()
    model = model.removeprefix("openrouter/")
    if not model:
        raise PrologRuntimeBridgeError("Prolog-RLM model routing requires a model")

    native_tools, name_map = build_responses_function_tools(agent)
    agent.set_data(TOOL_NAME_MAP_KEY, name_map)
    tools = [_openai_tool(tool) for tool in native_tools if _valid_native_tool(tool)]
    system, body = _split_system(messages)
    recent_count = max(1, int(settings.get("recent_message_count", 8)))
    recent = body[-recent_count:]
    older = body[:-recent_count]
    message = _last_user_text(body)
    if not message:
        raise PrologRuntimeBridgeError("Prolog-RLM turn has no user message")

    units = []
    if system:
        _append_context_units(
            units,
            kind="instruction",
            name="agent_zero_system",
            description="Current Agent Zero system contract",
            content=_message_content(system),
            permanent=True,
        )
    for index, old_message in enumerate(older):
        content = _message_content(old_message)
        if content:
            _append_context_units(
                units,
                kind="resource",
                name=f"history_{index:04d}",
                description="Earlier Agent Zero conversation turn",
                content=content,
                permanent=False,
            )

    skill_packages, selected_skills = _skill_projection(agent)

    for tool in native_tools:
        if not _valid_native_tool(tool):
            continue
        name = str(tool["name"])
        units.append(
            {
                "kind": "tool",
                "format": "agent_zero_tool",
                "name": name,
                "description": str(tool.get("description") or name),
                "content": str(tool.get("description") or name),
                "compact": str(tool.get("description") or name),
                "schema": tool["parameters"],
                "effect": TOOL_EFFECTS.get(name, "write"),
                "permanent": name in PERMANENT_TOOLS,
            }
        )

    return {
        "model": model,
        "context_window": int(model_config.get("ctx_length") or 128_000),
        "max_completion_tokens": max(
            1, int(settings.get("max_completion_tokens", 4096))
        ),
        "messages": [_model_message(item) for item in recent],
        "tools": tools,
        "compile_request": {
            "message": message,
            "max_context_tokens": max(
                1024, int(settings.get("max_context_tokens", 32_768))
            ),
            "units": units,
            # Agent Zero owns visibility/precedence and passes only the exact
            # admitted package directories. Prolog-RLM owns SKILL.md parsing,
            # canonical metadata, selection, and graph validation.
            "skill_packages": skill_packages,
            "selected_skills": selected_skills,
            "include_core_skills": bool(settings.get("include_core_skills", True)),
        },
    }


def _skill_projection(agent: Any) -> tuple[list[dict[str, str]], list[str]]:
    """Return Agent Zero-visible packages plus current-chat pinned skill names.

    `helpers.skills.list_skills` already applies Agent Zero's root precedence,
    project/profile scope and hidden-skill policy. We deliberately pass exact
    package directories rather than broad roots so the Prolog loader cannot
    rediscover hidden or shadowed siblings. The loaded-skill ledger is only a
    host selection hint; Prolog-RLM still validates every selected name against
    the normalized catalog and never gains tool authority from skill metadata.
    """
    visible = skills.list_skills(
        agent=agent,
        include_content=False,
        include_hidden=False,
    )
    packages: list[dict[str, str]] = []
    visible_names: set[str] = set()
    for skill in visible:
        name = str(skill.name or skill.path.name).strip()
        path = str(skill.path).strip()
        if not name or not path or name in visible_names:
            continue
        visible_names.add(name)
        packages.append({"name": name, "path": path})

    selected = [
        name
        for name in skills.get_loaded_skill_names(agent)
        if name in visible_names
    ]
    return packages, selected


async def route_model_turn(
    agent: Any,
    messages: list[BaseMessage],
    *,
    response_callback: Callable[[str, str], Awaitable[str | None]] | None = None,
    reasoning_callback: Callable[[str, str], Awaitable[None]] | None = None,
) -> LLMResult:
    config = plugins.get_plugin_config(PLUGIN_NAME, agent=agent) or {}
    request = build_turn_request(agent, messages, config)
    turn = await asyncio.to_thread(shared_runtime_bridge(config).call, "turn", request)
    result = _llm_result(turn, request)

    if result.reasoning and reasoning_callback:
        await reasoning_callback(result.reasoning, result.reasoning)
    if result.response and not result.function_calls and response_callback:
        await response_callback(result.response, result.response)

    _record_context_usage(agent, turn, request)
    return result


def _llm_result(turn: dict[str, Any], request: dict[str, Any]) -> LLMResult:
    calls = []
    for raw_call in turn.get("tool_calls") or []:
        function = raw_call.get("function") if isinstance(raw_call, dict) else None
        if not isinstance(function, dict) or not function.get("name"):
            continue
        calls.append(
            ResponseItem(
                type="function_call",
                data={
                    "type": "function_call",
                    "id": str(raw_call.get("id") or ""),
                    "call_id": str(raw_call.get("id") or ""),
                    "name": str(function["name"]),
                    "arguments": function.get("arguments") or "{}",
                },
            )
        )
    text = str(turn.get("text") or "")
    reasoning = str(turn.get("reasoning") or "")
    items = list(calls)
    if text:
        items.append(
            ResponseItem(
                type="message",
                data={
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": text}],
                },
            )
        )
    result = LLMResult(
        response=text,
        reasoning=reasoning,
        output_items=items,
        provider_model_key=f"prolog-rlm/openrouter/{turn.get('selected_model') or request['model']}",
        mode="responses",
        state="off",
        usage=dict(turn.get("usage") or {}),
        raw=dict(turn),
        capability={"prolog_rlm": True, "context_compiled": True, "skills": True},
    )
    if not result.response and result.function_calls:
        result.response = result.function_calls_text()
    return result


def _record_context_usage(
    agent: Any, turn: dict[str, Any], request: dict[str, Any]
) -> None:
    usage = turn.get("usage") or {}
    prompt_tokens = _positive_int(usage.get("prompt_tokens"))
    source = "prolog_rlm_provider_usage"
    estimated = False
    if prompt_tokens is None:
        projection = turn.get("projection") or {}
        ledger = projection.get("token_ledger") or {}
        prompt_tokens = _positive_int(ledger.get("selected_context_tokens"))
        source = "prolog_rlm_context_ledger"
        estimated = True
    if prompt_tokens is None:
        prompt_tokens = tokens.approximate_prompt_tokens(
            json.dumps(request, ensure_ascii=False, sort_keys=True, default=str)
        )
        source = "prolog_rlm_request_estimate"
        estimated = True
    agent.set_data(
        CTX_WINDOW_KEY,
        {
            "tokens": prompt_tokens,
            "context_window": request["context_window"],
            "source": source,
            "estimated": estimated,
            "projection": turn.get("projection") or {},
        },
    )


def _openai_tool(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": str(tool["name"]),
            "description": str(tool.get("description") or tool["name"]),
            "parameters": dict(tool["parameters"]),
        },
    }


def _append_context_units(
    units: list[dict[str, Any]],
    *,
    kind: str,
    name: str,
    description: str,
    content: str,
    permanent: bool,
) -> None:
    chunks = [
        content[offset : offset + MAX_CONTEXT_UNIT_CHARS]
        for offset in range(0, len(content), MAX_CONTEXT_UNIT_CHARS)
    ] or [""]
    for index, chunk in enumerate(chunks):
        chunk_name = name if len(chunks) == 1 else f"{name}_{index:04d}"
        units.append(
            {
                "kind": kind,
                "format": "agent_zero_context",
                "name": chunk_name,
                "description": description,
                "content": chunk,
                "permanent": permanent,
            }
        )


def _valid_native_tool(tool: Any) -> bool:
    return (
        isinstance(tool, dict)
        and tool.get("type") == "function"
        and bool(tool.get("name"))
        and isinstance(tool.get("parameters"), dict)
    )


def _split_system(
    messages: list[BaseMessage],
) -> tuple[BaseMessage | None, list[BaseMessage]]:
    if messages and isinstance(messages[0], SystemMessage):
        return messages[0], list(messages[1:])
    return None, list(messages)


def _last_user_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if str(getattr(message, "type", "")) in {"human", "user"}:
            return _message_content(message)
    return ""


def _model_message(message: BaseMessage) -> dict[str, Any]:
    role = {
        "human": "user",
        "user": "user",
        "ai": "assistant",
        "assistant": "assistant",
        "system": "system",
        "tool": "tool",
    }.get(str(getattr(message, "type", "")), "user")
    return {"role": role, "content": _message_content(message)}


def _message_content(message: BaseMessage) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True, default=str)


def _positive_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None
