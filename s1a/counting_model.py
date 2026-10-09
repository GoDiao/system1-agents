# coding: utf-8
"""``CountingModel``: a chat-model wrapper that records every call's latency, tokens and tool calls."""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

from openjiuwen.core.foundation.llm import AssistantMessage, AssistantMessageChunk, Model


def call_record(reply: AssistantMessage, started: float) -> dict[str, Any]:
    usage = reply.usage_metadata
    calls = list(reply.tool_calls or [])
    return {
        "ms": round((time.perf_counter() - started) * 1000),
        "input_tokens": usage.input_tokens if usage is not None else 0,
        "output_tokens": usage.output_tokens if usage is not None else 0,
        "cache_tokens": int(usage.cache_tokens or 0) if usage is not None else 0,
        "tool_calls": [str(call.name) for call in calls],
        "tool_args": [str(call.arguments) for call in calls],
        "content_chars": len(reply.content) if isinstance(reply.content, str) else 0,
    }


class CountingModel(Model):
    """Forwards ``invoke`` and ``stream`` to ``inner``; appends one record per call to ``calls``."""

    def __init__(self, inner: Model, calls: list[dict[str, Any]]) -> None:
        super().__init__(inner.model_client_config, inner.model_config)
        self._inner = inner
        self._calls = calls

    async def invoke(self, messages: Any, *, tools: Any = None, **kwargs: Any) -> AssistantMessage:
        started = time.perf_counter()
        reply = await self._inner.invoke(messages, tools=tools, **kwargs)
        self._calls.append(call_record(reply, started))
        return reply

    async def stream(self, messages: Any, *, tools: Any = None, **kwargs: Any) -> AsyncIterator[AssistantMessageChunk]:
        started = time.perf_counter()
        merged: AssistantMessageChunk | None = None
        async for chunk in self._inner.stream(messages, tools=tools, **kwargs):
            merged = chunk if merged is None else merged + chunk
            yield chunk
        if merged is not None:
            self._calls.append(call_record(merged, started))
