import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import boto3
import requests

from ca1.config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    AWS_SESSION_TOKEN,
    END_DATE,
    OPENAQ_API_KEY,
    OPENAQ_BASE_URL,
    POLLUTANTS,
    RAW_DATA_DIR,
    S3_BUCKET,
    START_DATE,
    TARGET_STATIONS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def get_s3_client():
    if not (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET):
        return None
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN,
    )


def make_request(session, url, params=None):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()

            if response.status_code in {401, 403}:
                logger.error("Authentication failed (%s): %s", response.status_code, response.text[:200])
                sys.exit(f"Fatal auth error: HTTP {response.status_code}")

            if response.status_code == 404:
                logger.warning("Resource not found (%s): %s", url, response.status_code)
                return None

            if response.status_code in RETRYABLE_STATUSES and attempt < MAX_ATTEMPTS:
                delay = int(response.headers.get("x-ratelimit-reset", 2 ** attempt))
                logger.warning("HTTP %s. Retrying in %ss (attempt %s/%s)...", response.status_code, delay, attempt, MAX_ATTEMPTS)
                time.sleep(delay)
                continue

            logger.error("Request failed with status %s: %s", response.status_code, response.text[:200])
            sys.exit(f"Request failed: HTTP {response.status_code}")
        except requests.RequestException as exc:
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 ** attempt)
                continue
            logger.error("Network error: %s", exc)
            sys.exit(f"Network failure: {exc}")
    return None


def get_station_sensors(session, location_id):
    url = f"{OPENAQ_BASE_URL}/locations/{location_id}"
    payload = make_request(session, url)
    if not payload:
        return {}

    results = payload.get("results", [])
    if not results:
        return {}

    sensors = results[0].get("sensors", [])
    # Newest sensors have higher IDs and represent current active feeds
    sorted_sensors = sorted(sensors, key=lambda s: s.get("id", 0), reverse=True)
    active_sensors = {}
    for sensor in sorted_sensors:
        param_name = (sensor.get("parameter") or {}).get("name")
        if param_name in POLLUTANTS and param_name not in active_sensors:
            active_sensors[param_name] = sensor.get("id")
    return active_sensors


def extract_station_hourly(session, sensor_id, start_iso, end_iso):
    url = f"{OPENAQ_BASE_URL}/sensors/{sensor_id}/hours"
    params = {
        "datetime_from": start_iso,
        "datetime_to": end_iso,
        "limit": 1000,
    }
    payload = make_request(session, url, params=params)
    if not payload:
        return []
    return payload.get("results", [])


def extract_all():
    if not OPENAQ_API_KEY:
        sys.exit("OPENAQ_API_KEY is missing from environment")

    session = requests.Session()
    session.headers["X-API-Key"] = OPENAQ_API_KEY

    ingest_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw_subfolder = RAW_DATA_DIR / "openaq" / f"ingest_date={ingest_date}"
    raw_subfolder.mkdir(parents=True, exist_ok=True)

    start_iso = START_DATE.strftime("%Y-%m-%dT00:00:00Z")
    end_iso = END_DATE.strftime("%Y-%m-%dT23:59:59Z")
    logger.info("Extracting OpenAQ readings between %s and %s", start_iso, end_iso)

    s3 = get_s3_client()
    raw_records = []
    total_extracted_rows = 0

    for station in TARGET_STATIONS:
        loc_id = station["location_id"]
        station_name = station["name"]
        logger.info("Querying sensors for station %s (%s)", loc_id, station_name)

        active_sensors = get_station_sensors(session, loc_id)
        for param, sensor_id in active_sensors.items():
            results = extract_station_hourly(session, sensor_id, start_iso, end_iso)
            count = len(results)
            total_extracted_rows += count
            logger.info("  Sensor %s (%s): extracted %s hourly records", sensor_id, param, count)

            # Store raw JSON locally
            file_name = f"location_{loc_id}_{param}_{sensor_id}.json"
            local_path = raw_subfolder / file_name
            with local_path.open("w", encoding="utf-8") as f:
                json.dump(results, f)

            # Upload raw JSON to S3 raw layer
            if s3 and S3_BUCKET:
                s3_key = f"raw_data/openaq/ingest_date={ingest_date}/{file_name}"
                s3.upload_file(str(local_path), S3_BUCKET, s3_key)

            for record in results:
                raw_records.append({
                    "station_id": loc_id,
                    "station_name": station_name,
                    "latitude": station["latitude"],
                    "longitude": station["longitude"],
                    "provider": station["provider"],
                    "sensor_id": sensor_id,
                    "parameter": param,
                    "raw_data": record,
                })

    logger.info("Extraction completed: %s total hourly records extracted across %s stations", total_extracted_rows, len(TARGET_STATIONS))
    return raw_records


if __name__ == "__main__":
    extract_all()
