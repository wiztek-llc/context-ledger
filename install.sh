#!/usr/bin/env bash
# Install Context Ledger.
#   ./install.sh                  # install the ctxledger CLI; prompt for live hooks
#   ./install.sh --with-hooks     # also install the live Claude Code hooks (no prompt)
#   ./install.sh --no-hooks       # CLI only
#   ./install.sh --with-bench     # also set up the benchmark venv
#
# The live hooks make Context Ledger run on your real builds:
#   * after every `git commit`, a compact ledger entry is recorded + injected
#   * at session start, the ledger is re-injected so it survives compaction
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"; HOOKS="$HOME/.claude/hooks"; SETTINGS="$HOME/.claude/settings.json"

WITH_HOOKS=""; WITH_BENCH=""
for a in "$@"; do case "$a" in
  --with-hooks) WITH_HOOKS=1;; --no-hooks) WITH_HOOKS=0;; --with-bench) WITH_BENCH=1;;
esac; done

command -v python3 >/dev/null || { echo "✗ python3 required"; exit 1; }
command -v git >/dev/null || { echo "✗ git required"; exit 1; }

echo "→ Installing Context Ledger"
mkdir -p "$BIN"
install -m 0755 "$SRC/ctxledger" "$BIN/ctxledger"
echo "  ✓ ctxledger CLI → $BIN/ctxledger"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "  ! add $BIN to PATH";; esac

if [ -z "$WITH_HOOKS" ]; then
  if [ -t 0 ]; then
    echo; echo "→ Install the LIVE hooks so Context Ledger runs on your real builds?"
    echo "  • records + injects a ledger entry after every git commit"
    echo "  • re-injects the ledger at session start (survives compaction)"
    printf "  Enable? [y/N] "; read -r ans || ans=""; case "$ans" in [Yy]*) WITH_HOOKS=1;; *) WITH_HOOKS=0;; esac
  else WITH_HOOKS=0; fi
fi

if [ "$WITH_HOOKS" = "1" ]; then
  mkdir -p "$HOOKS" "$HOME/.claude"
  install -m 0755 "$SRC/hooks/ledger-commit.py" "$HOOKS/ledger-commit.py"
  install -m 0755 "$SRC/hooks/ledger-inject.py" "$HOOKS/ledger-inject.py"
  echo "  ✓ hooks → $HOOKS"
  HOOKS="$HOOKS" SETTINGS="$SETTINGS" python3 - <<'PY'
import json, os, shutil
settings = os.environ["SETTINGS"]; hd = os.environ["HOOKS"]
if os.path.isfile(settings) and not os.path.exists(settings + ".bak"):
    shutil.copy(settings, settings + ".bak")
data = json.load(open(settings)) if os.path.isfile(settings) else {}
data.setdefault("hooks", {})
def ensure(event, entry, cmd):
    arr = data["hooks"].setdefault(event, [])
    for g in arr:
        for h in g.get("hooks", []):
            if h.get("command") == cmd: return
    arr.append(entry)
commit = hd + "/ledger-commit.py"; inject = hd + "/ledger-inject.py"
ensure("PostToolUse", {"matcher": "Bash", "hooks": [{"type": "command", "command": commit}]}, commit)
ensure("SessionStart", {"hooks": [{"type": "command", "command": inject}]}, inject)
json.dump(data, open(settings, "w"), indent=2)
print("  ✓ settings.json hooks → PostToolUse(Bash) + SessionStart")
PY
  echo "  • per-project ledger lives at <project>/.claude/context-ledger.md"
else
  echo "  · skipped live hooks (re-run with --with-hooks to add)"
fi

if [ "$WITH_BENCH" = "1" ]; then
  echo; echo "→ Setting up benchmark venv"
  [ -d "$SRC/.venv" ] || python3 -m venv "$SRC/.venv"
  "$SRC/.venv/bin/pip" install --quiet tiktoken matplotlib numpy
  echo "  ✓ venv ready — run ./run_all.sh to reproduce the benchmark"
fi
echo; echo "Done."
echo "Try:  ctxledger --help    |    in a git repo:  git commit … then  ctxledger show"
