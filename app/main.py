"""Interactive observed-data analytics and explicitly illustrative scenarios."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    "Energy Overview",
    "Data Explorer",
    "Energy Forecasting",
    "Forecast Performance",
    "Digital Twin Simulator",
    "Energy Optimization",
    "Cost & Sustainability",
    "About & Methodology",
]
MODEL_NAMES = {
    "last_naive": "Last observation",
    "daily_naive": "Daily seasonal naïve",
    "weekly_naive": "Weekly seasonal naïve",
    "ridge": "Ridge regression",
    "hist_gradient_boosting": "Histogram gradient boosting",
}
REPOSITORY = "https://github.com/Priynka-Roy/enertwin-industrial-energy-digital-twin"


@st.cache_data(show_spinner=False)
def load_artifacts(root: str = str(ROOT)) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load lightweight, immutable artifacts; never fit a model in the app."""
    base = Path(root)
    history = pd.read_parquet(base / "data/demo/history.parquet")
    if "timestamp" in history.columns:
        history = history.set_index("timestamp")
    history.index = pd.to_datetime(history.index)
    history = history.sort_index()
    forecasts = pd.read_parquet(base / "data/demo/forecasts.parquet")
    for column in ("origin", "target_timestamp"):
        forecasts[column] = pd.to_datetime(forecasts[column])
    metrics = json.loads((base / "artifacts/metrics.json").read_text())
    return history, forecasts, metrics


def energy_column(history: pd.DataFrame) -> str:
    for column in ("Usage_kWh", "usage_kwh", "energy_kwh", "sourceUsage_kWh"):
        if column in history:
            return column
    raise ValueError("The deployment history has no electricity consumption column.")


def select_forecast(
    frame: pd.DataFrame, model: str, origin: pd.Timestamp, horizon: int = 96
) -> pd.DataFrame:
    """A fixed origin is retained when displaying a shorter forecast horizon."""
    return (
        frame.loc[
            (frame["model"] == model) & (frame["origin"] == origin) & (frame["horizon"] <= horizon)
        ]
        .sort_values("horizon")
        .copy()
    )


def chart(figure: go.Figure) -> None:
    figure.update_layout(
        template="plotly_white",
        font_family="Arial",
        height=400,
        margin=dict(l=20, r=20, t=45, b=25),
        colorway=["#087F8C", "#EF8354", "#526A9C", "#18A999"],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.18),
    )
    st.plotly_chart(figure, use_container_width=True, config={"displaylogo": False})


def kpis(items: list[tuple[str, str]]) -> None:
    for column, (label, value) in zip(st.columns(len(items)), items, strict=True):
        column.metric(label, value)


def time_filter(history: pd.DataFrame) -> pd.DataFrame:
    starts = history.index - pd.Timedelta(minutes=15)
    dates = st.date_input(
        "Observed period",
        value=(starts.min().date(), starts.max().date()),
        min_value=starts.min().date(),
        max_value=starts.max().date(),
    )
    if len(dates) != 2:
        st.info("Choose the start and end dates to inspect a period.")
        return history.iloc[:0]
    return history.loc[
        (starts >= pd.Timestamp(dates[0]))
        & (starts < pd.Timestamp(dates[1]) + pd.Timedelta(days=1))
    ]


