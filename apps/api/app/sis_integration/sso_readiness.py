"""Identity and SSO claim verification, mapping, and linking with fail-closed security."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .errors import (
    IdentityAlreadyLinkedError,
    IdentityAmbiguousError,
    IdentityNotFoundError,
    TenantMismatchError,
)


class SSOClaimValidator:
    """Validates and processes external IdP claims (OIDC / SAML / JWT) for student identity linking."""

    @staticmethod
    def validate_and_extract_claims(
        claims: dict[str, Any],
        expected_tenant_key: str,
        expected_issuer: str | None = None,
    ) -> dict[str, str]:
        """Validate IdP claims against tenant invariants."""
        # 1. Tenant claim check
        tenant_claim = claims.get("tenant_key") or claims.get("university_tenant") or expected_tenant_key
        if str(tenant_claim).strip().lower() != expected_tenant_key.strip().lower():
            raise TenantMismatchError(
                f"Claim tenant '{tenant_claim}' does not match expected tenant '{expected_tenant_key}'"
            )

        # 2. Issuer verification if configured
        if expected_issuer:
            iss = claims.get("iss") or claims.get("issuer")
            if not iss or str(iss).strip().rstrip("/") != expected_issuer.strip().rstrip("/"):
                raise TenantMismatchError(f"IdP issuer '{iss}' does not match configured '{expected_issuer}'")

        # 3. Required identity subject and student ID
        sub = claims.get("sub") or claims.get("subject")
        if not sub or not str(sub).strip():
            raise IdentityNotFoundError("IdP claims do not contain a valid subject ('sub')")

        student_id = claims.get("student_id") or claims.get("university_student_id") or claims.get("preferred_username")
        if not student_id or not str(student_id).strip():
            raise IdentityNotFoundError("IdP claims do not contain a valid student ID claim")

        email = claims.get("email")

        return {
            "external_subject": str(sub).strip(),
            "university_student_id": str(student_id).strip(),
            "email": str(email).strip() if email else "",
            "idp_issuer": str(claims.get("iss") or expected_issuer or "").strip(),
        }

    @staticmethod
    def evaluate_linkage(
        claims: dict[str, str],
        existing_identities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Determine whether the SSO claim can be safely linked to a Morshidi student identity."""
        sub = claims["external_subject"]
        student_id = claims["university_student_id"]

        for ident in existing_identities:
            ext_sub = ident.get("external_subject")
            ext_id = str(ident.get("university_student_id") or ident.get("external_student_id") or "")

            # Exact match: same external subject and student id -> Valid and linked
            if ext_sub and ext_sub == sub:
                if ext_id == student_id:
                    return {"action": "EXISTING_LINK", "identity_id": ident.get("id"), "status": "LINKED"}
                # Conflict: same subject but different student ID
                raise IdentityAmbiguousError(
                    f"External subject '{sub}' is already bound to student '{ext_id}', conflict with '{student_id}'"
                )

            # Different subject claiming an already-linked student ID
            if ext_id == student_id and ext_sub and ext_sub != sub:
                raise IdentityAlreadyLinkedError(
                    f"Student ID '{student_id}' is already linked to a different IdP subject"
                )

        # No conflicting link found, candidate for fresh linkage
        return {"action": "CREATE_LINK", "status": "PENDING"}

