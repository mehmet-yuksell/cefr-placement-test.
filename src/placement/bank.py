"""Load, validate and query the item bank.

The bank lives in ``data/item_bank``: one JSON list of items per CEFR level
(``a1.json`` ... ``c2.json``) plus ``passages.json``. Validation is a pure
function over the raw records and returns a list of :class:`Issue`, so the
CLI, the tests and the app all apply exactly the same rules.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from placement.config import ANCHOR_B, CEFR_LEVELS, MAX_B_ADJUSTMENT, SKILL_TAGS
from placement.models import SEGMENT_RE, Item, Passage, count_words

DEFAULT_BANK_DIR = Path(__file__).resolve().parents[2] / "data" / "item_bank"
PASSAGES_FILE = "passages.json"

TYPE_CODES = {"cloze": "CLZ", "error_id": "ERR", "reading": "RDG", "lexical_pragmatic": "LEX"}
TYPE_DOMAINS = {
    "cloze": {"grammar", "vocabulary"},
    "error_id": {"grammar"},
    "reading": {"reading"},
    "lexical_pragmatic": {"vocabulary"},
}
STATUSES = {"provisional", "calibrated", "retired"}

MAX_EXPLANATION_WORDS = 60
PASSAGE_WORD_RANGE = (40, 140)
PASSAGE_ITEM_RANGE = (2, 3)
# Short distractors (up to this many words) must be named in the explanation.
NAMED_DISTRACTOR_MAX_WORDS = 4
# Bank-wide: the key may be the strictly longest (or shortest) option in at
# most this share of items, checked once the bank has enough items.
KEY_EXTREME_MAX_SHARE = 0.40
KEY_EXTREME_MIN_ITEMS = 10

_NUMBER = (int, float)
ITEM_FIELDS: dict[str, tuple[type, ...]] = {
    "id": (str,),
    "cefr_level": (str,),
    "type": (str,),
    "question": (str,),
    "options": (list,),
    "correct_answer": (str,),
    "skill_tested": (str,),
    "explanation": (str,),
    "domain": (str,),
    "passage_id": (str, type(None)),
    "difficulty_b": _NUMBER,
    "discrimination_a": _NUMBER,
    "guessing_c": _NUMBER,
    "distractor_rationale": (dict,),
    "status": (str,),
    "author_notes": (str,),
    "version": (int,),
}
OPTIONAL_ITEM_FIELDS: dict[str, tuple[type, ...]] = {"instruction": (str,), "legacy_id": (int,)}
PASSAGE_FIELDS: dict[str, tuple[type, ...]] = {
    "id": (str,),
    "cefr_level": (str,),
    "title": (str,),
    "text": (str,),
    "status": (str,),
    "version": (int,),
}

ITEM_ID_RE = re.compile(r"^(A1|A2|B1|B2|C1|C2)-(CLZ|ERR|RDG|LEX)-(\d{3})$")
PASSAGE_ID_RE = re.compile(r"^P-(A1|A2|B1|B2|C1|C2)-(\d{2})$")
BLANK_RE = re.compile(r"_{3,}")
FORBIDDEN_PATTERNS = (
    re.compile(r"\b(all|none) of (the above|these)\b", re.IGNORECASE),
    re.compile(r"\b(both|either|neither)\s+[A-D]\s+(and|or|nor)\s+[A-D]\b", re.IGNORECASE),
)
# Lower-case negation in an instruction (or a reading question) counts as a
# negative stem; an essential negation must be capitalised (NOT, EXCEPT).
NEGATIVE_STEM_RE = re.compile(r"\b(not|except|least|never)\b|n't\b")
# Spellings that mark British or American English; rephrase to stay neutral.
VARIETY_SPELLING_RE = re.compile(
    r"\b(colou?r|favou?r|behaviou?r|neighbou?r|flavou?r"
    r"|organi[sz](e|ed|es|ing|ation|ations|er|ers)"
    r"|reali[sz](e|ed|es|ing|ation)|recogni[sz](e|ed|es|ing)|apologi[sz](e|ed|es|ing)"
    r"|analy[sz]e|cent(re|er)s?\b|theat(re|er)|travell?(ed|ing|er|ers)\b"
    r"|cancell?(ed|ing)\b|programmes?\b|cheques?\b|gr[ae]y\b|jewel(le)?ry"
    r"|defen[cs]e|catalogu?e?|mom\b|mum\b)",
    re.IGNORECASE,
)

DEFAULT_INSTRUCTIONS = {
    "cloze": "Choose the option that best fills the gap.",
    "error_id_segments": "One of the parts in brackets is wrong. Choose that part.",
    "error_id": "",
    "reading": "",
    "lexical_pragmatic": "Choose the best option.",
}


@dataclass(frozen=True)
class Issue:
    """One validation problem, located by file and/or record id."""

    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}: {self.message}"


@dataclass
class RawBank:
    """Unparsed bank records. ``items`` pairs each record with its file's level."""

    items: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    passages: list[dict[str, Any]] = field(default_factory=list)


