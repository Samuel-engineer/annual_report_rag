import json

import pytest

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
    moto_s3_client,
) -> None:
    downloads: list[tuple[str, str]] = []
    moto_s3_client.put_object(
        Bucket="excel-bucket",
        Key="Apple/CIK0000320193.json",
        Body=json.dumps(SOURCE_JSON).encode(),
    )

    settings = config.Settings("excel-bucket", "raw-bucket", SEC_USER_AGENT)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "s3_client", moto_s3_client)

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
    assert result == {"documents_uploaded": 2, "documents_skipped": 0}
    assert len(downloads) == 2
    assert all(user_agent == SEC_USER_AGENT for _, user_agent in downloads)
    keys = [
        "2024/320193/annual_report_000032019324000006_aapl-20230930.htm",
        (
            "2024/320193/annual_report_000032019324000006_aapl-20230930.htm"
            ".metadata.json"
        ),
        "2024/320193/proxy_statement_000032019324000002_def14a.htm",
        ("2024/320193/proxy_statement_000032019324000002_def14a.htm.metadata.json"),
    ]
    assert [
        item["Key"]
        for item in moto_s3_client.list_objects_v2(Bucket="raw-bucket")["Contents"]
    ] == keys
    metadata_objects = [
        moto_s3_client.get_object(Bucket="raw-bucket", Key=key)
        for key in (keys[1], keys[3])
    ]
    assert [json.loads(item["Body"].read()) for item in metadata_objects] == [
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
    assert [
        moto_s3_client.head_object(Bucket="raw-bucket", Key=key)["ContentType"]
        for key in keys
    ] == [
        "application/octet-stream",
        "application/json",
        "application/octet-stream",
        "application/json",
    ]
    assert [
        moto_s3_client.get_object(Bucket="raw-bucket", Key=key)["Body"].read()
        for key in (keys[0], keys[2])
    ] == [b"filing document", b"filing document"]


def test_handler_rejects_missing_submission_references() -> None:
    with pytest.raises(ValueError, match="submissions list"):
        main.lambda_handler({}, None)


def test_handler_skips_filings_with_matching_metadata(
    monkeypatch: pytest.MonkeyPatch,
    moto_s3_client,
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

    moto_s3_client.put_object(
        Bucket="excel-bucket",
        Key=submission_key,
        Body=json.dumps(SOURCE_JSON).encode(),
    )
    for metadata_key, filing_url in metadata_by_key.items():
        document_key = metadata_key.removesuffix(".metadata.json")
        moto_s3_client.put_object(
            Bucket="raw-bucket",
            Key=document_key,
            Body=b"already ingested document",
        )
        moto_s3_client.put_object(
            Bucket="raw-bucket",
            Key=metadata_key,
            Body=json.dumps({"metadataAttributes": {"filingUrl": filing_url}}).encode(),
        )

    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: config.Settings("excel-bucket", "raw-bucket", SEC_USER_AGENT),
    )
    monkeypatch.setattr(main, "s3_client", moto_s3_client)
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
