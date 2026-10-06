# Served Laya recovery trial

Eight predeclared trials ran through the System1-Omni Python CPU worker with the `laya-served` client from PR #35. In both window profiles the normal form passed with recovery enabled; the locked-field task failed in both profiles. This is workflow evidence from two small synthetic tasks with one repetition per arm, not a success-rate measurement.

## Runtime and configuration

| Component | Exact revision or setting |
| --- | --- |
| Agents PR #31 | `bd54c1461a782c138e28801441ece47321b274bd` |
| Served client PR #35 | `365a17cf71b2273159874e4e61235887dc0f8f5f` |
| PR #35 base | `a2c46f4f40ce2c580f2bce14e6efb0b3315923e5` |
| System1-Omni | `ae86032cba2466f45f42c2ebdfadbcfa8c30eb9f` |
| Checkpoint | `convaiinnovations/laya`, English, `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` |
| Worker | `frontend.laya_mps` on CPU, Laya 0.3.20, torch 2.14.0+cpu, 4 intra/inter-op threads |
| Planner and free text | Go `deepseek-v4.1-flash`, thinking disabled, temperature 0, SDK retries 0 |
| Budgets | 180 s/task, 24 steps, stall after 3 unchanged actions, 3 recovery attempts, 45 s recovery active time |
| Request limits | 45 s/served decision, 45 s/chat request, 120-token recovery plan, 768-token ordinary chat ceiling |

PR #35 was unmerged at execution. The run used an isolated, uncommitted combination of the two PR heads with two merge conflicts resolved. A patch that reconstructs the recorded runtime from the PR #31 head is provided as `reproduction/source-snapshot.patch` inside the `served-recovery-evidence-preview.zip` archive; all 108 files under `s1a/` and `evals/` were compared byte for byte. [Provenance](data/provenance.json) records the pins and hashes.

PR #35 later advanced to `cdb6d6a7d20e1ba515d456d27b3acb08f55ced89`. A direct tree comparison shows 15 changed paths, all documentation, templates, logos and recipes, with no runtime change under `s1a/` or `evals/recovery/`. The experimental pins above are unchanged and are not rewritten to the newer head.

The worker's loaded `agent.cfg` was inspected before each profile:

| Profile | Loaded before | Applied override | Loaded after | Client `LAYA_SERVED_MAX_LEN` |
| --- | --- | --- | --- | --- |
| Checkpoint default (`native`) | 512 / 192 | none | 512 / 192 | 512 |
| Expanded (`match-legacy`) | 512 / 192 | 4096 / 1536 | 4096 / 1536 | 4096 |

Values are `max_len / head_max_len`. `native` names the checkpoint defaults; both profiles used the Python CPU worker with 4 threads and no GPU. The expanded profile changed the loaded configuration with the same weights. It is a private runtime override, not the worker default and not a retrained checkpoint. Raising the client threshold alone would not change the worker. [Loaded-worker diagnostics](data/worker-config.json) record device, package versions and both configurations. Checkpoint provenance comes from the fixed local snapshot's source manifest; the unmodified worker `/health` response reports `revision: null` for that local path.

No per-head truncation diagnostic was collected. Aggregate decision input-token counts sum across question heads, so a count above 512 does not by itself show overflow. Verifying the loaded configuration does not prove every prompt fit.

## Results

| Worker window | Task | Recovery | Independently verified | Decision calls | Replans | Total LLM calls | Elapsed s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 512/192 | normal | off | no | 4 | 0 | 2 | 30.517 |
| 512/192 | normal | on | yes | 7 | 1 | 3 | 42.044 |
| 512/192 | recoverable | off | no | 5 | 0 | 1 | 35.064 |
| 512/192 | recoverable | on | no | 5 | 0 | 1 | 34.899 |
| 4096/1536 (override) | normal | off | no | 7 | 0 | 4 | 85.169 |
| 4096/1536 (override) | normal | on | yes | 9 | 1 | 4 | 99.523 |
| 4096/1536 (override) | recoverable | off | no | 6 | 0 | 1 | 86.736 |
| 4096/1536 (override) | recoverable | on | no | 10 | 2 | 3 | 151.160 |

The fixture accepts a recorded `POST /submit/<task>` only when its value matches `hello world`. Every trial had a fresh fixture. Empty or `original` submissions returned a validation error and stayed failures. `DONE` and process exit codes are not the completion criterion.

