# EnerTwin AI Version 2 case study

## Industrial question

How can an energy planner schedule additional flexible work when background-demand forecasts are imperfect? EnerTwin AI combines real steel-facility electricity profiles, complete next-day forecasts, empirical uncertainty and a constrained hypothetical workload simulator. Version 2 investigates forecast-risk decisions rather than presenting a point forecast as certain.

## Evidence and implementation

The attributed UCI dataset provides 35,040 quarter-hour readings from one facility-year. A sequence-based correction restores midnight chronology without changing original measured values. Five models forecast 96 targets from one frozen midnight information set. V1 selected Histogram Gradient Boosting with original MAE 10.870 kWh/interval versus weekly seasonal naive 12.942. Its nominal 90% pointwise band covered only 78.70%, motivating the upgrade.

V2 compares fixed horizon-wise, six-hour pooled and rolling pooled residual calibration. Pooled scores use complete daily maxima in each six-hour bin to avoid treating neighboring observations as independent. A development experiment selects methodology before the retained final-profile comparison. October–December results are explicitly retrospective because V1 already inspected those outcomes. Point forecasts remain unchanged; interval improvements do not constitute new independent predictive validation.

Signed whole-day residual paths support demand scenarios and preserve recorded intra-day co-movement. A SciPy HiGHS LP issues one workload schedule feasible under every included path. Deterministic and robust schedules complete identical hypothetical work and are evaluated on subsequently observed background, with infeasible issuance reported separately. The robust envelope formulation adds protection through constraints, while fixed tariffs make a distinct CVaR objective uninformative here.

## Interpretation

Additional work, task windows, prices and equipment limits are assumptions. A scenario cost difference is conditional model output; it is not a measured factory benefit. Energy is conserved, average power is kWh/0.25 h, and a constant emissions factor cannot create emissions savings from shifting time. More conservative intervals or scenarios can improve measured coverage/protection while widening bands, raising costs or preventing issuance. [V2 results](V2_RESULTS.md) disclose these trade-offs and actual denominators.

## Evidence-based career drafts

These are draft source material for later CV/portfolio work, not edits to external profiles.

- Developed an eight-section industrial energy application using 35,040 real quarter-hour records, five causal 96-step forecast methods and reproducible chronological evaluation.
- Implemented development-selected, time-aware residual calibration with complete-day score pooling, horizon/coverage/width diagnostics and explicit separation of retrospective results from independent validation.
- Built and mathematically tested deterministic and finite-scenario robust SciPy HiGHS workload scheduling, including frozen-decision backtests, power-cap feasibility, workload conservation and modeled cost trade-offs.

**GitHub description:** Industrial energy forecasting and uncertainty-aware digital twin with causal 24-hour forecasts, historical residual scenarios, robust HiGHS scheduling and an interactive Streamlit application.

**LinkedIn draft:** EnerTwin AI explores industrial energy forecasting and scheduling under uncertain demand using real UCI steel-facility telemetry. It combines five complete next-day forecasters, empirically evaluated residual bands, whole-day scenario generation and a shared robust LP workload allocation. Version 2 reports retrospective coverage and hypothetical decision trade-offs openly, including infeasible cases. It demonstrates applied statistics, machine learning, operations research and reproducible decision support without claiming realized factory savings.

## Technical interview explanation

I froze all 96 predictions at midnight to avoid teacher forcing and excluded future observed load labels and electrical covariates. V1 undercoverage motivated uncertainty work, but its inspected test could no longer serve as new independent validation. I used earlier development data to compare empirical calibration and kept day-level score units because quarter-hour errors are dependent. Historical residual blocks retain intra-day structure; they define illustrative paths rather than calibrated scenario probabilities. The robust LP uses one allocation across all paths, and the componentwise background maximum is exactly equivalent to every supplied peak constraint. Fixed background costs do not affect scheduling preferences, so a separate CVaR method would add complexity without a meaningful decision difference. I evaluate frozen schedules against observed background plus hypothetical work and disclose feasibility rates alongside violations and costs.

Hosting both applications, the combined CV and the portfolio website remain the user's later phase.
