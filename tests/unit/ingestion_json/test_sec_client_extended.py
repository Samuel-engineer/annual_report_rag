"""
Extended tests for function/ingestion_json/sec_client.py — gzip decompression branch
and invalid CIK rejection.
"""

import gzip
import json
from typing import Any, Self

import pytest

from function.ingestion_json import sec_client

SEC_USER_AGENT = "AnnualReportRag/1.0 (test@example.com)"


# ---------------------------------------------------------------------------
# Fake response helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Plain (non-gzip) fake context-manager response."""

    def __init__(self, body: bytes, content_encoding: str = "") -> None:
        self._body = body
        self.headers: dict[str, str] = {}
        if content_encoding:
            self.headers["Content-Encoding"] = content_encoding

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


# ---------------------------------------------------------------------------
# Test: gzip decompression path
# ---------------------------------------------------------------------------


def test_fetch_submissions_decompresses_gzip_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Response with Content-Encoding: gzip → body is decompressed before JSON parse."""
    raw_payload = json.dumps({"cik": "0001018724"}).encode("utf-8")
    compressed = gzip.compress(raw_payload)

    def fake_urlopen(request: Any, timeout: int) -> _FakeResponse:
        return _FakeResponse(body=compressed, content_encoding="gzip")

    monkeypatch.setattr(sec_client, "urlopen", fake_urlopen)

    result = sec_client.fetch_submissions("0001018724", SEC_USER_AGENT)

    # Result must be the decompressed JSON bytes (not the gzip envelope)
    assert json.loads(result) == {"cik": "0001018724"}


# ---------------------------------------------------------------------------
# Test: invalid CIK rejected before HTTP call
# ---------------------------------------------------------------------------


def test_fetch_submissions_rejects_invalid_cik(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """normalise_cik raises on a bad CIK before any HTTP call is made."""
    calls: list[Any] = []

    def fake_urlopen(request: Any, timeout: int) -> _FakeResponse:
        calls.append(request)
        return _FakeResponse(body=b"{}")

    monkeypatch.setattr(sec_client, "urlopen", fake_urlopen)

    with pytest.raises(ValueError):
        sec_client.fetch_submissions("not-a-cik", SEC_USER_AGENT)

    assert calls == [], "urlopen should not be called for an invalid CIK"
