from datetime import date
from io import BytesIO
from typing import Any

import pytest
from function.ingestion_doc import excel_utils
from openpyxl import Workbook


@pytest.mark.parametrize(
    ("value", "expected_year"),
    [
        (date(2023, 12, 31), 2023),
        ("2024-09-30", 2024),
        ("09/30/2025", 2025),
        ("20260930", 2026),
    ],
)
def test_reporting_year_accepts_excel_date_formats(
    value: Any,
    expected_year: int,
) -> None:
    assert excel_utils.reporting_year(value, 4) == expected_year


def test_reporting_year_rejects_invalid_date_with_row_number() -> None:
    with pytest.raises(ValueError, match="row 5"):
        excel_utils.reporting_year("not-a-date", 5)


def test_filing_rows_extracts_hyperlink_and_reporting_year(
    filing_workbook_bytes: bytes,
) -> None:
    assert excel_utils.filing_rows(filing_workbook_bytes) == [
        (
            2024,
            "https://www.sec.gov/Archives/edgar/data/1018724/filing.htm",
            2,
        )
    ]


def test_filing_rows_requires_both_expected_columns() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    if worksheet is None:
        raise AssertionError("Workbook did not create an active worksheet.")
    worksheet.append(["Filing Date", "Company"])
    stream = BytesIO()
    workbook.save(stream)

    with pytest.raises(ValueError, match="Filings URL.*Reporting Date"):
        excel_utils.filing_rows(stream.getvalue())
