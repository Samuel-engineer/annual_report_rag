import logging
from typing import Any, cast

import boto3

from .config import Settings
from .filings import extract_filings
from .sec_client import download_filing
from .storage import (
    S3Client,
    decode_s3_object_key,
    load_submissions,
    upload_filing,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = cast(S3Client, boto3.client("s3"))


def get_settings() -> Settings:
    return Settings.from_env()


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, int]:
    logger.info("Received event, processing S3 records")
    records = event.get("Records")
    if not isinstance(records, list) or not records:
        raise ValueError("Expected an S3 ObjectCreated event with at least one record.")

    cfg = get_settings()
    documents_uploaded = 0
    for record in records:
        bucket_name, encoded_key = _record_location(record)
        key = decode_s3_object_key(encoded_key)
        payload = load_submissions(s3_client, bucket_name, key)

        for filing in extract_filings(payload):
            document = download_filing(filing.archive_url, cfg.sec_user_agent)
            upload_filing(
                s3_client=s3_client,
                bucket_name=cfg.raw_bucket_name,
                filing=filing,
                body=document,
            )
            documents_uploaded += 1

    logger.info("Total filing documents uploaded: %d", documents_uploaded)
    return {"documents_uploaded": documents_uploaded}


def _record_location(record: Any) -> tuple[str, str]:
    if not isinstance(record, dict):
        raise TypeError("Each S3 event record must be an object.")
    s3_data = record.get("s3")
    if not isinstance(s3_data, dict):
        raise TypeError("S3 event record is missing its s3 object.")
    bucket_data = s3_data.get("bucket")
    object_data = s3_data.get("object")
    if not isinstance(bucket_data, dict) or not isinstance(object_data, dict):
        raise TypeError("S3 event record is missing its bucket or object details.")
    bucket_name = bucket_data.get("name")
    key = object_data.get("key")
    if not isinstance(bucket_name, str) or not bucket_name:
        raise ValueError("S3 event record has an invalid bucket name.")
    if not isinstance(key, str) or not key:
        raise ValueError("S3 event record has an invalid object key.")
    return bucket_name, key
