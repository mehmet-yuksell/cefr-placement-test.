"""End-to-end tests of app.py through Streamlit's AppTest harness."""

import sqlite3
from contextlib import closing

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from placement.models import UNSURE
from tools import run_personas

APP = str(run_personas.ROOT / "app.py")


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("PLACEMENT_DB", str(tmp_path / "app.db"))
    monkeypatch.setenv("PLACEMENT_KEY", str(tmp_path / "app.key"))
    monkeypatch.setenv("PLACEMENT_SEED", "5")
    st.cache_resource.clear()
    yield tmp_path
    st.cache_resource.clear()


def start(email="tester@example.org", lang="en"):
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    at.radio(key="lang").set_value(lang).run()
    at.text_input(key="email").input(email)
    at.button(key="start").click().run()
    return at


def answer_current(at, correct=True):
    from placement.bank import load_bank

    item = load_bank().get(at.session_state["shown_item"])
    radio = next(r for r in at.radio if r.key and r.key.endswith(item.id))
    radio.set_value(item.correct_answer if correct else item.distractors[0]).run()
    at.button(key="next").click().run()


def test_invalid_email_is_rejected():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    at.text_input(key="email").input("nope")
    at.button(key="start").click().run()
    assert at.session_state["phase"] == "start"
    assert at.error


def test_full_test_shows_result_card_and_persists(isolated_storage):
    run = run_personas.run_persona("B2-like", 0.5, "en", seed=5)
    assert run.n_answered == 28
    assert "Result card" in run.markdown and "Please note" in run.markdown
    conn = sqlite3.connect(isolated_storage / "app.db")
    status, n = conn.execute(
        "SELECT status, (SELECT COUNT(*) FROM responses) FROM sessions"
    ).fetchone()
    assert (status, n) == ("completed", 28)
    times = [row[0] for row in conn.execute("SELECT response_time_s FROM responses")]
    assert all(t >= 0 for t in times)
    dump = "\n".join(conn.iterdump())
    assert "b2-like@example.org" not in dump


def test_quitting_early_gives_no_result_then_retake_uses_new_items(isolated_storage):
    at = start()
    first = []
    for _ in range(3):
        first.append(at.session_state["shown_item"])
        answer_current(at)
    at.button(key="quit").click().run()
    assert at.session_state["phase"] == "result"
    assert at.session_state["result"] is None
    assert at.warning  # "at least 10 answers are needed"
    at.button(key="retake").click().run()
    assert at.session_state["phase"] == "start"
    at.button(key="start").click().run()
    assert at.session_state["attempt"] == 2
    assert at.session_state["shown_item"] not in first
    with closing(sqlite3.connect(isolated_storage / "app.db")) as conn:
        statuses = sorted(r[0] for r in conn.execute("SELECT status FROM sessions"))
    assert statuses == ["abandoned", "in_progress"]


def test_partial_result_after_ten_answers_and_language_switch():
    at = start(lang="tr")
    for _ in range(10):
        answer_current(at, correct=False)
    at.button(key="quit").click().run()
    result = at.session_state["result"]
    assert result is not None and not result.complete
    assert "İngilizce seviye testi sonucum" in at.code[0].value
    at.radio(key="lang").set_value("en").run()
    assert "My English level test result" in at.code[0].value
    assert not at.exception


def test_unsure_is_stored_and_scored_wrong(isolated_storage):
    at = start()
    item_id = at.session_state["shown_item"]
    radio = next(r for r in at.radio if r.key and r.key.endswith(item_id))
    radio.set_value(UNSURE).run()
    at.button(key="next").click().run()
    assert at.session_state["engine"].answers == [False]
    with closing(sqlite3.connect(isolated_storage / "app.db")) as conn:
        assert conn.execute("SELECT chosen_option, is_correct FROM responses").fetchone() == (UNSURE, 0)


def test_unfinished_test_resumes_after_reload():
    first = start(email="resume@example.org")
    for _ in range(3):
        answer_current(first)
    expected_next = first.session_state["shown_item"]

    reloaded = AppTest.from_file(APP, default_timeout=30)  # same browser after a reload
    reloaded.query_params["resume"] = first.query_params["resume"]
    reloaded.run()
    reloaded.text_input(key="email").input("resume@example.org")
    reloaded.button(key="start").click().run()
    assert reloaded.session_state["pending_resume"]["answered"] == 3
    reloaded.button(key="resume").click().run()
    assert reloaded.session_state["phase"] == "test"
    assert len(reloaded.session_state["answered"]) == 3
    assert reloaded.session_state["shown_item"] == expected_next
    assert reloaded.session_state["attempt"] == 1