def overview(history: pd.DataFrame, forecasts: pd.DataFrame, metrics: dict) -> None:
    st.markdown("### From electricity records to operational scenarios")
    st.write(
        "Explore a year of real steel-facility electricity readings, compare genuine 24-hour forecasts, "
        "and investigate a constrained, hypothetical flexible-load schedule."
    )
    st.caption("OBSERVED DATA · UCI Steel Industry Energy Consumption · South Korea · 2018")
    selected = time_filter(history)
    if selected.empty:
        return
    energy = energy_column(selected)
    interval_energy = pd.Series(
        selected[energy].to_numpy(), index=selected.index - pd.Timedelta(minutes=15)
    )
    daily = interval_energy.resample("D").sum().rename("Electricity (kWh)")
    kpis(
        [
            ("Observed electricity", f"{selected[energy].sum():,.0f} kWh"),
            ("Maximum interval-average demand", f"{selected[energy].max() / 0.25:,.1f} kW"),
            ("15-minute readings", f"{len(selected):,}"),
            ("Mean daily electricity", f"{daily.mean():,.0f} kWh"),
        ]
    )
    chart(
        px.line(
            daily,
            title="Observed daily electricity consumption",
            labels={
                "index": "Date",
                "timestamp": "Date",
                "value": "Electricity (kWh)",
                "variable": "",
            },
        )
    )
    left, right = st.columns(2)
    with left:
        pattern = (
            selected.assign(hour=(selected.index - pd.Timedelta(minutes=15)).hour)
            .groupby("hour")[energy]
            .mean()
        )
        chart(
            px.bar(
                pattern.rename("Mean interval electricity (kWh)"),
                title="Typical within-day profile",
            )
        )
    with right:
        st.markdown("#### Read the evidence in context")
        st.write(
            "Each kWh value covers 15 minutes. Divide by 0.25 hours to obtain interval-average kW; "
            "this is not an instantaneous equipment power measurement."
        )
        st.write(
            "Load categories describe the recorded operating condition. They are not known future "
            "production schedules and are excluded from future forecast inputs."
        )
        st.write(
            "The scenario pages add explicitly assumed flexible demand. Cost reductions are modeled "
            "results, with no measured intervention or verified factory savings."
        )
    st.info(
        "Guided route: inspect a historical period → compare held-out forecasts → adjust an illustrative "
        "time-of-use tariff → test a constrained schedule."
    )


def explorer(history: pd.DataFrame, forecasts: pd.DataFrame, metrics: dict) -> None:
    st.caption("OBSERVED DATA · Associations do not establish causal effects.")
    selected = time_filter(history)
    if selected.empty:
        return
    energy = energy_column(selected)
    numeric = selected.select_dtypes(include="number").columns.tolist()
    variable = st.selectbox("Observed variable", numeric, index=numeric.index(energy))
    chart(
        px.line(
            selected.reset_index(),
            x=selected.index.name or "index",
            y=variable,
            title=f"Historical {variable}",
        )
    )
    col1, col2 = st.columns(2)
    with col1:
        chart(px.histogram(selected, x=variable, nbins=50, title="Distribution of readings"))
    with col2:
        load = next((c for c in selected if c.lower() == "load_type"), None)
        if load:
            chart(px.box(selected, x=load, y=energy, title="Observed consumption by load category"))
        else:
            chart(
                px.bar(
                    selected.groupby((selected.index - pd.Timedelta(minutes=15)).dayofweek)[
                        energy
                    ].mean(),
                    title="Mean by weekday",
                )
            )
    tab1, tab2, tab3 = st.tabs(["Relationships", "Descriptive statistics", "Calendar patterns"])
    with tab1:
        corr = selected[numeric].corr()
        chart(
            px.imshow(
                corr,
                zmin=-1,
                zmax=1,
                color_continuous_scale="RdBu_r",
                title="Pearson correlations · observational only",
            )
        )
    with tab2:
        st.dataframe(selected[numeric].describe().T, width="stretch")
        st.dataframe(selected.head(100), width="stretch")
    with tab3:
        start = selected.index - pd.Timedelta(minutes=15)
        calendar = selected.assign(weekday=start.dayofweek, hour=start.hour)
        pattern = calendar.pivot_table(
            index="weekday", columns="hour", values=energy, aggfunc="mean"
        )
        pattern.index = pattern.index.map(
            dict(
                enumerate(
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                )
            )
        )
        chart(
            px.imshow(
                pattern,
                color_continuous_scale="Teal",
                title="Mean interval energy by weekday and hour",
                labels={"color": "kWh per interval", "x": "Hour of interval start", "y": "Weekday"},
            )
        )


