"""Streamlit entry point: the test-taker UI.

Run with ``streamlit run app.py``. All test logic lives in ``placement``;
this file only renders screens and wires user actions to the engine,
scoring, report and storage modules. The look comes from ``placement.web``.

Environment overrides (used by the automated run-through):
``PLACEMENT_DB`` (SQLite path), ``PLACEMENT_KEY`` (hash-key file) and
``PLACEMENT_SEED`` (fixed base seed; each attempt then uses base + attempt).
"""

from __future__ import annotations

import os
import random
import secrets
import time
import uuid
from pathlib import Path

import streamlit as st

from placement import engine, storage, web
from placement.bank import ItemBank, load_bank
from placement.config import MIN_ITEMS_FOR_RESULT, TEST_LENGTH
from placement.i18n import DEFAULT_LANGUAGE, LANGUAGES, faq, level_group, t
from placement.models import UNSURE, Item, Response
from placement.report import ResultCard, build_card, to_markdown
from placement.scoring import InsufficientDataError, score_responses


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


def lang() -> str:
    return st.session_state.get("lang", DEFAULT_LANGUAGE)


def now_ms() -> int:
    return int(time.time() * 1000)


def answer_options(item: Item, seed: int) -> list[str]:
    """Options in a per-session random order, then "I'm not sure".

    The key's position is never stored.
    """
    options = list(item.options)
    random.Random(f"{seed}:{item.id}").shuffle(options)
    return [*options, UNSURE]


# ---- Session control -------------------------------------------------------------------


def begin(state: engine.TestState, *, session_id: str, attempt: int, email: str,
          answered: list[tuple[str, str]], spent_s: float) -> None:
    """Put a (new or restored) test into the Streamlit session."""
    st.session_state.update(
        phase="test",
        email_prefill=email,
        session_id=session_id,
        attempt=attempt,
        engine=state,
        answered=answered,
        started_ms=now_ms() - int(spent_s * 1000),
        shown_item=None,
        result=None,
        answered_count=len(answered),
        pending_resume=None,
        view_pos=len(answered),
        confirm_for=None,
    )


def start_new_test(email: str, mode: str) -> None:
    """Create a session record and a fresh engine state."""
    conn = get_conn()
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
    state = engine.new_test(get_bank(), seed=seed, mode=mode, seen=storage.seen_items(conn, user_hash))
    begin(state, session_id=session_id, attempt=attempt, email=email, answered=[], spent_s=0.0)


def resume_test(email: str, mode: str) -> None:
    """Rebuild the user's unfinished session by replaying its stored answers."""
    conn, bank = get_conn(), get_bank()
    user_hash = storage.hash_email(email, get_key())
    row = storage.latest_in_progress(conn, user_hash)
    answered = storage.session_answers(conn, row["session_id"])
    known = {item.id for item in bank.items}
    state = None
    if all(item_id in known for item_id, _ in answered):
        state = engine.replay(
            bank,
            [(item_id, bank.get(item_id).is_correct(chosen)) for item_id, chosen in answered],
            seed=row["seed"],
            mode=row["mode"],
            length=row["test_length"],
            seen=storage.seen_items(conn, user_hash, before_attempt=row["attempt_no"]),
        )
    if state is None:
        start_new_test(email, mode)
        st.session_state.toast = "resume_failed"
        return
    begin(state, session_id=row["session_id"], attempt=row["attempt_no"], email=email, answered=answered,
          spent_s=storage.session_time_spent(conn, row["session_id"]))
    st.session_state.toast = "resumed_toast"


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
    st.session_state.update(
        phase="result",
        result=result,
        answered_count=len(state.answers),
        elapsed_s=(now_ms() - st.session_state.started_ms) // 1000,
    )


def submit_answer(item: Item, chosen: str) -> None:
    """Record the answer in the engine and the database."""
    state: engine.TestState = st.session_state.engine
    position = len(state.answers)
    elapsed = round(time.monotonic() - st.session_state.shown_at, 2)
    stage = engine.stage_of(state, position)
    engine.record_answer(state, get_bank(), item.id, item.is_correct(chosen))
    storage.record_response(
        get_conn(),
        st.session_state.session_id,
        Response(item.id, chosen, item.is_correct(chosen), elapsed, stage, position),
        item_version=item.version,
    )
    st.session_state.answered.append((item.id, chosen))
    st.session_state.view_pos = len(state.answers)
    st.session_state.confirm_for = None
    if state.finished:
        finish_test(abandoned=False)
    elif engine.stage_of(state, position + 1) != stage:
        first = engine.stage_start(state, position) + 1
        st.session_state.toast = (f"stage_toast_{stage + 1}", {"a": first, "b": position + 1})


