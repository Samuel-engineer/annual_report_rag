import hashlib
from typing import Any

import pytest

from function.knowledge_base_sync import main


def test_handler_starts_ingestion_job_with_execution_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str]] = []

    class FakeBedrockClient:
        def start_ingestion_job(self, **kwargs: str) -> dict[str, Any]:
            calls.append(kwargs)
            return {"ingestionJob": {"ingestionJobId": "job-123"}}

    monkeypatch.setattr(main, "bedrock_client", FakeBedrockClient())
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-123")
    monkeypatch.setenv("DATA_SOURCE_ID", "source-123")

    result = main.lambda_handler(
        {"operation": "start", "executionId": "execution-arn"},
        None,
    )

    assert result == {"jobId": "job-123"}
    assert calls == [
        {
            "knowledgeBaseId": "kb-123",
            "dataSourceId": "source-123",
            "clientToken": hashlib.sha256(b"execution-arn").hexdigest(),
        }
    ]


def test_handler_returns_ingestion_job_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeBedrockClient:
        def get_ingestion_job(self, **kwargs: str) -> dict[str, Any]:
            assert kwargs == {
                "knowledgeBaseId": "kb-123",
                "dataSourceId": "source-123",
                "ingestionJobId": "job-123",
            }
            return {"ingestionJob": {"status": "COMPLETE"}}

    monkeypatch.setattr(main, "bedrock_client", FakeBedrockClient())
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-123")
    monkeypatch.setenv("DATA_SOURCE_ID", "source-123")

    result = main.lambda_handler({"operation": "status", "jobId": "job-123"}, None)

    assert result == {"jobId": "job-123", "status": "COMPLETE"}


def test_handler_rejects_unknown_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-123")
    monkeypatch.setenv("DATA_SOURCE_ID", "source-123")

    with pytest.raises(ValueError, match="operation"):
        main.lambda_handler({"operation": "invalid"}, None)
