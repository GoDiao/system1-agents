# Desktop input-to-save evidence

Source and test revision: [`041a71e50a67b01c7a049afff8548f1f37e54bd4`](https://github.com/ThinkFlowLab/system1-agents/commit/041a71e50a67b01c7a049afff8548f1f37e54bd4).
Fixture: [fixture.swift](fixture.swift). The fixture writes `/tmp/s1a-desktop-fixture.txt` only from Save.
Success requires the supplied text in fresh field readback, the Saved status, and a fresh file containing
exactly that text. The recorder independently reads/stats the file after each episode.

The native runs below were made on 2026-10-05 from clean source checkouts. The original evidence update added
documentation only. PR merge base: `222e656a1a53d7d19c815d8ac66defaad557b1c5`; upstream `main`
was refreshed at `a2c46f4f40ce2c580f2bce14e6efb0b3315923e5` and was not merged into the PR.

These records replace the earlier author-reported native figures. The earlier raw artifacts and their
source bindings were unavailable, so their revision, retries and interventions could not be audited.
No historical timing is reused here. All native attempts made for this follow-up are listed.

Mac: macOS 26.2 (25C56), arm64; Python 3.13.5; Swift 6.3. Cua Driver 0.30.1, using the signed
`/Applications/CuaDriver.app/Contents/MacOS/cua-driver`, standard permission mode, Accessibility and
Screen Recording enabled. Input delivery was background, bound to the fixture's PID/window ID.
The driver offered an update; it was left at 0.30.1 throughout these runs.

Episode time starts **after reset** and includes per-episode agent cleanup. It excludes model
construction/loading, fixture launch/reset, imports and series/model teardown. Command wall time includes those costs. Model files were
downloaded before the timed commands. These are small fixture demonstrations, without a baseline/head
speed comparison or a general task-success-rate claim. Total cost was not measured.

## Native results

| Run | Selection | Task successes | Episode seconds | Task actions |
|---|---|---:|---|---|
| English input to Save, seeds 0–2 | Real local Laya | 3/3 | 9.9, 8.4, 8.4 (26.7 total) | 4 each |
| Chinese multiline replacement to Save, seed 0 | Fixed plan | 1/1 | 4.9 | 2 |

Laya: **0.3.5 from this revision's lock file**, PyTorch 2.14.0, Transformers 5.17.0, MPS;
checkpoint [`convaiinnovations/laya@55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`](https://huggingface.co/convaiinnovations/laya/tree/55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851), root checkpoint,
`max_len=512`, `head_max_len=192`, no overrides. This is a fresh run, separate from the earlier 0.3.20 report.
Laya construction/loading: **12.451 s**; its no-op `warm()` took less than 1 ms; command wall: **75.260 s**.
There were 12 model decisions and 12 task input RPCs, plus 3 Clear setup clicks; median decision: **138 ms**.
No hosted decision/chat calls, fixed action plan or manual input was used in these Laya episodes.

Each Laya episode first chose **Save twice with an empty Body**. Both attempts kept `text_pending=True`,
`done=False`, and score 0. These ineffective actions are retained below. After replacement, field readback
matched, but the file still lacked the payload; only the final Save completed the task.
The driver reported `effect=confirmed`, `route=accessibility`, `evidence=[value_readback]` for each
`set_value`. Save/Clear AXPress replies reported `effect=unverifiable`; success comes from subsequent
readback and the independent file check, not that driver reply.

The runtime warned that the checkpoint's `choice:11+` temperature was outside its calibration bounds
and was clamped. Confidence values below are raw diagnostics, not reliability estimates. Dependency
syntax/deprecation warnings and the driver's update notice were also present; no execution error occurred.

### Laya terminal trace

Supplied text: `Local Laya agent demo`. All decisions and post-action field states are shown.
The only setup intervention was building/launching the repository fixture and its configured Clear on reset.
No trial was discarded or rerun.

```text
seed=0 start=2026-10-05T06:07:17.417879+00:00 episode_s=9.9
  reset: Clear; Body="" Status="Editing" text_pending=True score=0
  1 click:Save decision_ms=1358 confidence=0.091
    readback Body="" Status="Saved" text_pending=True done=False score=0.0
  2 click:Save decision_ms=169 confidence=0.087
    readback Body="" Status="Saved" text_pending=True done=False score=0.0
  3 type:Body decision_ms=118 confidence=0.078
    readback Body="Local Laya agent demo" Status="Saved" text_pending=False done=False score=0.0
  4 click:Save decision_ms=143 confidence=0.14
    readback Body="Local Laya agent demo" Status="Saved" text_pending=False done=True score=1.0
  error=None chat_calls=0 invalid_keys=0
independent file check: fresh=True matches=True content="Local Laya agent demo"
  before_mtime_ns=1791180139861157797 check_started_ns=1791180434624610000 after_mtime_ns=1791180445890694523
seed=1 start=2026-10-05T06:07:29.746816+00:00 episode_s=8.4
  reset: Clear; Body="" Status="Editing" text_pending=True score=0
  1 click:Save decision_ms=136 confidence=0.091
    readback Body="" Status="Saved" text_pending=True done=False score=0.0
  2 click:Save decision_ms=137 confidence=0.087
    readback Body="" Status="Saved" text_pending=True done=False score=0.0
  3 type:Body decision_ms=108 confidence=0.078
    readback Body="Local Laya agent demo" Status="Saved" text_pending=False done=False score=0.0
  4 click:Save decision_ms=137 confidence=0.14
    readback Body="Local Laya agent demo" Status="Saved" text_pending=False done=True score=1.0
  error=None chat_calls=0 invalid_keys=0
independent file check: fresh=True matches=True content="Local Laya agent demo"
  before_mtime_ns=1791180445890694523 check_started_ns=1791180447357358000 after_mtime_ns=1791180456982935337
seed=2 start=2026-10-05T06:07:40.558759+00:00 episode_s=8.4
  reset: Clear; Body="" Status="Editing" text_pending=True score=0
  1 click:Save decision_ms=141 confidence=0.091
    readback Body="" Status="Saved" text_pending=True done=False score=0.0
  2 click:Save decision_ms=139 confidence=0.087
    readback Body="" Status="Saved" text_pending=True done=False score=0.0
  3 type:Body decision_ms=101 confidence=0.078
    readback Body="Local Laya agent demo" Status="Saved" text_pending=False done=False score=0.0
  4 click:Save decision_ms=140 confidence=0.14
    readback Body="Local Laya agent demo" Status="Saved" text_pending=False done=True score=1.0
  error=None chat_calls=0 invalid_keys=0
independent file check: fresh=True matches=True content="Local Laya agent demo"
  before_mtime_ns=1791180456982935337 check_started_ns=1791180458141525000 after_mtime_ns=1791180467775123466
```

### Fixed-plan Chinese/multiline terminal trace

This separate execution check supplies the action sequence; it measures no model selection.
It ran once, before the Laya run, with no manual input during the episode.

```text
supplied text="本地桌面代理\n第二行：验证保存。"
reset: Clear; Body="" Status="Editing" text_pending=True score=0
1 type:Body source=plan decision_ms=0
  readback Body="本地桌面代理\n第二行：验证保存。" Status="Editing" text_pending=False done=False score=0.0
2 click:Save source=plan decision_ms=0
  readback Body="本地桌面代理\n第二行：验证保存。" Status="Saved" text_pending=False done=True score=1.0
independent file check: before_exists=False fresh=True matches=True
  command_started_ns=1791180130176611000 after_mtime_ns=1791180139861157797
  content="本地桌面代理\n第二行：验证保存。"
episode_s=4.9 command_wall_s=11.324 exit=0
```

## Reproduce

Use the source revision above in a clean checkout. Close an older document fixture first.
Install with `uv sync --extra dev --extra laya --frozen`, then:

```bash
bash evals/desktop/build_fixture.sh /tmp/S1AReviewDocument.app
export CUA_DRIVER_BIN=/Applications/CuaDriver.app/Contents/MacOS/cua-driver
export CUA_DRIVER_PERMISSION_MODE=standard LAYA_DEVICE=mps
export LAYA_MODEL="$(uv run --no-sync python -c 'from huggingface_hub import snapshot_download; print(snapshot_download("convaiinnovations/laya", revision="55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851", allow_patterns=["model.safetensors", "rl_agent_config.json", "encoder/*", "tokenizer/*"]))')"
export HF_HUB_OFFLINE=1
export S1A_HOME="$(mktemp -d /tmp/s1a-text-evidence.XXXXXX)"
export EVIDENCE_DIR="$S1A_HOME/trace"
export EVIDENCE_FILE=/tmp/s1a-desktop-fixture.txt
export EVIDENCE_EXPECTED='Local Laya agent demo'
# Save the recorder below as /tmp/s1a-evidence-recorder.py first.
uv run --no-sync python /tmp/s1a-evidence-recorder.py \
  --model laya --rethink off --episodes 3 --seed 0 \
  --app S1ADocumentFixture --app-path /tmp/S1AReviewDocument.app \
  --window-title 'S1A Document Fixture' \
  --goal 'Enter the task text in Body and save it' --expect Saved \
  --text 'Local Laya agent demo' --text-target Body --text-mode replace \
  --verify-file /tmp/s1a-desktop-fixture.txt --clear Clear --execute --log
```

Fixed-plan invocation (separate output directory). The external check records the timestamp before
launch and compares both file content and mtime afterward; the recorder above can perform this check too.

```bash
export S1A_HOME="$(mktemp -d /tmp/s1a-text-fixed.XXXXXX)"
export S1A_FILE_CHECK_STARTED_NS="$(uv run --no-sync python -c 'import time; print(time.time_ns())')"
uv run --no-sync s1a run desktop \
  --model rule --rethink off --episodes 1 \
  --app S1ADocumentFixture --app-path /tmp/S1AReviewDocument.app \
  --window-title 'S1A Document Fixture' \
  --goal 'Enter the text in Body and save it' --expect Saved \
  --text $'本地桌面代理\n第二行：验证保存。' --text-target Body --text-mode replace \
  --verify-file /tmp/s1a-desktop-fixture.txt --clear Clear \
  --plan 'type:Body,Save' --execute --log
uv run --no-sync python - <<'PY'
import os
from pathlib import Path
path = Path('/tmp/s1a-desktop-fixture.txt')
assert path.read_text(encoding='utf-8') == '本地桌面代理\n第二行：验证保存。'
assert path.stat().st_mtime_ns >= int(os.environ['S1A_FILE_CHECK_STARTED_NS'])
print('Verified fresh file and exact multiline text')
PY
```

## Current-code regression output

These are the existing **fake-driver tests**, separate from the native runs. The same-text case models
a confirmed replacement of the selected `hello` in `hello world`; it does not establish arbitrary native
selection-range support. Ambiguity checks cover duplicate labels, duplicate identifiers, disabled duplicates,
and the valid same-label/distinct-identifier case. [Test source](../../tests/test_desktop_actions.py).

```bash
uv sync --extra dev --frozen
uv run pytest -v --tb=short tests/test_desktop_actions.py -k \
  'saved_status_requires_verified_text_without_file_check or insert_accepts_replacing_selected_payload_with_identical_text or ambiguous_text_fields_are_not_offered_or_written or same_label_with_distinct_identifiers_keeps_readback_identity or unchanged_insert_requires_driver_confirmation_and_matching_text'
uv run pytest -q --tb=short
```

Terminal excerpts, Python 3.13.5 / pytest 9.1.1:

```text
tests/test_desktop_actions.py::TestDocumentActions::test_ambiguous_text_fields_are_not_offered_or_written PASSED [ 20%]
tests/test_desktop_actions.py::TestDocumentActions::test_insert_accepts_replacing_selected_payload_with_identical_text PASSED [ 40%]
tests/test_desktop_actions.py::TestDocumentActions::test_same_label_with_distinct_identifiers_keeps_readback_identity PASSED [ 60%]
tests/test_desktop_actions.py::TestDocumentActions::test_saved_status_requires_verified_text_without_file_check PASSED [ 80%]
tests/test_desktop_actions.py::TestDocumentActions::test_unchanged_insert_requires_driver_confirmation_and_matching_text PASSED [100%]
5 passed, 12 deselected, 3 warnings, 5 subtests passed in 0.02s
522 passed, 41 skipped, 3 warnings, 81 subtests passed in 17.14s
```

Core + dev checks also passed: `ruff format --check .`, `ruff check .`, `ty check`, `uv lock --check`,
`uv build`, `bash -n evals/desktop/*.sh`, and `scripts/smoke.sh` (`smoke: ok`). The 41 skips are optional
game/replay dependency checks in the core install; the browser system directory is separately excluded by
the repository's default pytest configuration. Both localhost-server lifecycle tests that were previously
environment-blocked passed in this run. Three upstream deprecation warnings remained.
Windows title-selection/binding coverage uses mocked driver replies; there was no native Windows run.
At capture time, [upstream CI for this source](https://github.com/ThinkFlowLab/system1-agents/actions/runs/37215823156)
was `action_required`, with no test jobs run. Local passes are not an upstream CI pass.

## Sharing and attribution

This terminal evidence uses only the repository's fixture and synthetic task text. Personal paths and
process/session identifiers are omitted; timestamps, actions, failures and verification results are retained.
It is an actual-run transcript, with no video, replay speed or staged screens. The trace, recorder and
fixture-derived evidence are contributed under the repository's [Apache-2.0 license](../../LICENSE).
Attribution: QianCyrus; fixture copyright 2026 ThinkFlowLab. Retain the license and applicable attribution
when reusing it. No model weights or third-party desktop content are included.

## Recorder used for the instrumented runs

The recorder calls the existing CLI entry point with the listed desktop flags. Its wrappers await the
original model/driver methods and return their results unchanged. It records model setup time, fixture
snapshots, input RPC replies, every episode and a separate filesystem check. The Chinese fixed-plan
run used the plain CLI plus the same before/after filesystem checks.

Save this source as `/tmp/s1a-evidence-recorder.py`. Set `EVIDENCE_DIR`, `EVIDENCE_FILE` and
`EVIDENCE_EXPECTED`; for the append-only visual fixture also set `EVIDENCE_APPEND=1`.
Use a new output directory for each run. Raw local outputs may contain paths or session identifiers;
review them before sharing. The public transcript above normalizes those identifiers and paths.
Formatted recorder SHA-256: `89ecbfbca2e1a48abc90b0bd449e8c1c43f5439db4de97dff59c004005322b7c`.
The source below differs only in formatting from the recorder used for the 2026-10-05 runs
([original source](https://github.com/ThinkFlowLab/system1-agents/blob/1ffac8b4fd64b72bedfa15352f33e6827222811b/evals/desktop/text-evidence.md)).
Original-run recorder SHA-256: `dceb4f0984d431fa4c6fdd6c833257f25ca6070ee8bf6f5b3ea39994c1acdefd`. The parsed Python syntax trees match;
the historical run results above are unchanged.

<details>
<summary>Recorder source (observations only)</summary>

```python
"""Observe the real desktop CLI without changing its model choices or driver results."""

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from s1a import console  # noqa: F401 -- route harness logs before other imports
from s1a.desktop.driver import CuaDriver
from s1a.entry import s1a
from s1a.tool import series

root = Path(os.environ["EVIDENCE_DIR"])
root.mkdir(parents=True, exist_ok=True)
output = Path(os.environ["EVIDENCE_FILE"])
expected = os.environ["EVIDENCE_EXPECTED"]
append = os.environ.get("EVIDENCE_APPEND") == "1"
events = root / "trace.jsonl"


def record(kind, **fields):
    with events.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"kind": kind, **fields}, ensure_ascii=False) + "\n")


original_build = series.build_model
original_episode = series.run_episode
original_call = CuaDriver.call
original_snapshot = CuaDriver.window_state


def build_model(*args, **kwargs):
    started = time.perf_counter()
    model = original_build(*args, **kwargs)
    record("model_build", seconds=time.perf_counter() - started, name=model.name)
    original_warm = model.warm

    async def warm():
        started = time.perf_counter()
        try:
            return await original_warm()
        finally:
            record("model_warm", seconds=time.perf_counter() - started)

    model.warm = warm
    return model


async def call(self, tool, **args):
    result = await original_call(self, tool, **args)
    if tool in {"click", "type_text", "set_value"}:
        record("driver_input", tool=tool, args=args, result=result)
    else:
        record("driver_call", tool=tool)
    return result


async def snapshot(self, window, **kwargs):
    result = await original_snapshot(self, window, **kwargs)
    fields = {
        "window": asdict(window),
        "snapshot_id": result.snapshot_id,
        "elements": [asdict(e) for e in result.elements if e.label in {"Body", "Status", "Save", "Clear", "Reset"}],
    }
    capture = getattr(result, "capture", None)
    if capture is not None:
        import hashlib

        data = capture.image.data
        digest = hashlib.sha256(data).hexdigest()
        (root / f"{digest}.png").write_bytes(data)
        fields["capture"] = {
            "id": capture.capture_id,
            "width": capture.width,
            "height": capture.height,
            "sha256": digest,
        }
    record("snapshot", **fields)
    return result


async def episode(*args, **kwargs):
    before = output.read_text(encoding="utf-8") if output.exists() else None
    before_mtime = output.stat().st_mtime_ns if output.exists() else None
    started_ns = time.time_ns()
    result = await original_episode(*args, **kwargs)
    after = output.read_text(encoding="utf-8") if output.exists() else None
    after_mtime = output.stat().st_mtime_ns if output.exists() else None
    record("episode", **asdict(result))
    record(
        "independent_file_check",
        seed=result.seed,
        before=before,
        after=after,
        before_mtime_ns=before_mtime,
        after_mtime_ns=after_mtime,
        started_ns=started_ns,
        fresh=after_mtime is not None and after_mtime >= started_ns and after_mtime != before_mtime,
        matches=after == ((before or "") + expected if append else expected),
    )
    return result


sys.argv = ["s1a", "run", "desktop", *sys.argv[1:]]
with (
    patch.object(series, "build_model", build_model),
    patch.object(series, "run_episode", episode),
    patch.object(CuaDriver, "call", call),
    patch.object(CuaDriver, "window_state", snapshot),
):
    s1a()
```

</details>
