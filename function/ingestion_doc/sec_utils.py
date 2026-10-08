import os
import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "annual-report-rag/0.1.0 (SEC filings ingestion)",
)


def filing_filename(url: str, row_number: int) -> str:
    filename = PurePosixPath(unquote(urlparse(url).path)).name
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
    if filename in ("", ".", ".."):
        filename = f"filing-row-{row_number}.html"
    return filename


def download_filing(url: str) -> bytes:
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname or ""
    if parsed_url.scheme != "https" or not (
        hostname == "sec.gov" or hostname.endswith(".sec.gov")
    ):
        raise ValueError(f"Filing URL must point to SEC over HTTPS: {url!r}")

    request = Request(url, headers={"User-Agent": SEC_USER_AGENT})
    with urlopen(request, timeout=60) as response:
        final_host = urlparse(response.geturl()).hostname or ""
        if final_host != "sec.gov" and not final_host.endswith(".sec.gov"):
            raise ValueError(
                f"SEC filing redirected to an unexpected host: {final_host}"
            )
        return response.read()
