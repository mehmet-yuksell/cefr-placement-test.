"""Shared fixtures: a synthetic bank large enough for no-repeat guarantees."""

from __future__ import annotations

import pytest

from placement.bank import ItemBank, load_bank
from placement.config import ANCHOR_B, CEFR_LEVELS, SKILL_TAGS
from placement.models import Item, Passage

TYPE3 = {"cloze": "CLZ", "error_id": "ERR", "reading": "RDG", "lexical_pragmatic": "LEX"}
OFFSETS = (-0.2, 0.0, 0.2, -0.1, 0.1)


def make_item(level: str, item_type: str, domain: str, n: int, passage_id: str | None = None) -> Item:
    """A structurally valid synthetic item (content is placeholder text)."""
    return Item(
        id=f"{level}-{TYPE3[item_type]}-{n:03d}",
        cefr_level=level,
        type=item_type,
        question=f"Synthetic {item_type} {n} ___",
        options=("key", "d1", "d2", "d3"),
        correct_answer="key",
        skill_tested=SKILL_TAGS[domain][n % len(SKILL_TAGS[domain])],
        explanation="synthetic",
        domain=domain,
        passage_id=passage_id,
        difficulty_b=ANCHOR_B[level] + OFFSETS[n % len(OFFSETS)],
        discrimination_a=1.0,
        guessing_c=0.25,
        distractor_rationale={"d1": "a", "d2": "b", "d3": "c"},
        status="provisional",
        author_notes="synthetic",
        version=1,
        instruction="",
    )


def make_bank(
    cloze_grammar: int = 4,
    cloze_vocab: int = 4,
    error_id: int = 6,
    lexical: int = 5,
    passage_sizes: tuple[int, ...] = (2, 3, 2),
    levels: tuple[str, ...] = CEFR_LEVELS,
) -> ItemBank:
    """Build a synthetic bank with the given number of units per level."""
    items: list[Item] = []
    passages: list[Passage] = []
    for level in levels:
        plan: list[tuple[str, str, str | None]] = (
            [("cloze", "grammar", None)] * cloze_grammar
            + [("cloze", "vocabulary", None)] * cloze_vocab
            + [("error_id", "grammar", None)] * error_id
            + [("lexical_pragmatic", "vocabulary", None)] * lexical
        )
        for p, size in enumerate(passage_sizes, start=1):
            pid = f"P-{level}-{p:02d}"
            passages.append(Passage(pid, level, f"Passage {pid}", "synthetic text " * 30))
            plan += [("reading", "reading", pid)] * size
        counter: dict[str, int] = {}
        for item_type, domain, passage_id in plan:
            counter[item_type] = counter.get(item_type, 0) + 1
            items.append(make_item(level, item_type, domain, counter[item_type], passage_id))
    return ItemBank(items, passages)


@pytest.fixture(scope="session")
def big_bank() -> ItemBank:
    return make_bank()


@pytest.fixture(scope="session")
def real_bank() -> ItemBank:
    return load_bank()
