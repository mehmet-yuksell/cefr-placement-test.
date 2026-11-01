"""Visual layer for the web app: the stylesheet and HTML fragments.

Pure functions that return HTML strings (no Streamlit import), so the look of
every screen can be tested without a browser. Every dynamic value is escaped;
only constant strings from :mod:`placement.i18n` that deliberately contain
markup (the hero title) are inserted raw.
"""

from __future__ import annotations

import html
import re
from collections.abc import Sequence

from placement.config import CEFR_LEVELS, SCALED_THETA_RANGE
from placement.i18n import cefr_short, level_group, t
from placement.models import SEGMENT_RE, Item, Passage, Result
from placement.report import ResultCard
from placement.scoring import DOMAINS

BLANK_RE = re.compile(r"_{3,}")

LEVEL_COLORS = {
    "A1": "#0ea5e9",
    "A2": "#06b6d4",
    "B1": "#10b981",
    "B2": "#6366f1",
    "C1": "#8b5cf6",
    "C2": "#d946ef",
}

# Text glyphs, not SVG: st.html sanitises inline SVG away.
_ICONS = {"honest": "✓", "target": "◎", "plan": "☰", "retake": "↻", "resume": "⏵", "lock": "⚿"}


def _e(text: object) -> str:
    return html.escape(str(text), quote=True)


def _icon(name: str) -> str:
    return f'<span aria-hidden="true">{_ICONS[name]}</span>'


