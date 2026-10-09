import re
import unicodedata
from typing import Any


def normalise_cik(value: Any) -> str:
    cik = str(value).strip()
    if not cik.isdigit() or len(cik) > 10 or int(cik) == 0:
        raise ValueError(f"Invalid SEC CIK: {value!r}")
    return cik.zfill(10)


def get_enterprises(event: Any) -> dict[str, str]:
    if not isinstance(event, dict):
        raise TypeError("The Lambda event must be a JSON object.")

    enterprises = event.get("enterprises", event)
    if not isinstance(enterprises, dict) or not enterprises:
        raise ValueError(
            'Provide enterprises as {"enterprises": {"Amazon": "1018724"}}.'
        )

    result: dict[str, str] = {}
    for name, cik in enterprises.items():
        enterprise_name = str(name).strip()
        if not enterprise_name:
            raise ValueError("Enterprise names cannot be empty.")
        result[enterprise_name] = normalise_cik(cik)
    return result


def enterprise_s3_key(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    key = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_name).strip("._-")
    if not key:
        raise ValueError(f"Enterprise name cannot be used in an S3 key: {name!r}")
    return key
