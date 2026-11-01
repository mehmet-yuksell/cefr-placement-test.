"""Scripted run-through of the real Streamlit app with three personas.

Usage:
    python tools/run_personas.py [--lang en|tr] [--out FILE]

Each persona answers like a simulated learner with a fixed true ability
(A2-like theta = -1.5, B2-like 0.5, C1-like 1.5): an item is answered
correctly with the 3PL probability for that ability, using a fixed seed. The
app is driven through Streamlit's AppTest harness, so every screen, widget
and database write in ``app.py`` is exercised. The result cards are printed
(or written to a file). Data goes to a temporary database.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from streamlit.testing.v1 import AppTest

from placement.bank import load_bank
from placement.report import build_card, to_markdown
from placement.scoring import p_correct

ROOT = Path(__file__).resolve().parents[1]
PERSONAS = (("A2-like", -1.5), ("B2-like", 0.5), ("C1-like", 1.5))


@dataclass
class PersonaRun:
    """Outcome of one scripted session."""

    name: str
    theta: float
    level: str
    n_answered: int
    markdown: str


def run_persona(name: str, theta: float, lang: str, seed: int = 7, timeout: float = 30) -> PersonaRun:
    """Drive app.py through a full test for one persona and return its card."""
    bank = load_bank()
    rng = random.Random(f"{seed}:{name}")
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=timeout)
    at.run()
    at.radio(key="lang").set_value(lang).run()
    at.text_input(key="email").input(f"{name.lower()}@example.org")
    at.button(key="start").click().run()
    while at.session_state["phase"] == "test":
        item = bank.get(at.session_state["shown_item"])
        correct = rng.random() < p_correct(theta, item.difficulty_b, item.discrimination_a, item.guessing_c)
        choice = item.correct_answer if correct else rng.choice(list(item.distractors))
        radio = next(r for r in at.radio if r.key and r.key.endswith(item.id))
        radio.set_value(choice).run()
        at.button(key="next").click().run()
        if at.exception:
            raise RuntimeError(at.exception[0].message)

    result = at.session_state["result"]
    state = at.session_state["engine"]
    answers = [(bank.get(i), chosen) for i, chosen in at.session_state["answered"]]
    card = build_card(
        result, answers, lang=lang, test_length=state.length, flags=state.flags,
        passage_titles={p.id: p.title for p in bank.passages},
    )
    return PersonaRun(name, theta, result.level, result.n_answered, to_markdown(card))


def main(argv: list[str] | None = None) -> int:
    """Run all personas and print (or save) their result cards."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lang", choices=("en", "tr"), default="en")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--seed", type=int, default=42, help="base seed for the app and the personas")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    tmp = Path(tempfile.mkdtemp(prefix="placement-run-"))
    os.environ["PLACEMENT_DB"] = str(tmp / "run.db")
    os.environ["PLACEMENT_KEY"] = str(tmp / "run.key")
    os.environ["PLACEMENT_SEED"] = str(args.seed)

    chunks = []
    for name, theta in PERSONAS:
        run = run_persona(name, theta, args.lang, seed=args.seed)
        summary = f"{run.name}: true theta {run.theta:+.1f} -> headline {run.level} ({run.n_answered} answers)"
        print(summary)
        chunks.append(f"<!-- {summary} -->\n{run.markdown}")
    text = "\n\n---\n\n".join(chunks)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
