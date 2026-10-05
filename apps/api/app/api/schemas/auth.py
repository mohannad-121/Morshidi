"""Pydantic schemas for Morshidi public authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class UniversityLoginRequest(BaseModel):
    """Request payload for authenticating via external university student credentials."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    student_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Official student ID issued by the external university.",
        examples=["202310001"],
    )
    password: SecretStr = Field(
        ...,
        description="External university portal password. Kept strictly in transient memory.",
    )

    @field_validator("student_id")
    @classmethod
    def validate_student_id(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Student ID must not be empty.")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().strip():
            raise ValueError("Password must not be empty.")
        return v


class SessionData(BaseModel):
    """Morshidi Supabase Auth session tokens."""

    model_config = ConfigDict(extra="forbid")

    access_token: str = Field(..., description="JWT access token representing internal Morshidi user.")
    refresh_token: str = Field(..., description="Supabase Auth refresh token.")
    token_type: str = Field(default="bearer", description="Token type, typically bearer.")
    expires_in: int = Field(default=3600, description="Token lifetime in seconds.")
    expires_at: int | None = Field(default=None, description="UNIX timestamp of expiration.")


class UserData(BaseModel):
    """Internal Morshidi user account details."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Morshidi Supabase Auth user UUID.")
    student_id: str = Field(..., description="Verified external university student ID.")
    email: str = Field(..., description="Canonical internal Morshidi email address.")


class SyncData(BaseModel):
    """Summary of synchronized academic data."""

    model_config = ConfigDict(extra="forbid")

    synced_at: str = Field(..., description="ISO 8601 timestamp of synchronization completion.")
    courses_synced: int = Field(..., ge=0, description="Number of catalog courses referenced.")
    attempts_synced: int = Field(..., ge=0, description="Number of historical grade attempts synced.")
    enrollments_synced: int = Field(..., ge=0, description="Number of active semester enrollments synced.")


class UniversityLoginResponse(BaseModel):
    """Successful university login and session issuance response."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(default=True)
    session: SessionData
    user: UserData
    sync: SyncData


class UniversityLoginErrorResponse(BaseModel):
    """Standardized error response for public university login endpoint."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(default=False)
    error: str = Field(..., description="Machine-readable error code.")
