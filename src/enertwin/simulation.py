"""Explicitly assumed scenarios layered on a fixed observational forecast."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from enertwin.optimization import _vector, optimize_schedule


def tariff_profile(
    n_slots: int = 96,
    kind: str = "time_of_use",
    flat_price: float = 0.12,
    peak_price: float = 0.22,
    offpeak_price: float = 0.08,
) -> list[float]:
    """Assumed tariffs for a horizon starting at midnight; no real-company tariff claim."""
    if n_slots <= 0 or not isinstance(n_slots, int):
        raise ValueError("n_slots must be a positive integer")
    if (
        not np.isfinite([flat_price, peak_price, offpeak_price]).all()
        or min(flat_price, peak_price, offpeak_price) < 0
    ):
        raise ValueError("Prices must be finite and nonnegative")
    if kind == "flat":
        return [float(flat_price)] * n_slots
    if kind != "time_of_use":
        raise ValueError("Tariff kind must be flat or time_of_use")
    hour = np.arange(n_slots) * 24 / n_slots
    return np.where((hour >= 8) & (hour < 20), peak_price, offpeak_price).tolist()


def simulate_scenario(
    background_kwh: Sequence[float],
    prices_eur_kwh: Sequence[float] | float,
    tasks: list[dict[str, Any]] | None = None,
    shared_capacity_kw: float = 80.0,
    peak_limit_kw: float = 500.0,
    demand_multiplier: float = 1.0,
    emissions_kg_per_kwh: Sequence[float] | float = 0.4,
    interval_hours: float = 0.25,
) -> dict[str, Any]:
    """Compare schedules for NEW assumed workload added to assumed fixed demand.

    Scaling is scenario arithmetic, not a learned causal response or a plant twin.
    A constant emissions factor cannot create reductions through rescheduling alone.
    """
    background = _vector(background_kwh, None, "background_kwh")
    if not np.isfinite(demand_multiplier) or demand_multiplier < 0:
        raise ValueError("demand_multiplier must be finite and nonnegative")
    emissions = _vector(emissions_kg_per_kwh, len(background), "emissions_kg_per_kwh")
    result = optimize_schedule(
        background * demand_multiplier,
        prices_eur_kwh,
        tasks,
        shared_capacity_kw,
        peak_limit_kw,
        interval_hours,
    )
    result["assumptions"] = {
        "demand_multiplier": float(demand_multiplier),
        "emissions_kg_per_kwh": emissions.tolist(),
        "background": "Observed-profile or forecast demand assumed fixed; no controllable fraction inferred.",
        "workloads": "Additional hypothetical interruptible workloads, not observed production decisions.",
        "financial": "Modeled energy charges only; no verified factory tariff, demand charge or realized savings.",
        "emissions": "Assumed factors, not observed plant or verified marginal emissions.",
    }
    if result["feasible"]:
        for label in ["baseline", "optimized"]:
            result["metrics"][label]["emissions_kg"] = float(
                np.asarray(result[f"{label}_kwh"]) @ emissions
            )
        delta = (
            result["metrics"]["baseline"]["emissions_kg"]
            - result["metrics"]["optimized"]["emissions_kg"]
        )
        result["emissions_difference_kg"] = 0.0 if abs(delta) < 1e-8 else float(delta)
    return result
