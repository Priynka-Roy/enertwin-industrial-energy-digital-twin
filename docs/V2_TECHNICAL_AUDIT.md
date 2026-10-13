# Version 2 technical audit

The audit inspected source ingestion, timestamp repair, feature construction, chronological fitting, uncertainty evaluation, deterministic LP scheduling, scenario simulation, portable application paths, tests, dependencies and GitHub Actions. It builds on the preserved [Version 1 baseline](V1_BASELINE.md). This is an internal implementation review, not industrial certification.

## Findings and disposition

| Priority | Finding | Consequence and Version 2 response |
|---|---|---|
| P0 | No demonstrated correctness defect in the audited fixed-origin forecasts or deterministic LP | Preserve the functioning foundation. Do not relabel methodological improvements as repaired leakage. Retain source-sequence timestamp tests, future-corruption checks and hand-calculated LP tests. |
| P1 | Only 30 September residual profiles supported 96 separate horizon-width estimates | Estimates are unstable and selected-model nominal 90% coverage was 78.70%. Investigate pooled horizon groups and time-aware historical updates using development data. |
| P1 | Residual distributions change over time and observations within/between days are dependent | Finite-sample ranks do not establish exact distribution-free guarantees. Report coverage, width, horizon/calendar/peak strata and width stability empirically. |
| P1 | October–December test outcomes have already been examined | Preserve V1 values and label all new comparisons on these dates retrospective. Select new methodological settings on earlier development dates. |
| P1 | Substituting marginal lower/upper profiles does not supply a calibrated joint demand distribution | Preserve complete historical residual trajectories when building scenarios; identify synthetic stress profiles and distinguish scenario feasibility from probability guarantees. |
| P1 | Deterministic scheduling alone does not evaluate forecast-risk decisions | Add a single fixed schedule satisfying every included scenario, and a chronological decision backtest that evaluates frozen schedules on subsequently observed background. |
| P1 | Expected cost and worst-case cost can have identical scheduling preferences under fixed tariffs and exogenous additive background | Use meaningful robust peak-feasibility constraints. Do not add a nominal CVaR objective that cannot change the schedule under the declared assumptions. |
| P2 | V1 interface emphasizes deterministic outputs | Retain eight sections, add interval diagnostics, scenario provenance, deterministic/robust comparison, infeasibility status and retrospective labels. |
| P2 | Version ownership and historical evidence need clearer navigation | Preserve the V1 tag/snapshot and separate V2 outputs, add experiment/configuration manifests, model card and comparison documentation. |

## Foundation verified

The CSV parser corrects same-date midnight rows only when they immediately follow 23:45, preserves sequence and measured values, and rejects missing/duplicated/non-quarter-hour telemetry. The documented interval-end inference yields 365 corrections and 35,040 contiguous records. Corrected midnight labels align with the preceding interval-start day. The source CO2-unit contradiction remains disclosed.

Feature construction truncates history at the origin. Daily and weekly target-aligned lags, recent summaries and known future calendar fields generate a complete 96-step forecast. No future observed load categories, reactive energy, power factors or CO2 enter prediction. Ridge scaling fits inside its training pipeline. Model selection uses chronological validation rather than the original test period.

The deterministic solver uses energy variables in kWh, task completion equalities, window bounds, individual/shared capacities and interval-average power caps. Baseline and cost-minimizing schedules solve jointly under identical constraints. Background cost is constant in the LP and included in reported totals. Solver results are independently checked before being marked feasible. Infeasible cases return no fabricated allocations. Flat-price timing is an arbitrary optimum rather than evidence of peak minimization.

Tests cover forecast causality and alignment, timestamp correction, telemetry rejection, calibration rank fixtures, hand-computable metrics, LP constraints/units/conservation, artifact integrity and eight-page app integration. CI runs Python 3.11 and 3.12 without downloading raw telemetry; its raw-source audit is intentionally skipped when source bytes are absent. Reproduction and raw-source verification remain local capabilities.

## Remaining external limits

One observed plant-year cannot establish multi-plant generalization. Historical flexible work is added hypothetical demand, not measured controllable production. Expert equipment constraints, real tariffs, actual marginal emissions, prospective forecasts and operational interventions are unavailable. Version 2 cannot repair these limits by adding algorithms; it makes them explicit.

## V2 development findings resolved before publication

P0: the prototype reused V1 hyperparameters selected in August for July diagnostic replay. Corrected by January–March fitting, April–June selection and January–June refit, with all tuning completed by July 1. No V1 forecast results changed. The corrected development selector chooses fixed horizon bands; wider pooled bands remain alternatives.

P2: sensitivity initially used an already-infeasible 500 kW cap for every axis. Corrected to the recorded 700 kW case cap for non-cap variations. No absent plan is counted as a safe dispatched schedule.
