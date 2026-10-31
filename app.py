"""Streamlit entry point: the test-taker UI.

Run with ``streamlit run app.py``. All test logic lives in ``placement``;
this file only renders screens and wires user actions to the engine,
scoring, report and storage modules.

Environment overrides (used by the automated run-through):
``PLACEMENT_DB`` (SQLite path), ``PLACEMENT_KEY`` (hash-key file) and
``PLACEMENT_SEED`` (fixed base seed; each attempt then uses base + attempt).
"""

from __future__ import annotations

import html
import os
import random
import re
import secrets
import time
import uuid
from pathlib import Path

import streamlit as st

from placement import engine, storage
from placement.bank import ItemBank, load_bank
from placement.config import MIN_ITEMS_FOR_RESULT, TEST_LENGTH
from placement.i18n import DEFAULT_LANGUAGE, LANGUAGES, t
from placement.models import SEGMENT_RE, Item, Response
from placement.report import ResultCard, build_card, to_markdown
from placement.scoring import InsufficientDataError, score_responses

BLANK_RE = re.compile(r"_{3,}")


@st.cache_resource
def get_bank() -> ItemBank:
    """The validated item bank (loaded once per server process)."""
    return load_bank()


@st.cache_resource(on_release=lambda conn: conn.close())
def get_conn():
    """Shared SQLite connection."""
    return storage.connect(Path(os.environ.get("PLACEMENT_DB", storage.DEFAULT_DB_PATH)))


@st.cache_resource
def get_key() -> bytes:
    """The installation's email-hashing key."""
    return storage.load_or_create_key(Path(os.environ.get("PLACEMENT_KEY", storage.DEFAULT_KEY_PATH)))


def render_question(text: str) -> str:
    """HTML-safe Markdown for a stem: [segments] underlined, gaps visible."""
    safe = html.escape(text, quote=False)
    safe = SEGMENT_RE.sub(lambda m: f"<u><b>{m.group(1)}</b></u>", safe)
    return BLANK_RE.sub(r"\\_\\_\\_\\_\\_\\_", safe)


def shuffled_options(item: Item, seed: int) -> list[str]:
    """Options in a per-session random order; the key's position is never stored."""
    options = list(item.options)
    random.Random(f"{seed}:{item.id}").shuffle(options)
    return options


def lang() -> str:
    return st.session_state.get("lang", DEFAULT_LANGUAGE)


def start_test(email: str, mode: str) -> None:
    """Create the session record and the engine state, then go to the test."""
    conn, bank = get_conn(), get_bank()
    user_hash = storage.hash_email(email, get_key())
    storage.mark_abandoned(conn, user_hash)
    attempt = storage.next_attempt_no(conn, user_hash)
    fixed_seed = os.environ.get("PLACEMENT_SEED")
    seed = int(fixed_seed) + attempt if fixed_seed else secrets.randbelow(2**31)
    session_id = uuid.uuid4().hex
    storage.create_session(
        conn, session_id=session_id, user_hash=user_hash, attempt_no=attempt, mode=mode, seed=seed,
        test_length=TEST_LENGTH,
    )
    st.session_state.update(
        phase="test",
        email_prefill=email,
        session_id=session_id,
        attempt=attempt,
        engine=engine.new_test(bank, seed=seed, mode=mode, seen=storage.seen_items(conn, user_hash)),
        answered=[],
        test_started=time.monotonic(),
        shown_item=None,
        result=None,
        answered_count=0,
    )


def finish_test(abandoned: bool) -> None:
    """Score the session (if there is enough data) and persist the outcome."""
    state: engine.TestState = st.session_state.engine
    bank = get_bank()
    try:
        result = score_responses(engine.scored_responses(state, bank), complete=not abandoned)
    except InsufficientDataError:
        result = None
    storage.finish_session(
        get_conn(),
        st.session_state.session_id,
        status="abandoned" if abandoned else "completed",
        result=result,
        flags=state.flags,
        engine_state=state.to_dict(),
    )
    st.session_state.update(phase="result", result=result, answered_count=len(state.answers))


def current_card() -> ResultCard | None:
    """Build the result card in the currently selected language."""
    result = st.session_state.get("result")
    if result is None:
        return None
    state: engine.TestState = st.session_state.engine
    bank = get_bank()
    answers = [(bank.get(item_id), chosen) for item_id, chosen in st.session_state.answered]
    titles = {p.id: p.title for p in bank.passages}
    return build_card(result, answers, lang=lang(), test_length=state.length, flags=state.flags, passage_titles=titles)


def submit_answer(item: Item, chosen: str) -> None:
    """Record the answer in the engine and the database."""
    state: engine.TestState = st.session_state.engine
    position = len(state.answers)
    elapsed = round(time.monotonic() - st.session_state.shown_at, 2)
    engine.record_answer(state, get_bank(), item.id, item.is_correct(chosen))
    storage.record_response(
        get_conn(),
        st.session_state.session_id,
        Response(item.id, chosen, item.is_correct(chosen), elapsed, engine.stage_of(state, position), position),
        item_version=item.version,
    )
    st.session_state.answered.append((item.id, chosen))
    if state.finished:
        finish_test(abandoned=False)


