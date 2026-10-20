"""Integration tests for PilotRepository against local Supabase verifying DB persistence and RLS."""

from __future__ import annotations

import os
from uuid import UUID, uuid4
import pytest

from app.pilot_onboarding.defaults import (
    DEFAULT_ACCEPTANCE_CHECKS,
    DEFAULT_IT_REQUIREMENTS,
)
from app.pilot_onboarding.models import (
    BlockerSeverity,
    BlockerStatus,
    PilotBlocker,
    PilotCohortScope,
    PilotMode,
    PilotSignoff,
    PilotStakeholder,
    PilotStatus,
    SignoffRole,
    SignoffStatus,
    StakeholderRole,
    UniversityPilot,
)
from app.pilot_onboarding.repository import PilotRepository

URL = os.getenv("MORSHIDI_LOCAL_SUPABASE_URL")
SERVER_KEY = os.getenv("MORSHIDI_LOCAL_SUPABASE_SERVER_KEY")
ANON_KEY = os.getenv("MORSHIDI_LOCAL_SUPABASE_ANON_KEY")
pytestmark = pytest.mark.skipif(
    not all((URL, SERVER_KEY, ANON_KEY)),
    reason="set local-only MORSHIDI_LOCAL_SUPABASE_* values",
)
TEST_UNI_ID = UUID("10000000-0000-0000-0000-000000000001")


@pytest.fixture
def local_repo() -> PilotRepository:
    assert URL and SERVER_KEY
    return PilotRepository(supabase_url=URL, server_key=SERVER_KEY)


@pytest.mark.anyio
async def test_pilot_db_lifecycle_and_foreign_keys(local_repo: PilotRepository) -> None:
    """Tests creating, querying, updating, and cascading a pilot entity in local Supabase."""
    pilot_id = uuid4()
    pilot = UniversityPilot(
        id=pilot_id,
        university_id=TEST_UNI_ID,
        pilot_name="اختبار قاعدة البيانات المحلية للدفعة التجريبية",
        status=PilotStatus.DRAFT,
        mode=PilotMode.READ_ONLY_PILOT,
        cohort_scope=PilotCohortScope(
            faculties=["كلية الهندسة"],
            majors=["هندسة الحاسوب"],
            estimated_student_count=60,
            scope_notes="عينة تحقق RLS وتكامل قاعدة البيانات",
        ),
    )

    try:
        # 1. Create pilot
        created = await local_repo.create_pilot(pilot)
        assert created.id == pilot_id
        assert created.pilot_name == pilot.pilot_name

        # 2. Get pilot
        fetched = await local_repo.get_pilot(pilot_id)
        assert fetched is not None
        assert fetched.id == pilot_id
        assert fetched.status == PilotStatus.DRAFT

        # 3. Bulk init requirements
        reqs = await local_repo.bulk_init_requirements(pilot_id, DEFAULT_IT_REQUIREMENTS[:5])
        assert len(reqs) == 5

        # 4. Update requirement status
        updated_req = await local_repo.update_requirement(
            pilot_id,
            reqs[0].requirement_key,
            {"status": "VALIDATED", "secret_ref_name": "LOCAL_SECRET_KEY"},
        )
        assert updated_req.status.value == "VALIDATED"
        assert updated_req.secret_ref_name == "LOCAL_SECRET_KEY"

        # 5. Add Blocker
        blocker = PilotBlocker(
            id=uuid4(),
            pilot_id=pilot_id,
            blocker_code="BLK_LOCAL_001",
            title_ar="عائق تحقق محلي",
            severity=BlockerSeverity.SEV1,
            owner_role="UNIVERSITY_IT",
            status=BlockerStatus.OPEN,
        )
        created_blocker = await local_repo.add_blocker(blocker)
        assert created_blocker.blocker_code == "BLK_LOCAL_001"

        # 6. Bulk init acceptance checks
        checks = await local_repo.bulk_init_acceptance_checks(pilot_id, DEFAULT_ACCEPTANCE_CHECKS[:3])
        assert len(checks) == 3

        # 7. Add Stakeholder
        stk = PilotStakeholder(
            id=uuid4(),
            pilot_id=pilot_id,
            role=StakeholderRole.UNIVERSITY_TECHNICAL_CONTACT,
            name="م. حسام المحلي",
            email="hussam@test.local",
        )
        created_stk = await local_repo.add_stakeholder(stk)
        assert created_stk.name == "م. حسام المحلي"

        # 8. Record signoff
        sign = PilotSignoff(
            id=uuid4(),
            pilot_id=pilot_id,
            signoff_role=SignoffRole.TECHNICAL_SIGN_OFF,
            signee_name="د. سامي",
            signee_role="عميد الكلية",
            status=SignoffStatus.APPROVED,
        )
        created_sign = await local_repo.record_signoff(sign)
        assert created_sign.status == SignoffStatus.APPROVED

        # 9. Log activity & verify list
        await local_repo.log_activity(
            pilot_id,
            "TEST_LOCAL_ACTION",
            actor_id=None,
            actor_email="admin@morshidi.institution",
            details={"test": True},
        )
        acts = await local_repo.list_activity(pilot_id)
        assert any(a.action == "TEST_LOCAL_ACTION" for a in acts)

        # 10. Update pilot status to DISCOVERY
        updated_pilot = await local_repo.update_pilot(pilot_id, {"status": PilotStatus.DISCOVERY.value})
        assert updated_pilot.status == PilotStatus.DISCOVERY

    finally:
        # Cleanup pilot (cascades to all 6 child tables via foreign keys)
        try:
            await local_repo._delete("university_pilots", {"id": f"eq.{pilot_id}"})
        except Exception:
            pass


@pytest.mark.anyio
async def test_pilot_check_constraints_fail_closed(local_repo: PilotRepository) -> None:
    """Verifies that invalid status or mode violates PostgreSQL check constraints."""
    # 1. Invalid status
    bad_status_payload = {
        "id": str(uuid4()),
        "university_id": str(TEST_UNI_ID),
        "pilot_name": "مشروع غير صالح",
        "status": "NON_EXISTENT_STATUS_STATE",
        "mode": "READ_ONLY_PILOT",
    }
    with pytest.raises(Exception) as exc_info:
        await local_repo._post("university_pilots", bad_status_payload)
    assert "status" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

    # 2. Invalid mode
    bad_mode_payload = {
        "id": str(uuid4()),
        "university_id": str(TEST_UNI_ID),
        "pilot_name": "مشروع غير صالح",
        "status": "DRAFT",
        "mode": "UNAUTHORIZED_WRITE_MODE",
    }
    with pytest.raises(Exception) as exc_info:
        await local_repo._post("university_pilots", bad_mode_payload)
    assert "mode" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_pilot_rls_anon_access_rejected() -> None:
    """Verifies that anonymous requests cannot query university_pilots table due to RLS and privilege revoking."""
    assert URL and ANON_KEY
    anon_repo = PilotRepository(supabase_url=URL, server_key=ANON_KEY)
    try:
        with pytest.raises(Exception) as exc_info:
            await anon_repo.list_pilots()
        # Verifies fail-closed: anon is denied access
        err_msg = str(exc_info.value).lower()
        assert "permission denied" in err_msg or "401" in err_msg or "403" in err_msg
    finally:
        await anon_repo.close()
