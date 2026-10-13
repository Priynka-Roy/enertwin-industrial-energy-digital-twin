# Dataset card

EnerTwin AI uses the [UCI Steel Industry Energy Consumption dataset](https://archive.ics.uci.edu/dataset/851/steel+industry+energy+consumption), DOI [10.24432/C52G8C](https://doi.org/10.24432/C52G8C). UCI describes electricity records from DAEWOO Steel Co. Ltd., Gwangyang, South Korea. This is one observational facility dataset, not a record of production scheduling interventions.

**Attribution:** Sathishkumar V E, Changsun Shin, and Yongyun Cho (2021). *Steel Industry Energy Consumption* [Dataset]. UCI Machine Learning Repository. DOI 10.24432/C52G8C. Distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Software is independently MIT licensed. The authors and plant do not endorse this project.

| Field | Source meaning/unit | Project treatment |
|---|---|---|
| date | Timestamp | Parse day first; explicitly normalize source midnight sequence |
| Usage_kWh | Interval electricity, kWh | Forecast target; historical lags only |
| Lagging_Current_Reactive.Power_kVarh | Reactive energy, kVarh | Descriptive analysis only |
| Leading_Current_Reactive_Power_kVarh | Reactive energy, kVarh | Descriptive analysis only |
| Lagging_Current_Power_Factor | Percent | Descriptive analysis only |
| Leading_Current_Power_Factor | Percent | Descriptive analysis only |
| CO2(tCO2) | Header implies tonnes; UCI lists ppm | Unresolved unit conflict; no emissions conversion or predictive input |
| NSM | Seconds from midnight | Validate against timestamps; calendar features reconstructed from timestamps |
| WeekStatus | Weekday/weekend label | Descriptive consistency check |
| Day_of_week | Named weekday | Descriptive consistency check |
| Load_Type | Light, medium, maximum category | Observational stratification; never a future feature or controllable workload |

Independent ingestion confirms 35,040 observations, no missing values, no duplicate corrected timestamps and exact 15-minute spacing. All source weekday labels match interval-start days and all NSM values match corrected interval-end seconds. Total observed energy is 959,636.71 kWh; the median is 4.57 kWh/interval and the largest interval is 157.18 kWh, equivalent to 628.72 kW average power over 15 minutes. UCI lists 35,040 instances and no missing values. The ingestion report records the downloaded file hash, measured row count, timestamp coverage, gaps, duplicate times, missingness and value checks. No timezone is supplied. A source defect places each day's final `00:00` row on the same calendar date after `23:45`. The ingestion parser moves those 365 sequence-confirmed rows forward one day, treating them as interval ends. It preserves original row order, consumption values and raw bytes; it does not sort the erroneous dates and pretend the series was valid. Corrected coverage is 2018-01-01 00:15 through 2019-01-01 00:00, a continuous 35,040-interval year. Source weekday labels agree with interval-start days, including corrected midnight ends. Calendar forecasting features refer to interval starts. The timezone remains naive because the source does not declare it. Interval energy becomes average power using `kW = kWh / 0.25`; this is not instantaneous demand.

The original CSV has 2,731,389 bytes and SHA-256 `9b1cee6f9cb9cd9df2b95814ca90a9a2ff15b7f5f1fba0fae3c643e82072eacc`; the source ZIP has 481,973 bytes. Original download bytes remain unchanged under `data/raw/` and are excluded from Git. Deployment files are transformations: parsed timestamps, typed columns, validated observations, derived summaries and predictions. These derivatives retain this attribution. Validation rejects conflicting timestamps and invalid target values rather than silently interpolating them. See generated provenance/validation reports for measured results.

The dataset supplies no equipment capacities, deadlines, job precedence, electricity tariffs, causal flexibility fraction, weather forecasts, marginal grid emissions or independently observed savings. All simulator workloads, prices, caps and emissions factors are explicit hypothetical assumptions.
