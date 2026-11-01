import copy
import json

import pytest

from placement.bank import (
    DEFAULT_BANK_DIR,
    BankValidationError,
    RawBank,
    load_bank,
    read_raw_bank,
    validate_raw,
)
from placement.config import CEFR_LEVELS, SKILL_TAGS
from tools import validate_bank


@pytest.fixture(scope="module")
def raw():
    raw, issues = read_raw_bank()
    assert issues == []
    return raw


def mutate(raw: RawBank, item_id: str, **changes) -> RawBank:
    """Return a deep copy of ``raw`` with one item's fields replaced."""
    clone = copy.deepcopy(raw)
    for _, record in clone.items:
        if record["id"] == item_id:
            for key, value in changes.items():
                if value is None and key in ("instruction",):
                    record.pop(key, None)
                else:
                    record[key] = value
    return clone


def messages(raw: RawBank) -> str:
    return "\n".join(str(i) for i in validate_raw(raw))


def test_real_bank_is_valid_and_balanced(raw):
    assert validate_raw(raw) == []
    bank = load_bank()
    per_level = {level: len(bank.query(level=level)) for level in CEFR_LEVELS}
    assert min(per_level.values()) >= 8
    for level in CEFR_LEVELS:
        types = {i.type for i in bank.query(level=level)}
        assert types == {"cloze", "error_id", "reading", "lexical_pragmatic"}
    tags = {t for tags in SKILL_TAGS.values() for t in tags}
    assert all(item.skill_tested in tags for item in bank.items)


def test_bank_queries():
    bank = load_bank()
    item = bank.get("B1-RDG-002")
    assert item.passage_id == "P-B1-01"
    siblings = bank.passage_items("P-B1-01")
    assert [i.id for i in siblings] == sorted(i.id for i in siblings)
    assert item in siblings
    assert bank.passage("P-B1-01").word_count > 40
    assert all(i.domain == "grammar" for i in bank.query(domain="grammar"))
    assert all(i.type == "cloze" for i in bank.query(item_type="cloze", level="A1"))
    assert bank.query(skill="Inference")
    assert bank.passage_items("missing") == ()
    assert item.is_correct(item.correct_answer)
    assert not item.is_correct(item.distractors[0])
    assert bank.get("A1-ERR-001").uses_segments
    assert not bank.get("A2-ERR-002").uses_segments


@pytest.mark.parametrize(
    ("item_id", "changes", "expected"),
    [
        ("A1-CLZ-001", {"options": ["works", "work", "is work"]}, "exactly 4"),
        ("A1-CLZ-001", {"options": ["works", "Works", "is work", "working"]}, "unique"),
        ("A1-CLZ-001", {"correct_answer": "worked"}, "not one of the options"),
        ("A1-CLZ-001", {"distractor_rationale": {"work": "x", "is work": "y"}}, "one entry per distractor"),
        ("A1-CLZ-001", {"distractor_rationale": {"work": "x", "is work": "y", "working": " "}}, "non-empty"),
        ("A1-CLZ-001", {"difficulty_b": -1.9}, "from the A1 anchor"),
        ("A1-CLZ-001", {"author_notes": ""}, "justify it"),
        ("A1-CLZ-001", {"question": "My brother works in a bank."}, "exactly one ___ gap"),
        ("A1-CLZ-001", {"explanation": "word " * 61}, "exceeds 60 words"),
        ("A1-CLZ-001", {"explanation": "Use 'works' for he/she/it."}, "why 'is work' is wrong"),
        ("A1-CLZ-001", {"skill_tested": "Detail"}, "not a grammar tag"),
        ("A1-CLZ-001", {"domain": "reading"}, "not allowed for type"),
        ("A1-CLZ-001", {"id": "A2-CLZ-001"}, "id prefix"),
        ("A1-CLZ-001", {"id": "A1-CLOZE-1"}, "id must look like"),
        ("A1-CLZ-001", {"cefr_level": "A2"}, "is in the A1 file"),
        ("A1-CLZ-001", {"passage_id": "P-A1-01"}, "only reading items"),
        ("A1-CLZ-001", {"status": "draft"}, "unknown status"),
        ("A1-CLZ-001", {"version": 0}, "version must be"),
        ("A1-CLZ-001", {"discrimination_a": 0}, "discrimination_a"),
        ("A1-CLZ-001", {"guessing_c": 0.6}, "guessing_c"),
        ("A1-CLZ-001", {"difficulty_b": True}, "wrong type"),
        ("A1-CLZ-001", {"extra": 1}, "unknown field"),
        ("A1-CLZ-001", {"options": ["works", "work", "is work", "all of the above"]}, "forbidden"),
        ("A1-CLZ-001", {"instruction": "Choose the option that is not correct."}, "negative stem"),
        ("A1-CLZ-001", {"question": "My neighbour ___ in a bank."}, "variety-specific"),
        ("A1-RDG-001", {"passage_id": "P-XX-99"}, "valid passage_id"),
        ("A1-RDG-001", {"passage_id": "P-A2-01"}, "passage level differs"),
        ("A1-RDG-001", {"question": "Why doesn't Lena like her job?"}, "negative stem"),
        ("A1-ERR-001", {"question": "We [are] from Spain, but now we [live] in [the] Paris."}, "segment options"),
        (
            "A1-CLZ-001",
            {"options": ["works hard every day", "work", "is work", "go"], "correct_answer": "works hard every day",
             "distractor_rationale": {"work": "a", "is work": "b", "go": "c"}},
            "conspicuously longer",
        ),
        (
            "A1-CLZ-001",
            {"options": ["go", "working hard", "is working", "works daily"], "correct_answer": "go",
             "distractor_rationale": {"working hard": "a", "is working": "b", "works daily": "c"}},
            "conspicuously shorter",
        ),
        ("A1-LEX-002", {"question": "Can I ___ you ___?"}, "at most one gap"),
        ("A1-CLZ-001", {"type": "essay"}, "unknown type"),
        ("A1-CLZ-001", {"cefr_level": "D1"}, "unknown cefr_level"),
    ],
)
def test_validator_catches_rule_breaks(raw, item_id, changes, expected):
    assert expected in messages(mutate(raw, item_id, **changes))


