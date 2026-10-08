from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self, cast

import pytest
from playwright.sync_api import Page

from function.ingestion_excel import retrieve_excel


def test_download_report_selects_filter_and_saves_download(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str]] = []

    class FakeLocator:
        def __init__(self, selector: str) -> None:
            self.selector = selector

        def click(self) -> None:
            calls.append(("click", self.selector))

    class FakeDownload:
        def save_as(self, target_path: Path) -> None:
            target_path.write_bytes(b"xlsx contents")

    class FakeDownloadContext:
        value = FakeDownload()

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    class FakePage:
        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator(selector)

        def expect_download(self) -> FakeDownloadContext:
            return FakeDownloadContext()

        def get_by_role(self, *_args: Any, **_kwargs: Any) -> FakeLocator:
            return FakeLocator("Excel button")

    target = tmp_path / "export.xlsx"
    assert (
        retrieve_excel._download_report(
            cast(Page, FakePage()), "annualOrQuarterlyReports", target
        )
        == b"xlsx contents"
    )
    assert calls == [
        ("click", "#btnGroupDrop1"),
        ("click", 'a[data-filter="annualOrQuarterlyReports"]'),
        ("click", "Excel button"),
    ]


def test_retrieve_filings_excels_applies_filters_and_closes_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, Any]] = []

    class FakeDownload:
        def save_as(self, target_path: Path) -> None:
            target_path.write_bytes(target_path.name.encode())

    class FakeDownloadContext:
        value = FakeDownload()

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    class FakeLocator:
        def __init__(self, selector: str) -> None:
            self.selector = selector

        def fill(self, value: str) -> None:
            calls.append((self.selector, value))

        def click(self) -> None:
            calls.append(("click", self.selector))

    class FakePage:
        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator(selector)

        def goto(self, url: str, *, wait_until: str) -> None:
            calls.append(("goto", (url, wait_until)))

        def expect_download(self) -> FakeDownloadContext:
            return FakeDownloadContext()

        def get_by_role(self, *_args: Any, **_kwargs: Any) -> FakeLocator:
            return FakeLocator("Excel button")

    class FakeBrowser:
        def new_page(self, **kwargs: Any) -> FakePage:
            calls.append(("new_page", kwargs))
            return FakePage()

        def close(self) -> None:
            calls.append(("browser_closed", True))

    class FakePlaywrightContext:
        def __enter__(self) -> Any:
            return SimpleNamespace(
                chromium=SimpleNamespace(
                    launch=lambda: calls.append(("launch", True)) or FakeBrowser()
                )
            )

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(
        retrieve_excel,
        "sync_playwright",
        lambda: FakePlaywrightContext(),
    )

    result = retrieve_excel.retrieve_filings_excels(
        "https://www.sec.gov/edgar/browse/?CIK=1018724",
        search_value="10-K",
        filing_date_from="2020-01-01",
        filter_values=["annualOrQuarterlyReports", "proxyStatements"],
        user_agent="test-agent",
    )

    assert result == {
        "annualOrQuarterlyReports": b"annualOrQuarterlyReports.xlsx",
        "proxyStatements": b"proxyStatements.xlsx",
    }
    assert (
        "goto",
        ("https://www.sec.gov/edgar/browse/?CIK=1018724", "domcontentloaded"),
    ) in calls
    assert ("#searchbox", "10-K") in calls
    assert ("#filingDateFrom", "2020-01-01") in calls
    assert (
        "new_page",
        {"accept_downloads": True, "user_agent": "test-agent"},
    ) in calls
    assert ("browser_closed", True) in calls