class BankValidationError(Exception):
    """Raised by :func:`load_bank` when the bank has validation errors."""

    def __init__(self, issues: list[Issue]) -> None:
        self.issues = issues
        super().__init__(f"{len(issues)} item-bank error(s); first: {issues[0]}")


def default_instruction(item_type: str, question: str) -> str:
    """Return the instruction shown when an item does not define its own."""
    if item_type == "error_id" and SEGMENT_RE.search(question):
        return DEFAULT_INSTRUCTIONS["error_id_segments"]
    return DEFAULT_INSTRUCTIONS.get(item_type, "")


def read_raw_bank(bank_dir: Path = DEFAULT_BANK_DIR) -> tuple[RawBank, list[Issue]]:
    """Read the JSON files of a bank directory without validating content.

    Returns:
        The raw records and any file-level problems (missing or unparsable
        files, wrong top-level type).
    """
    raw = RawBank()
    issues: list[Issue] = []
    for level in CEFR_LEVELS:
        records = _read_json_list(bank_dir / f"{level.lower()}.json", issues)
        raw.items.extend((level, record) for record in records)
    raw.passages = _read_json_list(bank_dir / PASSAGES_FILE, issues)
    return raw, issues


def _read_json_list(path: Path, issues: list[Issue]) -> list[dict[str, Any]]:
    if not path.exists():
        issues.append(Issue(path.name, "file is missing"))
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(Issue(path.name, f"invalid JSON: {exc}"))
        return []
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        issues.append(Issue(path.name, "top level must be a list of objects"))
        return []
    return data


def _type_ok(value: Any, types: tuple[type, ...]) -> bool:
    if isinstance(value, bool) and bool not in types:
        return False
    return isinstance(value, types)


def _check_fields(
    record: dict[str, Any],
    required: dict[str, tuple[type, ...]],
    optional: dict[str, tuple[type, ...]],
    where: str,
) -> list[Issue]:
    issues = []
    for name, types in required.items():
        if name not in record:
            issues.append(Issue(where, f"missing field '{name}'"))
        elif not _type_ok(record[name], types):
            issues.append(Issue(where, f"field '{name}' has the wrong type"))
    for name, types in optional.items():
        if name in record and not _type_ok(record[name], types):
            issues.append(Issue(where, f"field '{name}' has the wrong type"))
    for name in record.keys() - required.keys() - optional.keys():
        issues.append(Issue(where, f"unknown field '{name}'"))
    return issues


def _normalise(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text.lower()).split())


def stem_identity(record: dict[str, Any]) -> str:
    """Key used to detect duplicate stems.

    Reading stems repeat across passages and rewrite-style error items share
    the stem "Which sentence is correct?", so those include their context.
    """
    question = _normalise(record["question"])
    if record["type"] == "reading":
        return f"{record['passage_id']}|{question}"
    if record["type"] == "error_id" and not SEGMENT_RE.search(record["question"]):
        return f"{question}|{_normalise(record['correct_answer'])}"
    return question


