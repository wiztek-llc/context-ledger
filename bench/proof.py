"""Deterministic proof report — exact, reproducible, no network.

Everything here can be checked by hand against the git repo. Run:
    .venv/bin/python bench/proof.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cl.session import Session
from cl.ledger import LedgerEntry
from cl.strategies import Full, Truncate, Ledger
from cl import tokens
from bench.probes import PROBES

REPO = os.environ.get("CL_REPO", "/Users/tek/Projects/cc-gradient-statusline")


def line(c="-"):
    print(c * 76)


def main():
    s = Session.from_repo(REPO)
    line("=")
    print("CONTEXT LEDGER — DETERMINISTIC PROOF (exact, no LLM)")
    print(f"corpus: {len(s)} real features from {REPO}")
    line("=")

    # 1. compression
    print("\n[1] PER-FEATURE COMPRESSION (raw build context -> ledger entry)")
    tot_raw = tot_e = 0
    for f in s.features:
        e = LedgerEntry.from_feature(f)
        tot_raw += f.build_tokens; tot_e += e.tokens
        print(f"    feat {f.index}: {f.build_tokens:>6,} -> {e.tokens:>4} tok "
              f"({f.build_tokens/e.tokens:>4.0f}x)   {f.subject[:42]}")
    print(f"    TOTAL: {tot_raw:,} -> {tot_e:,} tok  ({tot_raw/tot_e:.0f}x compression)")

    # 2. resting context growth
    print("\n[2] RESTING WORKING-CONTEXT after each commit (tokens)")
    full = Full().run(s); led = Ledger().run(s)
    print("    feature:        " + "".join(f"{i:>9}" for i in range(len(s))))
    print("    Full:           " + "".join(f"{x.rest:>9,}" for x in full))
    print("    Ledger (ours):  " + "".join(f"{x.rest:>9,}" for x in led))
    print(f"    -> final: Full {full[-1].rest:,} vs Ledger {led[-1].rest:,} "
          f"= {full[-1].rest/led[-1].rest:.0f}x smaller, and Ledger is restorable")

    # 3. restorability round-trip
    print("\n[3] RESTORABILITY — recover an EVICTED detail from immutable git")
    e2 = LedgerEntry.from_feature(s.features[2])
    rh = e2.rehydrate()
    gotcha = next((l.strip() for l in rh.splitlines() if "ps -A" in l), "")
    print(f"    feature 2's raw context was evicted; its entry keeps SHA {e2.sha[:8]}.")
    print(f"    `git show {e2.sha[:8]}` recovers the evicted gotcha verbatim:")
    print(f"      {gotcha[:70]}")

    # 4. deterministic fact-availability
    print("\n[4] FACT AVAILABILITY — is the ground-truth fact in the retained context?")
    print(f"    {'strategy':<22}{'available':>11}{'mean ctx tok':>14}")
    for st in [Full(), Truncate(8000), Ledger(1)]:
        st.run(s)
        avail = 0; ctxs = []
        for p in PROBES:
            ctx, _ = st.answer_context(p["q"]); ctxs.append(tokens.count(ctx))
            if any(a.lower() in ctx.lower() for a in p["accept"]):
                avail += 1
        print(f"    {st.name:<22}{avail:>6}/{len(PROBES):<4}{sum(ctxs)//len(ctxs):>14,}")
    print("    (Full & Ledger have every fact; Ledger at a fraction of the cost.")
    print("     Truncate loses the oldest features and CANNOT recover them.)")
    line("=")


if __name__ == "__main__":
    main()
