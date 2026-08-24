from __future__ import annotations

import atexit
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from plugins._prolog_context_compiler.helpers.transport import (
    PrologBridgeError,
    PrologJsonWorker,
    PrologTransportError,
)


PrologContextBridgeError = PrologBridgeError
PrologContextTransportError = PrologTransportError


def compiler_root(config: dict[str, Any] | None = None) -> str:
    settings = config or {}
    return str(
        settings.get("prolog_rlm_root") or os.getenv("PROLOG_RLM_ROOT") or ""
    ).strip()


def compiler_enabled(
    agent: Any = None, config: dict[str, Any] | None = None
) -> bool:
    if config is None and agent is not None:
        from helpers import plugins

        config = plugins.get_plugin_config(
            "_prolog_context_compiler", agent=agent
        ) or {}
    settings = config or {}
    enabled = settings.get("enabled", os.getenv("PROLOG_RLM_ENABLED", ""))
    return bool(compiler_root(settings) or _truthy(enabled))


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


class PrologContextBridge(PrologJsonWorker):
    """Compile Agent Zero context through the public Prolog-RLM adapter."""

    def __init__(
        self,
        *,
        prolog_rlm_root: str | Path | None = None,
        timeout: float = 2.0,
        max_request_bytes: int = 2_000_000,
        max_response_bytes: int = 4_000_000,
    ) -> None:
        worker = Path(__file__).resolve().parent.parent / "prolog" / "context_worker.pl"
        super().__init__(
            worker,
            prolog_rlm_root=prolog_rlm_root,
            timeout=timeout,
            max_request_bytes=max_request_bytes,
            max_response_bytes=max_response_bytes,
        )

    def compile(self, request: dict[str, Any]) -> dict[str, Any]:
        envelope = dict(request)
        envelope["request_id"] = str(request.get("request_id") or uuid.uuid4())
        return self._validate_response(envelope, self.request(envelope))

    def _validate_response(
        self, request: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        if response.get("request_id") != request["request_id"]:
            raise PrologContextBridgeError("context compiler response id mismatch")
        if response.get("ok") is not True:
            error = str(response.get("error") or "unknown Prolog compiler failure")
            raise PrologContextBridgeError(error)
        required = (
            "text",
            "active_tools",
            "active_units",
            "fingerprint",
            "token_ledger",
        )
        missing = [key for key in required if key not in response]
        if missing:
            raise PrologContextBridgeError(
                "context compiler response missing " + ", ".join(missing)
            )
        if not isinstance(response["text"], str):
            raise PrologContextBridgeError("context compiler text is not a string")
        if not isinstance(response["active_tools"], list):
            raise PrologContextBridgeError("context compiler active_tools is not a list")
        return response


_shared_bridge: PrologContextBridge | None = None
_shared_lock = threading.Lock()


def shared_bridge(config: dict[str, Any] | None = None) -> PrologContextBridge:
    global _shared_bridge
    settings = config or {}
    with _shared_lock:
        if _shared_bridge is None:
            _shared_bridge = PrologContextBridge(
                prolog_rlm_root=compiler_root(settings) or None,
                timeout=float(settings.get("compile_timeout_seconds", 2.0)),
                max_request_bytes=int(settings.get("max_request_bytes", 2_000_000)),
                max_response_bytes=int(settings.get("max_response_bytes", 4_000_000)),
            )
        return _shared_bridge


def close_shared_bridge() -> None:
    global _shared_bridge
    with _shared_lock:
        bridge, _shared_bridge = _shared_bridge, None
    if bridge is not None:
        bridge.close()


atexit.register(close_shared_bridge)
