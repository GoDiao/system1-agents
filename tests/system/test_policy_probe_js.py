# coding: utf-8
"""Opt-in check of ``POLICY_PROBE_JS`` against a fixture page in a headless Chromium through @playwright/mcp.

Run with ``S1A_BROWSER_TESTS=1 pytest tests/system``; needs Node (``npx``) and a chat key is not needed.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from typing import Any

import pytest
from openjiuwen.core.runner import Runner

from s1a.tool.hands import BrowserHands
from s1a.browser.probe_js import POLICY_PROBE_JS, STAMP_ATTRIBUTE

FIXTURE = """<!doctype html><html><head><title>Probe fixture</title></head><body>
<h1>Trip</h1>
<label for="from">Where from?</label><input id="from" role="combobox" value="Tokyo" aria-controls="list">
<ul id="list" role="listbox" hidden></ul>
<span id="to-label">Where to?</span><input aria-labelledby="to-label" type="text">
<label>Class <select id="class"><option value="e" selected>Economy</option><option value="b">Business</option>
<option value="f" disabled>First</option></select></label>
<input type="checkbox" id="nonstop" aria-label="Nonstop only" checked>
<button type="submit">Search</button>
<button disabled>Disabled</button>
<input type="password" aria-label="Secret">
<input type="hidden" value="h">
<a href="/help">Help</a>
<a href="/r1">quick pasta sauce &lt;img src="https://x/a.jpg" width="282"&gt; 130 Ratings</a>
<a href="/r2">Baked salmon &lt;img src="https://x/b.jpg" width="282"</a>
<div role="dialog" aria-label="Passengers"><button>Add adult</button></div>
<p>Visible paragraph text.</p>
<p hidden>Hidden text.</p>
<button style="position:absolute; left:-9999px">Offscreen</button>
</body></html>"""
WRITE_FIXTURE = "(html) => { document.open(); document.write(html); document.close(); return document.title; }"
COUNT_MATCHES = "(hints) => hints.map((hint) => document.querySelectorAll(hint).length)"
SET_VALUE = (
    "(a) => { const e = document.querySelector(a.selector); e.value = a.text; "
    "e.dispatchEvent(new Event('input', {bubbles: true})); return 'ok'; }"
)

pytestmark = pytest.mark.skipif(
    not os.getenv("S1A_BROWSER_TESTS") or not shutil.which("npx"),
    reason="Set S1A_BROWSER_TESTS=1 with Node installed to run the policy probe check.",
)


def _by_label(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["label"]: item for item in snapshot["elements"]}


async def _probe(hands: BrowserHands, after: dict[str, Any] | None) -> dict[str, Any]:
    params = {"stamp_attribute": STAMP_ATTRIBUTE, "after": after, "max_items": 250}
    snapshot = await hands.read(POLICY_PROBE_JS, params)
    assert isinstance(snapshot, dict) and not snapshot.get("error"), snapshot
    return snapshot


async def _exercise() -> None:
    hands = BrowserHands(headless=True)
    await Runner.start()
    try:
        async with hands.session("about:blank", ready_selector="body", timeout_s=20.0):
            assert await hands.read(WRITE_FIXTURE, FIXTURE) == "Probe fixture"

            first = await _probe(hands, None)
            items = _by_label(first)
            assert set(items) == {
                "Where from?",
                "Where to?",
                "Class",
                "Nonstop only",
                "Search",
                "Help",
                "quick pasta sauce 130 Ratings",  # escaped markup in the page text is dropped from the name
                "Baked salmon",  # an unclosed tag-shaped run at the end too
                "Add adult",
            }, items
            assert items["Where from?"]["role"] == "combobox" and items["Where from?"]["editable"] is True
            assert items["Where from?"]["value"] == "Tokyo"
            assert items["Where to?"]["role"] == "textbox" and items["Where to?"]["editable"] is True
            assert items["Class"]["editable"] is False and items["Class"]["value"] == "Economy"
            assert items["Class"]["options"] == [{"label": "Business", "value": "b"}]
            assert items["Nonstop only"]["checked"] == "true"
            assert items["Search"]["role"] == "button" and items["Help"]["role"] == "link"
            assert items["Add adult"]["region"] == "dialog:Passengers"
            assert "Visible paragraph text." in first["text"] and "Hidden text." not in first["text"]
            assert first["can_scroll_down"] is False and first["omitted"] == 0
            hints = [item["selector_hint"] for item in first["elements"]]
            assert await hands.read(COUNT_MATCHES, hints) == [1] * len(hints), "stamped selectors must be unique"

            second = await _probe(hands, None)
            assert {k: v["node"] for k, v in _by_label(second).items()} == {k: v["node"] for k, v in items.items()}
            assert second["page_key"] == first["page_key"]

            field = items["Where from?"]
            assert await hands.read(SET_VALUE, {"selector": field["selector_hint"], "text": "Zurich"}) == "ok"
            third = await _probe(hands, {"kind": "fill", "node": field["node"]})
            assert _by_label(third)["Where from?"]["value"] == "Zurich"
            assert _by_label(third)["Where from?"]["node"] == field["node"]
            assert third["page_key"] != first["page_key"], "a changed field value must change the page key"

            whole = await hands.read(
                POLICY_PROBE_JS, {"stamp_attribute": STAMP_ATTRIBUTE, "after": None, "all_text": True}
            )
            assert "Visible paragraph text." in whole["text"] and "Hidden text." not in whole["text"]
    finally:
        await Runner.stop()


def test_policy_probe_describes_fixture_controls() -> None:
    asyncio.run(_exercise())
