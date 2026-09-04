"""Host-facing Prolog-RLM harness client.

Turns runtime envelopes into structured, typed results for any Agent Zero
caller (tools, extensions, API handlers) without exposing worker internals.
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

from plugins._prolog_context_compiler.helpers.bridge import compiler_root
from plugins._prolog_rlm.helpers.harness.transport import Transport, shared_transport


class HarnessError(RuntimeError):
    pass


class RuntimeFailure(HarnessError):
    def __init__(self, message: str, *, error: str = "", detail: str = "") -> None:
        super().__init__(message)
        self.error = error
        self.detail = detail


@dataclass(frozen=True)
class RunResult:
    run_id: str
    action: str
    payload: Any
    elapsed_seconds: float


class PrologRLM:
    """Async typed client over the runtime worker.

    The worker transport is blocking; every call offloads it with
    ``asyncio.to_thread`` so chat-loop event loops stay responsive. Callers
    await these methods directly (``await harness.complete(...)``).
    """

    def __init__(self, transport: Transport) -> None:
        self.transport = transport

    async def call(
        self,
        action: str,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> RunResult:
        action = str(action or "").strip()
        if not action:
            raise HarnessError("Prolog-RLM action is required")
        run_id = uuid.uuid4().hex
        started = time.perf_counter()
        envelope = await asyncio.to_thread(
            self.transport.run, action, arguments or {}, timeout
        )
        elapsed = time.perf_counter() - started
        if not envelope.ok:
            raise RuntimeFailure(
                envelope.error or f"Prolog-RLM action {action} failed",
                error=envelope.error,
                detail=envelope.detail,
            )
        return RunResult(
            run_id=run_id,
            action=action,
            payload=envelope.result,
            elapsed_seconds=elapsed,
        )

    async def status(self, timeout: float | None = None) -> RunResult:
        return await self.call("status", timeout=timeout)

    async def direct(self, prompt: str, budget: dict[str, Any] | None = None,
                     timeout: float | None = None) -> RunResult:
        return await self.call(
            "direct",
            {"prompt": prompt, "budget": budget or {}},
            timeout=timeout,
        )

    async def complete(self, query: str, context: str = "",
                       budget: dict[str, Any] | None = None,
                       timeout: float | None = None) -> RunResult:
        return await self.call(
            "complete",
            {"query": query, "context": context, "budget": budget or {}},
            timeout=timeout,
        )

    async def demo(self, name: str = "context", timeout: float | None = None) -> RunResult:
        return await self.call("demo", {"name": name}, timeout=timeout)


_harnesses: dict[tuple[str, str, float], PrologRLM] = {}
_harnesses_lock = threading.Lock()


def shared_harness(config: dict[str, Any] | None = None) -> PrologRLM:
    settings = config or {}
    key = (
        compiler_root(settings),
        str(settings.get("openrouter_model") or ""),
        float(settings.get("request_timeout_seconds", 45.0)),
    )
    with _harnesses_lock:
        harness = _harnesses.get(key)
        if harness is None:
            harness = PrologRLM(shared_transport(settings))
            _harnesses[key] = harness
        return harness


def close_harnesses() -> None:
    from plugins._prolog_rlm.helpers.harness.transport import close_transports

    with _harnesses_lock:
        _harnesses.clear()
    close_transports()
