import random

import pytest

from placement import exposure


def test_unseen_and_oldest_seen():
    seen = {"a": 1, "b": 2, "c": 1}
    assert exposure.unseen(["a", "x", "b", "y"], seen) == ["x", "y"]
    assert exposure.oldest_seen(["b", "c", "a", "x"], seen) == ["c", "a"]
    assert exposure.oldest_seen(["x"], seen) == []


def test_randomesque_picks_only_from_closest_n():
    values = list(range(20))
    picks = {
        exposure.randomesque(values, lambda v: abs(v - 10), str, random.Random(s), n=3) for s in range(200)
    }
    assert picks <= {9, 10, 11}
    assert len(picks) > 1
    assert exposure.randomesque(values, lambda v: abs(v - 10), str, random.Random(0), n=1) == 10


def test_randomesque_is_reproducible_and_rejects_empty():
    values = [5, 3, 8, 1]
    first = exposure.randomesque(values, abs, str, random.Random(42))
    assert first == exposure.randomesque(values, abs, str, random.Random(42))
    with pytest.raises(ValueError):
        exposure.randomesque([], abs, str, random.Random(0))


def test_summarise_exposure():
    summary = exposure.summarise_exposure({"a": 10, "b": 5}, ["a", "b", "c", "d"], n_tests=10)
    assert summary.max_rate == 1.0
    assert summary.median_rate == 0.25
    assert summary.unused_share == 0.5
    assert summary.most_exposed[0] == ("a", 1.0)
    empty = exposure.summarise_exposure({}, [], n_tests=0)
    assert empty.max_rate == 0.0 and empty.unused_share == 0.0