def key_length_profile(records: Iterable[dict[str, Any]]) -> tuple[float, float]:
    """Share of items whose key is the strictly longest / strictly shortest option."""
    longest = shortest = total = 0
    for record in records:
        key_len = len(record["correct_answer"])
        others = [len(o) for o in record["options"] if o != record["correct_answer"]]
        total += 1
        longest += key_len > max(others)
        shortest += key_len < min(others)
    if total == 0:
        return 0.0, 0.0
    return longest / total, shortest / total


def _validate_passage(record: dict[str, Any]) -> list[Issue]:
    where = f"passages.json:{record.get('id', '?')}"
    issues = _check_fields(record, PASSAGE_FIELDS, {}, where)
    if issues:
        return issues
    match = PASSAGE_ID_RE.match(record["id"])
    if not match:
        issues.append(Issue(where, "id must look like P-B1-01"))
    elif match.group(1) != record["cefr_level"]:
        issues.append(Issue(where, "id level does not match cefr_level"))
    if record["cefr_level"] not in CEFR_LEVELS:
        issues.append(Issue(where, "unknown cefr_level"))
    if record["status"] not in STATUSES:
        issues.append(Issue(where, "unknown status"))
    if record["version"] < 1:
        issues.append(Issue(where, "version must be >= 1"))
    words = count_words(record["text"])
    low, high = PASSAGE_WORD_RANGE
    if not low <= words <= high:
        issues.append(Issue(where, f"passage has {words} words; must be {low}-{high}"))
    found = VARIETY_SPELLING_RE.search(record["text"])
    if found:
        issues.append(Issue(where, f"variety-specific spelling '{found.group(0)}'"))
    return issues


