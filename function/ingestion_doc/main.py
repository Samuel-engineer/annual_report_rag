import logging
from typing import Any, cast

import boto3

from .config import Settings
from .filings import extract_filings
from .sec_client import download_filing
from .storage import (
    S3Client,
    filing_is_current,
    load_submissions,
    upload_filing,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = cast(S3Client, boto3.client("s3"))


def get_settings() -> Settings:
    return Settings.from_env()


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, int]:
    logger.info("Received workflow event, processing submissions")
    submissions = event.get("submissions")
    if not isinstance(submissions, list) or not submissions:
        raise ValueError("Expected a non-empty submissions list.")

    cfg = get_settings()
    documents_uploaded = 0
    documents_skipped = 0
    for submission in submissions:
        enterprise, bucket_name, key = _submission_location(submission)
        if bucket_name != cfg.excel_bucket_name:
            raise ValueError(
                f"Submission bucket {bucket_name!r} does not match the configured "
                f"Excel bucket {cfg.excel_bucket_name!r}."
            )
        payload = load_submissions(s3_client, bucket_name, key)

        for filing in extract_filings(payload):
            if filing_is_current(s3_client, cfg.raw_bucket_name, filing):
                documents_skipped += 1
                logger.info(
                    "Skipping already ingested filing %s",
                    filing.accession_number,
                )
                continue
            document = download_filing(filing.archive_url, cfg.sec_user_agent)
            upload_filing(
                s3_client=s3_client,
                bucket_name=cfg.raw_bucket_name,
                filing=filing,
                body=document,
                enterprise=enterprise,
            )
            documents_uploaded += 1

    logger.info("Total filing documents uploaded: %d", documents_uploaded)
    logger.info("Total filing documents skipped: %d", documents_skipped)
    return {
        "documents_uploaded": documents_uploaded,
        "documents_skipped": documents_skipped,
    }


def _submission_location(submission: Any) -> tuple[str, str, str]:
    if not isinstance(submission, dict):
        raise TypeError("Each submission reference must be an object.")
    enterprise = submission.get("enterprise")
    bucket_name = submission.get("bucket")
    key = submission.get("key")
    if not isinstance(enterprise, str) or not enterprise:
        raise ValueError("Submission reference has an invalid enterprise.")
    if not isinstance(bucket_name, str) or not bucket_name:
        raise ValueError("Submission reference has an invalid bucket name.")
    if not isinstance(key, str) or not key:
        raise ValueError("Submission reference has an invalid object key.")
    return enterprise, bucket_name, key
