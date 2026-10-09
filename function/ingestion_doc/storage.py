import json
from typing import Any, Protocol
from urllib.parse import unquote_plus

from .filings import Filing


class S3Client(Protocol):
    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]: ...

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: dict[str, str] | None = None,
    ) -> object: ...


def decode_s3_object_key(key: str) -> str:
    return unquote_plus(key)


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
) -> None:
    s3_client.put_object(
        Bucket=bucket_name,
        Key=filing.s3_key,
        Body=body,
        ContentType="application/octet-stream",
        Metadata={
            "form": filing.form,
            "filingDate": filing.filing_date.isoformat(),
            "accessionNumber": filing.accession_number,
        },
    )
