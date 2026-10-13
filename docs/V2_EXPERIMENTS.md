# Version 2 experiment protocol

## Evidence ownership

V1 commit `38f757f` and tag `v1.0.0` preserve the original experiment. Its files are copied into `versions/v1/`; V2 outputs are separate. The source CSV, timestamp correction, target units, five forecasting models and V1 final-fit point predictions are retained. V2 does not claim improved point accuracy from different interval processing.

## Frozen uncertainty study

`configs/v2_experiment.json` records seed 42, 96 targets, quarter-hour duration, nominal 80%/90% levels, four six-hour bins, a 60-completed-day rolling window and a 20-day minimum. Diagnostic parameters use January–March fitting and April–June validation, followed by January–June refit. Selection is complete before July. July–August calibration and September evaluation compare `v1_fixed`, `fixed_pooled` and `rolling_pooled` under the recorded coverage/width selector. Inspected October–December outcomes are excluded from this method selector.

The final-profile study retains the V1 model fitted through August, starts with September residuals and evaluates October–December retrospectively. Rolling methods add complete prior-day profiles; fixed methods do not absorb the evaluation outcomes. Each origin's source-completion metadata supports causality checks. Report both nominal score targets and empirical pointwise/six-hour/whole-day outcomes.

## Decision study

At each origin, historical signed residual blocks construct twelve illustrative demand paths using seed 42 and strength 1.0, with up to 60 completed historical days. Central, low/high-total residual, seeded resampled and synthetic 1.5× positive-error stress paths retain provenance. No occurrence probabilities are assigned.

Two new hypothetical tasks require 120 and 80 kWh, respectively. Each has a 40 kW task cap; windows begin at slots 32 and 40 and end at slot 96. Shared capacity is 80 kW. The illustrative tariff is €0.08/kWh off-peak and €0.22/kWh from 08:00 through 19:45. Demand caps are tested at 350, 500 and 700 kW. These are reproducible assumptions, not measured factory operating constraints or actual prices.

The deterministic and robust optimizers receive the same tasks, tariffs and cap. Robust mode adds every included scenario's peak constraint to one allocation. Issued schedules are frozen, then tested against observed historical background. Feasible issuance, paired origins, realized-background violations, modeled costs, peak power and computational times are reported separately. Background alone may make either formulation infeasible; those days do not count as successful zero-violation schedules.

## Sensitivity and presentation

Sensitivity varies tariffs, demand caps, residual strength, workload quantities, equipment capacity and scheduling windows. Changing assumptions creates conditional model experiments. A stronger scenario set may increase cost or prevent issuance; a result with equal costs is still informative if allocations/feasibility differ. Figures show error, coverage and width by horizon, calendar drift and decision protection-versus-feasibility/cost trade-offs.

[Results](V2_RESULTS.md) contain actual generated values. [Methodology](V2_METHODOLOGY.md) defines score units and availability. Reproduction commands and generated paths are documented in the README after integration. No source download or model training runs during application startup.
