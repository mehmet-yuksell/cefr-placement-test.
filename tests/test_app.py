"""End-to-end tests of app.py through Streamlit's AppTest harness."""

import sqlite3
from contextlib import closing

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

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
    at.sidebar.radio(key="lang").set_value(lang).run()
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
    assert any("Sonuç kartı" in t.value for t in at.title)
    at.sidebar.radio(key="lang").set_value("en").run()
    assert any("Result card" in t.value for t in at.title)
    assert not at.exception
