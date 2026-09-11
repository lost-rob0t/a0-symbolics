from __future__ import annotations

from typing import Any

from helpers import plugins
from helpers.extension import Extension
from plugins._prolog_rlm.helpers.loop import collect_tool_declarations, wrap_chat_model


class RouteReasoningMode(Extension):
    async def execute(self, call_data: dict[str, Any], **kwargs: Any) -> None:
        if not self.agent:
            return
        config = plugins.get_plugin_config("_prolog_rlm", agent=self.agent) or {}
        compiler_config = (
            plugins.get_plugin_config("_prolog_context_compiler", agent=self.agent) or {}
        )
        declarations = collect_tool_declarations(self.agent, compiler_config)
        model = wrap_chat_model(
            call_data.get("model"),
            config,
            agent=self.agent,
            declarations=declarations,
        )
        if model is not call_data.get("model"):
            call_data["model"] = model
