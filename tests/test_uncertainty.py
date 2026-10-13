import numpy as np
import pandas as pd
import pytest
from enertwin.uncertainty import calibrated_bands, eligible_blocks, band_summary


def blocks():
    dates = pd.date_range("2018-01-01", periods=30, freq="D")
    residuals = np.repeat(np.arange(1, 31, dtype=float)[:, None], 96, axis=1)
    return residuals, dates


def test_pool_scores_have_day_rank_not_quarter_hour_sample_rank():
    errors, dates = blocks()
    result = calibrated_bands(
        np.full(96, 100.0), errors, dates, "2018-02-01", method="fixed_pooled"
    )
    np.testing.assert_array_equal(result["upper90"], np.full(96, 128.0))
    np.testing.assert_array_equal(result["upper80"], np.full(96, 125.0))
    assert result["n_blocks"] == 30


def test_pooled_scores_are_maxima_of_each_day_bin():
    errors, dates = blocks()
    errors[:, 23] = 2 * errors[:, 23]
    result = calibrated_bands(
        np.full(96, 100.0), errors, dates, "2018-02-01", method="fixed_pooled"
    )
    np.testing.assert_array_equal(result["upper90"][:24], np.full(24, 156.0))
    np.testing.assert_array_equal(result["upper90"][24:], np.full(72, 128.0))


def test_future_and_incomplete_day_cannot_change_bands():
    errors, dates = blocks()
    before = calibrated_bands(np.full(96, 50.0), errors, dates, "2018-01-25", min_blocks=20)
    errors[dates + pd.Timedelta(days=1) > pd.Timestamp("2018-01-25")] = 99999
    after = calibrated_bands(np.full(96, 50.0), errors, dates, "2018-01-25", min_blocks=20)
    np.testing.assert_array_equal(before["upper90"], after["upper90"])
    assert before["n_blocks"] == 24
    assert pd.Timestamp(before["last_residual_completion"]) <= pd.Timestamp("2018-01-25")


def test_rolling_only_last_completed_window_days():
    errors, dates = blocks()
    values, d = eligible_blocks(errors, dates, "2018-02-01", window=20)
    assert len(values) == 20 and d[0] == dates[10]
    result = calibrated_bands(np.ones(96), errors, dates, "2018-02-01", window=20)
    assert result["n_blocks"] == 20 and (result["lower90"] == 0).all()


def test_coverage_counts_point_bins_days_and_sorts():
    table = pd.DataFrame(
        {
            "origin": np.repeat(pd.to_datetime(["2018-01-01", "2018-01-02"]), 96),
            "horizon": np.tile(np.arange(1, 97), 2),
            "actual": np.ones(192),
            "lower90": np.zeros(192),
            "upper90": np.ones(192),
        }
    )
    table.loc[0, "upper90"] = 0
    result = band_summary(table.sample(frac=1, random_state=42))
    assert result["coverage"] == 191 / 192
    assert result["whole_day_coverage"] == 0.5
    assert result["six_hour_block_coverage"] == 7 / 8
    with pytest.raises(ValueError, match="complete"):
        band_summary(table.iloc[:-1])


@pytest.mark.parametrize(
    "setting", ["nat", "duplicate", "nonfinite", "too_few", "bad_method", "bad_bin"]
)
def test_invalid_calibration_inputs_rejected(setting):
    errors, dates = blocks()
    origin = "2018-02-01"
    kwargs = {}
    if setting == "nat":
        origin = pd.NaT
    elif setting == "duplicate":
        dates = pd.DatetimeIndex([dates[0]] * 30)
    elif setting == "nonfinite":
        errors[0, 0] = np.nan
    elif setting == "too_few":
        origin = "2018-01-04"
    elif setting == "bad_method":
        kwargs["method"] = "unknown"
    else:
        kwargs["bin_size"] = 25
    with pytest.raises(ValueError):
        calibrated_bands(np.ones(96), errors, dates, origin, **kwargs)
