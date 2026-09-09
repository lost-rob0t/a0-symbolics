import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import models
from helpers import litellm_transport

TOOL_CHOICE_ERROR = RuntimeError(
    "Upstream error from NextBit: upstream model did not return a valid "
    "tool call for the requested tool_choice"
)


def _chunk(content: str) -> dict:
    return {"choices": [{"delta": {"content": content}, "message": {}}]}


class _StreamThenFail:
    """Streams one content chunk, then raises mid-stream like NextBit."""

    def __init__(self, content: str, exc: Exception):
        self._content = content
        self._exc = exc
        self.index = 0
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index == 0:
            self.index += 1
            return _chunk(self._content)
        raise self._exc

    async def aclose(self):
        self.closed = True


class _SimpleStream:
    def __init__(self, chunks: list[dict]):
        self._chunks = chunks
        self.index = 0
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self.index]
        self.index += 1
        return chunk

    async def aclose(self):
        self.closed = True


@pytest.fixture
def _patch_settings(monkeypatch):
    monkeypatch.setattr(
        models.settings,
        "get_settings",
        lambda: {"litellm_global_kwargs": {}},
    )


@pytest.mark.asyncio
async def test_unified_call_drops_tool_choice_after_mid_stream_failure(
    monkeypatch, _patch_settings
):
    calls: list[dict] = []

    async def fake_acompletion(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _StreamThenFail("partial reasoning", TOOL_CHOICE_ERROR)
        return _SimpleStream([_chunk("recovered plain answer")])

    async def fake_rate_limiter(*args, **kwargs):
        return None

    monkeypatch.setattr(litellm_transport, "acompletion", fake_acompletion)
    monkeypatch.setattr(models, "apply_rate_limiter", fake_rate_limiter)

    wrapper = models.LiteLLMChatWrapper(
        model="test-model",
        provider="openai",
        model_config=None,
        a0_api_mode="chat",
        tools=[{"type": "function", "function": {"name": "response", "parameters": {"type": "object"}}}],
        tool_choice="required",
    )

    async def response_callback(chunk: str, full: str):
        return None

    response, reasoning = await wrapper.unified_call(
        messages=[],
        response_callback=response_callback,
    )

    assert response == "recovered plain answer"
    assert reasoning == ""
    assert len(calls) == 2
    assert calls[0].get("tool_choice") == "required"
    assert "tool_choice" not in calls[1]
    assert calls[1].get("stream") is True


@pytest.mark.asyncio
async def test_unified_turn_drops_tool_choice_after_mid_stream_failure(
    monkeypatch, _patch_settings
):
    calls: list[dict] = []

    async def fake_acompletion(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _StreamThenFail("partial reasoning", TOOL_CHOICE_ERROR)
        return _SimpleStream([_chunk("recovered plain answer")])

    async def fake_rate_limiter(*args, **kwargs):
        return None

    monkeypatch.setattr(litellm_transport, "acompletion", fake_acompletion)
    monkeypatch.setattr(models, "apply_rate_limiter", fake_rate_limiter)

    wrapper = models.LiteLLMChatWrapper(
        model="test-model",
        provider="openai",
        model_config=None,
        a0_api_mode="chat",
        tools=[{"type": "function", "function": {"name": "response", "parameters": {"type": "object"}}}],
        tool_choice="required",
    )

    async def response_callback(chunk: str, full: str):
        return None

    result = await wrapper.unified_turn(
        messages=[],
        response_callback=response_callback,
    )

    assert result.response == "recovered plain answer"
    assert len(calls) == 2
    assert calls[0].get("tool_choice") == "required"
    assert "tool_choice" not in calls[1]


@pytest.mark.asyncio
async def test_unified_call_drops_tool_choice_only_once(monkeypatch, _patch_settings):
    calls: list[dict] = []

    async def fake_acompletion(*args, **kwargs):
        calls.append(kwargs)
        raise TOOL_CHOICE_ERROR

    async def fake_rate_limiter(*args, **kwargs):
        return None

    monkeypatch.setattr(litellm_transport, "acompletion", fake_acompletion)
    monkeypatch.setattr(models, "apply_rate_limiter", fake_rate_limiter)

    wrapper = models.LiteLLMChatWrapper(
        model="test-model",
        provider="openai",
        model_config=None,
        a0_api_mode="chat",
        tools=[{"type": "function", "function": {"name": "response", "parameters": {"type": "object"}}}],
        tool_choice="required",
    )

    with pytest.raises(RuntimeError, match="did not return a valid tool call"):
        await wrapper.unified_call(messages=[])

    assert len(calls) == 2
