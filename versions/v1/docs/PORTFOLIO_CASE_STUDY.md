# EnerTwin AI case study

## Industrial problem

Energy planning needs demand estimates and a transparent assessment of flexible workload timing. Forecast error and operational constraints make simple claims of savings unreliable. EnerTwin AI combines an honest daily forecast evaluation with a constrained scheduling simulator to expose those trade-offs.

## Evidence and design

The source is UCI's Steel Industry Energy Consumption dataset, representing recorded electricity at one South Korean steel facility. Historical profiles, observed load categories, reactive energy and power factors support descriptive analysis. Only historical target values and known calendar information support future forecasts. Daily 96-step origins distinguish full-day forecasting from one-step regression with access to later measurements.

Seasonal baselines, regularized linear forecasting and direct gradient boosting are compared chronologically. Validation chooses settings; separate September residual calibration supports evaluated prediction bands; October–December provides the final comparison. The project reports computed accuracy and coverage even when a baseline wins or uncertainty misses its target.

## Operations model

The background profile can be historical, a held-out forecast or an explicitly altered scenario. Additional flexible workload is hypothetical. A continuous linear program allocates its required energy within availability and power limits while respecting the total cap and minimizing tariff cost. The reference schedule is feasible under identical assumptions. Timing can change cost and peak power while conserving energy. Constant-factor emissions therefore remain unchanged.

Four guided cases connect historical patterns, full-day forecasting, time-of-use optimization and cap sensitivity. Selected gradient boosting achieved final-test MAE 10.870 kWh/interval versus weekly naive 12.942, a 16.02% reduction. Its 90% pointwise residual band covered only 78.70%, showing why model accuracy and uncertainty reliability must be evaluated separately. Actual figures and metrics are recorded in [experiment results](EXPERIMENT_RESULTS.md). They support modeled decision analysis, not realized plant savings.

## Professional contribution

The work demonstrates chronological validation, leakage prevention, forecast uncertainty evaluation, energy/power units, optimization feasibility, reproducible artifacts and interactive presentation. GitHub publication is part of delivery. Public hosting and the combined CV/portfolio website are deferred as requested; no external deployment is claimed.

## Interview talking points

Explain why future load labels inflate forecasting results; why a full-day forecast freezes information at origin; why pointwise intervals differ from simultaneous daily coverage; why divisible workload needs an LP rather than job-start claims; why a cost-optimal schedule must be compared to a feasible reference; and why energy, peak demand, cost and emissions are separate outcomes.


## Draft career text for the later combined portfolio update

These drafts are evidence-based source material, not edits to a CV, LinkedIn profile or portfolio website.

- Built an eight-section industrial energy analytics application using 35,040 real quarter-hour records, chronological 24-hour forecasting and independently checked scenario optimization.
- Compared five forecasting methods across 92 held-out daily origins; selected direct gradient boosting reduced MAE 16.02% versus weekly seasonal naive, while documenting prediction-band undercoverage.
- Implemented a SciPy HiGHS scheduling model with conserved workload, explicit power caps and feasibility tests; an illustrative tariff case reduced modeled charges €28 while preserving energy and assumed constant-factor emissions.

**Short project summary:** EnerTwin AI combines industrial demand analysis, genuine next-day forecasting, empirical uncertainty assessment and constrained hypothetical workload scheduling. It uses real steel-facility telemetry and explicitly separates statistical evidence from assumed tariffs, workloads and emissions.

**LinkedIn draft:** Built EnerTwin AI, an industrial energy forecasting and scheduling portfolio project using UCI steel-facility telemetry. Five methods issue complete 24-hour forecasts with chronological validation, and an interactive simulator uses a genuine constrained LP for hypothetical flexible workload. The selected model improved held-out MAE over weekly naive, but its prediction bands undercovered—a limitation reported openly. Scenario cost differences are modeled, not realized factory savings.