def _validate_item(
    file_level: str, record: dict[str, Any], passages: dict[str, dict[str, Any]]
) -> list[Issue]:
    where = f"{file_level.lower()}.json:{record.get('id', '?')}"
    issues = _check_fields(record, ITEM_FIELDS, OPTIONAL_ITEM_FIELDS, where)
    if issues:
        return issues

    def err(message: str) -> None:
        issues.append(Issue(where, message))

    item_type, level, domain = record["type"], record["cefr_level"], record["domain"]
    if level not in CEFR_LEVELS:
        err("unknown cefr_level")
    elif level != file_level:
        err(f"cefr_level {level} is in the {file_level} file")
    if item_type not in TYPE_CODES:
        err("unknown type")
        return issues
    match = ITEM_ID_RE.match(record["id"])
    if not match:
        err("id must look like B2-CLZ-014")
    elif match.group(1) != level or match.group(2) != TYPE_CODES[item_type]:
        err("id prefix does not match cefr_level/type")

    if domain not in TYPE_DOMAINS[item_type]:
        err(f"domain '{domain}' is not allowed for type '{item_type}'")
    elif record["skill_tested"] not in SKILL_TAGS[domain]:
        err(f"skill_tested '{record['skill_tested']}' is not a {domain} tag")
    if record["status"] not in STATUSES:
        err("unknown status")
    if record["version"] < 1:
        err("version must be >= 1")

    # Options and key.
    options = record["options"]
    key = record["correct_answer"]
    if len(options) != 4 or not all(isinstance(o, str) for o in options):
        err("must have exactly 4 string options")
        return issues
    if any(not o.strip() or o != o.strip() for o in options):
        err("options must be non-empty and have no surrounding spaces")
    if len({o.lower() for o in options}) != 4:
        err("options must be unique (case-insensitive)")
    if key not in options:
        err("correct_answer is not one of the options")
        return issues
    distractors = [o for o in options if o != key]

    rationale = record["distractor_rationale"]
    if set(rationale) != set(distractors):
        err("distractor_rationale must have exactly one entry per distractor")
    if any(not isinstance(v, str) or not v.strip() for v in rationale.values()):
        err("every distractor rationale must be a non-empty string")

    # Option-length balance for this item.
    key_len = len(key)
    longest_other = max(len(o) for o in distractors)
    shortest_other = min(len(o) for o in distractors)
    if key_len - longest_other > max(3, 0.25 * longest_other):
        err("key is conspicuously longer than every distractor")
    if shortest_other - key_len > max(3, 0.25 * shortest_other):
        err("key is conspicuously shorter than every distractor")

    # Wording rules.
    instruction = record.get("instruction", default_instruction(item_type, record["question"]))
    texts = [record["question"], instruction, *options]
    for pattern in FORBIDDEN_PATTERNS:
        if any(pattern.search(t) for t in texts):
            err(f"forbidden option pattern: {pattern.pattern}")
    negative_targets = [instruction] + ([record["question"]] if item_type == "reading" else [])
    if any(NEGATIVE_STEM_RE.search(t) for t in negative_targets):
        err("negative stem; capitalise an essential negation (NOT, EXCEPT)")
    for text in [*texts, record["explanation"]]:
        found = VARIETY_SPELLING_RE.search(text)
        if found:
            err(f"variety-specific spelling '{found.group(0)}'")
            break

    explanation = record["explanation"]
    if count_words(explanation) > MAX_EXPLANATION_WORDS:
        err(f"explanation exceeds {MAX_EXPLANATION_WORDS} words")
    if item_type != "reading":
        for d in distractors:
            if count_words(d) <= NAMED_DISTRACTOR_MAX_WORDS and d.lower() not in explanation.lower():
                err(f"explanation does not say why '{d}' is wrong")

    # Type-specific structure.
    blanks = len(BLANK_RE.findall(record["question"]))
    if item_type == "cloze" and blanks != 1:
        err("cloze question must contain exactly one ___ gap")
    if item_type == "lexical_pragmatic" and blanks > 1:
        err("lexical item may contain at most one gap")
    if item_type == "error_id" and SEGMENT_RE.search(record["question"]):
        segments = SEGMENT_RE.findall(record["question"])
        if sorted(segments) != sorted(options):
            err("segment options must match the [bracketed] parts of the question exactly")

    # Passage link.
    passage_id = record["passage_id"]
    if item_type == "reading":
        if passage_id not in passages:
            err(f"reading item needs a valid passage_id (got {passage_id!r})")
        elif passages[passage_id].get("cefr_level") != level:
            err("passage level differs from item level")
    elif passage_id is not None:
        err("only reading items may have a passage_id")

    # Provisional parameters.
    b = record["difficulty_b"]
    if level in ANCHOR_B:
        offset = b - ANCHOR_B[level]
        if abs(offset) > MAX_B_ADJUSTMENT + 1e-9:
            err(f"difficulty_b {b} is more than {MAX_B_ADJUSTMENT} from the {level} anchor")
        elif abs(offset) > 1e-9 and not record["author_notes"].strip():
            err("difficulty_b differs from the anchor; justify it in author_notes")
    if not 0 < record["discrimination_a"] <= 3:
        err("discrimination_a must be in (0, 3]")
    if not 0 <= record["guessing_c"] < 0.5:
        err("guessing_c must be in [0, 0.5)")
    return issues


