#!/bin/bash
# The demo CONTRIBUTING.md asks for: application/task -> system1-agents -> System1-Omni inference -> result,
# in one run, through the frontend rather than straight at clm-serve.
cd /Users/xiaoyu/Documents/casual/work/s1a-clm || exit 1
export UV_CACHE_DIR=/Users/xiaoyu/Documents/casual/.uv-cache
PY=.venv/bin/python
QUIET='grep -v -e "INFO |" -e "SyntaxWarning" -e "txt = " -e "for match in"'

echo "# application/task   ticket routing: 30 labelled tickets, five queues"
echo "# agents             s1a run ticket_router --model clm"
echo "# System1-Omni       omni-jev :8080  ->  clm-serve :8091  ->  Qwen3-8B on one RTX 4090"
echo

echo "\$ curl -s http://127.0.0.1:8080/health          # the frontend, ready, saying who is behind it"
curl -s http://127.0.0.1:8080/health | $PY -c "
import json, sys
d = json.load(sys.stdin)
print('  ', json.dumps({k: d[k] for k in ('ok', 'embedder', 'models')}))
print('   vector cache on', d['cache']['device'])
" 2>&1 | grep -v "INFO |"
echo

echo "\$ the three tickets this run routes (seed 0, the first three of thirty)"
$PY -c "
import random, sys
sys.path.insert(0, '.')
from s1a.agents.ticket_router import load_tickets, DEFAULT_DATASET
rows = load_tickets(DEFAULT_DATASET)
random.Random(0).shuffle(rows)
for r in rows[:3]:
    print(f\"   {r['id']}  label={r['label']:9} {r['title']}\")
    print(f\"      {r['description'][:92]}\")
" 2>&1 | grep -v "INFO |"
echo

echo "\$ CLM_URL=http://127.0.0.1:8080 s1a run ticket_router --model clm --rethink off \\"
echo "      --episodes 1 --seed 0 --batch-size 3 --max-steps 3 --showcase --log"
CLM_URL=http://127.0.0.1:8080 uv run --no-sync s1a run ticket_router --model clm --rethink off \
  --episodes 1 --seed 0 --batch-size 3 --max-steps 3 --showcase --log 2>&1 \
  | eval $QUIET
echo

echo "\$ the identity recorded in every tick, from the run's own episode.json"
JOB=$(ls -dt evals/showcase/ticket_router/*__clm | head -1)
$PY -c "
import glob, json
d = json.load(open(glob.glob('$JOB/*/agent/episode.json')[0]))
t = d['decisions'][0]
print('   source', t['source'], '| model', t['model'], '| ms', t['ms'])
print('   served_by', json.dumps(t['served_by']))
tr = d['extra']['ticket_router']
print('   routes  ', ', '.join(f\"{r['expected']}->{r['predicted']}\" for r in tr['routes']))
print('   correct ', str(tr['correct']) + '/' + str(tr['total']))
" 2>&1 | grep -v "INFO |"
