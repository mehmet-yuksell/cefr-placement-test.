"""Smoke tests for the simulation tool's experiment options."""

import pytest

from placement import config, engine
from placement.scoring import borderline_with
from tools import simulate


def test_borderline_factor_is_a_parameter():
    assert borderline_with(0.12, 0.5, "B2") == "B1"  # 0.12 < 0.30 x 0.5
    assert borderline_with(0.2, 0.5, "B2") is None
    assert borderline_with(0.2, 0.5, "B2", factor=0.5) == "B1"
    assert config.BORDERLINE_SE_FACTOR == 0.30


def test_routing_weights_can_be_overridden(big_bank):
    weights = {"A1": 1, "A2": 2, "B1": 2, "B2": 3, "C1": 1, "C2": 1}
    assert config.routing_levels(10, weights)[-1] == "C2"
    state = engine.new_test(big_bank, seed=1, routing_weights=weights)
    assert state.targets[9] == config.ANCHOR_B["C2"]
    assert simulate.parse_routing("A1:1, C2:2") == {"A1": 1, "C2": 2}
    assert simulate.parse_routing(" ") is None
    with pytest.raises(SystemExit):
        simulate.parse_routing("Z9:1")


def test_simulation_reports_factor_table_and_routing(capsys):
    code = simulate.main(["--n", "40", "--seed", "3", "--retakes", "0",
                          "--borderline-factors", "0.5,0.3", "--routing", "A1:1,A2:2,B1:3,B2:3,C1:1"])
    out = capsys.readouterr().out
    assert code in (0, 1)
    assert "routing weights:" in out
    assert "borderline factor comparison" in out
    assert out.count("0.50 ") >= 1 and "0.30 " in out
