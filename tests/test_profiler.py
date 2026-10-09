# coding: utf-8
"""The lab profiler's accounting: jev-ultrafast's window, clipped phases that add up, one row per step."""

import asyncio
import json

from s1a.browser.action_space import build_action_space, build_observation, build_questions
from s1a.decision_models import DecisionModel, ChoiceQuestion, Observation, ScriptedModel
from s1a.browser.profiler import BrowserProfiler, Span, render

SITE = "https://www.google.com/travel/flights"
RESULTS_URL = "https://www.google.com/travel/flights/search?tfs=x"
FINAL = json.dumps({"status": "DONE", "url": RESULTS_URL})
CLICK = "mcp_playwright-official_browser_click"  # the runtime registers browser tools under a server prefix


def _recorded_run() -> BrowserProfiler:
    profiler = BrowserProfiler()

    def add(kind: str, name: str, t0: float, t1: float, **meta: object) -> None:
        profiler.spans.append(Span(kind, name, t0, t1, dict(meta)))

    add("turn", "browser", 0.0, 0.72, finish_reason="tool_calls")
    add("probe", "settle=500", 0.0, 0.2)
    add("wire", "evaluate", 0.01, 0.19)
    add("decision", "typesafe/jev-1.13", 0.2, 0.7)
    add("tool", CLICK, 0.73, 0.76)
    add("wire", "click", 0.735, 0.755)
    add("turn", "browser", 0.8, 1.41, finish_reason="stop", content=FINAL)
    add("probe", "settle=500", 0.8, 0.9)
    add("wire", "evaluate", 0.81, 0.89)
    add("decision", "typesafe/jev-1.13", 0.9, 1.4)
    return profiler


def test_report_starts_at_the_first_decision_and_its_phases_add_up() -> None:
    report = _recorded_run().report(ticks=[{"value_ms": 0}, {}], waits=0, final_url=RESULTS_URL, verified_prefix=SITE)

    assert report["elapsed_ms"] == 1210
    assert report["run_ms"] == 1410, "the run ends at the last span to finish, not the last to start"
    assert report["decision_requests"] == 2
    assert report["browser_turns"] == 2
    assert report["decision_total_ms"] == 1000
    assert report["browser_actions"] == 1
    assert report["verified"] is True
    phases = report["phases"]
    assert phases["probe"] == 100, "the probe before the first decision is outside the window"
    assert phases["probe_wire"] == 80
    assert phases["tool"] == 30 and phases["tool_wire"] == 20
    critical_path = ("decision", "probe", "activate", "value_wait", "model_overhead", "tool", "framework")
    assert sum(phases[name] for name in critical_path) == 1210
    assert [step["tool"] for step in report["steps"]] == [CLICK, ""]
    assert report["steps"][0]["gap_ms"] == 50
    assert "window 1210 ms" in render(report)


def test_a_turn_served_through_both_stream_and_invoke_is_counted_once() -> None:
    profiler = _recorded_run()
    profiler.spans.append(Span("turn", "browser", 0.8, 1.41, {"finish_reason": "stop", "content": FINAL}))

    phases = profiler.report(ticks=[{"value_ms": 0}, {}], waits=0, final_url=RESULTS_URL, verified_prefix=SITE)[
        "phases"
    ]

    assert phases["framework"] == 50, "an overlapping turn span must not push the framework gap negative"
    assert phases["model_overhead"] == 30


def test_report_without_a_browser_turn_names_the_gap() -> None:
    assert BrowserProfiler().report(ticks=[], waits=0, final_url="", verified_prefix="") == {
        "error": "no browser turn recorded",
        "spans": 0,
    }


def test_verified_needs_done_on_a_page_under_the_goal_site() -> None:
    profiler = _recorded_run()

    elsewhere = profiler.report(ticks=[], waits=0, final_url="https://www.bing.com/travel", verified_prefix=SITE)
    assert elsewhere["verified"] is False

    profiler.spans[-4].meta["content"] = json.dumps({"status": "BLOCKED", "url": RESULTS_URL})
    blocked = profiler.report(ticks=[], waits=0, final_url=RESULTS_URL, verified_prefix=SITE)
    assert blocked["verified"] is False


def test_the_decide_span_survives_an_observation_without_browser_state() -> None:
    """A tool-front observation has no element table and no operation head; the span records empty meta."""
    profiler = BrowserProfiler().attach()
    try:
        decision = asyncio.run(
            ScriptedModel(choose="a").decide_many(Observation({"n": 1}), {"pick": ChoiceQuestion({"a": "A"})})
        )
    finally:
        profiler.detach()

    (span,) = profiler.spans
    assert decision.choice("pick").key == "a"
    assert span.t1 > 0 and span.meta["elements"] == [] and "operations" not in span.meta
    assert span.meta["answers"] == {"pick": {"choice": "a", "confidence": 1.0}}


def test_attach_times_every_decide_many_as_a_jev_span_and_detach_restores_it() -> None:
    """The profiler patches the decision-model interface, so Jev, Laya and a scripted double are timed alike."""
    snapshot = {
        "url": "https://x",
        "title": "t",
        "text": "",
        "elements": [{"node": 1, "target_id": "t1", "role": "button", "label": "Search", "value": ""}],
    }
    space = build_action_space(snapshot, [])
    original = DecisionModel.decide_many
    profiler = BrowserProfiler().attach()
    try:
        assert DecisionModel.decide_many is not original
        decision = asyncio.run(
            ScriptedModel(model="scripted-model").decide_many(  # first offered key per head: CLICK, element 1
                build_observation(space, snapshot, []),
                build_questions(space, goal="g", values=[], rules="r", language="en"),
                attempts=2,
            )
        )
    finally:
        profiler.detach()

    assert DecisionModel.decide_many is original
    assert decision.choice("operation").key == "CLICK"
    (span,) = [s for s in profiler.spans if s.kind == "decision"]
    assert (span.name, span.t1 > span.t0) == ("scripted-model", True)
    assert span.meta["elements"] == ["[1] Search"]
    assert span.meta["operations"] == space.operations
    assert span.meta["answers"]["operation"] == {"choice": "CLICK", "confidence": 1.0}
    assert span.meta["answers"]["click_target"] == {"choice": "1", "confidence": 1.0}


def test_turn_name_recognises_prefixed_browser_tools() -> None:
    from types import SimpleNamespace

    from s1a.browser.profiler import _turn_name

    assert _turn_name([SimpleNamespace(name="mcp_playwright-official_browser_click")]) == "browser"
    assert _turn_name([SimpleNamespace(name="read_file")]) == "chat"
