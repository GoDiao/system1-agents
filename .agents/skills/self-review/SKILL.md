---
name: self-review
description: Self-review System1-Agents changes before opening a PR or requesting review, with reproducible task outcomes, appropriate demos, and evidence-backed claims.
---

# System1-Agents self-review

Read the target checkout's `CONTRIBUTING.md`, PR template, and applicable local
instructions. Record the actual target branch and base/head commits, and review
the full diff from their merge base plus relevant uncommitted changes. Distinguish
what is in the PR from local-only work; disclose if the base could not be refreshed.

Check correctness, focused scope, decision-model and front contracts, fallback
behavior, cancellation/timeouts, and resource cleanup as relevant. Verify tests
cover the changed behavior, including failure paths and a regression case for a
fix. Match docs and commands to the implementation. Run the applicable checks in
`CONTRIBUTING.md`; report exact commands, outcomes, and skipped checks with reasons.
Documentation-only changes need link/example/claim checks, not unrelated model runs.

This skill prepares a local contributor report. It does not itself authorize
edits, commits, pushes, external posts, paid model calls, downloads, or changes to
review status. Use only separately authorized execution resources and budgets.

## Task evidence

For changes to what an agent can accomplish, show a concrete task as **input →
actions → final result**. Define success using an observable outcome, not just a
`DONE` signal. Use a safe, reproducible scenario or fixture; include setup,
commands, inputs/seed, model and configuration, environment, and exact source
commits. Link the resulting logs or artifacts so a reviewer can trace the story.

When claiming improvement, compare baseline and head on the same tasks, inputs,
success criteria, and budgets. Report completion counts/denominators, elapsed
time, model calls and tool calls when measured. Include cost only if measured,
with the accounting scope and pricing basis; do not infer total cost from latency
or an incomplete token charge. Keep failures, retries, timeouts, and human
intervention in the results. Report repetitions and variation; one successful
demo is not a task-success rate. Mark missing metrics unmeasured, and remove or
qualify unsupported claims rather than manufacturing a comparison.

Use [CONTRIBUTING.md's video guide](../../../CONTRIBUTING.md#agent-video-demos)
to prepare, record and attach an agent demo. For agent behavior changes, prefer a
short real video (about 20–45 seconds); a terminal recording works for text agents
and rails. Screenshots can support the clip or explain a recording gap. Show the
relevant input, action sequence, and result, with failures or human intervention
visible. Label cuts, replay speed,
and elapsed timing honestly; link a fuller trace when a clip omits context. Do not
stage screens or present a replay as a live run. A replay must identify the source
run/commit, workload, and speed; a historical or upstream model demo is not proof
that the current agent integration works.

Choose figures that answer the review question: workflow screenshots, a short
action timeline, or task-success comparisons backed by the run records. There is
no asset quota. Nonvisual, docs-only, and test-only changes may use test output or
a concise explanation instead of video. If a relevant run cannot be made within
the available authorization, resources, or budget, report the gap and its impact;
do not turn a missing run into a pass or require a production-scale demonstration.

## PR demo/evidence section

Prepare a **Demo / evidence** section for the PR containing what applies:

- Task and observable result, or `N/A` with a concrete reason.
- Reproduction command/fixture, configuration, and baseline/head commits.
- Measured comparison and raw result links, including failures and limitations;
  distinguish personally run checks, author-reported results, and observed CI.
- Demo/figure links with captions stating the workload, source revision, and
  whether each item is an actual run, recorded replay, or explanatory illustration.

Make evidence reusable for accurate reviews and public updates without implying
permission to publish it elsewhere. Before attaching assets, check ownership,
license/attribution, and permission to share. Use safe sample data and redact
credentials, private URLs, personal/customer information, and sensitive screen or
log content. Verify redaction in the final exported files, captions, and metadata.
Keep useful measurement context after redaction. Clearly label diagrams, mockups,
and generated artwork as illustrations; never fabricate screens, results, or
performance claims. Link durable, reviewer-accessible artifacts rather than local
paths. If rights or safe disclosure are unresolved, omit the asset and state why.

Check System1-Omni's current model, modality and hardware support as described in
the video guide. Try a supported serving path when the branch has a compatible
client; otherwise record the missing integration or configuration. Pin both
repositories and verify the actual worker/frontend from run evidence. Keep
agent-task evidence separate from serving/kernel measurements. Do not add an
unrequested backend integration or run outside the authorized resources/budget
merely to produce a demo.

## Report

Lead with actionable findings and file/line references, then the reviewed scope,
commands/results, demo/evidence summary, and remaining gaps. Say when there are no
actionable findings without implying maintainer approval. Keep blocking gaps
visible and recommend a draft while they remain. Do not check the contributor's
boxes or publish on their behalf without separate authorization.
