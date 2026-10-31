import logging
import sys
from pathlib import Path
import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ca1.config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    AWS_SESSION_TOKEN,
    PROCESSED_DATA_DIR,
    S3_BUCKET,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


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


def save_and_upload_parquet(df: pd.DataFrame, local_root: Path = PROCESSED_DATA_DIR):
    local_root.mkdir(parents=True, exist_ok=True)
    s3 = get_s3_client()

    uploaded_partitions = []
    total_bytes = 0

    # Group by partition keys: year, month
    for (year, month), partition_df in df.groupby(["year", "month"]):
        partition_rel_path = f"year={year}/month={month:02d}"
        partition_dir = local_root / partition_rel_path
        partition_dir.mkdir(parents=True, exist_ok=True)

        parquet_file = partition_dir / "mumbai_daily_air_quality.parquet"
        
        # Write Parquet with Snappy compression using PyArrow
        table = pa.Table.from_pandas(partition_df)
        pq.write_table(table, parquet_file, compression="SNAPPY")
        file_size = parquet_file.stat().st_size
        total_bytes += file_size

        logger.info("Saved local partition %s (%s rows, %s bytes)", partition_rel_path, len(partition_df), file_size)

        if s3 and S3_BUCKET:
            s3_key = f"processed_data/{partition_rel_path}/mumbai_daily_air_quality.parquet"
            s3.upload_file(str(parquet_file), S3_BUCKET, s3_key)

            # Post-upload verification: confirm object existence and byte size
            head = s3.head_object(Bucket=S3_BUCKET, Key=s3_key)
            remote_size = head.get("ContentLength")
            remote_timestamp = head.get("LastModified")

            if remote_size != file_size:
                logger.error("Size mismatch for %s: local %s vs remote %s", s3_key, file_size, remote_size)
                sys.exit(f"Upload verification failed for {s3_key}")

            logger.info("  Verified S3 object: s3://%s/%s (size=%s bytes, modified=%s)", S3_BUCKET, s3_key, remote_size, remote_timestamp)
            uploaded_partitions.append({
                "s3_key": s3_key,
                "size_bytes": remote_size,
                "rows": len(partition_df),
                "last_modified": str(remote_timestamp),
            })

    logger.info("Parquet storage completed: %s partitions uploaded, %s total bytes", len(uploaded_partitions), total_bytes)
    return uploaded_partitions

