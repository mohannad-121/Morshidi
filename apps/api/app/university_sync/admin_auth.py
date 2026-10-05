"""Supabase Admin Auth client for internal shadow identity provisioning.

This module uses server-side service credentials only to manage internal
Supabase Auth accounts (auth.users) corresponding to external university students.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx

from app.university_sync.errors import (
    InternalIdentityProvisionFailedError,
    UniversityIdentityConflictError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MorshidiSession:
    """Internal Morshidi Supabase Auth session representation."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    expires_at: int | None = None
    user_id: str = ""
    email: str = ""

    def __repr__(self) -> str:
        """Prevent logging of access/refresh tokens."""
        return (
            f"MorshidiSession(token_type={self.token_type!r}, "
            f"expires_in={self.expires_in}, "
            f"expires_at={self.expires_at!r}, "
            f"user_id={self.user_id!r}, "
            f"email={self.email!r})"
        )

# Canonical domain for Fake University (Zarqa) students
ZARQA_UNIVERSITY_ID = "10000000-0000-0000-0000-000000000001"


def build_canonical_student_email(university_student_id: str, university_id: str | UUID) -> str:
    """Deterministically construct the canonical shadow email address for a university student.

    Centralized in this helper per architectural invariant B.
    """
    clean_student_id = str(university_student_id).strip()
    clean_uni_id = str(university_id).strip().lower()

    if clean_uni_id == ZARQA_UNIVERSITY_ID:
        return f"{clean_student_id}@std.morshidi.edu.jo"
    # Future-proof fallback for subsequent institutions
    return f"{clean_student_id}@{clean_uni_id[:8]}.morshidi.internal"


