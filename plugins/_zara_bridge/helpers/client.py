from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass


class ZaraBridgeError(RuntimeError):
    pass


def _env(name: str, fallback: object) -> object:
    value = os.environ.get(name)
    return fallback if value is None else value


@dataclass(frozen=True)
class ZaraBridgeConfig:
    zara_binary: str = "zara"
    endpoint: str = ""
    timeout_seconds: float = 35.0
    max_message_chars: int = 20000
    max_output_chars: int = 50000

    @classmethod
    def load(cls, mapping: dict | None) -> "ZaraBridgeConfig":
        source = dict(mapping or {})
        config = cls(
            zara_binary=str(
                _env("A0_ZARA_BINARY", source.get("zara_binary", "zara"))
            ).strip(),
            endpoint=str(
                _env("A0_ZARA_ENDPOINT", source.get("endpoint", ""))
            ).strip(),
            timeout_seconds=float(source.get("timeout_seconds", 35.0)),
            max_message_chars=int(source.get("max_message_chars", 20000)),
            max_output_chars=int(source.get("max_output_chars", 50000)),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not self.zara_binary:
            raise ZaraBridgeError("zara_binary is required")
        if not 0.1 <= self.timeout_seconds <= 300:
            raise ZaraBridgeError("timeout_seconds must be between 0.1 and 300")
        if not 1 <= self.max_message_chars <= 200000:
            raise ZaraBridgeError("max_message_chars must be between 1 and 200000")
        if not 1 <= self.max_output_chars <= 500000:
            raise ZaraBridgeError("max_output_chars must be between 1 and 500000")


class ZaraDaemonClient:
    def __init__(self, config: ZaraBridgeConfig) -> None:
        self.config = config

    def send(self, message: str) -> str:
        text = str(message).strip()
        if not text:
            raise ZaraBridgeError("message is required")
        if len(text) > self.config.max_message_chars:
            raise ZaraBridgeError("message exceeds configured limit")
        if not self.config.endpoint:
            raise ZaraBridgeError("Zara daemon endpoint is not configured")

        argv = [
            self.config.zara_binary,
            "--connect",
            self.config.endpoint,
            text,
        ]
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                completed = subprocess.run(
                    argv,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    timeout=self.config.timeout_seconds,
                    check=False,
                )
            except FileNotFoundError as error:
                raise ZaraBridgeError(
                    f"Zara executable not found: {self.config.zara_binary}"
                ) from error
            except subprocess.TimeoutExpired as error:
                raise ZaraBridgeError(
                    f"Zara turn exceeded {self.config.timeout_seconds:.2f}s timeout"
                ) from error

            stdout_file.seek(0)
            stderr_file.seek(0)
            byte_limit = self.config.max_output_chars * 4 + 1
            stdout = stdout_file.read(byte_limit)
            stderr = stderr_file.read(min(byte_limit, 4097))

        if len(stdout) >= byte_limit:
            raise ZaraBridgeError("Zara response exceeded configured limit")
        try:
            output = stdout.decode("utf-8")
            error_output = stderr.decode("utf-8", errors="replace")
        except UnicodeDecodeError as error:
            raise ZaraBridgeError("Zara response was not valid UTF-8") from error
        if len(output) > self.config.max_output_chars:
            raise ZaraBridgeError("Zara response exceeded configured limit")
        if completed.returncode != 0:
            detail = " ".join(error_output.split())[:512]
            raise ZaraBridgeError(
                f"Zara exited with status {completed.returncode}: {detail or 'no error output'}"
            )
        return output.strip()
