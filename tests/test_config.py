import pytest

from placement import config


def test_apportion_sums_and_is_deterministic():
    split = config.apportion(7, {"a": 1, "b": 1, "c": 1})
    assert split == {"a": 3, "b": 2, "c": 2}
    assert sum(config.apportion(40, config.SLOT_SHARES).values()) == 40


@pytest.mark.parametrize(("total", "weights"), [(-1, {"a": 1}), (3, {"a": 0})])
def test_apportion_rejects_bad_input(total, weights):
    with pytest.raises(ValueError):
        config.apportion(total, weights)


def test_default_length_matches_brief():
    assert config.stage_lengths() == (10, 10, 8)
    quotas = config.slot_quotas()
    assert quotas == {
        ("cloze", "grammar"): 4,
        ("cloze", "vocabulary"): 4,
        ("error_id", "grammar"): 7,
        ("reading", "reading"): 7,
        ("lexical_pragmatic", "vocabulary"): 6,
    }
    grammar = sum(n for (_, d), n in quotas.items() if d == "grammar")
    vocabulary = sum(n for (_, d), n in quotas.items() if d == "vocabulary")
    assert (grammar, vocabulary) == (11, 10)
    assert config.routing_levels(10) == ["A1", "A2", "A2", "B1", "B1", "B1", "B2", "B2", "B2", "C1"]


@pytest.mark.parametrize("length", [20, 28, 40, 55])
def test_quotas_scale_with_length(length):
    assert sum(config.stage_lengths(length)) == length
    assert sum(config.slot_quotas(length).values()) == length
    assert len(config.fixed_form_levels(length)) == length
    assert len(config.routing_levels(config.stage_lengths(length)[0])) == config.stage_lengths(length)[0]
