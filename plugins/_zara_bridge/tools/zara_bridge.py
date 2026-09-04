from __future__ import annotations

import asyncio

from helpers import plugins
from helpers.tool import Response, Tool
from plugins._zara_bridge.helpers.client import ZaraBridgeConfig, ZaraDaemonClient


PLUGIN_NAME = "_zara_bridge"


class ZaraBridge(Tool):
    async def execute(self, message: str = "", **kwargs):
        del kwargs
        text = str(message or self.args.get("message") or "").strip()
        config_data = plugins.get_plugin_config(
            PLUGIN_NAME,
            agent=self.agent,
            caller="agent",
        ) or {}
        config = ZaraBridgeConfig.load(config_data)
        response = await asyncio.to_thread(ZaraDaemonClient(config).send, text)
        return Response(message=response, break_loop=False)