def forecast_controls(
    forecasts: pd.DataFrame, prefix: str = "forecast", selected_model: str | None = None
) -> tuple[pd.DataFrame, str]:
    forecasts = forecasts.loc[forecasts["partition"] == "test"]
    models = forecasts["model"].unique().tolist()
    model = st.selectbox(
        "Forecast model",
        models,
        format_func=lambda x: MODEL_NAMES.get(x, x),
        index=models.index(selected_model) if selected_model in models else 0,
        key=f"{prefix}_model",
    )
    origins = sorted(forecasts.loc[forecasts["model"] == model, "origin"].unique())
    origin = st.selectbox(
        "Forecast origin · all inputs stop here",
        origins,
        index=len(origins) - 1,
        format_func=lambda x: pd.Timestamp(x).strftime("%d %b %Y, %H:%M"),
        key=f"{prefix}_origin",
    )
    horizon = st.select_slider(
        "Displayed horizon",
        options=[24, 48, 96],
        value=96,
        format_func=lambda x: f"{x // 4} hours / {x} intervals",
        key=f"{prefix}_horizon",
    )
    return select_forecast(forecasts, model, pd.Timestamp(origin), horizon), model


def forecasting(history: pd.DataFrame, forecasts: pd.DataFrame, metrics: dict) -> None:
    st.caption(
        "FINAL TEST FORECASTS · Out-of-sample retrospective forecasts; not a live facility feed."
    )
    st.info(
        f"Validation-selected model: {MODEL_NAMES.get(metrics.get('selected_model'), metrics.get('selected_model'))}. "
        "The final test was not used to select it."
    )
    selected, model = forecast_controls(forecasts, selected_model=metrics.get("selected_model"))
    origin = selected["origin"].iloc[0]
    energy = energy_column(history)
    context = history.loc[
        (history.index > origin - pd.Timedelta(days=1)) & (history.index <= origin)
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=context.index, y=context[energy], name="Observed before origin", line_color="#526A9C"
        )
    )
    for coverage in (90, 80):
        lower, upper = f"lower{coverage}", f"upper{coverage}"
        if lower in selected and selected[lower].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=selected.target_timestamp,
                    y=selected[upper],
                    mode="lines",
                    line_width=0,
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=selected.target_timestamp,
                    y=selected[lower],
                    mode="lines",
                    line_width=0,
                    fill="tonexty",
                    fillcolor="rgba(8,127,140,0.12)",
                    name=f"{coverage}% empirical interval",
                )
            )
    fig.add_trace(
        go.Scatter(
            x=selected.target_timestamp,
            y=selected.prediction,
            name=MODEL_NAMES.get(model, model),
            line_color="#087F8C",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=selected.target_timestamp,
            y=selected.actual,
            name="Held-out actual · evaluation only",
            line=dict(color="#EF8354", dash="dot"),
        )
    )
    fig.update_layout(
        title="Fixed-origin electricity forecast", yaxis_title="Electricity per 15 minutes (kWh)"
    )
    chart(fig)
    kpis(
        [
            ("Forecast origin", origin.strftime("%d %b, %H:%M")),
            ("Last target timestamp", selected.target_timestamp.max().strftime("%d %b, %H:%M")),
            ("Forecast energy", f"{selected.prediction.sum():,.1f} kWh"),
            ("Held-out actual energy", f"{selected.actual.sum():,.1f} kWh"),
        ]
    )
    st.write(
        "All 96 predictions are made from one information cutoff. A shorter display does not refresh "
        "the model with observations from inside that forecast. Future reactive power, power factor, "
        "load category and CO₂ readings are not used as forecast inputs."
    )
    st.caption(
        "Interval bounds are empirical forecasts; they do not imply a physical minimum or maximum. "
        "Intervals use earlier calibration errors. Serial dependence and distribution change mean "
        "nominal coverage is a target, not an exact guarantee. See measured test coverage below."
    )
    explanation_path = ROOT / "artifacts/explanations.json"
    if explanation_path.exists():
        explanations = json.loads(explanation_path.read_text())
        with st.expander("Why this model makes this forecast"):
            descriptions = {
                "last_naive": "Repeats the last electricity reading known at the origin across the entire day.",
                "daily_naive": "Repeats the preceding day's matching 15-minute interval profile.",
                "weekly_naive": "Repeats the preceding week's matching weekday and 15-minute interval profile.",
                "ridge": "Combines preceding day/week readings, past-only summary statistics, calendar cycles and the forecast horizon.",
                "hist_gradient_boosting": "Uses nonlinear relationships between past-only electricity histories, known calendar cycles and the forecast horizon. No future electrical measurements enter the model.",
            }
            st.write(descriptions.get(model, "See the recorded methodology for this model."))
            if model in explanations:
                details = explanations[model]
                st.caption(details["method"])
                features = pd.DataFrame(details["features"])
                if "coefficient" in features:
                    chart(
                        px.bar(
                            features.sort_values("coefficient"),
                            x="coefficient",
                            y="feature",
                            orientation="h",
                            title="Training-fitted standardized regression coefficients",
                        )
                    )
                elif "importance" in features:
                    chart(
                        px.bar(
                            features.sort_values("importance"),
                            x="importance",
                            y="feature",
                            error_x="repeat_std",
                            orientation="h",
                            title="Validation permutation diagnostic · change in MAE (kWh)",
                        )
                    )
                    st.caption(
                        "Feature groups are permuted in whole-origin blocks on validation data. "
                        "Error bars show variation across five permutations, not confidence intervals. "
                        "Negative importance can occur with correlated inputs; synthetic feature combinations "
                        "make this an association diagnostic, not a causal or operational intervention."
                    )
            st.caption(
                "Predictive associations fitted on training observations are not causal effects. "
                "Correlated lag features make isolated coefficient rankings difficult to interpret."
            )
    st.dataframe(
        selected.drop(columns=["model"], errors="ignore"), width="stretch", hide_index=True
    )


