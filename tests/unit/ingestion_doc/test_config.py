"""Tests for function/ingestion_doc/config.py — Settings.from_env()."""

import pytest

from function.ingestion_doc.config import Settings


def test_from_env_returns_settings_with_all_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All three env vars set → dataclass is returned with the correct values."""
    monkeypatch.setenv("EXCEL_BUCKET_NAME", "my-excel-bucket")
    monkeypatch.setenv("RAW_BUCKET_NAME", "my-raw-bucket")
    monkeypatch.setenv("SEC_USER_AGENT", "MyApp/1.0 (user@example.com)")

    settings = Settings.from_env()

    assert settings.excel_bucket_name == "my-excel-bucket"
    assert settings.raw_bucket_name == "my-raw-bucket"
    assert settings.sec_user_agent == "MyApp/1.0 (user@example.com)"


def test_from_env_uses_default_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When SEC_USER_AGENT is not set, the built-in default string is used."""
    monkeypatch.setenv("EXCEL_BUCKET_NAME", "my-excel-bucket")
    monkeypatch.setenv("RAW_BUCKET_NAME", "my-raw-bucket")
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    settings = Settings.from_env()

    assert "@" in settings.sec_user_agent  # default value contains an email


def test_from_env_raises_when_excel_bucket_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """EXCEL_BUCKET_NAME missing/empty → RuntimeError mentioning EXCEL_BUCKET_NAME."""
    monkeypatch.delenv("EXCEL_BUCKET_NAME", raising=False)
    monkeypatch.setenv("RAW_BUCKET_NAME", "my-raw-bucket")
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    with pytest.raises(RuntimeError, match="EXCEL_BUCKET_NAME"):
        Settings.from_env()


def test_from_env_raises_when_excel_bucket_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """EXCEL_BUCKET_NAME set to empty string → RuntimeError mentioning EXCEL_BUCKET_NAME."""
    monkeypatch.setenv("EXCEL_BUCKET_NAME", "")
    monkeypatch.setenv("RAW_BUCKET_NAME", "my-raw-bucket")
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    with pytest.raises(RuntimeError, match="EXCEL_BUCKET_NAME"):
        Settings.from_env()


def test_from_env_raises_when_raw_bucket_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RAW_BUCKET_NAME missing → RuntimeError mentioning RAW_BUCKET_NAME."""
    monkeypatch.setenv("EXCEL_BUCKET_NAME", "my-excel-bucket")
    monkeypatch.delenv("RAW_BUCKET_NAME", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    with pytest.raises(RuntimeError, match="RAW_BUCKET_NAME"):
        Settings.from_env()


def test_from_env_raises_when_raw_bucket_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RAW_BUCKET_NAME set to empty string → RuntimeError mentioning RAW_BUCKET_NAME."""
    monkeypatch.setenv("EXCEL_BUCKET_NAME", "my-excel-bucket")
    monkeypatch.setenv("RAW_BUCKET_NAME", "")
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    with pytest.raises(RuntimeError, match="RAW_BUCKET_NAME"):
        Settings.from_env()


def test_from_env_raises_when_user_agent_missing_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC_USER_AGENT set to a value without '@' → RuntimeError mentioning SEC_USER_AGENT."""
    monkeypatch.setenv("EXCEL_BUCKET_NAME", "my-excel-bucket")
    monkeypatch.setenv("RAW_BUCKET_NAME", "my-raw-bucket")
    monkeypatch.setenv("SEC_USER_AGENT", "MyApp/1.0 no-email-here")

    with pytest.raises(RuntimeError, match="SEC_USER_AGENT"):
        Settings.from_env()
