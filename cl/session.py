"""Reconstruct a REAL coding session from a git repository's history.

A "session" models a long-horizon agent building a product feature-by-feature.
Each commit is one feature. The *build context* for a feature — the token-heavy
material an agent accumulates while building it — is modeled, from real repo
data, as:

    commit message  +  the full diff  +  the post-commit content of changed
    source files (what the agent had to read to make the change)

This is real bytes from a real project, so the token magnitudes and the facts
embedded in them are genuine (not synthetic).
"""
from __future__ import annotations
import subprocess
from dataclasses import dataclass, field
from typing import List

from . import tokens


def _git(repo: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, check=True,
    ).stdout


def _filter_diff(diff: str, exclude_exts) -> str:
    """Drop per-file sections of a unified diff whose path ends in an excluded
    extension (e.g. docs), so doc text doesn't leak cross-feature facts."""
    if not exclude_exts:
        return diff
    out, keep = [], True
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git "):
            path = line.split(" b/")[-1].strip()
            keep = not path.endswith(tuple(exclude_exts))
        if keep:
            out.append(line)
    return "".join(out)


@dataclass
class Feature:
    """One committed feature and the build context that produced it."""
    index: int
    sha: str
    subject: str
    body: str
    files: List[str]
    diff: str
    file_contents: dict          # path -> content at this commit (read context)
    repo: str

    @property
    def build_context(self) -> str:
        """The raw, token-heavy context an agent holds while building this."""
        reads = "\n".join(
            f"=== FILE {p} ===\n{c}" for p, c in self.file_contents.items()
        )
        return (
            f"## Building feature {self.index}: {self.subject}\n"
            f"{self.body}\n\n"
            f"--- files read ---\n{reads}\n\n"
            f"--- diff produced ---\n{self.diff}\n"
        )

    @property
    def build_tokens(self) -> int:
        return tokens.count(self.build_context)

    def show(self, ref: str) -> str:
        """Rehydrate arbitrary detail from git on demand (restorable memory)."""
        return _git(self.repo, "show", ref)


@dataclass
class Session:
    repo: str
    features: List[Feature] = field(default_factory=list)

    @classmethod
    def from_repo(cls, repo: str, max_files_per_commit: int = 12,
                  source_exts=(".py", ".sh", ".json"),
                  exclude_exts=(".md",)) -> "Session":
        """Reconstruct a session. By default DOCS (.md) are excluded from the
        build context: READMEs are written to summarize features, so including a
        later feature's docs re-states earlier features' facts and confounds a
        *memory* test. Facts then live in the code / commit message / diff that
        actually created them. (Docs still appear in each feature's file map.)
        """
        shas = _git(repo, "log", "--reverse", "--format=%H").split()
        feats: List[Feature] = []
        for i, sha in enumerate(shas):
            subject = _git(repo, "show", "-s", "--format=%s", sha).strip()
            body = _git(repo, "show", "-s", "--format=%b", sha).strip()
            files = [f for f in _git(repo, "show", "--name-only",
                                     "--format=", sha).split("\n") if f.strip()]
            diff = _filter_diff(_git(repo, "show", "--format=", sha), exclude_exts)
            contents = {}
            for p in files[:max_files_per_commit]:
                if not p.endswith(source_exts) or p.endswith(exclude_exts):
                    continue
                try:
                    contents[p] = _git(repo, "show", f"{sha}:{p}")
                except subprocess.CalledProcessError:
                    pass  # file deleted in this commit
            feats.append(Feature(i, sha, subject, body, files, diff, contents, repo))
        return cls(repo, feats)

    def __len__(self):
        return len(self.features)
