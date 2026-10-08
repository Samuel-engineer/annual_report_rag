import os
from typing import Any

import boto3

from .retrieve_excel import retrieve_filings_excels
from .utils import company_s3_key, get_companies, sec_browse_url

SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "annual-report-rag/0.1.0 (SEC filings ingestion)",
)
FILING_DATE_FROM = os.getenv("FILING_DATE_FROM", "2020-01-01")
FILING_EXPORTS = (
    ("10-K", "annualOrQuarterlyReports"),
    ("DEF 14A", "proxyStatements"),
)

s3_client = boto3.client("s3")

EXCEL_BUCKET_NAME = os.getenv("EXCEL_BUCKET_NAME")


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    excel_bucket = EXCEL_BUCKET_NAME
    if not excel_bucket:
        raise RuntimeError("EXCEL_BUCKET_NAME must be configured.")

    company_results = {}
    for company_name, cik in get_companies(event).items():
        browse_url = sec_browse_url(cik)
        company_key = company_s3_key(company_name)
        spreadsheets_uploaded = 0

        for search_value, filter_value in FILING_EXPORTS:
            exports = retrieve_filings_excels(
                url=browse_url,
                search_value=search_value,
                filing_date_from=FILING_DATE_FROM,
                filter_values=[filter_value],
                user_agent=SEC_USER_AGENT,
            )
            for export_name, workbook_bytes in exports.items():
                s3_client.put_object(
                    Bucket=excel_bucket,
                    Key=f"sec_filings/{company_key}/{cik}/{export_name}.xlsx",
                    Body=workbook_bytes,
                    ContentType=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                )
                spreadsheets_uploaded += 1

        company_results[company_name] = {
            "cik": cik,
            "spreadsheets_uploaded": spreadsheets_uploaded,
        }

    return {"companies": company_results}
