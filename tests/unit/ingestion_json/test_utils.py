import pytest

from function.ingestion_json import utils


@pytest.mark.parametrize(
    "event",
    [
        {"enterprises": {"Amazon": "1018724", "Example": 42}},
        {"Amazon": "1018724", "Example": 42},
    ],
)
def test_get_enterprises_normalises_ciks(event: dict[str, object]) -> None:
    assert utils.get_enterprises(event) == {
        "Amazon": "0001018724",
        "Example": "0000000042",
    }


def test_get_enterprises_rejects_invalid_cik() -> None:
    with pytest.raises(ValueError, match="Invalid SEC CIK"):
        utils.get_enterprises({"enterprises": {"Amazon": "not-a-cik"}})


def test_get_enterprises_rejects_non_object_event() -> None:
    with pytest.raises(TypeError, match="JSON object"):
        utils.get_enterprises(["Amazon", "1018724"])


@pytest.mark.parametrize("cik", ["0", "12345678901"])
def test_normalise_cik_rejects_zero_and_overlong_values(cik: str) -> None:
    with pytest.raises(ValueError, match="Invalid SEC CIK"):
        utils.normalise_cik(cik)


def test_enterprise_s3_key_normalises_name() -> None:
    assert utils.enterprise_s3_key(" Société Amazon! ") == "Societe_Amazon"


def test_enterprise_s3_key_rejects_name_without_usable_characters() -> None:
    with pytest.raises(ValueError, match="cannot be used"):
        utils.enterprise_s3_key("!!!")
