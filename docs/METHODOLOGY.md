# Methodology

The pipeline separates measured demand, estimated relationships, held-out forecasts and hypothetical scheduling. The statistical target is energy in each 15-minute interval; the operations model uses interval energy and converts it to average power consistently.

## Chronological protocol

| Stage | Recorded 2018 dates | Purpose |
|---|---|---|
| Training | January 8–June 30 | Fit candidate models and preprocessing |
| Validation | July–August | Select hyperparameters and default by MAE |
| Refit | January 8–August 31 | Fit selected parameter settings before calibration |
| Calibration | September | Estimate residual interval widths; no model selection |
| Final test | October–December | Compare frozen models and uncertainty |

A seven-day history warm-up excludes January 1–7 from training targets. There are 174 training, 62 validation, 30 calibration and 92 final-test daily origins. At each daily midnight origin, all 96 quarter-hour predictions are issued together. Every predictor uses only historical observations at or before origin and calendar values known in advance. Yesterday/week-ago aligned profiles and recent history summaries remain frozen over the horizon. Newly observed targets within a forecast day never refresh predictions for that day. At the next day's origin, elapsed historical observations are available, as in a daily operational forecast.

Preprocessing is fitted on the appropriate training segment. Validation forecasts select parameters; the selected models are refitted through August and then frozen. The test is not a hyperparameter or interval calibration set. Advanced forecasts are clipped at zero because interval energy cannot be negative; baseline comparisons use the same target units.

## Analysis

The reproducible [EDA report](../reports/eda/EDA_REPORT.md) includes source-aware summaries and figures. Historical distributions, calendar profiles, autocorrelation, monthly totals, reactive-energy/power-factor relationships and observed load-category summaries describe the facility. Trend/seasonality and stationarity checks are diagnostic, not proof of a stable data-generating process. Differenced-series analysis can clarify repeated patterns without requiring all forecasters to use differencing. Calendar-aware baselines are necessary because industrial work patterns are strong.

## Uncertainty and interpretation

September absolute residuals calibrate horizon-specific bands and a day-block maximum-residual band. Thirty daily blocks provide limited evidence, and their dependence prevents an exact exchangeability guarantee. Report final-test empirical coverage and width; a nominal level does not establish calibration. Explanations describe associations learned from lag/calendar information, not causal changes in production.

The digital twin adds explicitly specified flexible workload to background demand. It does not infer a controllable part of the historical factory load. See [the formulation](OPTIMIZATION_MODEL.md) and [simulator assumptions](DIGITAL_TWIN.md).
