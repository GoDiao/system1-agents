# coding: utf-8
"""``CountingModel`` records latency, tokens and tool calls for invoke and for stream, and forwards the reply."""

from __future__ import annotations

from typing import Any
from unittest import IsolatedAsyncioTestCase

from openjiuwen.core.foundation.llm import AssistantMessage, AssistantMessageChunk, ToolCall
from openjiuwen.core.foundation.llm.schema.message import UsageMetadata

from s1a.counting_model import CountingModel
from s1a.tool.models import placeholder_model

ACT = ToolCall(id="c1", type="function", name="act", arguments='{"key": "inc"}')


def _inner(reply: AssistantMessage, chunks: list[AssistantMessageChunk]) -> Any:
    inner = placeholder_model()

    async def invoke(messages: Any, *, tools: Any = None, **kwargs: Any) -> AssistantMessage:
        return reply

    async def stream(messages: Any, *, tools: Any = None, **kwargs: Any):
        for chunk in chunks:
            yield chunk

    inner.invoke = invoke
    inner.stream = stream
    return inner


class TestCountingModel(IsolatedAsyncioTestCase):
    async def test_invoke_records_tokens_and_tool_calls_and_returns_the_reply(self) -> None:
        reply = AssistantMessage(
            content="",
            tool_calls=[ACT],
            usage_metadata=UsageMetadata(input_tokens=120, output_tokens=9, cache_tokens=100),
        )
        calls: list[dict[str, Any]] = []
        model = CountingModel(_inner(reply, []), calls)

        returned = await model.invoke([{"role": "user", "content": "play"}], tools=[])

        self.assertIs(returned, reply)
        (record,) = calls
        self.assertEqual((record["input_tokens"], record["output_tokens"], record["cache_tokens"]), (120, 9, 100))
        self.assertEqual((record["tool_calls"], record["tool_args"]), (["act"], ['{"key": "inc"}']))
        self.assertGreaterEqual(record["ms"], 0)

    async def test_a_reply_without_usage_counts_zero_tokens(self) -> None:
        calls: list[dict[str, Any]] = []
        await CountingModel(_inner(AssistantMessage(content="four words of text"), []), calls).invoke("hi")
        self.assertEqual(
            (calls[0]["input_tokens"], calls[0]["output_tokens"], calls[0]["cache_tokens"], calls[0]["content_chars"]),
            (0, 0, 0, 18),
        )

    async def test_stream_yields_every_chunk_and_records_the_merged_call(self) -> None:
        chunks = [
            AssistantMessageChunk(content="", tool_calls=[ACT]),
            AssistantMessageChunk(content="", usage_metadata=UsageMetadata(input_tokens=40, output_tokens=3)),
        ]
        calls: list[dict[str, Any]] = []
        model = CountingModel(_inner(AssistantMessage(content=""), chunks), calls)

        seen = [chunk async for chunk in model.stream("play", tools=[])]

        self.assertEqual(len(seen), 2)
        (record,) = calls
        self.assertEqual((record["input_tokens"], record["output_tokens"]), (40, 3))
        self.assertEqual(record["tool_calls"], ["act"])
