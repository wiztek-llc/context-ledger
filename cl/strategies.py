"""Context-assembly strategies under test.

Each strategy replays a session feature-by-feature and, at every step, exposes
the working context an agent would hold. We record:

  peak_i : working-context tokens WHILE building feature i  (the number that
           must stay under the model's window for the agent to keep going)
  rest_i : working-context tokens AFTER committing feature i (resting size)

and, for retention, `answer_context(probe)` — the context (plus any retrieval)
the strategy can offer to answer a question about earlier work.

Strategies:
  Full            keep all raw build context (no compaction) — the do-nothing baseline
  Truncate(K)     keep only the last K tokens of raw context — cheap, forgets old work
  RollingSummary  LLM-summarize evicted features into a bounded prose buffer (models /compact)
  Ledger          structured + git-restorable entries; rehydrate on demand  ( OURS)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List

from . import tokens
from .ledger import LedgerEntry
from . import llm

SYSTEM = ("You are a coding agent building a product feature by feature.\n"
          "Working context follows.\n\n")


@dataclass
class Step:
    index: int
    peak: int
    rest: int


def _last_k_tokens(text: str, k: int) -> str:
    enc = tokens._enc()
    ids = enc.encode(text, disallowed_special=())
    if len(ids) <= k:
        return text
    return enc.decode(ids[-k:])


class Full:
    name = "Full (no compaction)"

    def __init__(self):
        self._raw = []

    def run(self, session) -> List[Step]:
        steps = []
        for f in session.features:
            prior = tokens.count(SYSTEM + "\n".join(self._raw))
            peak = prior + f.build_tokens
            self._raw.append(f.build_context)
            rest = tokens.count(SYSTEM + "\n".join(self._raw))
            steps.append(Step(f.index, peak, rest))
        return steps

    def answer_context(self, probe: str):
        return SYSTEM + "\n".join(self._raw), 0


class Truncate:
    def __init__(self, k: int = 8000):
        self.k = k
        self.name = f"Truncate (last {k//1000}k tok)"
        self._raw = ""

    def run(self, session) -> List[Step]:
        steps = []
        for f in session.features:
            prior = tokens.count(SYSTEM + self._raw)
            peak = prior + f.build_tokens
            self._raw = _last_k_tokens(self._raw + "\n" + f.build_context, self.k)
            rest = tokens.count(SYSTEM + self._raw)
            steps.append(Step(f.index, min(peak, self.k + tokens.count(SYSTEM)), rest))
        return steps

    def answer_context(self, probe: str):
        return SYSTEM + self._raw, 0


class RollingSummary:
    """LLM compaction: when the buffer exceeds `budget`, summarize the oldest
    features into a single bounded prose summary (models naive /compact)."""

    def __init__(self, budget: int = 6000, summary_cap: int = 900):
        self.budget = budget
        self.summary_cap = summary_cap
        self.name = f"RollingSummary (budget {budget//1000}k)"
        self.summary = ""
        self._recent: List[str] = []   # raw build contexts not yet summarized

    def _live(self) -> str:
        s = f"[summary of earlier features]\n{self.summary}\n\n" if self.summary else ""
        return SYSTEM + s + "\n".join(self._recent)

    def _compact(self):
        old = "\n".join(self._recent)
        prompt = (
            "Compress the following coding-agent work-log into a dense summary of "
            f"AT MOST ~{self.summary_cap} tokens. Preserve key decisions, public "
            "interfaces, and gotchas a teammate would need later. Keep any prior "
            "summary's facts too.\n\n"
            f"PRIOR SUMMARY:\n{self.summary}\n\nWORK LOG:\n{old}"
        )
        self.summary = _last_k_tokens(llm.ask(prompt), self.summary_cap)
        self._recent = []

    def run(self, session) -> List[Step]:
        steps = []
        for f in session.features:
            prior = tokens.count(self._live())
            peak = prior + f.build_tokens
            self._recent.append(f.build_context)
            if tokens.count(self._live()) > self.budget:
                self._compact()
            rest = tokens.count(self._live())
            steps.append(Step(f.index, peak, rest))
        return steps

    def answer_context(self, probe: str):
        return self._live(), 0


class Ledger:
    """OURS: structured + git-restorable entries; rehydrate relevant detail."""

    name = "Ledger (ours)"

    def __init__(self, rehydrate_top: int = 1):
        self.entries: List[LedgerEntry] = []
        self.rehydrate_top = rehydrate_top
        self._building = None

    def _live(self) -> str:
        led = "\n".join(e.render() for e in self.entries)
        return SYSTEM + "## Feature ledger (compacted)\n" + led

    def run(self, session) -> List[Step]:
        steps = []
        for f in session.features:
            prior = tokens.count(self._live())
            peak = prior + f.build_tokens            # raw context only while building
            self.entries.append(LedgerEntry.from_feature(f))   # commit -> compact
            rest = tokens.count(self._live())
            steps.append(Step(f.index, peak, rest))
        return steps

    def _retrieve(self, probe: str) -> str:
        """Lexical retrieval over the ledger, then rehydrate the top entry's diff
        from git — modelling an agent that greps its ledger and re-reads code."""
        q = set(w.lower() for w in probe.split() if len(w) > 3)
        scored = []
        for e in self.entries:
            hay = (e.subject + " " + e.body + " " + " ".join(e.interfaces) +
                   " " + " ".join(e.files)).lower()
            scored.append((sum(hay.count(w) for w in q), e))
        scored.sort(key=lambda x: x[0], reverse=True)
        chunks = []
        for _, e in scored[:self.rehydrate_top]:
            chunks.append(f"--- rehydrated git show {e.sha[:8]} ---\n{e.rehydrate()}")
        return "\n".join(chunks)

    def answer_context(self, probe: str):
        retrieved = self._retrieve(probe)
        ctx = self._live() + "\n\n## Rehydrated on demand\n" + retrieved
        return ctx, tokens.count(retrieved)
