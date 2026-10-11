"""
Extended tests for function/ingestion_doc/main.py — covers _submission_location
error paths and handler validation branches not covered by test_handler.py.
"""

from typing import Any

import pytest

from function.ingestion_doc import config, main

SEC_USER_AGENT = "AnnualReportRag/1.0 (test@example.com)"

# ---------------------------------------------------------------------------
# Minimal S3 fake for handler tests
# ---------------------------------------------------------------------------


class _NoOpS3Client:
    """S3 client stub that should never be called in error-path tests."""

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("S3 get_object should not be called")

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("S3 head_object should not be called")

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("S3 put_object should not be called")


# ---------------------------------------------------------------------------
# lambda_handler — submissions list validation
# ---------------------------------------------------------------------------


def test_handler_rejects_empty_submissions_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """submissions: [] → ValueError matching 'submissions list'."""
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: config.Settings("excel-bucket", "raw-bucket", SEC_USER_AGENT),
    )
    monkeypatch.setattr(main, "s3_client", _NoOpS3Client())

    with pytest.raises(ValueError, match="submissions list"):
        main.lambda_handler({"submissions": []}, None)


def test_handler_rejects_non_list_submissions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """submissions: 'wrong' (string) → ValueError matching 'submissions list'."""
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: config.Settings("excel-bucket", "raw-bucket", SEC_USER_AGENT),
    )
    monkeypatch.setattr(main, "s3_client", _NoOpS3Client())

    with pytest.raises(ValueError, match="submissions list"):
        main.lambda_handler({"submissions": "wrong"}, None)


# ---------------------------------------------------------------------------
# _submission_location — validation
# ---------------------------------------------------------------------------


def test_submission_location_rejects_non_dict() -> None:
    """_submission_location('string') → TypeError matching 'object'."""
    with pytest.raises(TypeError, match="object"):
        main._submission_location("string")  # type: ignore[arg-type]


def test_submission_location_rejects_missing_enterprise() -> None:
    """Dict without 'enterprise' key → ValueError matching 'enterprise'."""
    with pytest.raises(ValueError, match="enterprise"):
        main._submission_location({"bucket": "b", "key": "k"})


def test_submission_location_rejects_empty_enterprise() -> None:
    """enterprise: '' → ValueError matching 'enterprise'."""
    with pytest.raises(ValueError, match="enterprise"):
        main._submission_location({"enterprise": "", "bucket": "b", "key": "k"})


def test_submission_location_rejects_missing_bucket() -> None:
    """Dict without 'bucket' key → ValueError matching 'bucket name'."""
    with pytest.raises(ValueError, match="bucket name"):
        main._submission_location({"enterprise": "Apple", "key": "k"})


def test_submission_location_rejects_missing_key() -> None:
    """Dict without 'key' → ValueError matching 'object key'."""
    with pytest.raises(ValueError, match="object key"):
        main._submission_location({"enterprise": "Apple", "bucket": "b"})


# ---------------------------------------------------------------------------
# lambda_handler — bucket mismatch check
# ---------------------------------------------------------------------------


def test_handler_raises_when_bucket_does_not_match_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """submission.bucket != cfg.excel_bucket_name → ValueError matching 'does not match'."""
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: config.Settings("excel-bucket", "raw-bucket", SEC_USER_AGENT),
    )
    monkeypatch.setattr(main, "s3_client", _NoOpS3Client())

    with pytest.raises(ValueError, match="does not match"):
        main.lambda_handler(
            {
                "submissions": [
                    {
                        "enterprise": "Apple",
                        "bucket": "wrong-bucket",
                        "key": "Apple/CIK0000320193.json",
                    }
                ]
            },
            None,
        )