CSS = """
<style>
:root {
  --ink: #0f172a; --ink-2: #334155; --muted: #64748b; --line: #e6e8ef; --bg: #f6f7fb;
  --card: #ffffff; --brand: #4f46e5; --brand-2: #7c3aed; --brand-soft: #eef2ff;
  --ok: #059669; --ok-soft: #ecfdf5; --warn: #b45309; --warn-soft: #fffbeb;
  --radius: 20px; --shadow: 0 1px 2px rgba(15,23,42,.04), 0 10px 30px rgba(15,23,42,.06);
}
html, body, .stApp, .stApp button, .stApp input, .stApp textarea {
  font-family: "Inter", "Segoe UI Variable", "Segoe UI", system-ui, -apple-system, Roboto, sans-serif;
}
#MainMenu, header[data-testid="stHeader"], footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
.stApp {
  background:
    radial-gradient(1100px 520px at 0% -8%, #e9ecff 0%, rgba(233,236,255,0) 60%),
    radial-gradient(900px 480px at 100% -4%, #f3e8ff 0%, rgba(243,232,255,0) 55%),
    var(--bg);
  color: var(--ink);
}
[data-testid="stMainBlockContainer"], .block-container { max-width: 900px; padding: 1.1rem 1.25rem 4rem; }
.stApp [data-testid="stElementContainer"]:has(> .stHtml) { margin-bottom: 0; }
p, li { color: var(--ink-2); }

/* Cards made from keyed Streamlit containers */
.st-key-start_card, .st-key-qcard, .st-key-resume_card, .st-key-result_actions {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 26px 28px 22px;
}
.st-key-start_card { border-top: 4px solid var(--brand); }

/* Buttons */
.stApp .stButton > button, .stApp .stDownloadButton > button {
  border-radius: 12px; font-weight: 600; min-height: 46px; transition: transform .12s, box-shadow .12s, background .12s;
}
.stApp .stButton > button[kind="primary"], .stApp .stDownloadButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--brand), var(--brand-2)); border: 0; color: #fff;
  box-shadow: 0 8px 20px rgba(79,70,229,.28);
}
.stApp .stButton > button[kind="primary"]:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 12px 26px rgba(79,70,229,.34); }
.stApp .stButton > button[kind="primary"]:disabled { background: #c7cbe0; box-shadow: none; color: #fff; }
.stApp .stButton > button[kind="secondary"], .stApp .stDownloadButton > button[kind="secondary"] {
  background: #fff; border: 1px solid var(--line); color: var(--ink);
}
.stApp .stButton > button[kind="secondary"]:hover { border-color: #c7d2fe; color: var(--brand); }
.stApp .stButton > button[kind="tertiary"] { color: var(--muted); min-height: 40px; }
.stApp .stButton > button[kind="tertiary"]:hover { color: var(--ink); }

/* Inputs */
.stApp .stTextInput label p { font-weight: 600; color: var(--ink); }
.stApp [data-testid="stTextInputRootElement"] { border-radius: 12px; border: 1.5px solid var(--line); background: #fff; }
.stApp [data-testid="stTextInputRootElement"]:focus-within { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(79,70,229,.12); }
.stApp [data-testid="stTextInputRootElement"] input { font-size: 1rem; padding: .8rem .95rem; background: #fff; }
.stApp button p { color: inherit; }
.stApp .stButton > button[kind="primary"] p { font-size: 1rem; font-weight: 650; }

/* Radio groups (react-aria DOM: group > wrapper div > label[data-selected]) */
.st-key-lang [data-testid="stRadioGroup"] { gap: 0; background: #fff; border: 1px solid var(--line); border-radius: 999px;
  padding: 3px; width: max-content; margin-left: auto; }
.st-key-lang [data-testid="stRadioOption"] { margin: 0; padding: .3rem .85rem; border-radius: 999px; cursor: pointer; }
.st-key-lang [data-testid="stRadioOption"] > div > div:first-child { display: none; }
.st-key-lang [data-testid="stRadioOption"] p { font-size: .82rem; font-weight: 700; color: var(--muted); letter-spacing: .03em; }
.st-key-lang [data-testid="stRadioOption"][data-selected="true"] { background: var(--brand-soft); }
.st-key-lang [data-testid="stRadioOption"][data-selected="true"] p { color: var(--brand); }

.st-key-options [data-testid="stElementContainer"], .st-key-options [data-testid="stRadio"],
.st-key-options [data-testid="stRadioGroup"] > div, .st-key-options [data-testid="stRadioOption"] { width: 100% !important; max-width: 100%; }
.st-key-options [data-testid="stRadioGroup"] { display: flex; flex-direction: column; gap: .62rem; counter-reset: opt; width: 100%; }
.st-key-options [data-testid="stRadioGroup"] > div { counter-increment: opt; width: 100%; }
.st-key-options [data-testid="stRadioOption"] {
  position: relative; width: 100%; margin: 0; min-height: 58px; box-sizing: border-box;
  display: flex; align-items: center; padding: .85rem 1rem .85rem 3.55rem; cursor: pointer;
  background: #fff; border: 1.5px solid var(--line); border-radius: 14px;
  transition: border-color .12s, background .12s, box-shadow .12s;
}
.st-key-options [data-testid="stRadioOption"]::before {
  content: counter(opt, upper-alpha); position: absolute; left: .85rem; top: 50%; transform: translateY(-50%);
  width: 1.95rem; height: 1.95rem; border-radius: 10px; display: grid; place-items: center;
  background: #f1f5f9; color: var(--ink-2); font-weight: 700; font-size: .9rem;
}
.st-key-options [data-testid="stRadioOption"] > div > div:first-child { display: none; }
.st-key-options [data-testid="stRadioOption"] p { margin: 0; font-size: 1.04rem; color: var(--ink); line-height: 1.45; }
.st-key-options [data-testid="stRadioOption"]:hover { border-color: #c7d2fe; background: #fbfbff; }
.st-key-options [data-testid="stRadioOption"][data-selected="true"] {
  border-color: var(--brand); background: var(--brand-soft); box-shadow: 0 0 0 3px rgba(79,70,229,.12);
}
.st-key-options [data-testid="stRadioOption"][data-selected="true"]::before { background: var(--brand); color: #fff; }
.st-key-options [data-testid="stRadioGroup"] > div:last-child [data-testid="stRadioOption"] { border-style: dashed; background: #fcfcfd; }
.st-key-options [data-testid="stRadioGroup"] > div:last-child [data-testid="stRadioOption"] p { color: var(--muted); font-size: .98rem; }
.st-key-options [data-testid="stRadioGroup"] > div:last-child [data-testid="stRadioOption"]::before { content: "?"; }
.st-key-options [data-testid="stRadioGroup"] > div:last-child [data-testid="stRadioOption"][data-selected="true"] { border-style: solid; }

/* Expanders (FAQ, review) */
.stApp [data-testid="stExpander"] details { border: 1px solid var(--line); border-radius: 14px; background: #fff; }
.stApp [data-testid="stExpander"] summary p { font-weight: 600; color: var(--ink); }
.stApp [data-testid="stCode"] pre { border-radius: 12px; }

/* ---- HTML fragments ---- */
.pt-top { display: flex; align-items: center; gap: .6rem; padding: .25rem 0; }
.pt-logo { width: 36px; height: 36px; border-radius: 11px; display: grid; place-items: center; color: #fff;
  background: linear-gradient(135deg, var(--brand), var(--brand-2)); font-weight: 800; font-size: 1rem;
  box-shadow: 0 6px 14px rgba(79,70,229,.3); }
.pt-brand { font-weight: 800; font-size: 1.12rem; color: var(--ink); line-height: 1.1; }
.pt-brand small { display: block; font-weight: 500; font-size: .78rem; color: var(--muted); }

.pt-hero { text-align: center; padding: 2.2rem .5rem 1.4rem; }
.pt-badge { display: inline-flex; align-items: center; gap: .4rem; padding: .35rem .8rem; border-radius: 999px;
  background: #fff; border: 1px solid var(--line); color: var(--ink-2); font-size: .85rem; font-weight: 600; }
.pt-badge i { width: 8px; height: 8px; border-radius: 50%; background: var(--ok); display: inline-block; }
.pt-hero h1 { font-size: clamp(2rem, 5vw, 3.1rem); line-height: 1.08; letter-spacing: -.03em; margin: 1rem 0 .8rem;
  color: var(--ink); font-weight: 800; }
.pt-hero h1 em { font-style: normal; background: linear-gradient(135deg, var(--brand), var(--brand-2));
  -webkit-background-clip: text; background-clip: text; color: transparent; }
.pt-hero p { max-width: 640px; margin: 0 auto; font-size: 1.1rem; line-height: 1.6; color: var(--muted); }

.pt-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: .75rem; margin: 1.4rem 0 .4rem; }
.pt-stat { background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: 1rem; text-align: center; }
.pt-stat b { display: block; font-size: 1.35rem; color: var(--ink); letter-spacing: -.02em; }
.pt-stat span { font-size: .82rem; color: var(--muted); }

.pt-section { margin: 3rem 0 1rem; }
.pt-section h2 { font-size: 1.65rem; letter-spacing: -.02em; margin: 0 0 .3rem; color: var(--ink); font-weight: 800; }
.pt-section > p { margin: 0 0 1.2rem; color: var(--muted); }
.pt-grid { display: grid; gap: .85rem; }
.pt-grid.c4 { grid-template-columns: repeat(4, 1fr); }
.pt-grid.c3 { grid-template-columns: repeat(3, 1fr); }
.pt-tile { background: #fff; border: 1px solid var(--line); border-radius: 18px; padding: 1.15rem 1.15rem 1rem; }
.pt-tile h3 { font-size: 1.02rem; margin: .7rem 0 .35rem; color: var(--ink); font-weight: 700; }
.pt-tile p { margin: 0; font-size: .92rem; line-height: 1.5; color: var(--muted); }
.pt-num { width: 32px; height: 32px; border-radius: 10px; display: grid; place-items: center; font-weight: 800;
  background: var(--brand-soft); color: var(--brand); }
.pt-ico { width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center;
  background: var(--brand-soft); color: var(--brand); font-size: 1.25rem; font-weight: 700; }

.pt-ladder { display: grid; gap: .5rem; }
.pt-rung { display: grid; grid-template-columns: 56px 1fr; gap: .9rem; align-items: center; background: #fff;
  border: 1px solid var(--line); border-radius: 14px; padding: .7rem .9rem; }
.pt-rung.on { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(79,70,229,.1); }
.pt-chip { display: grid; place-items: center; height: 36px; border-radius: 10px; color: #fff; font-weight: 800; }
.pt-rung b { color: var(--ink); font-size: .92rem; }
.pt-rung span { display: block; color: var(--muted); font-size: .9rem; line-height: 1.4; }
.pt-footer { text-align: center; color: var(--muted); font-size: .85rem; margin-top: 3rem; padding-top: 1.2rem;
  border-top: 1px solid var(--line); }

/* Test screen */
.pt-qhead { display: flex; justify-content: space-between; align-items: center; gap: .8rem; flex-wrap: wrap; }
.pt-count { font-weight: 800; font-size: 1.05rem; color: var(--ink); }
.pt-count small { color: var(--muted); font-weight: 600; }
.pt-tags { display: flex; gap: .4rem; flex-wrap: wrap; }
.pt-tag { padding: .22rem .65rem; border-radius: 999px; font-size: .78rem; font-weight: 700; background: #f1f5f9; color: var(--ink-2); }
.pt-tag.brand { background: var(--brand-soft); color: var(--brand); }
.pt-progress { display: flex; gap: 4px; margin: .7rem 0 0; }
.pt-seg { height: 8px; border-radius: 999px; background: #e9ebf3; overflow: hidden; }
.pt-seg i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--brand), var(--brand-2));
  transition: width .35s ease; }
.pt-passage { background: #f8fafc; border: 1px solid var(--line); border-radius: 14px; padding: 1rem 1.15rem;
  max-height: 340px; overflow: auto; margin-bottom: 1rem; }
.pt-passage h4 { margin: 0 0 .5rem; font-size: .8rem; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
.pt-passage p { margin: 0 0 .55rem; font-size: 1.01rem; line-height: 1.7; color: var(--ink); }
.pt-instr { font-size: .8rem; text-transform: uppercase; letter-spacing: .06em; font-weight: 700; color: var(--brand); margin: .2rem 0 .45rem; }
.pt-question { font-size: 1.32rem; line-height: 1.5; font-weight: 650; color: var(--ink); margin: 0 0 1.1rem; letter-spacing: -.01em; }
.pt-seg-mark { text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 4px;
  text-decoration-color: var(--brand); background: var(--brand-soft); padding: 0 .2rem; border-radius: 4px; }
.pt-gap { display: inline-block; min-width: 4.5rem; border-bottom: 2.5px solid var(--brand); margin: 0 .2rem; transform: translateY(-.25rem); }
.pt-note { color: var(--muted); font-size: .84rem; margin-top: .4rem; }

/* Result screen */
.pt-result { background: linear-gradient(135deg, #312e81, #4f46e5 55%, #7c3aed); color: #fff; border-radius: 24px;
  padding: 1.8rem 1.8rem 1.5rem; box-shadow: 0 20px 50px rgba(49,46,129,.3); display: grid;
  grid-template-columns: auto 1fr; gap: 1.6rem; align-items: center; }
.pt-ring { width: 150px; height: 150px; border-radius: 50%; display: grid; place-items: center;
  background: conic-gradient(#fff var(--p), rgba(255,255,255,.18) 0); }
.pt-ring > div { width: 122px; height: 122px; border-radius: 50%; background: #3f3aa8; display: grid; place-items: center; text-align: center; }
.pt-ring b { font-size: 2.7rem; line-height: 1; letter-spacing: -.03em; }
.pt-ring span { font-size: .78rem; opacity: .85; }
.pt-result .eyebrow { font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; opacity: .8; font-weight: 700; }
.pt-result h2 { margin: .25rem 0 .5rem; font-size: 1.6rem; letter-spacing: -.02em; color: #fff; }
.pt-result p { color: rgba(255,255,255,.9); margin: 0 0 .8rem; line-height: 1.5; }
.pt-pills { display: flex; gap: .45rem; flex-wrap: wrap; }
.pt-pill { padding: .3rem .7rem; border-radius: 999px; background: rgba(255,255,255,.16); font-size: .82rem; font-weight: 600; }
.pt-panel { background: #fff; border: 1px solid var(--line); border-radius: 20px; padding: 1.25rem 1.35rem; margin-top: 1rem; box-shadow: var(--shadow); }
.pt-panel h3 { margin: 0 0 .9rem; font-size: 1.05rem; color: var(--ink); font-weight: 750; }
.pt-scale { position: relative; padding-top: 2.1rem; }
.pt-bands { display: grid; grid-template-columns: repeat(6, 1fr); gap: 3px; }
.pt-band { height: 14px; border-radius: 4px; opacity: .9; }
.pt-band-labels { display: grid; grid-template-columns: repeat(6, 1fr); font-size: .78rem; color: var(--muted); font-weight: 700; margin-top: .35rem; text-align: center; }
.pt-se { position: absolute; top: 2.1rem; height: 14px; background: rgba(15,23,42,.18); border-radius: 4px; }
.pt-marker { position: absolute; top: 0; transform: translateX(-50%); text-align: center; }
.pt-marker span { display: inline-block; background: var(--ink); color: #fff; font-size: .74rem; font-weight: 700; padding: .15rem .5rem; border-radius: 6px; }
.pt-marker i { display: block; width: 2px; height: 22px; background: var(--ink); margin: 2px auto 0; }
.pt-probs { display: grid; gap: .45rem; }
.pt-prob { display: grid; grid-template-columns: 34px 1fr 48px; gap: .7rem; align-items: center; font-size: .9rem; }
.pt-prob b { color: var(--ink); }
.pt-bar { height: 10px; border-radius: 999px; background: #eef0f6; overflow: hidden; }
.pt-bar i { display: block; height: 100%; border-radius: 999px; }
.pt-prob em { font-style: normal; text-align: right; color: var(--muted); font-weight: 600; }
.pt-prob.top b, .pt-prob.top em { color: var(--brand); }
.pt-conf { margin: .9rem 0 0; padding: 0; list-style: none; }
.pt-conf li { padding: .35rem 0 .35rem 1.2rem; position: relative; font-size: .92rem; }
.pt-conf li::before { content: ""; position: absolute; left: 0; top: .78rem; width: 7px; height: 7px; border-radius: 50%; background: var(--brand); }
.pt-subs { display: grid; grid-template-columns: repeat(3, 1fr); gap: .75rem; }
.pt-sub { border: 1px solid var(--line); border-radius: 16px; padding: .95rem; }
.pt-sub h4 { margin: 0 0 .5rem; font-size: .9rem; color: var(--muted); font-weight: 700; }
.pt-sub .lvl { font-size: 1.6rem; font-weight: 800; letter-spacing: -.02em; }
.pt-sub .na { font-size: 1rem; font-weight: 700; color: var(--muted); }
.pt-sub small { display: block; color: var(--muted); margin: .25rem 0 .55rem; }
.pt-twocol { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.pt-chiplist { display: flex; flex-wrap: wrap; gap: .45rem; }
.pt-chip2 { padding: .4rem .75rem; border-radius: 10px; font-size: .88rem; font-weight: 600; }
.pt-chip2.good { background: var(--ok-soft); color: var(--ok); }
.pt-chip2.work { background: var(--warn-soft); color: var(--warn); }
.pt-muted { color: var(--muted); font-size: .88rem; }
.pt-steps { counter-reset: step; display: grid; gap: .6rem; margin: 0; padding: 0; list-style: none; }
.pt-steps li { counter-increment: step; position: relative; padding: .85rem 1rem .85rem 3.2rem; border: 1px solid var(--line);
  border-radius: 14px; font-size: .95rem; line-height: 1.5; color: var(--ink-2); }
.pt-steps li::before { content: counter(step); position: absolute; left: .85rem; top: .8rem; width: 1.7rem; height: 1.7rem;
  border-radius: 8px; background: var(--brand-soft); color: var(--brand); display: grid; place-items: center; font-weight: 800; font-size: .85rem; }
.pt-cando { margin: 0; padding-left: 1.1rem; }
.pt-cando li { margin: .3rem 0; }
.pt-notice { background: var(--warn-soft); color: var(--warn); border-radius: 14px; padding: .8rem 1rem; margin-top: 1rem; font-size: .9rem; }
.pt-review { border-left: 3px solid var(--line); padding: .2rem 0 .2rem .9rem; margin: .8rem 0; }
.pt-review b { color: var(--ink); }
.pt-review .you { color: #b91c1c; }
.pt-review .key { color: var(--ok); }

@media (max-width: 720px) {
  .pt-stats, .pt-grid.c4 { grid-template-columns: repeat(2, 1fr); }
  .pt-grid.c3, .pt-subs, .pt-twocol { grid-template-columns: 1fr; }
  .pt-result { grid-template-columns: 1fr; justify-items: center; text-align: center; }
  .pt-pills { justify-content: center; }
  .pt-question { font-size: 1.15rem; }
  .st-key-start_card, .st-key-qcard, .st-key-resume_card { padding: 20px 18px 16px; }
}
</style>
"""


