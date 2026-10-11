import json
from json import JSONDecodeError
from typing import Any, Protocol

from botocore.exceptions import ClientError

from .filings import Filing


class S3Client(Protocol):
    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]: ...

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]: ...

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
    ) -> object: ...


def load_submissions(s3_client: S3Client, bucket: str, key: str) -> dict[str, Any]:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise TypeError(
            f"Submissions object s3://{bucket}/{key} must be a JSON object."
        )
    return payload


def upload_filing(
    s3_client: S3Client,
    bucket_name: str,
    filing: Filing,
    body: bytes,
    enterprise: str,
) -> None:
    s3_client.put_object(
        Bucket=bucket_name,
        Key=filing.s3_key,
        Body=body,
        ContentType="application/octet-stream",
    )
    raw_attributes = {
        "enterprise": enterprise,
        "filingDate": filing.filing_date.strftime("%d/%m/%Y"),
        "reportingDate": (
            filing.reporting_date.strftime("%d/%m/%Y") if filing.reporting_date else ""
        ),
        "filingUrl": filing.index_url,
    }
    metadata = {
        "metadataAttributes": {k: v for k, v in raw_attributes.items() if v != ""}
    }
    s3_client.put_object(
        Bucket=bucket_name,
        Key=f"{filing.s3_key}.metadata.json",
        Body=json.dumps(metadata, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def filing_is_current(
    s3_client: S3Client,
    bucket_name: str,
    filing: Filing,
) -> bool:
    metadata_key = f"{filing.s3_key}.metadata.json"
    if not _object_exists(s3_client, bucket_name, filing.s3_key):
        return False
    if not _object_exists(s3_client, bucket_name, metadata_key):
        return False

    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=metadata_key)
    except ClientError as error:
        if _is_missing_object(error):
            return False
        raise
    metadata_body = response["Body"].read()
    try:
        metadata = json.loads(metadata_body)
    except (JSONDecodeError, UnicodeDecodeError):
        return False
    attributes = (
        metadata.get("metadataAttributes") if isinstance(metadata, dict) else None
    )
    return (
        isinstance(attributes, dict) and attributes.get("filingUrl") == filing.index_url
    )


def _object_exists(s3_client: S3Client, bucket_name: str, key: str) -> bool:
    try:
        s3_client.head_object(Bucket=bucket_name, Key=key)
    except ClientError as error:
        if _is_missing_object(error):
            return False
        raise
    return True


def _is_missing_object(error: ClientError) -> bool:
    return error.response.get("Error", {}).get("Code") in {
        "404",
        "NoSuchKey",
        "NotFound",
    }
