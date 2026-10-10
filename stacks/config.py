from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    embedding_dimension: int = 1024
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