def change_answer(position: int, item: Item, chosen: str) -> None:
    """Store a changed answer to an earlier question of the current part."""
    state: engine.TestState = st.session_state.engine
    correct = item.is_correct(chosen)
    engine.change_answer(state, get_bank(), position, correct)
    storage.update_response(
        get_conn(), st.session_state.session_id, position, chosen, correct,
        extra_time_s=round(time.monotonic() - st.session_state.shown_at, 2),
    )
    st.session_state.answered[position] = (item.id, chosen)


def go_to(position: int) -> None:
    """Show another question. Navigating never saves an unsaved selection."""
    st.session_state.view_pos = position
    st.session_state.confirm_for = None


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


# ---- Screens ---------------------------------------------------------------------------


def screen_start() -> None:
    lg = lang()
    st.html(web.hero(lg))
    with st.container(key="start_card"):
        email = st.text_input(
            t("email_label", lg), value=st.session_state.get("email_prefill", ""), key="email",
            placeholder="ornek@eposta.com" if lg == "tr" else "you@example.com", help=t("email_help", lg),
        )
        pending = st.session_state.get("pending_resume")
        if pending and pending["email"] == email:
            st.html(web.note(t("resume_found", lg, n=pending["answered"], total=pending["length"])))
            left, right = st.columns(2)
            if left.button(t("resume_button", lg), type="primary", key="resume", width="stretch"):
                resume_test(email, st.session_state.get("mode", "adaptive"))
                st.rerun()
            if right.button(t("fresh_button", lg), key="fresh", width="stretch"):
                start_new_test(email, st.session_state.get("mode", "adaptive"))
                st.rerun()
        elif st.button(t("start_button", lg) + "  →", type="primary", key="start", width="stretch"):
            try:
                storage.normalise_email(email)
            except ValueError:
                st.error(t("invalid_email", lg))
                return
            row = storage.latest_in_progress(get_conn(), storage.hash_email(email, get_key()))
            if row is not None:
                answered = len(storage.session_answers(get_conn(), row["session_id"]))
                st.session_state.pending_resume = {"email": email, "answered": answered, "length": row["test_length"]}
            else:
                start_new_test(email, st.session_state.get("mode", "adaptive"))
            st.rerun()
        st.html(web.note(t("cta_note", lg)))
    with st.expander(t("advanced", lg)):
        st.radio(t("mode_label", lg), ["adaptive", "fixed"], key="mode", format_func=lambda m: t(f"mode_{m}", lg))
    st.html(web.stats(lg, TEST_LENGTH))
    st.html(web.how_it_works(lg))
    st.html(web.features(lg))
    st.html(web.cefr_ladder(lg))
    st.html(web.section_title(t("faq_title", lg)))
    for question, answer in faq(lg):
        with st.expander(question):
            st.write(answer)
    st.html(web.footer(lg))


