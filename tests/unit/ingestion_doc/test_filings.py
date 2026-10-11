from datetime import date
from typing import Any

import pytest

from function.ingestion_doc.filings import extract_filings


@pytest.fixture
def submissions() -> dict[str, Any]:
    return {
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


def test_extract_filings_filters_forms_and_reconstructs_archive_urls(
    submissions: dict[str, Any],
) -> None:
    filings = extract_filings(submissions)

    assert [filing.form for filing in filings] == ["10-K", "DEF 14A"]
    assert [filing.filing_date for filing in filings] == [
        date(2024, 1, 25),
        date(2024, 1, 10),
    ]
    assert [filing.reporting_date for filing in filings] == [
        date(2023, 9, 30),
        date(2023, 12, 31),
    ]
    assert [filing.archive_url for filing in filings] == [
        (
            "https://www.sec.gov/Archives/edgar/data/320193/"
            "000032019324000006/aapl-20230930.htm"
        ),
        (
            "https://www.sec.gov/Archives/edgar/data/320193/"
            "000032019324000002/def14a.htm"
        ),
    ]
    assert [filing.s3_key for filing in filings] == [
        "2024/320193/annual_report_000032019324000006_aapl-20230930.htm",
        "2024/320193/proxy_statement_000032019324000002_def14a.htm",
    ]
    assert [filing.index_url for filing in filings] == [
        (
            "https://www.sec.gov/Archives/edgar/data/320193/"
            "000032019324000006/0000320193-24-000006-index.htm"
        ),
        (
            "https://www.sec.gov/Archives/edgar/data/320193/"
            "000032019324000002/0000320193-24-000002-index.htm"
        ),
    ]


def test_extract_filings_rejects_mismatched_arrays(
    submissions: dict[str, Any],
) -> None:
    submissions["filings"]["recent"]["filingDate"].pop()

    with pytest.raises(ValueError, match="different lengths"):
        extract_filings(submissions)


def test_extract_filings_rejects_invalid_selected_filing(
    submissions: dict[str, Any],
) -> None:
    submissions["filings"]["recent"]["accessionNumber"][0] = "not-an-accession"

    with pytest.raises(ValueError, match="accessionNumber"):
        extract_filings(submissions)


def test_extract_filings_rejects_missing_root_cik(
    submissions: dict[str, Any],
) -> None:
    del submissions["cik"]

    with pytest.raises(ValueError, match="root CIK"):
        extract_filings(submissions)
