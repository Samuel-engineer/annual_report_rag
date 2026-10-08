import pytest
from function.ingestion_excel import utils


def test_get_companies_accepts_wrapped_payload_and_normalises_cik() -> None:
    assert utils.get_companies({"companies": {"Amazon": "1018724", "Example": 42}}) == {
        "Amazon": "0001018724",
        "Example": "0000000042",
    }


def test_get_companies_rejects_invalid_cik() -> None:
    with pytest.raises(ValueError, match="Invalid SEC CIK"):
        utils.get_companies({"Amazon": "not-a-cik"})


def test_get_companies_rejects_non_object_event() -> None:
    with pytest.raises(TypeError, match="JSON object"):
        utils.get_companies(["Amazon", "1018724"])


@pytest.mark.parametrize("cik", ["0", "12345678901"])
def test_normalise_cik_rejects_zero_and_overlong_values(cik: str) -> None:
    with pytest.raises(ValueError, match="Invalid SEC CIK"):
        utils.normalise_cik(cik)


def test_company_s3_key_normalises_name() -> None:
    assert utils.company_s3_key(" Société Amazon! ") == "Societe_Amazon"


def test_company_s3_key_rejects_name_without_usable_characters() -> None:
    with pytest.raises(ValueError, match="cannot be used"):
        utils.company_s3_key("!!!")


def test_sec_browse_url_uses_unpadded_cik() -> None:
    assert utils.sec_browse_url("0001018724") == (
        "https://www.sec.gov/edgar/browse/?CIK=1018724"
    )
