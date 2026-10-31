import numpy as np
import pandas as pd
import pytest

from ca1.transform import (
    aggregate_openaq_daily,
    clean_openaq_hourly,
    conform_and_merge_datasets,
    load_thresholds,
)


def test_clean_openaq_negative_and_sentinel():
    data = pd.DataFrame([
        {
            "station_id": 1,
            "station_name": "Test Station",
            "provider": "MPCB",
            "latitude": 19.0,
            "longitude": 72.8,
            "sensor_id": 100,
            "parameter": "pm25",
            "value_ugm3": -10.0,
            "observed_at_utc": "2026-10-01T00:00:00Z",
        },
        {
            "station_id": 1,
            "station_name": "Test Station",
            "provider": "MPCB",
            "latitude": 19.0,
            "longitude": 72.8,
            "sensor_id": 100,
            "parameter": "pm25",
            "value_ugm3": 45.0,
            "observed_at_utc": "2026-10-01T01:00:00Z",
        },
        {
            "station_id": 1,
            "station_name": "Test Station",
            "provider": "MPCB",
            "latitude": 19.0,
            "longitude": 72.8,
            "sensor_id": 100,
            "parameter": "pm25",
            "value_ugm3": 5000.0,  # Extreme outlier > 1000
            "observed_at_utc": "2026-10-01T02:00:00Z",
        },
    ])
    cleaned = clean_openaq_hourly(data)
    # Negative value at index 0 had no predecessor, so remains NaN and not imputed
    assert pd.isna(cleaned.loc[cleaned["observed_at_utc"] == "2026-10-01T00:00:00Z", "value_ugm3"].values[0])
    # Valid reading kept as-is
    assert cleaned.loc[cleaned["observed_at_utc"] == "2026-10-01T01:00:00Z", "value_ugm3"].values[0] == 45.0
    # Outlier at index 2 was rejected as invalid (> 1000) and short-gap forward-filled from valid predecessor
    outlier_row = cleaned.loc[cleaned["observed_at_utc"] == "2026-10-01T02:00:00Z"]
    assert outlier_row["value_ugm3"].values[0] == 45.0
    assert outlier_row["is_imputed"].values[0] == True


def test_clean_openaq_deduplication():
    data = pd.DataFrame([
        {
            "station_id": 1,
            "station_name": "Test Station",
            "provider": "MPCB",
            "latitude": 19.0,
            "longitude": 72.8,
            "sensor_id": 100,
            "parameter": "pm25",
            "value_ugm3": 20.0,
            "observed_at_utc": "2026-10-01T00:00:00Z",
        },
        {
            "station_id": 1,
            "station_name": "Test Station",
            "provider": "MPCB",
            "latitude": 19.0,
            "longitude": 72.8,
            "sensor_id": 100,
            "parameter": "pm25",
            "value_ugm3": 25.0,  # Updated duplicate reading
            "observed_at_utc": "2026-10-01T00:00:00Z",
        },
    ])
    cleaned = clean_openaq_hourly(data)
    assert len(cleaned) == 1
    assert cleaned["value_ugm3"].values[0] == 25.0


def test_short_gap_imputation():
    # 1 valid, 2 NaN gaps, 1 valid -> gaps should be forward-filled
    timestamps = [
        "2026-10-01T00:00:00Z",
        "2026-10-01T01:00:00Z",
        "2026-10-01T02:00:00Z",
        "2026-10-01T03:00:00Z",
    ]
    data = pd.DataFrame([
        {
            "station_id": 1,
            "station_name": "Test Station",
            "provider": "MPCB",
            "latitude": 19.0,
            "longitude": 72.8,
            "sensor_id": 100,
            "parameter": "pm25",
            "value_ugm3": 50.0 if i == 0 or i == 3 else np.nan,
            "observed_at_utc": ts,
        }
        for i, ts in enumerate(timestamps)
    ])
    cleaned = clean_openaq_hourly(data)
    # The 2 NaNs should be forward-filled with 50.0 and marked is_imputed=True
    imputed_rows = cleaned[cleaned["is_imputed"]]
    assert len(imputed_rows) == 2
    assert all(imputed_rows["value_ugm3"] == 50.0)


def test_long_gap_never_imputed():
    # 1 valid, 4 NaN gaps -> 4th NaN should remain NaN (limit=3)
    timestamps = [
        "2026-10-01T00:00:00Z",
        "2026-10-01T01:00:00Z",
        "2026-10-01T02:00:00Z",
        "2026-10-01T03:00:00Z",
        "2026-10-01T04:00:00Z",
    ]
    data = pd.DataFrame([
        {
            "station_id": 1,
            "station_name": "Test Station",
            "provider": "MPCB",
            "latitude": 19.0,
            "longitude": 72.8,
            "sensor_id": 100,
            "parameter": "pm25",
            "value_ugm3": 50.0 if i == 0 else np.nan,
            "observed_at_utc": ts,
        }
        for i, ts in enumerate(timestamps)
    ])
    cleaned = clean_openaq_hourly(data)
    # Fifth row (index 4) should remain NaN
    assert pd.isna(cleaned.iloc[4]["value_ugm3"])
    assert cleaned.iloc[4]["is_imputed"] == False


def test_daily_aggregation_18_hour_rule():
    thresholds = {"pm25": 60.0, "pm10": 100.0, "no2": 80.0}

    # Station A: 20 hours present (>= 18) -> valid daily mean
    # Station B: 12 hours present (< 18) -> daily mean becomes NaN
    rows = []
    for h in range(20):
        rows.append({
            "station_id": 1,
            "station_name": "Station A",
            "provider": "MPCB",
            "latitude": 19.0,
            "longitude": 72.8,
            "sensor_id": 100,
            "parameter": "pm25",
            "value_ugm3": 70.0,
            "observed_at_utc": f"2026-10-01T{h:02d}:00:00Z",
            "observed_at_ist": pd.Timestamp(f"2026-10-01 {h:02d}:00:00", tz="Asia/Kolkata"),
            "is_imputed": False,
        })
    for h in range(12):
        rows.append({
            "station_id": 2,
            "station_name": "Station B",
            "provider": "MPCB",
            "latitude": 19.1,
            "longitude": 72.9,
            "sensor_id": 101,
            "parameter": "pm25",
            "value_ugm3": 70.0,
            "observed_at_utc": f"2026-10-01T{h:02d}:00:00Z",
            "observed_at_ist": pd.Timestamp(f"2026-10-01 {h:02d}:00:00", tz="Asia/Kolkata"),
            "is_imputed": False,
        })

    hourly_df = pd.DataFrame(rows)
    daily = aggregate_openaq_daily(hourly_df, thresholds)

    st_a = daily[daily["station_id"] == 1]
    st_b = daily[daily["station_id"] == 2]

    assert st_a["pm25"].values[0] == 70.0
    assert st_a["exceeds_pm25_standard"].values[0] == True  # 70 > 60

    assert pd.isna(st_b["pm25"].values[0])
    assert st_b["exceeds_pm25_standard"].values[0] == False
