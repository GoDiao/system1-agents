# coding: utf-8
"""RethinkRail on scripted act results: repeats block a key, stalls ask for a plan, too many stalls give up."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest import IsolatedAsyncioTestCase, TestCase

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.foundation.llm import AssistantMessage

from s1a.tool.rethink import RethinkRail, parse_tool_args, parse_tool_result, progress_digest
from s1a.tool.models import EvalState

BOARD = {"grid": [[2, 0], [0, 0]]}


def act(key: str, score: float, *, state: dict[str, Any] = BOARD, tool: str = "act") -> SimpleNamespace:
    result = {"state": state, "candidates": {"LEFT": "", "RIGHT": "", "UP": ""}, "done": False, "score": score}
    return SimpleNamespace(
        inputs=SimpleNamespace(tool_name=tool, tool_args={"key": key}, tool_result=json.dumps(result))
    )


class FakePlanner:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def invoke(self, messages: Any, **kwargs: Any) -> AssistantMessage:
        self.calls.append({"messages": messages, **kwargs})
        return AssistantMessage(content="  Slide RIGHT, then UP to open the corner.  ")


class FailingPlanner:
    def __init__(self) -> None:
        self.calls = 0

    async def invoke(self, messages: Any, **kwargs: Any) -> AssistantMessage:
        self.calls += 1
        raise build_error(StatusCode.MODEL_CALL_FAILED, error_msg="chat endpoint returned HTTP 401")


def rail(
    state: EvalState, *, planner: Any = None, stall_after: int = 0, repeat_after: int = 0, give_up_after: int = 3
) -> RethinkRail:
    return RethinkRail(
        state,
        rules="2048 rules",
        initial_score=8.0,
        planner=planner,
        stall_after=stall_after,
        repeat_after=repeat_after,
        give_up_after=give_up_after,
    )


class TestRethinkRail(IsolatedAsyncioTestCase):
    async def test_progress_records_nothing(self) -> None:
        state = EvalState()
        guard = rail(state, stall_after=2, repeat_after=2)
        for score in (12, 16, 20, 24):
            await guard.after_tool_call(act("LEFT", score))
        self.assertEqual((state.rethinks, state.blocked, state.plan), ([], set(), ""))

    async def test_exact_repeat_blocks_the_key_for_one_turn(self) -> None:
        state = EvalState()
        guard = rail(state, repeat_after=3)
        for _ in range(3):
            await guard.after_tool_call(act("LEFT", 8))
        self.assertEqual(state.blocked, {"LEFT"})
        self.assertEqual(state.rethinks, [{"kind": "repeat", "step": 3, "key": "LEFT"}])
        self.assertIn("LEFT", state.notices[0])

    async def test_a_repeat_after_productive_moves_is_no_repeat(self) -> None:
        state = EvalState()
        guard = rail(state, repeat_after=3)
        for score in (12, 16, 16):  # two merges, then a slide: a legal 2048 line
            await guard.after_tool_call(act("LEFT", score))
        self.assertEqual((state.rethinks, state.blocked), ([], set()))
        for _ in range(2):
            await guard.after_tool_call(act("LEFT", 16))
        self.assertEqual(state.rethinks, [{"kind": "repeat", "step": 5, "key": "LEFT"}])

    async def test_a_stall_on_another_key_keeps_the_repeat_block(self) -> None:
        state = EvalState()
        guard = rail(state, stall_after=6, repeat_after=3)
        for key in ("RIGHT", "RIGHT", "RIGHT", "LEFT", "LEFT", "LEFT"):
            await guard.after_tool_call(act(key, 8))
        self.assertEqual(state.blocked, {"LEFT", "RIGHT"})

    async def test_a_semantic_stall_asks_for_a_plan_and_blocks_the_most_repeated_key(self) -> None:
        state, planner = EvalState(), FakePlanner()
        guard = rail(state, planner=planner, stall_after=3)
        for key in ("LEFT", "RIGHT", "LEFT"):
            await guard.after_tool_call(act(key, 8))
        self.assertEqual(state.plan, "Slide RIGHT, then UP to open the corner.")
        self.assertEqual(state.blocked, {"LEFT"})
        self.assertEqual(state.rethinks[0]["kind"], "stall")
        self.assertEqual(state.rethinks[0]["blocked"], "LEFT")
        payload = json.loads(planner.calls[0]["messages"][1]["content"])
        self.assertEqual(payload["rules"], "2048 rules")
        self.assertEqual([step["key"] for step in payload["recent_steps"]], ["LEFT", "RIGHT", "LEFT"])
        self.assertEqual(payload["candidates"], {"LEFT": "", "RIGHT": "", "UP": ""})
        await guard.after_tool_call(act("UP", 16))
        self.assertEqual(len(state.rethinks), 1)

    async def test_a_failed_plan_is_the_episodes_error_and_no_give_up(self) -> None:
        state, planner = EvalState(), FailingPlanner()
        guard = rail(state, planner=planner, stall_after=2, give_up_after=1)
        for _ in range(6):
            await guard.after_tool_call(act("LEFT", 8))
        self.assertTrue(state.error.startswith("plan failed: "), state.error)
        self.assertIn("HTTP 401", state.error)
        self.assertFalse(state.give_up)
        self.assertEqual(planner.calls, 1)
        self.assertEqual(
            [event for event in state.rethinks if event["kind"] != "repeat"],
            [{"kind": "plan_failed", "step": 2, "error": state.error.removeprefix("plan failed: ")}],
        )

    async def test_a_stall_is_seen_through_the_progress_part_when_the_state_has_one(self) -> None:
        state = EvalState()
        guard = rail(state, stall_after=2)
        first = {"progress": {"holding": "mug"}, "recent_steps": ["go to shelf 1"], "steps_used": 1}
        second = {"progress": {"holding": "mug"}, "recent_steps": ["go to shelf 2"], "steps_used": 2}
        await guard.after_tool_call(act("go to shelf 1", 8, state=first))
        await guard.after_tool_call(act("go to shelf 2", 8, state=second))
        self.assertEqual(state.blocked, {"go to shelf 1"})
        self.assertEqual(progress_digest(first), progress_digest(second))
        self.assertNotEqual(progress_digest({"a": 1}), progress_digest({"a": 2}))

    async def test_a_stall_without_a_planner_still_blocks(self) -> None:
        state = EvalState()
        guard = rail(state, stall_after=2)
        for key in ("LEFT", "LEFT"):
            await guard.after_tool_call(act(key, 8))
        self.assertEqual((state.plan, state.blocked), ("", {"LEFT"}))

    async def test_too_many_stalls_without_progress_give_up(self) -> None:
        state = EvalState()
        guard = rail(state, planner=FakePlanner(), stall_after=2, give_up_after=1)
        for _ in range(2):
            await guard.after_tool_call(act("LEFT", 8))
        self.assertFalse(state.give_up)
        for _ in range(2):
            await guard.after_tool_call(act("LEFT", 8))
        self.assertTrue(state.give_up)
        self.assertEqual(state.rethinks[-1]["kind"], "give_up")

    async def test_a_stall_in_a_new_state_restarts_the_give_up_count(self) -> None:
        state = EvalState()
        guard = rail(state, stall_after=2, give_up_after=1)
        shelf = {"progress": {"at": "shelf 1"}}
        drawer = {"progress": {"at": "drawer 1"}}
        for place in (shelf, shelf, drawer, drawer):  # a binary score: two stalls in two different places
            await guard.after_tool_call(act(f"go to {place['progress']['at']}", 8, state=place))
        self.assertEqual([event["kind"] for event in state.rethinks], ["stall", "stall"])
        self.assertFalse(state.give_up)

    async def test_other_tools_and_unparseable_results_are_ignored(self) -> None:
        state = EvalState()
        guard = rail(state, stall_after=1, repeat_after=1)
        await guard.after_tool_call(act("LEFT", 8, tool="observe"))
        await guard.after_tool_call(
            SimpleNamespace(inputs=SimpleNamespace(tool_name="act", tool_args={}, tool_result="not json"))
        )
        self.assertEqual(state.rethinks, [])


class TestParsers(TestCase):
    def test_args_and_results_from_strings_and_objects(self) -> None:
        self.assertEqual(parse_tool_args('{"key": "a"}'), {"key": "a"})
        self.assertEqual(parse_tool_args({"key": "b"}), {"key": "b"})
        self.assertEqual(parse_tool_args("nope"), {})
        self.assertEqual(parse_tool_result('{"score": 1}'), {"score": 1})
        self.assertEqual(parse_tool_result(SimpleNamespace(content='{"score": 2}')), {"score": 2})
        self.assertIsNone(parse_tool_result("[1, 2]"))
