import re
import unicodedata
from typing import Any

SEC_BROWSE_URL = "https://www.sec.gov/edgar/browse/"


def normalise_cik(value: Any) -> str:
    cik = str(value).strip()
    if not cik.isdigit() or len(cik) > 10 or int(cik) == 0:
        raise ValueError(f"Invalid SEC CIK: {value!r}")
    return cik.zfill(10)


def get_companies(event: Any) -> dict[str, str]:
    if not isinstance(event, dict):
        raise TypeError("The Lambda event must be a JSON object.")

    companies = event.get("companies", event)
    if not isinstance(companies, dict) or not companies:
        raise ValueError(
            'Provide companies as {"companies": {"Amazon": "1018724"}} '
            "or as a company-to-CIK JSON object."
        )

    result = {}
    for name, cik in companies.items():
        company_name = str(name).strip()
        if not company_name:
            raise ValueError("Company names cannot be empty.")
        result[company_name] = normalise_cik(cik)
    return result


def company_s3_key(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    key = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_name).strip("._-")
    if not key:
        raise ValueError(f"Company name cannot be used in an S3 key: {name!r}")
    return key


def sec_browse_url(cik: str) -> str:
    return f"{SEC_BROWSE_URL}?CIK={int(cik)}"