def test_fresh_start_abandons_the_unfinished_test(isolated_storage):
    first = start(email="fresh@example.org")
    answer_current(first)
    again = AppTest.from_file(APP, default_timeout=30)
    again.run()
    again.text_input(key="email").input("fresh@example.org")
    again.button(key="start").click().run()
    again.button(key="fresh").click().run()
    assert again.session_state["attempt"] == 2
    with closing(sqlite3.connect(isolated_storage / "app.db")) as conn:
        statuses = sorted(r[0] for r in conn.execute("SELECT status FROM sessions"))
    assert statuses == ["abandoned", "in_progress"]


def test_same_email_second_full_attempt_gets_new_questions(isolated_storage):
    """Ali finishes a test, comes back with the same email: no question repeats."""
    from placement.bank import load_bank

    bank = load_bank()
    attempts = []
    for _ in range(2):
        at = AppTest.from_file(APP, default_timeout=30)
        at.run()
        at.text_input(key="email").input("Ali@Example.com ")  # case and spaces are normalised
        at.button(key="start").click().run()
        shown = []
        while at.session_state["phase"] == "test":
            item = bank.get(at.session_state["shown_item"])
            shown.append(item.id)
            answer_current(at, correct=item.cefr_level in ("A1", "A2"))
        assert at.session_state["result"] is not None
        attempts.append(set(shown))
    assert len(attempts[0]) == len(attempts[1]) == 28
    assert not attempts[0] & attempts[1]


# ---- Going back within a part ----------------------------------------------------------


def current_item_of(at):
    from placement.bank import load_bank

    return load_bank().get(at.session_state["shown_item"])


def answer_radio(at, item, correct=True):
    radio = next(r for r in at.radio if r.key and r.key.endswith(item.id))
    radio.set_value(item.correct_answer if correct else item.distractors[0]).run()
    return radio


def answer_confirmed(at, correct=True):
    """Answer the question on screen; confirm when it ends a part."""
    item = current_item_of(at)
    answer_radio(at, item, correct)
    at.button(key="next").click().run()
    if at.session_state["confirm_for"] == item.id:
        at.button(key="next").click().run()


def test_back_and_change_updates_state_and_database(isolated_storage):
    at = start()
    first = current_item_of(at)
    answer_confirmed(at, correct=True)
    answer_confirmed(at, correct=True)
    third = at.session_state["shown_item"]
    at.button(key="back").click().run()
    at.button(key="back").click().run()
    assert at.session_state["view_pos"] == 0 and at.session_state["shown_item"] == first.id
    radio = next(r for r in at.radio if r.key and r.key.endswith(first.id))
    assert radio.value == first.correct_answer  # the stored answer is pre-selected
    radio.set_value(first.distractors[0]).run()
    at.button(key="next").click().run()
    assert at.session_state["engine"].answers[0] is False
    assert at.session_state["answered"][0] == (first.id, first.distractors[0])
    assert at.session_state["view_pos"] == 1
    with closing(sqlite3.connect(isolated_storage / "app.db")) as conn:
        row = conn.execute("SELECT chosen_option, is_correct, changes FROM responses WHERE position = 0").fetchone()
        exposure = conn.execute("SELECT count FROM item_exposure WHERE item_id = ?", (first.id,)).fetchone()[0]
    assert row == (first.distractors[0], 0, 1)
    assert exposure == 1
    at.button(key="nav_2").click().run()
    assert at.session_state["shown_item"] == third
    assert not at.exception


def test_unsaved_selection_is_lost_when_navigating_away():
    at = start()
    answer_confirmed(at)
    answer_confirmed(at)
    frontier_item = current_item_of(at)
    answer_radio(at, frontier_item)  # chosen but not saved with «Next»
    at.button(key="back").click().run()
    at.button(key="nav_2").click().run()
    radio = next(r for r in at.radio if r.key and r.key.endswith(frontier_item.id))
    assert radio.value is None
    assert len(at.session_state["engine"].answers) == 2


