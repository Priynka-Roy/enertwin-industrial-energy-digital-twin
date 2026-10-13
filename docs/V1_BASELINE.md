# Preserved Version 1 baseline

Version 1 is preserved at Git tag `v1.0.0` and commit `38f757f`. The `versions/v1/` snapshot retains its artifacts, configuration, reports, deployment data and methodological documentation. Version 2 does not rewrite these historical results.

The selected model was Histogram Gradient Boosting. Training origins were January 8–June 30, 2018; July–August validation selected model settings; the advanced models were refitted through August; September supplied 30 calibration days. October–December supplied 92 test origins. All 96 quarter-hour predictions were issued together at midnight using only completed history and known calendar features.

| Original test model | MAE, kWh/interval | RMSE, kWh/interval |
|---|---:|---:|
| Last observation | 23.038 | 39.171 |
| Daily seasonal naive | 15.641 | 28.718 |
| Weekly seasonal naive | 12.942 | 24.771 |
| Ridge | 13.452 | 20.477 |
| Histogram Gradient Boosting | 10.870 | 19.408 |

These are original results, not new independent Version 2 evidence. The October–December outcomes have now been inspected; subsequent comparisons using them are retrospective.

| Original selected-model interval | Empirical coverage |
|---|---:|
| Nominal 80% pointwise | 69.95% |
| Nominal 90% pointwise | 78.70% |
| Nominal 90% whole-day block | 88.04% of complete daily profiles |

Pointwise and whole-day coverage are different targets. The whole-day bands were much wider. The finite-sample residual rank did not establish an exact temporal-dependence coverage guarantee.

The original October 1 hypothetical scheduling example compared €360 baseline cost with €332 optimized cost: a **€28 modeled difference**, with **1,819.52 kWh** in both cases. Workloads, time-of-use prices and operating constraints were assumptions; no realized industrial savings were measured. Constant-factor emissions also remained unchanged.

The original deterministic optimizer, all five model candidates and fixed-origin forecasting logic remain available in Version 2. New outputs are stored separately in Version 2 artifact/report directories.
