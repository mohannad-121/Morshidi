"""Security, SSRF, secret isolation, capability negotiation, and webhook/SSO tests."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import hmac
import os
import time
from uuid import UUID, uuid4
import pytest

from app.sis_integration.capabilities import (
    CapabilityNegotiator,
    PilotMode,
    SISCapability,
    TenantStatus,
)
from app.sis_integration.errors import (
    IdentityAlreadyLinkedError,
    IdentityAmbiguousError,
    IdentityNotFoundError,
    SSRFSecurityError,
    TenantMismatchError,
    WebhookReplayedError,
    WebhookSignatureInvalidError,
)
from app.sis_integration.mapping_layer import MappingLayer
from app.sis_integration.models import (
    HealthResult,
    NormalizedEnrollment,
    NormalizedGradeAttempt,
    NormalizedStudent,
    UniversityIntegrationConfig,
    UniversityMapping,
    UniversityTenant,
)
from app.sis_integration.pilot_readiness import PilotReadinessEvaluator
from app.sis_integration.reconciliation import ReconciliationEngine
from app.sis_integration.security import (
    mask_secret_status,
    resolve_secret,
    validate_target_url,
)
from app.sis_integration.sso_readiness import SSOClaimValidator
from app.sis_integration.webhook_engine import WebhookEngine


def test_ssrf_prevention():
    """Verify SSRF defense blocks loopback, private IPs, metadata, and invalid schemes."""
    # Invalid schemes
    with pytest.raises(SSRFSecurityError, match="Unsupported URL scheme"):
        validate_target_url("ftp://example.com/api")
    with pytest.raises(SSRFSecurityError, match="Unsupported URL scheme"):
        validate_target_url("file:///etc/passwd")

    # Loopback / Localhost blocked by default
    with pytest.raises(SSRFSecurityError, match="Localhost destination"):
        validate_target_url("http://localhost:8000")
    with pytest.raises(SSRFSecurityError, match="Localhost destination"):
        validate_target_url("http://127.0.0.1:5000/api")

    # Cloud metadata service (169.254.169.254)
    with pytest.raises(SSRFSecurityError, match="prohibited private or metadata network"):
        validate_target_url("http://169.254.169.254/latest/meta-data")

    # Private RFC 1918 networks
    with pytest.raises(SSRFSecurityError, match="prohibited private or metadata network"):
        validate_target_url("http://10.0.0.5/api")
    with pytest.raises(SSRFSecurityError, match="prohibited private or metadata network"):
        validate_target_url("http://192.168.1.100/sis")

    # Valid public HTTPS URL passes
    valid_url = "https://sis.some-university.edu/api/v1"
    assert validate_target_url(valid_url) == "https://sis.some-university.edu/api/v1"

    # Localhost allowed only when explicitly flagged for local testing
    assert validate_target_url("http://127.0.0.1:8000/api", allow_localhost=True) == "http://127.0.0.1:8000/api"


def test_secret_isolation(monkeypatch: pytest.MonkeyPatch):
    """Verify secrets are resolved from environment and never exposed in masked status."""
    monkeypatch.setenv("TEST_SIS_SECRET_KEY", "super-secret-token-12345")

    # Resolved properly
    assert resolve_secret("TEST_SIS_SECRET_KEY") == "super-secret-token-12345"
    assert resolve_secret("NON_EXISTENT_VAR") == ""
    assert resolve_secret(None) == ""

    # Masked status does not leak secret value
    masked_present = mask_secret_status("TEST_SIS_SECRET_KEY")
    assert "super-secret-token-12345" not in masked_present
    assert "CONFIGURED" in masked_present

    masked_missing = mask_secret_status("NON_EXISTENT_VAR")
    assert "MISSING_ENV" in masked_missing
    assert mask_secret_status(None) == "NOT_CONFIGURED"


def test_capability_negotiator():
    """Verify write actions and capabilities are negotiated strictly by pilot mode and status."""
    caps = {SISCapability.STUDENT_PROFILE_READ, SISCapability.REGISTRATION_PREVIEW}

    # 1. Tenant suspended blocks everything
    permitted, reason = CapabilityNegotiator.is_action_permitted(
        "preview", caps, PilotMode.READ_ONLY_PILOT, TenantStatus.SUSPENDED
    )
    assert permitted is False
    assert reason == "TENANT_SUSPENDED"

    # 2. In READ_ONLY_PILOT, register is blocked
    permitted, reason = CapabilityNegotiator.is_action_permitted(
        "register", caps | {SISCapability.REGISTRATION_WRITE}, PilotMode.READ_ONLY_PILOT, TenantStatus.ACTIVE
    )
    assert permitted is False
    assert reason == "WRITE_ACTION_BLOCKED_BY_PILOT_MODE"

    # 3. In WRITE_ENABLED_PILOT, register requires REGISTRATION_WRITE
    permitted, reason = CapabilityNegotiator.is_action_permitted(
        "register", caps, PilotMode.WRITE_ENABLED_PILOT, TenantStatus.ACTIVE
    )
    assert permitted is False
    assert reason == "CAPABILITY_REGISTRATION_WRITE_REQUIRED"

    permitted, reason = CapabilityNegotiator.is_action_permitted(
        "register", caps | {SISCapability.REGISTRATION_WRITE}, PilotMode.WRITE_ENABLED_PILOT, TenantStatus.ACTIVE
    )
    assert permitted is True
    assert reason is None

    # 4. Preview works in READ_ONLY_PILOT if capability is present
    permitted, reason = CapabilityNegotiator.is_action_permitted(
        "preview", caps, PilotMode.READ_ONLY_PILOT, TenantStatus.ACTIVE
    )
    assert permitted is True


def test_webhook_engine():
    """Verify HMAC verification, replay window, and idempotency."""
    engine = WebhookEngine()
    secret = "webhook-hmac-test-secret-key"
    body = b'{"event":"STUDENT_UPDATED","student_id":"2026001"}'

    # Compute valid signature
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    now_ts = str(int(time.time()))

    # 1. Valid webhook accepted
    res = engine.process_inbound_webhook(
        raw_body=body,
        headers={
            "x-morshidi-signature": f"sha256={sig}",
            "x-morshidi-timestamp": now_ts,
            "x-morshidi-event-id": "evt-1001",
        },
        webhook_secret=secret,
    )
    assert res["status"] == "ACCEPTED"
    assert res["event_id"] == "evt-1001"

    # 2. Duplicate event deduplicated
    res_dup = engine.process_inbound_webhook(
        raw_body=body,
        headers={
            "x-morshidi-signature": f"sha256={sig}",
            "x-morshidi-timestamp": now_ts,
            "x-morshidi-event-id": "evt-1001",
        },
        webhook_secret=secret,
    )
    assert res_dup["status"] == "DUPLICATE"

    # 3. Bad signature rejected with WebhookSignatureInvalidError
    with pytest.raises(WebhookSignatureInvalidError):
        engine.process_inbound_webhook(
            raw_body=body,
            headers={
                "x-morshidi-signature": "sha256=invalidhex00000000000000000000000000000000",
                "x-morshidi-timestamp": now_ts,
            },
            webhook_secret=secret,
        )

    # 4. Stale timestamp (> 300s) rejected with WebhookReplayedError
    stale_ts = str(int(time.time()) - 350)
    with pytest.raises(WebhookReplayedError, match="stale"):
        engine.process_inbound_webhook(
            raw_body=body,
            headers={
                "x-morshidi-signature": f"sha256={sig}",
                "x-morshidi-timestamp": stale_ts,
            },
            webhook_secret=secret,
        )


def test_sso_claim_validator():
    """Verify IdP claim validation, tenant mismatch defense, and identity conflict detection."""
    # 1. Valid claim extracted
    claims = {
        "sub": "oidc-sub-9988",
        "student_id": "2026001",
        "email": "student@pilot-uni.edu",
        "tenant_key": "pilot-uni",
        "iss": "https://idp.pilot-uni.edu",
    }
    extracted = SSOClaimValidator.validate_and_extract_claims(
        claims,
        expected_tenant_key="pilot-uni",
        expected_issuer="https://idp.pilot-uni.edu",
    )
    assert extracted["external_subject"] == "oidc-sub-9988"
    assert extracted["university_student_id"] == "2026001"

    # 2. Tenant mismatch fails closed
    with pytest.raises(TenantMismatchError):
        SSOClaimValidator.validate_and_extract_claims(
            claims,
            expected_tenant_key="other-uni",
        )

    # 3. Missing subject fails closed
    bad_claims = dict(claims, sub="")
    with pytest.raises(IdentityNotFoundError):
        SSOClaimValidator.validate_and_extract_claims(bad_claims, expected_tenant_key="pilot-uni")

    # 4. Linkage evaluation: fresh candidate
    linkage = SSOClaimValidator.evaluate_linkage(extracted, existing_identities=[])
    assert linkage["action"] == "CREATE_LINK"

    # 5. Linkage evaluation: existing link
    existing = [{"id": str(uuid4()), "external_subject": "oidc-sub-9988", "university_student_id": "2026001"}]
    linkage_existing = SSOClaimValidator.evaluate_linkage(extracted, existing)
    assert linkage_existing["action"] == "EXISTING_LINK"

    # 6. Linkage evaluation: conflict - same subject claiming different student_id
    existing_conflict = [{"id": str(uuid4()), "external_subject": "oidc-sub-9988", "university_student_id": "2099999"}]
    with pytest.raises(IdentityAmbiguousError):
        SSOClaimValidator.evaluate_linkage(extracted, existing_conflict)

    # 7. Linkage evaluation: conflict - student_id already bound to another subject
    existing_other_sub = [{"id": str(uuid4()), "external_subject": "other-subject-111", "university_student_id": "2026001"}]
    with pytest.raises(IdentityAlreadyLinkedError):
        SSOClaimValidator.evaluate_linkage(extracted, existing_other_sub)


def test_reconciliation_drift_detection():
    """Verify reconciliation detects missing and stale local records while protecting intelligence."""
    uni_id = UUID("10000000-0000-0000-0000-000000000001")
    auth_student = NormalizedStudent(
        university_student_id="2026001",
        full_name="Ahmad Student",
        cumulative_gpa=Decimal("3.75"),
        earned_credit_hours=Decimal("60"),
        academic_standing="GOOD_STANDING",
    )

    # 1. Missing locally
    items = ReconciliationEngine.reconcile_student_profile(uni_id, auth_student, None)
    assert len(items) == 1
    assert items[0].status == "MISSING_LOCALLY"

    # 2. In sync
    matching_local = {
        "cumulative_gpa": "3.75",
        "earned_credit_hours": "60",
        "academic_standing": "GOOD_STANDING",
    }
    items_sync = ReconciliationEngine.reconcile_student_profile(uni_id, auth_student, matching_local)
    assert len(items_sync) == 1
    assert items_sync[0].status == "IN_SYNC"

    # 3. GPA drift -> STALE_LOCALLY
    drifted_local = {
        "cumulative_gpa": "3.50",
        "earned_credit_hours": "60",
        "academic_standing": "GOOD_STANDING",
    }
    items_drift = ReconciliationEngine.reconcile_student_profile(uni_id, auth_student, drifted_local)
    assert any(i.status == "STALE_LOCALLY" and i.details.get("field") == "cumulative_gpa" for i in items_drift)


def test_pilot_readiness_scorecard(monkeypatch: pytest.MonkeyPatch):
    """Verify 16-point deterministic readiness scorecard evaluation."""
    monkeypatch.setenv("TEST_PILOT_SECRET", "valid-secret-token")

    uni_id = UUID("10000000-0000-0000-0000-000000000005")
    tenant = UniversityTenant(
        id=uni_id,
        tenant_key="test-pilot-uni",
        name_ar="جامعة تجريبية",
        name_en="Test Pilot University",
        country="Jordan",
    )
    config = UniversityIntegrationConfig(
        university_id=uni_id,
        provider_type="generic_rest",
        base_url="https://sis.test-pilot.edu",
        auth_method="token",
        secret_env_ref="TEST_PILOT_SECRET",
        supported_capabilities=[
            SISCapability.IDENTITY_AUTH,
            SISCapability.STUDENT_PROFILE_READ,
            SISCapability.ENROLLMENTS_READ,
        ],
        pilot_mode=PilotMode.READ_ONLY_PILOT,
    )
    health = HealthResult(status="HEALTHY", connectivity=True, latency_ms=120.0)
    mapping = MappingLayer(uni_id)

    # Add required mappings
    mapping.add_mapping(UniversityMapping(university_id=uni_id, entity_type="FACULTY", external_code="F1", canonical_id="IT"))
    mapping.add_mapping(UniversityMapping(university_id=uni_id, entity_type="MAJOR", external_code="M1", canonical_id="AI"))
    mapping.add_mapping(UniversityMapping(university_id=uni_id, entity_type="PLAN", external_code="P1", canonical_id="ZU:IT:AI:P12"))
    mapping.add_mapping(UniversityMapping(university_id=uni_id, entity_type="COURSE", external_code="CS1", canonical_id="CS101", canonical_code="CS101"))
    mapping.add_mapping(UniversityMapping(university_id=uni_id, entity_type="TERM", external_code="T1", canonical_id="2026-1"))

    known_entities = {
        "faculty": ["F1"],
        "major": ["M1"],
        "plan": ["P1"],
        "course": ["CS1"],
        "term": ["T1"],
    }

    scorecard = PilotReadinessEvaluator.evaluate(
        tenant, config, health, mapping, known_entities, sync_job_count=1, recent_sync_succeeded=True
    )
    assert scorecard.overall_status == "PASS"
    assert scorecard.checklist["TENANT_CONFIG_EXISTS"] == "PASS"
    assert scorecard.checklist["CREDENTIALS_CONFIGURED"] == "PASS"
    assert scorecard.checklist["CONNECTIVITY_PROBE"] == "PASS"
    assert scorecard.checklist["DATA_ISOLATION_CONFIRMED"] == "PASS"
    assert "مكتملة" in scorecard.summary_ar

