"""Reproducible descriptive analysis; historical associations are not causal."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from enertwin.data import TARGET  # noqa: E402


ASSOCIATION_FIELDS = [
    "Lagging_Current_Reactive.Power_kVarh", "Leading_Current_Reactive_Power_kVarh",
    "Lagging_Current_Power_Factor", "Leading_Current_Power_Factor",
]


def write_analysis(frame: pd.DataFrame, output_dir: Path | str) -> dict:
    """Write EDA figures, strict JSON and Markdown from corrected interval-start times.

    This function does not alter input data or filter unusual observations. It
    expects the validated loader output, including exact interval_start.
    """
    required = [TARGET, "interval_start", "Load_Type", *ASSOCIATION_FIELDS]
    if frame.empty or not set(required).issubset(frame):
        raise ValueError("EDA requires nonempty validated energy data with interval_start")
    data = frame.copy()
    starts = pd.to_datetime(data["interval_start"])
    if starts.isna().any() or data[required].isna().any().any():
        raise ValueError("EDA requires complete interval-start and measurement fields")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    data["month"] = starts.dt.to_period("M").astype(str)
    data["weekday"] = starts.dt.dayofweek
    data["hour"] = starts.dt.hour + starts.dt.minute / 60
    y = data[TARGET]
    descriptive = {str(k): float(v) for k, v in y.describe(percentiles=[.25, .5, .75, .95, .99]).items()}
    category = {}
    for name, subset in data.groupby("Load_Type", observed=True):
        category[str(name)] = {
            "count": int(len(subset)), "total_kwh": float(subset[TARGET].sum()),
            "mean_kwh": float(subset[TARGET].mean()), "median_kwh": float(subset[TARGET].median()),
            "q25_kwh": float(subset[TARGET].quantile(.25)), "q75_kwh": float(subset[TARGET].quantile(.75)),
        }
    monthly = {}
    for name, subset in data.groupby("month", observed=True):
        monthly[str(name)] = {
            "count": int(len(subset)), "total_kwh": float(subset[TARGET].sum()),
            "mean_kwh": float(subset[TARGET].mean()), "peak_interval_average_kw": float(subset[TARGET].max() * 4),
        }
    associations = {}
    for field in ASSOCIATION_FIELDS:
        correlation = y.corr(data[field])
        associations[field] = {
            "pearson_r_with_energy": float(correlation) if np.isfinite(correlation) else None,
            "mean": float(data[field].mean()), "median": float(data[field].median()),
            "q25": float(data[field].quantile(.25)), "q75": float(data[field].quantile(.75)),
            "min": float(data[field].min()), "max": float(data[field].max()),
        }
    q1, q3 = y.quantile([.25, .75])
    fence = float(q3 + 1.5 * (q3 - q1))
    top = data.nlargest(10, TARGET)
    highest = [{"interval_start": str(row.interval_start), "energy_kwh": float(row[TARGET]),
                "interval_average_kw": float(row[TARGET] * 4), "observed_load_category": str(row.Load_Type)}
               for _, row in top.iterrows()]
    summary = {
        "rows": int(len(data)), "interval_start_min": str(starts.min()),
        "interval_start_max": str(starts.max()), "total_energy_kwh": float(y.sum()),
        "peak_interval_average_kw": float(y.max() * 4), "energy_kwh_descriptive": descriptive,
        "observational_load_categories": category, "monthly": monthly,
        "reactive_and_power_factor_associations": associations,
        "upper_tukey_fence_kwh": fence, "readings_above_upper_fence": int((y > fence).sum()),
        "highest_readings": highest,
        "interpretation": "Historical descriptive associations only; no inferred causality or verified billing peak.",
    }
    (output / "eda_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")

    with plt.rc_context({"font.family": "DejaVu Sans", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titlesize": 12,
                         "axes.labelsize": 10, "figure.facecolor": "white"}):
        fig, axes = plt.subplots(3, 2, figsize=(15, 13), layout="constrained")
        ax = axes[0, 0]
        ax.hist(y, bins=65, color="#187f8a", alpha=.9)
        ax.axvline(y.median(), color="#d77835", label=f"Median {y.median():.2f} kWh")
        ax.set(title="Distribution of interval electricity consumption", xlabel="kWh / 15 min", ylabel="Intervals")
        ax.legend(frameon=False)
        ax = axes[0, 1]
        for day, label in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            profile = data.loc[data.weekday.eq(day)].groupby("hour")[TARGET].mean()
            ax.plot(profile.index, profile.values, label=label, linewidth=1.5)
        ax.set(title="Mean intraday profile by interval-start weekday", xlabel="Hour at interval start", ylabel="Mean kWh / 15 min")
        ax.legend(ncol=4, frameon=False, fontsize=8)
        ax = axes[1, 0]
        categories = list(category)
        ax.boxplot([data.loc[data.Load_Type.eq(name), TARGET] for name in categories],
                   tick_labels=[name.replace("_", " ") for name in categories],
                   showfliers=False, patch_artist=True,
                   boxprops={"facecolor": "#93cad0"}, medianprops={"color": "#b5541d"})
        ax.set(title="Observed load categories (outliers hidden for readability)", ylabel="kWh / 15 min")
        ax = axes[1, 1]
        monthly_mean = data.groupby("month")[TARGET].mean()
        ax.bar(np.arange(len(monthly_mean)), monthly_mean.values, color="#187f8a")
        ax.set_xticks(np.arange(len(monthly_mean)), [name[5:] for name in monthly_mean.index])
        ax.set(title="Monthly mean consumption (not total-month exposure)", xlabel="Month of interval start", ylabel="Mean kWh / 15 min")
        # A fixed evenly spaced subset keeps rendering inexpensive and repeatable.
        scatter = data.iloc[::max(1, len(data) // 6000)]
        ax = axes[2, 0]
        ax.scatter(scatter["Lagging_Current_Reactive.Power_kVarh"], scatter[TARGET],
                   s=7, alpha=.25, color="#187f8a", rasterized=True)
        ax.set(title="Energy and lagging reactive energy: association", xlabel="Lagging reactive energy (kVarh)", ylabel="kWh / 15 min")
        ax = axes[2, 1]
        ax.scatter(scatter["Lagging_Current_Power_Factor"], scatter[TARGET],
                   s=7, alpha=.25, color="#995f9b", rasterized=True)
        ax.set(title="Energy and lagging power factor: association", xlabel="Lagging power factor (%)", ylabel="kWh / 15 min")
        fig.suptitle("EnerTwin AI | Historical industrial energy analysis", fontsize=18, fontweight="bold")
        fig.savefig(output / "eda_overview.png", dpi=140)
        plt.close(fig)
        fig, ax = plt.subplots(figsize=(14, 4), layout="constrained")
        ax.plot(starts, y, color="#187f8a", linewidth=.45, alpha=.75)
        ax.scatter(top.interval_start, top[TARGET], color="#d77835", s=25, label="10 highest measured intervals", zorder=3)
        ax.axhline(fence, color="#995f9b", linewidth=1, linestyle="--", label="Upper Tukey descriptive fence")
        ax.set(title="Unusual high readings retained; not automatically faults", xlabel="Corrected interval-start date", ylabel="kWh / 15 min")
        ax.legend(frameon=False, loc="upper right")
        fig.savefig(output / "eda_high_readings.png", dpi=140)
        plt.close(fig)

    lines = ["# Historical industrial energy analysis", "",
             f"The validated series contains **{len(data):,} quarter-hour observations**, totaling **{y.sum():,.2f} kWh**. Calendar summaries use corrected `interval_start`, from {starts.min()} through {starts.max()}.", "",
             f"Consumption median is {y.median():.2f} kWh per interval, with quartiles {q1:.2f} and {q3:.2f} kWh. Mean is {y.mean():.2f} and standard deviation {y.std():.2f} kWh. The largest reading is {y.max():.2f} kWh, equivalent to **{y.max() * 4:.2f} kW interval-average demand**. This is not a verified instantaneous or billing-demand peak.", "",
             "![Historical analysis](eda_overview.png)", "",
             "## Observational operating categories", "",
             "| Category | Intervals | Mean kWh | Median kWh | Q25–Q75 kWh |", "|---|---:|---:|---:|---:|"]
    for name, values in category.items():
        lines.append(f"| {name} | {values['count']:,} | {values['mean_kwh']:.2f} | {values['median_kwh']:.2f} | {values['q25_kwh']:.2f}–{values['q75_kwh']:.2f} |")
    lines += ["", "Load categories are observed classifications. Their consumption differences do not establish the effect of changing production schedules, and categories are not assumed known for a future forecast horizon.", "",
              "## Reactive energy and power factors", "", "| Variable | Pearson r with consumption | Median | Q25–Q75 |", "|---|---:|---:|---:|"]
    for name, values in associations.items():
        correlation_text = f"{values['pearson_r_with_energy']:.3f}" if values['pearson_r_with_energy'] is not None else "undefined"
        lines.append(f"| {name} | {correlation_text} | {values['median']:.2f} | {values['q25']:.2f}–{values['q75']:.2f} |")
    lines += ["", "Reactive energy uses kVarh and power-factor fields use percent, following the documented variable definitions. Correlations are descriptive and can reflect common operating regimes, timing and scale; they are not causal estimates. Contemporaneous reactive readings and power factors are excluded from deployed future-horizon predictors.", "",
              "## Calendar variation and unusual readings", "", "| Month | Intervals | Total kWh | Mean interval kWh |", "|---|---:|---:|---:|"]
    for name, values in monthly.items():
        lines.append(f"| {name} | {values['count']:,} | {values['total_kwh']:,.2f} | {values['mean_kwh']:.2f} |")
    lines += ["", "Monthly totals differ partly because months have different exposure. The figure therefore compares monthly interval means. Weekday profiles summarize observed averages rather than guaranteed future production patterns.", "",
              f"The upper Tukey fence is {fence:.2f} kWh; {int((y > fence).sum()):,} intervals exceed it. Such readings are descriptive extremes, not evidence of sensor errors or plant faults, and are retained. The highest ten readings are preserved in `eda_summary.json`.", "", "![High readings](eda_high_readings.png)", "",
              "These summaries use the full historical dataset for descriptive analysis. They are not training transformations or model-selection inputs; forecasting and uncertainty evaluation retain separate chronological boundaries. A single facility and single observed year limit external generalization. The source emissions field is excluded from emissions interpretation because its documentation has unresolved units; scenario emissions use explicitly assumed factors."]
    (output / "EDA_REPORT.md").write_text("\n".join(lines) + "\n")
    return summary
