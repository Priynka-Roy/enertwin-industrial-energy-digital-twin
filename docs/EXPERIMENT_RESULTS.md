# Computed experiment results

Results use corrected interval-end timestamps and true midnight-origin 96-step forecasts. The final test contains **92 days and 8,832 intervals** from October–December 2018. Hyperparameters and the default model were chosen on July–August validation MAE, before evaluating this test. September's 30 days calibrate intervals.

## Forecast comparison

| Model | Validation MAE | Test MAE | Test RMSE | Test bias | Test sMAPE (%) | Peak MAE |
|---|---:|---:|---:|---:|---:|---:|
| Last observation | 22.434 | 23.038 | 39.171 | -21.004 | 77.96 | 110.588 |
| Daily seasonal naive | 13.990 | 15.641 | 28.718 | -0.008 | 47.86 | 60.227 |
| Weekly seasonal naive | 13.576 | 12.942 | 24.771 | -0.027 | 37.87 | 52.750 |
| Pooled direct Ridge | 13.034 | 13.452 | 20.477 | +0.602 | 84.84 | 59.042 |
| Pooled direct gradient boosting | 10.331 | 10.870 | 19.408 | +1.002 | 40.57 | 50.447 |

MAE, RMSE, bias and peak MAE are kWh per 15-minute interval. The default is **histogram gradient boosting**, selected on validation MAE 10.331. It uses 31 leaves, L2 regularization 20, 200 iterations and seed 42. Ridge selects alpha 10. On this test, boosting reduces MAE by **16.02%** against weekly seasonal naive, with positive bias of 1.002 kWh/interval. Weekly naive has lower sMAPE than boosting; a single aggregate metric does not show every trade-off. This is one retrospective plant-year, not independent prospective validation. Peak intervals use the training 95th-percentile target threshold.

## Uncertainty

| Model | Nominal 80% coverage | Width | Nominal 90% coverage | Width | Nominal 90% block whole-day coverage | Block width |
|---|---:|---:|---:|---:|---:|---:|
| Last observation | 66.55% | 32.73 | 84.45% | 45.00 | 83.70% | 128.37 |
| Daily seasonal naive | 68.39% | 41.06 | 79.88% | 52.22 | 91.30% | 144.26 |
| Weekly seasonal naive | 72.33% | 38.96 | 80.99% | 47.70 | 92.39% | 134.25 |
| Pooled direct Ridge | 74.72% | 37.84 | 89.44% | 51.53 | 81.52% | 105.01 |
| Pooled direct gradient boosting | 69.95% | 31.60 | 78.70% | 41.63 | 88.04% | 105.26 |

Widths are kWh per interval. The selected model's nominal 90% pointwise band covers only **78.70%** of test intervals; its nominal 80% band covers **69.95%**. These are materially below nominal and remain disclosed without test-based recalibration. The separately calibrated 90% day-block band covers all 96 intervals on **81 of 92 days (88.04%)**, at average width 105.26 kWh/interval. Pointwise bands do not provide simultaneous day coverage: the selected model's 90% pointwise band covers a complete day on 0 of 92 days. The block band's width illustrates the cost of whole-day protection.

The 30 calibration blocks are dependent and limited. Finite-sample empirical ranks do not establish exact distribution-free temporal guarantees. See [evaluation protocol](FORECAST_EVALUATION.md).

## Historical demand

Observed annual energy is **959,636.71 kWh**, mean interval consumption **27.387 kWh**, median **4.57 kWh**, and maximum interval consumption **157.18 kWh** (average interval power **628.72 kW**). Load-category mean interval energies are Light 8.626, Medium 38.445 and Maximum 59.265 kWh. These labels describe the observations; they do not identify schedulable work or a causal operating lever. Original weekday labels match interval-start days after all 365 audited midnight corrections.

Machine-readable tables in `artifacts/metrics.json`, `data/demo/forecasts.parquet` and `reports/data_quality.json` are the numerical sources. Horizon-specific errors and observed-category results are retained rather than selected for favorable presentation.

Autocorrelation is 0.913 at one interval, 0.606 at one day and 0.677 at one week, supporting seasonal baselines rather than random-split regression. Monthly energy ranges from 57,883.07 kWh in September to 126,238.29 kWh in January; this is descriptive variation, not identified seasonal causation. The training hourly ADF diagnostic with trend gives statistic -8.465 and p-value 6.03e-12 at 24 selected lags. Rejection of its unit-root null does not establish globally stable industrial operations. Lagging reactive energy correlates 0.896 with active consumption; such contemporaneous association remains unsuitable as future input without a forecast of that quantity.

