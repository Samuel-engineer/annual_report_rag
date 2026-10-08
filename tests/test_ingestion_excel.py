from datetime import date
from io import BytesIO
from typing import Any

import pytest
from openpyxl import Workbook

from function.ingestion_doc import main as doc_main
from function.ingestion_doc import sec_utils as doc_sec_utils
from function.ingestion_excel import main as excel_main
from function.ingestion_excel import utils as excel_utils


def _make_workbook() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    if worksheet is None:
        raise AssertionError("Workbook did not create an active worksheet.")
    worksheet.append(["Filings URL", "Reporting Date"])
    worksheet.append(["Open filing", date(2024, 9, 30)])
    worksheet[
        "A2"
    ].hyperlink = "https://www.sec.gov/Archives/edgar/data/1018724/filing.htm"
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def test_get_companies_accepts_wrapped_payload_and_normalises_cik() -> None:
    assert excel_utils.get_companies(
        {"companies": {"Amazon": "1018724", "Example": 42}}
    ) == {
        "Amazon": "0001018724",
        "Example": "0000000042",
    }


def test_get_companies_rejects_invalid_cik() -> None:
    with pytest.raises(ValueError, match="Invalid SEC CIK"):
        excel_utils.get_companies({"Amazon": "not-a-cik"})


def test_company_s3_key_normalises_name() -> None:
    assert excel_utils.company_s3_key(" Société Amazon! ") == "Societe_Amazon"


def test_sec_browse_url_uses_unpadded_cik() -> None:
    assert excel_utils.sec_browse_url("0001018724") == (
        "https://www.sec.gov/edgar/browse/?CIK=1018724"
    )


def test_ingestion_excel_exports_spreadsheets_for_each_company(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded_objects: list[dict[str, Any]] = []
    retrieve_calls: list[dict[str, Any]] = []

    class FakeS3Client:
        def put_object(self, **kwargs: Any) -> None:
            uploaded_objects.append(kwargs)

    def fake_retrieve(**kwargs: Any) -> dict[str, bytes]:
        retrieve_calls.append(kwargs)
        return {str(kwargs["filter_values"][0]): _make_workbook()}

    monkeypatch.setenv("EXCEL_BUCKET_NAME", "excel-bucket")
    monkeypatch.setattr(excel_main, "s3_client", FakeS3Client())
    monkeypatch.setattr(excel_main, "retrieve_filings_excels", fake_retrieve)
    monkeypatch.setattr(
        excel_main, "FILING_EXPORTS", (("10-K", "annualOrQuarterlyReports"),)
    )

    result = excel_main.lambda_handler(
        {"companies": {"Amazon": "1018724"}},
        None,
    )

    assert retrieve_calls[0]["url"] == excel_utils.sec_browse_url("0001018724")
    assert result == {
        "companies": {
            "Amazon": {
                "cik": "0001018724",
                "spreadsheets_uploaded": 1,
            }
        }
    }
    assert uploaded_objects[0]["Bucket"] == "excel-bucket"
    assert uploaded_objects[0]["Key"] == (
        "sec_filings/Amazon/0001018724/annualOrQuarterlyReports.xlsx"
    )


def test_ingestion_doc_reads_excel_and_uploads_filings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded_objects: list[dict[str, Any]] = []

    class FakeS3Client:
        def get_object(self, **kwargs: Any) -> dict[str, Any]:
            assert kwargs == {
                "Bucket": "excel-bucket",
                "Key": ("sec_filings/Amazon/0001018724/annualOrQuarterlyReports.xlsx"),
            }
            return {"Body": BytesIO(_make_workbook())}

        def put_object(self, **kwargs: Any) -> None:
            uploaded_objects.append(kwargs)

    monkeypatch.setenv("RAW_BUCKET_NAME", "raw-bucket")
    monkeypatch.setattr(doc_main, "s3_client", FakeS3Client())
    monkeypatch.setattr(doc_main, "download_filing", lambda _url: b"filing contents")

    result = doc_main.lambda_handler(
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
    assert uploaded_objects == [
        {
            "Bucket": "raw-bucket",
            "Key": "2024/Amazon/filing.htm",
            "Body": b"filing contents",
        }
    ]


def test_download_filing_rejects_non_sec_url() -> None:
    with pytest.raises(ValueError, match="must point to SEC"):
        doc_sec_utils.download_filing("https://example.com/filing.htm")


def test_filing_filename_uses_sec_path_basename() -> None:
    assert (
        doc_sec_utils.filing_filename(
            "https://www.sec.gov/Archives/annual%20report.htm",
            2,
        )
        == "annual_report.htm"
    )
