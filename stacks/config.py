from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    embedding_dimension: int = 1024
    embedding_model_id: str = "anthropic.claude-haiku-4-5-20251001-v1:0"
