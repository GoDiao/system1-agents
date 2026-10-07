# Ticket router: CLM as the decision model

Date: 2026-10-06. The plan below was fixed before the runs. This page reports one measurement and one mechanism;
it is not a benchmark, and `--episodes 1 --seed 0` is 30 decisions, not 90.

## Setup

| | how | what answered |
|---|---|---|
| CLM | `--model clm`, `CLM_URL=http://127.0.0.1:8091` | `clm-latest` on `CLM_v0.1-8B.pt`, `clm-serve` over a tunnel |
| encoder | `serve_qwen3_8b.sh`'s settings, in Transformers | Qwen3-8B, last-token pooling, bfloat16, on one RTX 4090 (compute capability 8.9, driver 595.71.05, CUDA 13.0, transformers 5.17.0) |

- `system1-agents` at the commit that adds `--model clm`; `system1-omni` at `0450083`, whose
  `recipe/clm/native/VALIDATION.md` records the engine's own agreement with CLM's reference.
- `s1a run ticket_router --model clm --rethink off --episodes 3 --seed 0`, the whole 30-ticket set three times.
- The checkpoint is the published one, sha256 `b2b4a8c9…`; the engine reported `clm-latest` and the URL in every
  tick's `served_by`.
- 90 decisions, median 168 ms, no invalid keys, no errors.

## Results

| strategy | correct | source |
|---|---:|---|
| uniform random | 17/90 (19%) | [RESULTS.md](RESULTS.md) |
| keyword rule baseline | 51/90 (57%) | [RESULTS.md](RESULTS.md) |
| in-process Laya | 63/90 (70%) | [SERVED_LAYA.md](SERVED_LAYA.md) |
| **CLM, this loop's framing** | **18/90 (20%)** | this page |
| CLM, a short question instead of the rules | 36/90 (40%) | this page |

`--episodes 3 --seed 0` is 90 decisions over the same 30 tickets, and **every seed gave exactly 6**: the number is
not a noisy estimate, it is what a collapsed predictor scores. CLM's six are the six tickets whose label is
`human` — it answered `human` for all thirty, at a confidence of 0.86–0.98.

## Why, and what it costs

The tool loop observes `{"ticket": {…}, "progress": {…}}` and asks `ChoiceQuestion(queues, rules=RULES)`; the
backend sends the observation as the state and `RULES` as the instructions, which is what the wire body on this
branch shows. CLM's state head embeds the two together, and `RULES` is 696 characters of routing rubric that is
identical for every ticket — so it dominates that text and the thirty tickets stop being distinguishable. `RULES`
also ends with "If no unique queue fits, choose human", which is the answer the collapse lands on.

Sending the same tickets, the same five queue descriptions and the same rules under different renderings gives
(`evals/ticket_router/compare_framings.py`, 3 seeds, 90 decisions per row):

| state | instructions | correct |
|---|---|---:|
| the observation as JSON | the rules | 18/90 |
| the ticket as one sentence, then the rules | nothing | 18/90 |
| the ticket as one sentence | a short question | 36/90 |
| the ticket as one sentence | nothing | 39/90 |

The second row is the one that matters for where a fix belongs. Moving the rules out of `instructions` and into
the state — which is what the `cua` backend does with `cua_context`, and the only one of these a backend could do
without inventing text — changes **nothing**: 18/90 either way. Every point of the gap comes from replacing the
696-character rules essay with a short question, and that sentence is the caller's to write. A backend that made
it up would be answering a question nobody asked.

CLM's own preference — the short state and the short question its examples use (`"Dino runner game. 2 large cacti
ahead, 96 px away."` / `"Choose the best safe action for the dinosaur."`) — is the 40% row, and it is still below
the keyword baseline. `clm-raw`, the ablation that scores in the raw encoder space with no projection head, picks
`account` for the obvious password ticket where `clm-latest` picks `returns`, on two machines, so the encoder
ranks that ticket correctly and the heads are what move it (n=1; a control, not a finding).

## Recording

`docs/assets/demos/ticket-router-clm.gif` is the run in this table, recorded at the terminal: 30 tickets, every
decision with its key, confidence and latency, then the summary line. Nothing is typed or reordered — the frames
are drawn from the output as it arrived. The same run as an asciicast is `ticket-router-clm.cast`. A demo
illustrates one run; the table above is the evidence, and neither is a benchmark.

## Reproduce

```sh
# the encoder and the engine, per system1-omni's recipe/clm/README.md
CLM_URL=http://127.0.0.1:8091 uv run s1a run ticket_router --model clm --rethink off --episodes 1 --seed 0
```

The run's job folder holds the per-ticket routes, the probabilities behind each one and `served_by`.

## Limits

- 30 independent tickets. Three seeds shuffle the same thirty, so 90 decisions is not 90 samples, and the
  per-seed counts are identical rather than merely close. The 95% interval on 18/90 is roughly 12–30% — the random
  baseline — and on 36/90 it is 30–51%, which still does not reach the keyword baseline with confidence.
- The encoder is Transformers with last-token pooling, not a vLLM pooling server. The heads were trained against
  the vLLM path; a deployment's encoder is a different implementation and this page does not measure it.
- The framing table is one run per row and was measured after the first result, so it is exploratory.
- CLM answers choice and noul; the ticket router needs choice only.
