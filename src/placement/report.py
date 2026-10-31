"""Result card: turns a scored session into the text the user sees.

The card is plain data (:class:`ResultCard`) so the Streamlit app, the
Markdown download and the scripted run-through all show the same content.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from placement.config import CEFR_LEVELS, SUBSCORE_MIN_ITEMS
from placement.i18n import can_do, level_group, t, tag_advice, tag_name
from placement.models import Item, Result
from placement.scoring import DOMAINS, strengths_and_focus

MIN_PROBABILITY_SHOWN = 0.05
PLAN_TAGS = 3


@dataclass(frozen=True)
class MissedItem:
    """One wrongly answered item, for the optional review section."""

    item_id: str
    passage_title: str | None
    question: str
    chosen: str
    correct: str
    explanation: str


@dataclass(frozen=True)
class ResultCard:
    """Every section of the result card, already localised."""

    lang: str
    level: str
    headline: str
    scaled_score: str
    can_do: tuple[str, ...]
    confidence: list[str]
    subskills: list[str]
    subskill_note: str
    strengths: list[str]
    focus: list[str]
    tags_note: str
    action_plan: list[str]
    missed: list[MissedItem]
    notices: list[str]
    disclaimer: str


def _percent(value: float, lang: str) -> str:
    return f"%{value * 100:.0f}" if lang == "tr" else f"{value * 100:.0f}%"


def _confidence(result: Result, lang: str, test_length: int) -> list[str]:
    lines = []
    if result.borderline_with:
        low, high = sorted((result.level, result.borderline_with), key=CEFR_LEVELS.index)
        lines.append(t("confidence_borderline", lang, low=low, high=high))
    else:
        lines.append(t("confidence_clear", lang, level=result.level))
    shown = sorted(
        ((lvl, p) for lvl, p in result.level_probabilities.items() if p >= MIN_PROBABILITY_SHOWN),
        key=lambda kv: -kv[1],
    )
    lines.append(t("probabilities", lang, items=" · ".join(f"{lvl} {_percent(p, lang)}" for lvl, p in shown)))
    lines.append(t("se_note", lang, theta=result.theta, se=result.se))
    if not result.complete:
        lines.append(t("incomplete", lang, n=result.n_answered, total=test_length))
    return lines


def _subskills(result: Result, lang: str) -> list[str]:
    lines = []
    for domain in DOMAINS:
        score = result.domain_scores[domain]
        name = t(f"domain_{domain}", lang)
        if score.suppressed:
            lines.append(t("subskill_suppressed", lang, name=name, n=score.n_items, min=SUBSCORE_MIN_ITEMS))
        else:
            lines.append(
                t("subskill_row", lang, name=name, level=score.level, pct=score.percent_correct, n=score.n_items)
            )
    return lines


def _action_plan(result: Result, lang: str) -> list[str]:
    _, focus = strengths_and_focus(result.tag_scores)
    tags = [s.tag for s in focus]
    # Top up with the next-weakest tags so the plan always targets real data.
    for score in sorted(result.tag_scores, key=lambda s: (s.residual, s.tag)):
        if len(tags) >= PLAN_TAGS:
            break
        if score.tag not in tags:
            tags.append(score.tag)
    steps = [tag_advice(tag, lang) for tag in tags[:PLAN_TAGS]]
    if len(steps) < 2:
        steps.append(t("plan_vocab", lang))
    band = CEFR_LEVELS.index(result.level) // 2
    steps.append(t(("plan_read_basic", "plan_read_independent", "plan_read_proficient")[band], lang))
    steps.append(t("plan_time_top" if result.level == "C2" else "plan_time", lang))
    return steps


def build_card(
    result: Result,
    answers: Sequence[tuple[Item, str]],
    *,
    lang: str,
    test_length: int,
    flags: Iterable[str] = (),
    passage_titles: dict[str, str] | None = None,
) -> ResultCard:
    """Assemble the localised result card.

    Args:
        result: The scored session.
        answers: Each answered item with the option the user chose.
        lang: ``"tr"`` or ``"en"``.
        test_length: Planned number of items (for the "incomplete" note).
        flags: Engine relaxation flags; ``"repeat"`` adds a notice.
        passage_titles: Passage id -> title, for the missed-item review.
    """
    strengths, focus = strengths_and_focus(result.tag_scores)

    def tag_line(score) -> str:
        return t("tag_row", lang, tag=tag_name(score.tag, lang), n=score.n_items)

    titles = passage_titles or {}
    missed = [
        MissedItem(
            item_id=item.id,
            passage_title=titles.get(item.passage_id) if item.passage_id else None,
            question=item.question,
            chosen=chosen,
            correct=item.correct_answer,
            explanation=item.explanation,
        )
        for item, chosen in answers
        if not item.is_correct(chosen)
    ]
    return ResultCard(
        lang=lang,
        level=result.level,
        headline=t("headline", lang, level=result.level, group=level_group(result.level, lang)),
        scaled_score=t("scaled_score", lang, score=result.scaled_score),
        can_do=can_do(result.level, lang),
        confidence=_confidence(result, lang, test_length),
        subskills=_subskills(result, lang),
        subskill_note=t("subskill_note", lang),
        strengths=[tag_line(s) for s in strengths],
        focus=[tag_line(s) for s in focus],
        tags_note=t("tags_note", lang),
        action_plan=_action_plan(result, lang),
        missed=missed,
        notices=[t("repeat_notice", lang)] if "repeat" in set(flags) else [],
        disclaimer=t("disclaimer", lang),
    )


def to_markdown(card: ResultCard) -> str:
    """Render the card as Markdown (download and scripted run-through)."""
    lang = card.lang
    out = [f"# {t('card_title', lang)}", "", f"## {card.headline}", card.scaled_score, ""]
    out += [f"### {t('can_do_title', lang)}", *[f"- {line}" for line in card.can_do], ""]
    out += [f"### {t('confidence_title', lang)}", *[f"- {line}" for line in card.confidence], ""]
    out += [f"### {t('subskills_title', lang)}", *[f"- {line}" for line in card.subskills], "", card.subskill_note, ""]
    for title, lines in (("strengths_title", card.strengths), ("focus_title", card.focus)):
        out += [f"### {t(title, lang)}", *([f"- {line}" for line in lines] or [t("tags_none", lang)]), ""]
    out += [card.tags_note, ""]
    out += [f"### {t('plan_title', lang)}", *[f"{n}. {step}" for n, step in enumerate(card.action_plan, 1)], ""]
    out += [f"### {t('review_title', lang)}"]
    if card.missed:
        out.append(f"_{t('review_note', lang)}_")
        for m in card.missed:
            context = f" ({m.passage_title})" if m.passage_title else ""
            out += [
                f"- **{m.item_id}**{context}: {m.question}",
                f"  - {t('review_your_answer', lang)}: {m.chosen}",
                f"  - {t('review_correct', lang)}: {m.correct}",
                f"  - {m.explanation}",
            ]
    else:
        out.append(t("review_none", lang))
    out.append("")
    out += [f"> {notice}" for notice in card.notices]
    out += [f"### {t('disclaimer_title', lang)}", card.disclaimer, ""]
    return "\n".join(out)
