"""Availability, whole-day dependence, and reproducibility of scenarios."""
import json

import numpy as np
import pytest

from enertwin.scenarios import generate_scenarios


def test_completed_blocks_only_and_future_data_cannot_change_paths():
    blocks = np.array([np.arange(96) / 100, -np.ones(96), np.ones(96) * 999])
    dates = ["2018-09-01", "2018-09-02", "2018-09-03"]
    a = generate_scenarios(np.ones(96) * 2, blocks, dates, "2018-09-03", 12)
    blocks[-1] = -999
    b = generate_scenarios(np.ones(96) * 2, blocks, dates, "2018-09-03", 12)
    assert a == b
    assert a["eligible_blocks"] == 2
    assert a["excluded_incomplete_or_future_blocks"] == 1
    assert set(a["source_origins"][1:]) <= {"2018-09-01T00:00:00", "2018-09-02T00:00:00"}
    json.dumps(a, allow_nan=False)


def test_whole_signed_uncentered_blocks_and_explicit_stress():
    block = np.linspace(-.5, 2, 96)
    result = generate_scenarios(np.ones(96) * 3, [block], ["2018-01-01"], "2018-01-02", 4)
    assert np.asarray(result["profiles"]).shape == (4, 96)
    assert result["central_index"] == 0
    assert result["profiles"][0] == [3] * 96
    assert result["profiles"][1] == pytest.approx(3 + block)
    assert result["profiles"][2] == pytest.approx(3 + block)
    assert result["profiles"][3] == pytest.approx(3 + 1.5 * np.maximum(block, 0))
    assert result["kinds"][-1] == "synthetic_stress"
    assert "not forecast intervals" in result["interpretation"]


def test_negative_demand_is_clipped_not_hidden():
    result = generate_scenarios(np.ones(96), [-np.ones(96) * 2], ["2018-01-01"], "2018-01-02")
    assert min(result["profiles"][1]) == 0
    assert "clipped" in result["clipping"]


def test_zero_strength_and_seeded_reordering_reproducible():
    blocks = np.array([np.ones(96), np.ones(96) * 2])
    dates = ["2018-01-01", "2018-01-02"]
    a = generate_scenarios(np.ones(96), blocks, dates, "2018-01-03", seed=123)
    b = generate_scenarios(np.ones(96), blocks[::-1], dates[::-1], "2018-01-03", seed=123)
    assert a == b
    zero = generate_scenarios(np.ones(96), blocks, dates, "2018-01-03", strength=0)
    assert all(profile == [1] * 96 for profile in zero["profiles"])


def test_no_completed_blocks_raises_instead_of_leaking_same_day():
    with pytest.raises(ValueError, match="No completed"):
        generate_scenarios(np.ones(96), [np.zeros(96)], ["2018-01-01"], "2018-01-01T23:59")


@pytest.mark.parametrize("kwargs", [
    {"point": np.ones(95)}, {"point": -np.ones(96)}, {"point": np.full(96, np.nan)},
    {"residual_blocks": np.zeros((1, 95))}, {"residual_blocks": np.full((1, 96), np.inf)},
    {"residual_origins": []}, {"n_scenarios": 3}, {"n_scenarios": True},
    {"strength": -1}, {"strength": np.nan}, {"seed": -1},
])
def test_invalid_inputs_rejected(kwargs):
    inputs = dict(point=np.ones(96), residual_blocks=np.zeros((1, 96)),
                  residual_origins=["2018-01-01"], origin="2018-01-02")
    inputs.update(kwargs)
    with pytest.raises(ValueError):
        generate_scenarios(**inputs)


def test_duplicate_dates_rejected():
    with pytest.raises(ValueError, match="unique"):
        generate_scenarios(np.ones(96), np.zeros((2, 96)), ["2018-01-01"] * 2, "2018-01-02")
