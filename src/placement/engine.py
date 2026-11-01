"""Test assembly: on-the-fly multistage adaptive testing with content balancing.

A test is a sequence of positions split into stages (10/10/8 at 28 items).
Every position has a target difficulty:

* routing stage: the anchor of a planned CEFR level (1 A1, 2 A2, 3 B1,
  3 B2, 1 C1 per 10 items, easiest first);
* targeted stage: ``theta1 - INFO_PEAK_OFFSET``, where theta1 is the EAP
  estimate after the routing stage;
* refinement stage: halfway between theta2 and the nearest cut score, minus
  the same offset, so the last items sharpen the decision at that boundary.

The fixed form uses targets spread evenly over A1-C2 and never adapts.

For each new position the engine first chooses a slot kind (type/domain): the
kind furthest behind its proportional quota, ties broken at random. It then
picks a unit (an item, or a passage with all its questions, served together)
closest to the target, at random among the RANDOMESQUE_N closest. Content
balance takes priority over difficulty. When the preferred choice is
impossible it relaxes in this order, logging each relaxation as an event:

1. a kind with quota left, unseen by this user, within the band
   (|b - target| <= BAND_HALF_WIDTH), trying kinds in deficit order;
2. a kind with quota left, unseen, at any distance          -> "band_fallback";
3. any kind (quota exceeded), unseen                         -> "content_relaxed";
4. units the user has seen, from their oldest attempt first  -> "repeat";
5. nothing left at all: the test ends early                  -> "bank_exhausted".
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from itertools import accumulate
from typing import Any

from placement import exposure
from placement.bank import ItemBank
from placement.config import (
    ANCHOR_B,
    BAND_HALF_WIDTH,
    CUT_SCORES,
    EARLY_STOP_ENABLED,
    INFO_PEAK_OFFSET,
    RANDOMESQUE_N,
    TEST_LENGTH,
    fixed_form_levels,
    routing_levels,
    slot_quotas,
    stage_lengths,
)
from placement.models import Item
from placement.scoring import ScoredResponse, eap, early_stop_reached

READING_KIND = "reading/reading"
MIN_PASSAGE_SIZE = 2


def kind_of(item: Item) -> str:
    """Slot kind of an item, e.g. ``"cloze/grammar"``."""
    return f"{item.type}/{item.domain}"


@dataclass(frozen=True)
class Unit:
    """What the engine selects: one item, or one passage with its questions."""

    id: str
    kind: str
    item_ids: tuple[str, ...]
    b: float

    @property
    def size(self) -> int:
        """Number of positions the unit occupies."""
        return len(self.item_ids)


@lru_cache(maxsize=8)
def bank_units(bank: ItemBank) -> tuple[Unit, ...]:
    """All selectable units of a bank (retired items excluded)."""
    units = []
    for item in bank.query():
        if item.passage_id is None:
            units.append(Unit(item.id, kind_of(item), (item.id,), item.difficulty_b))
    for passage in bank.passages:
        items = [i for i in bank.passage_items(passage.id) if i.status != "retired"]
        if items:
            mean_b = sum(i.difficulty_b for i in items) / len(items)
            units.append(Unit(passage.id, READING_KIND, tuple(i.id for i in items), mean_b))
    return tuple(units)


@dataclass
class TestState:
    """Everything the engine knows about one test in progress.

    ``seen`` maps item ids from the user's earlier attempts to the attempt
    number in which each was last shown. ``selected`` holds every chosen item
    in serving order; ``answers[i]`` is the correctness of ``selected[i]``.
    """

    mode: str
    seed: int
    length: int
    stage_sizes: tuple[int, ...]
    quotas: dict[str, int]
    targets: list[float | None]
    seen: dict[str, int] = field(default_factory=dict)
    early_stop: bool = EARLY_STOP_ENABLED
    selected: list[str] = field(default_factory=list)
    answers: list[bool] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    finished: bool = False
    stopped_early: bool = False

    @property
    def stage_ends(self) -> list[int]:
        """Cumulative position at which each stage ends."""
        return list(accumulate(self.stage_sizes))

    @property
    def flags(self) -> list[str]:
        """Distinct relaxation events that happened, for the session record."""
        kinds = {e["event"] for e in self.events if e["event"] != "stage_end"}
        return sorted(kinds)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable snapshot (for the session log)."""
        return asdict(self)


