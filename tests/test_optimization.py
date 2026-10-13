import itertools
import json

import numpy as np
import pytest

from enertwin.optimization import optimize_schedule
from enertwin.simulation import simulate_scenario, tariff_profile


def task(energy=2, power=4, start=0, end=4, name="A"):
    return dict(name=name, energy_kwh=energy, max_power_kw=power, start_slot=start, end_slot=end)


def test_hand_calculated_optimum_and_power_conversion():
    result = optimize_schedule([1] * 4, [4, 3, 1, 2], [task()], 4, 8)
    assert result["feasible"]
    assert result["optimized_flexible_kwh"] == pytest.approx([0, 0, 1, 1])
    assert result["baseline_flexible_kwh"] == pytest.approx([1, 1, 0, 0])
    assert result["optimized_objective_eur"] == pytest.approx(13)
    assert result["baseline_objective_eur"] == pytest.approx(17)
    assert result["cost_savings_eur"] == pytest.approx(4)
    assert result["metrics"]["optimized"]["peak_kw"] == pytest.approx(8)
    assert result["metrics"]["optimized"]["total_energy_kwh"] == pytest.approx(6)
    assert all(all(checks.values()) for checks in result["constraint_verification"].values())


def test_solver_agrees_with_exhaustive_tiny_integer_case():
    prices = np.array([0.5, 0.1, 0.3, 0.2])
    possibilities = [np.array(x) for x in itertools.product([0, 1], repeat=4) if sum(x) == 2]
    optimum = min(float(prices @ x) for x in possibilities)
    result = optimize_schedule([0] * 4, prices, [task()], 4, 4)
    assert result["optimized_objective_eur"] == pytest.approx(optimum)


def test_windows_shared_capacity_and_peak_constraint():
    tasks = [task(1.5, 4, 0, 3), task(1, 4, 1, 4, "B")]
    result = optimize_schedule([0.5] * 4, [4, 1, 2, 3], tasks, 4, 6)
    assert result["feasible"]
    for label in ["baseline", "optimized"]:
        allocation = result[f"{label}_task_allocations"]
        assert allocation["A"][3] == 0
        assert allocation["B"][0] == 0
        assert sum(allocation["A"]) == pytest.approx(1.5)
        assert sum(allocation["B"]) == pytest.approx(1)
        assert max(result[f"{label}_flexible_kwh"]) <= 1 + 1e-7
        assert max(result[f"{label}_kwh"]) * 4 <= 6 + 1e-7


def test_baseline_joint_solver_handles_overlapping_deadlines():
    # A naive first-task greedy baseline fills slot 0 and makes B impossible.
    result = optimize_schedule([0, 0], [2, 1], [task(1, 4, 0, 2), task(1, 4, 0, 1, "B")], 4, 4)
    assert result["feasible"]
    assert result["baseline_task_allocations"]["B"] == pytest.approx([1, 0])
    assert result["baseline_task_allocations"]["A"] == pytest.approx([0, 1])


@pytest.mark.parametrize(
    "tasks,background,shared,peak",
    [
        ([task(5)], [0] * 4, 4, 4),
        ([task(1, 0)], [0] * 4, 4, 4),
        ([task(1, 4, 1, 1)], [0] * 4, 4, 4),
        ([task(1)], [2] * 4, 4, 4),
        ([task(1)], [0] * 4, 0, 4),
    ],
)
def test_infeasible_without_relaxation(tasks, background, shared, peak):
    result = optimize_schedule(background, 0.1, tasks, shared, peak)
    assert not result["feasible"]
    assert result["status"] == "infeasible"
    assert "optimized_kwh" not in result


def test_flat_price_and_zero_flexibility_have_no_artificial_savings():
    flat = simulate_scenario([1] * 4, 0.1, [task()], 4, 8)
    assert flat["cost_savings_eur"] == 0
    assert flat["energy_savings_kwh"] == 0
    assert flat["emissions_difference_kg"] == 0
    empty = simulate_scenario([1] * 4, [4, 3, 2, 1], [], 4, 8)
    assert empty["baseline_kwh"] == empty["optimized_kwh"]
    assert empty["cost_savings_eur"] == 0
    assert empty["peak_reduction_kw"] == 0


def test_constant_emissions_and_time_varying_assumptions():
    constant = simulate_scenario([0] * 4, [4, 3, 1, 2], [task()], 4, 8, emissions_kg_per_kwh=0.4)
    assert constant["emissions_difference_kg"] == 0
    varying = simulate_scenario(
        [0] * 4, [4, 3, 1, 2], [task()], 4, 8, emissions_kg_per_kwh=[0.1, 0.1, 0.8, 0.8]
    )
    assert varying["emissions_difference_kg"] == pytest.approx(-1.4)
    assert varying["energy_savings_kwh"] == 0


def test_fractional_lp_and_energy_cost_objective():
    result = optimize_schedule([0, 0], [0.4, 0.1], [task(0.7, 2, 0, 2)], 2, 2)
    assert result["optimized_flexible_kwh"] == pytest.approx([0.2, 0.5])
    assert result["optimized_objective_eur"] == pytest.approx(0.13)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"background_kwh": [-1, 1]},
        {"background_kwh": [float("nan"), 1]},
        {"prices_eur_kwh": [-1, 1]},
        {"shared_capacity_kw": -1},
        {"peak_limit_kw": -1},
        {"interval_hours": 0},
        {"tasks": [task(-1, end=2)]},
        {"tasks": [task(start=-1, end=2)]},
        {"tasks": [task(end=3)]},
        {"tasks": [task(start=0.5, end=2)]},
        {"tasks": [task(end=2), task(end=2)]},
    ],
)
def test_invalid_inputs_rejected(kwargs):
    inputs = dict(background_kwh=[0, 0], prices_eur_kwh=[1, 2], tasks=[])
    inputs.update(kwargs)
    with pytest.raises(ValueError):
        optimize_schedule(**inputs)


def test_scenario_multiplier_and_tariff():
    result = simulate_scenario([1, 2], 0.1, [], 10, 20, demand_multiplier=2)
    assert result["metrics"]["optimized"]["total_energy_kwh"] == 6
    assert result["metrics"]["optimized"]["peak_kw"] == 16
    assert len(tariff_profile()) == 96
    assert tariff_profile()[32] == 0.22
    assert tariff_profile()[80] == 0.08
    with pytest.raises(ValueError):
        simulate_scenario([1], 0.1, [], demand_multiplier=-1)
    with pytest.raises(ValueError):
        simulate_scenario([1], 0.1, [], emissions_kg_per_kwh=-1)


@pytest.mark.parametrize("multiplier", [0.0, 0.8, 1.0, 1.2, 100.0])
def test_results_export_as_strict_json_including_infeasible(multiplier):
    result = simulate_scenario(np.full(96, 5.0), tariff_profile(),
                               demand_multiplier=multiplier,
                               emissions_kg_per_kwh=np.full(96, 0.4))
    restored = json.loads(json.dumps(result, allow_nan=False))
    assert restored["feasible"] == result["feasible"]
    if multiplier == 100.0:
        assert restored["status"] == "infeasible"
    else:
        assert restored["status"] == "optimal"
