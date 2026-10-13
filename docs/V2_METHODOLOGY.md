# Version 2 methodology

Version 2 preserves the five point forecasters and the original final-fit predictions. It improves empirical uncertainty diagnostics and adds finite-scenario scheduling. The original October–December outcomes have already been inspected; all Version 2 comparisons on those dates are **retrospective**, with no new independent evaluation dataset.

## Fixed forecast origin

At each midnight origin, all 96 quarter-hour targets run from origin plus 15 minutes through origin plus 24 hours. Features use completed target history through the origin and known calendar information. Neither uncertainty updates nor scenario sampling may use a residual day before its last target is observed. Residual origin `d` becomes eligible at `d + 24 hours`, including equality at the current midnight.

## Development investigation

Diagnostic Ridge and Histogram Gradient Boosting settings are selected using January–March fitting and April–June validation, then refitted on January–June. Selection ends before the first July origin; reusing V1 settings selected in August for July replay would have introduced selection timing leakage. July–August supply residual calibration profiles; September is the development evaluation period for interval methods. Previously inspected data remain development evidence, not new independent validation. Development investigates three predeclared methods: original fixed horizon widths, fixed pooled widths and rolling pooled widths.

The method rule first considers methods whose measured development pointwise coverage is at least nominal minus 0.03 at both 80% and 90%. Among qualifying methods it chooses the smallest average interval width. If none qualifies, it minimizes mean absolute coverage deviation, then width. The original October–December outcomes do not enter this rule. A coverage criterion applied to pointwise outcomes does not convert pooled block levels into exact pointwise probabilities.

## Historical block calibration

For each complete residual day, let `r[d,h] = actual[d,h] - prediction[d,h]`. The original `v1_fixed` method calibrates `abs(r[d,h])` separately at every horizon.

The pooled methods divide the 96 horizons into four consecutive six-hour bins of 24 intervals. For day `d` and bin `b`, their score is:

```text
s[d,b] = max(h in bin b) abs(r[d,h])
```

At level `L`, sort the available **day-level** scores separately for each bin and select rank `min(D, ceil((D+1)*L))`. Repeat that bin's selected width over its 24 horizons. This pools horizon behavior without treating 24 within-day residuals as independent calibration samples. `fixed_pooled` retains the pre-evaluation residual set; `rolling_pooled` uses at most the most recent 60 completed residual days, with at least 20 required days. Bounds are `max(0, prediction-width)` and `prediction+width`.

The nominal levels refer to each six-hour block-score construction. Measure pointwise, six-hour simultaneous and full-24-hour simultaneous coverage separately. Four six-hour blocks do not imply a joint 24-hour nominal guarantee. Serial dependence, changing regimes, limited day counts and reused historical data prevent an exact exchangeability-based guarantee; the finite-sample rank is an empirical construction.

After development selection, the unchanged V1 final point model remains fitted through August. September residuals seed final-profile calibration. Rolling updates add only newly completed days before each October–December origin. Actual outcomes after an origin may evaluate that forecast but cannot alter its issued intervals.

## Scenario generation

Scenarios use signed, intact 96-slot historical residual days added to the current point forecast. The generator filters by completed-day availability, retains source-origin metadata and uses a recorded seed. The finite set includes the central forecast, the eligible lowest/highest total-residual profiles, seeded sampled blocks and an explicitly synthetic positive-error stress profile at 1.5 times the chosen strength. Demand is clipped at zero when necessary.

Intact signed blocks preserve their recorded intra-day co-movement; resampling days does not reproduce across-day dependence or guarantee that errors are transferable to the current operating regime. Selecting extremes by daily residual sum does not establish that they are pointwise lower/upper paths. Stress clipping and scaling change the historical profile and are declared assumptions. Scenarios have no assigned occurrence probabilities and are distinct from prediction intervals.

## Decisions and retrospective backtest

Both deterministic and robust schedules are issued before observed target-day demand is available. They use identical hypothetical tasks, tariffs, power limits and windows. Robust scheduling allocates one shared workload schedule subject to every included background-demand scenario; it does not choose a different schedule after uncertainty resolves. The interval-wise maximum background enforces the finite-scenario cap constraints exactly.

Evaluate each frozen feasible schedule against the subsequently observed historical background plus the hypothetical workload. Report infeasibility separately, modeled tariff costs, peak-limit violations and runtime. Fair comparisons must disclose eligible/paired denominators: failure to issue a robust schedule cannot be counted as a safe operating day. Costs are hypothetical energy charges, not actual bills or realized savings. See [LP formulation](OPTIMIZATION_MODEL.md), [experiment protocol](V2_EXPERIMENTS.md) and [results](V2_RESULTS.md).