# ---- Landing page --------------------------------------------------------------------


def topbar(lang: str) -> str:
    """Logo and product name."""
    return (
        '<div class="pt-top"><div class="pt-logo">S</div>'
        f'<div class="pt-brand">{_e(t("brand", lang))}<small>{_e(t("brand_tag", lang))}</small></div></div>'
    )


def hero(lang: str) -> str:
    """Headline block of the landing page."""
    return (
        '<div class="pt-hero">'
        f'<span class="pt-badge"><i></i>{_e(t("hero_badge", lang))}</span>'
        f'<h1>{t("hero_title", lang)}</h1>'
        f'<p>{_e(t("hero_sub", lang))}</p></div>'
    )


def stats(lang: str, length: int) -> str:
    """Four key facts about the test."""
    cells = [
        (t("stat_questions", lang, n=length), t("stat_questions_label", lang)),
        (t("stat_minutes", lang), t("stat_minutes_label", lang)),
        (t("stat_levels", lang), t("stat_levels_label", lang)),
        (t("stat_skills", lang), t("stat_skills_label", lang)),
    ]
    inner = "".join(f'<div class="pt-stat"><b>{_e(v)}</b><span>{_e(k)}</span></div>' for v, k in cells)
    return f'<div class="pt-stats">{inner}</div>'


