"""A shared continuous workload schedule feasible across a finite demand set."""
from __future__ import annotations

from typing import Any

import numpy as np

from enertwin.optimization import optimize_schedule


def optimize_robust(
    background_scenarios: Any,
    prices_eur_kwh: Any,
    tasks: list[dict[str, Any]] | None = None,
    shared_capacity_kw: float = 80.0,
    peak_limit_kw: float = 500.0,
    interval_hours: float = 0.25,
) -> dict[str, Any]:
    """Solve the exact finite-scenario robust LP via interval-wise max background.

    All scenarios share one task allocation and deterministic tariffs. Scenario
    background charges are decision-independent, so minimizing flexible charges
    also minimizes either expected or worst-case total charges. No scenario
    probability or artificial CVaR penalty is needed. The envelope enforces all
    supplied peak constraints exactly; it is not an extra synthetic trajectory.
    """
    scenarios = np.asarray(background_scenarios, dtype=float)
    if scenarios.ndim != 2 or not all(scenarios.shape):
        raise ValueError("background_scenarios must be a nonempty S×H array")
    if not np.isfinite(scenarios).all() or (scenarios < 0).any():
        raise ValueError("background_scenarios must contain finite nonnegative kWh values")
    result = optimize_schedule(
        scenarios.max(axis=0), prices_eur_kwh, tasks,
        shared_capacity_kw, peak_limit_kw, interval_hours,
    )
    result.update(
        background_scenarios=scenarios.tolist(),
        scenario_count=int(len(scenarios)),
        method="Exact finite-scenario LP using componentwise maximum background",
        objective_explanation="Deterministic tariffs and fixed scenario backgrounds make flexible-cost, mean-total-cost, and worst-total-cost minimizers identical over the same robust feasible set.",
        guarantee_scope="Constraints verified for supplied scenarios only; unseen demand may violate limits.",
    )
    if not result["feasible"]:
        result["scenario_constraint_verification"] = {}
        result["scenario_metrics"] = {}
        return result
    prices = np.asarray(result["prices_eur_kwh"])
    scenario_metrics = {}
    scenario_checks = {}
    for schedule in ("baseline", "optimized"):
        flex = np.asarray(result[f"{schedule}_flexible_kwh"])
        total = scenarios + flex
        # Task/window/power conservation is independent of background and was
        # checked by the deterministic solver; check every scenario separately.
        common = result["constraint_verification"][schedule]
        scenario_checks[schedule] = [
            {**common,
             "peak_limit_respected": bool(np.all(row <= peak_limit_kw * interval_hours + 1e-7)),
             "energy_balance": bool(np.isclose(row.sum(), background.sum() + flex.sum()))}
            for row, background in zip(total, scenarios, strict=True)
        ]
        scenario_metrics[schedule] = [
            {
                "scenario_index": index,
                "total_energy_kwh": float(row.sum()),
                "flexible_energy_kwh": float(flex.sum()),
                "flexible_cost_eur": float(flex @ prices),
                "cost_eur": float(row @ prices),
                "peak_kw": float(row.max() / interval_hours),
            }
            for index, row in enumerate(total)
        ]
    verified = all(all(check.values()) for checks in scenario_checks.values() for check in checks)
    result.update(
        feasible=verified,
        status="optimal" if verified else "verification_failed",
        scenario_metrics=scenario_metrics,
        scenario_constraint_verification=scenario_checks,
        scenario_cost_summary={
            schedule: {
                "mean_cost_eur": float(np.mean([row["cost_eur"] for row in rows])),
                "worst_cost_eur": float(max(row["cost_eur"] for row in rows)),
                "max_peak_kw": float(max(row["peak_kw"] for row in rows)),
            }
            for schedule, rows in scenario_metrics.items()
        },
    )
    return result
