"""Tests for function/ingestion_doc/storage.py."""

import json
from datetime import date

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


def test_load_submissions_returns_parsed_dict(moto_s3_client) -> None:
    """Happy path: S3 body is valid JSON object → returns the parsed dict."""
    payload = {"cik": "0000320193", "filings": {}}
    moto_s3_client.put_object(
        Bucket="my-bucket",
        Key="submissions.json",
        Body=json.dumps(payload).encode(),
    )

    result = load_submissions(moto_s3_client, "my-bucket", "submissions.json")

    assert result == payload


def test_load_submissions_raises_if_body_is_json_array(moto_s3_client) -> None:
    """Body is a JSON array → TypeError mentioning 'JSON object'."""
    moto_s3_client.put_object(
        Bucket="my-bucket",
        Key="submissions.json",
        Body=b"[]",
    )

    with pytest.raises(TypeError, match="JSON object"):
        load_submissions(moto_s3_client, "my-bucket", "submissions.json")


def test_load_submissions_raises_if_body_is_invalid_json(moto_s3_client) -> None:
    """Body is not valid JSON → json.JSONDecodeError is raised."""
    moto_s3_client.put_object(
        Bucket="my-bucket",
        Key="submissions.json",
        Body=b"not-json",
    )

    with pytest.raises(json.JSONDecodeError):
        load_submissions(moto_s3_client, "my-bucket", "submissions.json")


# ---------------------------------------------------------------------------
# upload_filing
# ---------------------------------------------------------------------------


def test_upload_filing_puts_document_and_metadata(moto_s3_client) -> None:
    """upload_filing makes two put_object calls: the document and its metadata JSON."""
    upload_filing(
        s3_client=moto_s3_client,
        bucket_name="raw-bucket",
        filing=FILING,
        body=b"filing bytes",
        enterprise="Apple",
    )

    document = moto_s3_client.get_object(Bucket="raw-bucket", Key=FILING.s3_key)
    metadata_object = moto_s3_client.get_object(
        Bucket="raw-bucket",
        Key=f"{FILING.s3_key}.metadata.json",
    )
    assert document["Body"].read() == b"filing bytes"
    assert document["ContentType"] == "application/octet-stream"
    assert metadata_object["ContentType"] == "application/json"

    metadata = json.loads(metadata_object["Body"].read())
    attrs = metadata["metadataAttributes"]
    assert attrs["enterprise"] == "Apple"
    assert attrs["filingDate"] == "25/01/2024"
    assert attrs["reportingDate"] == "30/09/2023"
    assert attrs["filingUrl"] == FILING.index_url


def test_upload_filing_metadata_empty_reporting_date(moto_s3_client) -> None:
    """When filing.reporting_date is None, reportingDate field in metadata is ''."""
    upload_filing(
        s3_client=moto_s3_client,
        bucket_name="raw-bucket",
        filing=FILING_NO_REPORT_DATE,
        body=b"filing bytes",
        enterprise="Apple",
    )

    metadata_object = moto_s3_client.get_object(
        Bucket="raw-bucket",
        Key=f"{FILING_NO_REPORT_DATE.s3_key}.metadata.json",
    )
    attrs = json.loads(metadata_object["Body"].read())["metadataAttributes"]
    assert attrs["reportingDate"] == ""


# ---------------------------------------------------------------------------
# filing_is_current
# ---------------------------------------------------------------------------


def test_filing_is_current_returns_false_when_document_missing(
    moto_s3_client,
) -> None:
    """head_object raises 404 for the document key → filing_is_current returns False."""
    assert filing_is_current(moto_s3_client, "raw-bucket", FILING) is False


def test_filing_is_current_returns_false_when_metadata_missing(moto_s3_client) -> None:
    """Document exists but head_object raises 404 for .metadata.json → False."""
    moto_s3_client.put_object(
        Bucket="raw-bucket",
        Key=FILING.s3_key,
        Body=b"filing bytes",
    )

    assert filing_is_current(moto_s3_client, "raw-bucket", FILING) is False


def test_filing_is_current_returns_false_when_metadata_url_differs(
    moto_s3_client,
) -> None:
    """Both objects exist, but metadata filingUrl != filing.index_url → False."""
    moto_s3_client.put_object(Bucket="raw-bucket", Key=FILING.s3_key, Body=b"filing")
    metadata = {
        "metadataAttributes": {"filingUrl": "https://www.sec.gov/Archives/other"}
    }
    moto_s3_client.put_object(
        Bucket="raw-bucket",
        Key=f"{FILING.s3_key}.metadata.json",
        Body=json.dumps(metadata).encode(),
    )

    assert filing_is_current(moto_s3_client, "raw-bucket", FILING) is False


def test_filing_is_current_returns_true_when_url_matches(moto_s3_client) -> None:
    """Both objects exist and filingUrl matches filing.index_url → True."""
    moto_s3_client.put_object(Bucket="raw-bucket", Key=FILING.s3_key, Body=b"filing")
    metadata = {"metadataAttributes": {"filingUrl": FILING.index_url}}
    moto_s3_client.put_object(
        Bucket="raw-bucket",
        Key=f"{FILING.s3_key}.metadata.json",
        Body=json.dumps(metadata).encode(),
    )

    assert filing_is_current(moto_s3_client, "raw-bucket", FILING) is True


def test_filing_is_current_returns_false_when_metadata_is_invalid_json(
    moto_s3_client,
) -> None:
    """get_object returns non-JSON bytes → filing_is_current returns False."""
    moto_s3_client.put_object(Bucket="raw-bucket", Key=FILING.s3_key, Body=b"filing")
    moto_s3_client.put_object(
        Bucket="raw-bucket",
        Key=f"{FILING.s3_key}.metadata.json",
        Body=b"not valid json {{",
    )

    assert filing_is_current(moto_s3_client, "raw-bucket", FILING) is False
