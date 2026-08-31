from __future__ import annotations

import asyncio
import json
from typing import Any

from helpers import plugins
from helpers.tool import Response, Tool
from plugins._prolog_rlm.helpers.bridge import (
    PrologRuntimeBridgeError,
    shared_runtime_bridge,
)


PLUGIN_NAME = "_prolog_rlm"


class PrologRLM(Tool):
    async def execute(
        self,
        action: str = "status",
        prompt: str = "",
        query: str = "",
        context: str = "",
        name: str = "",
        budget: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Response:
        action = str(action or self.args.get("action") or "status").strip().lower()
        config = plugins.get_plugin_config(PLUGIN_NAME, agent=self.agent) or {}
        arguments: dict[str, Any]

        if action in {"status", "catalog"}:
            arguments = {}
        elif action == "demo":
            arguments = {"name": name or self.args.get("name") or "context"}
        elif action == "direct":
            arguments = {
                "prompt": prompt or self.args.get("prompt") or "",
                "budget": budget or self.args.get("budget") or {},
            }
        elif action == "agent":
            arguments = {
                "query": query or self.args.get("query") or "",
                "context": context or self.args.get("context") or "",
                "budget": budget or self.args.get("budget") or {},
            }
        elif action == "complete":
            arguments = {
                "query": query or self.args.get("query") or "",
                "context": context or self.args.get("context") or "",
                "budget": budget or self.args.get("budget") or {},
            }
        else:
            return Response(
                message=(
                    "Unknown Prolog-RLM action. Supported actions: status, catalog, "
                    "demo, direct, agent, complete."
                ),
                break_loop=False,
            )

        try:
            result = await asyncio.to_thread(
                shared_runtime_bridge(config).call, action, arguments
            )
        except PrologRuntimeBridgeError as exc:
            return Response(message=f"Prolog-RLM failed: {exc}", break_loop=False)

        rendered = json.dumps(result, ensure_ascii=False, sort_keys=True)
        limit = max(1000, int(config.get("max_tool_result_chars", 50_000)))
        if len(rendered) > limit:
            rendered = rendered[:limit] + "…[bounded Prolog-RLM result]"
        return Response(message=rendered, break_loop=False)
