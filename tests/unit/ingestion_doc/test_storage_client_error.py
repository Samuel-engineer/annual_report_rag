"""
Tests for the S3 ClientError re-raise paths in storage.filing_is_current
(covers non-404 head_object and get_object errors).
"""

import json
from datetime import date
from io import BytesIO
from typing import Any

import pytest
from botocore.exceptions import ClientError

from function.ingestion_doc.filings import Filing
from function.ingestion_doc.storage import filing_is_current

FILING = Filing(
    form="10-K",
    filing_date=date(2024, 1, 25),
    accession_number="0000320193-24-000006",
    cik="0000320193",
    primary_document="aapl-20230930.htm",
    reporting_date=date(2023, 9, 30),
)


def _access_denied() -> ClientError:
    return ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "HeadObject",
    )


class _FakeS3HeadFails:
    """head_object always raises the supplied error; get_object never called."""

    def __init__(self, error: ClientError) -> None:
        self._error = error

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        raise self._error

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        raise AssertionError("get_object should not be reached")


class _FakeS3GetFails:
    """
    head_object always succeeds; get_object raises the supplied error.
    Used to cover the get_object ClientError re-raise path.
    """

    def __init__(self, error: ClientError) -> None:
        self._error = error

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        raise self._error


def test_filing_is_current_reraises_non_404_head_object_error() -> None:
    """head_object raises AccessDenied ClientError → exception propagates unchanged."""
    client = _FakeS3HeadFails(_access_denied())

    with pytest.raises(ClientError) as exc_info:
        filing_is_current(client, "raw-bucket", FILING)  # type: ignore[arg-type]

    assert exc_info.value.response["Error"]["Code"] == "AccessDenied"


def test_filing_is_current_reraises_non_404_get_object_error() -> None:
    """Both head_object calls succeed but get_object raises AccessDenied → propagates."""
    client = _FakeS3GetFails(_access_denied())

    with pytest.raises(ClientError) as exc_info:
        filing_is_current(client, "raw-bucket", FILING)  # type: ignore[arg-type]

    assert exc_info.value.response["Error"]["Code"] == "AccessDenied"
