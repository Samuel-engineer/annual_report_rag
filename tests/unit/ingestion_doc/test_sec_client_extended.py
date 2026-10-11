"""
Extended tests for function/ingestion_doc/sec_client.py — redirect check (line 41)
and plain-body (non-gzip) path.
"""

import gzip
from typing import Any, Self

import pytest

from function.ingestion_doc import sec_client

SEC_USER_AGENT = "AnnualReportRag/1.0 (test@example.com)"


# ---------------------------------------------------------------------------
# Fake response helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Base fake context-manager response used in most tests."""

    def __init__(
        self,
        body: bytes,
        encoding: str = "",
        final_url: str = "https://www.sec.gov/Archives/edgar/data/320193/file.htm",
    ) -> None:
        self.body = body
        self.headers = {"Content-Encoding": encoding}
        self._final_url = final_url

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body

    def geturl(self) -> str:
        return self._final_url


# ---------------------------------------------------------------------------
# Test: redirect to non-SEC URL raises ValueError
# ---------------------------------------------------------------------------


def test_download_filing_raises_on_redirect_to_non_sec_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FakeResponse.geturl() returns a non-SEC URL → ValueError matching 'unexpected URL'."""

    def fake_urlopen(request: Any, timeout: int) -> _FakeResponse:
        return _FakeResponse(
            body=b"data",
            encoding="",
            final_url="https://example.com/file.htm",  # NOT sec.gov
        )

    monkeypatch.setattr(sec_client, "urlopen", fake_urlopen)
    monkeypatch.setattr(sec_client, "_wait_for_rate_limit", lambda: None)

    with pytest.raises(ValueError, match="unexpected URL"):
        sec_client.download_filing(
            "https://www.sec.gov/Archives/edgar/data/320193/file.htm",
            SEC_USER_AGENT,
        )


# ---------------------------------------------------------------------------
# Test: plain (non-gzip) body returned as-is
# ---------------------------------------------------------------------------


def test_download_filing_returns_plain_body_when_no_gzip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Response without Content-Encoding: gzip → body returned as-is (no decompression)."""

    def fake_urlopen(request: Any, timeout: int) -> _FakeResponse:
        return _FakeResponse(body=b"plain body", encoding="")

    monkeypatch.setattr(sec_client, "urlopen", fake_urlopen)
    monkeypatch.setattr(sec_client, "_wait_for_rate_limit", lambda: None)

    result = sec_client.download_filing(
        "https://www.sec.gov/Archives/edgar/data/320193/file.htm",
        SEC_USER_AGENT,
    )

    assert result == b"plain body"


# ---------------------------------------------------------------------------
# Test: non-HTTPS URL rejected before any HTTP call
# ---------------------------------------------------------------------------


def test_download_filing_rejects_url_not_starting_with_https_sec_gov(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """URL starting with http:// (non-HTTPS) → ValueError before HTTP call is made."""
    calls: list[Any] = []

    def fake_urlopen(request: Any, timeout: int) -> _FakeResponse:
        calls.append(request)
        return _FakeResponse(body=b"data")

    monkeypatch.setattr(sec_client, "urlopen", fake_urlopen)
    monkeypatch.setattr(sec_client, "_wait_for_rate_limit", lambda: None)

    with pytest.raises(ValueError):
        sec_client.download_filing(
            "http://www.sec.gov/Archives/edgar/data/320193/file.htm",
            SEC_USER_AGENT,
        )

    # urlopen must NOT have been called
    assert calls == []
