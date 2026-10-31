import logging
import sys
import time

from ca1.config import THRESHOLDS_PATH
from ca1.extract import extract_all
from ca1.load import save_and_upload_parquet
from ca1.transform import (
    aggregate_openaq_daily,
    clean_openaq_hourly,
    conform_and_merge_datasets,
    load_mendeley_historical,
    load_thresholds,
    parse_openaq_hourly_records,
)
from ca1.validate import validate_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ca1_pipeline")


def run():
    start_time = time.time()
    logger.info("=================================================================")
    logger.info("AIRTRUTH MUMBAI - CA1 DATA PIPELINE EXECUTION")
    logger.info("=================================================================")

    # 1. Load Reference Thresholds
    logger.info("[STAGE 0] Loading pollutant thresholds...")
    thresholds = load_thresholds(THRESHOLDS_PATH)
    logger.info("  Thresholds loaded: %s", thresholds)

    # 2. Extraction Stage
    logger.info("\n[STAGE 1] Ingesting multi-source data...")
    raw_api_records = extract_all()
    extracted_api_count = len(raw_api_records)
    logger.info("  Extracted %s raw hourly readings from OpenAQ API", extracted_api_count)

    # 3. Transformation Stage
    logger.info("\n[STAGE 2] Transforming & harmonising datasets...")
    # 3a. Process OpenAQ API stream
    parsed_api_df = parse_openaq_hourly_records(raw_api_records)
    logger.info("  Parsed %s OpenAQ hourly rows into structured DataFrame", len(parsed_api_df))

    cleaned_hourly_df = clean_openaq_hourly(parsed_api_df)
    logger.info("  Cleaned OpenAQ hourly rows: %s (imputed gaps count: %s)", len(cleaned_hourly_df), cleaned_hourly_df["is_imputed"].sum())

    openaq_daily_df = aggregate_openaq_daily(cleaned_hourly_df, thresholds)
    logger.info("  Aggregated OpenAQ to daily level: %s station-days (18/24h rule applied)", len(openaq_daily_df))

    # 3b. Process Mendeley historical baseline stream
    mendeley_daily_df = load_mendeley_historical(thresholds)
    logger.info("  Loaded %s Mendeley historical station-days", len(mendeley_daily_df))

    # 3c. Conform and merge both streams
    conformed_df = conform_and_merge_datasets(openaq_daily_df, mendeley_daily_df)
    logger.info("  Conformed unified dataset: %s total station-days across %s to %s",
                len(conformed_df),
                conformed_df["date"].min().strftime("%Y-%m-%d"),
                conformed_df["date"].max().strftime("%Y-%m-%d"))

    # 4. Validation Stage
    logger.info("\n[STAGE 3] Running data contract & quality validations...")
    validate_dataset(conformed_df)

    # 5. Storage / Load Stage
    logger.info("\n[STAGE 4] Writing partitioned Parquet and uploading to AWS S3...")
    uploaded_partitions = save_and_upload_parquet(conformed_df)

    # 6. Pipeline Execution Summary
    elapsed = time.time() - start_time
    logger.info("\n=================================================================")
    logger.info("EXECUTION SUMMARY - ALL CA1 MILESTONES COMPLETED SUCCESSFULLY")
    logger.info("=================================================================")
    logger.info("  Total Runtime: %.2f seconds", elapsed)
    logger.info("  OpenAQ API Raw Readings: %s rows", extracted_api_count)
    logger.info("  OpenAQ Cleaned Hourly:   %s rows", len(cleaned_hourly_df))
    logger.info("  OpenAQ Daily Aggregates: %s rows", len(openaq_daily_df))
    logger.info("  Mendeley Historical:     %s rows", len(mendeley_daily_df))
    logger.info("  Final Conformed Dataset: %s rows", len(conformed_df))
    logger.info("  Partitions Uploaded:     %s monthly partitions to S3", len(uploaded_partitions))
    logger.info("=================================================================")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        logger.error("Pipeline run failed: %s", exc, exc_info=True)
        sys.exit(1)

