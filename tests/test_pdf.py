import io
from datetime import date

import pypdf
import pytest

from placement.i18n import t
from placement.pdf import card_to_pdf
from placement.report import build_card
from placement.scoring import ScoredResponse, score_responses

TURKISH = "ğşıİöüçĞŞÖÜÇ"


def make_card(bank, lang, wrong_every=3, flags=()):
    items = list(bank.items)[:28]
    responses = [ScoredResponse(i.difficulty_b, n % wrong_every != 0, domain=i.domain, tag=i.skill_tested)
                 for n, i in enumerate(items)]
    answers = [(i, i.correct_answer if n % wrong_every else i.distractors[0]) for n, i in enumerate(items)]
    return build_card(score_responses(responses, complete=True), answers, lang=lang, test_length=28, flags=flags,
                      passage_titles={p.id: p.title for p in bank.passages})


def text_of(data: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() for page in reader.pages)


def test_turkish_pdf_embeds_a_unicode_font_and_keeps_every_letter(real_bank):
    card = make_card(real_bank, "tr", flags=["repeat"])
    data = card_to_pdf(card, issued=date(2026, 11, 1))
    assert data.startswith(b"%PDF")
    assert b"DejaVu" in data  # the TTF is embedded
    text = text_of(data)
    for letter in "ğşıİöüç":
        assert letter in text
    for needle in ("Sonuç kartı", card.level, "2026-11-01", t("disclaimer_title", "tr"), t("review_title", "tr")):
        assert needle in text
    assert t("repeat_notice", "tr")[:20] in text.replace("\n", " ")


def test_pdf_handles_the_full_turkish_alphabet():
    from placement.report import ResultCard

    card = ResultCard(lang="tr", level="B1", headline=f"B1 · {TURKISH}", scaled_score="50", can_do=(TURKISH,),
                      confidence=[TURKISH], subskills=[], subskill_note="", strengths=[], focus=[], tags_note="",
                      action_plan=[TURKISH], missed=[], notices=[], disclaimer=TURKISH)
    text = text_of(card_to_pdf(card))
    assert TURKISH in text.replace("\n", "")
    assert t("tags_none", "tr") in text and t("review_none", "tr") in text


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_pdf_in_both_languages(real_bank, lang):
    card = make_card(real_bank, lang, wrong_every=2)
    text = text_of(card_to_pdf(card))
    assert t("card_title", lang) in text
    assert t("plan_title", lang) in text
    assert len(pypdf.PdfReader(io.BytesIO(card_to_pdf(card))).pages) >= 2
