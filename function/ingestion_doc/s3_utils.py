from collections.abc import Mapping
from typing import Any
from urllib.parse import unquote_plus


def company_from_excel_key(key: str) -> str:
    parts = key.split("/")
    if (
        len(parts) != 4
        or parts[0] != "sec_filings"
        or not parts[1]
        or not parts[2].isdigit()
        or not parts[3].endswith(".xlsx")
    ):
        raise ValueError(f"Unexpected SEC Excel object key: {key!r}")
    return parts[1]


def excel_object_from_record(record: Mapping[str, Any]) -> tuple[str, str]:
    try:
        s3_record = record["s3"]
        bucket = s3_record["bucket"]["name"]
        key = unquote_plus(s3_record["object"]["key"])
    except (KeyError, TypeError) as error:
        raise ValueError("Malformed S3 event record.") from error

    if not isinstance(bucket, str) or not bucket:
        raise ValueError("S3 event record is missing a bucket name.")
    if not isinstance(key, str) or not key:
        raise ValueError("S3 event record is missing an object key.")
    return bucket, key
