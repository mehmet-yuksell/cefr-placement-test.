"""Ability estimation and score interpretation.

Pure functions only (no I/O, no UI). The response model is a 3PL with fixed,
provisional parameters:

    P(correct | theta) = c + (1 - c) / (1 + exp(-a (theta - b)))

Theta is estimated by EAP on a fixed grid with a normal prior; the standard
error is the posterior standard deviation.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from placement.config import (
    BORDERLINE_SE_FACTOR,
    CEFR_LEVELS,
    CUT_SCORES,
    DEFAULT_DISCRIMINATION,
    DEFAULT_GUESSING,
    EARLY_STOP_LEVEL_PROBABILITY,
    EARLY_STOP_MIN_ITEMS,
    MAX_TAGS_LISTED,
    MIN_ITEMS_FOR_RESULT,
    PRIOR_MEAN,
    PRIOR_SD,
    SCALED_THETA_RANGE,
    SUBSCORE_MIN_ITEMS,
    TAG_MIN_ITEMS,
    THETA_GRID_MAX,
    THETA_GRID_MIN,
    THETA_GRID_POINTS,
)
from placement.models import DomainScore, Result, TagScore

GRID: tuple[float, ...] = tuple(
    THETA_GRID_MIN + i * (THETA_GRID_MAX - THETA_GRID_MIN) / (THETA_GRID_POINTS - 1)
    for i in range(THETA_GRID_POINTS)
)
DOMAINS: tuple[str, ...] = ("grammar", "vocabulary", "reading")


class InsufficientDataError(ValueError):
    """Raised when too few items were answered to report a result."""


@dataclass(frozen=True)
class ScoredResponse:
    """The parts of one answer that scoring needs."""

    b: float
    correct: bool
    a: float = DEFAULT_DISCRIMINATION
    c: float = DEFAULT_GUESSING
    domain: str = ""
    tag: str = ""


@dataclass(frozen=True)
class Estimate:
    """EAP estimate with its posterior over :data:`GRID`."""

    theta: float
    se: float
    posterior: tuple[float, ...]


def p_correct(theta: float, b: float, a: float = DEFAULT_DISCRIMINATION, c: float = DEFAULT_GUESSING) -> float:
    """Probability of a correct response under the 3PL model."""
    z = max(-35.0, min(35.0, a * (theta - b)))
    return c + (1.0 - c) / (1.0 + math.exp(-z))


def posterior(
    responses: Sequence[ScoredResponse],
    prior_mean: float = PRIOR_MEAN,
    prior_sd: float = PRIOR_SD,
) -> tuple[float, ...]:
    """Normalised posterior weights over :data:`GRID` given the responses."""
    logs = []
    for theta in GRID:
        log_w = -0.5 * ((theta - prior_mean) / prior_sd) ** 2
        for r in responses:
            p = p_correct(theta, r.b, r.a, r.c)
            log_w += math.log(p if r.correct else 1.0 - p)
        logs.append(log_w)
    peak = max(logs)
    weights = [math.exp(v - peak) for v in logs]
    total = sum(weights)
    return tuple(w / total for w in weights)


def eap(
    responses: Sequence[ScoredResponse],
    prior_mean: float = PRIOR_MEAN,
    prior_sd: float = PRIOR_SD,
) -> Estimate:
    """Expected-a-posteriori theta and posterior SD (the reported SE)."""
    post = posterior(responses, prior_mean, prior_sd)
    mean = sum(w * t for w, t in zip(post, GRID))
    var = sum(w * (t - mean) ** 2 for w, t in zip(post, GRID))
    return Estimate(theta=mean, se=math.sqrt(var), posterior=post)


def level_for_theta(theta: float) -> str:
    """Map theta to a CEFR level with the provisional cut scores.

    A cut belongs to the level above it: theta = 0.0 is B2.
    """
    return CEFR_LEVELS[sum(theta >= cut for cut in CUT_SCORES)]


def level_probabilities(post: Sequence[float]) -> dict[str, float]:
    """Posterior probability of each CEFR level.

    Grid points that sit exactly on a cut score give half their mass to each
    neighbouring level, so the grid does not bias results upwards.
    """
    probs = dict.fromkeys(CEFR_LEVELS, 0.0)
    for weight, theta in zip(post, GRID):
        on_cut = [i for i, cut in enumerate(CUT_SCORES) if abs(theta - cut) < 1e-9]
        if on_cut:
            i = on_cut[0]
            probs[CEFR_LEVELS[i]] += weight / 2
            probs[CEFR_LEVELS[i + 1]] += weight / 2
        else:
            probs[level_for_theta(theta)] += weight
    return probs


def most_likely_level(probs: dict[str, float]) -> str:
    """The level with the highest probability (the lower level on a tie)."""
    return max(CEFR_LEVELS, key=lambda lvl: (probs[lvl], -CEFR_LEVELS.index(lvl)))


def borderline_with(theta: float, se: float, level: str, factor: float = BORDERLINE_SE_FACTOR) -> str | None:
    """Return the neighbouring level if theta is within ``factor`` x SE of a cut.

    Args:
        theta: The EAP estimate.
        se: Its standard error.
        level: The headline level; the neighbour is on the other side of the
            nearest cut from it.
        factor: Width of the borderline zone in SE units (config default).

    Returns:
        The neighbouring level, or None when the result is not borderline.
    """
    index = min(range(len(CUT_SCORES)), key=lambda i: abs(theta - CUT_SCORES[i]))
    if abs(theta - CUT_SCORES[index]) >= factor * se:
        return None
    lower, upper = CEFR_LEVELS[index], CEFR_LEVELS[index + 1]
    if level == lower:
        return upper
    if level == upper:
        return lower
    return None


def scaled_score(theta: float) -> int:
    """Display-only 0-100 score: theta clipped to [-3, 3], mapped linearly."""
    low, high = SCALED_THETA_RANGE
    clipped = max(low, min(high, theta))
    return round(100 * (clipped - low) / (high - low))


def domain_scores(responses: Sequence[ScoredResponse]) -> dict[str, DomainScore]:
    """Per-domain sub-scores; a band is given only with enough items."""
    scores = {}
    for domain in DOMAINS:
        subset = [r for r in responses if r.domain == domain]
        n_correct = sum(r.correct for r in subset)
        if len(subset) >= SUBSCORE_MIN_ITEMS:
            est = eap(subset)
            level = most_likely_level(level_probabilities(est.posterior))
            scores[domain] = DomainScore(domain, len(subset), n_correct, est.theta, est.se, level)
        else:
            scores[domain] = DomainScore(domain, len(subset), n_correct, None, None, None)
    return scores


def tag_scores(responses: Sequence[ScoredResponse], theta: float) -> list[TagScore]:
    """Observed vs model-expected correct answers per skill tag, sorted by tag."""
    groups: dict[str, list[ScoredResponse]] = {}
    for r in responses:
        if r.tag:
            groups.setdefault(r.tag, []).append(r)
    return [
        TagScore(
            tag=tag,
            n_items=len(group),
            n_correct=sum(r.correct for r in group),
            expected_correct=sum(p_correct(theta, r.b, r.a, r.c) for r in group),
        )
        for tag, group in sorted(groups.items())
    ]


def strengths_and_focus(
    tags: Sequence[TagScore],
    min_items: int = TAG_MIN_ITEMS,
    limit: int = MAX_TAGS_LISTED,
) -> tuple[list[TagScore], list[TagScore]]:
    """Split tags into strengths (did better than expected) and focus areas.

    Only tags backed by at least ``min_items`` items are considered; each list
    holds at most ``limit`` tags, strongest/weakest first.
    """
    eligible = [t for t in tags if t.n_items >= min_items]
    strengths = sorted((t for t in eligible if t.residual > 0), key=lambda t: (-t.residual, t.tag))
    focus = sorted((t for t in eligible if t.residual < 0), key=lambda t: (t.residual, t.tag))
    return strengths[:limit], focus[:limit]


def early_stop_reached(
    post: Sequence[float],
    n_answered: int,
    min_items: int = EARLY_STOP_MIN_ITEMS,
    threshold: float = EARLY_STOP_LEVEL_PROBABILITY,
) -> bool:
    """True once enough items are answered and one level is clearly favoured."""
    if n_answered < min_items:
        return False
    return max(level_probabilities(post).values()) >= threshold


def score_responses(responses: Sequence[ScoredResponse], complete: bool) -> Result:
    """Score a session.

    Args:
        responses: All answered items, in any order.
        complete: Whether the session reached its planned end (full length or
            a triggered early stop), as opposed to being abandoned.

    Raises:
        InsufficientDataError: if fewer than MIN_ITEMS_FOR_RESULT answers.
    """
    if len(responses) < MIN_ITEMS_FOR_RESULT:
        raise InsufficientDataError(
            f"{len(responses)} answers; at least {MIN_ITEMS_FOR_RESULT} are needed for a result"
        )
    est = eap(responses)
    probs = level_probabilities(est.posterior)
    level = most_likely_level(probs)
    return Result(
        theta=est.theta,
        se=est.se,
        level=level,
        scaled_score=scaled_score(est.theta),
        level_probabilities=probs,
        borderline_with=borderline_with(est.theta, est.se, level),
        n_answered=len(responses),
        complete=complete,
        domain_scores=domain_scores(responses),
        tag_scores=tag_scores(responses, est.theta),
    )
