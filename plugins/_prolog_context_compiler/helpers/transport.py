from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any


class PrologBridgeError(RuntimeError):
    pass


class PrologTransportError(PrologBridgeError):
    pass


class PrologJsonWorker:
    """Supervise one bounded JSON-lines SWI-Prolog worker.

    The worker protocol is normally request/reply, but a worker running a
    long-lived operation may emit ``callback`` frames mid-run (for example a
    Prolog-RLM direct run that must execute a host tool). The host answers
    those frames inline; the frame loop below keeps the protocol bounded and
    fail-closed.
    """

    def __init__(
        self,
        worker: str | Path,
        *,
        prolog_rlm_root: str | Path | None = None,
        timeout: float = 2.0,
        max_request_bytes: int = 2_000_000,
        max_response_bytes: int = 4_000_000,
        environment: dict[str, str] | None = None,
        command: list[str] | None = None,
    ) -> None:
        configured_root = prolog_rlm_root or os.getenv("PROLOG_RLM_ROOT", "")
        self.prolog_rlm_root = (
            Path(configured_root).expanduser().resolve() if configured_root else None
        )
        self.worker = Path(worker).resolve()
        self.timeout = max(0.05, float(timeout))
        self.max_request_bytes = int(max_request_bytes)
        self.max_response_bytes = int(max_response_bytes)
        self.environment = dict(environment or {})
        self.command = list(command) if command else None
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._tool_handlers: dict[str, Any] = {}

    def register_tool_handler(self, token: str, handler: Any) -> None:
        """Bind a trusted host callback for one session token."""
        self._tool_handlers[str(token)] = handler

    def unregister_tool_handler(self, token: str) -> None:
        self._tool_handlers.pop(str(token), None)

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        envelope = dict(payload)
        envelope["request_id"] = str(payload.get("request_id") or uuid.uuid4())
        with self._lock:
            try:
                response = self._exchange(envelope)
            except PrologTransportError:
                self._stop()
                response = self._exchange(envelope)
        if response.get("request_id") != envelope["request_id"]:
            raise PrologBridgeError("Prolog worker response id mismatch")
        return response

    def close(self) -> None:
        with self._lock:
            self._tool_handlers.clear()
            self._stop()

    def _exchange(self, request: dict[str, Any]) -> dict[str, Any]:
        process = self._ensure_process()
        payload = json.dumps(
            request, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
        if len(payload.encode("utf-8")) > self.max_request_bytes:
            raise PrologBridgeError("Prolog worker request exceeds size limit")
        try:
            assert process.stdin is not None
            process.stdin.write(payload + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise PrologTransportError("Prolog worker pipe failed") from exc

        # Frame loop: final replies end the exchange; callback frames are
        # answered inline and the loop continues.
        while True:
            frame = self._read_frame()
            if isinstance(frame, dict) and frame.get("callback") == "tool":
                self._dispatch_tool_callback(process, frame)
                continue
            return frame

    def _read_frame(self) -> dict[str, Any]:
        process = self._process
        assert process is not None and process.stdout is not None
        ready, _, _ = select.select([process.stdout], [], [], self.timeout)
        if not ready:
            raise PrologTransportError(
                f"Prolog worker exceeded {self.timeout:.3f}s"
            )
        line = process.stdout.readline(self.max_response_bytes + 1)
        if not line:
            stderr = ""
            if process.stderr is not None and process.poll() is not None:
                stderr = process.stderr.read(2048).strip()
            detail = f": {stderr}" if stderr else ""
            raise PrologTransportError(
                f"Prolog worker exited without a response{detail}"
            )
        if len(line.encode("utf-8")) > self.max_response_bytes:
            raise PrologTransportError("Prolog worker response is too large")
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PrologTransportError("Prolog worker returned malformed JSON") from exc
        if not isinstance(response, dict):
            raise PrologTransportError("Prolog worker returned a non-object response")
        return response

    def _dispatch_tool_callback(self, process: subprocess.Popen[str], frame: dict) -> None:
        call_id = frame.get("call_id")
        token = str(frame.get("token") or "")
        handler = self._tool_handlers.get(token)
        reply: dict[str, Any]
        if handler is None:
            reply = {
                "call_id": call_id,
                "ok": False,
                "error": f"no host tool handler registered for session",
            }
        else:
            try:
                result = handler(str(frame.get("name") or ""), frame.get("arguments") or {})
                if not isinstance(result, dict):
                    raise TypeError("host tool callback must return a dict")
                reply = {"call_id": call_id, "ok": True, "result": result}
            except Exception as exc:  # fail the single tool call, not the run
                reply = {"call_id": call_id, "ok": False, "error": str(exc)[:500]}
        payload = json.dumps(reply, ensure_ascii=False, separators=(",", ":"))
        if len(payload.encode("utf-8")) > self.max_request_bytes:
            payload = json.dumps(
                {
                    "call_id": call_id,
                    "ok": False,
                    "error": "host tool result exceeded the protocol size limit",
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        try:
            assert process.stdin is not None
            process.stdin.write(payload + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise PrologTransportError("Prolog worker pipe failed") from exc

    def _ensure_process(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process
        if not self.worker.is_file():
            raise PrologBridgeError(f"Prolog worker is unavailable: {self.worker}")
        if self.command:
            args = list(self.command)
        else:
            swipl = shutil.which("swipl")
            if not swipl:
                raise PrologBridgeError("SWI-Prolog executable 'swipl' is unavailable")
            args = [swipl, "-q", "-f", "none", "-s", str(self.worker), "--"]
            if self.prolog_rlm_root:
                args.extend(["--prolog-root", str(self.prolog_rlm_root)])
        environment = os.environ.copy()
        environment.update(self.environment)
        self._process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=environment,
        )
        return self._process

    def _stop(self) -> None:
        process, self._process = self._process, None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=0.5)
