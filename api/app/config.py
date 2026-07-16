from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    anthropic_api_key: str
    openai_api_key: str
    cohere_api_key: str | None = None


class RetrievalConfig(BaseModel):
    """Every retrieval knob lives here so the eval harness can sweep them.
    Never hardcode these values inline elsewhere."""

    vector_top_k: int = 20
    keyword_top_k: int = 20
    rrf_k: int = 60
    fused_top_k: int = 20
    rerank_top_k: int = 5
    chunk_target_tokens: int = 500
    chunk_overlap_ratio: float = 0.15
    # "local" runs bge-reranker-base on this process (no extra cost, needs
    # the model weights on disk); "cohere" calls the hosted Rerank API.
    reranker: Literal["local", "cohere"] = "local"


settings = Settings()
default_retrieval_config = RetrievalConfig()
