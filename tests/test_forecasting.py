import numpy as np
import pandas as pd
import pytest
from enertwin.forecasting import features, predict
from enertwin.evaluation import residual_quantile, interval_stats, scores
from enertwin.data import parse_timestamps, load_data
from pathlib import Path


def history():
    return pd.Series(
        np.arange(96 * 12, dtype=float),
        index=pd.date_range("2018-01-01 00:15", periods=96 * 12, freq="15min"),
    )


def test_fixed_origin_features_ignore_all_future_observations():
    s = history()
    origin = pd.Timestamp("2018-01-09")
    before, t = features(s, origin)
    s.loc[s.index > origin] = 999999
    after, _ = features(s, origin)
    np.testing.assert_array_equal(before, after)
    assert len(t) == 96 and t[-1] == origin + pd.Timedelta(days=1)


def test_seasonal_alignment_and_origin_boundary():
    s = history()
    o = pd.Timestamp("2018-01-09")
    x, t = features(s, o)
    np.testing.assert_array_equal(x[:, 0], s.reindex(t - pd.Timedelta(days=1)))
    np.testing.assert_array_equal(x[:, 1], s.reindex(t - pd.Timedelta(days=7)))
    assert x[-1, 0] == s[o]
    for model, col in [("daily_naive", 0), ("weekly_naive", 1), ("last_naive", 2)]:
        np.testing.assert_array_equal(predict(s, o, model)[1], x[:, col])


def test_insufficient_history_rejected():
    with pytest.raises(ValueError):
        features(history(), "2018-01-03")


def test_midnight_repairs_only_source_sequence_defect():
    values = pd.Series(["01/01/2018 23:45", "01/01/2018 00:00", "02/01/2018 00:15"])
    parsed = parse_timestamps(values)
    assert parsed[1] == pd.Timestamp("2018-01-02")
    ordinary = parse_timestamps(pd.Series(["01/01/2018 23:45", "02/01/2018 00:00"]))
    assert ordinary[1] == pd.Timestamp("2018-01-02")
    explicit = parse_timestamps(pd.Series(["01/01/2018 24:00"]))
    assert explicit[0] == pd.Timestamp("2018-01-02")


def test_dataset_quality():
    p = Path("data/raw/Steel_industry_data.csv")
    if not p.exists():
        pytest.skip("Source download not requested in lightweight CI")
    frame, audit = load_data(p)
    assert len(frame) == 35040 and audit["same_date_midnight_corrections"] == 365
    assert audit["calendar_interval_start_day_disagreements"] == 0
    assert np.isclose(frame.Usage_kWh.sum(), 959636.71)


def test_quantile_finite_sample_rank_and_coverage():
    values = np.arange(1, 31)
    assert residual_quantile(values, 0.9) == 28
    assert residual_quantile(values, 0.8) == 25
    a = np.ones(192)
    lower = np.zeros(192)
    upper = np.ones(192)
    assert interval_stats(a, lower, upper)["whole_day_coverage"] == 1
    upper[0] = 0
    assert interval_stats(a, lower, upper)["whole_day_coverage"] == 0.5


def test_metrics_hand_calculation_zero_smape():
    metric = scores(np.array([0.0, 2.0]), np.array([0.0, 4.0]))
    assert metric["MAE"] == 1 and metric["bias"] == 1
    assert np.isclose(metric["RMSE"], np.sqrt(2))


@pytest.mark.parametrize(
    "defect", ["gap", "duplicate", "negative", "nonfinite", "power_factor", "missing_column"]
)
def test_validation_rejects_invalid_telemetry(defect):
    from enertwin.data import validate_data

    sample = pd.read_parquet("data/demo/history.parquet").iloc[:4].copy()
    if defect == "gap":
        sample = sample.drop(sample.index[1])
    elif defect == "duplicate":
        sample.index = [sample.index[0]] * 4
        sample.index = pd.DatetimeIndex(sample.index)
    elif defect == "negative":
        sample.iloc[0, sample.columns.get_loc("Usage_kWh")] = -1
    elif defect == "nonfinite":
        sample.iloc[0, sample.columns.get_loc("Usage_kWh")] = np.nan
    elif defect == "power_factor":
        sample.iloc[0, sample.columns.get_loc("Lagging_Current_Power_Factor")] = 101
    else:
        sample = sample.drop(columns="Usage_kWh")
    with pytest.raises(ValueError):
        validate_data(sample)
