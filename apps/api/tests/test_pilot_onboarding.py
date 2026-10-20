"""Comprehensive test suite for Pilot Onboarding, State Machine, Write Enablement Gate,
Acceptance Engine, and Institutional Pilot APIs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.institutional_pilots import _service
from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.pilot_onboarding.acceptance_engine import PilotAcceptanceEngine
from app.pilot_onboarding.defaults import (
    DATA_REQUIREMENTS_MATRIX,
    DEFAULT_ACCEPTANCE_CHECKS,
    DEFAULT_IT_REQUIREMENTS,
    SECURITY_QUESTIONNAIRE_SCHEMA,
    TECHNICAL_QUESTIONNAIRE_SCHEMA,
)
from app.pilot_onboarding.models import (
    AcceptanceCategory,
    AcceptanceStatus,
    BlockerSeverity,
    BlockerStatus,
    PilotAcceptanceCheck,
    PilotActivity,
    PilotBlocker,
    PilotCohortScope,
    PilotMode,
    PilotRequirement,
    PilotSignoff,
    PilotStakeholder,
    PilotStatus,
    PilotSummary,
    RequirementCategory,
    RequirementImportance,
    RequirementStatus,
    SignoffRole,
    SignoffStatus,
    UniversityPilot,
)
from app.pilot_onboarding.service import PilotService, PilotServiceError, PilotTransitionError
from app.pilot_onboarding.state_machine import (
    ALLOWED_TRANSITIONS,
    PilotStateMachine,
)
from app.pilot_onboarding.write_enablement import WriteEnablementGate

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_UNI_ID = UUID("10000000-0000-0000-0000-000000000001")


# ---------------------------------------------------------------------------
# In-Memory Mock Repository for Isolated Service Testing
# ---------------------------------------------------------------------------


class MockPilotRepository:
    """Mock repository providing stateful in-memory storage for pilot onboarding entities."""

    def __init__(self) -> None:
        self.pilots: dict[UUID, UniversityPilot] = {}
        self.requirements: dict[UUID, list[PilotRequirement]] = {}
        self.blockers: dict[UUID, list[PilotBlocker]] = {}
        self.stakeholders: dict[UUID, list[PilotStakeholder]] = {}
        self.checks: dict[UUID, list[PilotAcceptanceCheck]] = {}
        self.signoffs: dict[UUID, list[PilotSignoff]] = {}
        self.activity: dict[UUID, list[PilotActivity]] = {}

    async def list_pilots(self, university_id: UUID | None = None) -> list[UniversityPilot]:
        if university_id:
            return [p for p in self.pilots.values() if p.university_id == university_id]
        return list(self.pilots.values())

    async def get_pilot(self, pilot_id: UUID) -> UniversityPilot | None:
        return self.pilots.get(pilot_id)

    async def create_pilot(self, pilot: UniversityPilot) -> UniversityPilot:
        self.pilots[pilot.id] = pilot
        self.requirements[pilot.id] = []
        self.blockers[pilot.id] = []
        self.stakeholders[pilot.id] = []
        self.checks[pilot.id] = []
        self.signoffs[pilot.id] = []
        self.activity[pilot.id] = []
        return pilot

    async def update_pilot(self, pilot_id: UUID, updates: dict[str, Any]) -> UniversityPilot:
        pilot = self.pilots[pilot_id]
        for k, v in updates.items():
            if k == "status" and isinstance(v, str):
                v = PilotStatus(v)
            if hasattr(pilot, k):
                setattr(pilot, k, v)
        return pilot

    async def bulk_init_requirements(self, pilot_id: UUID, items: list[dict[str, Any]]) -> list[PilotRequirement]:
        reqs = []
        for it in items:
            r = PilotRequirement(
                id=uuid4(),
                pilot_id=pilot_id,
                requirement_key=it["requirement_key"],
                category=it["category"],
                title_ar=it["title_ar"],
                title_en=it["title_en"],
                importance=it.get("importance", RequirementImportance.REQUIRED),
                status=RequirementStatus.NOT_REQUESTED,
            )
            reqs.append(r)
        self.requirements[pilot_id] = reqs
        return reqs

    async def list_requirements(self, pilot_id: UUID) -> list[PilotRequirement]:
        return self.requirements.get(pilot_id, [])

    async def update_requirement(
        self,
        pilot_id: UUID,
        requirement_key: str,
        updates: dict[str, Any],
    ) -> PilotRequirement:
        for r in self.requirements.get(pilot_id, []):
            if r.requirement_key == requirement_key:
                for k, v in updates.items():
                    setattr(r, k, v)
                return r
        raise RuntimeError(f"Requirement {requirement_key} not found")

    async def list_blockers(self, pilot_id: UUID) -> list[PilotBlocker]:
        return self.blockers.get(pilot_id, [])

    async def add_blocker(self, blocker: PilotBlocker) -> PilotBlocker:
        p_id = blocker.pilot_id
        if p_id not in self.blockers:
            self.blockers[p_id] = []
        self.blockers[p_id].append(blocker)
        return blocker

    async def update_blocker(
        self,
        blocker_id: UUID,
        updates: dict[str, Any],
    ) -> PilotBlocker:
        for blist in self.blockers.values():
            for b in blist:
                if b.id == blocker_id:
                    for k, v in updates.items():
                        setattr(b, k, v)
                    return b
        raise RuntimeError(f"Blocker {blocker_id} not found")

    async def list_stakeholders(self, pilot_id: UUID) -> list[PilotStakeholder]:
        return self.stakeholders.get(pilot_id, [])

    async def add_stakeholder(self, stakeholder: PilotStakeholder) -> PilotStakeholder:
        p_id = stakeholder.pilot_id
        if p_id not in self.stakeholders:
            self.stakeholders[p_id] = []
        self.stakeholders[p_id].append(stakeholder)
        return stakeholder

    async def delete_stakeholder(self, stakeholder_id: UUID) -> None:
        for p_id, slist in self.stakeholders.items():
            self.stakeholders[p_id] = [s for s in slist if s.id != stakeholder_id]

    async def bulk_init_acceptance_checks(self, pilot_id: UUID, items: list[dict[str, Any]]) -> list[PilotAcceptanceCheck]:
        chks = []
        for it in items:
            c = PilotAcceptanceCheck(
                id=uuid4(),
                pilot_id=pilot_id,
                check_key=it["check_key"],
                category=it["category"],
                title_ar=it["title_ar"],
                title_en=it["title_en"],
                importance=it.get("importance", RequirementImportance.REQUIRED),
                is_automated=it.get("is_automated", False),
                status=AcceptanceStatus.NOT_TESTED,
            )
            chks.append(c)
        self.checks[pilot_id] = chks
        return chks

    async def list_acceptance_checks(self, pilot_id: UUID) -> list[PilotAcceptanceCheck]:
        return self.checks.get(pilot_id, [])

    async def update_acceptance_check(
        self,
        pilot_id: UUID,
        check_key: str,
        updates: dict[str, Any],
    ) -> PilotAcceptanceCheck:
        for c in self.checks.get(pilot_id, []):
            if c.check_key == check_key:
                for k, v in updates.items():
                    setattr(c, k, v)
                return c
        raise RuntimeError(f"Check {check_key} not found")

    async def list_signoffs(self, pilot_id: UUID) -> list[PilotSignoff]:
        return self.signoffs.get(pilot_id, [])

    async def record_signoff(self, signoff: PilotSignoff) -> PilotSignoff:
        p_id = signoff.pilot_id
        if p_id not in self.signoffs:
            self.signoffs[p_id] = []
        self.signoffs[p_id].append(signoff)
        return signoff

    async def log_activity(
        self,
        pilot_id: UUID,
        action: str,
        actor_id: UUID | None,
        actor_email: str,
        details: dict[str, Any],
    ) -> PilotActivity:
        act = PilotActivity(
            id=uuid4(),
            pilot_id=pilot_id,
            action=action,
            actor_id=actor_id,
            actor_email=actor_email,
            details=details,
            created_at=datetime.now(timezone.utc),
        )
        if pilot_id not in self.activity:
            self.activity[pilot_id] = []
        self.activity[pilot_id].append(act)
        return act

    async def list_activity(self, pilot_id: UUID) -> list[PilotActivity]:
        return self.activity.get(pilot_id, [])


# ---------------------------------------------------------------------------
# Unit Tests: Pilot State Machine
# ---------------------------------------------------------------------------


class TestPilotStateMachine:
    """Tests deterministic state transitions, prerequisite gates, and blocker barriers."""

    def test_all_19_states_defined(self) -> None:
        assert len(PilotStatus) == 19

    def test_valid_step_by_step_progression(self) -> None:
        current = PilotStatus.DRAFT
        # Step through read-only progression
        read_only_path = [
            PilotStatus.DISCOVERY,
            PilotStatus.WAITING_FOR_UNIVERSITY_IT,
            PilotStatus.TECHNICAL_REQUIREMENTS_RECEIVED,
            PilotStatus.SANDBOX_PREPARATION,
            PilotStatus.IDENTITY_CONFIGURATION,
            PilotStatus.ACADEMIC_MAPPING,
            PilotStatus.SECURITY_REVIEW,
            PilotStatus.TECHNICAL_VALIDATION,
            PilotStatus.READ_ONLY_PILOT_READY,
            PilotStatus.READ_ONLY_PILOT_ACTIVE,
            PilotStatus.READ_ONLY_PILOT_ACCEPTANCE,
        ]
        for next_st in read_only_path:
            assert next_st in ALLOWED_TRANSITIONS[current]
            current = next_st

        # Step through write-enablement and acceptance progression
        write_path = [
            PilotStatus.ACCEPTED,
            PilotStatus.WRITE_PILOT_REVIEW,
            PilotStatus.WRITE_ENABLED_PILOT_READY,
            PilotStatus.GO_LIVE_REVIEW,
            PilotStatus.ACCEPTED,
        ]
        for next_st in write_path:
            assert next_st in ALLOWED_TRANSITIONS[current]
            current = next_st

    def test_arbitrary_jump_draft_to_accepted_rejected(self) -> None:
        pilot = UniversityPilot(
            id=uuid4(),
            university_id=TEST_UNI_ID,
            pilot_name="Jump Test",
            status=PilotStatus.DRAFT,
            mode=PilotMode.READ_ONLY_PILOT,
        )
        can_move, reason = PilotStateMachine.can_transition(pilot, PilotStatus.ACCEPTED)
        assert can_move is False
        assert "ILLEGAL_TRANSITION" in (reason or "")

    def test_arbitrary_jump_draft_to_ready_rejected(self) -> None:
        pilot = UniversityPilot(
            id=uuid4(),
            university_id=TEST_UNI_ID,
            pilot_name="Jump Test",
            status=PilotStatus.DRAFT,
            mode=PilotMode.READ_ONLY_PILOT,
        )
        can_move, reason = PilotStateMachine.can_transition(pilot, PilotStatus.READ_ONLY_PILOT_READY)
        assert can_move is False
        assert "ILLEGAL_TRANSITION" in (reason or "")

    def test_sev1_blocker_blocks_ready_transition(self) -> None:
        pilot = UniversityPilot(
            id=uuid4(),
            university_id=TEST_UNI_ID,
            pilot_name="Blocker Test",
            status=PilotStatus.TECHNICAL_VALIDATION,
            mode=PilotMode.READ_ONLY_PILOT,
        )
        sev1_blocker = PilotBlocker(
            id=uuid4(),
            pilot_id=pilot.id,
            blocker_code="BLK_SSO_DOWN",
            title_ar="عطل في بوابة الـ SSO",
            severity=BlockerSeverity.SEV1,
            owner_role="UNIVERSITY_IT",
            status=BlockerStatus.OPEN,
        )
        can_move, reason = PilotStateMachine.can_transition(
            pilot,
            PilotStatus.READ_ONLY_PILOT_READY,
            blockers=[sev1_blocker],
        )
        assert can_move is False
        assert "UNRESOLVED_CRITICAL_BLOCKER" in (reason or "")

    def test_sev2_blocker_does_not_trigger_critical_block(self) -> None:
        pilot = UniversityPilot(
            id=uuid4(),
            university_id=TEST_UNI_ID,
            pilot_name="SEV2 Test",
            status=PilotStatus.TECHNICAL_VALIDATION,
            mode=PilotMode.READ_ONLY_PILOT,
        )
        sev2_blocker = PilotBlocker(
            id=uuid4(),
            pilot_id=pilot.id,
            blocker_code="BLK_LATENCY",
            title_ar="تأخير في استجابة الفهرس",
            severity=BlockerSeverity.SEV2,
            owner_role="UNIVERSITY_IT",
            status=BlockerStatus.OPEN,
        )
        reqs = [
            PilotRequirement(
                id=uuid4(),
                pilot_id=pilot.id,
                requirement_key="TEST_REQ",
                category=RequirementCategory.SIS_API,
                title_ar="متطلب",
                title_en="req",
                importance=RequirementImportance.REQUIRED,
                status=RequirementStatus.VALIDATED,
            )
        ]
        can_move, reason = PilotStateMachine.can_transition(
            pilot,
            PilotStatus.READ_ONLY_PILOT_READY,
            requirements=reqs,
            blockers=[sev2_blocker],
            technical_readiness_pass=True,
        )
        assert can_move is True
        assert reason is None

    def test_blocking_and_resuming_from_blocked(self) -> None:
        pilot = UniversityPilot(
            id=uuid4(),
            university_id=TEST_UNI_ID,
            pilot_name="Resume Test",
            status=PilotStatus.BLOCKED,
            mode=PilotMode.READ_ONLY_PILOT,
        )
        # From BLOCKED, can resume to allowed preparation or discovery states
        can_resume, _ = PilotStateMachine.can_transition(pilot, PilotStatus.DISCOVERY)
        assert can_resume is True
        can_resume_val, _ = PilotStateMachine.can_transition(pilot, PilotStatus.TECHNICAL_VALIDATION)
        assert can_resume_val is True


# ---------------------------------------------------------------------------
# Unit Tests: Write Enablement Gate (12 Criteria)
# ---------------------------------------------------------------------------


class TestWriteEnablementGate:
    """Tests the 12 criteria gating system that prevents unauthorized SIS mutation."""

    def test_all_12_criteria_pass(self) -> None:
        result = WriteEnablementGate.evaluate(
            pilot_id=uuid4(),
            has_registration_write_cap=True,
            has_drop_write_cap=True,
            idempotency_supported=True,
            drift_reconciliation_zero_drift=True,
            integration_audit_active=True,
            sis_health_healthy=True,
            registration_window_authoritative=True,
            section_capacity_authoritative=True,
            schedule_conflict_authoritative=True,
            error_contract_validated=True,
            sandbox_mutation_test_passed=True,
            explicit_platform_admin_approved=True,
        )
        assert result.can_enable_write is True
        assert result.overall_status == "PASS"
        assert len(result.checks) == 12
        assert all(c.status == "PASS" for c in result.checks)

    def test_missing_drop_capability_fails_write_gate(self) -> None:
        result = WriteEnablementGate.evaluate(
            pilot_id=uuid4(),
            has_registration_write_cap=True,
            has_drop_write_cap=False,
            idempotency_supported=True,
            drift_reconciliation_zero_drift=True,
            integration_audit_active=True,
            sis_health_healthy=True,
            registration_window_authoritative=True,
            section_capacity_authoritative=True,
            schedule_conflict_authoritative=True,
            error_contract_validated=True,
            sandbox_mutation_test_passed=True,
            explicit_platform_admin_approved=True,
        )
        assert result.can_enable_write is False
        assert result.overall_status == "FAIL"
        drop_chk = next(c for c in result.checks if c.check_key == "DROP_WRITE_CAPABILITY")
        assert drop_chk.status == "FAIL"

    def test_drift_in_reconciliation_fails_write_gate(self) -> None:
        result = WriteEnablementGate.evaluate(
            pilot_id=uuid4(),
            has_registration_write_cap=True,
            has_drop_write_cap=True,
            idempotency_supported=True,
            drift_reconciliation_zero_drift=False,
            integration_audit_active=True,
            sis_health_healthy=True,
            registration_window_authoritative=True,
            section_capacity_authoritative=True,
            schedule_conflict_authoritative=True,
            error_contract_validated=True,
            sandbox_mutation_test_passed=True,
            explicit_platform_admin_approved=True,
        )
        assert result.can_enable_write is False
        assert result.overall_status == "FAIL"
        drift_chk = next(c for c in result.checks if c.check_key == "DRIFT_RECONCILIATION_VERIFIED")
        assert drift_chk.status == "FAIL"

    def test_internal_academic_authority_fails_write_gate(self) -> None:
        # Invariant: SIS must remain authoritative for windows and capacity
        result = WriteEnablementGate.evaluate(
            pilot_id=uuid4(),
            has_registration_write_cap=True,
            has_drop_write_cap=True,
            idempotency_supported=True,
            drift_reconciliation_zero_drift=True,
            integration_audit_active=True,
            sis_health_healthy=True,
            registration_window_authoritative=False,
            section_capacity_authoritative=False,
            schedule_conflict_authoritative=True,
            error_contract_validated=True,
            sandbox_mutation_test_passed=True,
            explicit_platform_admin_approved=True,
        )
        assert result.can_enable_write is False
        win_chk = next(c for c in result.checks if c.check_key == "REGISTRATION_WINDOW_AUTHORITY")
        cap_chk = next(c for c in result.checks if c.check_key == "SECTION_CAPACITY_AUTHORITY")
        assert win_chk.status == "FAIL"
        assert cap_chk.status == "FAIL"


# ---------------------------------------------------------------------------
# Unit Tests: Pilot Acceptance Engine (Fail-Closed)
# ---------------------------------------------------------------------------


class TestPilotAcceptanceEngine:
    """Tests strict, fail-closed pilot acceptance evaluation."""

    def test_fail_closed_when_required_check_not_tested(self) -> None:
        checks = [
            PilotAcceptanceCheck(
                id=uuid4(),
                pilot_id=uuid4(),
                check_key="ACAD_PLAN_MAPPING",
                category=AcceptanceCategory.MAPPING,
                title_ar="مطابقة الخطط",
                title_en="Plan Mapping",
                importance=RequirementImportance.REQUIRED,
                is_automated=True,
                status=AcceptanceStatus.NOT_TESTED,
            )
        ]
        pilot = UniversityPilot(
            id=uuid4(),
            university_id=TEST_UNI_ID,
            pilot_name="Test Pilot",
            mode=PilotMode.READ_ONLY_PILOT,
        )
        result = PilotAcceptanceEngine.evaluate_suite(
            pilot,
            checks,
            blockers=[],
            signoffs=[],
        )
        assert result["recommendation"] == "BLOCKED"

    def test_fail_closed_when_open_sev1_blocker(self) -> None:
        checks = [
            PilotAcceptanceCheck(
                id=uuid4(),
                pilot_id=uuid4(),
                check_key="MAPPING_ALL",
                category=AcceptanceCategory.MAPPING,
                title_ar="المطابقة كاملة",
                title_en="Mapping All",
                importance=RequirementImportance.REQUIRED,
                is_automated=True,
                status=AcceptanceStatus.PASS,
            )
        ]
        blockers = [
            PilotBlocker(
                id=uuid4(),
                pilot_id=uuid4(),
                blocker_code="BLK_CRITICAL",
                title_ar="عائق حرج",
                severity=BlockerSeverity.SEV1,
                owner_role="UNIVERSITY_IT",
                status=BlockerStatus.OPEN,
            )
        ]
        pilot = UniversityPilot(
            id=uuid4(),
            university_id=TEST_UNI_ID,
            pilot_name="Test Pilot",
            mode=PilotMode.READ_ONLY_PILOT,
        )
        result = PilotAcceptanceEngine.evaluate_suite(
            pilot,
            checks,
            blockers=blockers,
            signoffs=[],
        )
        assert result["recommendation"] == "BLOCKED"

    def test_passes_when_all_passed_and_signoffs_present(self) -> None:
        checks = [
            PilotAcceptanceCheck(
                id=uuid4(),
                pilot_id=uuid4(),
                check_key="ACAD_PLAN_MAPPING",
                category=AcceptanceCategory.MAPPING,
                title_ar="مطابقة الخطط",
                title_en="Plan Mapping",
                importance=RequirementImportance.REQUIRED,
                is_automated=True,
                status=AcceptanceStatus.PASS,
            )
        ]
        signoffs = [
            PilotSignoff(
                id=uuid4(),
                pilot_id=uuid4(),
                signoff_role=SignoffRole.TECHNICAL_SIGN_OFF,
                signee_name="Dr. Ali",
                signee_role="IT Lead",
                status=SignoffStatus.APPROVED,
            ),
            PilotSignoff(
                id=uuid4(),
                pilot_id=uuid4(),
                signoff_role=SignoffRole.ACADEMIC_VALIDATION_SIGN_OFF,
                signee_name="Dr. Omar",
                signee_role="Dean",
                status=SignoffStatus.APPROVED,
            ),
        ]
        pilot = UniversityPilot(
            id=uuid4(),
            university_id=TEST_UNI_ID,
            pilot_name="Test Pilot",
            mode=PilotMode.READ_ONLY_PILOT,
        )
        result = PilotAcceptanceEngine.evaluate_suite(
            pilot,
            checks,
            blockers=[],
            signoffs=signoffs,
        )
        assert result["recommendation"] == "ACCEPTED"


# ---------------------------------------------------------------------------
# Unit Tests: Security Invariants & Data Minimization
# ---------------------------------------------------------------------------


class TestSecurityInvariants:
    """Verifies secret isolation and data minimization guarantees."""

    def test_pilot_requirement_does_not_store_raw_secrets(self) -> None:
        # Verify schema only has secret_ref_name and no raw secret storage
        req = PilotRequirement(
            id=uuid4(),
            pilot_id=uuid4(),
            requirement_key="SIS_API_KEY",
            category=RequirementCategory.SIS_API,
            title_ar="مفتاح واجهة الـ SIS",
            title_en="SIS API Key",
            secret_ref_name="SIS_PROD_API_KEY_ENV",
        )
        assert req.secret_ref_name == "SIS_PROD_API_KEY_ENV"
        assert not hasattr(req, "secret_value")
        assert not hasattr(req, "raw_secret")

    def test_data_minimization_matrix_excludes_financial_and_medical(self) -> None:
        # DATA_REQUIREMENTS_MATRIX must strictly exclude financial, medical, disciplinary, and national IDs
        excluded = DATA_REQUIREMENTS_MATRIX["entities"]["STUDENT"]["not_needed_strictly_excluded"]
        assert "financial_balance" in excluded
        assert "tuition_payment_status" in excluded
        assert "health_medical_records" in excluded
        assert "disciplinary_infractions" in excluded
        assert "national_identification_number" in excluded


# ---------------------------------------------------------------------------
# Integration Tests: Pilot Service & API Routes
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_service() -> PilotService:
    repo = MockPilotRepository()
    return PilotService(repository=repo)


@pytest.fixture
def client(mock_service: PilotService) -> TestClient:
    from app.api.routes.institutional_pilots import _service
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(TEST_USER_ID)
    app.dependency_overrides[_service] = lambda: mock_service
    app.state.pilot_service = mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestPilotApiRoutes:
    """Tests all REST endpoints under /api/v1/institutional/pilots/*."""

    def test_pilot_crud_and_lifecycle(self, client: TestClient) -> None:
        # 1. Create pilot
        payload = {
            "university_id": str(TEST_UNI_ID),
            "pilot_name": "مشروع كلية تكنولوجيا المعلومات ربيع 2026",
            "mode": "READ_ONLY_PILOT",
            "cohort_scope": {
                "faculties": ["كلية تكنولوجيا المعلومات"],
                "majors": ["علم الحاسوب"],
                "estimated_student_count": 80,
                "scope_notes": "دفعة تجريبية أولى",
            },
        }
        resp = client.post("/api/v1/institutional/pilots", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        pilot_id = data["id"]
        assert data["pilot_name"] == payload["pilot_name"]
        assert data["status"] == "DRAFT"

        # 2. List pilots
        resp = client.get("/api/v1/institutional/pilots")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        # 3. Get pilot by ID
        resp = client.get(f"/api/v1/institutional/pilots/{pilot_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == pilot_id

        # 4. Patch pilot
        resp = client.patch(
            f"/api/v1/institutional/pilots/{pilot_id}",
            json={"notes": "ملاحظات متابعة أسبوعية"},
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "ملاحظات متابعة أسبوعية"

        # 5. Transition status DRAFT -> DISCOVERY
        resp = client.post(
            f"/api/v1/institutional/pilots/{pilot_id}/transition",
            json={"target_status": "DISCOVERY", "notes": "بدء مرحلة الاستكشاف الفني"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "DISCOVERY"

        # 6. Invalid transition DISCOVERY -> ACCEPTED fails with 409 Conflict
        resp = client.post(
            f"/api/v1/institutional/pilots/{pilot_id}/transition",
            json={"target_status": "ACCEPTED"},
        )
        assert resp.status_code == 409

        # 7. Get Summary
        resp = client.get(f"/api/v1/institutional/pilots/{pilot_id}/summary")
        assert resp.status_code == 200
        sum_data = resp.json()
        assert sum_data["status"] == "DISCOVERY"
        assert sum_data["requirements_total_count"] == len(DEFAULT_IT_REQUIREMENTS)

        # 8. List and update requirements
        resp = client.get(f"/api/v1/institutional/pilots/{pilot_id}/requirements")
        assert resp.status_code == 200
        reqs = resp.json()
        assert len(reqs) == len(DEFAULT_IT_REQUIREMENTS)

        req_key = reqs[0]["requirement_key"]
        resp = client.patch(
            f"/api/v1/institutional/pilots/{pilot_id}/requirements/{req_key}",
            json={"status": "VALIDATED", "secret_ref_name": "TEST_KEY_ENV", "notes": "تم التحقق"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "VALIDATED"

        # 9. Blockers workflow
        resp = client.post(
            f"/api/v1/institutional/pilots/{pilot_id}/blockers",
            json={
                "blocker_code": "BLK_TEST_1",
                "title_ar": "مشكلة في شهادة SSL للـ API",
                "severity": "SEV1",
                "owner_role": "UNIVERSITY_IT",
            },
        )
        assert resp.status_code == 201
        blk = resp.json()
        blk_id = blk["id"]
        assert blk["severity"] == "SEV1"

        # Resolve blocker
        resp = client.patch(
            f"/api/v1/institutional/pilots/{pilot_id}/blockers/{blk_id}",
            json={"status": "RESOLVED", "resolution_notes": "تم تجديد الشهادة بنجاح"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "RESOLVED"

        # 10. Acceptance Checks
        resp = client.get(f"/api/v1/institutional/pilots/{pilot_id}/acceptance")
        assert resp.status_code == 200
        checks = resp.json()
        assert len(checks) == len(DEFAULT_ACCEPTANCE_CHECKS)

        # Update a check
        chk_key = checks[0]["check_key"]
        resp = client.patch(
            f"/api/v1/institutional/pilots/{pilot_id}/acceptance/{chk_key}",
            json={"status": "PASS", "evidence_ref": "audit_evidence_001.pdf"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "PASS"

        # 11. Record Signoff
        resp = client.post(
            f"/api/v1/institutional/pilots/{pilot_id}/signoffs",
            json={
                "signoff_role": "TECHNICAL_SIGN_OFF",
                "signee_name": "م. أحمد عثمان",
                "signee_role": "مدير مركز الحاسوب",
                "status": "APPROVED",
                "decision_notes": "جاهز للإطلاق التجريبي",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "APPROVED"

        # 12. Write Enablement evaluation
        resp = client.get(f"/api/v1/institutional/pilots/{pilot_id}/write-enablement")
        assert resp.status_code == 200
        wre = resp.json()
        assert "can_enable_write" in wre
        assert "checks" in wre

        # 13. Full Pilot Report
        resp = client.get(f"/api/v1/institutional/pilots/{pilot_id}/report")
        assert resp.status_code == 200
        report = resp.json()
        assert "final_recommendation" in report

        # 14. Activity trail
        resp = client.get(f"/api/v1/institutional/pilots/{pilot_id}/activity")
        assert resp.status_code == 200
        acts = resp.json()
        assert len(acts) >= 3  # create, patch, transition, etc.
