"""Deterministic engine tests (no LLM): exact, fast, reproducible."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cl.session import Session
from cl.ledger import LedgerEntry
from cl.strategies import Full, Truncate, Ledger
from cl import tokens
from cl.corpus import resolve_repo

REPO = resolve_repo()
ok = True


def check(name, cond):
    global ok
    ok = ok and cond
    print(("PASS " if cond else "FAIL ") + name)


def main():
    s = Session.from_repo(REPO)
    check("session loads features", len(s) >= 4)
    check("features carry real tokens", all(f.build_tokens > 500 for f in s.features))

    # ledger compression
    ratios = []
    for f in s.features:
        e = LedgerEntry.from_feature(f)
        ratios.append(f.build_tokens / e.tokens)
        check(f"entry {f.index} >=5x compression", f.build_tokens / e.tokens >= 5)
    check("mean compression >=10x", sum(ratios) / len(ratios) >= 10)

    # interface extraction finds a known signature
    e2 = LedgerEntry.from_feature(s.features[2])
    check("interfaces extracted", any("visible_len" in i for i in e2.interfaces))

    # rehydration round-trip recovers real evicted detail from git
    rh = e2.rehydrate()
    check("rehydrate returns the diff", len(rh) > 1000 and "diff --git" in rh)
    check("rehydrate recovers an evicted gotcha", "ps -A" in rh)
    rh_file = e2.rehydrate("statusline.py")
    check("rehydrate a specific file", "def visible_len" in rh_file)

    # strategy invariants
    full = Full().run(s)
    check("Full grows monotonically", all(full[i].rest <= full[i + 1].rest
                                          for i in range(len(full) - 1)))
    led = Ledger().run(s)
    check("Ledger resting < Full/10", led[-1].rest < full[-1].rest / 10)
    check("Ledger peak bounded by largest feature + small ledger",
          max(x.peak for x in led) < max(f.build_tokens for f in s.features) + 3000)
    trunc = Truncate(8000).run(s)
    check("Truncate stays under budget", all(x.rest <= 8016 + 50 for x in trunc))

    # token counting determinism
    check("token count deterministic", tokens.count("hello world") == tokens.count("hello world"))

    print("\n" + ("ALL PASS" if ok else "SOME FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
