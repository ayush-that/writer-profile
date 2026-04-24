from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WRITER_PROFILE_",
        extra="ignore",
    )

    anthropic_api_key: SecretStr = Field(alias="ANTHROPIC_API_KEY")
    chroma_path: str = ".chroma"
    profiles_path: str = "./profiles"
    hooks_path: str = "./data/hooks.jsonl"
    writing_model: str = "claude-sonnet-4-6"
    classifier_model: str = "claude-haiku-4-5-20251001"
    judge_model: str = "claude-sonnet-4-6"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    refine_max_iterations: int = 2
    retrieval_k: int = 5
    hook_suggestion_k: int = 5
