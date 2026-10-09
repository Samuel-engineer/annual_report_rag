import logging
from typing import Any, cast

import boto3

from .config import Settings
from .sec_client import fetch_submissions
from .storage import (
    S3PutObjectClient,
    submissions_s3_key,
    upload_submissions,
)
from .utils import enterprise_s3_key, get_enterprises

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = cast(S3PutObjectClient, boto3.client("s3"))


def get_settings() -> Settings:
    return Settings.from_env()


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    cfg = get_settings()
    enterprises = get_enterprises(event)
    results: dict[str, dict[str, str]] = {}

    for enterprise_name, cik in enterprises.items():
        enterprise_key = enterprise_s3_key(enterprise_name)
        payload = fetch_submissions(cik, cfg.sec_user_agent)
        key = submissions_s3_key(enterprise_key, cik)
        upload_submissions(
            s3_client=s3_client,
            bucket_name=cfg.excel_bucket_name,
            key=key,
            body=payload,
        )
        results[enterprise_name] = {
            "cik": cik,
            "bucket": cfg.excel_bucket_name,
            "key": key,
        }
        logger.info(
            "Stored SEC submissions for %s (CIK %s) at s3://%s/%s",
            enterprise_name,
            cik,
            cfg.excel_bucket_name,
            key,
        )

    return {"enterprises": results}
