from __future__ import annotations

import atexit
import os
import threading
from pathlib import Path
from typing import Any

from plugins._prolog_context_compiler.helpers.bridge import compiler_root
from plugins._prolog_context_compiler.helpers.transport import (
    PrologBridgeError,
    PrologJsonWorker,
)


class PrologRuntimeBridgeError(PrologBridgeError):
    def __init__(self, message: str, *, detail: str = "") -> None:
        super().__init__(message)
        self.detail = detail


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
        environment = {"OPENROUTER_TEST_MODEL": model} if model else {}
        worker = Path(__file__).resolve().parent.parent / "prolog" / "runtime_worker.pl"
        super().__init__(
            worker,
            prolog_rlm_root=compiler_root(settings) or None,
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
            detail = str(response.get("detail") or "")
            message = str(response.get("error") or "Prolog-RLM request failed")
            raise PrologRuntimeBridgeError(
                f"{message}: {detail}" if detail else message,
                detail=detail,
            )
        if "result" not in response:
            raise PrologRuntimeBridgeError("Prolog-RLM response is missing result")
        return response["result"]


_bridges: dict[tuple[str, str, float], PrologRuntimeBridge] = {}
_bridges_lock = threading.Lock()


def shared_runtime_bridge(config: dict[str, Any] | None = None) -> PrologRuntimeBridge:
    settings = config or {}
    key = (
        compiler_root(settings),
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