def performance(history: pd.DataFrame, forecasts: pd.DataFrame, metrics: dict) -> None:
    st.caption(
        "CHRONOLOGICAL EVALUATION · Advanced models must compete with seasonal naïve baselines."
    )
    test = forecasts.loc[
        forecasts.get("partition", pd.Series("test", index=forecasts.index)) == "test"
    ]
    rows = []
    for model, group in test.groupby("model"):
        error = group.prediction - group.actual
        denominator = group.prediction.abs() + group.actual.abs()
        peak = group.actual >= metrics["peak_threshold_kwh"]
        rows.append(
            {
                "Model": MODEL_NAMES.get(model, model),
                "MAE (kWh)": error.abs().mean(),
                "RMSE (kWh)": np.sqrt((error**2).mean()),
                "sMAPE (%)": (200 * error.abs() / denominator.replace(0, np.nan)).fillna(0).mean(),
                "Bias (kWh)": error.mean(),
                "Peak MAE (kWh)": error.loc[peak].abs().mean(),
                "Origins": group.origin.nunique(),
            }
        )
    table = pd.DataFrame(rows).sort_values("MAE (kWh)")
    st.dataframe(table, width="stretch", hide_index=True)
    st.caption(
        "Positive bias means overprediction. Peak periods exceed a threshold estimated from training data. "
        "Actual future readings are used only to evaluate these periods."
    )
    grouped = (
        test.assign(absolute_error=(test.prediction - test.actual).abs())
        .groupby(["model", "horizon"], as_index=False)
        .absolute_error.mean()
    )
    grouped["model"] = grouped.model.map(lambda x: MODEL_NAMES.get(x, x))
    chart(
        px.line(
            grouped,
            x="horizon",
            y="absolute_error",
            color="model",
            title="Error by forecast horizon",
            labels={"absolute_error": "MAE (kWh)", "horizon": "15-minute steps from origin"},
        )
    )
    intervals = []
    for model, group in test.groupby("model"):
        for nominal in (80, 90):
            lo, hi = f"lower{nominal}", f"upper{nominal}"
            if lo in group and group[lo].notna().any():
                valid = group.dropna(subset=[lo, hi])
                intervals.append(
                    {
                        "Model": MODEL_NAMES.get(model, model),
                        "Nominal (%)": nominal,
                        "Test coverage (%)": 100
                        * ((valid.actual >= valid[lo]) & (valid.actual <= valid[hi])).mean(),
                        "Mean width (kWh)": (valid[hi] - valid[lo]).mean(),
                    }
                )
    st.markdown("#### Empirical prediction interval coverage")
    st.dataframe(pd.DataFrame(intervals), width="stretch", hide_index=True)
    st.caption(
        "Interval metrics above assess individual bins; the separate day-block envelope targets "
        "simultaneous coverage of a complete 96-interval day. Temporal dependence still limits guarantees."
    )
    with st.expander("Simultaneous whole-day interval evaluation"):
        st.json(
            {
                model: values.get("day_block90", {})
                for model, values in metrics.get("intervals", {}).items()
            }
        )
    conditions = metrics.get("operating_conditions", {})
    if conditions:
        with st.expander("Post-hoc performance by observed operating condition"):
            rows = [
                {"Model": MODEL_NAMES.get(model, model), **entry}
                for model, entries in conditions.items()
                for entry in entries
            ]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            st.caption(
                "Future load category is an evaluation label only. It never enters forecast features."
            )
    with st.expander("Recorded evaluation protocol and provenance"):
        st.json(metrics)
    st.warning(
        "One facility and one year provide limited evidence of transferability. The fixed final test "
        "period evaluates historical generalization; no prospective deployment outcome is available."
    )


