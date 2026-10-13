# Forecast models

All methods issue a complete 24-hour profile at midnight. Forecast labels align to the next 96 recorded quarter-hour timestamps. No model receives future observed reactive power, power factor, CO2, load categories or target values.

| Model | Information and strategy | Interpretation |
|---|---|---|
| Last observation | Repeat final historical interval | Persistence reference; weak when demand varies by hour |
| Daily seasonal naive | Repeat previous day's aligned 96 intervals | Captures daily patterns, misses weekday transitions |
| Weekly seasonal naive | Repeat previous week's aligned profile | Captures weekday schedules, misses changing regimes |
| Ridge | Standardized regularized pooled direct forecast using history and known calendar | Linear association; scaling learned only from fitting data |
| Histogram gradient boosting | Pooled direct forecast conditioned on horizon/calendar/history | Nonlinear lag/calendar association; no recursive target refresh |

Fourteen features are previous-day and previous-week aligned demand, last observed demand, previous-day mean/standard deviation/maximum, previous-week mean/standard deviation, cyclic hour and weekday, weekend indicator and normalized horizon index. Features refer to interval-start calendar times. A pooled direct estimator predicts each horizon from this feature row; it does not recursively feed earlier predictions into later ones. Ridge uses StandardScaler plus Ridge with candidate alpha 10, 100 and 1000. Gradient boosting uses 200 iterations, no internal random validation/early stopping, seed 42 and candidates (15 leaves, L2=10) and (31 leaves, L2=20). Standardized Ridge coefficients are descriptive associations; correlated inputs limit individual attribution. The implementation and experiment configuration record these choices. Selected settings minimize validation MAE. Test results can favor a baseline even when an advanced model wins validation; that disagreement must remain visible. Nonnegative clipping prevents physically impossible forecast energy but does not turn a statistical model into a physical simulator.

Explanations use transparent feature definitions, seasonal baselines and model association summaries. Changing a feature in a statistical model is not an identified factory intervention. No deep learning or external explanation service is required.

## Explainability

The gradient boosting explanation uses the January–June fitted model on validation data. It permutes groups of whole origin blocks, preserving each within-day group's profile, with five seed-controlled repeats. Validation MAE increases by 3.236 kWh/interval when known calendar/horizon groups are permuted, 1.169 for recent historical summaries and 1.033 for aligned daily/weekly profiles. These grouped permutation associations suggest calendar and history both contribute to predictions. They are not a precise additive decomposition: correlated groups and unrealistic combinations affect attribution, and five-repeat standard deviations are not independent confidence intervals. No test labels select explanation settings. The separately saved standardized Ridge coefficients describe the refitted linear model.