def test_future_questions_are_not_clickable():
    at = start()
    assert not at.button(key="nav_0").disabled
    assert all(at.button(key=f"nav_{i}").disabled for i in range(1, 28))
    assert at.button(key="back").disabled


def test_part_end_asks_for_confirmation_and_review_keeps_it_open():
    at = start()
    for _ in range(9):
        answer_confirmed(at)
    tenth = current_item_of(at)
    answer_radio(at, tenth)
    at.button(key="next").click().run()
    assert at.session_state["confirm_for"] == tenth.id
    assert len(at.session_state["engine"].answers) == 9
    at.button(key="review").click().run()
    assert at.session_state["confirm_for"] is None
    assert not at.button(key="back").disabled  # the part is still open
    at.button(key="back").click().run()
    assert at.session_state["view_pos"] == 8
    at.button(key="nav_9").click().run()
    answer_radio(at, tenth)
    at.button(key="next").click().run()
    at.button(key="next").click().run()  # «Finish this part»
    state = at.session_state["engine"]
    assert len(state.answers) == 10
    from placement import engine

    assert engine.editable_range(state) == range(10, 10)
    assert all(at.button(key=f"nav_{i}").disabled for i in range(10))
    assert at.button(key="back").disabled
    with pytest.raises(ValueError):
        engine.change_answer(state, _bank(), 0, True)


def _bank():
    from placement.bank import load_bank

    return load_bank()


def test_last_question_asks_to_finish_the_test():
    at = start()
    for _ in range(27):
        answer_confirmed(at)
    last = current_item_of(at)
    answer_radio(at, last)
    at.button(key="next").click().run()
    assert at.session_state["phase"] == "test" and at.session_state["confirm_for"] == last.id
    at.button(key="next").click().run()
    assert at.session_state["phase"] == "result"


def test_changed_answers_survive_reload_and_resume():
    first = start(email="change@example.org")
    for _ in range(4):
        answer_confirmed(first)
    first.button(key="back").click().run()
    first.button(key="back").click().run()
    item = current_item_of(first)
    answer_radio(first, item, correct=False)
    first.button(key="next").click().run()
    expected_answers = list(first.session_state["engine"].answers)
    expected_selected = list(first.session_state["engine"].selected)
    first.button(key="nav_4").click().run()
    expected_next = first.session_state["shown_item"]

    reloaded = AppTest.from_file(APP, default_timeout=30)  # same browser after a reload
    reloaded.query_params["resume"] = first.query_params["resume"]
    reloaded.run()
    reloaded.text_input(key="email").input("change@example.org")
    reloaded.button(key="start").click().run()
    reloaded.button(key="resume").click().run()
    state = reloaded.session_state["engine"]
    assert state.answers == expected_answers
    assert state.selected[: len(expected_answers)] == expected_selected[: len(expected_answers)]
    assert reloaded.session_state["shown_item"] == expected_next


def test_result_uses_the_changed_answers():
    from placement.report import build_card

    at = start()
    for _ in range(9):
        answer_confirmed(at)
    at.button(key="nav_0").click().run()
    first = current_item_of(at)
    answer_radio(at, first, correct=False)
    at.button(key="next").click().run()
    at.button(key="nav_9").click().run()
    answer_radio(at, current_item_of(at))
    at.button(key="next").click().run()  # asks for confirmation
    at.button(key="quit").click().run()  # quitting keeps the confirmed choice
    result = at.session_state["result"]
    assert result is not None and result.n_answered == 10
    answers = [(_bank().get(i), c) for i, c in at.session_state["answered"]]
    card = build_card(result, answers, lang="en", test_length=28)
    assert [m.item_id for m in card.missed] == [first.id]
    assert sum(at.session_state["engine"].answers) == 9


def test_resume_ignores_item_version_changes(isolated_storage):
    """Replay works by item id, so a later item revision does not break resuming."""
    first = start(email="version@example.org")
    for _ in range(3):
        answer_confirmed(first)
    expected = first.session_state["shown_item"]
    with closing(sqlite3.connect(isolated_storage / "app.db")) as conn:
        conn.execute("UPDATE responses SET item_version = 0")
        conn.commit()
    again = AppTest.from_file(APP, default_timeout=30)  # same browser after a reload
    again.query_params["resume"] = first.query_params["resume"]
    again.run()
    again.text_input(key="email").input("version@example.org")
    again.button(key="start").click().run()
    again.button(key="resume").click().run()
    assert again.session_state["shown_item"] == expected
    assert len(again.session_state["engine"].answers) == 3



