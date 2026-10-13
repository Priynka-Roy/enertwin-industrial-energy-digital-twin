"""Continuous, interruptible hypothetical-workload scheduling with SciPy HiGHS."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, kron


def default_tasks(n_slots: int = 96) -> list[dict[str, Any]]:
    """Illustrative additional tasks; these are not inferred factory equipment."""
    return [
        {
            "name": "Flexible workload A",
            "energy_kwh": 120.0,
            "max_power_kw": 40.0,
            "start_slot": 0,
            "end_slot": n_slots,
        },
        {
            "name": "Flexible workload B",
            "energy_kwh": 80.0,
            "max_power_kw": 40.0,
            "start_slot": n_slots // 4,
            "end_slot": 3 * n_slots // 4,
        },
    ]


def _vector(value: Any, n: int | None, name: str, nonnegative: bool = True) -> np.ndarray:
    result = np.asarray(value, dtype=float)
    if result.ndim == 0 and n is not None:
        result = np.full(n, float(result))
    if result.ndim != 1 or len(result) == 0 or (n is not None and len(result) != n):
        raise ValueError(f"{name} must have exactly {n or 'a nonzero number of'} intervals")
    if not np.isfinite(result).all() or (nonnegative and (result < 0).any()):
        raise ValueError(f"{name} must contain finite nonnegative values")
    return result


def optimize_schedule(
    background_kwh: Sequence[float],
    prices_eur_kwh: Sequence[float] | float,
    tasks: list[dict[str, Any]] | None = None,
    shared_capacity_kw: float = 80.0,
    peak_limit_kw: float = 500.0,
    interval_hours: float = 0.25,
) -> dict[str, Any]:
    """Minimize energy charges under identical baseline and optimized constraints.

    Each variable is task energy (kWh) in one interval. Tasks may split across
    intervals; minimum run length, start-up costs and precedence are not modeled.
    Invalid inputs raise ValueError; valid but impossible scenarios return feasible=False.
    """
    background = _vector(background_kwh, None, "background_kwh")
    n = len(background)
    prices = _vector(prices_eur_kwh, n, "prices_eur_kwh")
    for name, value in [
        ("shared_capacity_kw", shared_capacity_kw),
        ("peak_limit_kw", peak_limit_kw),
        ("interval_hours", interval_hours),
    ]:
        if not np.isfinite(value) or value < 0 or (name == "interval_hours" and value == 0):
            raise ValueError(
                f"{name} must be finite and {'positive' if name == 'interval_hours' else 'nonnegative'}"
            )
    tasks = default_tasks(n) if tasks is None else tasks
    validated = []
    names = set()
    for task in tasks:
        name = str(task["name"])
        if not name or name in names:
            raise ValueError("Task names must be nonempty and unique")
        names.add(name)
        energy, power = float(task["energy_kwh"]), float(task["max_power_kw"])
        start, end = task["start_slot"], task["end_slot"]
        if not np.isfinite([energy, power]).all() or min(energy, power) < 0:
            raise ValueError("Task energy and maximum power must be finite and nonnegative")
        if not isinstance(start, (int, np.integer)) or not isinstance(end, (int, np.integer)):
            raise ValueError("Task window boundaries must be integer slots")
        if not 0 <= start <= end <= n:
            raise ValueError("Task windows must satisfy 0 <= start <= end <= horizon")
        validated.append(
            dict(
                name=name,
                energy_kwh=energy,
                max_power_kw=power,
                start_slot=int(start),
                end_slot=int(end),
            )
        )
    result: dict[str, Any] = {
        "feasible": False,
        "status": "infeasible",
        "message": "",
        "tasks": validated,
        "interval_hours": float(interval_hours),
        "background_kwh": background.tolist(),
        "prices_eur_kwh": prices.tolist(),
        "shared_capacity_kw": float(shared_capacity_kw),
        "peak_limit_kw": float(peak_limit_kw),
        "solver": "SciPy HiGHS linear programming",
    }
    headroom = peak_limit_kw * interval_hours - background
    if (headroom < -1e-8).any():
        result["message"] = (
            "Fixed background demand exceeds the peak limit; constraints were not relaxed."
        )
        return result
    headroom = np.maximum(headroom, 0.0)
    m = len(validated)
    bounds = []
    for task in validated:
        bounds.extend(
            [
                (
                    0.0,
                    task["max_power_kw"] * interval_hours
                    if task["start_slot"] <= slot < task["end_slot"]
                    else 0.0,
                )
                for slot in range(n)
            ]
        )
    if m:
        equality = kron(csr_matrix(np.eye(m)), csr_matrix(np.ones((1, n))), format="csr")
        capacity = kron(csr_matrix(np.ones((1, m))), csr_matrix(np.eye(n)), format="csr")
        rhs = np.minimum(shared_capacity_kw * interval_hours, headroom)
        kwargs = dict(
            A_eq=equality,
            b_eq=[task["energy_kwh"] for task in validated],
            A_ub=capacity,
            b_ub=rhs,
            bounds=bounds,
            method="highs",
        )
        baseline = linprog(np.tile(np.arange(n, dtype=float), m), **kwargs)
        if not baseline.success:
            result["message"] = baseline.message
            result["solver_status"] = int(baseline.status)
            return result
        optimized = linprog(np.tile(prices, m), **kwargs)
        if not optimized.success:
            result.update(
                status="solver_error",
                message=optimized.message,
                solver_status=int(optimized.status),
            )
            return result
        baseline_x = np.maximum(baseline.x.reshape(m, n), 0)
        optimized_x = np.maximum(optimized.x.reshape(m, n), 0)
    else:
        baseline_x = optimized_x = np.zeros((0, n))
    checks = {}
    metrics = {}
    for label, allocation in [("baseline", baseline_x), ("optimized", optimized_x)]:
        flexible = allocation.sum(axis=0)
        total = background + flexible
        task_errors = [
            abs(allocation[j].sum() - task["energy_kwh"]) for j, task in enumerate(validated)
        ]
        window_ok = all(
            np.all(allocation[j, : task["start_slot"]] <= 1e-7)
            and np.all(allocation[j, task["end_slot"] :] <= 1e-7)
            for j, task in enumerate(validated)
        )
        check = {
            "workload_conserved": bool(max(task_errors, default=0.0) <= 1e-6),
            "windows_respected": bool(window_ok),
            "task_capacity_respected": all(
                np.all(allocation[j] <= task["max_power_kw"] * interval_hours + 1e-7)
                for j, task in enumerate(validated)
            ),
            "shared_capacity_respected": bool(
                np.all(flexible <= shared_capacity_kw * interval_hours + 1e-7)
            ),
            "peak_limit_respected": bool(np.all(total <= peak_limit_kw * interval_hours + 1e-7)),
            "nonnegative": bool(np.all(allocation >= -1e-7)),
            "energy_balance": bool(
                np.isclose(total.sum(), background.sum() + sum(t["energy_kwh"] for t in validated))
            ),
        }
        checks[label] = check
        metrics[label] = {
            "total_energy_kwh": float(total.sum()),
            "flexible_energy_kwh": float(flexible.sum()),
            "cost_eur": float(total @ prices),
            "flexible_cost_eur": float(flexible @ prices),
            "peak_kw": float(total.max() / interval_hours),
        }
        result[f"{label}_kwh"] = total.tolist()
        result[f"{label}_flexible_kwh"] = flexible.tolist()
        result[f"{label}_task_allocations"] = {
            task["name"]: allocation[j].tolist() for j, task in enumerate(validated)
        }
    verified = all(all(check.values()) for check in checks.values())
    savings = metrics["baseline"]["cost_eur"] - metrics["optimized"]["cost_eur"]
    result.update(
        feasible=verified,
        status="optimal" if verified else "verification_failed",
        message="Optimal feasible schedule; independently verified constraints."
        if verified
        else "Constraint verification failed.",
        solver_status=0,
        constraint_verification=checks,
        metrics=metrics,
        baseline_objective_eur=metrics["baseline"]["cost_eur"],
        optimized_objective_eur=metrics["optimized"]["cost_eur"],
        cost_savings_eur=0.0 if abs(savings) < 1e-8 else float(savings),
        energy_savings_kwh=0.0,
        peak_reduction_kw=float(metrics["baseline"]["peak_kw"] - metrics["optimized"]["peak_kw"]),
    )
    return result
