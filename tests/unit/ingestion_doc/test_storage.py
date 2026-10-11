"""Tests for function/ingestion_doc/storage.py."""

import json
from datetime import date
from io import BytesIO
from typing import Any

import pytest
from botocore.exceptions import ClientError

from function.ingestion_doc.filings import Filing
from function.ingestion_doc.storage import (
    filing_is_current,
    load_submissions,
    upload_filing,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FILING = Filing(
    form="10-K",
    filing_date=date(2024, 1, 25),
    accession_number="0000320193-24-000006",
    cik="0000320193",
    primary_document="aapl-20230930.htm",
    reporting_date=date(2023, 9, 30),
)

FILING_NO_REPORT_DATE = Filing(
    form="10-K",
    filing_date=date(2024, 1, 25),
    accession_number="0000320193-24-000006",
    cik="0000320193",
    primary_document="aapl-20230930.htm",
    reporting_date=None,
)


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "msg"}}, "op")


# ---------------------------------------------------------------------------
# load_submissions
# ---------------------------------------------------------------------------


class _FakeGetObject:
    """Minimal S3-like client for load_submissions tests."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        return {"Body": BytesIO(self._body)}


def test_load_submissions_returns_parsed_dict() -> None:
    """Happy path: S3 body is valid JSON object → returns the parsed dict."""
    payload = {"cik": "0000320193", "filings": {}}
    client = _FakeGetObject(json.dumps(payload).encode())

    result = load_submissions(client, "my-bucket", "my-key.json")  # type: ignore[arg-type]

    assert result == payload


def test_load_submissions_raises_if_body_is_json_array() -> None:
    """Body is a JSON array → TypeError mentioning 'JSON object'."""
    client = _FakeGetObject(b"[]")

    with pytest.raises(TypeError, match="JSON object"):
        load_submissions(client, "my-bucket", "my-key.json")  # type: ignore[arg-type]


def test_load_submissions_raises_if_body_is_invalid_json() -> None:
    """Body is not valid JSON → json.JSONDecodeError is raised."""
    client = _FakeGetObject(b"not-json")

    with pytest.raises(json.JSONDecodeError):
        load_submissions(client, "my-bucket", "my-key.json")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# upload_filing
# ---------------------------------------------------------------------------


class _FakePutObject:
    """Minimal S3-like client that records put_object calls."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def put_object(self, **kwargs: Any) -> dict[str, str]:
        self.calls.append(kwargs)
        return {}


def test_upload_filing_puts_document_and_metadata() -> None:
    """upload_filing makes two put_object calls: the document and its metadata JSON."""
    client = _FakePutObject()

    upload_filing(
        s3_client=client,  # type: ignore[arg-type]
        bucket_name="raw-bucket",
        filing=FILING,
        body=b"filing bytes",
        enterprise="Apple",
    )

    assert len(client.calls) == 2
    doc_call, meta_call = client.calls

    # Document upload
    assert doc_call["Bucket"] == "raw-bucket"
    assert doc_call["Key"] == FILING.s3_key
    assert doc_call["Body"] == b"filing bytes"
    assert doc_call["ContentType"] == "application/octet-stream"

    # Metadata upload
    assert meta_call["Bucket"] == "raw-bucket"
    assert meta_call["Key"] == f"{FILING.s3_key}.metadata.json"
    assert meta_call["ContentType"] == "application/json"

    metadata = json.loads(meta_call["Body"])
    attrs = metadata["metadataAttributes"]
    assert attrs["enterprise"] == "Apple"
    assert attrs["filingDate"] == "25/01/2024"
    assert attrs["reportingDate"] == "30/09/2023"
    assert attrs["filingUrl"] == FILING.index_url


def test_upload_filing_metadata_empty_reporting_date() -> None:
    """When filing.reporting_date is None, reportingDate field in metadata is ''."""
    client = _FakePutObject()

    upload_filing(
        s3_client=client,  # type: ignore[arg-type]
        bucket_name="raw-bucket",
        filing=FILING_NO_REPORT_DATE,
        body=b"filing bytes",
        enterprise="Apple",
    )

    _doc_call, meta_call = client.calls
    attrs = json.loads(meta_call["Body"])["metadataAttributes"]
    assert attrs["reportingDate"] == ""


# ---------------------------------------------------------------------------
# filing_is_current
# ---------------------------------------------------------------------------


class _FakeS3ForCurrentCheck:
    """
    Configurable fake S3 client for filing_is_current tests.

    head_responses: mapping key → None (exists) or ClientError (raise)
    get_response: bytes to return from get_object, or ClientError to raise
    """

    def __init__(
        self,
        head_responses: dict[str, ClientError | None],
        get_body: bytes | ClientError | None = None,
    ) -> None:
        self._head = head_responses
        self._get_body = get_body

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        err = self._head.get(Key)
        if err is not None:
            raise err
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if isinstance(self._get_body, ClientError):
            raise self._get_body
        if self._get_body is None:
            raise _client_error("404")
        return {"Body": BytesIO(self._get_body)}


def test_filing_is_current_returns_false_when_document_missing() -> None:
    """head_object raises 404 for the document key → filing_is_current returns False."""
    client = _FakeS3ForCurrentCheck(
        head_responses={FILING.s3_key: _client_error("404")}
    )

    assert filing_is_current(client, "raw-bucket", FILING) is False  # type: ignore[arg-type]


def test_filing_is_current_returns_false_when_metadata_missing() -> None:
    """Document exists but head_object raises 404 for .metadata.json → False."""
    metadata_key = f"{FILING.s3_key}.metadata.json"
    client = _FakeS3ForCurrentCheck(
        head_responses={metadata_key: _client_error("404")}
    )

    assert filing_is_current(client, "raw-bucket", FILING) is False  # type: ignore[arg-type]


def test_filing_is_current_returns_false_when_metadata_url_differs() -> None:
    """Both objects exist, but metadata filingUrl != filing.index_url → False."""
    metadata = {
        "metadataAttributes": {"filingUrl": "https://www.sec.gov/Archives/other"}
    }
    client = _FakeS3ForCurrentCheck(
        head_responses={},
        get_body=json.dumps(metadata).encode(),
    )

    assert filing_is_current(client, "raw-bucket", FILING) is False  # type: ignore[arg-type]


def test_filing_is_current_returns_true_when_url_matches() -> None:
    """Both objects exist and filingUrl matches filing.index_url → True."""
    metadata = {
        "metadataAttributes": {"filingUrl": FILING.index_url}
    }
    client = _FakeS3ForCurrentCheck(
        head_responses={},
        get_body=json.dumps(metadata).encode(),
    )

    assert filing_is_current(client, "raw-bucket", FILING) is True  # type: ignore[arg-type]


def test_filing_is_current_returns_false_when_metadata_is_invalid_json() -> None:
    """get_object returns non-JSON bytes → filing_is_current returns False."""
    client = _FakeS3ForCurrentCheck(
        head_responses={},
        get_body=b"not valid json {{",
    )

    assert filing_is_current(client, "raw-bucket", FILING) is False  # type: ignore[arg-type]


def test_filing_is_current_reraises_unexpected_client_error() -> None:
    """head_object raises ClientError with code 500 → the exception propagates."""
    client = _FakeS3ForCurrentCheck(
        head_responses={FILING.s3_key: _client_error("500")}
    )

    with pytest.raises(ClientError):
        filing_is_current(client, "raw-bucket", FILING)  # type: ignore[arg-type]
