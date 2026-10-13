# Limitations

- One steel facility and one recorded year cannot establish transfer to other industries, plants, future years or new operating regimes.
- Timestamps do not declare timezone; interval-end semantics are inferred from the recorded sequence and independently checked against source weekday labels. Same-date midnight rows require the documented sequence correction. Average interval kW must not be presented as instantaneous meter peaks or a billable demand definition.
- Load categories are observational labels. Their production meaning and controllability are not established.
- Future reactive energy, power factor, CO2 and load labels are unavailable at a true forecast origin, so they are excluded rather than used to inflate forecast accuracy.
- The CO2 header and UCI units conflict. No observed emissions estimate or marginal-emissions attribution is supported.
- September contains only 30 calibration day blocks. Serial dependence and distribution drift may cause prediction bands to miss their nominal coverage.
- Calendar splits provide honest within-dataset evidence, not independent prospective deployment validation. MAE selection may choose a model that fails to beat seasonal baselines on the final test.
- The digital twin is a data-driven scenario simulator. No equipment dynamics, process physics or causal intervention response has been validated.
- Flexible workload, availability, per-task capacity, total-demand cap, electricity prices and emissions factors are user assumptions. Fractional allocations imply divisible, interruptible work, not validated steel-process scheduling.
- Optimizer savings are modeled scenario differences against a feasible reference with identical constraints. Rescheduling conserved energy does not reduce total kWh. A constant emissions factor cannot yield emissions savings from timing alone.
- Forecast background error can cause real cap violations even if the deterministic assumed profile is feasible. Upper-band scenarios are conservative illustrations, not robust feasibility guarantees.
- No live meter integration, realized financial savings, production readiness, public hosting or industrial partner endorsement is claimed.

Priorities for future work are additional years/plants, expert-reviewed operational labels, realistic plant constraints and tariffs, externally validated emissions inputs, rolling prospective forecasts and decision validation under uncertain demand.
