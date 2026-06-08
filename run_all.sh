#!/usr/bin/env bash
# Reproduce every result in this repo from scratch.
#   ./run_all.sh                 # full run (uses LLM cache if present)
#   CL_REPO=/path/to/repo ./run_all.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install --quiet tiktoken matplotlib numpy
fi
PY=.venv/bin/python

echo "== engine tests (deterministic, no LLM) =="
$PY tests/test_engine.py

echo; echo "== scaling experiment (deterministic) =="
$PY bench/scaling.py

echo; echo "== retention benchmark (LLM via cached claude -p) =="
$PY bench/run.py

echo; echo "== charts =="
$PY bench/plot.py

echo; echo "== summary =="
$PY bench/summary.py
echo "artifacts in ./artifacts/"
