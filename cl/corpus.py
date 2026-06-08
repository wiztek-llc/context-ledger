"""Resolve the benchmark corpus.

Default: materialize the bundled real history (corpus/statusline.bundle) into
.corpus/ so the published numbers reproduce identically after a fresh clone —
no personal paths, no network. Override with CL_REPO=/path/to/any/git/repo.
"""
import os
import subprocess


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_repo():
    r = os.environ.get("CL_REPO")
    if r:
        return r
    root = repo_root()
    dest = os.path.join(root, ".corpus", "statusline")
    if not os.path.isdir(os.path.join(dest, ".git")):
        bundle = os.path.join(root, "corpus", "statusline.bundle")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        subprocess.run(["git", "clone", "-q", bundle, dest], check=True)
    return dest