def how_it_works(lang: str) -> str:
    """The four steps of the test."""
    tiles = "".join(
        f'<div class="pt-tile"><div class="pt-num">{n}</div><h3>{_e(t(f"step{n}_title", lang))}</h3>'
        f'<p>{_e(t(f"step{n}_text", lang))}</p></div>'
        for n in range(1, 5)
    )
    return (
        f'<div class="pt-section"><h2>{_e(t("how_title", lang))}</h2><p>{_e(t("how_sub", lang))}</p>'
        f'<div class="pt-grid c4">{tiles}</div></div>'
    )


def features(lang: str) -> str:
    """Six reasons to use this test."""
    icons = ["honest", "target", "plan", "retake", "resume", "lock"]
    tiles = "".join(
        f'<div class="pt-tile"><div class="pt-ico">{_icon(icon)}</div><h3>{_e(t(f"feat{n}_title", lang))}</h3>'
        f'<p>{_e(t(f"feat{n}_text", lang))}</p></div>'
        for n, icon in enumerate(icons, start=1)
    )
    return f'<div class="pt-section"><h2>{_e(t("features_title", lang))}</h2><div class="pt-grid c3">{tiles}</div></div>'


def cefr_ladder(lang: str, highlight: str | None = None) -> str:
    """The six CEFR levels with one-line descriptions (optionally one highlighted)."""
    rungs = "".join(
        f'<div class="pt-rung{" on" if level == highlight else ""}">'
        f'<div class="pt-chip" style="background:{LEVEL_COLORS[level]}">{level}</div>'
        f"<div><b>{_e(level_group(level, lang))}</b><span>{_e(cefr_short(level, lang))}</span></div></div>"
        for level in CEFR_LEVELS
    )
    return (
        f'<div class="pt-section"><h2>{_e(t("cefr_title", lang))}</h2><p>{_e(t("cefr_sub", lang))}</p>'
        f'<div class="pt-ladder">{rungs}</div></div>'
    )


