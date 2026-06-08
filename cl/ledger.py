"""The Context Ledger: structured, restorable feature memory.

At each commit boundary we replace a feature's raw build context (~10k tokens)
with a compact LedgerEntry (~hundreds of tokens) that keeps:

  * the human-authored commit message (decisions/gotchas live here),
  * the public interface signatures touched (what later features depend on),
  * the changed-file map,
  * a git pointer (SHA) -> the LOSSLESS store any detail can be recovered from.

The entry is what stays in the agent's context. The pointer is what makes
eviction *safe*: when later work needs evicted detail, `rehydrate()` pulls the
exact bytes back from git. This is "restorable compression" (drop content, keep
the handle) applied at a semantic boundary (the commit).
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List

from . import tokens
from .session import Feature

# public signatures we care about for cross-feature dependencies
_SIG = re.compile(r"^\+\s*((?:def|class|async def)\s+[A-Za-z_]\w*\s*\([^)]*\)"
                  r"|[A-Z_][A-Z0-9_]+\s*=)", re.M)


def _interfaces(diff: str, limit: int = 14) -> List[str]:
    seen, out = set(), []
    for m in _SIG.finditer(diff):
        sig = re.sub(r"\s+", " ", m.group(1)).strip().rstrip("=").strip()
        if sig not in seen:
            seen.add(sig)
            out.append(sig)
        if len(out) >= limit:
            break
    return out


@dataclass
class LedgerEntry:
    index: int
    sha: str
    subject: str
    body: str
    interfaces: List[str]
    files: List[str]
    repo: str

    @classmethod
    def from_feature(cls, f: Feature) -> "LedgerEntry":
        return cls(f.index, f.sha, f.subject, f.body,
                   _interfaces(f.diff), f.files, f.repo)

    def render(self) -> str:
        """The compact text that lives in the agent's working context."""
        ifaces = "\n".join(f"    - {s}" for s in self.interfaces) or "    - (none)"
        files = ", ".join(self.files)
        return (
            f"### Feature {self.index}: {self.subject}  [commit {self.sha[:8]}]\n"
            f"{self.body}\n"
            f"  public interfaces:\n{ifaces}\n"
            f"  files: {files}\n"
            f"  rehydrate: git show {self.sha[:8]}  (or {self.sha[:8]}:<path>)\n"
        )

    @property
    def tokens(self) -> int:
        return tokens.count(self.render())

    # --- restorable memory: pull exact evicted detail back on demand ----------
    def rehydrate(self, path: str = None) -> str:
        import subprocess
        ref = f"{self.sha}:{path}" if path else self.sha
        return subprocess.run(["git", "-C", self.repo, "show", ref],
                              capture_output=True, text=True).stdout
