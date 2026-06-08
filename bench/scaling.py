"""Scaling experiment: how peak working-context grows with session length.

We build N-feature sessions by cycling the 4 REAL features (so every feature has
a real token weight and a real ledger entry), then measure each deterministic
strategy's PEAK working context — the number that must stay under the model's
window for the agent to keep going. This shows exactly where Full crosses the
200k wall while Ledger stays flat.
"""
from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cl.session import Session, Feature
from cl.strategies import Full, Truncate, Ledger

REPO = os.environ.get("CL_REPO", "/Users/tek/Projects/cc-gradient-statusline")
ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts")


def session_of_n(base, n):
    feats = []
    for i in range(n):
        b = base.features[i % len(base.features)]
        feats.append(Feature(i, b.sha, b.subject, b.body, b.files, b.diff,
                             b.file_contents, b.repo))
    return Session(base.repo, feats)


def run():
    base = Session.from_repo(REPO)
    Ns = list(range(1, 41))
    out = {"Ns": Ns, "series": {}}
    for label, make in [("Full (no compaction)", lambda: Full()),
                        ("Truncate (last 8k tok)", lambda: Truncate(8000)),
                        ("Ledger (ours)", lambda: Ledger(1))]:
        peaks, rests = [], []
        for n in Ns:
            st = make()
            steps = st.run(session_of_n(base, n))
            peaks.append(max(s.peak for s in steps))
            rests.append(steps[-1].rest)
        out["series"][label] = {"peak": peaks, "rest": rests}
        print(f"{label:26}  peak@N=40 = {peaks[-1]:>9,}   rest@N=40 = {rests[-1]:>8,}")
    os.makedirs(ART, exist_ok=True)
    with open(os.path.join(ART, "scaling.json"), "w") as f:
        json.dump(out, f, indent=2)

    # where does Full cross the 200k window?
    full = out["series"]["Full (no compaction)"]["peak"]
    led = out["series"]["Ledger (ours)"]["peak"]
    per_full = full[-1] / Ns[-1]
    per_led = (led[-1] - led[0]) / (Ns[-1] - 1) if Ns[-1] > 1 else 0
    print(f"\nFull grows ~{per_full:,.0f} tok/feature -> crosses 200k at "
          f"N≈{200000/per_full:.0f}, crosses 1M at N≈{1000000/per_full:.0f}")
    print(f"Ledger grows ~{per_led:,.0f} tok/feature -> crosses 200k at "
          f"N≈{(200000-led[0])/per_led:,.0f}" if per_led > 0 else "Ledger ~flat")
    print("wrote artifacts/scaling.json")


if __name__ == "__main__":
    run()
