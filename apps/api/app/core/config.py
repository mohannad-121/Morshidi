from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_API_ENV_FILE = str(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables when available."""

    app_name: str = "Morshidi API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"

    supabase_url: str | None = None
    supabase_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "supabase_secret_key",
            "supabase_service_role_key",
        ),
    )

    advisor_llm_api_key: SecretStr | None = None
    advisor_llm_model: str | None = None

    policy_embedding_api_key: SecretStr | None = None
    policy_embedding_model: str = "text-embedding-3-large"
    policy_embedding_dimensions: int = 1536

    mock_registration_minimum_disclosure_group_size: int = 3
    mock_registration_max_intents: int = 1000
    mock_registration_max_catalog_courses: int = 10000

    academic_compute_max_concurrent: int = Field(default=1, ge=1, le=4)

    # University integration
    uni_base_url: str = "https://fake-university-aqdn.onrender.com"
    uni_client_id: str = "morshidi"
    uni_client_secret: SecretStr | None = None
    uni_service_key: SecretStr | None = None
    uni_webhook_secret: SecretStr | None = None
    uni_internal_auth_secret: SecretStr | None = None
    uni_university_id: str | None = None

    @field_validator("uni_base_url", mode="after")
    @classmethod
    def normalize_uni_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    model_config = SettingsConfigDict(
        env_file=(_API_ENV_FILE, ".env"),
        extra="ignore",
    )


settings = Settings()
