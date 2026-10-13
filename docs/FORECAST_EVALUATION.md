# Forecast evaluation

Daily origins create complete, nonoverlapping 96-interval forecast blocks. Calendar splitting is chronological: January 8–June 30 training, July–August validation, September residual calibration and October–December final testing. Parameter selection uses validation MAE only. After refitting through August, model parameters remain frozen through calibration and test.

**MAE** is mean absolute error in kWh per interval. **RMSE** gives larger errors more weight in the same units. **Bias** is mean predicted minus observed kWh; positive means overforecasting. **sMAPE** is mean `200*abs(pred-actual)/(abs(pred)+abs(actual))`, with both-zero pairs assigned zero. It can be unstable for very small consumption. Peak-interval MAE complements average interval accuracy; complete daily prediction tables support inspection of energy and profile errors.

Peak-period evaluation uses a threshold learned from fitting demand, never an optimally selected test threshold. Operating-category errors stratify by observed test labels after forecasts are made; those labels are not model inputs. Horizon tables measure intervals 1–96 and grouped horizon ranges. Saved daily forecasts permit inspection of variation across origins rather than relying on one aggregate average.

## Prediction bands

Horizon-specific bands use September absolute forecast errors, finite-sample corrected empirical quantiles and nonnegative lower bounds. Nominal 80% and 90% pointwise levels describe interval predictions, not simultaneous 24-hour coverage. A separate nominal 90% day-block band calibrates the largest absolute residual within each September day; its empirical whole-day coverage is reported separately.

Thirty calibration days, serial dependence and potential calendar drift limit calibration. No exact distribution-free guarantee or externally validated reliability is claimed. Width is average upper minus lower bound in kWh per interval. Coverage is measured on the untouched final test after calibration. Saving all forecasts, timestamps and residuals permits independent reproduction.

See [computed results](EXPERIMENT_RESULTS.md) for actual comparison tables.
