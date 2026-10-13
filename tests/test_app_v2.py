"""V2 UI artifact pairing and retrospective interval diagnostics."""

import json
import shutil

import pandas as pd
import pytest

from app.main import ROOT, load_artifacts, uncertainty_diagnostics


def test_v2_loader_rejects_partial_bundle(tmp_path):
    (tmp_path / "data/demo/v2").mkdir(parents=True)
    shutil.copy(ROOT / "data/demo/history.parquet", tmp_path / "data/demo/history.parquet")
    pd.DataFrame({"origin": [], "target_timestamp": []}).to_parquet(
        tmp_path / "data/demo/v2/forecasts.parquet"
    )
    with pytest.raises(ValueError, match="published together"):
        load_artifacts(str(tmp_path))


def test_v2_loader_requires_schema_and_uses_paired_metrics(tmp_path):
    (tmp_path / "data/demo/v2").mkdir(parents=True)
    (tmp_path / "artifacts/v2").mkdir(parents=True)
    shutil.copy(ROOT / "data/demo/history.parquet", tmp_path / "data/demo/history.parquet")
    shutil.copy(ROOT / "data/demo/forecasts.parquet", tmp_path / "data/demo/v2/forecasts.parquet")
    path = tmp_path / "artifacts/v2/metrics.json"
    path.write_text(json.dumps({"schema_version": 1}))
    with pytest.raises(ValueError, match="schema_version 2"):
        load_artifacts(str(tmp_path))
    path.write_text(json.dumps({"schema_version": 2, "selected_model": "ridge"}))
    _, forecasts, metrics = load_artifacts(str(tmp_path))
    assert metrics["schema_version"] == 2
    assert metrics["selected_model"] == "ridge"
    assert not forecasts.empty


def test_coverage_diagnostics_preserve_methods_and_observed_strata():
    origin = pd.Timestamp("2018-10-01")
    frame = pd.DataFrame(
        {
            "origin": [origin, origin],
            "model": ["ridge", "ridge"],
            "method": ["fixed_pooled", "rolling_pooled"],
            "horizon": [1, 96],
            "actual": [10.0, 30.0],
            "lower80": [0.0, 0.0],
            "upper80": [20.0, 20.0],
            "lower90": [0.0, 0.0],
            "upper90": [40.0, 40.0],
        }
    )
    diagnostics = uncertainty_diagnostics(frame, 25.0)
    summary = diagnostics["method"]
    assert len(summary) == 4
    rolling80 = summary.loc[
        (summary.method == "rolling_pooled") & (summary.nominal_percent == 80)
    ].iloc[0]
    assert rolling80.coverage_percent == 0.0
    assert rolling80.mean_width_kwh == 20.0
    assert set(diagnostics["Demand stratum"]["Demand stratum"]) == {
        "High demand (training threshold)",
        "Other demand",
    }


def test_residual_blocks_exclude_incomplete_and_unfinished_days():
    import numpy as np
    from app.main import completed_residual_blocks

    origin = pd.Timestamp("2018-10-03")
    rows = []
    for day, length in (("2018-10-01", 96), ("2018-10-02", 95), ("2018-10-03", 96)):
        prior = pd.Timestamp(day)
        for horizon in range(1, length + 1):
            rows.append(
                {
                    "model": "ridge",
                    "origin": prior,
                    "horizon": horizon,
                    "target_timestamp": prior + pd.Timedelta(minutes=15 * horizon),
                    "actual": 3.0,
                    "prediction": 1.0,
                }
            )
    blocks, dates = completed_residual_blocks(pd.DataFrame(rows), "ridge", origin)
    assert dates == [pd.Timestamp("2018-10-01")]
    np.testing.assert_array_equal(blocks, np.full((1, 96), 2.0))