def test_validator_bank_level_rules(raw):
    clone = copy.deepcopy(raw)
    first = clone.items[0][1]
    clone.items.append(clone.items[0])
    assert "duplicate item id" in messages(clone)

    clone = mutate(raw, "A1-CLZ-002", question=raw.items[0][1]["question"])
    assert "duplicate stem" in messages(clone)

    clone = copy.deepcopy(raw)
    clone.passages[0]["text"] = "Too short."
    clone.passages.append(copy.deepcopy(clone.passages[1]))
    out = messages(clone)
    assert "words; must be" in out
    assert "duplicate passage id" in out
    assert "duplicate passage text" in out

    clone = copy.deepcopy(raw)
    clone.passages[0].update(id="P-A2-09", status="x", version=0)
    out = messages(clone)
    assert "id level does not match" in out and "unknown status" in out and "version must be" in out
    clone.passages[0].update(id="bad", cefr_level="Z9")
    assert "id must look like" in messages(clone)
    clone.passages[0]["text"] = "My favourite colour " * 10
    assert "variety-specific" in messages(clone)
    clone.passages[0].pop("title")
    assert "missing field 'title'" in messages(clone)
    assert first  # the original record was not modified by the clones


def test_key_length_profile_rule(raw):
    clone = copy.deepcopy(raw)
    for _, record in clone.items:
        key = record["correct_answer"]
        others = [o for o in record["options"] if o != key]
        longest = max(len(o) for o in others)
        if len(key) <= longest:
            new_key = key + "." * (longest - len(key) + 1)
            record["options"] = [new_key if o == key else o for o in record["options"]]
            record["correct_answer"] = new_key
    assert "longest option in" in messages(clone)


def test_load_bank_raises_on_errors(tmp_path):
    for path in DEFAULT_BANK_DIR.iterdir():
        (tmp_path / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    data = json.loads((tmp_path / "a1.json").read_text(encoding="utf-8"))
    data[0]["options"] = data[0]["options"][:3]
    (tmp_path / "a1.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(BankValidationError) as excinfo:
        load_bank(tmp_path)
    assert "exactly 4" in str(excinfo.value)


def test_read_raw_bank_reports_file_problems(tmp_path):
    (tmp_path / "a1.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "a2.json").write_text('{"items": []}', encoding="utf-8")
    _, issues = read_raw_bank(tmp_path)
    text = "\n".join(map(str, issues))
    assert "invalid JSON" in text
    assert "list of objects" in text
    assert "file is missing" in text


def test_cli_ok_and_fail(tmp_path, capsys):
    assert validate_bank.main(["--show", "B1-RDG-002", "A1-CLZ-001"]) == 0
    out = capsys.readouterr().out
    assert "[KEY]" in out and "Passage P-B1-01" in out and "OK:" in out
    assert validate_bank.main(["--bank-dir", str(tmp_path)]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_key_length_warning_is_not_an_error(raw, capsys, monkeypatch):
    from placement.bank import key_length_warnings

    records = [r for _, r in raw.items]
    assert key_length_warnings(records) == []  # the real bank is balanced
    skewed = []
    for record in records[:20]:
        clone = copy.deepcopy(record)
        others = [o for o in clone["options"] if o != clone["correct_answer"]]
        longest = max(len(o) for o in others)
        if len(clone["correct_answer"]) <= longest:
            key = clone["correct_answer"] + "." * (longest - len(clone["correct_answer"]) + 1)
            clone["options"] = [key if o == clone["correct_answer"] else o for o in clone["options"]]
            clone["correct_answer"] = key
        skewed.append(clone)
    assert "warning above 30%" in key_length_warnings(skewed)[0]
    assert key_length_warnings(skewed[:5]) == []  # too few items to judge
    monkeypatch.setattr(validate_bank, "key_length_warnings", lambda records: ["key is long"])
    assert validate_bank.main([]) == 0
    assert "WARNING: key is long" in capsys.readouterr().out
