"""Tests for function/ingestion_json/storage.py."""

from typing import Any

import pytest

from function.ingestion_json.storage import submissions_s3_key, upload_submissions


# ---------------------------------------------------------------------------
# submissions_s3_key
# ---------------------------------------------------------------------------


def test_submissions_s3_key_builds_correct_path() -> None:
    """submissions_s3_key('Amazon', '0001018724') → 'Amazon/CIK0001018724.json'."""
    assert submissions_s3_key("Amazon", "0001018724") == "Amazon/CIK0001018724.json"


def test_submissions_s3_key_builds_path_for_arbitrary_enterprise() -> None:
    """submissions_s3_key('Apple', '0000320193') → 'Apple/CIK0000320193.json'."""
    assert submissions_s3_key("Apple", "0000320193") == "Apple/CIK0000320193.json"


# ---------------------------------------------------------------------------
# upload_submissions
# ---------------------------------------------------------------------------


class _FakeS3PutObjectClient:
    """Minimal fake that records put_object calls."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def put_object(self, **kwargs: Any) -> dict[str, str]:
        self.calls.append(kwargs)
        return {}


def test_upload_submissions_calls_put_object_with_correct_args() -> None:
    """upload_submissions calls put_object with Bucket, Key, Body and ContentType='application/json'."""
    client = _FakeS3PutObjectClient()
    body = b'{"cik":"0001018724"}'

    upload_submissions(
        s3_client=client,  # type: ignore[arg-type]
        bucket_name="my-bucket",
        key="Amazon/CIK0001018724.json",
        body=body,
    )

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["Bucket"] == "my-bucket"
    assert call["Key"] == "Amazon/CIK0001018724.json"
    assert call["Body"] == body
    assert call["ContentType"] == "application/json"