def test_unsure_note_is_shown_in_both_languages():
    for lang, text in (("tr", "«Emin değilim» yanlış sayılır"), ("en", "“I'm not sure” counts as wrong")):
        at = start(email=f"note-{lang}@example.org", lang=lang)
        bodies = [h.proto.body for h in at.get("html")]
        assert any(text in body or text.replace("'", "&#x27;") in body for body in bodies)


def test_other_browser_cannot_resume_someone_elses_test():
    """Knowing the email is not enough: the resume token lives only in the starting browser."""
    victim = start(email="owner@example.org")
    for _ in range(3):
        answer_confirmed(victim)
    other = AppTest.from_file(APP, default_timeout=30)  # different browser, no token in the URL
    other.run()
    other.text_input(key="email").input("owner@example.org")
    other.button(key="start").click().run()
    assert other.session_state["pending_resume"]["can_resume"] is False
    assert not [b for b in other.button if b.key == "resume"]
    other.button(key="fresh").click().run()
    assert other.session_state["attempt"] == 2  # a new test, not the owner's answers
    assert other.session_state["answered"] == []
    stranger = AppTest.from_file(APP, default_timeout=30)  # a forged token does not help either
    stranger.query_params["resume"] = "forged-token"
    stranger.run()
    stranger.text_input(key="email").input("owner@example.org")
    stranger.button(key="start").click().run()
    assert stranger.session_state["pending_resume"]["can_resume"] is False


# ---- Admin screen and hidden fixed form ------------------------------------------------


def admin_app(monkeypatch, password="s3cret!"):
    if password is None:
        monkeypatch.delenv("PLACEMENT_ADMIN_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("PLACEMENT_ADMIN_PASSWORD", password)
    at = AppTest.from_file(APP, default_timeout=30)
    at.query_params["admin"] = "1"
    at.run()
    return at


def test_admin_screen_is_closed_without_a_password(monkeypatch):
    at = admin_app(monkeypatch, password=None)
    assert not [w for w in at.text_input if w.key == "admin_password"]
    assert at.text_input(key="email")  # the normal start page instead


def test_admin_screen_requires_the_right_password(monkeypatch):
    finished = start(email="admin.check@example.org")
    for _ in range(10):
        answer_confirmed(finished)
    finished.button(key="quit").click().run()

    at = admin_app(monkeypatch)
    at.text_input(key="admin_password").input("wrong").run()
    at.button(key="admin_login").click().run()
    assert at.error and not at.dataframe
    at.text_input(key="admin_password").input("s3cret!").run()
    at.button(key="admin_login").click().run()
    sessions, exposure = at.dataframe
    shown = sessions.value.to_string() + exposure.value.to_string()
    assert "@" not in shown and "admin.check" not in shown
    assert len(sessions.value) == 1 and sessions.value.iloc[0, 0].endswith("…")
    assert len(exposure.value) == 144


def test_admin_exports_contain_no_email(isolated_storage):
    from placement import admin, storage

    at = start(email="csv.user@example.org")
    answer_confirmed(at)
    conn = storage.connect(isolated_storage / "app.db")
    sessions_csv = admin.to_csv(storage.all_sessions(conn), admin.SESSION_COLUMNS)
    responses_csv = admin.to_csv(storage.all_responses(conn), admin.RESPONSE_COLUMNS)
    conn.close()
    assert sessions_csv.splitlines()[0].startswith("session_id,user_hash")
    assert len(sessions_csv.splitlines()) == 2 and len(responses_csv.splitlines()) == 2
    assert "csv.user" not in sessions_csv + responses_csv and "@" not in sessions_csv + responses_csv


def test_fixed_form_is_hidden_unless_allowed(monkeypatch):
    monkeypatch.delenv("PLACEMENT_ALLOW_FIXED", raising=False)
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not [r for r in at.radio if r.key == "mode"]
    monkeypatch.setenv("PLACEMENT_ALLOW_FIXED", "1")
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    at.radio(key="mode").set_value("fixed").run()
    at.text_input(key="email").input("fixed@example.org")
    at.button(key="start").click().run()
    assert at.session_state["engine"].mode == "fixed"
