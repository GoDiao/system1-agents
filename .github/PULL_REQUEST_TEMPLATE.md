<!-- Title: [Feat], [Fix], [Docs] or [Chore], then the outcome in one line. -->

## Why

<!-- The symptom: what a user, a run or a reviewer hits today. Link the issue if there is one. -->

## How

<!-- The root cause, then the fix. Name the files a reviewer should open first. -->

## What

<!-- Agents, flags, commands, records and docs that changed. Anything a caller has to change on their side. -->

## Verification

<!-- What you ran and what it printed, in a form a reviewer can repeat. -->

- [ ] `uv run ruff format --check . && uv run ruff check . && uv run ty check`
- [ ] `uv run pytest -q` and `scripts/smoke.sh`
- [ ] `CHANGELOG.md` and the docs say what the code does now

## Demo / evidence

<!-- Follow .agents/skills/self-review/SKILL.md: task input → actions → observed result;
reproduction command/fixture and exact baseline/head commits; measured comparisons
and raw results; useful demo/figure links with source revision, replay speed, and
limitations. Check asset rights and redaction. Label illustrations separately from
actual runs. Video is optional; use N/A with a reason where evidence does not apply. -->

For an agent-assisted self-review, use the [self-review skill](https://github.com/ThinkFlowLab/system1-agents/blob/main/.agents/skills/self-review/SKILL.md).