def section_title(title: str) -> str:
    """A section heading without body (used above Streamlit widgets)."""
    return f'<div class="pt-section" style="margin-bottom:.2rem"><h2>{_e(title)}</h2></div>'


def footer(lang: str) -> str:
    """Page footer with the short disclaimer."""
    return f'<div class="pt-footer">{_e(t("footer", lang))}</div>'


# ---- Test screen -----------------------------------------------------------------------


def test_header(lang: str, *, position: int, total: int, stage: int, stage_sizes: Sequence[int], item: Item) -> str:
    """Question counter, stage/type tags and a progress bar split into stages."""
    segments = []
    start = 0
    for size in stage_sizes:
        done = min(max(position - start, 0), size)
        segments.append(
            f'<div class="pt-seg" style="flex:{size}"><i style="width:{100 * done / size:.1f}%"></i></div>'
        )
        start += size
    return (
        '<div class="pt-qhead">'
        f'<div class="pt-count">{position + 1} <small>/ {total}</small></div>'
        '<div class="pt-tags">'
        f'<span class="pt-tag brand">{_e(t(f"stage_{stage}", lang))}</span>'
        f'<span class="pt-tag">{_e(t(f"type_{item.type}", lang))}</span>'
        "</div></div>"
        f'<div class="pt-progress">{"".join(segments)}</div>'
    )


