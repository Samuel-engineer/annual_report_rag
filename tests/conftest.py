from collections.abc import Iterator
from datetime import date
from io import BytesIO
from typing import Any

import boto3
import pytest
from moto import mock_aws
from openpyxl import Workbook


@pytest.fixture
def moto_s3_client() -> Iterator[Any]:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        for bucket in ("excel-bucket", "raw-bucket", "my-bucket"):
            client.create_bucket(Bucket=bucket)
        yield client


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
