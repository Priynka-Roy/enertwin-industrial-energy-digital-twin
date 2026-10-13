"""Backtest metrics and finite-sample empirical residual intervals."""

import numpy as np


def scores(actual, predicted, peak_threshold=None):
    a, p = np.asarray(actual), np.asarray(predicted)
    error = p - a
    denominator = np.abs(a) + np.abs(p)
    smape = np.divide(
        200 * np.abs(error),
        denominator,
        out=np.zeros_like(error, dtype=float),
        where=denominator > 0,
    )
    result = dict(
        MAE=float(np.mean(np.abs(error))),
        RMSE=float(np.sqrt(np.mean(error**2))),
        sMAPE=float(smape.mean()),
        bias=float(error.mean()),
        n=len(a),
    )
    if peak_threshold is not None:
        mask = a >= peak_threshold
        result["peak_MAE"] = float(np.abs(error[mask]).mean()) if mask.any() else None
    return result


def residual_quantile(residuals, level):
    values = np.asarray(residuals)
    n = values.shape[0]
    rank = min(n, int(np.ceil((n + 1) * level)))
    return np.sort(np.abs(values), axis=0)[rank - 1]


def interval_stats(actual, lower, upper):
    covered = (actual >= lower) & (actual <= upper)
    return {
        "coverage": float(covered.mean()),
        "mean_width": float(np.mean(upper - lower)),
        "whole_day_coverage": float(covered.reshape(-1, 96).all(axis=1).mean()),
    }
