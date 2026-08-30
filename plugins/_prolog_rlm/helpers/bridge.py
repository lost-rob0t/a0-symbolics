from __future__ import annotations

import atexit
import os
import threading
from pathlib import Path
from typing import Any

from plugins._prolog_rlm.helpers.transport import PrologBridgeError, PrologJsonWorker


class PrologRuntimeBridgeError(PrologBridgeError):
    pass


def runtime_root(config: dict[str, Any] | None = None) -> str:
    settings = config or {}
    return str(
        settings.get("prolog_rlm_root") or os.getenv("PROLOG_RLM_ROOT") or ""
    ).strip()


class PrologRuntimeBridge(PrologJsonWorker):
    """Typed access to the full stable Prolog-RLM runtime worker."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        settings = config or {}
        model = str(
            settings.get("openrouter_model")
            or os.getenv("OPENROUTER_MODEL")
            or os.getenv("OPENROUTER_TEST_MODEL")
            or ""
        ).strip()
        api_key = str(
            os.getenv("OPENROUTER_API_KEY")
            or os.getenv("API_KEY_OPENROUTER")
            or ""
        ).strip()
        environment = {}
        if model:
            environment["OPENROUTER_TEST_MODEL"] = model
        if api_key:
            environment["OPENROUTER_API_KEY"] = api_key
        worker = Path(__file__).resolve().parent.parent / "prolog" / "runtime_worker.pl"
        super().__init__(
            worker,
            prolog_rlm_root=runtime_root(settings) or None,
            timeout=float(settings.get("request_timeout_seconds", 45.0)),
            max_request_bytes=int(settings.get("max_request_bytes", 2_000_000)),
            max_response_bytes=int(settings.get("max_response_bytes", 4_000_000)),
            environment=environment,
        )

    def call(self, action: str, arguments: dict[str, Any] | None = None) -> Any:
        response = self.request(
            {"action": str(action or "").strip(), "arguments": arguments or {}}
        )
        if response.get("ok") is not True:
            detail = response.get("detail")
            message = str(response.get("error") or "Prolog-RLM request failed")
            if detail:
                message = f"{message}: {detail}"
            raise PrologRuntimeBridgeError(message)
        if "result" not in response:
            raise PrologRuntimeBridgeError("Prolog-RLM response is missing result")
        return response["result"]


_bridges: dict[tuple[str, str, float], PrologRuntimeBridge] = {}
_bridges_lock = threading.Lock()


def shared_runtime_bridge(config: dict[str, Any] | None = None) -> PrologRuntimeBridge:
    settings = config or {}
    key = (
        runtime_root(settings),
        str(settings.get("openrouter_model") or os.getenv("OPENROUTER_MODEL") or ""),
        float(settings.get("request_timeout_seconds", 45.0)),
    )
    with _bridges_lock:
        bridge = _bridges.get(key)
        if bridge is None:
            bridge = PrologRuntimeBridge(settings)
            _bridges[key] = bridge
        return bridge


def close_runtime_bridges() -> None:
    with _bridges_lock:
        bridges = list(_bridges.values())
        _bridges.clear()
    for bridge in bridges:
        bridge.close()


atexit.register(close_runtime_bridges)
