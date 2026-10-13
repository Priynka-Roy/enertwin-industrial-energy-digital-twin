"""Independent numerical consistency checks for the portable backtest artifacts."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from enertwin.evaluation import scores, residual_quantile

ROOT = Path(__file__).resolve().parents[1]


def test_backtest_partition_targets_metrics_and_calibration_match():
    frame = pd.read_parquet(ROOT / "data/demo/forecasts.parquet")
    history = pd.read_parquet(ROOT / "data/demo/history.parquet")
    metrics = json.loads((ROOT / "artifacts/metrics.json").read_text())
    assert set(frame.model) == {
        "last_naive",
        "daily_naive",
        "weekly_naive",
        "ridge",
        "hist_gradient_boosting",
    }
    expected = frame.origin + pd.to_timedelta(frame.horizon * 15, unit="min")
    pd.testing.assert_series_equal(frame.target_timestamp, expected, check_names=False)
    np.testing.assert_array_equal(frame.actual, history.Usage_kWh.reindex(frame.target_timestamp))
    for model, group in frame.groupby("model", sort=False):
        cal = group[group.partition == "calibration"]
        test = group[group.partition == "test"]
        assert cal.origin.nunique() == 30 and test.origin.nunique() == 92
        assert cal.target_timestamp.max() <= test.origin.min()
        computed = scores(test.actual, test.prediction, metrics["peak_threshold_kwh"])
        for key, value in computed.items():
            assert np.isclose(value, metrics["test"][model][key])
        errors = (cal.actual - cal.prediction).to_numpy().reshape(30, 96)
        for level in [0.8, 0.9]:
            suffix = str(int(100 * level))
            q = residual_quantile(errors, level)
            np.testing.assert_allclose(test["upper" + suffix], test.prediction + np.tile(q, 92))
            assert (test["lower" + suffix] >= 0).all()
            assert (test["lower" + suffix] <= test.prediction).all()
            coverage = (
                (test.actual >= test["lower" + suffix]) & (test.actual <= test["upper" + suffix])
            ).mean()
            assert np.isclose(coverage, metrics["intervals"][model][suffix]["coverage"])
    winner = min(metrics["validation"], key=lambda m: metrics["validation"][m]["MAE"])
    assert metrics["selected_model"] == winner


def test_scenario_artifact_energy_and_feasibility():
    cases = json.loads((ROOT / "artifacts/scenarios.json").read_text())
    assert not cases["infeasible_peak"]["feasible"]
    for name in ["flat_tariff", "time_of_use", "peak_constrained"]:
        case = cases[name]
        assert case["feasible"]
        assert all(case["constraint_verification"]["baseline"].values())
        assert all(case["constraint_verification"]["optimized"].values())
        b, o = case["metrics"]["baseline"], case["metrics"]["optimized"]
        assert np.isclose(b["total_energy_kwh"], o["total_energy_kwh"])
        assert np.isclose(b["emissions_kg"], o["emissions_kg"])
        assert o["cost_eur"] <= b["cost_eur"] + 1e-8
    assert np.isclose(cases["flat_tariff"]["cost_savings_eur"], 0)
    assert cases["peak_constrained"]["metrics"]["baseline"]["peak_kw"] <= 190 + 1e-8
    outcomes = {c["result"]["feasible"] for c in cases["sensitivity"]}
    assert outcomes == {True, False}


def test_generated_artifact_hashes_match_manifest():
    import hashlib

    manifest = json.loads((ROOT / "reports/artifact_manifest.json").read_text())
    for name, expected in manifest["sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
