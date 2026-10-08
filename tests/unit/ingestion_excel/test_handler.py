from typing import Any

import pytest
from function.ingestion_excel import main, utils


def test_handler_exports_spreadsheets_for_each_company(
    monkeypatch: pytest.MonkeyPatch,
    filing_workbook_bytes: bytes,
) -> None:
    uploaded_objects: list[dict[str, Any]] = []
    retrieve_calls: list[dict[str, Any]] = []

    class FakeS3Client:
        def put_object(self, **kwargs: Any) -> None:
            uploaded_objects.append(kwargs)

    def fake_retrieve(**kwargs: Any) -> dict[str, bytes]:
        retrieve_calls.append(kwargs)
        return {str(kwargs["filter_values"][0]): filing_workbook_bytes}

    monkeypatch.setattr(main, "EXCEL_BUCKET_NAME", "excel-bucket")
    monkeypatch.setattr(main, "s3_client", FakeS3Client())
    monkeypatch.setattr(main, "retrieve_filings_excels", fake_retrieve)
    monkeypatch.setattr(main, "FILING_EXPORTS", (("10-K", "annualOrQuarterlyReports"),))

    result = main.lambda_handler({"companies": {"Amazon": "1018724"}}, None)

    assert retrieve_calls == [
        {
            "url": utils.sec_browse_url("0001018724"),
            "search_value": "10-K",
            "filing_date_from": main.FILING_DATE_FROM,
            "filter_values": ["annualOrQuarterlyReports"],
            "user_agent": main.SEC_USER_AGENT,
        }
    ]
    assert result == {
        "companies": {
            "Amazon": {
                "cik": "0001018724",
                "spreadsheets_uploaded": 1,
            }
        }
    }
    assert uploaded_objects == [
        {
            "Bucket": "excel-bucket",
            "Key": "sec_filings/Amazon/0001018724/annualOrQuarterlyReports.xlsx",
            "Body": filing_workbook_bytes,
            "ContentType": (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        }
    ]


def test_handler_requires_excel_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "EXCEL_BUCKET_NAME", None)
    with pytest.raises(RuntimeError, match="EXCEL_BUCKET_NAME"):
        main.lambda_handler({"companies": {"Amazon": "1018724"}}, None)