def test_v2_forecasting_method_switch_and_robust_controls(monkeypatch):
    import app.main as app_module
    from streamlit.testing.v1 import AppTest

    history, forecasts, metrics = load_artifacts(str(ROOT))
    metrics = {**metrics, "schema_version": 2, "selected_uncertainty_method": "rolling_pooled"}
    selected = forecasts.loc[
        (forecasts.model == metrics["selected_model"])
        & (forecasts.origin == forecasts.origin.max())
    ]
    bands = pd.concat(
        [
            selected.assign(method=method)
            for method in ("v1_fixed", "fixed_pooled", "rolling_pooled")
        ]
    )
    monkeypatch.setattr(app_module, "load_artifacts", lambda: (history, forecasts, metrics))
    monkeypatch.setattr(app_module, "load_uncertainty", lambda: bands)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("Energy Forecasting").run()
    method = next(item for item in app.selectbox if item.label == "Uncertainty calibration method")
    assert method.value == "rolling_pooled"
    method.set_value("v1_fixed").run()
    assert not app.exception
    assert any("previously inspected" in item.value for item in app.caption)
    app.sidebar.radio[0].set_value("Energy Optimization").run()
    strength = next(
        item for item in app.slider if item.label == "Historical residual scenario strength"
    )
    strength.set_value(0.0).run()
    assert not app.exception
    assert any(item.label == "Demand path to inspect" for item in app.selectbox)
    peak = next(
        item for item in app.number_input if item.label == "Maximum interval-average demand (kW)"
    )
    peak.set_value(1.0).run()
    assert not app.exception
    assert any("No schedule or savings" in item.value for item in app.warning)


def test_actual_v2_uncertainty_methods_match_every_model():
    from app.main import load_uncertainty
    from streamlit.testing.v1 import AppTest

    _, forecasts, metrics = load_artifacts(str(ROOT))
    assert metrics["schema_version"] == 2
    uncertainty = load_uncertainty(str(ROOT))
    assert set(uncertainty.method) == {"v1_fixed", "fixed_pooled", "rolling_pooled"}
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("Energy Forecasting").run()
    for model in forecasts.model.unique():
        picker = next(item for item in app.selectbox if item.label == "Forecast model")
        picker.set_value(model).run()
        for method in ("v1_fixed", "fixed_pooled", "rolling_pooled"):
            methods = next(
                item for item in app.selectbox if item.label == "Uncertainty calibration method"
            )
            methods.set_value(method).run()
            assert not app.exception
            assert not app.error
            origin = next(
                item.value for item in app.selectbox if item.label.startswith("Forecast origin")
            )
            expected = uncertainty.loc[
                (uncertainty.model == model)
                & (uncertainty.origin == origin)
                & (uncertainty.method == method)
            ].sort_values("horizon")
            displayed = app.dataframe[-1].value.sort_values("horizon")
            pd.testing.assert_series_equal(
                displayed.lower90.reset_index(drop=True),
                expected.lower90.reset_index(drop=True),
                check_names=False,
            )


def test_actual_v2_robust_zero_strength_and_infeasibility():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("Energy Optimization").run()
    peak = next(
        item for item in app.number_input if item.label == "Maximum interval-average demand (kW)"
    )
    peak.set_value(10000.0).run()
    strength = next(
        item for item in app.slider if item.label == "Historical residual scenario strength"
    )
    strength.set_value(0.0).run()
    assert not app.exception
    comparison = next(
        item.value for item in app.dataframe if "Scenario violation intervals" in item.value.columns
    )
    assert comparison["Feasible on planning constraints"].all()
    assert comparison["Scenario violation intervals"].eq(0).all()
    assert comparison["Worst scenario cost (€)"].nunique() == 1
    peak.set_value(1.0).run()
    assert not app.exception
    comparison = next(
        item.value for item in app.dataframe if "Scenario violation intervals" in item.value.columns
    )
    assert not comparison["Feasible on planning constraints"].any()
    assert comparison["Scenario violation intervals"].isna().all()
    assert comparison["Worst scenario cost (€)"].isna().all()


def test_forecast_default_uses_development_selected_method():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("Energy Forecasting").run()
    metrics = json.loads((ROOT / "artifacts/v2/metrics.json").read_text())
    method = next(
        widget for widget in app.selectbox if widget.label == "Uncertainty calibration method"
    )
    assert method.value == metrics["selected_uncertainty_method"]
    assert not app.exception


def test_residual_scenario_history_is_limited_to_last_sixty_days():
    import numpy as np
    from app.main import completed_residual_blocks

    dates = pd.date_range("2018-01-01", periods=75, freq="D")
    frame = pd.DataFrame(
        {
            "origin": np.repeat(dates, 96),
            "horizon": np.tile(np.arange(1, 97), 75),
            "model": "ridge",
            "actual": np.repeat(np.arange(75), 96),
            "prediction": 0.0,
        }
    )
    frame["target_timestamp"] = frame.origin + pd.to_timedelta(frame.horizon * 15, unit="min")
    values, origins = completed_residual_blocks(frame, "ridge", pd.Timestamp("2018-04-01"))
    assert len(values) == 60 and origins[0] == dates[15]
    np.testing.assert_array_equal(values[0], np.full(96, 15.0))
