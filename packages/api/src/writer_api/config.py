from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    exa_api_key: SecretStr = Field(alias="EXA_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    gemini_api_key: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY")
    openrouter_api_key: SecretStr | None = Field(default=None, alias="OPENROUTER_API_KEY")
    mistral_api_key: SecretStr | None = Field(default=None, alias="MISTRAL_API_KEY")

    chroma_api_key: SecretStr | None = Field(default=None, alias="CHROMA_API_KEY")
    chroma_tenant: str | None = Field(default=None, alias="CHROMA_TENANT")
    chroma_database: str | None = Field(default=None, alias="CHROMA_DATABASE")
    chroma_collection: str = "ceo_posts"

    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-6"

    moe_generator_models: list[str] = Field(
        default_factory=lambda: ["claude", "gemini", "mistral"]
    )
    moe_judge_models: list[str] = Field(
        default_factory=lambda: ["claude", "gemini", "mistral"]
    )

    profiles_path: str = "../../data/profiles"
    hooks_path: str = "../../data/hooks.jsonl"

    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "https://writer-profile.pages.dev",
            "https://writer-profile-api-production.up.railway.app",
        ],
        alias="CORS_ORIGINS",
    )


settings = Settings()