All [eight trial records](data/trials.json) are included, including the six unverified outcomes. Arms ran off before on, and profiles ran sequentially. The small sample and fixed order do not support general success-rate, causal or performance claims.

`Total LLM calls` includes answer/value generation and the recovery planner; replans are already counted there and must not be added again. All `cost_usd` values are `null` because no explicit price configuration was supplied; `null` means unknown, not free. The reported 19-21 ms "model load" values measure HTTP-client construction, not the worker's model loading. Peak RSS and cold-start model load time were not measured; the job requested 4 CPUs, 12 GiB and no GPU.

An initial launch rejected a redundant `--require-device` argument before any trial or planner call. Only that outer CLI argument was removed; the wrapper still forwards the device requirement to the engine. The same original eight-cell schedule then ran once. The separate launch failure is recorded in [provenance](data/provenance.json).

The historical in-process report used Laya 0.3.5 on four CPU threads, also CPU. This run used 0.3.20 with different worker defaults in the first profile. The device did not change between the two runs, so this is not a serving-versus-in-process comparison and cannot isolate the effect of HTTP serving.

## Recorded workflows

**Success video ([PR #31 evidence comment](https://github.com/ThinkFlowLab/system1-agents/pull/31)), [trace](traces/success.json).** Default-window `normal/on`:

1. Laya selected Submit, Submit, Value and Value. Three consecutive actions left the page unchanged.
2. Recovery made a read-only refresh. The Value field was empty and the validation error remained.
3. The real planner wrote: "Type 'hello world' into the Value field (index 1) using TYPE_TEXT, then click Submit (index 2). The field is currently empty, so typing is the required next step before submitting."
4. Served Laya selected `TYPE_TEXT(Value)`. The Go value provider supplied `hello world`; Laya then selected `CLICK(Submit)`.
5. The independent server oracle accepted the final POST. There were 7 decision calls, 1 replan and 3 total LLM calls.

**Failure video ([PR #31 evidence comment](https://github.com/ThinkFlowLab/system1-agents/pull/31)), [trace](traces/failure.json).** Expanded-window `recoverable/on`:

The refreshed observation showed a locked field containing `original`. Two real plans recommended clicking Enable editing before typing. After the first plan, Laya selected `PRESS_ENTER(Value)` and kept pressing Enter; after the second plan the next decision was `BLOCKED`. No correct submission occurred. The oracle retained the single `original` POST. There were 10 decision calls and 2 replans, ending after 151.160 s. The planner succeeded; the model did not carry out the proposed first action.

The default-window `recoverable/on` failed without recovery: its four executed actions were Value, Value, Enable editing and Submit, followed by `BLOCKED`. It ended before the stall threshold triggered.

The success clip plays at 1x; the failure clip plays the entire recorded session at 3x. Both show the upper 200 pixels of the original 800x450 viewport, with no temporal cuts and a four-second oracle end card. Uncropped originals are `videos/success-original.webm` and `videos/failure-original.webm` inside the `served-recovery-evidence-preview.zip` archive. Caption timing follows trace phases and is approximate: browser screencast duration differs from the start/stop interval. The annotations come from saved records; no actions or plans were injected.

The recordings accompany the evidence comment on [PR #31](https://github.com/ThinkFlowLab/system1-agents/pull/31). The [reproduction archive](https://github.com/prettygirlisnotme/system1-agents/releases/download/pr31-served-recovery-evidence-20261006/served-recovery-evidence-preview.zip) contains the original recordings and source reconstruction. Recordings: contributor @prettygirlisnotme, using project fixtures. Reuse in project updates requires the author's approval.

## Reproduction

[Commands and runtime helpers](reproduction/README.md) cover the exact worker and agent invocations, the explicit profile settings and the source reconstruction patch. The archive `served-recovery-evidence-preview.zip` also contains the full reproduction helpers (`run_worker.py`, `record_live.py`, `preflight.sh`), the frozen `runtime-manifest.json` and `source-snapshot.patch`. The small PR #31 eval delta is kept separate as `reproduction/pr31-eval-candidate.patch` in the same archive; that integration delta is an uncommitted candidate and depends on the served client.

The earlier scripted mechanics runs remain separate evidence. The trials and videos in this report used actual Laya decisions and actual Go planner/value calls.
