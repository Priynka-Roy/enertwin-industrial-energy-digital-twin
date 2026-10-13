# EnerTwin AI model card — Version 2

**Purpose:** An interpretable industrial energy forecasting and hypothetical scheduling portfolio application. It supports inspection and experimentation; it is not certified plant control.

**Data:** UCI Steel Industry Energy Consumption, one South Korean steel-facility year, 35,040 quarter-hour observations. Attribution/license, source hashes and the documented midnight sequence repair are recorded in the [data card](DATA_CARD.md). Source timezone is unspecified. Consumption is kWh per interval; power is an interval average.

**Prediction target:** Complete next-day consumption profile at a midnight origin, 96 targets at 15-minute spacing. Only completed consumption history and known calendar/horizon features enter prediction. Excluded future observed covariates include load categories, reactive energy, power factors and the unresolved-unit CO2 column.

**Available models:** Last-observation, daily seasonal naive, weekly seasonal naive, standardized Ridge and direct Histogram Gradient Boosting. V1 validation selected gradient boosting; V2 retains final point predictions rather than claiming a new accuracy improvement. Original test MAE/RMSE were 10.870/19.408 kWh per interval. Full model comparisons are preserved in [V1 baseline](V1_BASELINE.md).

**Uncertainty:** Empirical original horizon-wise, fixed six-hour pooled and rolling six-hour pooled absolute-error methods. Pooled methods score each complete residual day using its largest absolute error in each six-hour bin. Only completed historical days calibrate an issued band. Bounds are clipped to nonnegative demand. Method selection uses an earlier diagnostic development experiment, with original inspected dates reserved for retrospective reporting. See [methodology](V2_METHODOLOGY.md) and [actual results](V2_RESULTS.md).

**Intended interpretation:** Interval and scenario uncertainty are different outputs. Nominal six-hour score levels do not provide a simultaneous 24-hour guarantee. Empirical coverage, width and strata are reported; temporal dependence and drift are unresolved.

**Decision component:** SciPy HiGHS allocates divisible, interruptible hypothetical tasks within task, window, equipment/shared-power and peak constraints. Robust mode issues one allocation feasible for all included historical-block/stress paths. Scenario weights/probabilities are not established; no production savings, real tariff, equipment causality or validated physical twin is inferred.

**Evaluation boundary:** The October–December test was first inspected in V1. V2 evaluation there is retrospective; no new independent external dataset is available. Chronological availability tests demonstrate implementation causality, not prospective generalization. Real observed background plus assumed extra work yields hypothetical policy results.

**Artifacts and reproducibility:** Preserved V1 artifacts remain in `versions/v1/`; separate V2 configuration, forecast diagnostics, scenarios and decision reports identify the active method and data provenance. The app uses precomputed artifacts without expensive training or source download at startup. Model artifacts are trusted repository-generated files, not arbitrary uploaded pickle inputs.

**Limitations and review:** [Limitations](LIMITATIONS.md), [technical audit](V2_TECHNICAL_AUDIT.md) and [final review](FINAL_REVIEW.md) record scientific and engineering boundaries. Future requirements include additional plant-years, prospective forecast/decision evaluation, expert validated task constraints, real tariffs and credible emissions factors.
