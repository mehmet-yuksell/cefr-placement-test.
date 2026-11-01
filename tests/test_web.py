import html
import re
from dataclasses import replace

from placement import engine, web
from placement.models import UNSURE
from placement.report import build_card
from placement.scoring import score_responses


def test_landing_fragments_render_both_languages():
    for lang in ("tr", "en"):
        page = "".join(
            [web.topbar(lang), web.hero(lang), web.stats(lang, 28), web.how_it_works(lang), web.features(lang),
             web.cefr_ladder(lang, highlight="B1"), web.section_title("x"), web.footer(lang), web.note("n")]
        )
        assert "pt-hero" in page and "28" in page and page.count("pt-rung") == 6
        assert 'class="pt-rung on"' in page
    assert "<style>" in web.CSS and ".st-key-options" in web.CSS


def test_stem_formatting_escapes_and_marks_segments():
    html = web.format_stem("A <b>[is]</b> ___ & more")
    assert "&lt;b&gt;" in html and "&amp;" in html
    assert '<span class="pt-seg-mark">is</span>' in html
    assert '<span class="pt-gap"></span>' in html


def test_question_screen_fragments(real_bank):
    reading = real_bank.get("B1-RDG-001")
    block = web.question_block(reading, real_bank.passage(reading.passage_id))
    assert "pt-passage" in block and "A new way to work" in block
    header = web.test_header("en", position=12, total=28, stage=2, stage_sizes=(10, 10, 8), item=reading)
    assert "13 <small>/ 28</small>" in header and "Adapt" in header and "Reading" in header
    assert 'style="width:100.0%"' in header and 'style="width:20.0%"' in header
    assert "setInterval" in web.timer_widget(1000, "Time")


def test_result_fragments(real_bank):
    state = engine.new_test(real_bank, seed=1)
    answers = []
    while (item := engine.current_item(state, real_bank)) is not None:
        chosen = item.correct_answer if item.difficulty_b < 0 else UNSURE
        engine.record_answer(state, real_bank, item.id, item.is_correct(chosen))
        answers.append((item, chosen))
    result = score_responses(engine.scored_responses(state, real_bank), complete=True)
    for lang in ("tr", "en"):
        card = build_card(result, answers, lang=lang, test_length=28, flags=["repeat"])
        page = "".join(
            [web.result_hero(card, result, lang, n_correct=10, elapsed_s=725), web.scale_panel(result, lang),
             web.probability_panel(result, card, lang), web.can_do_panel(card, lang),
             web.subskills_panel(result, card, lang), web.tags_panel(card, lang), web.plan_panel(card, lang),
             web.review_items(card, lang)]
        )
        assert result.level in page and "pt-ring" in page and len(re.findall(r'class="pt-prob( top)?"', page)) == 6
        assert "pt-notice" in page  # repeat flag
        unsure = "Emin değilim" if lang == "tr" else "I'm not sure"
        assert html.escape(unsure) in page
    assert "12 min 5 s" in web.result_hero(card, result, "en", n_correct=1, elapsed_s=725)
    empty = build_card(result, [], lang="en", test_length=28)
    assert "did not miss" in web.review_items(empty, "en")
    assert "Not enough data" in web.tags_panel(replace(empty, strengths=[], focus=[]), "en")
