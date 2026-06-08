"""Generate the evidence charts from results.json + scaling.json."""
from __future__ import annotations
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts")

# palette (the user's cyan-centric scheme)
C = {"Full (no compaction)": "#FF3C3C", "Truncate (last 8k tok)": "#9698A8",
     "RollingSummary (budget 6k)": "#C85AFF", "Ledger (ours)": "#00B7C3"}
plt.rcParams.update({"figure.facecolor": "white", "axes.grid": True,
                     "grid.alpha": 0.25, "font.size": 11})


def _color(name):
    for k, v in C.items():
        if name.startswith(k.split(" (")[0]):
            return v
    return "#444"


def load(name):
    with open(os.path.join(ART, name)) as f:
        return json.load(f)


def chart_growth(res):
    fig, ax = plt.subplots(figsize=(8, 5))
    for s in res["strategies"]:
        xs = list(range(1, len(s["rests"]) + 1))
        ax.plot(xs, s["rests"], marker="o", lw=2.4, color=_color(s["name"]),
                label=s["name"])
    ax.set_title("Resting context after each committed feature\n(real 4-feature build)")
    ax.set_xlabel("features committed"); ax.set_ylabel("working-context tokens")
    ax.legend(); ax.set_xticks(range(1, len(res["strategies"][0]["rests"]) + 1))
    fig.tight_layout(); fig.savefig(os.path.join(ART, "context_growth.png"), dpi=130)
    print("wrote context_growth.png")


def chart_scaling(sc):
    fig, ax = plt.subplots(figsize=(8, 5))
    Ns = sc["Ns"]
    full = sc["series"]["Full (no compaction)"]["peak"]
    cross = next((Ns[i] for i in range(len(Ns)) if full[i] >= 200000), None)
    for name, d in sc["series"].items():
        ax.plot(Ns, d["peak"], lw=2.6, color=_color(name), label=name)
    ax.axhline(200000, ls="--", color="#333", lw=1)
    ax.text(39, 203000, "200k context window", fontsize=9, ha="right")
    if cross:
        ax.axvline(cross, ls=":", color="#FF3C3C", lw=1.2)
        ax.scatter([cross], [200000], color="#FF3C3C", zorder=5)
        ax.annotate(f"Full dies\nat N≈{cross}", (cross, 200000),
                    textcoords="offset points", xytext=(8, -42), color="#FF3C3C",
                    fontsize=9, fontweight="bold")
    ax.annotate("Ledger: still flat", (40, sc["series"]["Ledger (ours)"]["peak"][-1]),
                textcoords="offset points", xytext=(-118, 16), color="#00B7C3",
                fontsize=9, fontweight="bold")
    ax.set_title("Peak working-context vs session length\n(longer session = closer to the wall)")
    ax.set_xlabel("features in the session"); ax.set_ylabel("peak context tokens")
    ax.set_ylim(0, 230000); ax.set_xlim(1, 40)
    ax.legend(loc="upper left", framealpha=0.95)
    fig.tight_layout(); fig.savefig(os.path.join(ART, "scaling.png"), dpi=130)
    print("wrote scaling.png")


def chart_retention(res):
    fig, ax = plt.subplots(figsize=(8, 5))
    names = [s["name"] for s in res["strategies"]]
    rates = [s["retention_rate"] * 100 for s in res["strategies"]]
    cols = [_color(n) for n in names]
    bars = ax.bar(range(len(names)), rates, color=cols)
    for b, r in zip(bars, rates):
        ax.text(b.get_x() + b.get_width() / 2, r + 1.5, f"{r:.0f}%",
                ha="center", fontweight="bold")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([n.split(" (")[0] for n in names], rotation=12)
    ax.set_ylim(0, 108); ax.set_ylabel("retention (% probes answered correctly)")
    ax.set_title("Retention of earlier-feature facts after the full session")
    fig.tight_layout(); fig.savefig(os.path.join(ART, "retention.png"), dpi=130)
    print("wrote retention.png")


def chart_pareto(res):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for s in res["strategies"]:
        x = s["mean_answer_ctx"]; y = s["retention_rate"] * 100
        ax.scatter(x, y, s=240, color=_color(s["name"]), zorder=3,
                   edgecolor="white", linewidth=1.5)
        ax.annotate(s["name"].split(" (")[0], (x, y),
                    textcoords="offset points", xytext=(10, 6), fontsize=10)
    ax.set_xscale("log")
    xs = [s["mean_answer_ctx"] for s in res["strategies"]]
    ax.set_xlim(min(xs) * 0.7, max(xs) * 1.9)
    ax.set_ylim(52, 100)
    ax.set_xlabel("context tokens needed to answer (log) — lower is cheaper")
    ax.set_ylabel("retention (%) — higher is better")
    ax.set_title("Pareto frontier: retention vs context cost\n"
                 "(top-LEFT is best: full memory, low cost)")
    led = next(s for s in res["strategies"] if "Ledger" in s["name"])
    full = next(s for s in res["strategies"] if s["name"].startswith("Full"))
    ax.annotate("same memory as Full,\n~5× cheaper context",
                (led["mean_answer_ctx"], led["retention_rate"]*100),
                textcoords="offset points", xytext=(2, -40), color="#00B7C3",
                fontsize=10, fontweight="bold", ha="center")
    ax.annotate("", xy=(full["mean_answer_ctx"], full["retention_rate"]*100),
                xytext=(led["mean_answer_ctx"], led["retention_rate"]*100),
                arrowprops=dict(arrowstyle="<->", color="#bbb", ls="--"))
    fig.tight_layout(); fig.savefig(os.path.join(ART, "pareto.png"), dpi=130)
    print("wrote pareto.png")


if __name__ == "__main__":
    sc = load("scaling.json"); chart_scaling(sc)
    if os.path.isfile(os.path.join(ART, "results.json")):
        res = load("results.json")
        chart_growth(res); chart_retention(res); chart_pareto(res)
    print("done")
