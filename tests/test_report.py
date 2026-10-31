import pytest

from placement import i18n
from placement.config import SKILL_TAGS
from placement.report import build_card, to_markdown
from placement.scoring import ScoredResponse, score_responses


def scored(bank, pattern):
    items = [i for i in bank.items][: len(pattern)]
    responses = [
        ScoredResponse(i.difficulty_b, ok, i.discrimination_a, i.guessing_c, i.domain, i.skill_tested)
        for i, ok in zip(items, pattern)
    ]
    answers = [(i, i.correct_answer if ok else i.distractors[0]) for i, ok in zip(items, pattern)]
    return responses, answers


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_card_has_every_section(real_bank, lang):
    responses, answers = scored(real_bank, [n % 3 != 0 for n in range(28)])
    result = score_responses(responses, complete=True)
    card = build_card(result, answers, lang=lang, test_length=28, flags=["repeat"],
                      passage_titles={p.id: p.title for p in real_bank.passages})
    assert card.level == result.level and result.level in card.headline
    assert 2 <= len(card.can_do) <= 3
    assert len(card.confidence) >= 3
    assert len(card.subskills) == 3
    assert 4 <= len(card.action_plan) <= 5
    assert len(card.missed) == sum(1 for n in range(28) if n % 3 == 0)
    assert card.notices  # repeat flag produces a notice
    md = to_markdown(card)
    for word in ("CEFR", card.headline, card.disclaimer):
        assert word in md
    assert "certified" not in md.lower() and "official certificate" not in md.lower().replace(
        "not an official certificate", ""
    )


def test_borderline_card_keeps_single_headline(real_bank):
    responses, answers = scored(real_bank, [True] * 14 + [False] * 14)
    result = score_responses(responses, complete=False)
    card = build_card(result, answers, lang="en", test_length=28)
    assert card.headline.startswith(result.level)
    if result.borderline_with:
        assert "boundary" in card.confidence[0]
    assert any("not completed" in line for line in card.confidence)


def test_suppressed_subskill_and_empty_tags(real_bank):
    grammar_only = [i for i in real_bank.items if i.domain == "grammar"][:12]
    responses = [ScoredResponse(i.difficulty_b, True, domain=i.domain, tag=i.skill_tested) for i in grammar_only]
    answers = [(i, i.correct_answer) for i in grammar_only]
    card = build_card(score_responses(responses, complete=True), answers, lang="en", test_length=28)
    assert any("not enough items" in line for line in card.subskills)
    assert not card.missed and not card.notices
    assert "You did not miss any questions." in to_markdown(card)


def test_top_level_plan_and_tag_fallback(real_bank):
    responses = [ScoredResponse(2.5, True)] * 28
    result = score_responses(responses, complete=True)
    card = build_card(result, [], lang="tr", test_length=28)
    assert card.level == "C2"
    assert "C2" in card.action_plan[-1]
    assert len(card.action_plan) >= 3
    assert i18n.t("tags_none", "tr") in to_markdown(card)


def test_i18n_tables_are_complete():
    assert set(i18n.STRINGS["tr"]) == set(i18n.STRINGS["en"])
    tags = [t for group in SKILL_TAGS.values() for t in group]
    for lang in i18n.LANGUAGES:
        for tag in tags:
            assert i18n.tag_advice(tag, lang)
            assert i18n.tag_name(tag, lang)
        for level in i18n.LEVEL_GROUPS["en"]:
            assert i18n.level_group(level, lang)
            assert 2 <= len(i18n.can_do(level, lang)) <= 3
    assert set(i18n.TAG_NAMES["tr"]) == set(tags)
    assert i18n.t("progress", "xx", n=1, total=2) == "Question 1 of 2"


def test_no_forbidden_claims_in_user_text():
    text = " ".join(" ".join(table.values()) for table in i18n.STRINGS.values()).lower()
    for phrase in ("internationally valid", "certified", "resmi olarak geçerli"):
        assert phrase not in text
