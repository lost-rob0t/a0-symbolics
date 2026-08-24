from __future__ import annotations

import asyncio
from typing import Any

from helpers import plugins
from helpers.extension import Extension
from plugins._prolog_context_compiler.helpers.bridge import (
    compiler_enabled,
    compiler_root,
    shared_bridge,
)
from plugins._prolog_context_compiler.helpers.projection import ACTIVE_CONTEXT_KEY
from plugins._prolog_context_compiler.helpers.working_context import (
    build_working_context_request,
    projected_messages,
    provider_payload_tokens,
)


class CompileWorkingContext(Extension):
    async def execute(self, data: dict[str, Any], **kwargs: Any) -> None:
        if not self.agent:
            return
        config = plugins.get_plugin_config(
            "_prolog_context_compiler", agent=self.agent
        ) or {}
        if not compiler_enabled(config=config):
            return
        messages = data.get("result")
        if not isinstance(messages, list) or len(messages) < 2:
            return
        request, recent, system = build_working_context_request(
            messages, _current_user_text(self.agent.loop_data), config
        )
        if not request["units"]:
            return
        root = compiler_root(config)
        if root:
            config = {**config, "prolog_rlm_root": root}
        projection = await asyncio.to_thread(shared_bridge(config).compile, request)
        projected = projected_messages(system, projection["text"], recent)
        visible_tokens = provider_payload_tokens(projected, [])
        limit = int(config.get("max_provider_input_tokens", 32_768))
        if visible_tokens > limit:
            raise RuntimeError(
                f"Prolog-RLM working context exceeds hard provider input limit: "
                f"{visible_tokens} > {limit} tokens"
            )
        data["result"] = projected
        active = self.agent.get_data(ACTIVE_CONTEXT_KEY) or {}
        self.agent.set_data(
            ACTIVE_CONTEXT_KEY,
            {
                **active,
                "working_context": {
                    "active_units": projection["active_units"],
                    "fingerprint": projection["fingerprint"],
                    "token_ledger": projection["token_ledger"],
                    "source_message_count": len(messages),
                    "projected_message_count": len(projected),
                },
            },
        )


def _current_user_text(loop_data: Any) -> str:
    message = getattr(loop_data, "user_message", None)
    if message is None:
        return ""
    output_text = getattr(message, "output_text", None)
    if callable(output_text):
        return str(output_text())
    return str(getattr(message, "content", "") or "")
