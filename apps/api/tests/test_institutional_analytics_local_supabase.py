"""Real local Supabase release gate for Institutional Intelligence V2.

The suite is opt-in, targets localhost only, creates isolated fixtures through
PostgREST/Auth, and removes them after the module completes.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import math
import os
from statistics import median
from time import perf_counter
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
import pytest
from fastapi.testclient import TestClient

from app.advisor_persistence.repository import SupabaseAdvisorAssignmentRepository
from app.institutional_analytics.copilot import (
    CopilotRequest,
    InstitutionalCopilotService,
    InstitutionalTool,
    ToolSelection,
)
from app.institutional_analytics.models import SectionFact, SimulationRequest
from app.institutional_analytics.repository import SupabaseInstitutionalAnalyticsRepository
from app.institutional_analytics.service import InstitutionalAnalyticsService, OfferingFacts
from app.main import app
from app.mock_registration_persistence.repository import SupabaseMockRegistrationRepository


URL = os.getenv("MORSHIDI_LOCAL_SUPABASE_URL")
SERVER_KEY = os.getenv("MORSHIDI_LOCAL_SUPABASE_SERVER_KEY")
ANON_KEY = os.getenv("MORSHIDI_LOCAL_SUPABASE_ANON_KEY")
pytestmark = pytest.mark.skipif(
    not all((URL, SERVER_KEY, ANON_KEY)),
    reason="set local-only MORSHIDI_LOCAL_SUPABASE_* values",
)


@dataclass(frozen=True)
class LocalFacts:
    university_id: str
    foreign_university_id: str
    plan_id: str
    load_plan_id: str
    course_code: str
    admin_id: str
    admin_token: str
    advisor_id: str
    advisor_token: str
    other_advisor_id: str
    other_advisor_token: str
    student_a_id: str
    student_a_token: str
    student_b_id: str
    foreign_admin_id: str
    foreign_admin_token: str
    created_user_ids: tuple[str, ...]
    created_plan_ids: tuple[str, ...]
    created_course_ids: tuple[str, ...]


def _service_headers(*, representation: bool = True) -> dict[str, str]:
    headers = {"apikey": SERVER_KEY or "", "Authorization": f"Bearer {SERVER_KEY or ''}"}
    if representation:
        headers["Prefer"] = "return=representation"
    return headers


def _user_headers(token: str) -> dict[str, str]:
    return {"apikey": ANON_KEY or "", "Authorization": f"Bearer {token}"}


def _insert(client: httpx.Client, resource: str, payload, *, representation: bool = True):
    response = client.post(
        f"{URL}/rest/v1/{resource}",
        headers=_service_headers(representation=representation),
        json=payload,
    )
    response.raise_for_status()
    return response.json() if representation else None


def _delete(client: httpx.Client, resource: str, **filters: str) -> None:
    response = client.delete(
        f"{URL}/rest/v1/{resource}", headers=_service_headers(representation=False), params=filters,
    )
    response.raise_for_status()


def _create_user(client: httpx.Client, label: str, run_id: str) -> tuple[str, str]:
    email = f"institutional-{label}-{run_id}@local.test"
    password = f"Local-{run_id}-Aa1!"
    created = client.post(
        f"{URL}/auth/v1/admin/users", headers=_service_headers(),
        json={"email": email, "password": password, "email_confirm": True},
    )
    created.raise_for_status()
    signed_in = client.post(
        f"{URL}/auth/v1/token", params={"grant_type": "password"},
        headers={"apikey": ANON_KEY or ""}, json={"email": email, "password": password},
    )
    signed_in.raise_for_status()
    return created.json()["id"], signed_in.json()["access_token"]


@pytest.fixture(scope="module")
def local_facts():
    assert URL is not None and URL.startswith(("http://127.0.0.1", "http://localhost"))
    assert "supabase.co" not in URL
    run_id = uuid4().hex[:12]
    users: list[str] = []
    created_course_ids: list[str] = []
    with httpx.Client(timeout=60) as client:
        university_id = str(uuid5(NAMESPACE_URL, f"institutional-university:{run_id}"))
        faculty_id = str(uuid5(NAMESPACE_URL, f"institutional-faculty:{run_id}"))
        major_id = str(uuid5(NAMESPACE_URL, f"institutional-major:{run_id}"))
        plan_id = str(uuid5(NAMESPACE_URL, f"institutional-plan:{run_id}"))
        group_id = str(uuid5(NAMESPACE_URL, f"institutional-group:{run_id}"))
        load_major_id = str(uuid5(NAMESPACE_URL, f"institutional-load-major:{run_id}"))
        load_plan_id = str(uuid5(NAMESPACE_URL, f"institutional-load-plan:{run_id}"))
        load_group_id = str(uuid5(NAMESPACE_URL, f"institutional-load-group:{run_id}"))
        _insert(client, "universities", {
            "id": university_id, "name_ar": "Institutional local", "country": "LOCAL",
        })
        _insert(client, "faculties", {
            "id": faculty_id, "university_id": university_id, "code": "LOCAL",
            "name_ar": "Institutional local faculty",
        })
        _insert(client, "majors", [
            {"id": major_id, "faculty_id": faculty_id, "code": "BASE", "name_ar": "Base program"},
            {"id": load_major_id, "faculty_id": faculty_id, "code": "LOAD", "name_ar": "Load program"},
        ])
        _insert(client, "study_plans", [
            {"id": plan_id, "major_id": major_id, "plan_number": "12",
             "total_credit_hours": 132, "status": "active"},
            {"id": load_plan_id, "major_id": load_major_id, "plan_number": "12",
             "total_credit_hours": 132, "status": "active"},
        ])
        _insert(client, "requirement_groups", [
            {"id": group_id, "study_plan_id": plan_id, "group_code": "BASE_REQUIRED",
             "name_ar": "Base required", "scope": "major", "requirement_type": "required",
             "required_credit_hours": 9},
            {"id": load_group_id, "study_plan_id": load_plan_id, "group_code": "LOAD_REQUIRED",
             "name_ar": "Load required", "scope": "major", "requirement_type": "required",
             "required_credit_hours": 0},
        ])

        identities = [_create_user(client, label, run_id) for label in (
            "admin", "advisor", "advisor-other", "student-a", "student-b", "foreign-admin", "foreign-student",
        )]
        users.extend(item[0] for item in identities)
        (admin_id, admin_token), (advisor_id, advisor_token), (other_advisor_id, other_advisor_token), \
            (student_a_id, student_a_token), (student_b_id, _), (foreign_admin_id, foreign_admin_token), \
            (foreign_student_id, _) = identities

        course_rows = []
        membership_rows = []
        for index in range(1155):
            course_id = str(uuid5(NAMESPACE_URL, f"institutional-course:{run_id}:{index}"))
            created_course_ids.append(course_id)
            course_rows.append({
                "id": course_id, "university_id": university_id,
                "course_code": f"I{run_id[:4].upper()}{index:04d}",
                "name_en": f"Institutional local course {index}", "catalog_status": "known",
            })
            target_plan = plan_id if index < 3 else load_plan_id
            target_group = group_id if index < 3 else load_group_id
            membership_rows.append({
                "id": str(uuid5(NAMESPACE_URL, f"institutional-membership:{run_id}:{index}")),
                "study_plan_id": target_plan, "course_id": course_id,
                "requirement_group_id": target_group, "credit_hours": 3,
                "prerequisite_logic_status": "not_applicable", "verification_status": "verified",
                "display_order": index, "active": True,
            })
        for start in range(0, 1155, 100):
            _insert(client, "courses", course_rows[start:start + 100], representation=False)
            _insert(client, "study_plan_courses", membership_rows[start:start + 100], representation=False)
        course_code = course_rows[0]["course_code"]

        profile_rows = _insert(client, "student_academic_profiles", [
            {"owner_user_id": student_a_id, "study_plan_id": plan_id, "reported_earned_credit_hours": 90},
            {"owner_user_id": student_b_id, "study_plan_id": plan_id, "reported_earned_credit_hours": 18},
        ])
        _insert(client, "student_course_attempts", {
            "profile_id": profile_rows[0]["id"], "course_id": course_rows[1]["id"],
            "outcome": "PASSED", "attempt_sequence": 1, "record_source": "admin_correction",
        })
        _insert(client, "institutional_memberships", [
            {"subject_user_id": admin_id, "university_id": university_id,
             "provider_namespace": f"local-{run_id}", "role": "INSTITUTIONAL_ANALYST",
             "authority_source": "LOCAL_RELEASE_GATE", "authority_source_version": "1"},
            {"subject_user_id": advisor_id, "university_id": university_id,
             "provider_namespace": f"local-{run_id}", "role": "ACADEMIC_ADVISOR",
             "authority_source": "LOCAL_RELEASE_GATE", "authority_source_version": "1"},
            {"subject_user_id": other_advisor_id, "university_id": university_id,
             "provider_namespace": f"local-{run_id}", "role": "ACADEMIC_ADVISOR",
             "authority_source": "LOCAL_RELEASE_GATE", "authority_source_version": "1"},
        ])
        _insert(client, "advisor_student_assignments", {
            "advisor_user_id": advisor_id, "student_user_id": student_a_id,
            "university_id": university_id, "authority_source": "LOCAL_RELEASE_GATE",
            "authority_version": "1",
        })

        # A second institution proves the repository filter rather than relying
        # on course-code or plan-number uniqueness.
        foreign_university_id = str(uuid5(NAMESPACE_URL, f"institutional-foreign-university:{run_id}"))
        foreign_faculty_id = str(uuid5(NAMESPACE_URL, f"institutional-foreign-faculty:{run_id}"))
        foreign_major_id = str(uuid5(NAMESPACE_URL, f"institutional-foreign-major:{run_id}"))
        foreign_plan_id = str(uuid5(NAMESPACE_URL, f"institutional-foreign-plan:{run_id}"))
        foreign_group_id = str(uuid5(NAMESPACE_URL, f"institutional-foreign-group:{run_id}"))
        foreign_course_id = str(uuid5(NAMESPACE_URL, f"institutional-foreign-course:{run_id}"))
        created_course_ids.append(foreign_course_id)
        _insert(client, "universities", {"id": foreign_university_id, "name_ar": "Foreign local", "country": "LOCAL"})
        _insert(client, "faculties", {"id": foreign_faculty_id, "university_id": foreign_university_id,
                                       "code": "FOREIGN", "name_ar": "Foreign faculty"})
        _insert(client, "majors", {"id": foreign_major_id, "faculty_id": foreign_faculty_id,
                                    "code": "FOREIGN", "name_ar": "Foreign major"})
        _insert(client, "study_plans", {"id": foreign_plan_id, "major_id": foreign_major_id,
                                         "plan_number": "12", "total_credit_hours": 120, "status": "active"})
        _insert(client, "requirement_groups", {"id": foreign_group_id, "study_plan_id": foreign_plan_id,
                                                "group_code": "FOREIGN", "name_ar": "Foreign",
                                                "scope": "major", "requirement_type": "required",
                                                "required_credit_hours": 3})
        _insert(client, "courses", {"id": foreign_course_id, "university_id": foreign_university_id,
                                     "course_code": course_code, "name_en": "Foreign same code",
                                     "catalog_status": "known"})
        _insert(client, "study_plan_courses", {"study_plan_id": foreign_plan_id,
                                                "course_id": foreign_course_id,
                                                "requirement_group_id": foreign_group_id,
                                                "credit_hours": 3, "verification_status": "verified",
                                                "prerequisite_logic_status": "not_applicable"})
        _insert(client, "student_academic_profiles", {"owner_user_id": foreign_student_id,
                                                       "study_plan_id": foreign_plan_id,
                                                       "reported_earned_credit_hours": 30})
        _insert(client, "institutional_memberships", {
            "subject_user_id": foreign_admin_id, "university_id": foreign_university_id,
            "provider_namespace": f"local-{run_id}", "role": "INSTITUTIONAL_ANALYST",
            "authority_source": "LOCAL_RELEASE_GATE", "authority_source_version": "1",
        })

        facts = LocalFacts(
            university_id=university_id, foreign_university_id=foreign_university_id,
            plan_id=plan_id, load_plan_id=load_plan_id, course_code=course_code,
            admin_id=admin_id, admin_token=admin_token, advisor_id=advisor_id,
            advisor_token=advisor_token, other_advisor_id=other_advisor_id,
            other_advisor_token=other_advisor_token, student_a_id=student_a_id,
            student_a_token=student_a_token, student_b_id=student_b_id,
            foreign_admin_id=foreign_admin_id, foreign_admin_token=foreign_admin_token,
            created_user_ids=tuple(users), created_plan_ids=(plan_id, load_plan_id, foreign_plan_id),
            created_course_ids=tuple(created_course_ids),
        )
        try:
            yield facts
        finally:
            user_filter = f"in.({','.join(users)})"
            plan_filter = f"in.({plan_id},{load_plan_id},{foreign_plan_id})"
            _delete(client, "advisor_student_assignments", advisor_user_id=f"in.({advisor_id},{other_advisor_id})")
            _delete(client, "institutional_memberships", subject_user_id=user_filter)
            _delete(client, "student_academic_profiles", owner_user_id=user_filter)
            _delete(client, "study_plan_courses", study_plan_id=plan_filter)
            _delete(client, "requirement_groups", study_plan_id=plan_filter)
            _delete(client, "study_plans", id=plan_filter)
            for start in range(0, len(created_course_ids), 100):
                batch = f"in.({','.join(created_course_ids[start:start + 100])})"
                _delete(client, "courses", id=batch)
            _delete(client, "majors", id=f"in.({major_id},{load_major_id})")
            _delete(client, "majors", id=f"eq.{foreign_major_id}")
            _delete(client, "faculties", id=f"eq.{foreign_faculty_id}")
            _delete(client, "universities", id=f"eq.{foreign_university_id}")
            _delete(client, "faculties", id=f"eq.{faculty_id}")
            _delete(client, "universities", id=f"eq.{university_id}")
            for user_id in users:
                response = client.delete(f"{URL}/auth/v1/admin/users/{user_id}", headers=_service_headers())
                response.raise_for_status()


class _LocalOfferingProvider:
    def __init__(self, course_code: str) -> None:
        self.course_code = course_code

    async def load(self, university_id: str, term_key: str) -> OfferingFacts:
        return OfferingFacts(
            (SectionFact("LOCAL-SECTION", self.course_code, 1, 0, 1, "OPEN"),),
            "local-offering-v1", True, term_key,
        )


def _services(facts: LocalFacts):
    client = httpx.AsyncClient(timeout=60)
    analytics_repo = SupabaseInstitutionalAnalyticsRepository(URL or "", SERVER_KEY or "", client)
    membership_repo = SupabaseMockRegistrationRepository(URL or "", SERVER_KEY or "", client)
    assignment_repo = SupabaseAdvisorAssignmentRepository(URL or "", SERVER_KEY or "", client)
    service = InstitutionalAnalyticsService(
        analytics_repo, membership_repo, assignment_repo, _LocalOfferingProvider(facts.course_code),
        minimum_cohort_size=3,
    )
    return client, analytics_repo, service


def test_real_postgrest_pagination_tenant_scope_metrics_privacy_and_what_if(local_facts: LocalFacts) -> None:
    async def run():
        client, repository, service = _services(local_facts)
        try:
            snapshot = await repository.load_snapshot(local_facts.university_id, "LOCAL-TERM")
            assert len(snapshot.courses) == 1155
            assert local_facts.load_plan_id in {item.plan_id for item in snapshot.programs}
            assert all(item.plan_id != local_facts.created_plan_ids[-1] for item in snapshot.programs)
            assert len(snapshot.students) == 2

            admin = await service.dashboard(
                local_facts.admin_id, university_id=local_facts.university_id, term_key="LOCAL-TERM")
            advisor = await service.dashboard(
                local_facts.advisor_id, university_id=local_facts.university_id, term_key="LOCAL-TERM")
            unassigned = await service.dashboard(
                local_facts.other_advisor_id, university_id=local_facts.university_id, term_key="LOCAL-TERM")
            assert admin.overview.total_active_students.value == 2
            assert advisor.role_scope == "ADVISOR_ASSIGNED"
            assert advisor.overview.total_active_students.value == 1
            assert unassigned.overview.total_active_students.value == 0
            assert sum(admin.overview.students_by_major.values()) == 2
            assert all(item.plan_key != "ZU:FOREIGN:FOREIGN:P12" for item in admin.programs)
            assert next(item for item in admin.programs if item.plan_id == local_facts.plan_id).data_status == "SUPPRESSED"
            assert next(item for item in admin.programs if item.plan_id == local_facts.load_plan_id).data_status == "INSUFFICIENT_DATA"

            course = next(item for item in admin.courses if item.course_code == local_facts.course_code)
            assert course.projected_demand.value == 2
            assert course.projection_components.currently_eligible == 2
            assert course.projection_components.degree_path_upcoming == 2
            assert course.projected_demand.inputs["method"] == "DISTINCT_STUDENT_UNION"
            assert course.capacity_state == "OVER_DEMAND"
            assert course.demand_capacity_gap.value == 1
            assert sum(item.demand_count for item in course.demand_by_program) == 2
            assert course.bottleneck_reasons == sorted(course.bottleneck_reasons, key=lambda item: [
                "REQUIRED_CORE_COURSE", "VERIFIED_DOWNSTREAM_DEPENDENCIES",
                "PROJECTED_DEMAND_EXCEEDS_CAPACITY", "STUDENTS_AFFECTED",
            ].index(item))

            before = await repository.load_snapshot(local_facts.university_id, "LOCAL-TERM")
            scenarios = (
                SimulationRequest(university_id=local_facts.university_id, term_key="LOCAL-TERM",
                                  course_code=local_facts.course_code, kind="ADD_SECTION", seats=30),
                SimulationRequest(university_id=local_facts.university_id, term_key="LOCAL-TERM",
                                  course_code=local_facts.course_code, kind="CHANGE_SECTION_CAPACITY",
                                  section_id="LOCAL-SECTION", seats=45),
                SimulationRequest(university_id=local_facts.university_id, term_key="LOCAL-TERM",
                                  course_code=local_facts.course_code, kind="REMOVE_OFFERING"),
            )
            results = [await service.simulate(local_facts.admin_id, item) for item in scenarios]
            after = await repository.load_snapshot(local_facts.university_id, "LOCAL-TERM")
            assert all(item.simulation_only for item in results)
            assert [item.capacity_after for item in results] == [31, 45, 0]
            assert before == after

            serialized = json.dumps(admin.model_dump(mode="json"), sort_keys=True)
            for forbidden in (*local_facts.created_user_ids, "@local.test", "owner_user_id",
                              "profile_id", "raw_answer", "access_token", "password"):
                assert forbidden not in serialized
        finally:
            await client.aclose()

    asyncio.run(run())


def test_real_auth_endpoint_rls_and_role_matrix(local_facts: LocalFacts) -> None:
    with httpx.Client(timeout=30) as raw:
        anon = raw.get(f"{URL}/rest/v1/institutional_memberships", headers={"apikey": ANON_KEY or ""})
        assert anon.status_code in (401, 403)
        for token in (local_facts.student_a_token, local_facts.advisor_token, local_facts.admin_token):
            direct = raw.get(f"{URL}/rest/v1/institutional_memberships", headers=_user_headers(token))
            assert direct.status_code in (401, 403)
        other_profiles = raw.get(
            f"{URL}/rest/v1/student_academic_profiles", headers=_user_headers(local_facts.student_a_token),
            params={"select": "owner_user_id", "owner_user_id": f"eq.{local_facts.student_b_id}"},
        )
        other_profiles.raise_for_status()
        assert other_profiles.json() == []

    query = {"university_id": local_facts.university_id, "term_key": "LOCAL-TERM"}
    with TestClient(app) as api:
        assert api.get("/api/v1/institutional/analytics/dashboard", params=query).status_code == 401
        student = api.get(
            "/api/v1/institutional/analytics/dashboard", params={**query, "role": "INSTITUTIONAL_ANALYST"},
            headers={"Authorization": f"Bearer {local_facts.student_a_token}"},
        )
        assert student.status_code == 403
        admin = api.get(
            "/api/v1/institutional/analytics/dashboard", params=query,
            headers={"Authorization": f"Bearer {local_facts.admin_token}"},
        )
        assert admin.status_code == 200, admin.text[:500]
        assert admin.json()["overview"]["total_active_students"]["value"] == 2
        advisor = api.get(
            "/api/v1/institutional/analytics/dashboard", params=query,
            headers={"Authorization": f"Bearer {local_facts.advisor_token}"},
        )
        assert advisor.status_code == 200
        assert advisor.json()["overview"]["total_active_students"]["value"] == 1
        assert advisor.json()["advisor_caseload"]["scope"] == "ASSIGNED_STUDENTS"
        foreign = api.get(
            "/api/v1/institutional/analytics/dashboard", params=query,
            headers={"Authorization": f"Bearer {local_facts.foreign_admin_token}"},
        )
        assert foreign.status_code == 403


class _SequenceInterpreter:
    def __init__(self, selections: list[ToolSelection]) -> None:
        self.selections = selections

    async def select(self, request: CopilotRequest) -> ToolSelection:
        return self.selections.pop(0)


def test_real_repository_copilot_grounding_and_performance(local_facts: LocalFacts) -> None:
    async def run():
        client, _, service = _services(local_facts)
        try:
            dashboard = await service.dashboard(
                local_facts.admin_id, university_id=local_facts.university_id, term_key="LOCAL-TERM")
            top = dashboard.courses[0].course_code
            interpreter = _SequenceInterpreter([
                ToolSelection(status="SELECTED", tool=InstitutionalTool.COURSE_DEMAND),
                ToolSelection(status="SELECTED", tool=InstitutionalTool.BOTTLENECKS, course_code=local_facts.course_code),
                ToolSelection(status="SELECTED", tool=InstitutionalTool.PROGRAM),
                ToolSelection(status="SELECTED", tool=InstitutionalTool.SIMULATE_CAPACITY,
                              course_code=local_facts.course_code, seats=30),
            ])
            copilot = InstitutionalCopilotService(service, interpreter)
            questions = (
                "What courses currently have the highest deterministic demand?",
                "Why is this selected course considered a bottleneck?",
                "Which program has the largest deterministic blocked count?",
                "What if we add an extra section with 30 seats for the selected course?",
            )
            requests = [CopilotRequest(question=item, university_id=local_facts.university_id,
                                       term_key="LOCAL-TERM") for item in questions]
            answers = [await copilot.ask(local_facts.admin_id, item) for item in requests]
            assert all(item.status == "ANSWERED" for item in answers)
            assert answers[0].result[0]["course_code"] == top
            deterministic = next(item for item in dashboard.courses if item.course_code == local_facts.course_code)
            assert answers[1].result[0]["bottleneck_score"] == deterministic.bottleneck_score
            assert answers[2].result == [item.model_dump(mode="json") for item in dashboard.programs]
            assert answers[3].result["simulation_only"] is True
            assert answers[3].result["capacity_after"] == 31
            copilot_json = json.dumps([item.model_dump(mode="json") for item in answers])
            assert all(user_id not in copilot_json for user_id in local_facts.created_user_ids)

            timings: dict[str, list[float]] = {key: [] for key in ("overview", "program", "demand", "bottleneck")}
            for key in timings:
                for _ in range(12):
                    started = perf_counter()
                    result = await service.dashboard(
                        local_facts.admin_id, university_id=local_facts.university_id,
                        term_key="LOCAL-TERM",
                        plan_key=(next(item.plan_key for item in dashboard.programs
                                       if item.plan_id == local_facts.plan_id) if key == "program" else None),
                    )
                    if key == "demand":
                        assert result.courses
                    elif key == "bottleneck":
                        _ = [item for item in result.courses if item.bottleneck_level in {"HIGH", "CRITICAL"}]
                    elapsed = (perf_counter() - started) * 1000
                    timings[key].append(elapsed)
            summary = {key: {"p50_ms": round(median(values), 2),
                             "p95_ms": round(sorted(values)[math.ceil(0.95 * len(values)) - 1], 2)}
                       for key, values in timings.items()}
            print("REAL_INSTITUTIONAL_TIMINGS=" + json.dumps(summary, sort_keys=True))
            assert all(item["p95_ms"] < 5000 for item in summary.values())
        finally:
            await client.aclose()

    asyncio.run(run())
