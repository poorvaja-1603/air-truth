import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# OpenAQ API Configuration
OPENAQ_API_KEY = os.environ.get("OPENAQ_API_KEY")
OPENAQ_BASE_URL = "https://api.openaq.org/v3"

# AWS Configuration
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.environ.get("AWS_SESSION_TOKEN")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
S3_BUCKET = os.environ.get("S3_BUCKET")

# Local directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"
REFERENCE_DIR = BASE_DIR / "reference"
THRESHOLDS_PATH = REFERENCE_DIR / "pollutant_thresholds.csv"

# Target Stations in Mumbai (5 stations representing varied urban environments)
TARGET_STATIONS = [
    {
        "location_id": 6945,
        "name": "Kurla, Mumbai - MPCB",
        "latitude": 19.0726,
        "longitude": 72.8845,
        "provider": "MPCB",
        "mendeley_name": "Kurla, Mumbai - MPCB",
    },
    {
        "location_id": 6967,
        "name": "Sion, Mumbai - MPCB",
        "latitude": 19.0396,
        "longitude": 72.8624,
        "provider": "MPCB",
        "mendeley_name": "Sion, Mumbai - MPCB",
    },
    {
        "location_id": 3409482,
        "name": "Bandra Kurla Complex, Mumbai - MPCB",
        "latitude": 19.0665,
        "longitude": 72.8696,
        "provider": "MPCB",
        "mendeley_name": "Bandra Kurla Complex, Mumbai - MPCB",
    },
    {
        "location_id": 6927,
        "name": "Colaba, Mumbai - MPCB",
        "latitude": 18.9067,
        "longitude": 72.8147,
        "provider": "MPCB",
        "mendeley_name": None,
    },
    {
        "location_id": 3409323,
        "name": "Worli, Mumbai - MPCB",
        "latitude": 19.0163,
        "longitude": 72.8166,
        "provider": "MPCB",
        "mendeley_name": None,
    },
]

# Pollutants of interest
POLLUTANTS = ["pm25", "pm10", "no2"]

# Extraction window: last 30 days
END_DATE = datetime.now(timezone.utc)
START_DATE = END_DATE - timedelta(days=30)

