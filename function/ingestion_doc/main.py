import os
from typing import Any

import boto3

from .excel_utils import filing_rows
from .s3_utils import company_from_excel_key, excel_object_from_record
from .sec_utils import download_filing, filing_filename

s3_client = boto3.client("s3")

RAW_BUCKET_NAME = os.getenv("RAW_BUCKET_NAME")


def _process_excel_object(bucket: str, key: str, raw_bucket: str) -> int:
    company_name = company_from_excel_key(key)
    response = s3_client.get_object(Bucket=bucket, Key=key)
    workbook_bytes = response["Body"].read()
    documents_uploaded = 0

    for year, filing_url, row_number in filing_rows(workbook_bytes):
        document = download_filing(filing_url)
        document_key = (
            f"{year}/{company_name}/{filing_filename(filing_url, row_number)}"
        )
        s3_client.put_object(
            Bucket=raw_bucket,
            Key=document_key,
            Body=document,
        )
        documents_uploaded += 1

    return documents_uploaded


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, int]:
    raw_bucket = RAW_BUCKET_NAME
    if not raw_bucket:
        raise RuntimeError("RAW_BUCKET_NAME must be configured.")

    records = event.get("Records")
    if not isinstance(records, list) or not records:
        raise ValueError("Expected an S3 ObjectCreated event with at least one record.")

    documents_uploaded = 0
    for record in records:
        bucket, key = excel_object_from_record(record)
        documents_uploaded += _process_excel_object(bucket, key, raw_bucket)

    return {"documents_uploaded": documents_uploaded}