from __future__ import annotations

import json
from typing import Any

from helpers import plugins
from helpers.tool import Response, Tool
from plugins._prolog_context_compiler.helpers.catalog import build_compile_request
from plugins._prolog_rlm.helpers.harness import RuntimeFailure, shared_harness


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
        elif action == "complete":
            arguments = {
                "query": query or self.args.get("query") or "",
                "context": context or self.args.get("context") or "",
                "budget": budget or self.args.get("budget") or {},
            }
        elif action == "validate_tools":
            compile_config = plugins.get_plugin_config(
                "_prolog_context_compiler", agent=self.agent
            ) or {}
            request = build_compile_request(
                self.agent, [], self.agent.loop_data, compile_config
            )
            arguments = {
                "declarations": [
                    unit
                    for unit in request["units"]
                    if unit.get("kind") in {"tool", "mcp_tool"}
                ]
            }
            action = "tool_pack_catalog"
        else:
            return Response(
                message=(
                    "Unknown Prolog-RLM action. Supported actions: status, catalog, "
                    "demo, direct, complete, validate_tools."
                ),
                break_loop=False,
            )

        try:
            result = await shared_harness(config).call(action, arguments)
        except RuntimeFailure as exc:
            message = str(exc)
            if exc.detail:
                message = f"{message}: {exc.detail}"
            return Response(message=f"Prolog-RLM failed: {message}", break_loop=False)

        rendered = json.dumps(result.payload, ensure_ascii=False, sort_keys=True)
        limit = max(1000, int(config.get("max_tool_result_chars", 50_000)))
        if len(rendered) > limit:
            rendered = rendered[:limit] + "…[bounded Prolog-RLM result]"
        return Response(message=rendered, break_loop=False)
