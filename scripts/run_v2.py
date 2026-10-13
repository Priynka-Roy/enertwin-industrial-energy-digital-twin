"""Frozen V2 development comparison and explicitly retrospective decision experiments."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import time
import platform
import importlib.metadata

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from enertwin.forecasting import design, estimator, predict, MODELS, FEATURES
from enertwin.uncertainty import calibrated_bands, band_summary, eligible_blocks
from enertwin.optimization import optimize_schedule
from enertwin.robust import optimize_robust
from enertwin.scenarios import generate_scenarios
from enertwin.simulation import tariff_profile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/v2"
DEMO = ROOT / "data/demo/v2"
REPORT = ROOT / "reports/v2"


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def residuals(table):
    table = table.sort_values(["origin", "horizon"])
    return (table.actual - table.prediction).to_numpy().reshape(-1, 96), pd.DatetimeIndex(
        table.origin.unique()
    )


def evaluate_bands(table, config):
    """At each origin update only with complete earlier day blocks."""
    output = []
    for model, group in table.groupby("model", sort=False):
        errors, dates = residuals(group)
        initial = group[group.partition == "calibration"]
        fixed, fixed_dates = residuals(initial)
        for origin, day in group[group.partition != "calibration"].groupby("origin"):
            for method in config["methods"]:
                blocks, origins = (
                    (errors, dates) if method == "rolling_pooled" else (fixed, fixed_dates)
                )
                bands = calibrated_bands(
                    day.prediction,
                    blocks,
                    origins,
                    origin,
                    method,
                    config["levels"],
                    config["rolling_days"],
                    config["bin_size"],
                    config["min_blocks"],
                )
                row = day.copy()
                for key in ["lower80", "upper80", "lower90", "upper90"]:
                    row[key] = bands[key]
                row["method"] = method
                row["calibration_days"] = bands["n_blocks"]
                row["last_residual_completion"] = pd.Timestamp(bands["last_residual_completion"])
                output.append(row)
    return pd.concat(output, ignore_index=True)


def uncertainty_report(bands, peak):
    result = {}
    for (model, method), table in bands.groupby(["model", "method"], sort=False):
        values = {str(level): band_summary(table, level) for level in [80, 90]}
        horizon = []
        for h, g in table.groupby("horizon"):
            error = g.prediction - g.actual
            horizon.append(
                {
                    "horizon": int(h),
                    "MAE": float(error.abs().mean()),
                    "RMSE": float(np.sqrt((error**2).mean())),
                    "bias": float(error.mean()),
                    **{
                        f"coverage{level}": float(
                            (
                                (g.actual >= g[f"lower{level}"]) & (g.actual <= g[f"upper{level}"])
                            ).mean()
                        )
                        for level in [80, 90]
                    },
                    **{
                        f"width{level}": float((g[f"upper{level}"] - g[f"lower{level}"]).mean())
                        for level in [80, 90]
                    },
                }
            )
        strata = []
        for name, mask in [
            ("weekday", table.origin.dt.dayofweek < 5),
            ("weekend", table.origin.dt.dayofweek >= 5),
            ("high_demand", table.actual >= peak),
            ("other_demand", table.actual < peak),
        ]:
            g = table[mask]
            strata.append(
                {
                    "group": name,
                    "n": len(g),
                    "bias": float((g.prediction - g.actual).mean()),
                    **{
                        f"coverage{level}": float(
                            (
                                (g.actual >= g[f"lower{level}"]) & (g.actual <= g[f"upper{level}"])
                            ).mean()
                        )
                        for level in [80, 90]
                    },
                }
            )
        monthly = [
            {
                "month": str(month),
                "coverage90": float(((g.actual >= g.lower90) & (g.actual <= g.upper90)).mean()),
                "width90": float((g.upper90 - g.lower90).mean()),
            }
            for month, g in table.groupby(table.origin.dt.to_period("M"))
        ]
        result.setdefault(model, {})[method] = {
            "intervals": values,
            "horizons": horizon,
            "strata": strata,
            "calendar": monthly,
        }
    return result


def decision_experiments(table, config):
    rows = []
    case = None
    prices = tariff_profile()
    for partition, group in table.groupby("partition", sort=False):
        if partition == "calibration":
            continue
        errors, dates = residuals(table)
        for origin, day in group.groupby("origin"):
            blocks, sources = eligible_blocks(
                errors, dates, origin, config["scenario_history_days"]
            )
            paths = generate_scenarios(
                day.prediction.to_numpy(),
                blocks,
                sources,
                origin,
                config["scenario_count"],
                config["scenario_strength"],
                config["seed"],
            )
            profiles = np.asarray(paths["profiles"])
            for cap in config["peak_caps_kw"]:
                results = {}
                for policy in ["deterministic", "robust"]:
                    start = time.perf_counter()
                    kwargs = dict(
                        tasks=config["tasks"],
                        shared_capacity_kw=config["shared_capacity_kw"],
                        peak_limit_kw=cap,
                    )
                    solved = (
                        optimize_schedule(day.prediction, prices, **kwargs)
                        if policy == "deterministic"
                        else optimize_robust(profiles, prices, **kwargs)
                    )
                    elapsed = time.perf_counter() - start
                    row = {
                        "origin": origin,
                        "partition": partition,
                        "policy": policy,
                        "peak_limit_kw": cap,
                        "feasible": solved["feasible"],
                        "planning_seconds": elapsed,
                        "status": solved["status"],
                        "scenario_count": len(profiles),
                        "scenario_source_origins": paths["source_origins"],
                        "last_source_completion": max(
                            pd.Timestamp(d) + pd.Timedelta(days=1)
                            for d in paths["source_origins"]
                            if d
                        ),
                    }
                    if solved["feasible"]:
                        allocation = np.array(solved["optimized_flexible_kwh"])
                        actual = day.actual.to_numpy()
                        total = actual + allocation
                        row.update(
                            flexible_schedule_kwh=allocation.tolist(),
                            realized_cost_eur=float(total @ prices),
                            realized_peak_kw=float(total.max() / 0.25),
                            realized_violation_intervals=int((total > cap * 0.25 + 1e-7).sum()),
                            background_violation_intervals=int((actual > cap * 0.25 + 1e-7).sum()),
                            incremental_violation_intervals=int(
                                ((total > cap * 0.25 + 1e-7) & (actual <= cap * 0.25 + 1e-7)).sum()
                            ),
                            scenario_violation_count=int(
                                ((profiles + allocation) > cap * 0.25 + 1e-7).any(axis=1).sum()
                            ),
                            mean_scenario_cost_eur=float(((profiles + allocation) @ prices).mean()),
                            worst_scenario_cost_eur=float(((profiles + allocation) @ prices).max()),
                            flexible_cost_eur=float(allocation @ prices),
                            flexible_energy_kwh=float(allocation.sum()),
                            energy_balance=bool(
                                np.isclose(
                                    total.sum(),
                                    actual.sum()
                                    + sum(task["energy_kwh"] for task in config["tasks"]),
                                )
                            ),
                        )
                    rows.append(row)
                    results[policy] = solved
                if (
                    case is None
                    and results["robust"]["feasible"]
                    and results["deterministic"]["feasible"]
                ):
                    case = {
                        "origin": str(origin),
                        "partition": partition,
                        "peak_limit_kw": cap,
                        "scenarios": paths,
                        "deterministic": results["deterministic"],
                        "robust": results["robust"],
                        "case_selection": "First chronological pair feasible under both policies, smallest feasible configured cap; no favorable result filter.",
                    }
    return pd.DataFrame(rows), case


def main():
    start = time.perf_counter()
    for path in [OUT, DEMO, REPORT, REPORT / "figures"]:
        path.mkdir(parents=True, exist_ok=True)
    config = json.loads((ROOT / "configs/v2_experiment.json").read_text())
    v1metrics = json.loads((ROOT / "versions/v1/artifacts/metrics.json").read_text())
    source = pd.read_parquet(ROOT / "versions/v1/data/demo/history.parquet")
    forecast = pd.read_parquet(ROOT / "versions/v1/data/demo/forecasts.parquet")
    train = pd.date_range("2018-01-08", "2018-06-30", freq="D")
    x, y = design(source.Usage_kWh, train)
    # Diagnostic tuning ends in June, before the first July calibration origin.
    # Reusing V1 parameters selected in August here would leak selection timing.
    tuning_train = pd.date_range("2018-01-08", "2018-03-31", freq="D")
    tuning_validation = pd.date_range("2018-04-01", "2018-06-30", freq="D")
    xt, yt = design(source.Usage_kWh, tuning_train)
    xv, yv = design(source.Usage_kWh, tuning_validation)
    v1config = json.loads((ROOT / "versions/v1/configs/experiment.json").read_text())
    diagnostic_parameters = {}
    tuning_records = {}
    for model in ["ridge", "hist_gradient_boosting"]:
        candidates = (
            [{"alpha": a} for a in v1config["ridge_alphas"]]
            if model == "ridge"
            else v1config["boosting_candidates"]
        )
        trials = []
        for parameters in candidates:
            candidate = estimator(model, parameters).fit(xt, yt)
            mae = float(np.abs(np.maximum(0, candidate.predict(xv)) - yv).mean())
            trials.append({"parameters": parameters, "MAE": mae})
        diagnostic_parameters[model] = min(trials, key=lambda row: row["MAE"])["parameters"]
        tuning_records[model] = trials
    save(
        OUT / "diagnostic_model_selection.json",
        {
            "training": "2018-01-08 through 2018-03-31",
            "validation": "2018-04-01 through 2018-06-30",
            "last_selection_target": "2018-07-01 00:00:00",
            "refit": "2018-01-08 through 2018-06-30",
            "parameters": diagnostic_parameters,
            "trials": tuning_records,
        },
    )
    development = []
    for model in MODELS:
        fitted = (
            estimator(model, diagnostic_parameters[model]).fit(x, y)
            if model in diagnostic_parameters
            else None
        )
        for origin in pd.date_range(
            config["development_calibration_start"], config["development_end"], freq="D"
        ):
            dates, point = predict(source.Usage_kWh, origin, model, fitted)
            development.append(
                pd.DataFrame(
                    {
                        "origin": origin,
                        "target_timestamp": dates,
                        "horizon": np.arange(1, 97),
                        "actual": source.Usage_kWh.reindex(dates).to_numpy(),
                        "prediction": point,
                        "model": model,
                        "partition": "calibration"
                        if origin < pd.Timestamp(config["development_evaluation_start"])
                        else "development",
                    }
                )
            )
    dev = pd.concat(development, ignore_index=True)
    dev.to_parquet(DEMO / "development_forecasts.parquet", index=False)
    devbands = evaluate_bands(dev, config)
    devreport = uncertainty_report(devbands, v1metrics["peak_threshold_kwh"])
    selected_model = v1metrics["selected_model"]
    eligible = []
    for method, report in devreport[selected_model].items():
        values = report["intervals"]
        met = all(
            values[str(level)]["coverage"] >= level / 100 - config["coverage_tolerance"]
            for level in [80, 90]
        )
        deviation = np.mean(
            [abs(values[str(level)]["coverage"] - level / 100) for level in [80, 90]]
        )
        width = np.mean([values[str(level)]["mean_width"] for level in [80, 90]])
        eligible.append((0 if met else 1, 0 if met else deviation, width, method))
    chosen = min(eligible)[-1]
    save(
        OUT / "development_selection.json",
        {
            "selected_method": chosen,
            "criterion": config["selection"],
            "candidates": devreport[selected_model],
            "data_status": "development evaluation; diagnostic parameters selected April-June before July residual generation. Previously inspected source, not new independent validation",
        },
    )
    print("Frozen development-selected uncertainty:", chosen, flush=True)
    bands = evaluate_bands(forecast, config)
    bands.to_parquet(DEMO / "uncertainty.parquet", index=False)
    devbands.to_parquet(DEMO / "development_uncertainty.parquet", index=False)
    report = uncertainty_report(bands, v1metrics["peak_threshold_kwh"])
    save(
        OUT / "uncertainty_metrics.json",
        {"schema_version": 2, "development": devreport, "retrospective": report},
    )
    mainforecast = forecast.copy()
    picked = bands[bands.method == chosen].set_index(["model", "origin", "horizon"])
    for key in ["lower80", "upper80", "lower90", "upper90"]:
        keys = pd.MultiIndex.from_frame(mainforecast[["model", "origin", "horizon"]])
        assigned = picked[key].reindex(keys).to_numpy()
        mask = mainforecast.partition == "test"
        mainforecast.loc[mask, key] = assigned[mask]
    mainforecast.to_parquet(DEMO / "forecasts.parquet", index=False)
    metrics = {
        **v1metrics,
        "schema_version": 2,
        "selected_uncertainty_method": chosen,
        "v2_config": config,
        "evaluation_status": config["evaluation_status"],
        "uncertainty_comparison": report,
    }
    metrics["intervals"] = {
        model: {
            **report[model][chosen]["intervals"],
            "day_block90": v1metrics["intervals"][model]["day_block90"],
        }
        for model in MODELS
    }
    save(OUT / "metrics.json", metrics)
    selecteddev = dev[dev.model == selected_model]
    devdecisions, devcase = decision_experiments(selecteddev, config)
    retrodecisions, retrocase = decision_experiments(
        forecast[forecast.model == selected_model], config
    )
    decisions = pd.concat([devdecisions, retrodecisions], ignore_index=True)
    decisions.to_parquet(OUT / "decision_backtest.parquet", index=False)
    summaries = []
    for (partition, cap), g in decisions.groupby(["partition", "peak_limit_kw"]):
        paired = g.pivot(index="origin", columns="policy", values="feasible").all(axis=1)
        common = g[g.origin.isin(paired[paired].index)]
        summaries.append(
            {
                "partition": partition,
                "peak_limit_kw": float(cap),
                "origins": int(g.origin.nunique()),
                "common_feasible_origins": int(paired.sum()),
                "policies": {
                    policy: {
                        "planning_feasible_origins": int(p.feasible.sum()),
                        "own_dispatched_violation_days": int(
                            (p[p.feasible].realized_violation_intervals > 0).sum()
                        )
                        if p.feasible.any()
                        else None,
                        "own_dispatched_violation_intervals": int(
                            p[p.feasible].realized_violation_intervals.sum()
                        )
                        if p.feasible.any()
                        else None,
                        "paired_violation_days": int(
                            (common[common.policy == policy].realized_violation_intervals > 0).sum()
                        )
                        if len(common)
                        else None,
                        "paired_mean_realized_cost_eur": float(
                            common[common.policy == policy].realized_cost_eur.mean()
                        )
                        if len(common)
                        else None,
                        "paired_incremental_violation_intervals": int(
                            common[common.policy == policy].incremental_violation_intervals.sum()
                        )
                        if len(common)
                        else None,
                        "mean_planning_seconds": float(p.planning_seconds.mean()),
                    }
                    for policy, p in g.groupby("policy")
                },
            }
        )
    save(OUT / "decision_summary.json", summaries)
    case = devcase or retrocase
    save(OUT / "case_study.json", case)
    sensitivity = []
    profiles = np.asarray(case["scenarios"]["profiles"])
    central = profiles[0]
    for dimension, values in {
        "peak_limit_kw": [250, 350, 500, 700],
        "uncertainty_strength": [0, 0.5, 1, 1.5],
        "workload_multiplier": [0.5, 1, 1.5],
        "capacity_kw": [40, 80, 120],
        "offpeak_price": [0.04, 0.08, 0.16],
        "window_start": [0, 32, 88],
    }.items():
        for value in values:
            caps = value if dimension == "peak_limit_kw" else case["peak_limit_kw"]
            paths = np.maximum(
                central
                + (profiles - central) * (value if dimension == "uncertainty_strength" else 1),
                0,
            )
            tasks = [
                {
                    **t,
                    "energy_kwh": t["energy_kwh"]
                    * (value if dimension == "workload_multiplier" else 1),
                    "start_slot": value if dimension == "window_start" else t["start_slot"],
                }
                for t in config["tasks"]
            ]
            r = optimize_robust(
                paths,
                tariff_profile(offpeak_price=value if dimension == "offpeak_price" else 0.08),
                tasks,
                shared_capacity_kw=value if dimension == "capacity_kw" else 80,
                peak_limit_kw=caps,
            )
            sensitivity.append(
                {
                    "dimension": dimension,
                    "value": value,
                    "feasible": r["feasible"],
                    "flexible_cost_eur": r["scenario_metrics"]["optimized"][0]["flexible_cost_eur"]
                    if r["feasible"]
                    else None,
                    "max_scenario_peak_kw": r["scenario_cost_summary"]["optimized"]["max_peak_kw"]
                    if r["feasible"]
                    else None,
                }
            )
    save(OUT / "sensitivity.json", sensitivity)
    toy_tasks = [
        {
            "name": "Synthetic illustrative job",
            "energy_kwh": 1.0,
            "max_power_kw": 1.0,
            "start_slot": 0,
            "end_slot": 2,
        }
    ]
    toy_paths = [[0.0, 0.0], [1.0, 0.0]]
    save(
        OUT / "hand_calculated_case.json",
        {
            "label": "Synthetic two-hour mathematical example, not UCI observed demand or 15-minute plant scenario",
            "interval_hours": 1.0,
            "prices_eur_kwh": [1.0, 3.0],
            "scenarios": toy_paths,
            "deterministic": optimize_schedule(toy_paths[0], [1.0, 3.0], toy_tasks, 1, 1, 1),
            "robust": optimize_robust(toy_paths, [1.0, 3.0], toy_tasks, 1, 1, 1),
        },
    )
    modelreport = report[selected_model]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for method, r in modelreport.items():
        h = pd.DataFrame(r["horizons"])
        axes[0, 0].plot(h.horizon, h.MAE, label=method)
        axes[0, 1].plot(h.horizon, h.RMSE, label=method)
        axes[1, 0].plot(h.horizon, h.coverage90, label=method)
        axes[1, 1].plot(h.horizon, h.width90, label=method)
    for ax, title in zip(
        axes.flat,
        [
            "MAE by horizon (kWh)",
            "RMSE by horizon (kWh)",
            "Retrospective 90% pointwise coverage",
            "90% band width (kWh)",
        ],
    ):
        ax.set(title=title, xlabel="15-minute horizon")
        ax.legend(fontsize=8)
    axes[1, 0].axhline(0.9, color="black", linestyle="--")
    fig.tight_layout()
    fig.savefig(REPORT / "figures/horizon_diagnostics.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))
    for ax, dimension in zip(axes.flat, sorted({r["dimension"] for r in sensitivity})):
        rows = [r for r in sensitivity if r["dimension"] == dimension]
        ax.plot(
            [r["value"] for r in rows],
            [np.nan if r["flexible_cost_eur"] is None else r["flexible_cost_eur"] for r in rows],
            marker="o",
        )
        ax.set(title=dimension, ylabel="Robust flexible cost (€)")
        ax.text(
            0.02, 0.95, "Missing points = infeasible", transform=ax.transAxes, fontsize=8, va="top"
        )
    fig.tight_layout()
    fig.savefig(REPORT / "figures/sensitivity.png", dpi=160)
    plt.close(fig)
    registry = {
        "schema_version": 2,
        "config": config,
        "selected_method": chosen,
        "point_forecast": "unchanged V1 refitted January-August models; diagnostic models tuned January-March/April-June then refitted January-June; all parameter selection precedes July origins",
        "feature_set": FEATURES,
        "diagnostic_parameters": diagnostic_parameters,
        "source": json.loads((ROOT / "reports/provenance.json").read_text()),
        "python": platform.python_version(),
        "packages": {
            p: importlib.metadata.version(p)
            for p in ["numpy", "pandas", "scipy", "scikit-learn", "streamlit"]
        },
        "solver": "scipy.optimize.linprog(method=highs), no relaxation",
        "runtime_seconds": time.perf_counter() - start,
        "outputs": [
            "uncertainty_metrics.json",
            "decision_backtest.parquet",
            "decision_summary.json",
            "case_study.json",
            "sensitivity.json",
        ],
        "scenario_objective": "Flexible cost minimization; deterministic prices make expected/worst background costs decision-independent; scenario means unweighted descriptive summaries, not probabilities.",
    }
    save(REPORT / "experiment_registry.json", registry)
    paths = [*OUT.glob("*"), *DEMO.glob("*")]
    save(
        REPORT / "artifact_manifest.json",
        {
            "sha256": {
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in paths
                if p.is_file()
            }
        },
    )
    print(
        json.dumps(
            {
                "selected_method": chosen,
                "coverage": modelreport[chosen]["intervals"],
                "decisions": summaries,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
