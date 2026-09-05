from __future__ import annotations

import asyncio
import inspect
import os
import shutil
import threading
from pathlib import Path

import pytest

from plugins._prolog_rlm.helpers.bridge import PrologRuntimeBridgeError
from plugins._prolog_rlm.helpers.harness import (
    Envelope,
    HarnessError,
    PrologRLM,
    RunResult,
    RuntimeFailure,
    WorkerTransport,
    shared_harness,
)


class FakeTransport:
    def __init__(self, envelope: Envelope | None = None, error: Exception | None = None):
        self.envelope = envelope
        self.error = error
        self.calls: list[tuple[str, dict, float | None]] = []

    def run(self, action, arguments, timeout=None):
        self.calls.append((action, arguments, timeout))
        if self.error is not None:
            raise self.error
        return self.envelope


def ok_envelope(payload=None):
    return Envelope(ok=True, result=payload if payload is not None else {"ready": True})


class TestClient:
    def test_call_is_async_and_runs_off_the_event_loop(self):
        # The chat loop awaits harness calls; the client must be awaitable
        # and must never block the loop with the blocking worker transport.
        assert inspect.iscoroutinefunction(PrologRLM.call)
        main_thread = threading.get_ident()
        seen_threads = []

        class ThreadRecordingTransport(FakeTransport):
            def run(self, action, arguments, timeout=None):
                seen_threads.append(threading.get_ident())
                return super().run(action, arguments, timeout)

        result = asyncio.run(
            PrologRLM(ThreadRecordingTransport(ok_envelope())).call("status")
        )
        assert isinstance(result, RunResult)
        assert seen_threads and seen_threads[0] != main_thread

    def test_call_returns_structured_run_result(self):
        transport = FakeTransport(ok_envelope({"ready": True}))
        result = asyncio.run(PrologRLM(transport).call("status"))
        assert isinstance(result, RunResult)
        assert len(result.run_id) == 32
        assert result.action == "status"
        assert result.payload == {"ready": True}
        assert result.elapsed_seconds >= 0.0

    def test_call_passes_arguments_and_timeout(self):
        transport = FakeTransport(ok_envelope())
        asyncio.run(
            PrologRLM(transport).call("direct", {"prompt": "hi"}, timeout=7.5)
        )
        assert transport.calls == [("direct", {"prompt": "hi"}, 7.5)]

    def test_blank_action_is_rejected_before_transport(self):
        transport = FakeTransport(ok_envelope())
        with pytest.raises(HarnessError):
            asyncio.run(PrologRLM(transport).call("  "))
        assert transport.calls == []

    def test_failed_envelope_raises_runtime_failure(self):
        transport = FakeTransport(Envelope(ok=False, error="boom", detail="ctx"))
        with pytest.raises(RuntimeFailure) as excinfo:
            asyncio.run(PrologRLM(transport).call("direct", {"prompt": "hi"}))
        assert excinfo.value.error == "boom"
        assert excinfo.value.detail == "ctx"

    def test_transport_errors_propagate(self):
        transport = FakeTransport(error=PrologRuntimeBridgeError("worker gone"))
        with pytest.raises(PrologRuntimeBridgeError):
            asyncio.run(PrologRLM(transport).call("status"))

    def test_convenience_actions_map_to_runtime_actions(self):
        transport = FakeTransport(ok_envelope())
        client = PrologRLM(transport)
        asyncio.run(client.status())
        asyncio.run(client.demo("graph"))
        asyncio.run(client.direct("hi", budget={"max_total_tokens": 512}))
        asyncio.run(client.complete("q", "ctx"))
        asyncio.run(client.compile({"message": "m", "units": []}))
        assert [c[0] for c in transport.calls] == [
            "status", "demo", "direct", "complete", "context_compile"
        ]
        assert transport.calls[1][1] == {"name": "graph"}
        assert transport.calls[2][1] == {
            "prompt": "hi", "budget": {"max_total_tokens": 512}, "context": ""
        }
        assert transport.calls[3][1] == {
            "query": "q", "context": "ctx", "budget": {}
        }
        assert transport.calls[4][1] == {"request": {"message": "m", "units": []}}


class TestWorkerTransport:
    def test_success_maps_to_ok_envelope(self):
        class Bridge:
            def call(self, action, arguments):
                assert (action, arguments) == ("demo", {"name": "context"})
                return {"status": "pass"}

        envelope = WorkerTransport(Bridge()).run("demo", {"name": "context"})
        assert envelope.ok is True
        assert envelope.result == {"status": "pass"}

    def test_bridge_error_maps_to_failed_envelope(self):
        class Bridge:
            def call(self, action, arguments):
                raise PrologRuntimeBridgeError("required_text(prompt)")

        envelope = WorkerTransport(Bridge()).run("direct", {})
        assert envelope.ok is False
        assert "required_text(prompt)" in envelope.error


class TestSharedHarness:
    def test_same_config_reuses_one_harness(self):
        first = shared_harness({"request_timeout_seconds": 45.0})
        second = shared_harness({"request_timeout_seconds": 45.0})
        assert first is second

    def test_different_timeout_gets_own_harness(self):
        first = shared_harness({"request_timeout_seconds": 45.0})
        second = shared_harness({"request_timeout_seconds": 46.0})
        assert first is not second


PROLOG_RLM_ROOT = Path(os.environ.get("PROLOG_RLM_TEST_ROOT", ""))
PROLOG_RLM_AVAILABLE = bool(
    os.environ.get("PROLOG_RLM_TEST_ROOT")
    and (PROLOG_RLM_ROOT / "prolog" / "rlm.pl").is_file()
)


@pytest.mark.skipif(
    shutil.which("swipl") is None or not PROLOG_RLM_AVAILABLE,
    reason="SWI-Prolog or PROLOG_RLM_TEST_ROOT is unavailable",
)
class TestLiveRuntime:
    def test_harness_reports_runtime_status(self):
        status_call = shared_harness(
            {
                "prolog_rlm_root": str(PROLOG_RLM_ROOT),
                "request_timeout_seconds": 10.0,
            }
        ).status()
        result = asyncio.run(status_call)
        assert result.payload["ready"] is True
        assert result.payload["runtime"] == "prolog-rlm"
