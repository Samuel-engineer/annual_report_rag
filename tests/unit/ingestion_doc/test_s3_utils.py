import pytest

from function.ingestion_doc import s3_utils


def test_company_from_excel_key_extracts_company() -> None:
    assert (
        s3_utils.company_from_excel_key(
            "sec_filings/Amazon/0001018724/annualOrQuarterlyReports.xlsx"
        )
        == "Amazon"
    )


def test_company_from_excel_key_rejects_invalid_key() -> None:
    with pytest.raises(ValueError, match="Unexpected SEC Excel object key"):
        s3_utils.company_from_excel_key("other/Amazon/file.xlsx")


def test_excel_object_from_record_decodes_url_encoded_key() -> None:
    assert s3_utils.excel_object_from_record(
        {
            "s3": {
                "bucket": {"name": "excel-bucket"},
                "object": {"key": "sec_filings/Acme%20Inc/123/file.xlsx"},
            }
        }
    ) == ("excel-bucket", "sec_filings/Acme Inc/123/file.xlsx")


def test_excel_object_from_record_rejects_malformed_record() -> None:
    with pytest.raises(ValueError, match="Malformed S3 event"):
        s3_utils.excel_object_from_record({})
