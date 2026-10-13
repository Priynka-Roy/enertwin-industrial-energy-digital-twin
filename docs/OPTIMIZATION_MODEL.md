# Mathematical scheduling model

EnerTwin solves a linear program with SciPy's open-source HiGHS solver. The demand profile is an observed historical profile or a statistical forecast, **assumed fixed background demand** for the scenario. Additional hypothetical flexible workloads are added to it. The original dataset contains no equipment capacities, production scheduling requirements or controllable share; none are inferred. All workload values, tariffs and limits are user assumptions.

## Variables and objective

For task `j` and interval `t`, `x[j,t] >= 0` is allocated energy in **kWh**. With interval duration `Δ = 0.25 h`, background `b[t]` in kWh and price `p[t]` in €/kWh, minimize:

```text
sum(t) p[t] * (b[t] + sum(j) x[j,t])
```

The background cost is constant and omitted from the solver objective, then included in reported costs. Tasks are continuously divisible, interruptible and may execute concurrently. This is an LP, not a start-time or indivisible-batch model. No minimum duration, task precedence, start-up cost, ramp limit or process quality constraint is claimed.

## Constraints

For each task with required energy `E[j]`, max power `P[j]` and permitted interval window `[start[j], end[j])`:

```text
sum(t) x[j,t] = E[j]
0 <= x[j,t] <= P[j] * Δ within its window
x[j,t] = 0 outside its window
sum(j) x[j,t] <= shared_capacity_kw * Δ, for each interval
b[t] + sum(j) x[j,t] <= peak_limit_kw * Δ, for each interval
```

Thus one kWh in a quarter hour corresponds to **four kW of interval-average demand**. The peak constraint limits interval-average power, not subinterval instantaneous transients. All inputs must be finite and nonnegative; the implementation's illustrative tariff domain excludes negative prices. Window endpoints are integer interval indices and the end is exclusive. The API supports smaller horizons for validation; the application uses 96 quarter-hour slots.

## Fair reference schedule

The reference baseline is another LP minimizing `sum(j,t) t * x[j,t]` under **exactly the same constraints**. It favors early completion while accounting jointly for overlapping windows and shared capacity. It is not an observed plant schedule. A sequential greedy assignment could falsely declare infeasibility, so both reference and cost-minimizing schedules use a joint solver.

Both schedules complete the same task energy and use the same background profile. Rescheduling cannot produce energy savings in this formulation. Cost changes arise from assumed time-varying prices; flat prices produce zero arbitrage benefit. The cost objective does not minimize peak demand independently: its selected optimum can have a higher or lower peak than the reference. A negative reported peak reduction means the optimized schedule's peak is higher. No demand charge is included.

## Feasibility and validation

Background demand already exceeding the peak limit is immediately infeasible. Other impossible combinations are reported from HiGHS without silently relaxing constraints. Invalid input raises `ValueError`. Infeasible scenarios return a status and message, without fabricated schedules or financial results. Successful solver output undergoes independent checks of task completion, scheduling windows, nonnegativity, individual and shared capacity, peak limits, and total energy balance before it is labeled feasible.

`tests/test_optimization.py` verifies a hand-calculated optimum, exhaustive enumeration of a small binary-extreme-point case, fractional allocations, jointly constrained reference scheduling, unit conversion, conservation, capacities, windows, invalid inputs and infeasibility. It also checks zero flexibility, flat prices and emissions consistency.

## Reproducible numerical example

Four quarter-hour slots each have background 1 kWh. A hypothetical task requires 2 kWh, with a maximum of 4 kW, full-horizon availability, shared capacity 4 kW and peak limit 8 kW. At prices `[4, 3, 1, 2]` €/kWh (deliberately simple mathematical fixture, **not a real tariff**), the reference allocates `[1,1,0,0]` kWh and the cost optimum `[0,0,1,1]` kWh. Total demand is 6 kWh in either schedule; modeled costs are €17 and €13, respectively, with 8 kW peak demand for each. These values are computed and asserted in the automated test.

See [Digital twin assumptions](DIGITAL_TWIN.md) for scenario interpretation. See the generated experiment results for real-forecast scenarios with explicitly hypothetical workload and tariff assumptions.

## Version 2 finite-scenario robust formulation

Let `b[s,t]` be background kWh for supplied scenario `s`. Keep the same decision variable `x[j,t]` for **every scenario** and minimize the same flexible-energy charges. Replace the deterministic peak constraint with:

```text
b[s,t] + sum(j) x[j,t] <= peak_limit_kw * Δ, for every s,t
```

All task-completion, scheduling-window, individual-power and shared-capacity constraints remain unchanged. This is equivalent to a single LP whose background is `max(s) b[s,t]` at each interval. The envelope is a mathematical constraint reduction; it need not be a physically occurring path and its total energy/cost must not be reported as an actual or mean scenario outcome. Report supplied scenario costs separately.

Under deterministic tariffs and exogenous additive background, scenario `s` total cost is `C[s] + sum(j,t) p[t]*x[j,t]`, where `C[s]` is decision-independent. Mean, probability-weighted expected and worst-case total-cost objectives therefore have the same minimizers **over the same feasible set**. There is no distinct informative CVaR scheduling policy under these assumptions. Robust scheduling differs from the deterministic policy through its feasible region. A robust schedule may cost more, cost the same, or be infeasible; it cannot improve the optimal flexible-cost value merely by adding constraints.

The API `optimize_robust` checks nonnegative finite scenario matrices, calls SciPy HiGHS and independently verifies the shared allocation against every supplied scenario. Its guarantee is finite-set feasibility only: unseen demand can still exceed a cap. An arithmetic mean across illustrative scenarios is a descriptive mean, not a calibrated expected future bill.

The robust baseline minimizes the same early-completion reference objective under robust constraints. For deterministic-versus-robust policy comparisons, both policies are evaluated on identical supplied profiles and the same observed background. Their respective reference schedules should not be confused with an observed factory schedule. Zero feasible schedules and background-only cap exceedance are explicitly reported; constraints are never silently relaxed.
