"""Lint the item bank and print a composition summary.

Usage:
    python tools/validate_bank.py [--bank-dir DIR] [--show ITEM_ID ...]

Exits with status 1 if any rule is broken, 0 otherwise. ``--show`` prints
the named items in full (with passage, key, rationales and notes) for review.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from placement.bank import (
    DEFAULT_BANK_DIR,
    TYPE_CODES,
    ItemBank,
    build_bank,
    key_length_profile,
    read_raw_bank,
    validate_raw,
)
from placement.config import CEFR_LEVELS


def format_item(bank: ItemBank, item_id: str) -> str:
    """Return a full, human-readable rendering of one item for review."""
    item = bank.get(item_id)
    header = (
        f"=== {item.id} · {item.cefr_level} · {item.type} · {item.skill_tested} "
        f"· domain={item.domain} · b={item.difficulty_b:+.1f} ==="
    )
    lines = [header]
    if item.passage_id:
        passage = bank.passage(item.passage_id)
        lines.append(f'Passage {passage.id} "{passage.title}" ({passage.word_count} words):')
        lines.extend(f"    {line}" for line in passage.text.splitlines())
    if item.instruction:
        lines.append(f"Instruction: {item.instruction}")
    lines.append(f"Question: {item.question}")
    for option in item.options:
        if option == item.correct_answer:
            lines.append(f"  [KEY] {option}")
        else:
            lines.append(f"  [ x ] {option}  -> {item.distractor_rationale[option]}")
    lines.append(f"Explanation: {item.explanation}")
    if item.author_notes:
        lines.append(f"Notes: {item.author_notes}")
    return "\n".join(lines)


def summary(bank: ItemBank) -> str:
    """Return a table of item counts per level and type, plus bank totals."""
    types = list(TYPE_CODES)
    counts = Counter((i.cefr_level, i.type) for i in bank.items)
    header = "level  " + "  ".join(f"{t[:9]:>9}" for t in types) + "  total"
    rows = [header]
    for level in CEFR_LEVELS:
        cells = [counts[(level, t)] for t in types]
        rows.append(f"{level:<5}  " + "  ".join(f"{c:>9}" for c in cells) + f"  {sum(cells):>5}")
    domains = Counter(i.domain for i in bank.items)
    records = [{"correct_answer": i.correct_answer, "options": i.options} for i in bank.items]
    longest, shortest = key_length_profile(records)
    rows.append(f"total  {len(bank)} items, {len(bank.passages)} passages")
    rows.append("domains: " + ", ".join(f"{d}={n}" for d, n in sorted(domains.items())))
    rows.append(f"key is strictly longest option in {longest:.0%} of items, shortest in {shortest:.0%}")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    """Run the validator; return the process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bank-dir", type=Path, default=DEFAULT_BANK_DIR)
    parser.add_argument("--show", nargs="+", metavar="ITEM_ID", default=[])
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    raw, issues = read_raw_bank(args.bank_dir)
    issues += validate_raw(raw)
    if issues:
        print(f"FAIL: {len(issues)} problem(s) in {args.bank_dir}")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    bank = build_bank(raw)
    print(summary(bank))
    for item_id in args.show:
        print()
        print(format_item(bank, item_id))
    print("\nOK: item bank passed all checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
