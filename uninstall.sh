#!/usr/bin/env bash
# Remove the Context Ledger CLI and live hooks.
set -euo pipefail
SETTINGS="$HOME/.claude/settings.json"
rm -f "$HOME/.local/bin/ctxledger" && echo "✓ removed ctxledger CLI"
for h in ledger-commit.py ledger-inject.py; do
  f="$HOME/.claude/hooks/$h"; [ -f "$f" ] && rm -f "$f" && echo "✓ removed $f"
done
if [ -f "$SETTINGS" ]; then
  SETTINGS="$SETTINGS" python3 - <<'PY'
import json, os
s = os.environ["SETTINGS"]; d = json.load(open(s))
for ev in ("PostToolUse", "SessionStart"):
    arr = d.get("hooks", {}).get(ev, [])
    arr[:] = [g for g in arr if not any("ledger-" in h.get("command", "")
              for h in g.get("hooks", []))]
    if not arr:
        d["hooks"].pop(ev, None)
json.dump(d, open(s, "w"), indent=2)
print("✓ removed ledger hooks from settings.json")
PY
fi
echo "Note: per-project .claude/context-ledger.md files are left in place (your memory)."