# Scenario rendering is shared by three pages, while calculations live in the package.
def scenario_controls(forecasts: pd.DataFrame, selected_model: str | None = None) -> dict:
    st.caption(
        "HYPOTHETICAL SCENARIO · Forecast reference + explicitly assumed additional flexible demand."
    )
    forecasts = forecasts.loc[forecasts["partition"] == "test"]
    models = forecasts.model.unique().tolist()
    model = st.selectbox(
        "Reference forecast",
        models,
        format_func=lambda x: MODEL_NAMES.get(x, x),
        index=models.index(selected_model) if selected_model in models else 0,
        key="scenario_model",
    )
    origins = sorted(forecasts.loc[forecasts.model == model, "origin"].unique())
    origin = st.selectbox(
        "Reference day origin",
        origins,
        index=len(origins) - 1,
        format_func=lambda x: pd.Timestamp(x).strftime("%d %b %Y, %H:%M"),
        key="scenario_origin",
    )
    profile = select_forecast(forecasts, model, pd.Timestamp(origin))
    col1, col2, col3 = st.columns(3)
    with col1:
        multiplier = st.slider("Assumed demand multiplier", 0.5, 1.5, 1.0, 0.05)
        uncertainty = st.selectbox(
            "Reference demand scenario",
            ["Point forecast", "Upper 80% envelope", "Lower 80% envelope"],
        )
        tariff = st.selectbox(
            "Illustrative tariff", ["Time of use", "Flat price", "User-defined hourly prices"]
        )
    with col2:
        offpeak = st.number_input(
            "Assumed off-peak price (€/kWh)", min_value=0.0, value=0.08, step=0.01
        )
        peakprice = st.number_input(
            "Assumed peak price (€/kWh)", min_value=0.0, value=0.22, step=0.01
        )
        peaklimit = st.number_input(
            "Maximum interval-average demand (kW)", min_value=1.0, value=700.0, step=25.0
        )
    with col3:
        taskenergy = st.number_input(
            "Additional flexible task energy (kWh)", min_value=0.0, value=200.0, step=25.0
        )
        capacity = st.number_input(
            "Flexible task capacity (kW)", min_value=1.0, value=100.0, step=10.0
        )
        window = st.slider("Permitted task hours [start, end)", 0, 24, (8, 24))
    hours = (profile.target_timestamp - pd.Timedelta(minutes=15)).dt.hour.to_numpy()
    prices = np.where((hours >= 8) & (hours < 20), peakprice, offpeak)
    if tariff == "Flat price":
        prices[:] = offpeak
    if tariff == "User-defined hourly prices":
        st.caption(
            "Edit all 24 assumed prices. These are scenario inputs, not a measured company tariff."
        )
        price_table = st.data_editor(
            pd.DataFrame({"Hour": range(24), "€/kWh": [float(offpeak)] * 24}),
            hide_index=True,
            disabled=["Hour"],
            key="hourly_prices",
            column_config={"€/kWh": st.column_config.NumberColumn(min_value=0.0)},
            width="stretch",
        )
        prices = price_table["€/kWh"].to_numpy()[hours]
    reference = {
        "Point forecast": "prediction",
        "Upper 80% envelope": "upper80",
        "Lower 80% envelope": "lower80",
    }[uncertainty]
    if reference not in profile or profile[reference].isna().all():
        st.warning("This model has no calibrated envelope. Using its point forecast.")
        reference = "prediction"
    base = np.maximum(profile[reference].to_numpy(), 0) * multiplier
    return {
        "profile": profile,
        "base": base,
        "prices": prices,
        "peaklimit": peaklimit,
        "taskenergy": taskenergy,
        "capacity": capacity,
        "window": window,
        "hours": hours,
        "uncertainty": uncertainty,
    }


