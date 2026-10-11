"""
Extended tests for function/ingestion_json/utils.py — empty-name guard and additional
normalise_cik / enterprise_s3_key edge cases.
"""

import pytest

from function.ingestion_json import utils


def test_get_enterprises_rejects_empty_enterprise_name() -> None:
    """{'enterprises': {'': '1018724'}} → ValueError matching 'empty'."""
    with pytest.raises(ValueError, match="empty"):
        utils.get_enterprises({"enterprises": {"": "1018724"}})


def test_normalise_cik_accepts_integer_input() -> None:
    """normalise_cik(1018724) → '0001018724' (zero-padded to 10 digits)."""
    assert utils.normalise_cik(1018724) == "0001018724"


def test_normalise_cik_rejects_non_digit_string() -> None:
    """normalise_cik('abc') → ValueError (non-digit string is invalid)."""
    with pytest.raises(ValueError):
        utils.normalise_cik("abc")


def test_enterprise_s3_key_strips_leading_and_trailing_symbols() -> None:
    """enterprise_s3_key('---amazon---') → 'amazon' (leading/trailing ._- stripped)."""
    result = utils.enterprise_s3_key("---amazon---")
    assert result == "amazon"
