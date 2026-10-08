from io import BytesIO
from typing import Any

import pytest
from function.ingestion_doc import main


def test_handler_reads_excel_and_uploads_filings(
    monkeypatch: pytest.MonkeyPatch,
    filing_workbook_bytes: bytes,
) -> None:
    uploaded_objects: list[dict[str, Any]] = []
    read_objects: list[dict[str, str]] = []

    class FakeS3Client:
        def get_object(self, **kwargs: Any) -> dict[str, Any]:
            read_objects.append(kwargs)
            return {"Body": BytesIO(filing_workbook_bytes)}

        def put_object(self, **kwargs: Any) -> None:
            uploaded_objects.append(kwargs)

    monkeypatch.setattr(main, "RAW_BUCKET_NAME", "raw-bucket")
    monkeypatch.setattr(main, "s3_client", FakeS3Client())
    monkeypatch.setattr(main, "download_filing", lambda _url: b"filing contents")

    result = main.lambda_handler(
        {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "excel-bucket"},
                        "object": {
                            "key": (
                                "sec_filings/Amazon/0001018724/"
                                "annualOrQuarterlyReports.xlsx"
                            )
                        },
                    }
                }
            ]
        },
        None,
    )

    assert result == {"documents_uploaded": 1}
    assert read_objects == [
        {
            "Bucket": "excel-bucket",
            "Key": ("sec_filings/Amazon/0001018724/annualOrQuarterlyReports.xlsx"),
        }
    ]
    assert uploaded_objects == [
        {
            "Bucket": "raw-bucket",
            "Key": "2024/Amazon/filing.htm",
            "Body": b"filing contents",
        }
    ]


def test_handler_rejects_missing_s3_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "RAW_BUCKET_NAME", "raw-bucket")
    with pytest.raises(ValueError, match="S3 ObjectCreated"):
        main.lambda_handler({}, None)


def test_handler_requires_raw_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "RAW_BUCKET_NAME", None)
    with pytest.raises(RuntimeError, match="RAW_BUCKET_NAME"):
        main.lambda_handler({"Records": []}, None)
