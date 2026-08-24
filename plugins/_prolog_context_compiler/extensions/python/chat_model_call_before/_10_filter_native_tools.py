from __future__ import annotations

from typing import Any

from helpers import plugins
from helpers.extension import Extension
from plugins._prolog_context_compiler.helpers.projection import (
    ACTIVE_CONTEXT_KEY,
    filter_native_tools,
)
from plugins._prolog_context_compiler.helpers.working_context import provider_payload_tokens


class FilterNativeTools(Extension):
    async def execute(self, call_data: dict[str, Any], **kwargs: Any) -> None:
        if not self.agent:
            return
        name_map = self.agent.get_data("responses_tool_name_map") or {}
        filtered = filter_native_tools(
            self.agent,
            call_data.get("a0_responses_function_tools"),
            name_map,
        )
        call_data["a0_responses_function_tools"] = filtered
        if not isinstance(self.agent.get_data(ACTIVE_CONTEXT_KEY), dict):
            return
        config = plugins.get_plugin_config(
            "_prolog_context_compiler", agent=self.agent
        ) or {}
        visible_tokens = provider_payload_tokens(call_data.get("messages") or [], filtered)
        limit = int(config.get("max_provider_input_tokens", 32_768))
        if visible_tokens > limit:
            raise RuntimeError(
                f"Provider-visible context exceeds hard Prolog-RLM limit: "
                f"{visible_tokens} > {limit} tokens"
            )
        projection = dict(self.agent.get_data(ACTIVE_CONTEXT_KEY) or {})
        projection["provider_visible_tokens"] = visible_tokens
        projection["provider_visible_token_limit"] = limit
        projection["provider_visible_native_tool_count"] = len(filtered)
        self.agent.set_data(ACTIVE_CONTEXT_KEY, projection)
