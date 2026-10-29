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
    cors_allowed_origins: str = ""

    supabase_url: str | None = None
    supabase_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "supabase_secret_key",
            "supabase_service_role_key",
        ),
    )

    advisor_llm_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "advisor_llm_api_key",
            "openai_api_key",
            "OPENAI_API_KEY",
        ),
    )
    advisor_llm_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "advisor_llm_model",
            "ADVISOR_LLM_MODEL",
        ),
    )

    # Realtime Live Voice Configuration
    morshidi_live_voice_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "morshidi_live_voice_enabled",
            "MORSHIDI_LIVE_VOICE_ENABLED",
        ),
    )
    morshidi_voice_model: str = Field(
        default="gpt-live-1",
        validation_alias=AliasChoices(
            "morshidi_voice_model",
            "MORSHIDI_VOICE_MODEL",
        ),
    )
    morshidi_voice_fallback_model: str = Field(
        default="gpt-realtime-2.1",
        validation_alias=AliasChoices(
            "morshidi_voice_fallback_model",
            "MORSHIDI_VOICE_FALLBACK_MODEL",
        ),
    )
    morshidi_voice_name: str = Field(
        default="alloy",
        validation_alias=AliasChoices(
            "morshidi_voice_name",
            "MORSHIDI_VOICE_NAME",
        ),
    )
    morshidi_voice_max_duration_seconds: int = Field(
        default=900,
        validation_alias=AliasChoices(
            "morshidi_voice_max_duration_seconds",
            "MORSHIDI_VOICE_MAX_DURATION_SECONDS",
        ),
    )
    morshidi_voice_max_daily_sessions_per_student: int = Field(
        default=25,
        validation_alias=AliasChoices(
            "morshidi_voice_max_daily_sessions_per_student",
            "MORSHIDI_VOICE_MAX_DAILY_SESSIONS_PER_STUDENT",
        ),
    )
    morshidi_voice_max_daily_minutes_per_student: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "morshidi_voice_max_daily_minutes_per_student",
            "MORSHIDI_VOICE_MAX_DAILY_MINUTES_PER_STUDENT",
        ),
    )

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