def format_stem(text: str) -> str:
    """Escape a stem and mark up [segments] and ___ gaps."""
    safe = html.escape(text, quote=False)
    safe = SEGMENT_RE.sub(lambda m: f'<span class="pt-seg-mark">{m.group(1)}</span>', safe)
    return BLANK_RE.sub('<span class="pt-gap"></span>', safe)


def question_block(item: Item, passage: Passage | None) -> str:
    """Passage (if any), instruction and the question stem."""
    parts = []
    if passage is not None:
        paragraphs = "".join(f"<p>{_e(line)}</p>" for line in passage.text.split("\n") if line.strip())
        parts.append(f'<div class="pt-passage"><h4>{_e(passage.title)}</h4>{paragraphs}</div>')
    if item.instruction:
        parts.append(f'<div class="pt-instr">{_e(item.instruction)}</div>')
    parts.append(f'<div class="pt-question">{format_stem(item.question)}</div>')
    return "".join(parts)


def note(text: str) -> str:
    """Small muted helper text."""
    return f'<div class="pt-note">{_e(text)}</div>'


def timer_widget(started_epoch_ms: int, label: str) -> str:
    """Self-contained live clock (rendered in its own small iframe)."""
    return f"""
<div style="font-family:Inter,'Segoe UI',system-ui,sans-serif;display:flex;justify-content:flex-end;align-items:center;
gap:.4rem;color:#64748b;font-size:14px;font-weight:600;height:28px">
<span>{_e(label)}</span><span id="t" style="font-variant-numeric:tabular-nums;color:#0f172a;background:#fff;
border:1px solid #e6e8ef;border-radius:999px;padding:2px 10px">00:00</span></div>
<script>
const start = {int(started_epoch_ms)};
const el = document.getElementById("t");
function tick() {{
  const s = Math.max(0, Math.floor((Date.now() - start) / 1000));
  el.textContent = String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
}}
tick(); setInterval(tick, 1000);
</script>"""


