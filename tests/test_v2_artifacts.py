"""V1 identity, causal residual use and numerical V2 experiment consistency."""

from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
from enertwin.uncertainty import band_summary

ROOT = Path(__file__).resolve().parents[1]


def test_v1_preserved_and_point_forecasts_identical():
    original = json.loads((ROOT / "versions/v1/reports/artifact_manifest.json").read_text())
    for name, digest in original["sha256"].items():
        assert hashlib.sha256((ROOT / "versions/v1" / name).read_bytes()).hexdigest() == digest
    v1 = pd.read_parquet(ROOT / "versions/v1/data/demo/forecasts.parquet")
    v2 = pd.read_parquet(ROOT / "data/demo/v2/forecasts.parquet")
    pd.testing.assert_frame_equal(
        v1[["origin", "target_timestamp", "horizon", "model", "actual", "prediction"]],
        v2[["origin", "target_timestamp", "horizon", "model", "actual", "prediction"]],
    )


def test_v2_bands_causality_coverage_and_identity():
    bands = pd.read_parquet(ROOT / "data/demo/v2/uncertainty.parquet")
    assert (bands.last_residual_completion <= bands.origin).all()
    assert bands.groupby(["model", "method", "origin"]).size().eq(96).all()
    metrics = json.loads((ROOT / "artifacts/v2/uncertainty_metrics.json").read_text())[
        "retrospective"
    ]
    for (model, method), g in bands.groupby(["model", "method"]):
        for level in [80, 90]:
            result = band_summary(g, level)
            for key, value in result.items():
                assert np.isclose(value, metrics[model][method]["intervals"][str(level)][key])
    selected = json.loads((ROOT / "artifacts/v2/development_selection.json").read_text())
    config = json.loads((ROOT / "configs/v2_experiment.json").read_text())
    keys = []
    for method, details in selected["candidates"].items():
        vals = details["intervals"]
        met = all(
            vals[str(level)]["coverage"] >= level / 100 - config["coverage_tolerance"]
            for level in [80, 90]
        )
        deviation = np.mean([abs(vals[str(level)]["coverage"] - level / 100) for level in [80, 90]])
        width = np.mean([vals[str(level)]["mean_width"] for level in [80, 90]])
        keys.append((0 if met else 1, 0 if met else deviation, width, method))
    assert min(keys)[-1] == selected["selected_method"]


def test_fixed_schedules_and_no_missing_plan_counted_safe():
    table = pd.read_parquet(ROOT / "artifacts/v2/decision_backtest.parquet")
    assert (table.last_source_completion <= table.origin).all()
    feasible = table[table.feasible]
    assert feasible.energy_balance.all()
    np.testing.assert_allclose(feasible.flexible_energy_kwh, 200)
    robust = feasible[feasible.policy == "robust"]
    assert (robust.scenario_violation_count == 0).all()
    unavailable = table[~table.feasible]
    assert unavailable.realized_cost_eur.isna().all()
    assert unavailable.realized_violation_intervals.isna().all()
    assert table.groupby(["origin", "partition", "peak_limit_kw"]).policy.nunique().eq(2).all()


def test_v2_artifact_checksums_match():
    manifest = json.loads((ROOT / "reports/v2/artifact_manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest


def test_diagnostic_tuning_precedes_first_calibration_origin():
    selection = json.loads((ROOT / "artifacts/v2/diagnostic_model_selection.json").read_text())
    config = json.loads((ROOT / "configs/v2_experiment.json").read_text())
    assert pd.Timestamp(selection["last_selection_target"]) <= pd.Timestamp(
        config["development_calibration_start"]
    )
    assert "2018-06-30" in selection["validation"]
    assert set(selection["parameters"]) == {"ridge", "hist_gradient_boosting"}


def test_recorded_frozen_allocations_reproduce_realized_costs_and_violations():
    from enertwin.simulation import tariff_profile

    records = pd.read_parquet(ROOT / "artifacts/v2/decision_backtest.parquet")
    history = pd.read_parquet(ROOT / "versions/v1/data/demo/history.parquet")
    prices = np.asarray(tariff_profile())
    for row in records[records.feasible].itertuples():
        targets = pd.date_range(row.origin + pd.Timedelta(minutes=15), periods=96, freq="15min")
        actual = history.Usage_kWh.reindex(targets).to_numpy()
        schedule = np.asarray(row.flexible_schedule_kwh)
        assert len(schedule) == 96 and np.isclose(schedule.sum(), 200)
        total = actual + schedule
        assert np.isclose(total @ prices, row.realized_cost_eur)
        assert (
            int((total > row.peak_limit_kw * 0.25 + 1e-7).sum()) == row.realized_violation_intervals
        )
        assert np.isclose(total.max() / 0.25, row.realized_peak_kw)
