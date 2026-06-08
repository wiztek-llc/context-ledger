"""Run the full benchmark: context-size curves + retention under each strategy.

For retention, each strategy answers every probe with `claude -p` using ONLY
the context that strategy retained at the END of the session (the hardest case:
the oldest feature is the most-compacted). Same model for all strategies.

Results -> artifacts/results.json  (re-runs are instant via the LLM cache).
"""
from __future__ import annotations
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cl.session import Session
from cl import tokens, llm
from cl.strategies import Full, Truncate, RollingSummary, Ledger
from bench.probes import PROBES

from cl.corpus import resolve_repo
REPO = resolve_repo()
ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts")


def judge(answer: str, accept) -> bool:
    a = answer.lower()
    if "not in context" in a:
        return False
    return any(s.lower() in a for s in accept)


def answer_probe(ctx: str, q: str) -> str:
    prompt = (
        f"{ctx}\n\n"
        "=== TASK ===\n"
        "You are resuming a coding project. Using ONLY the working context above, "
        f"answer this question:\n\nQ: {q}\n\n"
        "Answer in one sentence. If the context genuinely does not contain the "
        "answer, reply exactly: NOT IN CONTEXT"
    )
    return llm.ask(prompt)


def run():
    os.makedirs(ART, exist_ok=True)
    session = Session.from_repo(REPO)
    print(f"session: {len(session)} features from {REPO}", flush=True)

    strategies = [Full(), Truncate(8000), RollingSummary(6000, 900), Ledger(1)]
    results = {"repo": REPO, "n_features": len(session),
               "feature_tokens": [f.build_tokens for f in session.features],
               "strategies": []}

    for st in strategies:
        print(f"\n=== {st.name} ===", flush=True)
        steps = st.run(session)   # may make LLM calls (RollingSummary)
        peaks = [s.peak for s in steps]
        rests = [s.rest for s in steps]
        rec = {"name": st.name, "peaks": peaks, "rests": rests,
               "peak_max": max(peaks), "final_rest": rests[-1], "retention": []}
        print(f"  peak_max={max(peaks):,}  final_rest={rests[-1]:,}", flush=True)

        correct = 0
        for p in PROBES:
            ctx, retr = st.answer_context(p["q"])
            ans = answer_probe(ctx, p["q"])
            ok = judge(ans, p["accept"])
            correct += ok
            rec["retention"].append({
                "id": p["id"], "feature": p["feature"], "correct": ok,
                "answer_ctx_tokens": tokens.count(ctx), "retrieval_tokens": retr,
                "answer": ans[:240],
            })
            print(f"  [{'PASS' if ok else 'FAIL'}] {p['id']:18} "
                  f"ctx={tokens.count(ctx):>6,}  {ans[:70]!r}", flush=True)
        rec["retention_rate"] = correct / len(PROBES)
        rec["mean_answer_ctx"] = sum(r["answer_ctx_tokens"] for r in rec["retention"]) // len(PROBES)
        print(f"  RETENTION = {correct}/{len(PROBES)} = {rec['retention_rate']:.0%}  "
              f"mean answer ctx = {rec['mean_answer_ctx']:,} tok", flush=True)
        results["strategies"].append(rec)
        with open(os.path.join(ART, "results.json"), "w") as f:
            json.dump(results, f, indent=2)

    print(f"\nLLM cache: {llm.cache_stats()}", flush=True)
    print("wrote artifacts/results.json", flush=True)
    return results


if __name__ == "__main__":
    t0 = time.time()
    run()
    print(f"benchmark wall time: {time.time()-t0:.0f}s")
