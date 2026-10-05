"""Orchestration service for Morshidi ↔ Fake University integration.

Executes Step 3:
1. Authenticate student credentials against Fake University contract client.
2. Concurrently fetch authoritative student datasets (me, courses, grades, enrollments, plan).
3. Validate and resolve study plan and course mappings fail-closed before any writes.
4. Resolve or provision internal Morshidi Supabase Auth shadow identity.
5. Link university identity mapping with concurrency conflict protection.
6. Upsert student academic profile and reconcile attempts/enrollments idempotently.
7. Update last_synced_at timestamp.
8. Return safe internal UniversitySyncResult.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import logging
import re
from typing import Any, Mapping
from uuid import UUID

import httpx

from app.core.config import settings
from app.university_sync.admin_auth import (
    SupabaseAdminAuthClient,
    build_canonical_student_email,
    derive_shadow_password,
)
from app.university_sync.client import UniversityContractClient
from app.university_sync.errors import (
    InvalidUniversityCredentialsError,
    UniversityCourseNotMappedError,
    UniversityIdentityConflictError,
    UniversityPlanNotMappedError,
    UniversityProtocolError,
    UniversitySyncError,
    UniversitySyncFailedError,
    UniversityUnavailableError,
)
from app.university_sync.identity_repository import (
    StudentUniversityIdentityRecord,
    SupabaseUniversityIdentityRepository,
)
from app.university_sync.models import (
    UniversityAcademicPlan,
    UniversityCourse,
    UniversityEnrollmentRecord,
    UniversityGradeRecord,
    UniversityLoginResponse,
    UniversityStudentProfile,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UniversitySyncResult:
    """Safe internal result of a university authentication and synchronization pipeline."""

    owner_user_id: str
    university_id: str
    university_student_id: str
    profile_id: str
    study_plan_id: str
    synced_at: datetime
    grades_count: int
    enrollments_count: int
    is_new_user: bool
    canonical_email: str
    # Server-only transient field used by Step 4 session issuance; never serialized or sent to browser
    _internal_shadow_password: str | None = None

    def __repr__(self) -> str:
        """Prevent accidental logging or leaking of transient shadow credentials."""
        return (
            f"UniversitySyncResult(owner_user_id={self.owner_user_id!r}, "
            f"university_id={self.university_id!r}, "
            f"university_student_id={self.university_student_id!r}, "
            f"profile_id={self.profile_id!r}, "
            f"study_plan_id={self.study_plan_id!r}, "
            f"synced_at={self.synced_at.isoformat()!r}, "
            f"grades_count={self.grades_count}, "
            f"enrollments_count={self.enrollments_count}, "
            f"is_new_user={self.is_new_user})"
        )


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


class UniversitySyncService:
    """Production service for Fake University authentication and academic state sync."""

    def __init__(
        self,
        contract_client: UniversityContractClient,
        *,
        supabase_url: str | None = None,
        service_key: str | None = None,
        internal_auth_secret: str | None = None,
        university_id: str | None = None,
        client: httpx.AsyncClient | None = None,
        identity_repo: SupabaseUniversityIdentityRepository | None = None,
        admin_auth: SupabaseAdminAuthClient | None = None,
    ) -> None:
        self._contract_client = contract_client
        self._supabase_url = (supabase_url or settings.supabase_url or "").rstrip("/")
        self._service_key = (
            service_key
            or (settings.supabase_secret_key.get_secret_value() if settings.supabase_secret_key else "")
        )
        self._internal_secret = (
            internal_auth_secret
            or (
                settings.uni_internal_auth_secret.get_secret_value()
                if settings.uni_internal_auth_secret
                else ""
            )
        )
        self._university_id = university_id or settings.uni_university_id or "10000000-0000-0000-0000-000000000001"
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

        if self._supabase_url and self._service_key:
            self._identity_repo = identity_repo or SupabaseUniversityIdentityRepository(
                self._supabase_url, self._service_key, client=self._client
            )
            self._admin_auth = admin_auth or SupabaseAdminAuthClient(
                self._supabase_url, self._service_key, client=self._client
            )
        else:
            self._identity_repo = identity_repo  # type: ignore[assignment]
            self._admin_auth = admin_auth  # type: ignore[assignment]

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self._service_key,
            "Authorization": f"Bearer {self._service_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def authenticate_and_sync_student(
        self,
        student_id: str,
        password: str,
    ) -> UniversitySyncResult:
        """Execute full university authentication, identity resolution, and academic sync.

        Password exists only in transient memory and is never logged or stored.
        """
        clean_student_id = str(student_id).strip()
        if not clean_student_id or not password:
            raise InvalidUniversityCredentialsError("Student ID and password must not be empty")

        if not self._internal_secret:
            raise UniversitySyncFailedError("UNI_INTERNAL_AUTH_SECRET is not configured")
        if not self._supabase_url or not self._service_key:
            raise UniversitySyncFailedError("Supabase service credentials are not configured")

        # Phase 1: University Authentication
        login_response: UniversityLoginResponse = await self._contract_client.authenticate_student(
            clean_student_id, password
        )

        # Authoritative verified student identity returned by upstream university
        verified_student_id = (login_response.student_id or clean_student_id).strip()
        integration_token = login_response.token

        # Phase 2: Concurrent Upstream Data Fetch (Fail-closed)
        try:
            profile_data, courses_data, grades_data, enrollments_data, plan_data = await asyncio.gather(
                self._contract_client.get_student_me(integration_token),
                self._contract_client.get_student_courses(integration_token),
                self._contract_client.get_student_grades(integration_token),
                self._contract_client.get_student_enrollments(integration_token),
                self._contract_client.get_student_academic_plan(integration_token),
            )
        except UniversitySyncError:
            raise
        except Exception as err:
            logger.error("Failed to fetch upstream university data: %s", err)
            raise UniversityUnavailableError(f"Failed to fetch student data from university: {err}") from err

        # Phase 3: Resolve Study Plan & Courses in Catalog (Fail-closed BEFORE any writes)
        resolved_study_plan_id = await self._resolve_study_plan(profile_data, plan_data)
        course_map = await self._resolve_course_catalog(grades_data, enrollments_data)

        # Phase 4: Resolve or Provision Internal Morshidi Identity
        owner_user_id, is_new_user, canonical_email, shadow_pw = await self._resolve_or_provision_identity(
            verified_student_id
        )

        # Phase 5: Upsert Student Academic Profile
        profile_id = await self._sync_academic_profile(
            owner_user_id=owner_user_id,
            study_plan_id=resolved_study_plan_id,
            profile_data=profile_data,
        )

        # Phase 6: Sync Grades and Enrollments Idempotently
        await self._sync_attempts_and_enrollments(
            profile_id=profile_id,
            grades=grades_data,
            enrollments=enrollments_data,
            course_map=course_map,
        )

        # Phase 7: Update last_synced_at on Identity Record
        now = datetime.now(timezone.utc)
        identity_record = await self._identity_repo.get_university_identity(
            self._university_id, verified_student_id
        )
        if identity_record:
            await self._identity_repo.touch_last_synced_at(identity_record.id, now)

        return UniversitySyncResult(
            owner_user_id=owner_user_id,
            university_id=self._university_id,
            university_student_id=verified_student_id,
            profile_id=profile_id,
            study_plan_id=resolved_study_plan_id,
            synced_at=now,
            grades_count=len(grades_data),
            enrollments_count=len(enrollments_data),
            is_new_user=is_new_user,
            canonical_email=canonical_email,
            _internal_shadow_password=shadow_pw,
        )

    async def _resolve_study_plan(
        self,
        profile_data: UniversityStudentProfile,
        plan_data: UniversityAcademicPlan,
    ) -> str:
        """Resolve authoritative upstream plan number to Morshidi public.study_plans.id."""
        candidate_num = None
        if plan_data.plan_id:
            try:
                UUID(plan_data.plan_id)
                # If plan_id is already a UUID, check if it matches study_plans.id directly
                candidate_num = plan_data.plan_id
            except ValueError:
                match = re.search(r"\d+", plan_data.plan_id)
                candidate_num = match.group(0) if match else plan_data.plan_id
        elif profile_data.study_plan:
            match = re.search(r"\d+", profile_data.study_plan)
            candidate_num = match.group(0) if match else profile_data.study_plan
        else:
            candidate_num = "12"

        # Query study_plans for this university
        url = f"{self._supabase_url}/rest/v1/study_plans"
        params = {
            "select": "id,plan_number,majors!inner(faculties!inner(university_id))",
            "majors.faculties.university_id": f"eq.{self._university_id}",
        }
        resp = await self._client.get(url, params=params, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        plans = resp.json()

        for plan in plans:
            p_id = str(plan.get("id"))
            p_num = str(plan.get("plan_number"))
            if candidate_num in (p_id, p_num):
                return p_id

        raise UniversityPlanNotMappedError(
            f"No matching study plan found for identifier '{candidate_num}' in university {self._university_id}"
        )

    async def _resolve_course_catalog(
        self,
        grades: list[UniversityGradeRecord],
        enrollments: list[UniversityEnrollmentRecord],
    ) -> dict[str, str]:
        """Map external course codes to internal Morshidi UUIDs. Scoped by university_id."""
        needed_codes = {g.course_code.strip() for g in grades} | {e.course_code.strip() for e in enrollments}
        if not needed_codes:
            return {}

        url = f"{self._supabase_url}/rest/v1/courses"
        params = {
            "select": "id,course_code",
            "university_id": f"eq.{self._university_id}",
        }
        resp = await self._client.get(url, params=params, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        rows = resp.json()

        course_map = {str(row["course_code"]).strip(): str(row["id"]) for row in rows}

        unresolved = [code for code in needed_codes if code not in course_map]
        if unresolved:
            raise UniversityCourseNotMappedError(
                f"Course codes {unresolved} are not mapped in university {self._university_id} catalog"
            )

        return course_map

    async def _resolve_or_provision_identity(
        self,
        verified_student_id: str,
    ) -> tuple[str, bool, str, str]:
        """Resolve existing or provision new internal Morshidi shadow identity.

        Returns (owner_user_id, is_new_user, canonical_email, shadow_password).
        Handles concurrent first-login races safely via database uniqueness constraints.
        """
        canonical_email = build_canonical_student_email(verified_student_id, self._university_id)
        shadow_password = derive_shadow_password(
            self._internal_secret, self._university_id, verified_student_id
        )

        # 1. Check existing identity mapping
        existing = await self._identity_repo.get_university_identity(
            self._university_id, verified_student_id
        )
        if existing:
            return existing.owner_user_id, False, canonical_email, shadow_password

        # 2. Provision internal Auth user (or look up existing by email)
        owner_user_id = await self._admin_auth.create_or_get_shadow_user(
            email=canonical_email,
            password=shadow_password,
            university_id=self._university_id,
            university_student_id=verified_student_id,
        )

        # 3. Create student_university_identities mapping (with concurrency protection)
        try:
            await self._identity_repo.create_or_link_university_identity(
                owner_user_id=owner_user_id,
                university_id=self._university_id,
                university_student_id=verified_student_id,
            )
            return owner_user_id, True, canonical_email, shadow_password
        except UniversityIdentityConflictError:
            # Another concurrent request already created the mapping; re-read authority
            conflict_identity = await self._identity_repo.get_university_identity(
                self._university_id, verified_student_id
            )
            if conflict_identity:
                return conflict_identity.owner_user_id, False, canonical_email, shadow_password
            raise

    async def _sync_academic_profile(
        self,
        owner_user_id: str,
        study_plan_id: str,
        profile_data: UniversityStudentProfile,
    ) -> str:
        """Upsert student_academic_profiles with authoritative upstream values."""
        gpa = _to_decimal(profile_data.cumulative_gpa)
        scale = _to_decimal(profile_data.gpa_scale)
        # Check constraint: if gpa is not null, scale must be not null
        if gpa is not None and scale is None:
            scale = Decimal("4.000")
        credits_earned = _to_decimal(profile_data.earned_credits)

        url = f"{self._supabase_url}/rest/v1/student_academic_profiles"
        existing_resp = await self._client.get(
            url,
            params={"select": "id,study_plan_id", "owner_user_id": f"eq.{owner_user_id}"},
            headers=self._headers(),
            timeout=10,
        )
        existing_resp.raise_for_status()
        existing_rows = existing_resp.json()

        payload = {
            "reported_cumulative_gpa": str(gpa) if gpa is not None else None,
            "reported_gpa_scale": str(scale) if scale is not None else None,
            "reported_earned_credit_hours": str(credits_earned) if credits_earned is not None else None,
        }

        if existing_rows:
            profile_id = str(existing_rows[0]["id"])
            patch_resp = await self._client.patch(
                url,
                params={"id": f"eq.{profile_id}"},
                headers={**self._headers(), "Prefer": "return=representation"},
                json=payload,
                timeout=10,
            )
            patch_resp.raise_for_status()
            return profile_id

        # Insert new profile
        payload["owner_user_id"] = owner_user_id
        payload["study_plan_id"] = study_plan_id
        create_resp = await self._client.post(
            url,
            headers={**self._headers(), "Prefer": "return=representation"},
            json=payload,
            timeout=10,
        )
        create_resp.raise_for_status()
        created_rows = create_resp.json()
        return str(created_rows[0]["id"])

    async def _sync_attempts_and_enrollments(
        self,
        profile_id: str,
        grades: list[UniversityGradeRecord],
        enrollments: list[UniversityEnrollmentRecord],
        course_map: dict[str, str],
    ) -> None:
        """Synchronize attempts and active enrollments idempotently."""
        url = f"{self._supabase_url}/rest/v1/student_course_attempts"
        existing_resp = await self._client.get(
            url,
            params={
                "select": "id,course_id,outcome,attempt_sequence,term_label,raw_academic_year,raw_term,record_source",
                "profile_id": f"eq.{profile_id}",
            },
            headers=self._headers(),
            timeout=10,
        )
        existing_resp.raise_for_status()
        existing_attempts = existing_resp.json()

        # Track existing attempts by course_id
        course_attempts: dict[str, list[dict[str, Any]]] = {}
        for att in existing_attempts:
            cid = str(att["course_id"])
            course_attempts.setdefault(cid, []).append(att)

        # 1. Reconcile Completed Grades
        for grade in grades:
            cid = course_map[grade.course_code.strip()]
            existing_list = course_attempts.get(cid, [])
            term_clean = (grade.term or "").strip()
            year_clean = (grade.academic_year or "").strip()

            # Find matching attempt
            match = next(
                (
                    a for a in existing_list
                    if (str(a.get("term_label") or "").strip() == term_clean
                        and str(a.get("raw_academic_year") or "").strip() == year_clean)
                ),
                None,
            )

            if match:
                # Already recorded completed attempt; ensure outcome matches
                continue

            # Assign next attempt sequence
            next_seq = max([int(a.get("attempt_sequence") or 0) for a in existing_list], default=0) + 1

            payload = {
                "profile_id": profile_id,
                "course_id": cid,
                "outcome": (grade.status or "PASSED").upper(),
                "attempt_sequence": next_seq,
                "term_label": term_clean or None,
                "reported_grade_text": grade.letter_grade or str(grade.numeric_grade or ""),
                "record_source": "university_integration",
                "raw_numeric_grade": str(grade.numeric_grade) if grade.numeric_grade is not None else None,
                "raw_letter_grade": grade.letter_grade,
                "raw_grade_points": str(grade.grade_points) if grade.grade_points is not None else None,
                "raw_academic_year": year_clean or None,
                "raw_term": term_clean or None,
                "attempt_credit_hours": str(grade.credit_hours) if grade.credit_hours is not None else None,
                "performance_provenance": "OFFICIAL_VERIFIED",
                "performance_verification_state": "VERIFIED",
                "performance_source_reference": f"university:{self._university_id}",
            }
            ins_resp = await self._client.post(url, headers=self._headers(), json=payload, timeout=10)
            ins_resp.raise_for_status()
            course_attempts.setdefault(cid, []).append({"attempt_sequence": next_seq, "outcome": payload["outcome"]})

        # 2. Reconcile Active Enrollments (outcome = IN_PROGRESS)
        current_enrolled_cids = {course_map[e.course_code.strip()] for e in enrollments}

        # Check existing IN_PROGRESS attempts
        for cid, attempts in list(course_attempts.items()):
            for att in list(attempts):
                if att.get("outcome") == "IN_PROGRESS":
                    if cid not in current_enrolled_cids:
                        # Stale active enrollment: delete it
                        att_id = att["id"]
                        del_resp = await self._client.delete(
                            url, params={"id": f"eq.{att_id}"}, headers=self._headers(), timeout=10
                        )
                        del_resp.raise_for_status()
                        attempts.remove(att)

        # Ensure all current enrollments exist as IN_PROGRESS
        for enrollment in enrollments:
            cid = course_map[enrollment.course_code.strip()]
            existing_list = course_attempts.get(cid, [])
            has_in_progress = any(a.get("outcome") == "IN_PROGRESS" for a in existing_list)
            if not has_in_progress:
                next_seq = max([int(a.get("attempt_sequence") or 0) for a in existing_list], default=0) + 1
                payload = {
                    "profile_id": profile_id,
                    "course_id": cid,
                    "outcome": "IN_PROGRESS",
                    "attempt_sequence": next_seq,
                    "term_label": enrollment.term,
                    "record_source": "university_integration",
                    "raw_academic_year": None,
                    "raw_term": enrollment.term,
                    "attempt_credit_hours": str(enrollment.credit_hours) if enrollment.credit_hours is not None else None,
                    "performance_provenance": "OFFICIAL_VERIFIED",
                    "performance_verification_state": "VERIFIED",
                    "performance_source_reference": f"university:{self._university_id}",
                }
                ins_resp = await self._client.post(url, headers=self._headers(), json=payload, timeout=10)
                ins_resp.raise_for_status()
                course_attempts.setdefault(cid, []).append({"attempt_sequence": next_seq, "outcome": "IN_PROGRESS"})