# ---- Result screen ---------------------------------------------------------------------


def _theta_to_percent(theta: float) -> float:
    low, high = SCALED_THETA_RANGE
    return 100 * (max(low, min(high, theta)) - low) / (high - low)


def result_hero(card: ResultCard, result: Result, lang: str, *, n_correct: int, elapsed_s: int) -> str:
    """Gradient headline card with the level ring."""
    minutes, seconds = divmod(max(0, elapsed_s), 60)
    pills = [
        card.scaled_score,
        t("result_correct", lang, c=n_correct, n=result.n_answered),
        t("result_time", lang, minutes=minutes, seconds=seconds),
    ]
    return (
        f'<div class="pt-result"><div class="pt-ring" style="--p:{result.scaled_score}%"><div>'
        f"<div><b>{_e(result.level)}</b><br><span>{result.scaled_score}/100</span></div></div></div>"
        f'<div><div class="eyebrow">{_e(t("result_eyebrow", lang))}</div>'
        f"<h2>{_e(level_group(result.level, lang))}</h2>"
        f"<p>{_e(card.confidence[0])}</p>"
        f'<div class="pt-pills">{"".join(f"<span class=pt-pill>{_e(p)}</span>" for p in pills)}</div>'
        "</div></div>"
    )


def scale_panel(result: Result, lang: str) -> str:
    """CEFR scale with the estimate and its ±1 SE band."""
    bands = "".join(f'<div class="pt-band" style="background:{LEVEL_COLORS[lvl]}"></div>' for lvl in CEFR_LEVELS)
    labels = "".join(f"<span>{lvl}</span>" for lvl in CEFR_LEVELS)
    pos = min(97.0, max(3.0, _theta_to_percent(result.theta)))
    lo, hi = _theta_to_percent(result.theta - result.se), _theta_to_percent(result.theta + result.se)
    return (
        f'<div class="pt-panel"><h3>{_e(t("scale_title", lang))}</h3><div class="pt-scale">'
        f'<div class="pt-marker" style="left:{pos:.1f}%"><span>{_e(t("you_are_here", lang))}</span><i></i></div>'
        f'<div class="pt-bands">{bands}</div>'
        f'<div class="pt-se" style="left:{lo:.1f}%;width:{hi - lo:.1f}%"></div>'
        f'<div class="pt-band-labels">{labels}</div></div></div>'
    )


