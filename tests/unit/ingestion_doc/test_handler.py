import json
from io import BytesIO
from typing import Any

import pytest

from function.ingestion_doc import config, main

SEC_USER_AGENT = "AnnualReportRag/1.0 (test@example.com)"
SOURCE_JSON = {
    "cik": "0000320193",
    "filings": {
        "recent": {
            "form": ["10-K", "DEF 14A", "8-K"],
            "filingDate": ["2024-01-25", "2024-01-10", "2024-01-05"],
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


def test_handler_downloads_only_supported_filings_and_uploads_s3_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads: list[dict[str, str]] = []
    writes: list[dict[str, Any]] = []
    downloads: list[tuple[str, str]] = []

    class FakeS3Client:
        def get_object(self, **kwargs: str) -> dict[str, Any]:
            reads.append(kwargs)
            return {"Body": BytesIO(json.dumps(SOURCE_JSON).encode())}

        def put_object(self, **kwargs: Any) -> dict[str, str]:
            writes.append(kwargs)
            return {}

    settings = config.Settings("raw-bucket", SEC_USER_AGENT)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "s3_client", FakeS3Client())

    def fake_download(url: str, user_agent: str) -> bytes:
        downloads.append((url, user_agent))
        return b"filing document"

    monkeypatch.setattr(main, "download_filing", fake_download)

    result = main.lambda_handler(
        {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "excel-bucket"},
                        "object": {
                            "key": "Amazon%2FCIK0000320193.json",
                        },
                    }
                }
            ]
        },
        None,
    )

    assert result == {"documents_uploaded": 2}
    assert reads == [{"Bucket": "excel-bucket", "Key": "Amazon/CIK0000320193.json"}]
    assert len(downloads) == 2
    assert all(user_agent == SEC_USER_AGENT for _, user_agent in downloads)
    assert [write["Key"] for write in writes] == [
        "2024/320193/annual_report_aapl-20230930.htm",
        "2024/320193/proxy_statement_def14a.htm",
    ]
    assert [write["Metadata"] for write in writes] == [
        {
            "form": "10-K",
            "filingDate": "2024-01-25",
            "accessionNumber": "0000320193-24-000006",
        },
        {
            "form": "DEF 14A",
            "filingDate": "2024-01-10",
            "accessionNumber": "0000320193-24-000002",
        },
    ]
    assert all(write["Bucket"] == "raw-bucket" for write in writes)
    assert all(write["Body"] == b"filing document" for write in writes)


def test_handler_rejects_missing_s3_records() -> None:
    with pytest.raises(ValueError, match="S3 ObjectCreated"):
        main.lambda_handler({}, None)