def derive_shadow_password(internal_secret: str, university_id: str | UUID, university_student_id: str) -> str:
    """Derive a deterministic, versioned, server-only internal shadow password.

    HMAC_SHA256(secret, "v1:<university_id>:<student_id>")

    Invariants:
    - Never uses or touches the external university password.
    - Never stored, logged, or returned outside transient process memory.
    - Versioned ("v1:") to allow key rotation and migration.
    """
    if not internal_secret or not internal_secret.strip():
        raise InternalIdentityProvisionFailedError("UNI_INTERNAL_AUTH_SECRET is not configured")

    message = f"v1:{str(university_id).strip().lower()}:{str(university_student_id).strip()}".encode("utf-8")
    derived_hash = hmac.new(internal_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    # High-entropy password satisfying Supabase uppercase, lowercase, number, symbol requirements
    return f"Mor!v1_{derived_hash}"


class SupabaseAdminAuthClient:
    """Server-side client interfacing with Supabase GoTrue Admin endpoints."""

    def __init__(
        self,
        supabase_url: str,
        service_key: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not supabase_url.strip() or not service_key.strip():
            raise ValueError("supabase_url and service_key must not be empty")
        self._supabase_url = supabase_url.rstrip('/')
        self._auth_admin_url = f"{self._supabase_url}/auth/v1/admin"
        self._service_key = service_key
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self._service_key,
            "Authorization": f"Bearer {self._service_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Find an existing auth user by exact email using the GoTrue admin list endpoint."""
        target_email = email.strip().lower()
        try:
            response = await self._client.get(
                f"{self._auth_admin_url}/users",
                headers=self._headers(),
                params={"per_page": 50},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            users: list[dict[str, Any]] = (
                data.get("users", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            )
            for user in users:
                if str(user.get("email", "")).strip().lower() == target_email:
                    return user
            return None
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("Failed to query auth.users by email: %s", error)
            return None

    async def create_or_get_shadow_user(
        self,
        *,
        email: str,
        password: str,
        university_id: str,
        university_student_id: str,
    ) -> str:
        """Provision or locate an internal Supabase Auth user for this student.

        Returns the user's UUID (str).
        """
        payload = {
            "email": email.strip().lower(),
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "university_id": str(university_id),
                "university_student_id": str(university_student_id).strip(),
                "provider": "fake_university",
            },
        }

        try:
            response = await self._client.post(
                f"{self._auth_admin_url}/users",
                headers=self._headers(),
                json=payload,
                timeout=10,
            )
        except httpx.RequestError as error:
            raise InternalIdentityProvisionFailedError(f"Network error calling Supabase Auth Admin: {error}") from error

        if response.status_code in (200, 201):
            user_data = response.json()
            user_id = user_data.get("id")
            if not user_id:
                raise InternalIdentityProvisionFailedError("Supabase Auth Admin response missing user id")
            return str(user_id)

        # 422: User already exists with this email
        if response.status_code == 422:
            existing = await self.find_user_by_email(email)
            if not existing or not existing.get("id"):
                raise InternalIdentityProvisionFailedError(
                    f"User with email {email} reported existing (HTTP 422) but could not be retrieved"
                )

            meta = existing.get("user_metadata") or {}
            # Verify deterministic ownership evidence:
            # The existing account MUST be proven to be a Morshidi-managed shadow identity for the same university_id and student_id
            is_proven_shadow_user = (
                meta.get("provider") == "fake_university"
                and str(meta.get("university_id")) == str(university_id)
                and str(meta.get("university_student_id", "")).strip() == str(university_student_id).strip()
            )
            if not is_proven_shadow_user:
                logger.warning(
                    "Security invariant violation: Existing Auth user %s with email %s has invalid/missing shadow metadata. Failing closed.",
                    existing.get("id"),
                    email,
                )
                raise UniversityIdentityConflictError(
                    f"Existing account with email {email} cannot be proven to be a managed shadow identity for student {university_student_id}."
                )

            user_id = str(existing["id"])
            # Synchronize shadow password on proven managed account
            try:
                await self._client.put(
                    f"{self._auth_admin_url}/users/{user_id}",
                    headers=self._headers(),
                    json={"password": password},
                    timeout=10,
                )
            except Exception as update_err:
                logger.debug("Password sync on existing user returned: %s", update_err)
            return user_id

        # Any other failure
        raise InternalIdentityProvisionFailedError(
            f"Failed to create Supabase shadow identity (HTTP {response.status_code})"
        )

    async def issue_shadow_session(
        self,
        *,
        user_id: str,
        email: str,
        shadow_password: str,
    ) -> MorshidiSession:
        """Issue an internal Morshidi Supabase Auth session for the shadow student account.

        Uses GoTrue password grant against the internal shadow credentials.
        If the initial token request returns 400 (e.g., following a UNI_INTERNAL_AUTH_SECRET rotation
        where the user's stored password hash in Supabase Auth reflects a previous secret), this method
        safely updates the user's password to the current derived credential via the GoTrue Admin API
        and retries the password grant.
        """
        token_url = f"{self._supabase_url}/auth/v1/token?grant_type=password"
        headers = {
            "apikey": self._service_key,
            "Content-Type": "application/json",
        }
        clean_email = email.strip().lower()
        payload = {
            "email": clean_email,
            "password": shadow_password,
        }

        try:
            response = await self._client.post(
                token_url,
                headers=headers,
                json=payload,
                timeout=10,
            )
        except httpx.RequestError as error:
            raise InternalIdentityProvisionFailedError(
                f"Network error requesting Supabase user session: {error}"
            ) from error

        if response.status_code == 400:
            # Secret rotation recovery: Synchronize shadow password via Admin API and retry
            logger.info("GoTrue password grant returned 400; attempting shadow password sync for user %s", user_id)
            try:
                update_resp = await self._client.put(
                    f"{self._auth_admin_url}/users/{user_id}",
                    headers=self._headers(),
                    json={"password": shadow_password},
                    timeout=10,
                )
                if update_resp.status_code in (200, 201):
                    response = await self._client.post(
                        token_url,
                        headers=headers,
                        json=payload,
                        timeout=10,
                    )
            except Exception as update_err:
                logger.warning("Failed to synchronize rotated shadow password: %s", update_err)

        if response.status_code != 200:
            raise InternalIdentityProvisionFailedError(
                f"Failed to issue Supabase user session (HTTP {response.status_code})"
            )

        data = response.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        if not access_token or not refresh_token:
            raise InternalIdentityProvisionFailedError(
                "Supabase session response missing required tokens"
            )

        return MorshidiSession(
            access_token=str(access_token),
            refresh_token=str(refresh_token),
            token_type=str(data.get("token_type", "bearer")),
            expires_in=int(data.get("expires_in", 3600)),
            expires_at=data.get("expires_at"),
            user_id=user_id,
            email=clean_email,
        )
