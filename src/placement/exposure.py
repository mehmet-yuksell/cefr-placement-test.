"""Exposure control.

Three rules keep item use spread out and fair to people who retake the test:

* items a user has already seen are excluded while unseen ones remain;
* when repeats cannot be avoided, the items seen longest ago (lowest attempt
  number) are reused first;
* among suitable items, one is chosen at random from the ``n`` closest to the
  target difficulty (randomesque selection), so no single item dominates.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from statistics import median
from typing import TypeVar

from placement.config import RANDOMESQUE_N

T = TypeVar("T")


def unseen(ids: Iterable[str], seen: Mapping[str, int]) -> list[str]:
    """Return the ids that the user has never been shown, in input order."""
    return [i for i in ids if i not in seen]


def oldest_seen(ids: Iterable[str], seen: Mapping[str, int]) -> list[str]:
    """Return the seen ids from the user's oldest attempt among ``ids``.

    Args:
        ids: Candidate item (or unit) ids.
        seen: Item id -> attempt number in which the user last saw it.

    Returns:
        Only the candidates whose last-seen attempt is the earliest one, so
        reuse starts with the items the user is least likely to remember.
    """
    seen_ids = [i for i in ids if i in seen]
    if not seen_ids:
        return []
    oldest = min(seen[i] for i in seen_ids)
    return [i for i in seen_ids if seen[i] == oldest]


def randomesque(
    candidates: Sequence[T],
    distance: Callable[[T], float],
    key: Callable[[T], str],
    rng: random.Random,
    n: int = RANDOMESQUE_N,
) -> T:
    """Pick at random among the ``n`` candidates closest to the target.

    Ties in distance are broken by ``key`` so the shortlist, and therefore the
    result for a given ``rng`` state, is reproducible.
    """
    if not candidates:
        raise ValueError("no candidates to choose from")
    shortlist = sorted(candidates, key=lambda c: (distance(c), key(c)))[: max(1, n)]
    return rng.choice(shortlist)


@dataclass(frozen=True)
class ExposureSummary:
    """How evenly a bank was used across a number of administered tests."""

    n_tests: int
    max_rate: float
    median_rate: float
    unused_share: float
    most_exposed: list[tuple[str, float]]


def summarise_exposure(counts: Mapping[str, int], bank_ids: Iterable[str], n_tests: int) -> ExposureSummary:
    """Summarise exposure counts (times each item was shown) over ``n_tests``."""
    ids = list(bank_ids)
    rates = {i: counts.get(i, 0) / n_tests for i in ids} if n_tests else dict.fromkeys(ids, 0.0)
    ranked = sorted(rates.items(), key=lambda kv: (-kv[1], kv[0]))
    return ExposureSummary(
        n_tests=n_tests,
        max_rate=max(rates.values(), default=0.0),
        median_rate=median(rates.values()) if rates else 0.0,
        unused_share=sum(1 for r in rates.values() if r == 0) / len(ids) if ids else 0.0,
        most_exposed=ranked[:5],
    )
