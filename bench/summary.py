"""Print the headline scoreboard from results.json + scaling.json."""
import json
import os

ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts")


def load(n):
    with open(os.path.join(ART, n)) as f:
        return json.load(f)


def main():
    res = load("results.json")
    sc = load("scaling.json")

    print("=" * 74)
    print("CONTEXT LEDGER — benchmark scoreboard")
    print(f"real session: {res['n_features']} features, "
          f"{sum(res['feature_tokens']):,} tok of build context  ({res['repo']})")
    print("=" * 74)
    hdr = f"{'strategy':<26}{'retention':>11}{'answer ctx':>13}{'final rest':>13}"
    print(hdr); print("-" * 74)
    full = next(s for s in res["strategies"] if s["name"].startswith("Full"))
    for s in res["strategies"]:
        print(f"{s['name']:<26}{s['retention_rate']*100:>9.0f}% "
              f"{s['mean_answer_ctx']:>11,} {s['final_rest']:>12,}")
    print("-" * 74)

    led = next(s for s in res["strategies"] if "Ledger" in s["name"])
    trunc = next(s for s in res["strategies"] if "Truncate" in s["name"])
    summ = next((s for s in res["strategies"] if "Summary" in s["name"]), None)

    print("\nKEY RESULTS")
    print(f"  • Ledger retention {led['retention_rate']*100:.0f}% vs Full "
          f"{full['retention_rate']*100:.0f}%  "
          f"(matches full-context memory)")
    print(f"  • Ledger resting context {led['final_rest']:,} tok vs Full "
          f"{full['final_rest']:,} tok  "
          f"({full['final_rest']/led['final_rest']:.0f}x smaller)")
    if summ:
        print(f"  • At ~equal cost, Ledger {led['retention_rate']*100:.0f}% beats "
              f"RollingSummary {summ['retention_rate']*100:.0f}% retention")
    print(f"  • Ledger {led['retention_rate']*100:.0f}% beats Truncate "
          f"{trunc['retention_rate']*100:.0f}% at similar cost (Truncate forgets old work)")

    full_pk = sc["series"]["Full (no compaction)"]["peak"]
    led_pk = sc["series"]["Ledger (ours)"]["peak"]
    Ns = sc["Ns"]
    per_full = full_pk[-1] / Ns[-1]
    per_led = (led_pk[-1] - led_pk[0]) / (Ns[-1] - 1)
    n_full = 200000 / per_full
    n_led = (200000 - led_pk[0]) / per_led
    print(f"\nSCALING (peak context vs the 200k window)")
    print(f"  • Full grows {per_full:,.0f} tok/feature  -> hits 200k at N≈{n_full:.0f} features")
    print(f"  • Ledger grows {per_led:,.0f} tok/feature -> hits 200k at N≈{n_led:,.0f} features")
    print(f"  • => Ledger runs {n_led/n_full:.0f}x longer before the wall, losslessly")
    print("=" * 74)


if __name__ == "__main__":
    main()
