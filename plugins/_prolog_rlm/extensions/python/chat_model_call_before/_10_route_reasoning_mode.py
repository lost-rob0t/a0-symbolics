from __future__ import annotations

from typing import Any

from helpers import plugins
from helpers.extension import Extension
from plugins._prolog_rlm.helpers.loop import wrap_chat_model


class RouteReasoningMode(Extension):
    async def execute(self, call_data: dict[str, Any], **kwargs: Any) -> None:
        if not self.agent:
            return
        config = plugins.get_plugin_config("_prolog_rlm", agent=self.agent) or {}
        model = wrap_chat_model(call_data.get("model"), config)
        if model is not call_data.get("model"):
            call_data["model"] = model
