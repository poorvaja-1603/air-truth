import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ca1.config import EXTERNAL_DATA_DIR, THRESHOLDS_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Range limits from plan.md section 17 rule 5
MAX_VALID_RANGES = {
    "pm25": 1000.0,
    "pm10": 2000.0,
    "no2": 2000.0,
    "so2": 2000.0,
    "co": 10000.0,
    "o3": 1000.0,
}


def load_thresholds(thresholds_path=THRESHOLDS_PATH):
    if not Path(thresholds_path).exists():
        # Fallback to CPCB NAAQS defaults if file missing
        return {"pm25": 60.0, "pm10": 100.0, "no2": 80.0, "so2": 80.0}
    df = pd.read_csv(thresholds_path)
    return dict(zip(df["parameter"], df["threshold_ugm3"]))


def parse_openaq_hourly_records(raw_records):
    rows = []
    for item in raw_records:
        rec = item["raw_data"]
        val = rec.get("value")
        period = rec.get("period") or {}
        dt_from = period.get("datetimeFrom") or {}
        utc_str = dt_from.get("utc") if isinstance(dt_from, dict) else dt_from

        if not utc_str:
            continue

        rows.append({
            "station_id": item["station_id"],
            "station_name": item["station_name"],
            "provider": item["provider"],
            "latitude": item["latitude"],
            "longitude": item["longitude"],
            "sensor_id": item["sensor_id"],
            "parameter": item["parameter"],
            "value_ugm3": val,
            "observed_at_utc": utc_str,
        })
    return pd.DataFrame(rows)


def clean_openaq_hourly(df):
    if df.empty:
        return df

    # Rule 3: Explicit type casting
    df["station_id"] = df["station_id"].astype("int64")
    df["sensor_id"] = df["sensor_id"].astype("int64")
    df["value_ugm3"] = pd.to_numeric(df["value_ugm3"], errors="coerce")
    df["parameter"] = df["parameter"].astype(str).str.lower()

    # Rule 2: Datetime parsing & IST derivation
    df["observed_at_utc"] = pd.to_datetime(df["observed_at_utc"], utc=True)
    df["observed_at_ist"] = df["observed_at_utc"].dt.tz_convert("Asia/Kolkata")

    # Rule 4 & 5: Sentinel/negative values and range filters
    # Physically impossible values become NaN
    df.loc[df["value_ugm3"] < 0, "value_ugm3"] = np.nan
    for param, max_val in MAX_VALID_RANGES.items():
        mask = (df["parameter"] == param) & (df["value_ugm3"] > max_val)
        df.loc[mask, "value_ugm3"] = np.nan

    # Rule 6: Deduplication: keep latest reading per station, parameter, hour
    df = df.sort_values(["station_id", "parameter", "observed_at_utc"])
    df = df.drop_duplicates(subset=["station_id", "parameter", "observed_at_utc"], keep="last")

    # Rules 7 & 8: Short-gap imputation (<= 3 hours) per station & parameter
    df["is_imputed"] = False
    cleaned_groups = []
    for (st_id, param), group in df.groupby(["station_id", "parameter"]):
        group = group.sort_values("observed_at_utc").copy()
        is_missing = group["value_ugm3"].isna()
        # Impute forward fill with limit=3
        filled = group["value_ugm3"].ffill(limit=3)
        imputed_mask = is_missing & filled.notna()
        group["value_ugm3"] = filled
        group["is_imputed"] = imputed_mask
        cleaned_groups.append(group)

    if cleaned_groups:
        df = pd.concat(cleaned_groups, ignore_index=True)

    return df


