import gzip
from typing import Any, Self

import pytest

from function.ingestion_doc import sec_client

SEC_USER_AGENT = "AnnualReportRag/1.0 (test@example.com)"


class FakeResponse:
    def __init__(self, body: bytes, encoding: str = "") -> None:
        self.body = body
        self.headers = {"Content-Encoding": encoding}

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body

    def geturl(self) -> str:
        return "https://www.sec.gov/Archives/edgar/data/320193/file.htm"


def test_download_filing_sets_user_agent_and_decompresses_gzip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[tuple[Any, int]] = []

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        requests.append((request, timeout))
        return FakeResponse(gzip.compress(b"annual report"), "gzip")

    monkeypatch.setattr(sec_client, "urlopen", fake_urlopen)
    monkeypatch.setattr(sec_client, "_wait_for_rate_limit", lambda: None)

    assert (
        sec_client.download_filing(
            "https://www.sec.gov/Archives/edgar/data/320193/file.htm",
            SEC_USER_AGENT,
        )
        == b"annual report"
    )
    request, timeout = requests[0]
    assert request.get_header("User-agent") == SEC_USER_AGENT
    assert request.get_header("Accept-encoding") == "gzip, deflate"
    assert timeout == 60


def test_download_filing_rejects_non_archive_url() -> None:
    with pytest.raises(ValueError, match="SEC archives"):
        sec_client.download_filing("https://example.com/file.htm", SEC_USER_AGENT)


def test_rate_limiter_keeps_requests_at_or_below_ten_per_second(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    times = iter([10.0, 10.01, 10.02, 10.13])
    delays: list[float] = []
    monkeypatch.setattr(sec_client, "_last_request_at", None)
    monkeypatch.setattr(sec_client, "monotonic", lambda: next(times))
    monkeypatch.setattr(sec_client, "sleep", delays.append)

    sec_client._wait_for_rate_limit()
    sec_client._wait_for_rate_limit()

    assert delays == pytest.approx([0.1])
