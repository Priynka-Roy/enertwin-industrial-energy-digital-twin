# Final scientific and engineering review

This review records checks from five perspectives. It is an internal independent implementation review, not an external industrial certification.

| Perspective | Evidence checked | Finding and residual limit |
|---|---|---|
| Applied statistician | Daily-origin feature construction, chronological fitting/selection, calibration ranks, retained forecasts | All 96 forecasts use a frozen origin; no future target/covariate input. Pointwise 90% coverage is only 78.70%; retained without test recalibration. Dependence and 30 calibration blocks limit guarantees. |
| Energy analyst | Original source, timestamp sequence, energy/power arithmetic, units and emissions treatment | Independent reload confirms 365 audited midnight corrections, 35,040 contiguous records, no missing/duplicate times, matching interval-start weekday labels and 959,636.71 kWh total. CO2 unit conflict is disclosed and excluded. kW is interval-average power. |
| Operations research engineer | LP variable units, equalities, bounds, shared/peak capacity, objective and reference feasibility | Genuine SciPy HiGHS allocation conserves workload and energy, checks both schedules and reports infeasibility. Cap sensitivity was revised to include binding/infeasible cases rather than only loose caps. Divisible workloads are explicit assumptions. |
| ML engineer | Saved metrics/forecast tables, feature leak check, deterministic baselines and artifact paths | Independent recomputation reproduced all five test MAE/RMSE values. Replacing every post-origin target with 1,000,000 left features unchanged. Seasonal outputs equal explicit historical aligned profiles. Versioned artifacts avoid training at startup. |
| Technical hiring reviewer | README, application sections, guided cases and distinction between evidence and assumptions | The project demonstrates forecasting, uncertainty, LP feasibility and reproducibility. Results distinguish modeled costs from observed data and disclose undercoverage. Public hosting and combined portfolio/CV publication are deferred. |

## Independent numerical checks

The forecast reviewer loaded the raw source using the package parser, confirmed corrected start/end and 15-minute intervals, recomputed all final-test model MAE and RMSE from the saved prediction table, and directly exercised future-corruption and seasonal-profile checks. Forecast target times run from origin plus 15 minutes to origin plus 24 hours. The reference midnight observation is the completed preceding interval.

The operations model compares two feasible schedules under the same assumptions. Cost calculations include fixed background plus flexible demand; optimization can omit fixed cost from its objective because that term is constant. The October 1 example gives €28 modeled tariff benefit while conserving 1,819.52 kWh and assumed constant-factor emissions. With background multiplier 1.2, 170/190/220 kW caps are all correctly infeasible because background peak is 222.53 kW. A flat-price objective has multiple optima; its arbitrary timing is not evidence of purposeful peak reduction.

## Delivery checks

Use `python -m pytest -q` and `python -m ruff check .` to reproduce the automated checks. GitHub Actions runs dependency installation, lint and deterministic tests without raw downloads. The complete local suite passed **59 tests**, and Ruff passed, on Python **3.12.12**. CI status is verified separately after publication; local passing checks do not imply a completed remote CI run. Application screenshots document the locally running interface, not public hosting.

Source attribution is retained in README, data card and the application. Raw data and environment files are ignored, no credential is required for startup, and publication targets a separate public EnerTwin repository without changing IndustrialGuard AI.