def new_test(
    bank: ItemBank,
    *,
    seed: int,
    mode: str = "adaptive",
    length: int = TEST_LENGTH,
    seen: dict[str, int] | None = None,
    early_stop: bool = EARLY_STOP_ENABLED,
) -> TestState:
    """Plan a new test.

    Args:
        bank: The validated item bank (used only to check it is non-empty).
        seed: Seed for every random choice in this test.
        mode: ``"adaptive"`` (multistage) or ``"fixed"`` (non-adaptive form).
        length: Number of items; stages and quotas scale with it.
        seen: Item id -> attempt number for the user's earlier attempts.
        early_stop: Enable the optional posterior-probability stopping rule.
    """
    if mode not in ("adaptive", "fixed"):
        raise ValueError(f"unknown mode {mode!r}")
    if length < 1 or len(bank) == 0:
        raise ValueError("a test needs a positive length and a non-empty bank")
    sizes = stage_lengths(length)
    if mode == "fixed":
        targets: list[float | None] = [ANCHOR_B[lvl] for lvl in fixed_form_levels(length)]
    else:
        targets = [ANCHOR_B[lvl] for lvl in routing_levels(sizes[0])]
        targets += [None] * (length - sizes[0])
    quotas = {f"{t}/{d}": n for (t, d), n in slot_quotas(length).items()}
    return TestState(
        mode=mode,
        seed=seed,
        length=length,
        stage_sizes=sizes,
        quotas=quotas,
        targets=targets,
        seen=dict(seen or {}),
        early_stop=early_stop,
    )


def stage_of(state: TestState, position: int) -> int:
    """1-based stage number of a 0-based position."""
    return next(i for i, end in enumerate(state.stage_ends, start=1) if position < end)


def stage_start(state: TestState, position: int) -> int:
    """First position of the stage that contains ``position``."""
    starts = [0, *state.stage_ends[:-1]]
    return starts[stage_of(state, position) - 1]


def editable_range(state: TestState) -> range:
    """Answered positions whose answers may still be changed.

    Only the current stage's earlier answers are editable: item selection
    inside a stage depends on the stage's targets and content quotas, never
    on whether an answer was right, so changing them cannot change which
    items were shown. Theta is re-estimated at a stage boundary, so the
    previous stage's answers are locked from then on. Editing is disabled
    entirely when the optional early stop is on (a changed answer could
    change a stopping decision already taken) and once the test is over.
    """
    answered = len(state.answers)
    if state.early_stop or state.finished or answered >= state.length:
        return range(0)
    return range(stage_start(state, answered), answered)


def change_answer(state: TestState, bank: ItemBank, position: int, correct: bool) -> None:
    """Change the correctness of an earlier answer in the current stage.

    Raises ValueError outside :func:`editable_range`. Only
    ``state.answers[position]`` changes: no item is selected, no stage
    boundary is crossed and theta is not re-estimated.
    """
    if position not in editable_range(state):
        raise ValueError(f"position {position} is not editable")
    bank.get(state.selected[position])  # the item must still exist in the bank
    state.answers[position] = correct


def current_item(state: TestState, bank: ItemBank) -> Item | None:
    """Return the item to show now, selecting a new unit if needed.

    Returns None when the test is finished.
    """
    if state.finished:
        return None
    if len(state.answers) == len(state.selected):
        unit = _select_unit(state, bank)
        if unit is None:
            state.finished = True
            return None
        state.selected.extend(unit.item_ids)
    return bank.get(state.selected[len(state.answers)])


def record_answer(state: TestState, bank: ItemBank, item_id: str, correct: bool) -> None:
    """Record the answer to the current item and advance the test.

    At stage boundaries (adaptive mode) theta is re-estimated and the next
    stage's targets are set. Raises ValueError if ``item_id`` is not the item
    currently on screen.
    """
    n = len(state.answers)
    if state.finished or n >= len(state.selected) or state.selected[n] != item_id:
        raise ValueError(f"{item_id} is not the current item")
    state.answers.append(correct)
    n += 1
    if n >= state.length:
        state.finished = True
        return
    if state.early_stop:
        est = eap(scored_responses(state, bank))
        if early_stop_reached(est.posterior, n):
            state.finished = state.stopped_early = True
            state.events.append({"event": "early_stop", "position": n, "theta": round(est.theta, 3)})
            return
    ends = state.stage_ends
    if state.mode == "adaptive" and n in ends[:-1]:
        est = eap(scored_responses(state, bank))
        next_stage = ends.index(n) + 1
        if next_stage == 1:
            target = est.theta - INFO_PEAK_OFFSET
        else:
            cut = min(CUT_SCORES, key=lambda c: abs(c - est.theta))
            target = (est.theta + cut) / 2 - INFO_PEAK_OFFSET
        for pos in range(n, ends[next_stage]):
            state.targets[pos] = target
        state.events.append(
            {
                "event": "stage_end",
                "position": n,
                "theta": round(est.theta, 3),
                "se": round(est.se, 3),
                "next_target_b": round(target, 3),
            }
        )


