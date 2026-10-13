"""Finite illustrative demand paths built from completed historical residual days."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def generate_scenarios(
    point: Any,
    residual_blocks: Any,
    residual_origins: Any,
    origin: Any,
    n_scenarios: int = 12,
    strength: float = 1.0,
    seed: int = 42,
) -> dict[str, Any]:
    """Resample signed, intact 96-slot error blocks available at the decision time.

    This finite set is a stress experiment, not calibrated probabilities or a
    guarantee about future demand. No independently sampled interval bounds are
    stitched into paths. The final stress path uses positive errors at 1.5× the
    requested strength and is explicitly synthetic.
    """
    forecast = np.asarray(point, dtype=float)
    blocks = np.asarray(residual_blocks, dtype=float)
    if forecast.shape != (96,) or not np.isfinite(forecast).all() or (forecast < 0).any():
        raise ValueError("point must contain 96 finite nonnegative kWh values")
    if blocks.ndim != 2 or blocks.shape[1] != 96 or not np.isfinite(blocks).all():
        raise ValueError("residual_blocks must be a finite N×96 array")
    dates = pd.DatetimeIndex(pd.to_datetime(residual_origins))
    decision_time = pd.Timestamp(origin)
    if len(dates) != len(blocks) or dates.hasnans or pd.isna(decision_time):
        raise ValueError("Each residual block must have a valid origin")
    if dates.has_duplicates:
        raise ValueError("Residual origins must be unique")
    if not isinstance(n_scenarios, (int, np.integer)) or isinstance(n_scenarios, bool) or n_scenarios < 4:
        raise ValueError("n_scenarios must be an integer >= 4")
    if not np.isfinite(strength) or strength < 0:
        raise ValueError("strength must be finite and nonnegative")
    if not isinstance(seed, (int, np.integer)) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    try:
        eligible = dates + pd.Timedelta(days=1) <= decision_time
    except TypeError as exc:
        raise ValueError("Residual and decision origins must have consistent timezones") from exc
    indices = np.flatnonzero(eligible)
    if len(indices) == 0:
        raise ValueError("No completed historical residual days are available at origin")
    # Stable sorting makes ties and seeded samples reproducible across input order.
    indices = indices[np.argsort(dates[indices].asi8, kind="stable")]
    ranked = indices[np.argsort(blocks[indices].sum(axis=1), kind="stable")]
    sampled = np.random.default_rng(seed).choice(indices, size=n_scenarios - 4, replace=True)
    chosen = [int(ranked[0]), int(ranked[-1]), *map(int, sampled)]
    profiles = [forecast.tolist()]
    labels = ["Central point forecast"]
    sources: list[str | None] = [None]
    kinds = ["central"]
    for j, index in enumerate(chosen):
        profiles.append(np.maximum(forecast + strength * blocks[index], 0).tolist())
        labels.append(
            "Observed low-energy residual block" if j == 0 else
            "Observed high-energy residual block" if j == 1 else
            f"Resampled historical residual block {j - 1}"
        )
        sources.append(dates[index].isoformat())
        kinds.append("historical_block")
    stress_index = int(ranked[-1])
    profiles.append(np.maximum(forecast + 1.5 * strength * np.maximum(blocks[stress_index], 0), 0).tolist())
    labels.append("Synthetic positive-error stress (1.5×)")
    sources.append(dates[stress_index].isoformat())
    kinds.append("synthetic_stress")
    return {
        "profiles": profiles,
        "labels": labels,
        "source_origins": sources,
        "kinds": kinds,
        "central_index": 0,
        "origin": decision_time.isoformat(),
        "strength": float(strength),
        "seed": int(seed),
        "eligible_blocks": int(len(indices)),
        "excluded_incomplete_or_future_blocks": int(len(blocks) - len(indices)),
        "residual_definition": "actual minus point prediction; signed blocks are not centered",
        "interpretation": "Finite illustrative scenarios without assigned probabilities; not forecast intervals or future feasibility guarantees.",
        "clipping": "Negative constructed demand is clipped to zero kWh.",
    }
