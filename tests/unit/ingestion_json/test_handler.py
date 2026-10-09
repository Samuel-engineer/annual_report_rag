from typing import Any

import pytest

from function.ingestion_json import config, main

SEC_USER_AGENT = "AnnualReportRag/1.0 (test@example.com)"


def test_handler_fetches_and_uploads_each_enterprise_submissions_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded_objects: list[dict[str, Any]] = []
    request_calls: list[tuple[str, str]] = []

    class FakeS3Client:
        def put_object(self, **kwargs: Any) -> dict[str, str]:
            uploaded_objects.append(kwargs)
            return {}

    def fake_fetch(cik: str, user_agent: str) -> bytes:
        request_calls.append((cik, user_agent))
        return f'{{"cik": "{cik}"}}'.encode()

    settings = config.Settings(
        excel_bucket_name="excel-bucket",
        sec_user_agent=SEC_USER_AGENT,
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "s3_client", FakeS3Client())
    monkeypatch.setattr(main, "fetch_submissions", fake_fetch)

    result = main.lambda_handler(
        {"enterprises": {"Amazon": "1018724", "Société Amazon!": "789019"}},
        None,
    )

    assert request_calls == [
        ("0001018724", SEC_USER_AGENT),
        ("0000789019", SEC_USER_AGENT),
    ]
    assert result == {
        "enterprises": {
            "Amazon": {
                "cik": "0001018724",
                "bucket": "excel-bucket",
                "key": "Amazon/CIK0001018724.json",
            },
            "Société Amazon!": {
                "cik": "0000789019",
                "bucket": "excel-bucket",
                "key": "Societe_Amazon/CIK0000789019.json",
            },
        }
    }
    assert uploaded_objects == [
        {
            "Bucket": "excel-bucket",
            "Key": "Amazon/CIK0001018724.json",
            "Body": b'{"cik": "0001018724"}',
            "ContentType": "application/json",
        },
        {
            "Bucket": "excel-bucket",
            "Key": "Societe_Amazon/CIK0000789019.json",
            "Body": b'{"cik": "0000789019"}',
            "ContentType": "application/json",
        },
    ]


def test_handler_requires_bucket_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EXCEL_BUCKET_NAME", raising=False)
    monkeypatch.setenv("SEC_USER_AGENT", SEC_USER_AGENT)

    with pytest.raises(RuntimeError, match="EXCEL_BUCKET_NAME"):
        main.lambda_handler({"enterprises": {"Amazon": "1018724"}}, None)


def test_handler_rejects_invalid_event_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = config.Settings("excel-bucket", SEC_USER_AGENT)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(
        main,
        "fetch_submissions",
        lambda *_args: pytest.fail("Invalid events must not call the SEC API."),
    )

    with pytest.raises(ValueError, match="enterprises"):
        main.lambda_handler({"enterprises": {}}, None)
