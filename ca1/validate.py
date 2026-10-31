import logging
import sys
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "station_id", "station_name", "provider", "latitude", "longitude",
    "date", "pm25", "pm10", "no2",
    "exceeds_pm25_standard", "exceeds_pm10_standard", "exceeds_no2_standard",
    "source", "year", "month"
]


def validate_dataset(df: pd.DataFrame) -> bool:
    if df.empty:
        logger.error("Validation failed: dataset is empty.")
        raise ValueError("Dataset has 0 rows.")

    logger.info("Starting pre-upload validation on %s rows...", len(df))

    # 1. Required columns check
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        logger.error("Missing required columns: %s", missing_cols)
        raise ValueError(f"Missing columns: {missing_cols}")

    # 2. Type checks
    if not pd.api.types.is_integer_dtype(df["station_id"]):
        raise TypeError("station_id must be integer")
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        raise TypeError("date must be datetime")
    if not pd.api.types.is_bool_dtype(df["exceeds_pm25_standard"]):
        raise TypeError("exceeds_pm25_standard must be boolean")

    # 3. Physical range checks (no negative values allowed)
    for col, max_limit in [("pm25", 1000.0), ("pm10", 2000.0), ("no2", 2000.0)]:
        neg_count = (df[col] < 0).sum()
        if neg_count > 0:
            logger.error("Found %s negative values in column %s", neg_count, col)
            raise ValueError(f"Negative values detected in {col}")

        over_limit = (df[col] > max_limit).sum()
        if over_limit > 0:
            logger.error("Found %s values exceeding limit (%s) in column %s", over_limit, max_limit, col)
            raise ValueError(f"Extreme outliers detected in {col}")

    # 4. Source values check
    valid_sources = {"openaq_api", "mendeley_historical"}
    invalid_sources = set(df["source"].unique()) - valid_sources
    if invalid_sources:
        raise ValueError(f"Invalid sources present: {invalid_sources}")

    # Log summary statistics
    pm25_exceed = df["exceeds_pm25_standard"].sum()
    pm10_exceed = df["exceeds_pm10_standard"].sum()
    logger.info("Validation passed successfully:")
    logger.info("  Total rows: %s", len(df))
    logger.info("  Date range: %s to %s", df["date"].min().strftime("%Y-%m-%d"), df["date"].max().strftime("%Y-%m-%d"))
    logger.info("  Stations represented: %s (%s)", df["station_id"].nunique(), list(df["station_name"].unique()))
    logger.info("  PM2.5 Exceedances (> 60 ug/m3): %s / %s", pm25_exceed, df["pm25"].notna().sum())
    logger.info("  PM10 Exceedances (> 100 ug/m3): %s / %s", pm10_exceed, df["pm10"].notna().sum())
    return True
