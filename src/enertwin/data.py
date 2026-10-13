"""End-of-interval sensor data with strict timestamps and no implicit repair."""

from pathlib import Path

import numpy as np
import pandas as pd

TARGET = "Usage_kWh"
NUMERIC = [
    TARGET,
    "Lagging_Current_Reactive.Power_kVarh",
    "Leading_Current_Reactive_Power_kVarh",
    "CO2(tCO2)",
    "Lagging_Current_Power_Factor",
    "Leading_Current_Power_Factor",
    "NSM",
]
CATEGORICAL = ["WeekStatus", "Day_of_week", "Load_Type"]
UNITS = {
    TARGET: "kWh / 15 min",
    "Lagging_Current_Reactive.Power_kVarh": "kVarh",
    "Leading_Current_Reactive_Power_kVarh": "kVarh",
    "Lagging_Current_Power_Factor": "%",
    "Leading_Current_Power_Factor": "%",
    "CO2(tCO2)": "unresolved (column tCO2 versus UCI ppm)",
    "NSM": "s",
}


def parse_timestamps(values: pd.Series) -> pd.DatetimeIndex:
    """Repair source same-date midnight after 23:45 to next-day interval end.

    This documented sequence-based correction leaves original bytes/order intact.
    Explicit 24:00 is also normalized; ordinary midnight timestamps are unchanged.
    """
    text = values.astype(str)
    end_of_day = text.str.endswith("24:00")
    normalized = text.str.replace(r"24:00$", "00:00", regex=True)
    parsed = pd.to_datetime(normalized, format="%d/%m/%Y %H:%M", errors="raise")
    same_date_midnight = (
        parsed.dt.hour.eq(0)
        & parsed.dt.minute.eq(0)
        & parsed.shift().dt.hour.eq(23)
        & parsed.shift().dt.minute.eq(45)
        & parsed.dt.normalize().eq(parsed.shift().dt.normalize())
    )
    parsed = parsed + pd.to_timedelta((end_of_day | same_date_midnight).astype(int), unit="D")
    return pd.DatetimeIndex(parsed, name="timestamp")


def validate_data(frame: pd.DataFrame) -> dict:
    required = set(NUMERIC + CATEGORICAL)
    if not required.issubset(frame):
        raise ValueError(f"Missing columns: {sorted(required - set(frame))}")
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.empty or frame.index.hasnans:
        raise ValueError("Valid nonempty DatetimeIndex required")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("Timestamps must be unique and chronological")
    if not (frame.index.to_series().diff().dropna() == pd.Timedelta("15min")).all():
        raise ValueError(
            "Telemetry must have exact 15-minute spacing; investigate gaps before forecasting"
        )
    values = frame[NUMERIC].to_numpy(dtype=float)
    if not np.isfinite(values).all() or frame[CATEGORICAL].isna().any().any():
        raise ValueError("Missing or nonfinite observations need explicit investigation")
    if (frame[TARGET] < 0).any():
        raise ValueError("Consumption cannot be negative")
    for field in ["Lagging_Current_Power_Factor", "Leading_Current_Power_Factor"]:
        if not frame[field].between(0, 100).all():
            raise ValueError(f"{field} outside percent range")
    if not frame.Load_Type.isin(["Light_Load", "Medium_Load", "Maximum_Load"]).all():
        raise ValueError("Unexpected observational load category")
    end_seconds = frame.index.hour * 3600 + frame.index.minute * 60
    interval_start = frame.index - pd.Timedelta("15min")
    return {
        "rows": len(frame),
        "start": str(frame.index.min()),
        "end": str(frame.index.max()),
        "missing": frame.isna().sum().to_dict(),
        "duplicate_timestamps": int(frame.index.duplicated().sum()),
        "interval_minutes": 15,
        "target_min": float(frame[TARGET].min()),
        "target_max": float(frame[TARGET].max()),
        "calendar_end_day_disagreements": int(
            (frame.Day_of_week.to_numpy() != frame.index.day_name()).sum()
        ),
        "calendar_interval_start_day_disagreements": int(
            (frame.Day_of_week.to_numpy() != interval_start.day_name()).sum()
        ),
        "nsm_end_seconds_disagreements": int((frame.NSM.to_numpy() != end_seconds).sum()),
        "load_category_counts": frame.Load_Type.value_counts().to_dict(),
    }


def load_data(path: Path) -> tuple[pd.DataFrame, dict]:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if "date" not in frame:
        raise ValueError("Source date column missing")
    source_dates = frame.pop("date")
    frame.index = parse_timestamps(source_dates)
    quality = validate_data(frame)
    raw_dates = pd.to_datetime(
        source_dates.str.replace(r"24:00$", "00:00", regex=True), format="%d/%m/%Y %H:%M"
    )
    quality["same_date_midnight_corrections"] = int((frame.index != raw_dates).sum())
    frame["interval_start"] = frame.index - pd.Timedelta("15min")
    frame["average_power_kw"] = frame[TARGET] / 0.25
    return frame, quality
