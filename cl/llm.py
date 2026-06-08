"""Thin, CACHED wrapper around the local `claude -p` one-shot CLI.

Every call is keyed by (model, prompt) and cached on disk, so the benchmark is
cheap to re-run and its LLM outputs are reproducible and inspectable. The SAME
model is used for every strategy, so any cross-strategy comparison is fair.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "bench", "cache")
DEFAULT_MODEL = os.environ.get("CL_MODEL", "claude-haiku-4-5-20251001")


def _key(model: str, prompt: str) -> str:
    h = hashlib.sha256(f"{model}\x00{prompt}".encode()).hexdigest()[:32]
    return os.path.join(CACHE_DIR, f"{h}.json")


def ask(prompt: str, model: str = None, timeout: int = 120) -> str:
    """One-shot LLM call, cached. Returns the model's text reply."""
    model = model or DEFAULT_MODEL
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _key(model, prompt)
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)["reply"]
    out = subprocess.run(
        ["claude", "-p", "--model", model, prompt],
        capture_output=True, text=True, timeout=timeout,
    )
    reply = out.stdout.strip()
    with open(path, "w") as f:
        json.dump({"model": model, "prompt": prompt, "reply": reply}, f)
    return reply


def cache_stats() -> dict:
    if not os.path.isdir(CACHE_DIR):
        return {"entries": 0}
    return {"entries": len([f for f in os.listdir(CACHE_DIR) if f.endswith(".json")])}
