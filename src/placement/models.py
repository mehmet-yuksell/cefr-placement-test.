"""Core data structures: items, passages, responses, sessions and results.

These are plain dataclasses with no I/O. Items carry ``dict`` fields, so they
compare by value but are not hashable; use ``item.id`` as a key.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from placement.config import TEST_LENGTH

CefrLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
ItemType = Literal["cloze", "error_id", "reading", "lexical_pragmatic"]
Domain = Literal["grammar", "vocabulary", "reading"]
ItemStatus = Literal["provisional", "calibrated", "retired"]
SessionMode = Literal["adaptive", "fixed"]
SessionStatus = Literal["in_progress", "completed", "abandoned"]

# Error-identification items mark their candidate segments as [segment].
SEGMENT_RE = re.compile(r"\[([^\[\]]+)\]")
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*")


def count_words(text: str) -> int:
    """Count words the way the bank rules do (contractions count as one)."""
    return len(_WORD_RE.findall(text))


@dataclass(frozen=True)
class Passage:
    """A short reading text shared by two or three reading items."""

    id: str
    cefr_level: CefrLevel
    title: str
    text: str
    status: ItemStatus = "provisional"
    version: int = 1

    @property
    def word_count(self) -> int:
        """Number of words in the passage text."""
        return count_words(self.text)


@dataclass(frozen=True)
class Item:
    """One four-option multiple-choice item with provisional 3PL parameters."""

    id: str
    cefr_level: CefrLevel
    type: ItemType
    question: str
    options: tuple[str, ...]
    correct_answer: str
    skill_tested: str
    explanation: str
    domain: Domain
    passage_id: str | None
    difficulty_b: float
    discrimination_a: float
    guessing_c: float
    distractor_rationale: dict[str, str]
    status: ItemStatus
    author_notes: str
    version: int
    instruction: str
    legacy_id: int | None = None

    @property
    def distractors(self) -> tuple[str, ...]:
        """The options that are not the key, in stored order."""
        return tuple(o for o in self.options if o != self.correct_answer)

    @property
    def uses_segments(self) -> bool:
        """True for error-identification items whose options are [segments]."""
        return self.type == "error_id" and SEGMENT_RE.search(self.question) is not None

    def is_correct(self, option: str | None) -> bool:
        """Return whether ``option`` is the key (exact text match)."""
        return option == self.correct_answer


@dataclass(frozen=True)
class Response:
    """One answered item within a session."""

    item_id: str
    chosen_option: str
    is_correct: bool
    response_time_s: float
    stage: int
    position: int


@dataclass
class Session:
    """A single test attempt by one (pseudonymous) user."""

    session_id: str
    user_hash: str
    mode: SessionMode
    seed: int
    started_at: str
    attempt_no: int = 1
    status: SessionStatus = "in_progress"
    test_length: int = TEST_LENGTH
    responses: list[Response] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DomainScore:
    """Sub-score for one domain; ``level`` is None when suppressed."""

    domain: Domain
    n_items: int
    n_correct: int
    theta: float | None
    se: float | None
    level: CefrLevel | None

    @property
    def percent_correct(self) -> float:
        """Share of this domain's items answered correctly, 0-100."""
        return 100.0 * self.n_correct / self.n_items if self.n_items else 0.0

    @property
    def suppressed(self) -> bool:
        """True when too few items back this sub-score to report a band."""
        return self.level is None


@dataclass(frozen=True)
class TagScore:
    """Performance on one skill tag relative to what theta predicts."""

    tag: str
    n_items: int
    n_correct: int
    expected_correct: float

    @property
    def residual(self) -> float:
        """Mean (observed - expected) per item; positive means a strength."""
        return (self.n_correct - self.expected_correct) / self.n_items


@dataclass(frozen=True)
class Result:
    """Scored outcome of a session."""

    theta: float
    se: float
    level: CefrLevel
    scaled_score: int
    level_probabilities: dict[str, float]
    borderline_with: CefrLevel | None
    n_answered: int
    complete: bool
    domain_scores: dict[str, DomainScore]
    tag_scores: list[TagScore]
