import json
from io import BytesIO
from typing import Any

import pytest
from botocore.exceptions import ClientError

from function.ingestion_doc import config, main

SEC_USER_AGENT = "AnnualReportRag/1.0 (test@example.com)"
SOURCE_JSON = {
    "cik": "0000320193",
    "filings": {
        "recent": {
            "form": ["10-K", "DEF 14A", "8-K"],
            "filingDate": ["2024-01-25", "2024-01-10", "2024-01-05"],
            "reportDate": ["2023-09-30", "2023-12-31", ""],
            "accessionNumber": [
                "0000320193-24-000006",
                "0000320193-24-000002",
                "0000320193-24-000001",
            ],
            "primaryDocument": [
                "aapl-20230930.htm",
                "def14a.htm",
                "form8k.htm",
            ],
        }
    },
}


def test_handler_downloads_only_supported_filings_and_uploads_metadata_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads: list[dict[str, str]] = []
    writes: list[dict[str, Any]] = []
    downloads: list[tuple[str, str]] = []
    existing_keys: set[str] = set()

    class FakeS3Client:
        def get_object(self, **kwargs: str) -> dict[str, Any]:
            reads.append(kwargs)
            return {"Body": BytesIO(json.dumps(SOURCE_JSON).encode())}

        def head_object(self, **kwargs: str) -> dict[str, Any]:
            if kwargs["Key"] not in existing_keys:
                raise ClientError(
                    {"Error": {"Code": "404", "Message": "Not found"}},
                    "HeadObject",
                )
            return {}

        def put_object(self, **kwargs: Any) -> dict[str, str]:
            writes.append(kwargs)
            return {}

    settings = config.Settings("excel-bucket", "raw-bucket", SEC_USER_AGENT)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "s3_client", FakeS3Client())

    def fake_download(url: str, user_agent: str) -> bytes:
        downloads.append((url, user_agent))
        return b"filing document"

    monkeypatch.setattr(main, "download_filing", fake_download)

    result = main.lambda_handler(
        {
            "submissions": [
                {
                    "enterprise": "Apple",
                    "bucket": "excel-bucket",
                    "key": "Apple/CIK0000320193.json",
                }
            ]
        },
        None,
    )

    assert result == {"documents_uploaded": 2, "documents_skipped": 0}
    assert reads == [{"Bucket": "excel-bucket", "Key": "Apple/CIK0000320193.json"}]
    assert len(downloads) == 2
    assert all(user_agent == SEC_USER_AGENT for _, user_agent in downloads)
    assert [write["Key"] for write in writes] == [
        "2024/320193/annual_report_000032019324000006_aapl-20230930.htm",
        (
            "2024/320193/annual_report_000032019324000006_aapl-20230930.htm"
            ".metadata.json"
        ),
        "2024/320193/proxy_statement_000032019324000002_def14a.htm",
        ("2024/320193/proxy_statement_000032019324000002_def14a.htm.metadata.json"),
    ]
    assert all("Metadata" not in write for write in writes)
    assert [json.loads(write["Body"]) for write in (writes[1], writes[3])] == [
        {
            "metadataAttributes": {
                "enterprise": "Apple",
                "filingDate": "25/01/2024",
                "reportingDate": "30/09/2023",
                "filingUrl": (
                    "https://www.sec.gov/Archives/edgar/data/320193/"
                    "000032019324000006/0000320193-24-000006-index.htm"
                ),
            }
        },
        {
            "metadataAttributes": {
                "enterprise": "Apple",
                "filingDate": "10/01/2024",
                "reportingDate": "31/12/2023",
                "filingUrl": (
                    "https://www.sec.gov/Archives/edgar/data/320193/"
                    "000032019324000002/0000320193-24-000002-index.htm"
                ),
            }
        },
    ]
    assert [write["ContentType"] for write in writes] == [
        "application/octet-stream",
        "application/json",
        "application/octet-stream",
        "application/json",
    ]
    assert all(write["Bucket"] == "raw-bucket" for write in writes)
    assert writes[0]["Body"] == writes[2]["Body"] == b"filing document"


def test_handler_rejects_missing_submission_references() -> None:
    with pytest.raises(ValueError, match="submissions list"):
        main.lambda_handler({}, None)


def test_handler_skips_filings_with_matching_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submission_key = "Apple/CIK0000320193.json"
    metadata_by_key = {
        (
            "2024/320193/annual_report_000032019324000006_"
            "aapl-20230930.htm.metadata.json"
        ): (
            "https://www.sec.gov/Archives/edgar/data/320193/"
            "000032019324000006/0000320193-24-000006-index.htm"
        ),
        ("2024/320193/proxy_statement_000032019324000002_def14a.htm.metadata.json"): (
            "https://www.sec.gov/Archives/edgar/data/320193/"
            "000032019324000002/0000320193-24-000002-index.htm"
        ),
    }

    class FakeS3Client:
        def head_object(self, **_kwargs: str) -> dict[str, str]:
            return {}

        def get_object(self, **kwargs: str) -> dict[str, Any]:
            if kwargs["Key"] == submission_key:
                return {"Body": BytesIO(json.dumps(SOURCE_JSON).encode())}
            return {
                "Body": BytesIO(
                    json.dumps(
                        {
                            "metadataAttributes": {
                                "filingUrl": metadata_by_key[kwargs["Key"]]
                            }
                        }
                    ).encode()
                )
            }

        def put_object(self, **_kwargs: Any) -> dict[str, str]:
            pytest.fail("Already ingested filings should not be uploaded again.")

    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: config.Settings("excel-bucket", "raw-bucket", SEC_USER_AGENT),
    )
    monkeypatch.setattr(main, "s3_client", FakeS3Client())
    monkeypatch.setattr(
        main,
        "download_filing",
        lambda *_args: pytest.fail(
            "Already ingested filings should not be downloaded."
        ),
    )

    result = main.lambda_handler(
        {
            "submissions": [
                {
                    "enterprise": "Apple",
                    "bucket": "excel-bucket",
                    "key": submission_key,
                }
            ]
        },
        None,
    )

    assert result == {"documents_uploaded": 0, "documents_skipped": 2}
