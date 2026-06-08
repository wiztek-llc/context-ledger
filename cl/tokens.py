"""Deterministic token accounting via tiktoken (cl100k_base).

We use a real, public, deterministic tokenizer so every number in the benchmark
is exactly reproducible. tiktoken's cl100k counts are a well-established proxy
for transformer context cost; the *relative* comparisons between strategies
(which is what the thesis rests on) are tokenizer-agnostic.
"""
from __future__ import annotations
import functools
import tiktoken


@functools.lru_cache(maxsize=1)
def _enc():
    return tiktoken.get_encoding("cl100k_base")


def count(text: str) -> int:
    if not text:
        return 0
    return len(_enc().encode(text, disallowed_special=()))


def count_many(texts) -> int:
    return sum(count(t) for t in texts)
