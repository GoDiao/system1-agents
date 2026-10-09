# coding: utf-8
"""RethinkRail: after every ``act``, notice a stalled episode and hand the model a plan and a blocked key."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from openjiuwen.core.common.exception.errors import BaseError
from openjiuwen.core.foundation.llm import Model
from openjiuwen.core.single_agent.rail.base import AgentCallbackContext
from openjiuwen.harness.rails.base import DeepAgentRail

from s1a.tool.models import ACT_TOOL, EvalState

REPLAN_PROMPT = (
    "The player is stuck. From the rules, the recent steps, the current state and the candidates, write a plan of "
    "at most 60 words for the next few moves. Name concrete candidate keys."
)
REPLAN_MAX_TOKENS = 120
RECENT_STEPS = 12


def parse_tool_result(raw: Any) -> dict[str, Any] | None:
    """The ``act`` tool's JSON result, from the string or object the callback hands over."""
    text = raw if isinstance(raw, str) else getattr(raw, "content", None)
    if isinstance(raw, dict):
        return raw
    if not isinstance(text, str):
        return None
    try:
        parsed = json.loads(text)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def progress_digest(state: Any) -> str:
    """What "the same state" means for a stall: the observation's ``progress`` part when the adapter names one
    (histories and step counters change every step), otherwise the whole observation."""
    if isinstance(state, dict) and "progress" in state:
        state = state["progress"]
    return json.dumps(state, sort_keys=True, default=str)


def parse_tool_args(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


class RethinkRail(DeepAgentRail):
    """Three signals, cheapest first: an exact repeat blocks a key, a semantic stall asks for a plan, too many stalls give up.

    ``repeat_after``: the same key for that many consecutive acts without a score change blocks it for one turn.
    ``stall_after``: that many acts without a score change, with a state seen before in that window, trigger a plan.
    ``give_up_after``: a stall after that many plans, in the same state and without a score change, ends the episode
    (a fourth stall after three plans without a score change ends the episode).
    A plan the chat model fails to write is the episode's error. The plan and the block last one turn.

    The harness registers the overridden ``after_tool_call`` hook by itself.
    """

    def __init__(
        self,
        state: EvalState,
        *,
        rules: str,
        initial_score: float,
        planner: Model | None,
        stall_after: int,
        repeat_after: int,
        give_up_after: int,
    ) -> None:
        super().__init__()
        self._state = state
        self._rules = rules
        self._planner = planner
        self._stall_after = stall_after
        self._repeat_after = repeat_after
        self._give_up_after = give_up_after
        self._keys: list[str] = []
        self._scores: list[float] = []
        self._digests: list[str] = []
        self._last_score = initial_score
        self._since_progress = 0
        self._stalls_without_progress = 0
        self._stall_digest = ""  # the state of the last stall; a stall elsewhere restarts the give-up count

    async def after_tool_call(self, ctx: AgentCallbackContext) -> None:
        inputs = ctx.inputs
        name = str(getattr(inputs, "tool_name", "") or "")
        if not (name == ACT_TOOL or name.endswith("_" + ACT_TOOL)):
            return
        result = parse_tool_result(getattr(inputs, "tool_result", None))
        if result is None or "score" not in result or self._state.error is not None:
            return
        key = str(parse_tool_args(getattr(inputs, "tool_args", None)).get("key", ""))
        score = float(result["score"])
        progressed = score != self._last_score
        self._last_score = score
        self._keys.append(key)
        self._scores.append(score)
        self._digests.append(progress_digest(result.get("state")))
        if progressed:
            self._since_progress = 0
            self._stalls_without_progress = 0
            return
        self._since_progress += 1
        step = len(self._keys)
        state = self._state
        tail = self._keys[-self._repeat_after :]
        repeated = self._repeat_after and self._since_progress >= self._repeat_after and len(set(tail)) == 1
        if repeated:
            state.blocked.add(key)
            state.notices.append(f"{key} repeated {self._repeat_after} times without a score change")
            state.rethinks.append({"kind": "repeat", "step": step, "key": key})
        window = self._digests[-self._stall_after :]
        stalled = self._stall_after > 0 and self._since_progress >= self._stall_after and window.count(window[-1]) > 1
        if not stalled:
            return
        if window[-1] != self._stall_digest:
            self._stalls_without_progress = 0
            self._stall_digest = window[-1]
        self._stalls_without_progress += 1
        if self._stalls_without_progress > self._give_up_after:
            state.give_up = True
            state.rethinks.append({"kind": "give_up", "step": step})
            return
        most_repeated = Counter(self._keys[-self._stall_after :]).most_common(1)[0][0]
        since_progress, self._since_progress = self._since_progress, 0
        try:
            plan = await self._plan(self._planner, result) if self._planner is not None else ""
        except BaseError as exc:  # the callback framework swallows a raise; the error field is what stops the episode
            state.error = f"plan failed: {exc}"
            state.rethinks.append({"kind": "plan_failed", "step": step, "error": str(exc)})
            return
        state.plan = plan
        state.blocked.add(most_repeated)
        state.notices.append(f"no score change for {since_progress} steps; {most_repeated} blocked this turn")
        state.rethinks.append({"kind": "stall", "step": step, "blocked": most_repeated, "plan": plan})

    async def _plan(self, planner: Model, result: dict[str, Any]) -> str:
        context = {
            "rules": self._rules,
            "recent_steps": [
                {"key": key, "score": score}
                for key, score in zip(self._keys[-RECENT_STEPS:], self._scores[-RECENT_STEPS:])
            ],
            "state": result.get("state"),
            "candidates": result.get("candidates"),
        }
        reply = await planner.invoke(
            [
                {"role": "system", "content": REPLAN_PROMPT},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, default=str)},
            ],
            max_tokens=REPLAN_MAX_TOKENS,
            temperature=0,
        )
        return str(reply.content or "").strip()
