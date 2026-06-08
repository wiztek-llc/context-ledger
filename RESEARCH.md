# Where Context Ledger sits in the state of the art

The problem — long-horizon agents exhausting the context window — is the most
active frontier in agent engineering right now. Context Ledger is a specific,
testable point in that design space: **structured + git-restorable compaction at
the commit boundary.**

## Prior art, and what Ledger borrows or differs from

| System / idea | What it does | Relation to Ledger |
|---|---|---|
| **Anthropic context editing + memory tool** (2025) | Auto-clears stale tool results; stores memory in files outside context | Ledger is this, but the "memory" is *git itself* (already lossless + addressable) and eviction fires at the **commit boundary**, not a token threshold |
| **Anthropic long-running harness** (2026) | Initializer + coding agent; feature list, git, progress files; compaction between features | Same shape; Ledger formalizes the per-feature record as a **structured, rehydratable** entry and *measures* the retention/cost tradeoff |
| **Sub-agent isolation** (Claude Code, multi-agent research) | Each feature in its own window; only a summary returns | The *proactive* sibling of Ledger (never let detail in vs evict it after). Complementary; both keep the orchestrator bounded |
| **MemGPT / Letta** | OS-style memory hierarchy; agent self-edits memory blocks | Ledger is a domain-specialized instance: the "archival store" is git; the "core memory" is the ledger |
| **Manus** | Filesystem as memory; **restorable compression** (keep the URL/path) | Ledger's core principle, specialized to commits: keep the SHA, drop the diff |
| **Cline Memory Bank** | Markdown files (`progress.md`, etc.) the agent reads/updates | Ledger auto-derives the structured record from the commit + diff, and adds the rehydrate pointer |
| **MEM1 / "Memory as Action"** (2025–26) | *Learn* what to keep/evict as an RL action | The open frontier Ledger doesn't attempt: our eviction policy is fixed ("on commit"). A learned policy is the natural next step |

**The contribution being tested here:** that anchoring eviction to the commit and
keeping a *git pointer* (not just prose) yields **full-context-level retention at
truncation-level cost** — a Pareto point the prose-summary and truncation
baselines cannot reach, because they are not *restorable*.

## Limitations (measured and acknowledged)

- **Retrieval can miss.** Rehydration uses lexical retrieval over the ledger to
  pick what to `git show`. A bad pick means a wrong answer — the system is not
  magic, and the benchmark reports it honestly. A learned/embedding retriever
  would lift this.
- **Rehydration costs tokens when invoked.** Ledger is cheap at rest and pays a
  bounded cost only when a question reaches back. The benchmark counts that cost.
  The win holds because most context stays compact; you only pay to recover.
- **The commit is a good but imperfect boundary.** A feature can span commits or
  a commit can be mid-feature. A "feature done + tests green" signal is a better
  trigger than every commit.
- **Cross-feature internals.** If feature B depends on A's *internals* (not its
  public interface), B must rehydrate A. Ledger keeps interfaces in-context for
  exactly this reason; internals come back on demand.
- **The extractor is deterministic here** (commit message + signatures). A
  production version would use an LLM extractor for richer entries; we chose the
  deterministic one so the benchmark is exactly reproducible.

## How the claim is verified

1. **Deterministic, exact** (no network): per-entry compression, resting-context
   curves, scaling to N features, rehydration round-trip recovering an evicted
   gotcha from git. See `tests/test_engine.py`.
2. **LLM-judged retention** (cached, same model for all strategies): each
   strategy answers real factual probes from only its retained context; scored
   against ground truth. See `bench/run.py`, raw answers in `artifacts/results.json`.
