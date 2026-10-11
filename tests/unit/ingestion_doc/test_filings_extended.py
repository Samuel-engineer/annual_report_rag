"""
Extended tests for function/ingestion_doc/filings.py — error branches and edge cases
not covered by the existing test_filings.py.
"""

from datetime import date
from typing import Any

import pytest

from function.ingestion_doc.filings import Filing, extract_filings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_recent(**overrides: Any) -> dict[str, Any]:
    """Return a minimal valid 'recent' dict, allowing individual field overrides."""
    base: dict[str, Any] = {
        "form": ["10-K"],
        "filingDate": ["2024-01-25"],
        "reportDate": ["2023-09-30"],
        "accessionNumber": ["0000320193-24-000006"],
        "primaryDocument": ["aapl-20230930.htm"],
    }
    base.update(overrides)
    return base


def _make_payload(**recent_overrides: Any) -> dict[str, Any]:
    return {
        "cik": "0000320193",
        "filings": {"recent": _make_recent(**recent_overrides)},
    }


# ---------------------------------------------------------------------------
# extract_filings — structural error paths
# ---------------------------------------------------------------------------


def test_extract_filings_rejects_non_dict_payload() -> None:
    """extract_filings('not a dict') → TypeError."""
    with pytest.raises(TypeError):
        extract_filings("not a dict")  # type: ignore[arg-type]


def test_extract_filings_rejects_invalid_cik_zero() -> None:
    """cik '0000000000' (all zeros) → ValueError matching 'Invalid SEC CIK'."""
    payload = _make_payload()
    payload["cik"] = "0000000000"

    with pytest.raises(ValueError, match="Invalid SEC CIK"):
        extract_filings(payload)


def test_extract_filings_rejects_non_digit_cik() -> None:
    """cik 'ABCD' (non-digit) → ValueError matching 'valid root CIK'."""
    payload = _make_payload()
    payload["cik"] = "ABCD"

    with pytest.raises(ValueError, match="valid root CIK"):
        extract_filings(payload)


def test_extract_filings_rejects_missing_filings_recent() -> None:
    """Missing 'filings' key entirely → TypeError matching 'filings.recent'."""
    payload: dict[str, Any] = {"cik": "0000320193"}

    with pytest.raises(TypeError, match="filings.recent"):
        extract_filings(payload)


def test_extract_filings_rejects_missing_form_list() -> None:
    """'recent' dict missing 'form' key → TypeError matching 'form'."""
    payload: dict[str, Any] = {
        "cik": "0000320193",
        "filings": {
            "recent": {
                "filingDate": ["2024-01-25"],
                "accessionNumber": ["0000320193-24-000006"],
                "primaryDocument": ["aapl-20230930.htm"],
                # 'form' is intentionally absent
            }
        },
    }

    with pytest.raises(TypeError, match="form"):
        extract_filings(payload)


# ---------------------------------------------------------------------------
# extract_filings — per-row validation errors
# ---------------------------------------------------------------------------


def test_extract_filings_rejects_invalid_filing_date_format() -> None:
    """filingDate entry 'not-a-date' for a 10-K → ValueError matching 'filingDate'."""
    payload = _make_payload(filingDate=["not-a-date"])

    with pytest.raises(ValueError, match="filingDate"):
        extract_filings(payload)


def test_extract_filings_rejects_invalid_report_date_format() -> None:
    """reportDate entry 'not-a-date' for a 10-K → ValueError matching 'reportDate'."""
    payload = _make_payload(reportDate=["not-a-date"])

    with pytest.raises(ValueError, match="reportDate"):
        extract_filings(payload)


def test_extract_filings_rejects_non_string_report_date() -> None:
    """reportDate entry 123 (integer) for a 10-K → TypeError matching 'reportDate'."""
    payload = _make_payload(reportDate=[123])

    with pytest.raises(TypeError, match="reportDate"):
        extract_filings(payload)


def test_extract_filings_rejects_invalid_primary_document_with_slash() -> None:
    """primaryDocument 'path/to/file.htm' (contains slash) → ValueError matching 'primaryDocument'."""
    payload = _make_payload(primaryDocument=["path/to/file.htm"])

    with pytest.raises(ValueError, match="primaryDocument"):
        extract_filings(payload)


def test_extract_filings_accepts_empty_report_date() -> None:
    """reportDate entry '' → Filing is created with reporting_date is None."""
    payload = _make_payload(reportDate=[""])

    filings = extract_filings(payload)

    assert len(filings) == 1
    assert filings[0].reporting_date is None


def test_extract_filings_mismatched_report_date_array_length() -> None:
    """reportDate list shorter than other arrays → ValueError matching 'different lengths'."""
    payload = _make_payload(
        form=["10-K", "DEF 14A"],
        filingDate=["2024-01-25", "2024-01-10"],
        accessionNumber=["0000320193-24-000006", "0000320193-24-000002"],
        primaryDocument=["aapl-20230930.htm", "def14a.htm"],
        reportDate=["2023-09-30"],  # only one entry instead of two
    )

    with pytest.raises(ValueError, match="different lengths"):
        extract_filings(payload)


# ---------------------------------------------------------------------------
# Filing.s3_key — edge case
# ---------------------------------------------------------------------------


def test_filing_s3_key_raises_on_empty_primary_document_after_sanitise() -> None:
    """Filing.s3_key raises ValueError when the primary_document sanitises to empty."""
    filing = Filing(
        form="10-K",
        filing_date=date(2024, 1, 25),
        accession_number="0000320193-24-000006",
        cik="0000320193",
        primary_document="...",  # strips to empty after re.sub + strip("._-")
        reporting_date=None,
    )

    with pytest.raises(ValueError):
        _ = filing.s3_key
