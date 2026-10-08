from typing import Any, Self

import pytest
from function.ingestion_doc import sec_utils


def test_download_filing_rejects_non_sec_url() -> None:
    with pytest.raises(ValueError, match="must point to SEC"):
        sec_utils.download_filing("https://example.com/filing.htm")


def test_download_filing_fetches_sec_content_and_sets_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_requests: list[Any] = []

    class FakeResponse:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def geturl(self) -> str:
            return "https://www.sec.gov/Archives/filing.htm"

        def read(self) -> bytes:
            return b"SEC filing"

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        seen_requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(sec_utils, "urlopen", fake_urlopen)

    assert (
        sec_utils.download_filing("https://www.sec.gov/Archives/filing.htm")
        == b"SEC filing"
    )
    request, timeout = seen_requests[0]
    assert request.get_header("User-agent") == sec_utils.SEC_USER_AGENT
    assert timeout == 60


def test_download_filing_rejects_redirect_to_non_sec_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def geturl(self) -> str:
            return "https://example.com/filing.htm"

    monkeypatch.setattr(
        sec_utils,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    with pytest.raises(ValueError, match="unexpected host"):
        sec_utils.download_filing("https://www.sec.gov/filing.htm")


def test_filing_filename_uses_sec_path_basename() -> None:
    assert (
        sec_utils.filing_filename(
            "https://www.sec.gov/Archives/annual%20report.htm",
            2,
        )
        == "annual_report.htm"
    )


def test_filing_filename_uses_row_fallback_when_url_has_no_filename() -> None:
    assert sec_utils.filing_filename("https://www.sec.gov/", 7) == ("filing-row-7.html")
