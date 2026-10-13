# Data-driven scenario simulator

EnerTwin's digital twin is a scenario calculator combining real-data profiles or statistical forecasts with explicitly hypothetical operations. It is **not a physically validated steel-plant simulator** and has no independently validated intervention outcomes.

## What is observed, predicted and assumed

| Input or output | Status |
|---|---|
| Steel-industry electricity readings and historical categories | Observed, observational UCI data |
| 24-hour demand profile estimated from past energy and known calendar information | Statistical forecast |
| Fixed background interpretation of this profile | Explicit scenario assumption |
| Demand multiplier | User assumption applied arithmetically, not a learned causal effect |
| Additional flexible tasks, energy requirements, windows and capacities | Hypothetical workloads |
| Electricity price profile and emissions factors | Illustrative user assumptions |
| Feasible baseline and optimized schedule, costs, peaks and emissions | Model outputs conditional on all those assumptions |
| Realized savings or measured emissions benefit | Not available |

Historical forecasts already represent whole-facility consumption; additional task energy is therefore a **new hypothetical workload added on top**. The simulator does not remove an arbitrary fraction from the historical profile and call it controllable load. It does not infer machinery or controllable operations from observed load categories.

## User controls and calculations

Users can adjust fixed-demand scaling, flat or time-of-use prices, workload requirements, permitted shift windows, per-task power capacity, shared flexible capacity and a total demand limit. At 15-minute resolution, total interval kWh divided by 0.25 hours produces interval-average kW. Peak demand is the maximum of those interval averages. Total energy and energy charges are sums across the scenario horizon.

The default tariff template assumes the forecast starts at midnight: the peak illustrative price applies from 08:00 through 19:45 and the off-peak price otherwise. For a horizon with a different start time, callers must construct a timestamp-aligned price vector; the solver never infers tariff timing. No prices are represented as actual company charges.

Uncertainty scenarios can substitute a lower or upper forecast interval profile as fixed demand. Those are scenario inputs, not simultaneous joint prediction bands or probabilistic feasibility guarantees. Upper-bound demand can make a previously feasible schedule infeasible. Constraints are retained and the scenario is clearly labeled infeasible.

## Emissions and the four different outcomes

For assumed emission factors `g[t]` in kg CO₂e/kWh, scenario emissions are `sum(t) total_kwh[t] * g[t]`. Factors may be constant or a user-defined time-varying vector. They are not the dataset's observed emissions column, measured plant emissions or verified marginal emissions.

The app distinguishes:

- **Energy difference:** always zero between reference and optimized schedules with identical completed tasks and fixed background.
- **Modeled energy-cost difference:** depends on tariff timing; flat tariffs provide no shifting benefit.
- **Peak-demand difference:** can be positive, zero or negative because cost minimization does not directly minimize the peak.
- **Assumed emissions difference:** zero with a constant factor and conserved energy; with varying factors it can be positive or negative. The electricity-cost optimum does not optimize emissions.

No realized energy, financial or sustainability benefit is claimed. Costs exclude demand charges, taxes, maintenance, labor, start-up losses, productivity impacts and penalties. The formulation assumes tasks are interruptible and divisible; applying it to a real plant would require validated operating constraints and prospective measurements.

## API

`simulate_scenario(background_kwh, prices_eur_kwh, tasks, shared_capacity_kw, peak_limit_kw, demand_multiplier=1, emissions_kg_per_kwh=0.4)` returns the solver result, verified schedules when feasible, scenario metrics and explicit assumptions. `optimize_schedule` owns the LP and fair reference formulation. `tariff_profile` generates an illustrative midnight-aligned vector. All outputs are JSON-safe and suitable for lightweight committed artifacts. See [Optimization model](OPTIMIZATION_MODEL.md) for the complete formulation and tests.