def probability_panel(result: Result, card: ResultCard, lang: str) -> str:
    """Bar per level plus the confidence notes."""
    rows = []
    for level in CEFR_LEVELS:
        p = result.level_probabilities[level]
        top = " top" if level == result.level else ""
        pct = f"%{p * 100:.0f}" if lang == "tr" else f"{p * 100:.0f}%"
        rows.append(
            f'<div class="pt-prob{top}"><b>{level}</b><div class="pt-bar"><i style="width:{p * 100:.1f}%;'
            f'background:{LEVEL_COLORS[level]}"></i></div><em>{pct}</em></div>'
        )
    # confidence[0] is the headline sentence and [1] the probability list; both are shown elsewhere.
    notes = "".join(f"<li>{_e(line)}</li>" for line in card.confidence[2:])
    return (
        f'<div class="pt-panel"><h3>{_e(t("prob_title", lang))}</h3><div class="pt-probs">{"".join(rows)}</div>'
        f'<ul class="pt-conf">{notes}</ul></div>'
    )


def can_do_panel(card: ResultCard, lang: str) -> str:
    """What people at this level can typically do."""
    items = "".join(f"<li>{_e(line)}</li>" for line in card.can_do)
    return f'<div class="pt-panel"><h3>{_e(t("can_do_title", lang))}</h3><ul class="pt-cando">{items}</ul></div>'


def subskills_panel(result: Result, card: ResultCard, lang: str) -> str:
    """Three sub-skill tiles (band or 'not enough data')."""
    tiles = []
    for domain in DOMAINS:
        score = result.domain_scores[domain]
        if score.suppressed:
            value = f'<div class="na">{_e(t("subskill_hidden", lang))}</div>'
        else:
            value = f'<div class="lvl" style="color:{LEVEL_COLORS[score.level]}">{_e(score.level)}</div>'
        bar_color = LEVEL_COLORS[score.level] if score.level else "#cbd5e1"
        tiles.append(
            f'<div class="pt-sub"><h4>{_e(t(f"domain_{domain}", lang))}</h4>{value}'
            f'<small>{_e(t("subskill_items", lang, n=score.n_items, pct=score.percent_correct))}</small>'
            f'<div class="pt-bar"><i style="width:{score.percent_correct:.0f}%;background:{bar_color}"></i></div></div>'
        )
    return (
        f'<div class="pt-panel"><h3>{_e(t("subskills_title", lang))}</h3><div class="pt-subs">{"".join(tiles)}</div>'
        f'<p class="pt-muted" style="margin:.8rem 0 0">{_e(card.subskill_note)}</p></div>'
    )


def tags_panel(card: ResultCard, lang: str) -> str:
    """Strengths and focus areas as chips."""

    def chips(lines: list[str], kind: str) -> str:
        if not lines:
            return f'<span class="pt-muted">{_e(t("tags_none", lang))}</span>'
        return "".join(f'<span class="pt-chip2 {kind}">{_e(line)}</span>' for line in lines)

    return (
        '<div class="pt-panel"><div class="pt-twocol">'
        f'<div><h3>{_e(t("strengths_title", lang))}</h3><div class="pt-chiplist">{chips(card.strengths, "good")}</div></div>'
        f'<div><h3>{_e(t("focus_title", lang))}</h3><div class="pt-chiplist">{chips(card.focus, "work")}</div></div>'
        f'</div><p class="pt-muted" style="margin:.9rem 0 0">{_e(card.tags_note)}</p></div>'
    )


def plan_panel(card: ResultCard, lang: str) -> str:
    """Numbered action plan."""
    steps = "".join(f"<li>{_e(step)}</li>" for step in card.action_plan)
    notices = "".join(f'<div class="pt-notice">{_e(n)}</div>' for n in card.notices)
    return f'<div class="pt-panel"><h3>{_e(t("plan_title", lang))}</h3><ol class="pt-steps">{steps}</ol>{notices}</div>'


def review_items(card: ResultCard, lang: str) -> str:
    """Missed items with the chosen and correct answers and the explanation."""
    if not card.missed:
        return f'<p class="pt-muted">{_e(t("review_none", lang))}</p>'
    blocks = [f'<p class="pt-muted">{_e(t("review_note", lang))}</p>']
    for m in card.missed:
        context = f" · {_e(m.passage_title)}" if m.passage_title else ""
        blocks.append(
            f'<div class="pt-review"><b>{_e(m.item_id)}</b><span class="pt-muted">{context}</span>'
            f"<div>{format_stem(m.question)}</div>"
            f'<div class="you">{_e(t("review_your_answer", lang))}: {_e(m.chosen)}</div>'
            f'<div class="key">{_e(t("review_correct", lang))}: {_e(m.correct)}</div>'
            f'<div class="pt-muted">{_e(m.explanation)}</div></div>'
        )
    return "".join(blocks)
