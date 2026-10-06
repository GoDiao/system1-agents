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
- `s1a run ticket_router --model clm --rethink off --episodes 1 --seed 0`, the whole 30-ticket set.
- The checkpoint is the published one, sha256 `b2b4a8c9…`; the engine reported `clm-latest` and the URL in every
  tick's `served_by`.
- 30 decisions, median 161 ms, no invalid keys, no errors.

## Results

| strategy | correct | source |
|---|---:|---|
| uniform random | 17/90 (19%) | [RESULTS.md](RESULTS.md) |
| keyword rule baseline | 51/90 (57%) | [RESULTS.md](RESULTS.md) |
| in-process Laya | 63/90 (70%) | [SERVED_LAYA.md](SERVED_LAYA.md) |
| **CLM, this loop's framing** | **6/30 (20%)** | this page |
| CLM, a short state instead | 15/30 (50%) | this page |

CLM's six correct are exactly the six tickets whose label is `human`: it answered `human` for all thirty, at a
confidence of 0.86–0.98. That is a collapsed predictor at chance, not a model that is nearly right.

## Why, and what it costs

The tool loop sends `state = {"ticket": {…}, "progress": {…}}` and `instructions = {"rules": RULES}`, and CLM's
state head embeds `state + "\n\n" + instructions`. `RULES` is ~900 characters and identical for every ticket, so it
dominates the embedding and the thirty states stop being distinguishable. `RULES` also ends with "If no unique queue
fits, choose human", which is the answer the collapse lands on.

Sending the same 30 tickets with the same candidate texts but a different rendering gives:

| state | instructions | correct |
|---|---|---:|
| JSON object | the rules | 6/30 |
| JSON object | a short question | 10/30 |
| the ticket as one sentence | the rules | 8/30 |
| the ticket as one sentence | a short question | 15/30 |
| the ticket as one sentence | nothing | 16/30 |

So the framing is worth ~24 points and CLM's own preference — the short state and the short question its examples
use (`"Dino runner game. 2 large cacti ahead, 96 px away."` / `"Choose the best safe action for the dinosaur."`) —
is the 50% row. It is still below the keyword baseline. `clm-raw`, the ablation that scores in the raw encoder
space with no projection head, picks `account` for the obvious password ticket where `clm-latest` picks `returns`,
so the encoder ranks that ticket correctly and the heads are what move it (n=1; a control, not a finding).

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

- 30 decisions, one seed. The 95% interval on 6/30 is roughly 8–32%, which is the random baseline, and on 15/30 it
  is 33–67%, which straddles the keyword baseline. Nothing here separates CLM from either with confidence.
- The encoder is Transformers with last-token pooling, not a vLLM pooling server. The heads were trained against
  the vLLM path; a deployment's encoder is a different implementation and this page does not measure it.
- The framing table is one run per row and was measured after the first result, so it is exploratory.
- CLM answers choice and noul; the ticket router needs choice only.
