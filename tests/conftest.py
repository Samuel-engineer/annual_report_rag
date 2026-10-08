from datetime import date
from io import BytesIO

import pytest
from openpyxl import Workbook


@pytest.fixture
def filing_workbook_bytes() -> bytes:
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
