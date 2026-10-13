"""Causal residual calibration with daily scores and pooled six-hour maxima."""

from __future__ import annotations

import numpy as np
import pandas as pd
from enertwin.evaluation import residual_quantile

METHODS = ("v1_fixed", "fixed_pooled", "rolling_pooled")


def eligible_blocks(
    blocks: np.ndarray,
    origins: pd.DatetimeIndex,
    origin: pd.Timestamp | str,
    window: int | None = None,
) -> tuple[np.ndarray, pd.DatetimeIndex]:
    values = np.asarray(blocks, dtype=float)
    dates = pd.DatetimeIndex(origins)
    if values.ndim != 2 or values.shape[1] != 96 or len(dates) != len(values):
        raise ValueError("Residual blocks must have 96 horizons and matching origins")
    if (
        not np.isfinite(values).all()
        or dates.hasnans
        or dates.has_duplicates
        or not dates.is_monotonic_increasing
    ):
        raise ValueError("Finite residuals and unique chronological origins required")
    decision_origin = pd.Timestamp(origin)
    if pd.isna(decision_origin):
        raise ValueError("A valid decision origin is required")
    mask = dates + pd.Timedelta(days=1) <= decision_origin
    values, dates = values[mask], dates[mask]
    if window is not None:
        if not isinstance(window, (int, np.integer)) or isinstance(window, bool) or window < 1:
            raise ValueError("Window must be positive")
        values, dates = values[-window:], dates[-window:]
    return values, dates


def calibrated_bands(
    point,
    blocks,
    origins,
    origin,
    method="rolling_pooled",
    levels=(0.8, 0.9),
    window=60,
    bin_size=24,
    min_blocks=20,
):
    """Pooled methods calibrate each day's maximum residual within each 6h bin.

    Scores are daily blocks, not independent quarter-hour observations. Observed
    empirical pointwise/bin/day coverage must be reported; dependence invalidates
    an exact conformal guarantee. All residual profiles must have completed.
    """
    point = np.asarray(point, dtype=float)
    if point.shape != (96,) or not np.isfinite(point).all() or (point < 0).any():
        raise ValueError("Point forecast must contain 96 finite nonnegative values")
    if (
        method not in METHODS
        or not isinstance(bin_size, (int, np.integer))
        or isinstance(bin_size, bool)
        or bin_size < 1
        or 96 % bin_size
    ):
        raise ValueError("Unknown method or invalid pooling bin")
    values, dates = eligible_blocks(
        blocks, origins, origin, window if method == "rolling_pooled" else None
    )
    if (
        not isinstance(min_blocks, (int, np.integer))
        or isinstance(min_blocks, bool)
        or min_blocks < 1
    ):
        raise ValueError("Minimum block count must be a positive integer")
    if len(values) < min_blocks:
        raise ValueError("Insufficient completed calibration days")
    scores = (
        np.abs(values)
        if method == "v1_fixed"
        else np.abs(values).reshape(len(values), 96 // bin_size, bin_size).max(axis=2)
    )
    result = {
        "n_blocks": len(values),
        "last_residual_completion": str(dates[-1] + pd.Timedelta(days=1)),
        "method": method,
    }
    for level in levels:
        if not 0 < level < 1:
            raise ValueError("Coverage level must lie in (0,1)")
        q = residual_quantile(scores, level)
        if method != "v1_fixed":
            q = np.repeat(q, bin_size)
        suffix = str(round(level * 100))
        result["lower" + suffix] = np.maximum(0, point - q)
        result["upper" + suffix] = point + q
    return result


def band_summary(table: pd.DataFrame, level: int = 90) -> dict[str, float]:
    table = table.sort_values(["origin", "horizon"])
    if (
        table.empty
        or not table.groupby("origin")
        .horizon.apply(lambda h: h.tolist() == list(range(1, 97)))
        .all()
    ):
        raise ValueError("Coverage requires complete unique 96-step origin blocks")
    fields = table[["actual", "lower" + str(level), "upper" + str(level)]].to_numpy()
    if not np.isfinite(fields).all() or (fields[:, 1] > fields[:, 2]).any():
        raise ValueError("Coverage requires finite, ordered interval bounds")
    actual = table.actual.to_numpy()
    lower = table["lower" + str(level)].to_numpy()
    upper = table["upper" + str(level)].to_numpy()
    covered = (actual >= lower) & (actual <= upper)
    widths = upper - lower
    daily_width = table.assign(width=widths).groupby("origin").width.mean()
    return {
        "coverage": float(covered.mean()),
        "mean_width": float(widths.mean()),
        "whole_day_coverage": float(covered.reshape(-1, 96).all(axis=1).mean()),
        "six_hour_block_coverage": float(covered.reshape(-1, 24).all(axis=1).mean()),
        "daily_width_std": float(daily_width.std(ddof=0)),
        "max_adjacent_daily_width_change": float(daily_width.diff().abs().max())
        if len(daily_width) > 1
        else 0.0,
    }
