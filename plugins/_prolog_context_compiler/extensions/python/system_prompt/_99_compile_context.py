from __future__ import annotations

import asyncio
from typing import Any

from agent import LoopData
from helpers import plugins
from helpers.extension import Extension
from plugins._prolog_context_compiler.helpers.bridge import (
    compiler_enabled,
    compiler_root,
    shared_bridge,
)
from plugins._prolog_context_compiler.helpers.catalog import build_compile_request
from plugins._prolog_context_compiler.helpers.projection import ACTIVE_CONTEXT_KEY


class CompileProviderContext(Extension):
    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs: Any,
    ) -> None:
        if not self.agent:
            return
        config = plugins.get_plugin_config(
            "_prolog_context_compiler", agent=self.agent
        ) or {}
        if not compiler_enabled(config=config):
            self.agent.set_data(ACTIVE_CONTEXT_KEY, None)
            return
        root = compiler_root(config)
        if root:
            config = {**config, "prolog_rlm_root": root}
        request = build_compile_request(self.agent, system_prompt, loop_data, config)
        if not str(request.get("message") or "").strip():
            self.agent.set_data(ACTIVE_CONTEXT_KEY, None)
            return
        result = await asyncio.to_thread(shared_bridge(config).compile, request)
        if not result["text"].strip():
            raise RuntimeError("Prolog context compiler produced an empty projection")
        result["source_section_count"] = len(system_prompt)
        result["catalog_unit_count"] = len(request["units"])
        self.agent.set_data(ACTIVE_CONTEXT_KEY, result)
        system_prompt[:] = [result["text"]]
