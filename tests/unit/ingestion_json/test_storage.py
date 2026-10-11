"""Tests for function/ingestion_json/storage.py."""

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


def test_upload_submissions_stores_json_object(moto_s3_client) -> None:
    """upload_submissions calls put_object with Bucket, Key, Body and ContentType='application/json'."""
    body = b'{"cik":"0001018724"}'

    upload_submissions(
        s3_client=moto_s3_client,
        bucket_name="my-bucket",
        key="Amazon/CIK0001018724.json",
        body=body,
    )

    response = moto_s3_client.get_object(
        Bucket="my-bucket",
        Key="Amazon/CIK0001018724.json",
    )
    assert response["Body"].read() == body
    assert response["ContentType"] == "application/json"
