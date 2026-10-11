"""
Extended tests for function/knowledge_base_sync/main.py — missing branches
not covered by test_handler.py.
"""

import hashlib
from typing import Any

import pytest

from function.knowledge_base_sync import main


# ---------------------------------------------------------------------------
# Fake Bedrock client helpers
# ---------------------------------------------------------------------------


class _FakeBedrockStart:
    """Fake client whose start_ingestion_job returns a configurable response."""

    def __init__(self, response: dict[str, Any]) -> None:
        self.calls: list[dict[str, Any]] = []
        self._response = response

    def start_ingestion_job(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return self._response


class _FakeBedrockStatus:
    """Fake client whose get_ingestion_job returns a configurable response."""

    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    def get_ingestion_job(self, **kwargs: Any) -> dict[str, Any]:
        return self._response


# ---------------------------------------------------------------------------
# operation: "start" — missing / invalid executionId
# ---------------------------------------------------------------------------


def test_handler_start_without_execution_id_omits_client_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """operation 'start' with no executionId key → start_ingestion_job called WITHOUT clientToken."""
    fake_client = _FakeBedrockStart(
        {"ingestionJob": {"ingestionJobId": "job-abc"}}
    )
    monkeypatch.setattr(main, "bedrock_client", fake_client)
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-1")
    monkeypatch.setenv("DATA_SOURCE_ID", "ds-1")

    result = main.lambda_handler({"operation": "start"}, None)

    assert result == {"jobId": "job-abc"}
    assert len(fake_client.calls) == 1
    assert "clientToken" not in fake_client.calls[0]


def test_handler_start_raises_on_empty_execution_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """executionId: '' → ValueError matching 'executionId'."""
    monkeypatch.setattr(
        main,
        "bedrock_client",
        _FakeBedrockStart({"ingestionJob": {"ingestionJobId": "job-abc"}}),
    )
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-1")
    monkeypatch.setenv("DATA_SOURCE_ID", "ds-1")

    with pytest.raises(ValueError, match="executionId"):
        main.lambda_handler({"operation": "start", "executionId": ""}, None)


def test_handler_start_raises_when_bedrock_returns_no_job_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """start_ingestion_job returns {} → RuntimeError matching 'ingestion job ID'."""
    monkeypatch.setattr(main, "bedrock_client", _FakeBedrockStart({}))
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-1")
    monkeypatch.setenv("DATA_SOURCE_ID", "ds-1")

    with pytest.raises(RuntimeError, match="ingestion job ID"):
        main.lambda_handler(
            {"operation": "start", "executionId": "exec-1"}, None
        )


# ---------------------------------------------------------------------------
# operation: "status" — missing / invalid jobId
# ---------------------------------------------------------------------------


def test_handler_status_raises_when_job_id_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """operation 'status' without jobId → ValueError matching 'jobId'."""
    monkeypatch.setattr(
        main, "bedrock_client", _FakeBedrockStatus({"ingestionJob": {"status": "COMPLETE"}})
    )
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-1")
    monkeypatch.setenv("DATA_SOURCE_ID", "ds-1")

    with pytest.raises(ValueError, match="jobId"):
        main.lambda_handler({"operation": "status"}, None)


def test_handler_status_raises_when_bedrock_returns_no_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_ingestion_job returns {} → RuntimeError matching 'no status'."""
    monkeypatch.setattr(main, "bedrock_client", _FakeBedrockStatus({}))
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-1")
    monkeypatch.setenv("DATA_SOURCE_ID", "ds-1")

    with pytest.raises(RuntimeError, match="no status"):
        main.lambda_handler({"operation": "status", "jobId": "job-1"}, None)


# ---------------------------------------------------------------------------
# client token derivation
# ---------------------------------------------------------------------------


def test_handler_client_token_is_sha256_of_execution_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """clientToken in start_ingestion_job equals sha256(b'my-id').hexdigest()."""
    fake_client = _FakeBedrockStart(
        {"ingestionJob": {"ingestionJobId": "job-xyz"}}
    )
    monkeypatch.setattr(main, "bedrock_client", fake_client)
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-1")
    monkeypatch.setenv("DATA_SOURCE_ID", "ds-1")

    main.lambda_handler({"operation": "start", "executionId": "my-id"}, None)

    expected_token = hashlib.sha256(b"my-id").hexdigest()
    assert fake_client.calls[0]["clientToken"] == expected_token
