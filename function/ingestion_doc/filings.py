import re
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import quote

ARCHIVE_BASE_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik_raw}/{accession_nodash}/{primary_doc}"
)
SUPPORTED_FORMS = {"10-K": "10K", "DEF 14A": "DEF14A"}
ACCESSION_PATTERN = re.compile(r"^\d{10}-\d{2}-\d{6}$")


@dataclass(frozen=True)
class Filing:
    form: str
    filing_date: date
    accession_number: str
    cik: str
    primary_document: str

    @property
    def archive_url(self) -> str:
        return ARCHIVE_BASE_URL.format(
            cik_raw=str(int(self.cik)),
            accession_nodash=self.accession_number.replace("-", ""),
            primary_doc=quote(self.primary_document, safe=""),
        )

    @property
    def s3_key(self) -> str:
        filename = re.sub(
            r"[^A-Za-z0-9._-]+", "_", self.primary_document.rsplit("/", 1)[-1]
        ).strip("._-")
        if not filename:
            raise ValueError(
                f"Invalid primary document for accession {self.accession_number!r}."
            )
        prefix = SUPPORTED_FORMS[self.form]
        if prefix == "10K":
            return f"{self.filing_date.year}/{int(self.cik)!s}/annual_report_{filename}"
        if prefix == "DEF14A":
            return (
                f"{self.filing_date.year}/{int(self.cik)!s}/proxy_statement_{filename}"
            )
        return f"{self.filing_date.year}/{int(self.cik)!s}/{prefix}_{filename}"


def extract_filings(payload: Any) -> list[Filing]:
    if not isinstance(payload, dict):
        raise TypeError("SEC submissions must be a JSON object.")

    cik_value = payload.get("cik")
    if not isinstance(cik_value, (str, int)) or not str(cik_value).isdigit():
        raise ValueError("SEC submissions is missing a valid root CIK.")
    cik = str(cik_value).zfill(10)
    if len(cik) != 10 or int(cik) == 0:
        raise ValueError(f"Invalid SEC CIK: {cik_value!r}")

    filings_data = payload.get("filings")
    recent = filings_data.get("recent") if isinstance(filings_data, dict) else None
    if not isinstance(recent, dict):
        raise TypeError("SEC submissions is missing filings.recent.")

    fields = ("form", "filingDate", "accessionNumber", "primaryDocument")
    columns: dict[str, list[Any]] = {}
    for field in fields:
        values = recent.get(field)
        if not isinstance(values, list):
            raise TypeError(f"SEC filings.recent is missing the {field!r} list.")
        columns[field] = values

    row_count = len(columns["form"])
    if any(len(values) != row_count for values in columns.values()):
        raise ValueError("SEC filing arrays have different lengths.")

    result: list[Filing] = []
    for index, form_value in enumerate(columns["form"]):
        if not isinstance(form_value, str):
            raise TypeError(f"SEC filing at index {index} has an invalid form.")
        if form_value not in SUPPORTED_FORMS:
            continue

        filing_date_value = columns["filingDate"][index]
        accession_value = columns["accessionNumber"][index]
        primary_document_value = columns["primaryDocument"][index]
        if not isinstance(filing_date_value, str):
            raise TypeError(f"SEC filing at index {index} has an invalid filingDate.")
        try:
            filing_date = date.fromisoformat(filing_date_value)
        except ValueError as error:
            raise ValueError(
                f"SEC filing at index {index} has an invalid filingDate: "
                f"{filing_date_value!r}"
            ) from error
        if not isinstance(accession_value, str) or not ACCESSION_PATTERN.fullmatch(
            accession_value
        ):
            raise ValueError(
                f"SEC filing at index {index} has an invalid accessionNumber."
            )
        if (
            not isinstance(primary_document_value, str)
            or not primary_document_value
            or "/" in primary_document_value
            or "\\" in primary_document_value
            or primary_document_value in {".", ".."}
        ):
            raise ValueError(
                f"SEC filing at index {index} has an invalid primaryDocument."
            )

        result.append(
            Filing(
                form=form_value,
                filing_date=filing_date,
                accession_number=accession_value,
                cik=cik,
                primary_document=primary_document_value,
            )
        )
    return result
