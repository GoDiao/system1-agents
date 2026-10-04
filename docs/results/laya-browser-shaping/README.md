# Laya browser input shaping: evidence

What Laya receives on the browser front with `LAYA_COMPACT_BROWSER_STATE` off and on, on the same recorded input,
and the one live Google Flights run. Laya's own tokenizer and `build_sequence` produce every count; no model forward
pass is needed for them.

## Files

| file | what it is |
|---|---|
| `zurich-london.jsonl` | 12 browser ticks recorded from a Jev 1.13 run of the `flights` task (Zurich to London, one adult, economy), the `state` and `questions` exactly as the browser front sent them, and Jev's `answers`. File dated 2026-09-29; predates 0fbfc7a. The account button's label is the generic "Google Account"; no personal data. Page labels and text are Google Flights' own, kept for evaluation only; the `????` are characters the recorder could not encode. |
| `trace.txt` | the output of the command below: per tick and per question, state tokens (and how many fit the window), option tokens, and whether the options were cut to an equal share, compaction off and on, under two windows; then tick 8 (the calendar, 66 elements) as Laya reads it both ways. |
| `live-run-2026-09-28/` | `answer.json` and `decision_ticks.json` of the live run reported in the PR. |
| `regression-tests.txt` | the regression tests that pin the current shaping, the probe's string flags and the WAIT record. |

## Reproduce

```bash
uv sync --extra laya
uv run python scripts/laya_shaping_trace.py docs/results/laya-browser-shaping/zurich-london.jsonl --show 8
uv run pytest -v tests/test_decision_models_laya.py -k "TestLayaState or TestLayaBrowserQuestion"
uv run pytest -v "tests/test_browser_policy.py::TestJevWaitCollapsesIntoInPageSettling::test_a_wait_that_moved_the_page_is_recorded_as_progress"
```

Revisions: shaping code at 0fbfc7a plus the commit that adds this folder; tokenizer `convaiinnovations/laya` at
revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`. Environment of the trace: Windows 11, CPU, Python 3.13.14,
laya 0.3.5, transformers 5.17.0, torch 2.14.0+cpu.

## What the trace shows

Windows: `512 / 192` is the checkpoint's default (`max_len` / `head_max_len`); `1536 / 1024` is what the PR
recommends for browser runs (`LAYA_MAX_LEN` / `LAYA_HEAD_MAX_LEN`).

| | compaction off | compaction on |
|---|---|---|
| state tokens per tick | 256 to 4,726 | 91 to 998 |
| `click_target` option tokens (25-element page) | 640 to 672 | 136 to 152 |
| `click_target` option tokens (calendar, 66 to 67 elements) | 3,225 to 3,275 | 695 to 717 |
| `512 / 192`: options cut to an equal share | every `click_target` head of 10 elements or more (4 to 19 tokens per option) | the three `click_target` heads of 55 to 67 elements (4 tokens per option) |
| `512 / 192`: state kept | at most 316 tokens; the whole state only on the 3-element tick | the whole state on ticks 0 to 5; 232 to 439 tokens on ticks 6 to 11 |
| `1536 / 1024`: options cut | the calendar and results `click_target` heads (15 to 20 tokens per option) | none |
| `1536 / 1024`: state kept | 508 to 922 tokens of the 1,173- to 4,726-token states | the whole state on every question except the two calendar ticks' `click_target` (775 of 926, 753 of 998) |

So with the shaping and the browser window, every option reaches Laya whole on every recorded tick, and the state
fits except on the calendar's target head, where the 66 day buttons take the room. Under the default window the
shaping is not enough for those heads.

The calendar's target options (tick 8), first lines of `trace.txt`:

```text
off: 3: {"element": "[3] Friday, September 25, 2026 ????", "current_value": "", "role": "button", "region": "dialog:Ba...
on:  3: "Friday, September 25, 2026 ?"
```

Under `512 / 192` without the shaping, each of these options gets 4 tokens, so Laya reads the start of the JSON
(`{"element": "[`) and no date.

## The live run (2026-09-28, before ecefeea and 0fbfc7a)

```bash
LAYA_MAX_LEN=1536 LAYA_HEAD_MAX_LEN=1024 uv run s1a run flights --model laya --timeout 900
```

Code: the tree committed as e513234 nine minutes later (state and question shaping, before the review fixes);
checkpoint `convaiinnovations/laya` at `55cf4c4`; Windows 11, CPU only, Chrome over CDP.

`decision_ticks.json`: one tick, 25 elements, 1,254 input tokens over four questions, 12,397 ms. Operation
probabilities: DONE 0.548, CLICK 0.225, BLOCKED 0.087, WAIT 0.058, SCROLL_DOWN 0.049, TYPE_TEXT 0.033.

`answer.json`: `status` DONE with `steps: 0`, `interactions: 0` and an empty `history`; the final page is the
Google Flights home page (`https://www.google.com/travel/flights?hl=en`) with nothing filled, and the chat model's
answer says no Zurich to London flight is shown. The run's DONE is Laya's verdict at the first step, not a
completed task.