## Guided case A: historical industrial demand

**Problem:** understand demand before choosing a predictor or scheduling assumption. **Inputs:** all 35,040 validated observations, quarter-hour energy and interval-start calendar. **Method:** distributions, calendar profiles, autocorrelation, monthly totals and observed-category summaries. **Result:** 959,636.71 kWh annual observed energy, a median interval far below the mean, and stronger weekly than daily autocorrelation (0.677 versus 0.606). **Interpretation:** idle/active patterns and weekday schedules motivate seasonal comparisons. **Limits:** category differences and correlations are associations at one facility, not controllability or causal savings evidence.

## Guided case B: genuine 24-hour forecasting

**Problem:** estimate the entire next day before observing it. **Inputs:** history through midnight plus future calendar only. **Method:** pooled direct prediction, chronological selection and separate residual calibration. **Result:** gradient boosting test MAE 10.870 versus weekly naive 12.942 kWh/interval, while the 90% pointwise band covers only 78.70%. **Interpretation:** average accuracy improves in this test, but underestimated uncertainty weakens planning confidence. **Limits:** 92 test days in one year; forecasts update at the next day, never within the held-out day's horizon. The application shows every saved daily forecast, including errors.

## Guided case C: time-of-use electricity cost

**Problem:** compare timing of additional divisible workload under two assumed tariff periods. **Inputs:** selected-model forecast for October 1, 2018; 120 kWh batch A allowed 08:00–24:00; 80 kWh batch B allowed 10:00–24:00; each maximum 40 kW; shared flexible capacity 80 kW; total cap 700 kW. Prices are hypothetical **€0.22/kWh from 08:00–20:00** and **€0.08/kWh otherwise**. **Method:** feasible early-weighted reference versus tariff-minimizing LP, both with identical constraints.

| Outcome | Feasible reference | Optimized |
|---|---:|---:|
| Total modeled energy (kWh) | 1,819.52 | 1,819.52 |
| Flexible energy (kWh) | 200.00 | 200.00 |
| Modeled total energy charge (€) | 360.00 | 332.00 |
| Modeled flexible energy charge (€) | 44.00 | 16.00 |
| Average interval peak (kW) | 196.77 | 185.44 |
| Emissions at assumed 0.4 kg/kWh (kg) | 727.81 | 727.81 |

**Result:** modeled charge falls €28.00 (7.78% of total modeled charge); total energy and constant-factor emissions remain unchanged. The cost objective does not generally minimize peak, even though this case's reported peak is lower. **Limits:** forecast demand, workload flexibility, prices and factors are assumptions, not actual plant tariffs or realized savings. A flat hypothetical €0.12/kWh gives €218.34 for both schedules and zero arbitrage benefit. Any flat-price schedule peak difference reflects an arbitrary cost tie, not a designed peak-saving objective.

## Guided case D: constrained peak and sensitivity

**Problem:** determine whether assumed work remains feasible when aggregate average power is capped. **Inputs:** the same forecast/workloads/prices, now with a **190 kW cap**. **Method:** enforce the cap in both the baseline and optimized LPs; vary background multiplier and cap without relaxing constraints. **Result:** baseline peak is 190.00 kW, optimized peak 185.44 kW, and modeled charges remain €360.00 versus €332.00. The cap binds the reference schedule but is not binding at the cost-optimal solution. A 10 kW cap is infeasible because the fixed background itself exceeds it.

| Background multiplier | 170 kW cap | 190 kW cap | 220 kW cap |
|---|---|---|---|
| 0.8 | Feasible; €28 modeled reduction | Feasible; €28 modeled reduction | Feasible; €28 modeled reduction |
| 1.0 | Infeasible | Feasible; €28 modeled reduction | Feasible; €28 modeled reduction |
| 1.2 | Infeasible | Infeasible | Infeasible |

**Interpretation:** with 20% larger background, its own 222.53 kW peak violates even the 220 kW limit; workload timing cannot fix a noncontrollable background. With 20% smaller background, all caps are feasible. **Limits:** deterministic forecast caps do not guarantee realized peaks under forecast error. This scenario diagnoses feasibility; it does not establish real equipment response or demand-charge savings. These results are in `artifacts/scenarios.json` and can be reproduced directly through `simulate_scenario`.

## Variation across daily forecast origins

Selected boosting daily MAE has median 10.408 kWh/interval, interquartile range 7.028–13.816, and observed range 1.669–28.180 across the 92 held-out days. This describes variability across dependent days; it is not an independent-sample confidence interval. These daily error records are retained in `artifacts/metrics.json`.
