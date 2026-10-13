# Forecast evaluation

Daily origins create complete, nonoverlapping 96-interval forecast blocks. Calendar splitting is chronological: January 8–June 30 training, July–August validation, September residual calibration and October–December final testing. Parameter selection uses validation MAE only. After refitting through August, model parameters remain frozen through calibration and test.

**MAE** is mean absolute error in kWh per interval. **RMSE** gives larger errors more weight in the same units. **Bias** is mean predicted minus observed kWh; positive means overforecasting. **sMAPE** is mean `200*abs(pred-actual)/(abs(pred)+abs(actual))`, with both-zero pairs assigned zero. It can be unstable for very small consumption. Peak-interval MAE complements average interval accuracy; complete daily prediction tables support inspection of energy and profile errors.

Peak-period evaluation uses a threshold learned from fitting demand, never an optimally selected test threshold. Operating-category errors stratify by observed test labels after forecasts are made; those labels are not model inputs. Horizon tables measure intervals 1–96 and grouped horizon ranges. Saved daily forecasts permit inspection of variation across origins rather than relying on one aggregate average.

## Prediction bands

Horizon-specific bands use September absolute forecast errors, finite-sample corrected empirical quantiles and nonnegative lower bounds. Nominal 80% and 90% pointwise levels describe interval predictions, not simultaneous 24-hour coverage. A separate nominal 90% day-block band calibrates the largest absolute residual within each September day; its empirical whole-day coverage is reported separately.

Thirty calibration days, serial dependence and potential calendar drift limit calibration. No exact distribution-free guarantee or externally validated reliability is claimed. Width is average upper minus lower bound in kWh per interval. Coverage is measured on the untouched final test after calibration. Saving all forecasts, timestamps and residuals permits independent reproduction.

See [computed results](EXPERIMENT_RESULTS.md) for actual comparison tables.

## Version 2 evaluation boundary and interval diagnostics

The original test results above describe V1's initial experiment. Those dates have now been inspected. Every V2 October–December comparison is therefore retrospective, and the unchanged point forecasts reproduce the historical benchmark.

V2 investigates original horizon-wise bands, fixed six-hour pooled bands and rolling six-hour pooled bands using a January–June diagnostic fit, July–August residual calibration and September development evaluation. The recorded rule selects a method using development coverage/width; inspected October–December outcomes do not enter selection. The final point model still uses the preserved January–August fit.

Each pooled-bin calibration observation is a complete day's maximum absolute error within 24 adjacent horizons, rather than 24 supposedly independent interval errors. The rolling method uses up to 60 completed earlier days and requires at least 20. Nominal 80%/90% refer to the six-hour score construction. Measure pointwise, six-hour simultaneous and full-day coverage separately, including width, high-demand, horizon, calendar, bias and day-to-day width-stability diagnostics. Finite-sample ranks do not remove serial dependence or distribution shift.

[Version 2 methodology](V2_METHODOLOGY.md) states the exact selection and availability rules. [Version 2 results](V2_RESULTS.md) separates development evidence from retrospective comparison and retains the width cost of conservative coverage.
