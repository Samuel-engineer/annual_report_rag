from typing import Protocol


def submissions_s3_key(enterprise_name: str, cik: str) -> str:
    return f"{enterprise_name}/CIK{cik}.json"


class S3PutObjectClient(Protocol):
    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
    ) -> object: ...


def upload_submissions(
    s3_client: S3PutObjectClient,
    bucket_name: str,
    key: str,
    body: bytes,
) -> None:
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=body,
        ContentType="application/json",
    )
