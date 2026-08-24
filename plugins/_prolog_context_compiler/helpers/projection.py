from __future__ import annotations

from typing import Any

ACTIVE_CONTEXT_KEY = "_prolog_context_projection"


def filter_native_tools(
    agent: Any,
    tools: list[dict[str, Any]] | None,
    name_map: dict[str, str] | None,
) -> list[dict[str, Any]]:
    """Narrow an already-authorized schema list to the compiled projection."""

    available = list(tools or [])
    get_data = getattr(agent, "get_data", None)
    projection = get_data(ACTIVE_CONTEXT_KEY) if callable(get_data) else None
    if not isinstance(projection, dict):
        return available
    active = projection.get("active_tools")
    if not isinstance(active, list):
        return available
    active_names = {str(name) for name in active}
    return [
        tool
        for tool in available
        if (name_map or {}).get(
            str(tool.get("name") or ""), str(tool.get("name") or "")
        )
        in active_names
    ]
