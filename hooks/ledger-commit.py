#!/usr/bin/env python3
"""PostToolUse hook: after a successful `git commit`, append a Context Ledger
entry for the new HEAD and inject it into context (so the agent knows the
feature's build detail can now be compacted — and how to rehydrate it).

Reads the PostToolUse JSON on stdin; emits hookSpecificOutput.additionalContext.
Dependency-free (git + stdlib). Locates `ctxledger` on PATH or next to itself.
"""
import json
import os
import shutil
import subprocess
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    ti = data.get("tool_input", {}) or {}
    cmd = ti.get("command", "") or ""
    if "git commit" not in cmd:
        return
    resp = json.dumps(data.get("tool_response", "")).lower()
    if any(w in resp for w in ("nothing to commit", "error", "failed", "fatal")):
        return

    cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    ctx = shutil.which("ctxledger") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "ctxledger")
    try:
        out = subprocess.run([sys.executable, ctx, "record", "--repo", cwd],
                             capture_output=True, text=True, timeout=20)
        entry = out.stdout.strip()
    except Exception:
        return
    if not entry:
        return
    msg = ("Feature committed and recorded in the Context Ledger "
           "(.claude/context-ledger.md). This feature's exploration/build context "
           "is now safe to compact — the entry below preserves the decisions + "
           "interfaces, and `git show <sha>` rehydrates any exact detail.\n\n" + entry)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse", "additionalContext": msg}}))


if __name__ == "__main__":
    main()
