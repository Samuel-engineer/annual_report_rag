import json
import logging
from typing import Any
from urllib.request import Request, urlopen

logger = logging.getLogger()
logger.setLevel(logging.INFO)


import gzip

from .utils import normalise_cik

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"


def fetch_submissions(cik: str | int, sec_user_agent: str) -> bytes:
    # 1. Normalisation obligatoire : 10 chiffres avec zéros en tête
    cik_10 = normalise_cik(cik)
    url = SUBMISSIONS_URL.format(cik=cik_10)

    logger.info("Fetching SEC submissions for CIK %s from %s", cik_10, url)

    # 2. Construction de la requête avec en-têtes conformes
    request = Request(
        url,
        headers={
            "User-Agent": sec_user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        },
    )

    # 3. Récupération et décompression conditionnelle
    with urlopen(request, timeout=60) as response:
        raw_data = response.read()
        logger.info(
            "Fetched SEC submissions for CIK %s: %d bytes, Content-Encoding: %s",
            cik_10,
            len(raw_data),
            response.headers.get("Content-Encoding"),
        )

        # Si la SEC a renvoyé du gzip, décompresser avant de lire le JSON
        if response.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(raw_data)
        else:
            body = raw_data

    # 4. Validation que le contenu est bien un objet JSON valide
    payload: Any = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("SEC submissions response must be a JSON object.")

    return body
