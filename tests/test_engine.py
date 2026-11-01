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
    repeats_seen = False
    for attempt in range(1, 8):  # 7 x 28 > 144, so later attempts must reuse items
        state = run(real_bank, knows_up_to(0.5), seed=attempt, seen=seen)
        repeated = {i for i in state.selected if i in seen}
        logged = set()
        for event in state.events:
            if event["event"] == "repeat":
                unit = event["unit"]
                logged |= {i.id for i in real_bank.passage_items(unit)} or {unit}
        assert repeated <= logged
        if repeated:
            repeats_seen = True
            # Reuse starts with the user's oldest attempt.
            assert min(seen[i] for i in repeated) == min(seen.values())
        seen.update(dict.fromkeys(state.selected, attempt))
    assert repeats_seen
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


@pytest.mark.parametrize("theta", [-1.5, 0.5, 1.5])
def test_real_bank_gives_five_attempts_without_repeats(real_bank, theta):
    """A user retaking with the same email sees new items for 5 attempts (144-item bank)."""
    seen: dict[str, int] = {}
    for attempt in range(1, 6):
        state = run(real_bank, knows_up_to(theta), seed=500 + attempt, seen=seen)
        assert not set(state.selected) & set(seen), f"attempt {attempt} repeated items"
        assert "repeat" not in state.flags
        seen.update(dict.fromkeys(state.selected, attempt))


# ---- Going back within a part ----------------------------------------------------------


def answer_n(bank, n, answer=None, **kwargs):
    answer = answer or knows_up_to(0.0)
    state = engine.new_test(bank, **kwargs)
    for _ in range(n):
        item = engine.current_item(state, bank)
        engine.record_answer(state, bank, item.id, answer(item))
    return state


def test_editable_range_covers_only_the_current_part(big_bank):
    assert engine.editable_range(answer_n(big_bank, 0, seed=1)) == range(0)
    assert engine.editable_range(answer_n(big_bank, 3, seed=1)) == range(3)
    assert engine.editable_range(answer_n(big_bank, 10, seed=1)) == range(10, 10)  # part 1 just locked
    assert engine.editable_range(answer_n(big_bank, 13, seed=1)) == range(10, 13)
    assert engine.editable_range(answer_n(big_bank, 25, seed=1)) == range(20, 25)
    assert engine.editable_range(run(big_bank, knows_up_to(0.0), seed=1)) == range(0)  # finished
    assert engine.stage_start(answer_n(big_bank, 0, seed=1), 27) == 20


def test_change_answer_updates_only_that_answer(big_bank):
    state = answer_n(big_bank, 13, seed=2)
    before = (list(state.selected), list(state.targets), list(state.events))
    old = state.answers[11]
    engine.change_answer(state, big_bank, 11, not old)
    assert state.answers[11] is (not old)
    assert (state.selected, state.targets, state.events) == before
    for bad in (9, 0, 13, 14, -1):  # previous part, not yet answered, nonsense
        with pytest.raises(ValueError):
            engine.change_answer(state, big_bank, bad, True)


def test_changing_answers_inside_a_part_never_changes_its_items(big_bank):
    flip = {2, 5, 8}
    a = answer_n(big_bank, 10, seed=4)
    b = engine.new_test(big_bank, seed=4)
    for pos in range(10):
        item = engine.current_item(b, big_bank)
        engine.record_answer(b, big_bank, item.id, knows_up_to(0.0)(item) ^ (pos in flip))
    assert a.selected[:10] == b.selected[:10]


def test_replay_after_changed_answers_rebuilds_the_same_test(big_bank):
    state = answer_n(big_bank, 15, seed=6)
    engine.change_answer(state, big_bank, 11, not state.answers[11])
    engine.change_answer(state, big_bank, 14, not state.answers[14])
    rebuilt = engine.replay(big_bank, list(zip(state.selected[:15], state.answers)), seed=6, mode="adaptive")
    assert rebuilt.answers == state.answers
    assert rebuilt.selected[:15] == state.selected[:15]
    assert engine.current_item(rebuilt, big_bank).id == engine.current_item(state, big_bank).id


def test_no_going_back_when_early_stop_is_on(big_bank):
    state = answer_n(big_bank, 3, seed=1, early_stop=True)
    assert engine.editable_range(state) == range(0)
    with pytest.raises(ValueError):
        engine.change_answer(state, big_bank, 1, True)


def test_fixed_form_follows_the_same_rule(big_bank):
    state = answer_n(big_bank, 12, seed=1, mode="fixed")
    assert engine.editable_range(state) == range(10, 12)
    engine.change_answer(state, big_bank, 10, False)
    with pytest.raises(ValueError):
        engine.change_answer(state, big_bank, 9, False)
