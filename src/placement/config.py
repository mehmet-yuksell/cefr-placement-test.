"""Test-design constants shared by the bank, engine, scoring and report.

Every number that shapes the test lives here. Test length is a single
constant; stage lengths and content quotas are derived from it by
proportional apportionment, so a 40-item variant needs no code changes.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from typing import TypeVar

K = TypeVar("K", bound=Hashable)

CEFR_LEVELS: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

# Provisional expert difficulty anchors (logits) and cut scores between levels.
ANCHOR_B: dict[str, float] = {"A1": -2.5, "A2": -1.5, "B1": -0.5, "B2": 0.5, "C1": 1.5, "C2": 2.5}
MAX_B_ADJUSTMENT = 0.3
CUT_SCORES: tuple[float, ...] = (-2.0, -1.0, 0.0, 1.0, 2.0)

DEFAULT_DISCRIMINATION = 1.0
DEFAULT_GUESSING = 0.25

# EAP grid and prior.
THETA_GRID_MIN = -4.0
THETA_GRID_MAX = 4.0
THETA_GRID_POINTS = 81
PRIOR_MEAN = 0.0
PRIOR_SD = 1.0

# Scaled score: theta clipped to this range, mapped linearly to 0-100.
SCALED_THETA_RANGE = (-3.0, 3.0)

# A result is "borderline" when theta is within this many SEs of a cut score.
# 0.30 was chosen by simulation (DECISIONS.md, Phase 3): about 29% of results
# are flagged instead of 49% at 0.5, and the headline accuracy is unchanged.
BORDERLINE_SE_FACTOR = 0.30

# --- Test assembly -----------------------------------------------------------

TEST_LENGTH = 28

# Relative stage sizes (routing, targeted, refinement): 10/10/8 at 28 items.
STAGE_WEIGHTS: tuple[int, ...] = (10, 10, 8)

# Routing-stage level mix: 1 A1, 2 A2, 3 B1, 3 B2, 1 C1 per 10 items.
ROUTING_LEVEL_WEIGHTS: dict[str, int] = {"A1": 1, "A2": 2, "B1": 3, "B2": 3, "C1": 1}

# A slot kind is (item type, domain). Shares give type proportions of
# cloze 30 / error_id 25 / reading 25 / lexical_pragmatic 20 and domain
# proportions of grammar 40 / vocabulary 35 / reading 25.
SLOT_SHARES: dict[tuple[str, str], float] = {
    ("cloze", "grammar"): 0.15,
    ("cloze", "vocabulary"): 0.15,
    ("error_id", "grammar"): 0.25,
    ("reading", "reading"): 0.25,
    ("lexical_pragmatic", "vocabulary"): 0.20,
}

# For c = 0.25 and a = 1, a 3PL item is most informative at theta = b + 0.31,
# so an item aimed at ability t should have b close to t - INFO_PEAK_OFFSET.
INFO_PEAK_OFFSET = 0.31

# Randomesque selection: choose at random among the N best-matching items.
RANDOMESQUE_N = 5

# An item counts as "in band" when |b - target| is at most this.
BAND_HALF_WIDTH = 0.75

# Optional early stop (default off): stop once one level has at least this
# posterior probability, but never before EARLY_STOP_MIN_ITEMS answers.
EARLY_STOP_ENABLED = False
EARLY_STOP_MIN_ITEMS = 20
EARLY_STOP_LEVEL_PROBABILITY = 0.90

# --- Reporting ----------------------------------------------------------------

SUBSCORE_MIN_ITEMS = 5
TAG_MIN_ITEMS = 2
MAX_TAGS_LISTED = 3
# Below this many answers no result is produced (abandoned early).
MIN_ITEMS_FOR_RESULT = 10

# Controlled skill-tag vocabulary, per domain.
SKILL_TAGS: dict[str, tuple[str, ...]] = {
    "grammar": (
        "Tenses & aspect",
        "Verb patterns & agreement",
        "Articles & determiners",
        "Prepositions",
        "Comparatives & quantifiers",
        "Modal verbs",
        "Conditionals & hypotheticals",
        "Passive & causative",
        "Clause structure",
        "Inversion & emphasis",
    ),
    "vocabulary": (
        "Word choice",
        "Collocations",
        "Phrasal verbs",
        "Idioms & fixed expressions",
        "Register & pragmatics",
        "Word formation",
    ),
    "reading": ("Main idea", "Detail", "Inference", "Vocabulary in context"),
}


def apportion(total: int, weights: Mapping[K, float]) -> dict[K, int]:
    """Split ``total`` into integers proportional to ``weights``.

    Uses the largest-remainder method. Ties go to the key that comes first in
    ``weights``, so the result is deterministic.

    Args:
        total: Non-negative number of units to distribute.
        weights: Positive weights; they need not sum to one.

    Returns:
        A dict with the same keys whose values sum to ``total``.
    """
    if total < 0:
        raise ValueError("total must be non-negative")
    weight_sum = float(sum(weights.values()))
    if weight_sum <= 0:
        raise ValueError("weights must sum to a positive number")
    exact = {key: total * w / weight_sum for key, w in weights.items()}
    result = {key: int(value) for key, value in exact.items()}
    order = list(weights)
    leftovers = sorted(order, key=lambda k: (-(exact[k] - result[k]), order.index(k)))
    for key in leftovers[: total - sum(result.values())]:
        result[key] += 1
    return result


def stage_lengths(length: int = TEST_LENGTH) -> tuple[int, ...]:
    """Return the number of items in each stage for a test of ``length``."""
    split = apportion(length, dict(enumerate(STAGE_WEIGHTS)))
    return tuple(split[i] for i in range(len(STAGE_WEIGHTS)))


def slot_quotas(length: int = TEST_LENGTH) -> dict[tuple[str, str], int]:
    """Return how many items of each (type, domain) slot kind a test contains."""
    return apportion(length, SLOT_SHARES)


def routing_levels(n_items: int, weights: Mapping[str, int] | None = None) -> list[str]:
    """Return the target CEFR level for each routing position, easiest first.

    ``weights`` overrides ROUTING_LEVEL_WEIGHTS (used by simulation experiments).
    """
    split = apportion(n_items, weights or ROUTING_LEVEL_WEIGHTS)
    return [level for level in CEFR_LEVELS for _ in range(split.get(level, 0))]


def fixed_form_levels(length: int = TEST_LENGTH) -> list[str]:
    """Return the target level for each fixed-form position, spanning A1-C2."""
    split = apportion(length, {level: 1 for level in CEFR_LEVELS})
    return [level for level in CEFR_LEVELS for _ in range(split[level])]
