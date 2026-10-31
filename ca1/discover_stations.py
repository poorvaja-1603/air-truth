import csv
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.openaq.org/v3"
MUMBAI_BBOX = "72.75,18.85,73.05,19.30"
RECENT_DAYS = 14
PAGE_SIZE = 1000
MAX_ATTEMPTS = 3
OUTPUT_PATH = Path("data/discovery/mumbai_locations.csv")


def get_json(session, path, params):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = session.get(f"{BASE_URL}{path}", params=params, timeout=30)
        remaining = response.headers.get("x-ratelimit-remaining")
        print(f"GET {response.url} -> {response.status_code} (remaining: {remaining})")
        if response.status_code == 429 and attempt < MAX_ATTEMPTS:
            time.sleep(int(response.headers.get("x-ratelimit-reset", 60)) + 1)
            continue
        if response.status_code != 200:
            sys.exit(f"Request failed: {response.status_code} {response.text[:300]}")
        return response.json()


def utc_value(field):
    return field.get("utc") if isinstance(field, dict) else field


def parse_utc(text):
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def fetch_locations(session):
    results = []
    page = 1
    while True:
        payload = get_json(
            session,
            "/locations",
            {"bbox": MUMBAI_BBOX, "limit": PAGE_SIZE, "page": page},
        )
        batch = payload.get("results", [])
        results.extend(batch)
        if len(batch) < PAGE_SIZE:
            return results
        page += 1


def to_row(location, cutoff):
    last_seen = parse_utc(utc_value(location.get("datetimeLast")))
    coordinates = location.get("coordinates") or {}
    provider = location.get("provider") or {}
    sensors = ";".join(
        f"{(s.get('parameter') or {}).get('name')}:{s.get('id')}"
        for s in location.get("sensors", [])
    )
    return {
        "location_id": location.get("id"),
        "name": location.get("name"),
        "provider": provider.get("name"),
        "latitude": coordinates.get("latitude"),
        "longitude": coordinates.get("longitude"),
        "datetime_last_utc": last_seen.isoformat() if last_seen else "",
        "is_recent": bool(last_seen and last_seen >= cutoff),
        "sensors": sensors,
    }


def main():
    load_dotenv()
    api_key = os.environ.get("OPENAQ_API_KEY")
    if not api_key:
        sys.exit("OPENAQ_API_KEY is not set")

    session = requests.Session()
    session.headers["X-API-Key"] = api_key

    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
    rows = [to_row(location, cutoff) for location in fetch_locations(session)]
    rows.sort(key=lambda row: (not row["is_recent"], str(row["name"])))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    recent = [row for row in rows if row["is_recent"]]
    print(f"\n{len(rows)} locations in the Mumbai bounding box, {len(recent)} reported in the last {RECENT_DAYS} days")
    for row in recent:
        print(f"{row['location_id']:>8}  {row['name']}  [{row['provider']}]  last={row['datetime_last_utc']}  sensors={row['sensors']}")
    print(f"\nFull list written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
