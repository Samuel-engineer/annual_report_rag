"""Tests for function/ingestion_json/config.py — Settings.from_env()."""

import pytest

from function.ingestion_json.config import Settings


def test_from_env_returns_settings_with_all_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both env vars set → dataclass is returned with the correct values."""
    monkeypatch.setenv("EXCEL_BUCKET_NAME", "my-excel-bucket")
    monkeypatch.setenv("SEC_USER_AGENT", "MyApp/1.0 (user@example.com)")

    settings = Settings.from_env()

    assert settings.excel_bucket_name == "my-excel-bucket"
    assert settings.sec_user_agent == "MyApp/1.0 (user@example.com)"


def test_from_env_uses_default_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When SEC_USER_AGENT is not set, the built-in default string (with '@') is used."""
    monkeypatch.setenv("EXCEL_BUCKET_NAME", "my-excel-bucket")
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    settings = Settings.from_env()

    assert "@" in settings.sec_user_agent


def test_from_env_raises_when_bucket_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """EXCEL_BUCKET_NAME absent → RuntimeError mentioning EXCEL_BUCKET_NAME."""
    monkeypatch.delenv("EXCEL_BUCKET_NAME", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    with pytest.raises(RuntimeError, match="EXCEL_BUCKET_NAME"):
        Settings.from_env()


def test_from_env_raises_when_bucket_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """EXCEL_BUCKET_NAME set to '' → RuntimeError mentioning EXCEL_BUCKET_NAME."""
    monkeypatch.setenv("EXCEL_BUCKET_NAME", "")
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    with pytest.raises(RuntimeError, match="EXCEL_BUCKET_NAME"):
        Settings.from_env()


def test_from_env_raises_when_user_agent_has_no_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC_USER_AGENT without '@' → RuntimeError mentioning SEC_USER_AGENT."""
    monkeypatch.setenv("EXCEL_BUCKET_NAME", "my-excel-bucket")
    monkeypatch.setenv("SEC_USER_AGENT", "MyApp/1.0 no-at-sign-here")

    with pytest.raises(RuntimeError, match="SEC_USER_AGENT"):
        Settings.from_env()