def aggregate_openaq_daily(hourly_df, thresholds):
    if hourly_df.empty:
        return pd.DataFrame()

    hourly_df = hourly_df.copy()
    hourly_df["date_ist"] = hourly_df["observed_at_ist"].dt.date

    # Rule 11: 18 of 24 hours rule for valid daily mean
    grouped = hourly_df.groupby(["station_id", "station_name", "provider", "latitude", "longitude", "date_ist", "parameter"])
    agg = grouped.agg(
        hourly_count=("value_ugm3", "count"),
        daily_mean=("value_ugm3", "mean"),
    ).reset_index()

    # Apply 18/24 hour completeness rule
    agg["daily_mean_valid"] = np.where(agg["hourly_count"] >= 18, agg["daily_mean"], np.nan)

    # Pivot pollutants to wide format: pm25, pm10, no2
    pivoted = agg.pivot(
        index=["station_id", "station_name", "provider", "latitude", "longitude", "date_ist"],
        columns="parameter",
        values="daily_mean_valid",
    ).reset_index()

    pivoted.columns.name = None
    pivoted["date"] = pd.to_datetime(pivoted["date_ist"])
    pivoted = pivoted.drop(columns=["date_ist"])

    # Ensure canonical columns exist
    for col in ["pm25", "pm10", "no2"]:
        if col not in pivoted.columns:
            pivoted[col] = np.nan

    # Rule 12: Business flag - exceeds_24h_standard
    pm25_thresh = thresholds.get("pm25", 60.0)
    pm10_thresh = thresholds.get("pm10", 100.0)
    no2_thresh = thresholds.get("no2", 80.0)

    pivoted["exceeds_pm25_standard"] = pivoted["pm25"] > pm25_thresh
    pivoted["exceeds_pm10_standard"] = pivoted["pm10"] > pm10_thresh
    pivoted["exceeds_no2_standard"] = pivoted["no2"] > no2_thresh
    pivoted["source"] = "openaq_api"

    return pivoted


def load_mendeley_historical(thresholds, external_dir=EXTERNAL_DATA_DIR):
    csv_file = Path(external_dir) / "all_stations_combined.csv"
    if not csv_file.exists():
        logger.warning("External dataset file not found at %s", csv_file)
        return pd.DataFrame()

    raw_mendeley = pd.read_csv(csv_file)
    logger.info("Loaded %s historical records from %s", len(raw_mendeley), csv_file.name)

    # Filter/clean negative and extreme values
    for col in ["pm25", "pm10", "no2"]:
        if col in raw_mendeley.columns:
            raw_mendeley.loc[raw_mendeley[col] < 0, col] = np.nan
            max_val = MAX_VALID_RANGES.get(col, 2000.0)
            raw_mendeley.loc[raw_mendeley[col] > max_val, col] = np.nan

    raw_mendeley["date"] = pd.to_datetime(raw_mendeley["date"], errors="coerce")
    raw_mendeley = raw_mendeley.dropna(subset=["date"])

    # Coordinates mapping for known stations
    coords_map = {
        6945: (19.0726, 72.8845),
        6967: (19.0396, 72.8624),
        7035: (19.0665, 72.8696),
        6948: (19.0886, 72.8679),
        7850: (19.0544, 72.8402),
    }

    raw_mendeley["latitude"] = raw_mendeley["station_id"].map(lambda sid: coords_map.get(sid, (np.nan, np.nan))[0])
    raw_mendeley["longitude"] = raw_mendeley["station_id"].map(lambda sid: coords_map.get(sid, (np.nan, np.nan))[1])
    raw_mendeley["provider"] = "MPCB"
    raw_mendeley["source"] = "mendeley_historical"

    # Business flags
    pm25_thresh = thresholds.get("pm25", 60.0)
    pm10_thresh = thresholds.get("pm10", 100.0)
    no2_thresh = thresholds.get("no2", 80.0)

    raw_mendeley["exceeds_pm25_standard"] = raw_mendeley["pm25"] > pm25_thresh
    raw_mendeley["exceeds_pm10_standard"] = raw_mendeley["pm10"] > pm10_thresh
    raw_mendeley["exceeds_no2_standard"] = raw_mendeley["no2"] > no2_thresh

    canonical_cols = [
        "station_id", "station_name", "provider", "latitude", "longitude",
        "date", "pm25", "pm10", "no2",
        "exceeds_pm25_standard", "exceeds_pm10_standard", "exceeds_no2_standard", "source"
    ]
    return raw_mendeley[canonical_cols]


def conform_and_merge_datasets(openaq_daily_df, mendeley_df):
    canonical_cols = [
        "station_id", "station_name", "provider", "latitude", "longitude",
        "date", "pm25", "pm10", "no2",
        "exceeds_pm25_standard", "exceeds_pm10_standard", "exceeds_no2_standard", "source"
    ]
    frames = []
    if not openaq_daily_df.empty:
        frames.append(openaq_daily_df[canonical_cols])
    if not mendeley_df.empty:
        frames.append(mendeley_df[canonical_cols])

    if not frames:
        return pd.DataFrame(columns=canonical_cols)

    merged = pd.concat(frames, ignore_index=True)
    merged["station_id"] = merged["station_id"].astype("int64")
    merged["year"] = merged["date"].dt.year.astype("int32")
    merged["month"] = merged["date"].dt.month.astype("int32")

    # Sort deterministically
    merged = merged.sort_values(["date", "station_id", "source"]).reset_index(drop=True)
    return merged

