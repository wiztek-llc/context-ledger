"""Live before/after: a fact about the OLDEST feature that Truncate forgets
but Ledger recovers via git rehydration. Shows the actual mechanism + answers."""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cl.session import Session
from cl.strategies import Full, Truncate, RollingSummary, Ledger
from cl import tokens

REPO = os.environ.get("CL_REPO", "/Users/tek/Projects/cc-gradient-statusline")
ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts")
PROBE = "What RGB color is the dark 'pill' background behind the gradient status bar?"
FACT = "22, 23, 30"


def main():
    s = Session.from_repo(REPO)
    str: dict = {}
    full = Full(); full.run(s)
    trunc = Truncate(8000); trunc.run(s)
    led = Ledger(1); led.run(s)

    print("PROBE (a fact from feature 0, the OLDEST/most-compacted):")
    print(f"  {PROBE}")
    print(f"  ground truth: pill background = ({FACT})\n")
    print("Is the answer physically present in each strategy's retained context?")
    for name, st in [("Full", full), ("Truncate(8k)", trunc), ("Ledger(ours)", led)]:
        ctx, _ = st.answer_context(PROBE)
        present = FACT in ctx or FACT.replace(", ", ",") in ctx
        print(f"  {name:14} ctx={tokens.count(ctx):>6,} tok   fact present: "
              f"{'YES' if present else 'NO'}")

    print("\nLedger keeps only this compact entry for feature 0 in context:")
    print("  " + "\n  ".join(led.entries[0].render().splitlines()[:3]) + " ...")
    print("\n...and RECOVERS the exact evicted detail from git on demand:")
    rh = led.entries[0].rehydrate("statusline.py")
    for line in rh.splitlines():
        if FACT in line:
            print(f"  git show {led.entries[0].sha[:8]}:statusline.py  ->  {line.strip()}")
            break

    # actual LLM answers, if the benchmark has run
    rp = os.path.join(ART, "results.json")
    if os.path.isfile(rp):
        res = json.load(open(rp))
        print("\nActual LLM answers to this probe (from the benchmark):")
        for stg in res["strategies"]:
            r = next((x for x in stg["retention"] if x["id"] == "pill_bg"), None)
            if r:
                tag = "CORRECT" if r["correct"] else "WRONG  "
                print(f"  [{tag}] {stg['name'].split(' (')[0]:14}: {r['answer'][:90]}")


if __name__ == "__main__":
    main()
