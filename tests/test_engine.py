import json
from collections import Counter

import pytest

from placement import engine
from placement.config import ANCHOR_B, slot_quotas
from tests.conftest import make_bank


def run(bank, answer, **kwargs):
    """Run a whole test; ``answer(item)`` returns True for a correct answer."""
    state = engine.new_test(bank, **kwargs)
    while (item := engine.current_item(state, bank)) is not None:
        engine.record_answer(state, bank, item.id, answer(item))
    return state


def knows_up_to(theta):
    return lambda item: item.difficulty_b <= theta


def test_full_adaptive_test_meets_quotas_and_keeps_passages_together(big_bank):
    state = run(big_bank, knows_up_to(0.0), seed=1)
    assert len(state.answers) == 28 and state.finished
    kinds = Counter(engine.kind_of(big_bank.get(i)) for i in state.selected)
    assert kinds == {f"{t}/{d}": n for (t, d), n in slot_quotas().items()}
    assert state.flags == []
    assert [e["position"] for e in state.events if e["event"] == "stage_end"] == [10, 20]
    for pid in {big_bank.get(i).passage_id for i in state.selected} - {None}:
        positions = [n for n, i in enumerate(state.selected) if big_bank.get(i).passage_id == pid]
        assert positions == list(range(positions[0], positions[0] + len(positions)))
        assert len(positions) == len(big_bank.passage_items(pid))
        assert engine.stage_of(state, positions[0]) == engine.stage_of(state, positions[-1])
    json.dumps(state.to_dict())


def test_routing_stage_follows_level_plan(big_bank):
    state = engine.new_test(big_bank, seed=3)
    assert state.targets[:10] == [ANCHOR_B[x] for x in ["A1", "A2", "A2", "B1", "B1", "B1", "B2", "B2", "B2", "C1"]]
    assert all(t is None for t in state.targets[10:])


def test_stronger_examinee_gets_harder_items(big_bank):
    strong = run(big_bank, knows_up_to(2.0), seed=5)
    weak = run(big_bank, knows_up_to(-2.0), seed=5)

    def mean_b(state):
        later = state.selected[10:]
        return sum(big_bank.get(i).difficulty_b for i in later) / len(later)

    assert mean_b(strong) > mean_b(weak) + 2.0


def test_same_seed_same_test_different_seed_differs(big_bank):
    a = run(big_bank, knows_up_to(0.5), seed=11)
    b = run(big_bank, knows_up_to(0.5), seed=11)
    c = run(big_bank, knows_up_to(0.5), seed=12)
    assert a.selected == b.selected and a.events == b.events
    assert a.selected != c.selected


def test_fixed_form_is_identical_across_seeds_and_spans_all_levels(big_bank):
    a = run(big_bank, knows_up_to(0.0), seed=1, mode="fixed")
    b = run(big_bank, knows_up_to(2.0), seed=99, mode="fixed")
    assert a.selected == b.selected
    assert {big_bank.get(i).cefr_level for i in a.selected} == set(ANCHOR_B)
    assert not [e for e in a.events if e["event"] == "stage_end"]


def test_no_repeats_across_three_attempts(big_bank):
    seen: dict[str, int] = {}
    attempts = []
    for attempt in (1, 2, 3):
        state = run(big_bank, knows_up_to(0.3), seed=100 + attempt, seen=seen)
        assert "repeat" not in state.flags
        attempts.append(set(state.selected))
        seen.update(dict.fromkeys(state.selected, attempt))
    assert not attempts[0] & attempts[1]
    assert not attempts[0] & attempts[2]
    assert not attempts[1] & attempts[2]


def test_real_bank_repeats_only_through_logged_relaxation(real_bank):
    seen: dict[str, int] = {}
    for attempt in (1, 2, 3):
        state = run(real_bank, knows_up_to(0.5), seed=attempt, seen=seen)
        repeated = {i for i in state.selected if i in seen}
        logged = set()
        for event in state.events:
            if event["event"] == "repeat":
                unit = event["unit"]
                logged |= {i.id for i in real_bank.passage_items(unit)} or {unit}
        assert repeated <= logged
        if repeated:
            # Repeats come from the oldest attempt that still had unused items.
            assert min(seen[i] for i in repeated) == min(seen.values())
        seen.update(dict.fromkeys(state.selected, attempt))
    assert len(state.answers) == 28


def test_band_fallback_is_logged():
    bank = make_bank(levels=("A1", "A2"))
    state = run(bank, lambda item: True, seed=2)
    assert "band_fallback" in state.flags
    assert len(state.answers) == 28


def test_content_relaxed_when_a_kind_is_missing():
    bank = make_bank(lexical=0)
    state = run(bank, knows_up_to(0.0), seed=4)
    assert "content_relaxed" in state.flags
    assert len(state.answers) == 28


def test_bank_exhausted_ends_the_test():
    bank = make_bank(cloze_grammar=1, cloze_vocab=0, error_id=0, lexical=0, passage_sizes=(), levels=("B1",))
    state = run(bank, knows_up_to(0.0), seed=1)
    assert state.finished and len(state.answers) == 1
    assert "bank_exhausted" in state.flags
    assert engine.current_item(state, bank) is None


def test_early_stop_when_enabled(big_bank):
    state = run(big_bank, lambda item: False, seed=8, early_stop=True)
    assert state.stopped_early and len(state.answers) == 20
    assert "early_stop" in state.flags
    off = run(big_bank, lambda item: False, seed=8)
    assert len(off.answers) == 28 and not off.stopped_early


def test_length_is_configurable(big_bank):
    state = run(big_bank, knows_up_to(0.0), seed=1, length=40)
    assert len(state.answers) == 40
    assert state.stage_sizes == (14, 14, 12)


def test_guards(big_bank):
    with pytest.raises(ValueError):
        engine.new_test(big_bank, seed=1, mode="cat")
    with pytest.raises(ValueError):
        engine.new_test(big_bank, seed=1, length=0)
    state = engine.new_test(big_bank, seed=1)
    item = engine.current_item(state, big_bank)
    assert engine.current_item(state, big_bank) == item  # idempotent until answered
    with pytest.raises(ValueError):
        engine.record_answer(state, big_bank, "not-the-item", True)
    state.targets[0] = None
    state.selected.clear()
    with pytest.raises(RuntimeError):
        engine.current_item(state, big_bank)
    assert engine.stage_of(engine.new_test(big_bank, seed=1), 27) == 3


def test_replay_rebuilds_the_same_test(big_bank):
    original = run(big_bank, knows_up_to(0.3), seed=21)
    answers = list(zip(original.selected[:15], original.answers[:15]))
    rebuilt = engine.replay(big_bank, answers, seed=21, mode="adaptive")
    assert rebuilt.selected[:15] == original.selected[:15]
    assert engine.current_item(rebuilt, big_bank).id == original.selected[15]
    assert engine.replay(big_bank, [("B1-CLZ-999", True)], seed=21, mode="adaptive") is None
