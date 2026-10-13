# Version 2 scientific and engineering review

This is an internal implementation review from five professional perspectives, not external plant certification. V1's original review remains in `versions/v1/docs/FINAL_REVIEW.md`. The upgrade retains source evidence and distinguishes methodological development from retrospective comparison.

| Reviewer perspective | Evidence examined | Conclusion and remaining limit |
|---|---|---|
| Applied statistician | Complete-day residual score construction, origin completion gate, development selector, empirical horizon/strata/width outputs | Six-hour daily maxima avoid treating quarter-hour residuals as independent. Method selection uses development dates, but aggregate conservative coverage hides 84.31% peak-stratum coverage. Six-hour 88.04% is not whole-day 90%; the rolling alternative whole-day coverage is 61.96%. No exact dependence-robust guarantee. |
| Energy analytics specialist | Source repair, kWh/kW conversion, tariff/time-window alignment, fixed-factor emissions and workload totals | Original bytes/measurements remain preserved. kW is interval-average energy divided by 0.25 h. New tasks and tariffs are assumed; rescheduling conserves energy and constant-factor emissions. Unresolved source CO2 units remain excluded. |
| Operations research engineer | Shared allocation, componentwise max background equivalence, original LP constraint checks and per-scenario verification | The robust LP is mathematically exact for its finite scenario set. Envelope totals are not real paths; scenario costs are reported separately. Fixed background/deterministic tariffs make an additional CVaR objective redundant. Robust infeasibility is not a successful safe schedule. |
| Machine learning engineer | Original point predictions, frozen information sets, residual/scenario availability, artifact versioning and manifests | Forecast foundation remains causal and unchanged. Retrospective point metrics reproduce V1; V2 does not claim new independent accuracy gains. Portable committed artifacts support startup without raw-source downloads or model fitting. |
| Technical hiring manager | Eight-section app, guided uncertainty case, reproducible experiment/report navigation and career drafts | Demonstrates applied statistics, forecasting, LP decisions and candid evaluation. No actual plant savings, partner endorsement or hosted URL is claimed. Published repository work and local verification are distinguishable from later hosting/CV/site publication. |

## Independent review findings and fixes

The reviewer inspected ingestion, origin-frozen feature construction, V1 residual ranks, deterministic LP source and tests, V2 uncertainty/scenario/robust modules and experiment generation. No demonstrated P0 leakage or deterministic arithmetic defect was found in the original foundation.

The initial V2 sensitivity used a 500 kW cap even though the selected guided case required 700 kW, making most non-cap variations infeasible before their effects could be inspected. The review requested anchoring non-cap variations to the case's recorded cap, without selecting a favorable result. This improves experimental interpretability rather than tuning the historical interval methodology.

The review required explicit paired denominators and own-policy feasibility/violation counts. At 350/500 kW there are no paired robust feasible origins; zero paired violation counts cannot be interpreted as a benefit. At 700 kW both policies have zero paired violations and identical costs, while robust issuance is only 18/92. Documentation reports this negative/neutral evidence openly.

The review also checked that robust top-level envelope energy/cost is not confused with a supplied scenario or compared to deterministic central-profile cost. Complete profiles retain signed errors and identify synthetic positive-error stress changes. Scenario means have no calibrated probability interpretation.

## Reproducible acceptance checks

Run `python scripts/run_v2.py`, `python -m pytest -q` and `python -m ruff check .` from the repository root. Numerical acceptance includes unchanged V1 predictions, original benchmark reproduction, artifact hash compatibility, original and new origin-causality tests, interval-rank/coverage fixtures, signed whole-block scenario dependence, robust hand-computable optima, feasibility under every path, infeasible cases, conserved task energy and all-eight-section application integration.

GitHub Actions verifies Python 3.11 and 3.12. Raw-source verification requires the official source download and is intentionally skipped in lightweight CI when the raw CSV is absent. Local source auditing therefore adds evidence beyond deployed-artifact tests. Passing checks demonstrate the declared implementation behavior, not validated real-world forecasting guarantees or actual factory outcomes.

## Outstanding scientific requirements

Independent future plant-years, prospective decision evaluation, expert-reviewed equipment/process restrictions, real tariffs and trustworthy marginal emissions factors remain unavailable. Temporal distribution changes and conservative scenario construction need operational evaluation. Under the recorded assumptions, robust optimization was frequently infeasible and did not demonstrate a historical violation-reduction benefit. These limits remain visible in results, model card, interface and portfolio text.

The review also corrected diagnostic parameter-selection timing: V1 settings selected in August cannot be reused as if known at July replay origins. Diagnostic tuning now ends in June. The corrected development rule selects the original fixed method; the wider rolling construction remains an alternative rather than being promoted using inspected-test outcomes. The full local suite passed 115 tests and Ruff passed; remote CI is verified before merging.
