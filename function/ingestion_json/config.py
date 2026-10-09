import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    excel_bucket_name: str
    sec_user_agent: str

    @classmethod
    def from_env(cls) -> "Settings":
        bucket = os.getenv("EXCEL_BUCKET_NAME", "")
        sec_user_agent = os.getenv(
            "SEC_USER_AGENT", "MyApp/1.0 (toaly-samuel-boris.tan@efrei.net)"
        )
        if not bucket:
            raise RuntimeError("EXCEL_BUCKET_NAME must be configured.")
        if not sec_user_agent or "@" not in sec_user_agent:
            raise RuntimeError(
                "SEC_USER_AGENT must be configured with a contact email address."
            )

        return cls(
            excel_bucket_name=bucket,
            sec_user_agent=sec_user_agent,
        )