def run_scenario(inputs: dict):
    # Imported lazily so observed analytics remain available if scenario artifacts are absent.
    from enertwin.optimization import optimize_schedule

    allowed = np.flatnonzero(
        (inputs["hours"] >= inputs["window"][0]) & (inputs["hours"] < inputs["window"][1])
    )
    if inputs["taskenergy"] and len(allowed) == 0:
        return {
            "feasible": False,
            "message": "The permitted window has no intervals for required work.",
        }
    tasks = (
        [
            {
                "name": "Illustrative flexible workload",
                "energy_kwh": inputs["taskenergy"],
                "max_power_kw": inputs["capacity"],
                "start_slot": int(allowed.min()),
                "end_slot": int(allowed.max()) + 1,
            }
        ]
        if inputs["taskenergy"]
        else []
    )
    return optimize_schedule(
        inputs["base"],
        inputs["prices"],
        tasks,
        shared_capacity_kw=inputs["capacity"],
        peak_limit_kw=inputs["peaklimit"],
    )


def scenario_page(history: pd.DataFrame, forecasts: pd.DataFrame, metrics: dict, mode: str) -> None:
    inputs = scenario_controls(forecasts, metrics.get("selected_model"))
    try:
        result = run_scenario(inputs)
    except (ValueError, TypeError) as exc:
        st.error(f"Invalid scenario: {exc}")
        return
    render_scenario(result, inputs, mode)


