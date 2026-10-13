"""Reproduce frozen chronological experiment and assumed scheduling scenarios."""

from pathlib import Path
import json
import platform
import hashlib
import importlib.metadata

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from enertwin.data import load_data
from enertwin.analysis import write_analysis
from enertwin.forecasting import MODELS, FEATURES, design, estimator, predict
from enertwin.evaluation import scores, residual_quantile, interval_stats
from enertwin.simulation import simulate_scenario, tariff_profile

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    (ROOT / path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    config = json.loads((ROOT / "configs/experiment.json").read_text())
    if (
        config["horizon"],
        config["interval_minutes"],
        config["seed"],
        config["boosting_iterations"],
        config["interval_levels"],
    ) != (96, 15, 42, 200, [0.8, 0.9]):
        raise ValueError(
            "This implementation requires the documented frozen horizon, seed, iterations and interval levels"
        )
    frame, quality = load_data(ROOT / "data/raw/Steel_industry_data.csv")
    save("reports/data_quality.json", quality)
    frame.to_parquet(ROOT / "data/demo/history.parquet")
    series = frame.Usage_kWh
    train = pd.date_range(
        config["first_origin"],
        pd.Timestamp(config["validation_start"]) - pd.Timedelta(days=1),
        freq="D",
    )
    validation = pd.date_range(
        config["validation_start"],
        pd.Timestamp(config["calibration_start"]) - pd.Timedelta(days=1),
        freq="D",
    )
    calibration = pd.date_range(
        config["calibration_start"],
        pd.Timestamp(config["test_start"]) - pd.Timedelta(days=1),
        freq="D",
    )
    test = pd.date_range(config["test_start"], config["final_origin"], freq="D")
    x, y = design(series, train)
    xv, yv = design(series, validation)
    peak = float(np.quantile(y, config["peak_training_quantile"]))
    candidates = {}
    fitted = {}
    validation_scores = {}
    tuning = {}
    for model in MODELS:
        if model in ["ridge", "hist_gradient_boosting"]:
            options = (
                [{"alpha": a} for a in config["ridge_alphas"]]
                if model == "ridge"
                else config["boosting_candidates"]
            )
            trials = []
            for params in options:
                reg = estimator(model, params).fit(x, y)
                metric = scores(yv, np.maximum(0, reg.predict(xv)), peak)
                trials.append({"parameters": params, "metrics": metric})
            best = min(range(len(trials)), key=lambda i: trials[i]["metrics"]["MAE"])
            candidates[model] = options[best]
            tuning[model] = trials
            validation_scores[model] = trials[best]["metrics"]
        else:
            pv = np.concatenate([predict(series, o, model)[1] for o in validation])
            validation_scores[model] = scores(yv, pv, peak)
    selected = min(MODELS, key=lambda m: validation_scores[m]["MAE"])
    print("Validation selector:", selected, validation_scores, flush=True)
    xf, yf = design(series, train.append(validation))
    for model, params in candidates.items():
        fitted[model] = estimator(model, params).fit(xf, yf)
    rows = []
    metrics = {
        "selected_model": selected,
        "validation": validation_scores,
        "test": {},
        "intervals": {},
        "protocol": config,
        "horizon_errors": {},
        "operating_conditions": {},
        "peak_threshold_kwh": peak,
        "tuning": tuning,
        "origin_errors": {},
        "daily_error_summary": {},
    }
    for model in MODELS:
        blocks = []
        for partition, origins in [("calibration", calibration), ("test", test)]:
            for o in origins:
                timestamps, p = predict(series, o, model, fitted.get(model))
                blocks.append(
                    pd.DataFrame(
                        {
                            "origin": o,
                            "target_timestamp": timestamps,
                            "horizon": np.arange(1, 97),
                            "actual": series.reindex(timestamps).to_numpy(),
                            "model": model,
                            "prediction": p,
                            "partition": partition,
                        }
                    )
                )
        table = pd.concat(blocks, ignore_index=True)
        cal = table[table.partition == "calibration"]
        evaluation = table.partition == "test"
        residual = (cal.actual - cal.prediction).to_numpy().reshape(-1, 96)
        quantiles = {}
        for level in config["interval_levels"]:
            q = residual_quantile(residual, level)
            suffix = str(int(level * 100))
            quantiles[suffix] = q.tolist()
            table["lower" + suffix] = np.maximum(0, table.prediction - np.tile(q, len(table) // 96))
            table["upper" + suffix] = table.prediction + np.tile(q, len(table) // 96)
        blockq = float(residual_quantile(np.abs(residual).max(axis=1), 0.9))
        table["block_lower90"] = np.maximum(0, table.prediction - blockq)
        table["block_upper90"] = table.prediction + blockq
        t = table[evaluation]
        metrics["test"][model] = scores(t.actual, t.prediction, peak)
        daily_errors = [
            {"origin": str(o), **scores(g.actual, g.prediction, peak)}
            for o, g in t.groupby("origin")
        ]
        metrics["origin_errors"][model] = daily_errors
        daily_mae = np.array([d["MAE"] for d in daily_errors])
        metrics["daily_error_summary"][model] = {
            "median_MAE": float(np.median(daily_mae)),
            "Q1_MAE": float(np.quantile(daily_mae, 0.25)),
            "Q3_MAE": float(np.quantile(daily_mae, 0.75)),
            "minimum_MAE": float(daily_mae.min()),
            "maximum_MAE": float(daily_mae.max()),
            "interpretation": "Descriptive spread across dependent days, not an independent-sample confidence interval.",
        }
        metrics["intervals"][model] = {
            s: interval_stats(
                t.actual.to_numpy(), t["lower" + s].to_numpy(), t["upper" + s].to_numpy()
            )
            for s in ["80", "90"]
        }
        metrics["intervals"][model]["day_block90"] = interval_stats(
            t.actual.to_numpy(), t.block_lower90.to_numpy(), t.block_upper90.to_numpy()
        )
        metrics["horizon_errors"][model] = [
            {"horizon": int(h), **scores(g.actual, g.prediction)} for h, g in t.groupby("horizon")
        ]
        t = t.copy()
        t["Load_Type"] = frame.Load_Type.reindex(pd.DatetimeIndex(t.target_timestamp)).to_numpy()
        metrics["operating_conditions"][model] = [
            {"Load_Type": label, **scores(g.actual, g.prediction)}
            for label, g in t.groupby("Load_Type")
        ]
        quantiles["day_block90"] = blockq
        save(f"artifacts/intervals_{model}.json", quantiles)
        rows.append(table)
    forecasts = pd.concat(rows, ignore_index=True)
    forecasts.to_parquet(ROOT / "data/demo/forecasts.parquet", index=False)
    save("artifacts/metrics.json", metrics)
    joblib.dump(
        {
            "estimators": fitted,
            "feature_names": FEATURES,
            "config": config,
            "selected_model": selected,
        },
        ROOT / "artifacts/model.joblib",
        compress=3,
    )
    ridge = fitted["ridge"].named_steps["ridge"]
    explanations = {
        "ridge": {
            "method": "Standardized coefficients fitted on January–August; associations, not causal effects.",
            "features": [
                {"feature": f, "coefficient": float(c)} for f, c in zip(FEATURES, ridge.coef_)
            ],
        }
    }
    diagnostic = estimator("hist_gradient_boosting", candidates["hist_gradient_boosting"]).fit(x, y)
    reference_mae = scores(yv, np.maximum(0, diagnostic.predict(xv)))["MAE"]
    groups = {
        "Aligned daily and weekly profiles": [0, 1],
        "Recent historical summaries": [2, 3, 4, 5, 6, 7],
        "Known calendar and horizon": [8, 9, 10, 11, 12, 13],
    }
    rng = np.random.default_rng(config["seed"])
    importance = []
    dayblocks = xv.reshape(len(validation), 96, len(FEATURES))
    for group, columns in groups.items():
        changes = []
        for _ in range(5):
            perturbed = dayblocks.copy()
            shuffled = dayblocks[rng.permutation(len(validation))]
            perturbed[:, :, columns] = shuffled[:, :, columns]
            changes.append(
                scores(yv, np.maximum(0, diagnostic.predict(perturbed.reshape(-1, len(FEATURES)))))[
                    "MAE"
                ]
                - reference_mae
            )
        importance.append(
            {
                "feature": group,
                "importance": float(np.mean(changes)),
                "repeat_std": float(np.std(changes)),
            }
        )
    explanations["hist_gradient_boosting"] = {
        "method": "Validation origin-block group permutation: increase in MAE (kWh), five seeded repeats, train-only model. Correlated and synthetic feature combinations limit interpretation; not causal effects or independent uncertainty estimates.",
        "features": importance,
    }
    save("artifacts/explanations.json", explanations)
    background = forecasts[
        (forecasts.model == selected)
        & (forecasts.origin == pd.Timestamp(config["scenario_origin"]))
    ].prediction.to_numpy()
    tasks = [
        {
            "name": "Assumed batch A",
            "energy_kwh": 120,
            "max_power_kw": 40,
            "start_slot": 32,
            "end_slot": 96,
        },
        {
            "name": "Assumed batch B",
            "energy_kwh": 80,
            "max_power_kw": 40,
            "start_slot": 40,
            "end_slot": 96,
        },
    ]
    scenarios = {}
    for name, prices, limit in [
        ("flat_tariff", tariff_profile(kind="flat"), 700),
        ("time_of_use", tariff_profile(), 700),
        ("peak_constrained", tariff_profile(), 190),
        ("infeasible_peak", tariff_profile(), 10),
    ]:
        scenarios[name] = simulate_scenario(background, prices, tasks, peak_limit_kw=limit)
    scenarios["sensitivity"] = [
        {
            "demand_multiplier": m,
            "peak_limit_kw": limit,
            "result": simulate_scenario(
                background, tariff_profile(), tasks, demand_multiplier=m, peak_limit_kw=limit
            ),
        }
        for m in [0.8, 1.0, 1.2]
        for limit in [170, 190, 220]
    ]
    save("artifacts/scenarios.json", scenarios)
    save(
        "artifacts/repository.json",
        {"url": "https://github.com/Priynka-Roy/enertwin-industrial-energy-digital-twin"},
    )
    save(
        "reports/experiment_manifest.json",
        {
            "config": config,
            "python": platform.python_version(),
            "packages": {
                p: importlib.metadata.version(p)
                for p in ["numpy", "pandas", "scipy", "scikit-learn", "streamlit", "statsmodels"]
            },
            "fit_origins": len(train) + len(validation),
            "origin_lists": {
                name: [str(o) for o in origins]
                for name, origins in [
                    ("train", train),
                    ("validation", validation),
                    ("calibration", calibration),
                    ("test", test),
                ]
            },
            "validation_origins": len(validation),
            "calibration_origins": len(calibration),
            "test_origins": len(test),
            "final_parameters": candidates,
            "source": json.loads((ROOT / "reports/provenance.json").read_text()),
            "test_observed_only_after_selection": True,
        },
    )
    daily = frame.groupby(frame.interval_start.dt.date).Usage_kWh.sum()
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(pd.to_datetime(daily.index), daily)
    ax.set(ylabel="Observed daily consumption (kWh)", title="UCI steel energy: daily consumption")
    fig.tight_layout()
    fig.savefig(ROOT / "reports/figures/daily_consumption.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4))
    frame.groupby(frame.interval_start.dt.hour).Usage_kWh.mean().plot(ax=ax)
    ax.set(
        ylabel="Mean interval consumption (kWh)",
        xlabel="Interval-start hour",
        title="Observed average daily profile",
    )
    fig.tight_layout()
    fig.savefig(ROOT / "reports/figures/daily_profile.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(MODELS, [metrics["test"][m]["MAE"] for m in MODELS])
    ax.tick_params(axis="x", rotation=20)
    ax.set(
        ylabel="Holdout MAE (kWh / interval)", title="Frozen 24-hour forecasts, October–December"
    )
    fig.tight_layout()
    fig.savefig(ROOT / "reports/figures/forecast_comparison.png", dpi=160)
    plt.close(fig)
    eda = {
        "total_kwh": float(series.sum()),
        "daily_mean_kwh": float(daily.mean()),
        "autocorrelation": {str(lag): float(series.autocorr(lag)) for lag in [1, 96, 672]},
        "monthly_kwh": {
            str(k): float(v)
            for k, v in frame.groupby(frame.interval_start.dt.month).Usage_kWh.sum().items()
        },
        "numerical_correlations": frame.select_dtypes("number").corr().to_dict(),
    }
    from statsmodels.tsa.stattools import adfuller

    hourly = series.loc[:"2018-06-30 23:59"].resample("h").sum()
    adf = adfuller(hourly, maxlag=24, regression="ct", autolag="AIC")
    eda["training_hourly_adf"] = {
        "statistic": float(adf[0]),
        "p_value": float(adf[1]),
        "lags": int(adf[2]),
        "interpretation": "Trend-unit-root diagnostic only; seasonal structure and changing operations prevent a general stationarity conclusion.",
    }
    save("reports/eda.json", eda)
    write_analysis(frame, ROOT / "reports/eda")
    artifact_paths = sorted((ROOT / "artifacts").glob("*")) + sorted(
        (ROOT / "data/demo").glob("*.parquet")
    )
    hashes = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in artifact_paths
        if p.is_file()
    }
    save(
        "reports/artifact_manifest.json",
        {
            "sha256": hashes,
            "note": "Integrity checks for locally generated trusted model and portable demo artifacts; attribution in README and data card.",
        },
    )
    print(json.dumps(metrics["test"], indent=2), flush=True)


if __name__ == "__main__":
    main()
