#!/usr/bin/env python3
"""SessionStart hook: inject the project's Context Ledger into context so the
agent recalls every committed feature (decisions, interfaces, rehydrate pointers)
even in a fresh session or after a compaction. This is the durable memory that
makes commit-boundary eviction safe.

Plain stdout is added to context for SessionStart. Dependency-free.
"""
import os
import sys


def main():
    base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    ledger = os.path.join(base, ".claude", "context-ledger.md")
    if not os.path.isfile(ledger):
        return
    txt = open(ledger).read().strip()
    if not txt:
        return
    print("=== Context Ledger (compacted memory of prior features) ===")
    print(txt)
    print("=== rehydrate any feature's full detail with: git show <sha> ===")


if __name__ == "__main__":
    main()