def render_scenario(result, inputs: dict, mode: str) -> None:
    # The optimizer result contract is kept explicit; no fabricated or fallback solver outputs.
    if not result["feasible"]:
        st.error(f"Infeasible scenario: {result['message']}")
        st.write(
            "Required workload, allowed windows, capacity and peak limit cannot all be satisfied. "
            "No savings comparison is produced and constraints are not silently relaxed."
        )
        return
    baseline = np.asarray(result["baseline_kwh"])
    optimized = np.asarray(result["optimized_kwh"])
    prices = inputs["prices"]
    basecost, optcost = float(baseline @ prices), float(optimized @ prices)
    kpis(
        [
            ("Baseline modeled cost", f"€{basecost:,.2f}"),
            ("Optimized modeled cost", f"€{optcost:,.2f}"),
            ("Modeled cost difference", f"€{basecost - optcost:,.2f}"),
            ("Energy difference", f"{result['energy_savings_kwh']:,.3f} kWh"),
        ]
    )
    frame = pd.DataFrame(
        {
            "Timestamp": inputs["profile"].target_timestamp,
            "Reference demand (kW)": inputs["base"] / 0.25,
            "Feasible baseline (kW)": baseline / 0.25,
            "Optimized demand (kW)": optimized / 0.25,
        }
    )
    fig = px.line(
        frame,
        x="Timestamp",
        y=frame.columns[1:].tolist(),
        title="Illustrative scenario · interval-average demand",
        labels={"value": "Interval-average demand (kW)", "variable": ""},
    )
    fig.add_hline(y=inputs["peaklimit"], line_dash="dash", annotation_text="Assumed peak limit")
    chart(fig)
    st.success(f"Solver: {result['message']}")
    st.write(
        "The baseline assigns flexible energy to permitted intervals as early as the constraints allow. "
        "The optimizer uses the same energy requirement, capacity, window and peak limit. "
        "The task is divisible and interruptible; no real production specification is inferred."
    )
    if mode == "Energy Optimization":
        st.markdown("#### Constraint checks")
        checks = {
            "Baseline energy (kWh)": float(baseline.sum()),
            "Optimized energy (kWh)": float(optimized.sum()),
            "Baseline peak (kW)": float(baseline.max() / 0.25),
            "Optimized peak (kW)": float(optimized.max() / 0.25),
            "Peak limit (kW)": inputs["peaklimit"],
            "Required flexible energy (kWh)": inputs["taskenergy"],
        }
        st.dataframe(
            pd.DataFrame(checks.items(), columns=["Quantity", "Value"]),
            hide_index=True,
            width="stretch",
        )
        st.dataframe(
            pd.DataFrame(result["constraint_verification"]).rename_axis("Verified constraint"),
            width="stretch",
        )
        st.dataframe(
            frame.assign(**{"Illustrative price (€/kWh)": prices}), width="stretch", hide_index=True
        )
        st.latex(r"\min_{x_{t,j}\geq 0}\sum_t p_t\left(b_t+\sum_j x_{t,j}\right)")
        st.caption(
            "x is task electricity in kWh per interval; sum over each task equals required kWh. "
            "x ≤ capacity in kW × 0.25 h, x = 0 outside the task window, and total kWh ≤ peak kW × 0.25 h. SciPy HiGHS solves this linear program."
        )
    if mode == "Cost & Sustainability":
        factor = st.number_input(
            "Assumed constant emissions factor (kg CO₂e/kWh)", min_value=0.0, value=0.4, step=0.05
        )
        kpis(
            [
                ("Baseline scenario emissions", f"{baseline.sum() * factor:,.1f} kg CO₂e"),
                ("Optimized scenario emissions", f"{optimized.sum() * factor:,.1f} kg CO₂e"),
                ("Peak demand change", f"{(baseline.max() - optimized.max()) / 0.25:,.1f} kW"),
            ]
        )
        st.info(
            "Equal total energy and a constant assumed emissions factor imply equal modeled emissions. "
            "Tariff arbitrage does not automatically save energy or CO₂. Emissions factors here are assumptions, not measured plant or marginal grid emissions."
        )
        sensitivities = []
        for cap in [inputs["peaklimit"] * 0.75, inputs["peaklimit"], inputs["peaklimit"] * 1.25]:
            alternate = run_scenario({**inputs, "peaklimit": cap})
            sensitivities.append(
                {
                    "Peak limit (kW)": cap,
                    "Feasible": alternate["feasible"],
                    "Optimized modeled cost (€)": float(
                        np.asarray(alternate["optimized_kwh"]) @ prices
                    )
                    if alternate["feasible"]
                    else np.nan,
                }
            )
        st.markdown("#### Peak-limit sensitivity · same tariff and workload")
        st.dataframe(pd.DataFrame(sensitivities), width="stretch", hide_index=True)
    if mode == "Digital Twin Simulator":
        chart(
            px.line(
                x=inputs["profile"].target_timestamp,
                y=prices,
                title="Assumed electricity prices",
                labels={"x": "Timestamp", "y": "€/kWh"},
            )
        )
        st.warning(
            "This is a data-driven scenario simulator, not a physically validated plant digital twin. "
            "An interval uncertainty envelope is not a jointly calibrated whole-day demand path. "
            "Results support hypothesis exploration, not autonomous operating decisions."
        )


