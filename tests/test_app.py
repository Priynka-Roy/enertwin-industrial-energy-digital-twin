"""Committed-artifact application integration and fixed-origin display checks."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.main import PAGES, load_artifacts, run_scenario, select_forecast  # noqa: E402


def test_horizon_display_retains_fixed_origin():
    origin = pd.Timestamp("2018-10-01")
    frame = pd.DataFrame(
        {
            "origin": [origin] * 96 + [origin + pd.Timedelta(days=1)] * 96,
            "model": ["daily_naive"] * 192,
            "horizon": list(range(1, 97)) * 2,
        }
    )
    short = select_forecast(frame, "daily_naive", origin, 24)
    assert len(short) == 24
    assert short.origin.nunique() == 1
    assert short.horizon.tolist() == list(range(1, 25))


def test_committed_artifacts_load_without_training():
    history, forecasts, metrics = load_artifacts(str(ROOT))
    assert len(history) == 35040
    assert history.index.is_monotonic_increasing
    assert not history.index.has_duplicates
    assert forecasts.groupby(["model", "origin"]).size().eq(96).all()
    assert metrics["selected_model"] in forecasts.model.unique()


@pytest.mark.parametrize("page", PAGES)
def test_all_eight_sections(page):
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
    app.run()
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, [(item.message, item.stack_trace) for item in app.exception]
    assert not app.error, [item.value for item in app.error]
    assert app.title[0].value == page


def scenario_inputs(energy=20.0, window=(0, 24), prices=None):
    hours = np.repeat(np.arange(24), 4)
    return {
        "base": np.ones(96),
        "prices": np.full(96, 0.12) if prices is None else prices,
        "taskenergy": energy,
        "capacity": 20.0,
        "window": window,
        "hours": hours,
        "peaklimit": 40.0,
    }


def test_scenario_zero_flexibility_and_flat_tariffs():
    for energy in (0.0, 20.0):
        result = run_scenario(scenario_inputs(energy))
        assert result["feasible"]
        assert abs(result["cost_savings_eur"]) < 1e-8
        assert abs(result["energy_savings_kwh"]) < 1e-8


def test_scenario_empty_window_reports_infeasibility():
    result = run_scenario(scenario_inputs(window=(12, 12)))
    assert not result["feasible"]
    assert "no intervals" in result["message"]


def test_ui_infeasible_and_zero_flex_paths():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("Energy Optimization").run()
    peak = next(
        item for item in app.number_input if item.label == "Maximum interval-average demand (kW)"
    )
    peak.set_value(1.0).run()
    assert not app.exception
    assert app.error and "Infeasible scenario" in app.error[0].value
    peak.set_value(10000.0).run()
    energy = next(
        item for item in app.number_input if item.label == "Additional flexible task energy (kWh)"
    )
    energy.set_value(0.0).run()
    assert not app.exception
    assert not app.error
    cost = next(item for item in app.metric if item.label == "Modeled cost difference")
    assert cost.value == "€0.00"


def test_forecast_picker_excludes_calibration_and_explains_all_models():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("Energy Forecasting").run()
    _, forecasts, _ = load_artifacts(str(ROOT))
    expected = forecasts.loc[forecasts.partition == "test", "origin"].nunique()
    assert len(app.selectbox[1].options) == expected
    assert pd.Timestamp(app.selectbox[1].value) >= pd.Timestamp("2018-10-01")
    for model in forecasts.model.unique():
        app.selectbox[0].set_value(model).run()
        assert not app.exception
        assert len(app.selectbox[1].options) == expected