def replay(
    bank: ItemBank,
    answers: list[tuple[str, bool]],
    *,
    seed: int,
    mode: str,
    length: int = TEST_LENGTH,
    seen: dict[str, int] | None = None,
    early_stop: bool = EARLY_STOP_ENABLED,
) -> TestState | None:
    """Rebuild a test in progress from its stored answers.

    The engine is deterministic given the seed, the user's earlier exposure
    and the answers, so replaying them reproduces the same item sequence.
    Returns None if the stored items no longer match (e.g. the bank changed).
    """
    state = new_test(bank, seed=seed, mode=mode, length=length, seen=seen, early_stop=early_stop)
    for item_id, correct in answers:
        item = current_item(state, bank)
        if item is None or item.id != item_id:
            return None
        record_answer(state, bank, item_id, correct)
    return state


def scored_responses(state: TestState, bank: ItemBank) -> list[ScoredResponse]:
    """The answered items in a form :mod:`placement.scoring` can use."""
    out = []
    for item_id, correct in zip(state.selected, state.answers):
        item = bank.get(item_id)
        out.append(
            ScoredResponse(
                b=item.difficulty_b,
                correct=correct,
                a=item.discrimination_a,
                c=item.guessing_c,
                domain=item.domain,
                tag=item.skill_tested,
            )
        )
    return out


def _select_unit(state: TestState, bank: ItemBank) -> Unit | None:
    pos = len(state.selected)
    stage_end = next(end for end in state.stage_ends if pos < end)
    room = stage_end - pos
    target = state.targets[pos]
    if target is None:  # only reachable if a caller skipped record_answer
        raise RuntimeError(f"no target set for position {pos}")
    # The fixed form is the same for every first-time taker, so it ignores the seed.
    rng = random.Random(f"fixed:{pos}" if state.mode == "fixed" else f"{state.seed}:{pos}")
    n_best = 1 if state.mode == "fixed" else RANDOMESQUE_N

    counts: Counter[str] = Counter(kind_of(bank.get(i)) for i in state.selected)
    remaining = {k: q - counts[k] for k, q in state.quotas.items()}
    deficit = {k: q * (pos + 1) / state.length - counts[k] for k, q in state.quotas.items()}
    open_kinds = sorted((k for k, r in remaining.items() if r > 0), key=lambda k: (-deficit[k], rng.random()))

    used = set(state.selected)
    available = [u for u in bank_units(bank) if u.size <= room and not used.intersection(u.item_ids)]
    unit_seen = {
        u.id: max(state.seen[i] for i in u.item_ids if i in state.seen)
        for u in available
        if any(i in state.seen for i in u.item_ids)
    }
    fresh_ids = set(exposure.unseen((u.id for u in available), unit_seen))

    def fits_quota(u: Unit) -> bool:
        left = remaining.get(u.kind, 0) - u.size
        if left < 0:
            return False
        return u.kind != READING_KIND or left == 0 or left >= MIN_PASSAGE_SIZE

    def pick(pool: list[Unit], event: str | None) -> Unit:
        unit = exposure.randomesque(pool, lambda u: abs(u.b - target), lambda u: u.id, rng, n_best)
        if event:
            state.events.append(
                {"event": event, "position": pos, "unit": unit.id, "target_b": round(target, 3), "b": unit.b}
            )
        return unit

    fresh = [u for u in available if u.id in fresh_ids]
    for kind in open_kinds:
        pool = [u for u in fresh if u.kind == kind and fits_quota(u) and abs(u.b - target) <= BAND_HALF_WIDTH]
        if pool:
            return pick(pool, None)
    for kind in open_kinds:
        pool = [u for u in fresh if u.kind == kind and fits_quota(u)]
        if pool:
            return pick(pool, "band_fallback")
    if fresh:
        return pick(fresh, "content_relaxed")
    reuse = [u for u in available if fits_quota(u)] or available
    if reuse:
        oldest = set(exposure.oldest_seen((u.id for u in reuse), unit_seen))
        return pick([u for u in reuse if u.id in oldest], "repeat")
    state.events.append({"event": "bank_exhausted", "position": pos})
    return None