def about(history: pd.DataFrame, forecasts: pd.DataFrame, metrics: dict) -> None:
    st.markdown("### A transparent bridge from forecasting to decisions")
    st.write(
        "EnerTwin AI addresses short-term electricity planning with observed industrial data and "
        "a separate mathematical scenario model. Forecast accuracy and operational assumptions remain visible."
    )
    st.markdown("#### Data and attribution")
    st.markdown(
        "[UCI Steel Industry Energy Consumption](https://archive.ics.uci.edu/dataset/851/steel+industry+energy+consumption) "
        "· DOI [10.24432/C52G8C](https://doi.org/10.24432/C52G8C) · CC BY 4.0. "
        "The original records cover a South Korean steel facility in 2018, with 15-minute electricity, "
        "reactive-power and power-factor readings and operating load categories."
    )
    st.write(
        "Timestamps label interval ends. kWh is interval energy; kW is computed as kWh / 0.25 h. "
        "Load categories and contemporaneous electrical measurements are retrospective observations, "
        "not future-known forecast inputs or controllable interventions."
    )
    st.markdown("#### Forecasting and validation")
    st.write(
        "Chronological training, validation, calibration and final testing keep future observations "
        "out of input construction. Last-observation, daily and weekly seasonal baselines are compared "
        "with regularized linear and gradient-boosted forecasting. Calendar inputs are known in advance; "
        "demand histories stop at the forecast origin. Earlier residuals calibrate empirical intervals."
    )
    st.markdown("#### Optimization and scenario assumptions")
    st.write(
        "SciPy HiGHS minimizes assumed electricity expenditure while conserving the flexible task's "
        "energy, respecting availability, power capacity and a total-demand limit. Both the baseline "
        "and optimized schedule satisfy the same constraints. Tasks are divisible and interruptible."
    )
    st.markdown("#### Practical limits")
    st.write(
        "No measured operational cost savings, independent factory validation, production schedule "
        "or causal intervention effect is available. One historical facility limits generalization. "
        "All tariffs, task constraints and emissions factors are explicit illustrative inputs."
    )
    st.markdown(f"[Source code, reproduction and full methodology]({REPOSITORY})")
    st.caption(
        "Python · pandas · scikit-learn · SciPy HiGHS · Plotly · Streamlit · pytest · GitHub Actions"
    )


def main() -> None:
    st.set_page_config(page_title="EnerTwin AI | Industrial Energy", page_icon="⚡", layout="wide")
    st.markdown(
        """<style>
    .block-container {padding-top:2rem; padding-bottom:3rem; max-width:1400px;}
    [data-testid="stMetric"] {background:white; border:1px solid #E0E8EF; border-radius:12px; padding:18px;}
    h1 {letter-spacing:-1px;} [data-testid="stSidebar"] {border-right:1px solid #E0E8EF;}
    </style>""",
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.markdown("## ⚡ EnerTwin AI")
        st.caption("INDUSTRIAL ENERGY INTELLIGENCE")
        page = st.radio("Explore", PAGES, label_visibility="collapsed")
        st.divider()
        st.caption("Observed → Forecast → Assumed scenario")
        st.markdown(f"[GitHub repository]({REPOSITORY})")
        st.caption("Portfolio research application · no live control")
    st.title(page)
    st.caption("EnerTwin AI · Industrial Energy Forecasting & Optimization")
    try:
        history, forecasts, metrics = load_artifacts()
    except (FileNotFoundError, ValueError, KeyError) as exc:
        st.error(f"Deployment artifacts could not be loaded: {exc}")
        st.code("python scripts/run_pipeline.py")
        st.info(
            "Generate the reproducible artifacts before starting the app. No model is trained during startup."
        )
        return
    handlers = {
        "Energy Overview": overview,
        "Data Explorer": explorer,
        "Energy Forecasting": forecasting,
        "Forecast Performance": performance,
        "About & Methodology": about,
    }
    if page in handlers:
        handlers[page](history, forecasts, metrics)
    else:
        scenario_page(history, forecasts, metrics, page)
    st.divider()
    st.caption(
        "EnerTwin AI · UCI data under CC BY 4.0 · Financial and sustainability scenario outputs are modeled, not realized."
    )
