import json
from typing import Any, Self

import pytest

from function.ingestion_json import sec_client

SEC_USER_AGENT = "AnnualReportRag/1.0 (test@example.com)"


def test_fetch_submissions_uses_padded_cik_and_contact_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[tuple[Any, int]] = []

    class FakeResponse:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"cik":"0001018724"}'

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(sec_client, "urlopen", fake_urlopen)

    body = sec_client.fetch_submissions("0001018724", SEC_USER_AGENT)

    assert body == b'{"cik":"0001018724"}'
    request, timeout = requests[0]
    assert request.full_url == ("https://data.sec.gov/submissions/CIK0001018724.json")
    user_agent = request.get_header("User-agent")
    assert user_agent == SEC_USER_AGENT
    assert request.get_header("Accept") == "application/json"
    assert timeout == 60


@pytest.mark.parametrize("body", [b"not-json", json.dumps([]).encode()])
def test_fetch_submissions_rejects_invalid_json_payload(
    monkeypatch: pytest.MonkeyPatch,
    body: bytes,
) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return body

    monkeypatch.setattr(sec_client, "urlopen", lambda *_args, **_kwargs: FakeResponse())

    with pytest.raises((json.JSONDecodeError, TypeError)):
        sec_client.fetch_submissions("0001018724", SEC_USER_AGENT)
