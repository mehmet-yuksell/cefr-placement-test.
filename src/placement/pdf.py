"""Result card as a PDF (pure Python, via fpdf2).

The DejaVu Sans fonts in ``placement/fonts`` are embedded, so Turkish
characters (ğ ş ı İ ö ü ç) and the typographic quotes used in the item bank
render correctly. The PDF shows the same content as the Markdown download.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

from placement.i18n import t
from placement.report import ResultCard

FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT = "DejaVu"
BRAND = (79, 70, 229)
INK = (15, 23, 42)
MUTED = (100, 116, 139)
WARN = (180, 83, 9)


class _CardPDF(FPDF):
    def __init__(self, footer_text: str) -> None:
        super().__init__(format="A4")
        self._footer_text = footer_text
        self.add_font(FONT, "", str(FONT_DIR / "DejaVuSans.ttf"))
        self.add_font(FONT, "B", str(FONT_DIR / "DejaVuSans-Bold.ttf"))
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(auto=True, margin=18)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(FONT, "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"{self._footer_text}  ·  {self.page_no()}", align="C")


def _heading(pdf: FPDF, text: str) -> None:
    if pdf.get_y() > pdf.h - 45:  # keep a heading together with its first lines
        pdf.add_page()
    pdf.ln(3)
    pdf.set_font(FONT, "B", 12)
    pdf.set_text_color(*BRAND)
    pdf.multi_cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)


def _paragraph(pdf: FPDF, text: str, size: float = 10, color: tuple[int, int, int] = INK) -> None:
    pdf.set_font(FONT, "", size)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, 5.4, text, align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)


def _bullets(pdf: FPDF, lines: list[str] | tuple[str, ...], numbered: bool = False) -> None:
    pdf.set_font(FONT, "", 10)
    for n, line in enumerate(lines, start=1):
        marker = f"{n}." if numbered else "•"
        pdf.cell(7, 5.4, marker)
        pdf.multi_cell(0, 5.4, line, align="L", new_x="LMARGIN", new_y="NEXT")


def card_to_pdf(card: ResultCard, *, issued: date | None = None) -> bytes:
    """Render the result card as PDF bytes."""
    lang = card.lang
    pdf = _CardPDF(t("footer", lang))
    pdf.add_page()

    pdf.set_font(FONT, "B", 9)
    pdf.set_text_color(*MUTED)
    stamp = (issued or date.today()).isoformat()
    pdf.cell(0, 5, f"{t('brand', lang)} · {t('brand_tag', lang)} · {stamp}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font(FONT, "B", 20)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 10, t("card_title", lang), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 15)
    pdf.set_text_color(*BRAND)
    pdf.multi_cell(0, 8, card.headline, new_x="LMARGIN", new_y="NEXT")
    _paragraph(pdf, card.scaled_score, size=11)

    _heading(pdf, t("confidence_title", lang))
    _bullets(pdf, card.confidence)
    _heading(pdf, t("can_do_title", lang))
    _bullets(pdf, card.can_do)
    _heading(pdf, t("subskills_title", lang))
    _bullets(pdf, card.subskills)
    _paragraph(pdf, card.subskill_note, size=8.5, color=MUTED)
    for title, lines in (("strengths_title", card.strengths), ("focus_title", card.focus)):
        _heading(pdf, t(title, lang))
        if lines:
            _bullets(pdf, lines)
        else:
            _paragraph(pdf, t("tags_none", lang), color=MUTED)
    _paragraph(pdf, card.tags_note, size=8.5, color=MUTED)
    _heading(pdf, t("plan_title", lang))
    _bullets(pdf, card.action_plan, numbered=True)
    for notice in card.notices:
        pdf.ln(1)
        _paragraph(pdf, notice, color=WARN)

    _heading(pdf, t("review_title", lang))
    if card.missed:
        _paragraph(pdf, t("review_note", lang), size=8.5, color=MUTED)
        for m in card.missed:
            context = f" ({m.passage_title})" if m.passage_title else ""
            pdf.ln(1)
            pdf.set_font(FONT, "B", 10)
            pdf.multi_cell(0, 5.4, f"{m.item_id}{context}: {m.question}", new_x="LMARGIN", new_y="NEXT")
            _paragraph(pdf, f"{t('review_your_answer', lang)}: {m.chosen}")
            _paragraph(pdf, f"{t('review_correct', lang)}: {m.correct}")
            _paragraph(pdf, m.explanation, size=9, color=MUTED)
    else:
        _paragraph(pdf, t("review_none", lang))

    _heading(pdf, t("disclaimer_title", lang))
    _paragraph(pdf, card.disclaimer, size=9)
    return bytes(pdf.output())
