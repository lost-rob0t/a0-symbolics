"""Runtime policy API for the Prolog-RLM chat control (mode + budget)."""
from __future__ import annotations

from typing import Any

from helpers.api import ApiHandler, Input, Output, Request, Response
from helpers import plugins


PLUGIN_NAME = "_prolog_rlm"
_VALID_MODES = {"auto", "direct", "symbolic", "symbolic-recursive"}


def _clamp_percent(value: object, default: int = 30) -> int:
    try:
        percent = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return min(100, max(1, percent))


class RuntimePolicy(ApiHandler):
    """Read or update reasoning mode and context budget from the chat UI."""

    async def process(self, input: Input, request: Request) -> Output:
        action = str(input.get("action") or "get").strip().lower()
        if action not in {"get", "set"}:
            return Response(f"Unsupported action: {action}", 400)

        if action == "get":
            config = dict(plugins.get_plugin_config(PLUGIN_NAME) or {})
            return {
                "ok": True,
                "reasoning_mode": config.get("reasoning_mode", "auto"),
                "context_budget_percent": config.get("context_budget_percent", 30),
                "core_loop_enabled": config.get("core_loop_enabled", True),
            }

        current = dict(plugins.get_plugin_config(PLUGIN_NAME) or {})
        if "reasoning_mode" in input:
            mode = str(input.get("reasoning_mode") or "").strip().lower()
            if mode not in _VALID_MODES:
                return Response(f"Unsupported reasoning mode: {mode}", 400)
            current["reasoning_mode"] = mode
        if "context_budget_percent" in input:
            current["context_budget_percent"] = _clamp_percent(
                input.get("context_budget_percent")
            )
        if "core_loop_enabled" in input:
            current["core_loop_enabled"] = bool(input.get("core_loop_enabled"))
        plugins.save_plugin_config(PLUGIN_NAME, "", "", current)
        return {
            "ok": True,
            "reasoning_mode": current.get("reasoning_mode", "auto"),
            "context_budget_percent": current.get("context_budget_percent", 30),
            "core_loop_enabled": current.get("core_loop_enabled", True),
        }
