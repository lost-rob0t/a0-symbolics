"""Transport seam for the Prolog-RLM runtime worker.

Owns the machine-facing side of the harness: a protocol-shaped Transport
abstraction over the persistent JSON-lines runtime worker, normalized
envelopes, and shared-transport caching. Runtime semantics (authority,
budgets, capabilities, durable effects, cancellation) stay in Prolog; a
future CLI transport can replace the worker without touching clients.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Protocol

from plugins._prolog_context_compiler.helpers.bridge import compiler_root
from plugins._prolog_rlm.helpers.bridge import (
    PrologRuntimeBridge,
    PrologRuntimeBridgeError,
    shared_runtime_bridge,
)


@dataclass(frozen=True)
class Envelope:
    ok: bool
    result: Any = None
    error: str = ""
    detail: str = ""


class Transport(Protocol):
    def run(
        self,
        action: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
    ) -> Envelope: ...


class WorkerTransport:
    """Transport over the persistent Prolog-RLM runtime worker.

    The supervision timeout is fixed at worker construction
    (``request_timeout_seconds``); the per-call ``timeout`` argument is
    accepted for protocol compatibility and reserved for transports that
    spawn a fresh process per call.
    """

    def __init__(self, bridge: PrologRuntimeBridge) -> None:
        self.bridge = bridge

    def run(
        self,
        action: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
    ) -> Envelope:
        try:
            result = self.bridge.call(action, arguments)
        except PrologRuntimeBridgeError as exc:
            return Envelope(
                ok=False,
                error=str(exc),
                detail=str(getattr(exc, "detail", "") or ""),
            )
        return Envelope(ok=True, result=result)


_transports: dict[tuple[str, str, float], WorkerTransport] = {}
_transports_lock = threading.Lock()


def shared_transport(config: dict[str, Any] | None = None) -> WorkerTransport:
    settings = config or {}
    key = (
        compiler_root(settings),
        str(settings.get("openrouter_model") or ""),
        float(settings.get("request_timeout_seconds", 45.0)),
    )
    with _transports_lock:
        transport = _transports.get(key)
        if transport is None:
            transport = WorkerTransport(shared_runtime_bridge(settings))
            _transports[key] = transport
        return transport


def close_transports() -> None:
    with _transports_lock:
        transports = list(_transports.values())
        _transports.clear()
    for transport in transports:
        transport.bridge.close()
