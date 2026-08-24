from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import BaseMessage, SystemMessage


def build_working_context_request(
    messages: list[BaseMessage],
    current_message: str,
    config: dict[str, Any],
) -> tuple[dict[str, Any], list[BaseMessage], BaseMessage | None]:
    """Build bounded inert history/DOX units; Prolog decides what remains visible."""

    if not messages:
        return {"message": current_message, "units": []}, [], None
    system = messages[0] if isinstance(messages[0], SystemMessage) else None
    body = messages[1:] if system is not None else messages
    recent_count = max(1, int(config.get("recent_message_count", 8)))
    recent = list(body[-recent_count:])
    candidates = list(body[:-recent_count])
    max_units = max(1, int(config.get("max_working_units", 192)))
    max_chars = max(1000, int(config.get("max_working_unit_chars", 12_000)))

    instruction_units: list[dict[str, Any]] = []
    context_units: list[dict[str, Any]] = []
    for index, message in enumerate(candidates):
        content = _message_content(message)
        if not content:
            continue
        role = str(getattr(message, "type", "message") or "message")
        is_dox = _is_current_instruction(content)
        unit = {
            "kind": "instruction" if is_dox else "resource",
            "format": "dox" if is_dox else "agent_zero_context",
            "name": f"working_{index:04d}_{role}",
            "description": (
                "Current Agent Zero project/DOX instructions"
                if is_dox
                else f"Prior Agent Zero {role} message"
            ),
            "content": f"[{role}]\n{content[:max_chars]}",
            "permanent": is_dox,
        }
        (instruction_units if is_dox else context_units).append(unit)

    available = max(0, max_units - len(instruction_units))
    units = instruction_units + context_units[-available:] if available else instruction_units
    return (
        {
            "message": current_message,
            "max_context_tokens": int(config.get("working_context_tokens", 12_000)),
            "units": units,
        },
        recent,
        system,
    )


def projected_messages(
    system: BaseMessage | None,
    projection_text: str,
    recent: list[BaseMessage],
) -> list[BaseMessage]:
    result: list[BaseMessage] = []
    if system is not None:
        result.append(system)
    if projection_text.strip():
        result.append(
            SystemMessage(
                content=(
                    "## Prolog-RLM selected prior context\n"
                    "This is bounded evidence from earlier messages and current DOX.\n\n"
                    + projection_text.strip()
                )
            )
        )
    result.extend(recent)
    return result


def provider_payload_tokens(
    messages: list[BaseMessage], tools: list[dict[str, Any]]
) -> int:
    from helpers import tokens

    payload = {
        "messages": [
            {
                "role": str(getattr(message, "type", "message")),
                "content": _message_content(message),
            }
            for message in messages
        ],
        "tools": tools,
    }
    return tokens.approximate_tokens(
        json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )


def _message_content(message: BaseMessage) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True, default=str)


def _is_current_instruction(content: str) -> bool:
    lowered = content[:600].lower()
    return any(
        marker in lowered
        for marker in (
            "# project instructions",
            "# agents.md instructions",
            "active project instructions",
            "project context may be active",
        )
    )
