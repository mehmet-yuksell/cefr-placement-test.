import math

import pytest

from placement import scoring
from placement.config import CEFR_LEVELS, MIN_ITEMS_FOR_RESULT
from placement.models import TagScore
from placement.scoring import ScoredResponse as R


def items(bs, pattern, domain="grammar", tag="Tenses & aspect"):
    return [R(b=b, correct=c, domain=domain, tag=tag) for b, c in zip(bs, pattern)]


B28 = [(-2.5 + 5.0 * i / 27) for i in range(28)]


def test_p_correct_bounds_and_shape():
    assert scoring.p_correct(0.0, 0.0) == pytest.approx(0.625)
    assert scoring.p_correct(-50, 0) == pytest.approx(0.25)
    assert scoring.p_correct(50, 0) == pytest.approx(1.0)
    assert scoring.p_correct(1, 0) > scoring.p_correct(0, 0)


def test_eap_without_data_returns_prior():
    est = scoring.eap([])
    assert est.theta == pytest.approx(0.0, abs=1e-9)
    assert est.se == pytest.approx(1.0, abs=0.01)
    assert sum(est.posterior) == pytest.approx(1.0)


def test_eap_monotonic_in_number_correct():
    # Turning wrong answers into right ones, one at a time, never lowers theta.
    pattern = [False] * 28
    previous = scoring.eap(items(B28, pattern)).theta
    for i in range(28):
        pattern[i] = True
        theta = scoring.eap(items(B28, pattern)).theta
        assert theta > previous
        previous = theta


def test_all_correct_and_all_wrong_are_finite_and_extreme():
    top = scoring.eap(items(B28, [True] * 28))
    bottom = scoring.eap(items(B28, [False] * 28))
    assert math.isfinite(top.theta) and math.isfinite(bottom.theta)
    assert top.theta > 2.0 and bottom.theta < -2.0
    assert scoring.score_responses(items(B28, [True] * 28), True).level in ("C1", "C2")
    assert scoring.score_responses(items(B28, [False] * 28), True).level == "A1"


@pytest.mark.parametrize(
    ("theta", "level"),
    [(-2.0001, "A1"), (-2.0, "A2"), (-1.0001, "A2"), (-1.0, "B1"), (-0.0001, "B1"), (0.0, "B2"),
     (0.9999, "B2"), (1.0, "C1"), (1.9999, "C1"), (2.0, "C2"), (-9, "A1"), (9, "C2")],
)
def test_cut_score_boundaries(theta, level):
    assert scoring.level_for_theta(theta) == level


def test_level_probabilities_sum_to_one_and_split_cut_mass():
    post = [0.0] * len(scoring.GRID)
    post[scoring.GRID.index(min(scoring.GRID, key=lambda t: abs(t - 0.0)))] = 1.0
    probs = scoring.level_probabilities(post)
    assert probs["B1"] == pytest.approx(0.5) and probs["B2"] == pytest.approx(0.5)
    probs = scoring.level_probabilities(scoring.eap(items(B28, [True] * 14 + [False] * 14)).posterior)
    assert sum(probs.values()) == pytest.approx(1.0)
    assert set(probs) == set(CEFR_LEVELS)


def test_most_likely_level_breaks_ties_downwards():
    probs = dict.fromkeys(CEFR_LEVELS, 0.0)
    probs.update(B1=0.4, B2=0.4, C1=0.2)
    assert scoring.most_likely_level(probs) == "B1"


def test_borderline_rule():
    assert scoring.borderline_with(0.1, 0.5, "B2") == "B1"
    assert scoring.borderline_with(-0.1, 0.5, "B1") == "B2"
    assert scoring.borderline_with(0.3, 0.5, "B2") is None  # 0.3 >= 0.25
    assert scoring.borderline_with(0.1, 0.5, "C2") is None  # headline not next to that cut


def test_scaled_score():
    assert scoring.scaled_score(-5) == 0
    assert scoring.scaled_score(0) == 50
    assert scoring.scaled_score(3) == 100
    assert scoring.scaled_score(1.5) == 75


def test_domain_scores_are_suppressed_below_five_items():
    responses = items(B28[:6], [True] * 6, domain="grammar") + items(B28[:4], [True] * 4, domain="reading")
    scores = scoring.domain_scores(responses)
    assert not scores["grammar"].suppressed and scores["grammar"].level in CEFR_LEVELS
    assert scores["reading"].suppressed and scores["reading"].theta is None
    assert scores["reading"].percent_correct == 100.0
    assert scores["vocabulary"].n_items == 0 and scores["vocabulary"].percent_correct == 0.0


def test_tag_scores_and_strengths():
    responses = (
        items([0.0, 0.0, 0.0], [True, True, True], tag="Collocations")
        + items([0.0, 0.0, 0.0], [False, False, False], tag="Phrasal verbs")
        + items([0.0], [True], tag="Detail")
        + [R(b=0.0, correct=True)]
    )
    tags = scoring.tag_scores(responses, theta=0.0)
    assert [t.tag for t in tags] == ["Collocations", "Detail", "Phrasal verbs"]
    strengths, focus = scoring.strengths_and_focus(tags)
    assert [t.tag for t in strengths] == ["Collocations"]
    assert [t.tag for t in focus] == ["Phrasal verbs"]
    assert focus[0].residual == pytest.approx(-0.625)
    assert scoring.strengths_and_focus([TagScore("x", 2, 1, 1.0)]) == ([], [])


def test_early_stop_rule():
    clear = scoring.eap(items(B28, [False] * 28)).posterior
    assert not scoring.early_stop_reached(clear, 19)
    assert scoring.early_stop_reached(clear, 20)
    vague = scoring.eap([]).posterior
    assert not scoring.early_stop_reached(vague, 25)


def test_score_responses_result_and_insufficient_data():
    result = scoring.score_responses(items(B28, [i < 18 for i in range(28)]), complete=True)
    assert result.n_answered == 28 and result.complete
    assert result.level == scoring.most_likely_level(result.level_probabilities)
    assert 0 <= result.scaled_score <= 100
    assert result.se < 1.0
    partial = scoring.score_responses(items(B28[:12], [True] * 12), complete=False)
    assert not partial.complete
    with pytest.raises(scoring.InsufficientDataError):
        scoring.score_responses(items(B28[: MIN_ITEMS_FOR_RESULT - 1], [True] * 9), complete=False)