def screen_start() -> None:
    lg = lang()
    st.title(t("app_title", lg))
    st.caption(t("app_subtitle", lg, length=TEST_LENGTH))
    st.write(t("intro", lg))
    st.info(t("start_disclaimer", lg))
    email = st.text_input(t("email_label", lg), value=st.session_state.get("email_prefill", ""),
                          help=t("email_help", lg), key="email")
    with st.expander(t("advanced", lg)):
        mode = st.radio(
            t("mode_label", lg), ["adaptive", "fixed"], key="mode",
            format_func=lambda m: t(f"mode_{m}", lg),
        )
    if st.button(t("start_button", lg), type="primary", key="start"):
        try:
            storage.normalise_email(email)
        except ValueError:
            st.error(t("invalid_email", lg))
            return
        start_test(email, mode)
        st.rerun()


def screen_test() -> None:
    lg = lang()
    state: engine.TestState = st.session_state.engine
    bank = get_bank()
    item = engine.current_item(state, bank)
    if item is None:
        finish_test(abandoned=False)
        st.rerun()
        return
    if st.session_state.shown_item != item.id:
        st.session_state.shown_item = item.id
        st.session_state.shown_at = time.monotonic()

    n = len(state.answers) + 1
    st.progress(len(state.answers) / state.length, text=t("progress", lg, n=n, total=state.length))
    elapsed = int(time.monotonic() - st.session_state.test_started)
    st.caption(t("elapsed", lg, minutes=elapsed // 60, seconds=elapsed % 60))
    if st.session_state.attempt > 1 and n == 1:
        st.caption(t("attempt_info", lg, attempt=st.session_state.attempt))

    if item.passage_id:
        passage = bank.passage(item.passage_id)
        with st.container(border=True):
            st.markdown(f"**{t('passage_label', lg)}: {html.escape(passage.title)}**")
            for paragraph in passage.text.split("\n"):
                st.markdown(html.escape(paragraph, quote=False))
    if item.instruction:
        st.markdown(f"*{html.escape(item.instruction, quote=False)}*")
    st.markdown(f"#### {render_question(item.question)}", unsafe_allow_html=True)
    chosen = st.radio(
        t("choose_option", lg),
        shuffled_options(item, state.seed),
        index=None,
        key=f"answer_{st.session_state.session_id}_{item.id}",
        label_visibility="collapsed",
    )
    left, right = st.columns([1, 1])
    if left.button(t("next_button", lg), type="primary", disabled=chosen is None, key="next"):
        submit_answer(item, chosen)
        st.rerun()
    if right.button(t("quit_button", lg), key="quit", help=t("quit_help", lg, min=MIN_ITEMS_FOR_RESULT)):
        finish_test(abandoned=True)
        st.rerun()


def show_card(card: ResultCard) -> None:
    lg = card.lang
    st.title(t("card_title", lg))
    st.header(card.headline)
    st.subheader(card.scaled_score)
    for notice in card.notices:
        st.warning(notice)
    st.markdown(f"**{t('can_do_title', lg)}**")
    st.markdown("\n".join(f"- {line}" for line in card.can_do))
    st.markdown(f"**{t('confidence_title', lg)}**")
    st.markdown("\n".join(f"- {line}" for line in card.confidence))
    st.markdown(f"**{t('subskills_title', lg)}**")
    st.markdown("\n".join(f"- {line}" for line in card.subskills))
    st.caption(card.subskill_note)
    left, right = st.columns(2)
    for column, title, lines in ((left, "strengths_title", card.strengths), (right, "focus_title", card.focus)):
        column.markdown(f"**{t(title, lg)}**")
        column.markdown("\n".join(f"- {line}" for line in lines) if lines else t("tags_none", lg))
    st.caption(card.tags_note)
    st.markdown(f"**{t('plan_title', lg)}**")
    st.markdown("\n".join(f"{n}. {step}" for n, step in enumerate(card.action_plan, 1)))
    with st.expander(f"{t('review_title', lg)} ({len(card.missed)})"):
        if not card.missed:
            st.write(t("review_none", lg))
        else:
            st.caption(t("review_note", lg))
        for m in card.missed:
            context = f" — {html.escape(m.passage_title)}" if m.passage_title else ""
            st.markdown(f"**{m.item_id}**{context}: {render_question(m.question)}", unsafe_allow_html=True)
            st.markdown(
                f"- {t('review_your_answer', lg)}: {html.escape(m.chosen)}\n"
                f"- {t('review_correct', lg)}: {html.escape(m.correct)}\n"
                f"- {html.escape(m.explanation)}"
            )
    st.info(f"**{t('disclaimer_title', lg)}.** {card.disclaimer}")
    st.download_button(t("download_button", lg), to_markdown(card), file_name="result-card.md", key="download")


def screen_result() -> None:
    lg = lang()
    card = current_card()
    if card is None:
        st.title(t("card_title", lg))
        st.warning(t("no_result", lg, n=st.session_state.answered_count, min=MIN_ITEMS_FOR_RESULT))
    else:
        show_card(card)
    if st.button(t("retake_button", lg), key="retake"):
        st.session_state.phase = "start"
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="English Placement Test", page_icon="📝", layout="centered")
    st.sidebar.radio(
        t("language_label", lang()), list(LANGUAGES), key="lang", format_func=LANGUAGES.get
    )
    phase = st.session_state.setdefault("phase", "start")
    {"start": screen_start, "test": screen_test, "result": screen_result}[phase]()


main()
