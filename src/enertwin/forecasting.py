"""Direct 96-step forecasts with features available at a fixed midnight origin."""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "previous_day",
    "previous_week",
    "last",
    "day_mean",
    "day_std",
    "day_max",
    "week_mean",
    "week_std",
    "hour_sin",
    "hour_cos",
    "weekday_sin",
    "weekday_cos",
    "weekend",
    "horizon",
]
MODELS = ["last_naive", "daily_naive", "weekly_naive", "ridge", "hist_gradient_boosting"]


def features(series, origin):
    origin = pd.Timestamp(origin)
    history = series.loc[:origin]
    if len(history) < 672:
        raise ValueError("Seven full days of history required")
    targets = pd.date_range(origin + pd.Timedelta(minutes=15), periods=96, freq="15min")
    calendar = targets - pd.Timedelta(minutes=15)
    day, week = history.iloc[-96:], history.iloc[-672:]
    hour = calendar.hour + calendar.minute / 60
    x = np.column_stack(
        [
            history.reindex(targets - pd.Timedelta(days=1)),
            history.reindex(targets - pd.Timedelta(days=7)),
            np.full(96, history.iloc[-1]),
            np.full(96, day.mean()),
            np.full(96, day.std()),
            np.full(96, day.max()),
            np.full(96, week.mean()),
            np.full(96, week.std()),
            np.sin(2 * np.pi * hour / 24),
            np.cos(2 * np.pi * hour / 24),
            np.sin(2 * np.pi * calendar.dayofweek / 7),
            np.cos(2 * np.pi * calendar.dayofweek / 7),
            (calendar.dayofweek >= 5).astype(float),
            np.arange(1, 97) / 96,
        ]
    )
    if not np.isfinite(x).all():
        raise ValueError("History missing a required seasonal lag")
    return x, targets


def design(series, origins):
    blocks = [features(series, o) for o in origins]
    return np.concatenate([b[0] for b in blocks]), np.concatenate(
        [series.reindex(b[1]).to_numpy() for b in blocks]
    )


def estimator(model, params):
    if model == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=params["alpha"]))
    return HistGradientBoostingRegressor(
        max_iter=200, early_stopping=False, random_state=42, **params
    )


def predict(series, origin, model, fitted=None):
    x, timestamps = features(series, origin)
    if model == "last_naive":
        prediction = x[:, 2]
    elif model == "daily_naive":
        prediction = x[:, 0]
    elif model == "weekly_naive":
        prediction = x[:, 1]
    else:
        prediction = fitted.predict(x)
    return timestamps, np.maximum(0, prediction)
