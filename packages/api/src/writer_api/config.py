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

    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-6"

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
