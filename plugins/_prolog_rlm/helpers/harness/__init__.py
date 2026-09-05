"""Agent-facing Prolog-RLM harness: typed client seam over the runtime worker."""

from plugins._prolog_rlm.helpers.harness.client import (
    HarnessError,
    PrologRLM,
    RunResult,
    RuntimeFailure,
    close_harnesses,
    shared_harness,
)
from plugins._prolog_rlm.helpers.harness.transport import (
    Envelope,
    Transport,
    WorkerTransport,
    close_transports,
    shared_transport,
)

__all__ = [
    "Envelope",
    "HarnessError",
    "PrologRLM",
    "RunResult",
    "RuntimeFailure",
    "Transport",
    "WorkerTransport",
    "close_harnesses",
    "close_transports",
    "shared_harness",
    "shared_transport",
]
