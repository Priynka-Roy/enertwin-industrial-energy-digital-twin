"""Hand-solvable robust workload constraints and cost tradeoffs."""
import json

import numpy as np
import pytest

from enertwin.optimization import optimize_schedule
from enertwin.robust import optimize_robust


def task(energy=1.0, power=1.0, start=0, end=2):
    return [{"name": "Job", "energy_kwh": energy, "max_power_kw": power,
             "start_slot": start, "end_slot": end}]


def test_shared_robust_schedule_pays_known_premium_and_prevents_violation():
    backgrounds = [[0, 0], [1, 0]]
    prices = [1, 3]
    deterministic = optimize_schedule(backgrounds[0], prices, task(), 1, 1, 1)
    robust = optimize_robust(backgrounds, prices, task(), 1, 1, 1)
    assert deterministic["optimized_flexible_kwh"] == pytest.approx([1, 0])
    assert robust["optimized_flexible_kwh"] == pytest.approx([0, 1])
    assert deterministic["metrics"]["optimized"]["flexible_cost_eur"] == 1
    assert robust["metrics"]["optimized"]["flexible_cost_eur"] == 3
    assert np.max(np.asarray(backgrounds[1]) + deterministic["optimized_flexible_kwh"]) > 1
    assert [row["cost_eur"] for row in robust["scenario_metrics"]["optimized"]] == [3, 4]
    assert robust["scenario_cost_summary"]["optimized"]["worst_cost_eur"] == 4
    assert all(all(row.values()) for row in robust["scenario_constraint_verification"]["optimized"])
    json.dumps(robust, allow_nan=False)


def test_envelope_is_exact_for_noncoincident_scenario_peaks():
    result = optimize_robust([[.8, 0], [0, .8]], [1, 2], task(.4), 1, 1, 1)
    assert result["feasible"]
    assert result["optimized_flexible_kwh"] == pytest.approx([.2, .2])
    assert all(row["peak_kw"] == pytest.approx(1) for row in result["scenario_metrics"]["optimized"])


def test_individually_feasible_scenarios_can_have_no_shared_schedule():
    scenarios = [[1, 0], [0, 1]]
    assert all(optimize_schedule(row, [1, 2], task(), 1, 1, 1)["feasible"] for row in scenarios)
    result = optimize_robust(scenarios, [1, 2], task(), 1, 1, 1)
    assert not result["feasible"]
    assert "optimized_flexible_kwh" not in result


def test_one_scenario_matches_deterministic_solution():
    kwargs = dict(tasks=task(), shared_capacity_kw=2, peak_limit_kw=3, interval_hours=.5)
    normal = optimize_schedule([.1, .2], [2, 1], **kwargs)
    robust = optimize_robust([[.1, .2]], [2, 1], **kwargs)
    assert robust["optimized_task_allocations"] == normal["optimized_task_allocations"]


def test_robust_verifies_windows_power_completion_shared_capacity_and_units():
    tasks = [{"name": "A", "energy_kwh": .5, "max_power_kw": 1, "start_slot": 1, "end_slot": 3},
             {"name": "B", "energy_kwh": .25, "max_power_kw": 1, "start_slot": 0, "end_slot": 1}]
    result = optimize_robust([[.1, .2, .1], [.2, .1, .2]], [1, 2, 3], tasks, 1, 2, .25)
    assert result["feasible"]
    allocations = result["optimized_task_allocations"]
    assert allocations["A"][0] == 0
    assert sum(allocations["A"]) == pytest.approx(.5)
    assert sum(allocations["B"]) == pytest.approx(.25)
    assert max(result["optimized_flexible_kwh"]) <= .25 + 1e-8
    assert all(all(check.values()) for check in result["scenario_constraint_verification"]["optimized"])


@pytest.mark.parametrize("scenarios", [[], [1, 2], [[]], [[-1, 2]], [[np.nan, 0]], [[np.inf, 0]]])
def test_invalid_background_sets_rejected(scenarios):
    with pytest.raises(ValueError):
        optimize_robust(scenarios, [1, 1])


def test_background_exceeding_peak_not_relaxed_even_with_no_tasks():
    result = optimize_robust([[.2, .3], [.2, 2]], [1, 1], [], 1, 1, 1)
    assert not result["feasible"]
    assert result["scenario_metrics"] == {}


def test_flat_prices_conserve_cost_across_feasible_schedules():
    result = optimize_robust([[.1, .2], [.2, .1]], 2, task(), 2, 3, .5)
    assert result["feasible"]
    assert result["cost_savings_eur"] == 0
    assert result["energy_savings_kwh"] == 0
