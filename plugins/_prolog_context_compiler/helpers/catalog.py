from __future__ import annotations

import json
import threading
from typing import Any

from helpers import files, skills as skills_helper
from helpers.responses_tools import (
    _local_tool_prompts,
    _mcp_tools,
    build_responses_function_tools,
)


_PERMANENT_TOOL_LOCK = threading.Lock()
_PERMANENT_TOOLS = {
    "response",
    "text_editor",
    "code_execution_tool",
    "call_subordinate",
    "input",
    "wait",
    "skills_tool",
    "prolog_rlm",
}

_TOOL_EFFECTS = {
    "response": "read",
    "input": "read",
    "wait": "read",
    "notify_user": "read",
    "text_editor": "write",
    "code_execution_tool": "process",
    "exec": "process",
    "git": "read",
    "patch": "write",
    "call_subordinate": "process",
    "parallel": "process",
    "browser": "network_write",
    "search_engine": "network_write",
    "memory": "write",
    "scheduler": "write",
    "skills_tool": "read",
}

_TOOL_CATEGORIES = {
    "response": "agent",
    "input": "agent",
    "wait": "agent",
    "notify_user": "agent",
    "skills_tool": "agent",
    "goal": "agent",
    "text_editor": "filesystem",
    "document_query": "filesystem",
    "office_artifact": "filesystem",
    "code_execution_tool": "process",
    "exec": "process",
    "git": "git",
    "patch": "filesystem",
    "call_subordinate": "process",
    "parallel": "process",
    "system_jobs": "process",
    "browser": "network",
    "search_engine": "network",
    "a2a_chat": "network",
    "memory": "persistence",
    "memory_load": "persistence",
    "scheduler": "persistence",
    "prolog_rlm": "symbolic",
}


def register_permanent_tools(*names: str) -> None:
    """Code-owned adapter API for tools that must survive every projection."""

    normalized = {str(name).strip() for name in names if str(name).strip()}
    with _PERMANENT_TOOL_LOCK:
        _PERMANENT_TOOLS.update(normalized)


def permanent_tools(config: dict[str, Any]) -> set[str]:
    from plugins._prolog_rlm import hooks as prolog_rlm_hooks

    prolog_rlm_hooks.register_context_tools()
    with _PERMANENT_TOOL_LOCK:
        registered = set(_PERMANENT_TOOLS)
    registered.update(str(name) for name in config.get("permanent_tools", []))
    registered.update(str(name) for name in config.get("mandatory_tools", []))
    return registered


def build_compile_request(
    agent: Any,
    system_prompt: list[str],
    loop_data: Any,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Gather bounded inert host metadata; selection remains in Prolog."""

    mandatory_tools = permanent_tools(config)
    units: list[dict[str, Any]] = []
    for index, section in enumerate(system_prompt):
        text = str(section or "").strip()
        if not text:
            continue
        units.append(
            {
                "kind": "instruction",
                "format": "agent_zero_context",
                "name": f"system_{index:03d}",
                "description": f"Agent Zero system section {index}",
                "content": text,
                "permanent": True,
            }
        )

    units.append(
        {
            "kind": "instruction",
            "format": "agent_zero_context",
            "name": "tool_protocol",
            "description": "Provider-visible tool use contract",
            "content": (
                "## available tools\nUse only the tools selected below. Tool visibility "
                "does not grant execution authority."
            ),
            "permanent": True,
        }
    )

    native_tools, name_map = build_responses_function_tools(agent)
    schemas = {
        name_map.get(str(tool.get("name") or ""), str(tool.get("name") or "")): tool.get(
            "parameters"
        )
        or {}
        for tool in native_tools
        if tool.get("type") == "function"
    }

    seen: set[str] = set()
    for name, prompt in _local_tool_prompts(agent):
        if name in seen:
            continue
        seen.add(name)
        units.append(
            {
                "kind": "tool",
                "format": "agent_zero_tool",
                "name": name,
                "description": _description(prompt, name),
                "content": prompt,
                "compact": _compact_prompt(prompt),
                "schema": schemas.get(name, {}),
                "effect": _TOOL_EFFECTS.get(name, "write"),
                "category": _TOOL_CATEGORIES.get(name, "agent_zero"),
                "permanent": name in mandatory_tools,
            }
        )

    for name, tool in _mcp_tools(agent):
        if name in seen:
            continue
        seen.add(name)
        description = str(tool.get("description") or name).strip()
        schema = tool.get("input_schema") or schemas.get(name, {})
        server = str(tool.get("server") or name.partition(".")[0] or "mcp")
        units.append(
            {
                "kind": "mcp_tool",
                "format": "agent_zero_tool",
                "server": server,
                "name": name,
                "description": description,
                "content": _mcp_prompt(name, description, schema),
                "compact": f"### {name}\n{description}",
                "schema": schema,
                "effect": "network_write",
                "category": "mcp",
                "permanent": name in mandatory_tools,
            }
        )

    if config.get("compile_skills", True):
        for skill in skills_helper.list_skills(agent=agent):
            name = str(skill.name or "").strip()
            if not name:
                continue
            description = str(skill.description or "").strip()
            units.append(
                {
                    "kind": "skill",
                    "format": "agent_zero_skill",
                    "name": name,
                    "description": description,
                    "content": f"Available skill `{name}`: {description}".strip(),
                    "permanent": False,
                }
            )

    return {
        "message": _user_message(loop_data),
        "max_context_tokens": int(config.get("max_context_tokens", 16384)),
        "units": units,
    }


def _description(prompt: str, fallback: str) -> str:
    for line in str(prompt or "").splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped and stripped.lower() not in {fallback.lower(), f"{fallback}:"}:
            return stripped[:1000]
    return fallback


def _mcp_prompt(name: str, description: str, schema: Any) -> str:
    schema_text = json.dumps(schema, ensure_ascii=False, sort_keys=True)
    return (
        f"### {name}\n{description}\n"
        f"Input schema for tool_args: {schema_text}"
    )


def _compact_prompt(prompt: str) -> str:
    """Remove fenced examples while retaining the callable prose contract."""

    compact = files.remove_fenced_blocks(str(prompt or ""), "json")
    return "\n".join(
        line
        for line in compact.splitlines()
        if not line.lstrip().startswith("Input schema for tool_args:")
    )


def _user_message(loop_data: Any) -> str:
    message = getattr(loop_data, "user_message", None)
    if message is None:
        return ""
    content = getattr(message, "content", "")
    if isinstance(content, dict):
        return str(content.get("user_message") or content.get("message") or "")
    output_text = getattr(message, "output_text", None)
    if callable(output_text):
        return str(output_text())
    return str(content or "")