def screen_test() -> None:
    lg = lang()
    state: engine.TestState = st.session_state.engine
    bank = get_bank()
    frontier = len(state.answers)
    editable = engine.editable_range(state)
    view = st.session_state.get("view_pos", frontier)
    if view != frontier and view not in editable:
        view = frontier
    st.session_state.view_pos = view
    if view == frontier:
        item = engine.current_item(state, bank)
        if item is None:
            finish_test(abandoned=False)
            st.rerun()
            return
    else:
        item = bank.get(state.selected[view])
    if st.session_state.shown_item != item.id:
        st.session_state.shown_item = item.id
        st.session_state.shown_at = time.monotonic()

    key = f"answer_{st.session_state.session_id}_{item.id}"
    radio_kwargs: dict = {"index": None}
    if view < frontier:
        # Pre-select the stored answer through session state only (never together with ``index``).
        if key not in st.session_state:
            st.session_state[key] = st.session_state.answered[view][1]
        radio_kwargs = {}
    confirming = st.session_state.get("confirm_for") == item.id and view == frontier

    left, right = st.columns([1, 1], vertical_alignment="center")
    if left.button("← " + t("quit_button", lg), type="tertiary", key="quit",
                   help=t("quit_help", lg, min=MIN_ITEMS_FOR_RESULT)):
        pending = st.session_state.get(key)
        if confirming and pending is not None:
            submit_answer(item, pending)  # the user already confirmed a choice with «Next»
        if st.session_state.phase != "result":
            finish_test(abandoned=True)
        st.rerun()
    with right:
        st.iframe(web.timer_widget(st.session_state.started_ms, t("timer_label", lg)), height=34)

    with st.container(key="qcard"):
        st.html(web.test_header(lg, position=view, total=state.length, stage=engine.stage_of(state, view),
                                stage_sizes=state.stage_sizes, item=item))
        passage = bank.passage(item.passage_id) if item.passage_id else None
        st.html(web.question_block(item, passage))
        with st.container(key="options"):
            chosen = st.radio(
                t("choose_option", lg),
                answer_options(item, state.seed),
                key=key,
                label_visibility="collapsed",
                format_func=lambda o: t("unsure_label", lg) if o == UNSURE else o,
                **radio_kwargs,
            )
        st.html(web.note(t("unsure_note", lg)))
        if confirming:
            last = frontier + 1 == state.length
            text = t("confirm_test", lg) if last else t(
                "confirm_stage", lg, a=engine.stage_start(state, frontier) + 1, b=frontier + 1)
            st.html(web.confirm_box(text))
        with st.container(key="navbtns"):
            back_col, next_col = st.columns(2)
        if confirming:
            if back_col.button(t("review_button", lg), key="review", width="stretch"):
                st.session_state.confirm_for = None
                st.rerun()
            label = t("finish_test_button" if frontier + 1 == state.length else "finish_stage_button", lg)
        else:
            if back_col.button("← " + t("back_button", lg), key="back", width="stretch",
                               disabled=(view - 1) not in editable):
                go_to(view - 1)
                st.rerun()
            label = t("next_button", lg) + "  →"
        if next_col.button(label, type="primary", disabled=chosen is None, key="next", width="stretch"):
            if view < frontier:
                if chosen != st.session_state.answered[view][1]:
                    change_answer(view, item, chosen)
                go_to(view + 1)
            elif (frontier + 1) in state.stage_ends and not confirming:
                st.session_state.confirm_for = item.id
            else:
                submit_answer(item, chosen)
            st.rerun()
        st.html(web.note(t("no_back_note", lg)))

        states = web.navigator_states(state.length, frontier, editable, view)
        st.html(web.navigator_css(states))
        st.html(f'<div class="pt-navtitle">{t("nav_label", lg)}</div>')
        with st.container(horizontal=True, key="navigator"):
            for i, box in enumerate(states):
                if st.button(str(i + 1), key=f"nav_{i}", disabled=box not in web.NAV_CLICKABLE,
                             help=t(f"nav_{box}", lg, n=i + 1)) and i != view:
                    go_to(i)
                    st.rerun()
        st.html(web.nav_legend(lg))


def screen_result() -> None:
    lg = lang()
    card = current_card()
    result = st.session_state.get("result")
    if card is None or result is None:
        with st.container(key="resume_card"):
            st.html(f"<h3>{t('card_title', lg)}</h3>")
            st.warning(t("no_result", lg, n=st.session_state.answered_count, min=MIN_ITEMS_FOR_RESULT))
            if st.button(t("retake_button", lg), type="primary", key="retake"):
                st.session_state.phase = "start"
                st.rerun()
        return

    bank = get_bank()
    n_correct = sum(1 for item_id, chosen in st.session_state.answered if bank.get(item_id).is_correct(chosen))
    st.html(web.result_hero(card, result, lg, n_correct=n_correct, elapsed_s=st.session_state.get("elapsed_s", 0)))
    st.html(web.scale_panel(result, lg))
    st.html(web.probability_panel(result, card, lg))
    st.html(web.can_do_panel(card, lg))
    st.html(web.subskills_panel(result, card, lg))
    st.html(web.tags_panel(card, lg))
    st.html(web.plan_panel(card, lg))
    with st.expander(f"{t('review_title', lg)} ({len(card.missed)})"):
        st.html(web.review_items(card, lg))
    st.html(web.section_title(t("copy_title", lg)))
    st.code(
        t("copy_text", lg, level=result.level, group=level_group(result.level, lg), score=result.scaled_score),
        language=None, wrap_lines=True,
    )
    with st.container(key="result_actions"):
        left, right = st.columns(2)
        if left.button(t("retake_button", lg), type="primary", key="retake", width="stretch"):
            st.session_state.phase = "start"
            st.rerun()
        right.download_button(t("download_button", lg), to_markdown(card), file_name="result-card.md",
                              key="download", width="stretch")
    st.info(f"**{t('disclaimer_title', lg)}.** {card.disclaimer}")
    st.html(web.footer(lg))


def main() -> None:
    st.set_page_config(page_title=t("app_title", lang()), page_icon="🎯", layout="centered")
    st.html(web.CSS)
    brand, switch = st.columns([3, 1], vertical_alignment="center")
    brand.html(web.topbar(lang()))
    with switch:
        st.radio("lang", list(LANGUAGES), key="lang", horizontal=True, label_visibility="collapsed",
                 format_func=lambda code: code.upper())
    toast = st.session_state.pop("toast", None)
    if toast:
        key, values = toast if isinstance(toast, tuple) else (toast, {})
        st.toast(t(key, lang(), **values))
    phase = st.session_state.setdefault("phase", "start")
    {"start": screen_start, "test": screen_test, "result": screen_result}[phase]()


main()
