# Reproducing the recorded trial

The recording and worker wrappers for this isolated snapshot are the `reproduction/` entries of the [`served-recovery-evidence-preview.zip` archive](https://github.com/prettygirlisnotme/system1-agents/releases/download/pr31-served-recovery-evidence-20261006/served-recovery-evidence-preview.zip): `run_worker.py`, `record_live.py`, `preflight.sh`, `runtime-manifest.json`, `source-snapshot.patch` and `pr31-eval-candidate.patch`. Extract the archive and run the commands below from its root, so that the `reproduction/...` paths resolve.

## Source and environments

Start from agents PR #31 head `bd54c1461a782c138e28801441ece47321b274bd` and apply the archive's `reproduction/source-snapshot.patch`:

```bash
patch -p1 --batch --directory "$AGENT_SOURCE" < reproduction/source-snapshot.patch
```

The patch combines the PR #35 import and conflict resolutions with the separate PR #31 eval delta. Applying it to the PR #31 head and comparing against the executed snapshot produced an `s1a/` and `evals/` tree identical across 108 files, with zero differences. `pr31-eval-candidate.patch` is the eval delta alone for review; do not apply it again after the full patch.

Check out System1-Omni at `ae86032cba2466f45f42c2ebdfadbcfa8c30eb9f`. Its supported-models documentation describes the Python CPU worker. Recorded versions are in [worker-config.json](../data/worker-config.json) and [agent-environment.json](../data/agent-environment.json). In the agent environment the installed Laya is 0.3.5; that is not the decision backend, because HTTP requests go to the worker running 0.3.20.

Supply the English `convaiinnovations/laya@55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` checkpoint. In this run `MODEL_DIR` was a fixed local snapshot; a `.source.json` beside it carried the `repo` and `revision` values recorded above. Those are provenance metadata, not a health-reported revision, because the unmodified worker `/health` reports `revision: null` for a local path. Keep the fixed source when using `--model-path`, because the wrapper requires the recorded pin to match.

Chromium and Playwright MCP 0.0.78 are also required (recorded Node 24.12.0). The wrappers were validated in the existing environment; a new clean-room environment was not built.

## Worker invocation

Set `AGENT_SOURCE`, `OMNI_SOURCE`, `AGENT_PYTHON`, `WORKER_PYTHON`, `MODEL_DIR` and a fresh `RUN_ROOT` for your environment. Run both profiles sequentially, keeping worker and agent in the same compute job.

```bash
PROFILE=native                  # then match-legacy in a fresh run directory
PORT=8000                      # use an available loopback port
mkdir -p "$RUN_ROOT"
"$WORKER_PYTHON" reproduction/run_worker.py \
  --omni-src "$OMNI_SOURCE/src" \
  --profile "$PROFILE" --model-path "$MODEL_DIR" \
  --diagnostics "$RUN_ROOT/worker-diagnostics.json" \
  --device cpu --model english --host 127.0.0.1 --port "$PORT" --threads 4
```

Run this in the background under the job's cleanup handling, or in a second terminal in that job. Stop only the worker you started, after that profile.

Wait for a successful `/health` and populated diagnostics before the trials. The recorded gate, `preflight.sh`, expects `reproduction/env` to point at the worker environment and `reproduction/artifacts` to exist:

```bash
bash reproduction/preflight.sh \
  --diagnostics "$RUN_ROOT/worker-diagnostics.json" \
  --profile "$PROFILE" --port "$PORT"
```

The gate reads the loaded agent's configuration, CPU device and pinned revision. The default profile must show 512/192; the expanded profile must show 4096/1536. Read diagnostics before setting the matching client threshold; the health schema does not expose those windows.

## Exact agent invocation

Provide the credential file through `JEV_GO_KEY_FILE`; it is read without being printed. No credential is included here.

```bash
export JEV_SOURCE_ROOT="$AGENT_SOURCE"
export JEV_RECORD_DIR="$RUN_ROOT/recording"
export JEV_RECORD_VIDEO=1 JEV_RECORD_FULL_PROBE=1
export LAYA_SERVED_URL="http://127.0.0.1:$PORT"
export LAYA_SERVED_MODEL=english LAYA_SERVED_TIMEOUT_S=45
export LAYA_SERVED_MAX_LEN=512             # 4096 for match-legacy
export PLAYWRIGHT_MCP_ARGS='-y @playwright/mcp@0.0.78 --browser chromium'
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false

"$AGENT_PYTHON" reproduction/record_live.py \
  --model laya-served --tasks normal,recoverable --arms off,on --repeat 1 \
  --validate-submission --timeout 180 --max-steps 24 --stall-after 3 \
  --recovery-attempts 3 --recovery-timeout 45 \
  --results-dir "$RUN_ROOT/results"
```

For the second profile, start its worker afresh, pass its gate and change the client threshold to 4096. Keep results separate and retain failures.

The planner and chat text come from the real Go `deepseek-v4.1-flash` provider; the real `laya-served` client selects actions. Recording wraps existing calls and returns their original results. MCP video tools capture real browser frames. The saved oracle checks the actual form POST. Public excerpts omit routine probes and MCP file payloads but keep refreshed observations, plans, executed actions and the independent oracle. Source record and video hashes in [provenance.json](../data/provenance.json) identify the raw originals.

The `runtime-manifest.json` entry in the archive lists the original source and wrapper hashes. The full patch incorporates the separately recorded eval delta; its hash is in [provenance.json](../data/provenance.json).
