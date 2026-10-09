import gzip
import logging
from time import monotonic, sleep
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)
MIN_REQUEST_INTERVAL_SECONDS = 0.11
_last_request_at: float | None = None


def _wait_for_rate_limit() -> None:
    global _last_request_at
    now = monotonic()
    if _last_request_at is not None:
        delay = MIN_REQUEST_INTERVAL_SECONDS - (now - _last_request_at)
        if delay > 0:
            sleep(delay)
    _last_request_at = monotonic()


def download_filing(url: str, sec_user_agent: str) -> bytes:
    if not url.startswith("https://www.sec.gov/Archives/"):
        raise ValueError(f"Filing URL must point to SEC archives over HTTPS: {url!r}")

    _wait_for_rate_limit()
    request = Request(
        url,
        headers={
            "User-Agent": sec_user_agent,
            "Accept-Encoding": "gzip, deflate",
        },
    )
    with urlopen(request, timeout=60) as response:
        body = response.read()
        content_encoding = response.headers.get("Content-Encoding", "").lower()
        if "gzip" in (encoding.strip() for encoding in content_encoding.split(",")):
            body = gzip.decompress(body)
        final_url = response.geturl()

    if not final_url.startswith("https://www.sec.gov/Archives/"):
        raise ValueError(f"SEC filing redirected to an unexpected URL: {final_url!r}")
    logger.info("Downloaded filing %s (%d bytes)", url, len(body))
    return body
