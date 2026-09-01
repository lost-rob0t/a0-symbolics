from __future__ import annotations

from typing import Any

from helpers.extension import Extension
from plugins._prolog_rlm.helpers.model_turn import route_model_turn


class RouteChatModelThroughProlog(Extension):
    async def execute(self, data: dict[str, Any], **kwargs: Any) -> None:
        if not self.agent:
            return
        call_kwargs = data.get("kwargs") or {}
        messages = call_kwargs.get("messages")
        if messages is None:
            args = data.get("args") or ()
            messages = args[1] if len(args) > 1 else []
        data["result"] = await route_model_turn(
            self.agent,
            list(messages or []),
            response_callback=call_kwargs.get("response_callback"),
            reasoning_callback=call_kwargs.get("reasoning_callback"),
        )
