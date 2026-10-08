from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import Page, sync_playwright


def _download_report(page: Page, filter_value: str, target_path: Path) -> bytes:
    """Ouvre le dropdown, applique le filtre et récupère le fichier."""
    page.locator("#btnGroupDrop1").click()
    page.locator(f'a[data-filter="{filter_value}"]').click()

    with page.expect_download() as download_info:
        page.get_by_role("button", name="Excel", exact=True).click()

    download = download_info.value
    download.save_as(target_path)
    return target_path.read_bytes()


def retrieve_filings_excels(
    url: str,
    search_value: str | None = None,
    filing_date_from: str | None = None,
    filter_values: Sequence[str] = ("annualOrQuarterlyReports", "proxyStatements"),
    user_agent: str | None = None,
) -> dict[str, bytes]:
    """Télécharge les exports Excel pour chaque filtre demandé dans la même session."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(
                accept_downloads=True,
                user_agent=user_agent,
            )
            page.goto(url, wait_until="domcontentloaded")

            if search_value:
                page.locator("#searchbox").fill(search_value)
            if filing_date_from:
                page.locator("#filingDateFrom").fill(filing_date_from)

            results: dict[str, bytes] = {}

            with TemporaryDirectory() as download_dir:
                tmp_dir = Path(download_dir)
                for f_val in filter_values:
                    file_path = tmp_dir / f"{f_val}.xlsx"
                    results[f_val] = _download_report(page, f_val, file_path)

            return results
        finally:
            browser.close()