def validate_raw(raw: RawBank) -> list[Issue]:
    """Apply every bank rule to raw records and return the problems found."""
    issues: list[Issue] = []
    passages: dict[str, dict[str, Any]] = {}
    passage_texts: Counter[str] = Counter()
    for record in raw.passages:
        issues.extend(_validate_passage(record))
        pid = record.get("id")
        if isinstance(pid, str):
            if pid in passages:
                issues.append(Issue("passages.json", f"duplicate passage id {pid}"))
            passages[pid] = record
        if isinstance(record.get("text"), str):
            passage_texts[_normalise(record["text"])] += 1
    if any(n > 1 for n in passage_texts.values()):
        issues.append(Issue("passages.json", "duplicate passage text"))

    seen_ids: set[str] = set()
    stems: dict[str, str] = {}
    valid_records = []
    passage_sizes: Counter[str] = Counter()
    for file_level, record in raw.items:
        item_issues = _validate_item(file_level, record, passages)
        issues.extend(item_issues)
        item_id = record.get("id")
        if item_id in seen_ids:
            issues.append(Issue(str(item_id), "duplicate item id"))
        seen_ids.add(item_id)
        if item_issues:
            continue
        valid_records.append(record)
        identity = stem_identity(record)
        if identity in stems:
            issues.append(Issue(item_id, f"duplicate stem (same as {stems[identity]})"))
        stems.setdefault(identity, item_id)
        if record["passage_id"]:
            passage_sizes[record["passage_id"]] += 1

    low, high = PASSAGE_ITEM_RANGE
    for pid in passages:
        if not low <= passage_sizes[pid] <= high:
            issues.append(Issue(pid, f"passage has {passage_sizes[pid]} items; must be {low}-{high}"))

    if len(valid_records) >= KEY_EXTREME_MIN_ITEMS:
        longest, shortest = key_length_profile(valid_records)
        if longest > KEY_EXTREME_MAX_SHARE:
            issues.append(Issue("bank", f"key is the longest option in {longest:.0%} of items"))
        if shortest > KEY_EXTREME_MAX_SHARE:
            issues.append(Issue("bank", f"key is the shortest option in {shortest:.0%} of items"))
    return issues


class ItemBank:
    """In-memory, read-only view of a validated bank."""

    def __init__(self, items: Iterable[Item], passages: Iterable[Passage]) -> None:
        self._items = {item.id: item for item in items}
        self._passages = {p.id: p for p in passages}
        groups: dict[str, list[Item]] = {}
        for item in self._items.values():
            if item.passage_id:
                groups.setdefault(item.passage_id, []).append(item)
        self._passage_items = {pid: tuple(sorted(g, key=lambda i: i.id)) for pid, g in groups.items()}

    def __len__(self) -> int:
        return len(self._items)

    @property
    def items(self) -> tuple[Item, ...]:
        """All items, in id order."""
        return tuple(self._items[k] for k in sorted(self._items))

    @property
    def passages(self) -> tuple[Passage, ...]:
        """All passages, in id order."""
        return tuple(self._passages[k] for k in sorted(self._passages))

    def get(self, item_id: str) -> Item:
        """Return the item with ``item_id`` (KeyError if absent)."""
        return self._items[item_id]

    def passage(self, passage_id: str) -> Passage:
        """Return the passage with ``passage_id`` (KeyError if absent)."""
        return self._passages[passage_id]

    def passage_items(self, passage_id: str) -> tuple[Item, ...]:
        """Return the items attached to a passage, in id order."""
        return self._passage_items.get(passage_id, ())

    def query(
        self,
        *,
        level: str | None = None,
        item_type: str | None = None,
        domain: str | None = None,
        skill: str | None = None,
        include_retired: bool = False,
    ) -> list[Item]:
        """Return items matching every given filter, in id order."""
        return [
            item
            for item in self.items
            if (level is None or item.cefr_level == level)
            and (item_type is None or item.type == item_type)
            and (domain is None or item.domain == domain)
            and (skill is None or item.skill_tested == skill)
            and (include_retired or item.status != "retired")
        ]


def build_bank(raw: RawBank) -> ItemBank:
    """Turn raw records (assumed valid) into an :class:`ItemBank`."""
    passages = [Passage(**record) for record in raw.passages]
    items = []
    for _, record in raw.items:
        data = dict(record)
        data["options"] = tuple(data["options"])
        data["difficulty_b"] = float(data["difficulty_b"])
        data["discrimination_a"] = float(data["discrimination_a"])
        data["guessing_c"] = float(data["guessing_c"])
        data.setdefault("instruction", default_instruction(data["type"], data["question"]))
        items.append(Item(**data))
    return ItemBank(items, passages)


def load_bank(bank_dir: Path = DEFAULT_BANK_DIR) -> ItemBank:
    """Read, validate and build the bank; raise if any rule is broken."""
    raw, issues = read_raw_bank(bank_dir)
    issues += validate_raw(raw)
    if issues:
        raise BankValidationError(issues)
    return build_bank(raw)
