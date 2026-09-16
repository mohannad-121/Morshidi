"""Unit and repository-to-engine tests for the read-only catalog adapter."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.catalog.errors import (
    CatalogIntegrityError,
    CatalogTransportError,
    StudyPlanNotFound,
    TargetCourseNotFound,
    TargetCourseNotInStudyPlan,
)
from app.catalog.supabase_repository import SupabaseAcademicCatalogRepository
from app.rules.evaluator import evaluate_can_take
from app.rules.models import (
    AttemptOutcome,
    CanTakeRequest,
    Decision,
    DecisionReason,
    PrerequisiteLogicStatus,
    StudentCourseAttempt,
)

PLAN_ID = "11111111-1111-1111-1111-111111111111"
UNIVERSITY_ID = "22222222-2222-2222-2222-222222222222"
TARGET_ID = "33333333-3333-3333-3333-333333333333"
PLAN_COURSE_ID = "44444444-4444-4444-4444-444444444444"
GROUP_ID = "55555555-5555-5555-5555-555555555555"
SERVER_KEY = "test-server-key-not-a-real-secret"


class FixtureData:
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.plan_rows: list[dict[str, Any]] = [
            {"id": PLAN_ID, "majors": {"faculties": {"university_id": UNIVERSITY_ID}}}
        ]
        self.course_rows: list[dict[str, Any]] = [
            {
                "id": TARGET_ID,
                "course_code": "1501112",
                "name_ar": "برمجة الحاسوب (2)",
                "catalog_status": "known",
                "university_id": UNIVERSITY_ID,
            }
        ]
        self.plan_course_rows: list[dict[str, Any]] = [
            {
                "id": PLAN_COURSE_ID,
                "prerequisite_logic_status": "verified",
                "raw_prerequisite_text": "1501110",
            }
        ]
        self.group_rows: list[dict[str, Any]] = [
            {"id": GROUP_ID, "dependency_type": "prerequisite", "group_number": 1}
        ]
        self.option_rows: list[dict[str, Any]] = [
            {
                "dependency_group_id": GROUP_ID,
                "courses": {
                    "course_code": "1501110",
                    "catalog_status": "known",
                    "university_id": UNIVERSITY_ID,
                },
            }
        ]
        self.status_code: int | None = None
        self.malformed_json = False
        self.exception_factory: Callable[[httpx.Request], Exception] | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        assert request.method == "GET"
        assert request.headers["apikey"] == SERVER_KEY
        if self.exception_factory is not None:
            raise self.exception_factory(request)
        if self.status_code is not None:
            return httpx.Response(self.status_code, json={"message": "safe fixture error"})
        if self.malformed_json:
            return httpx.Response(200, content=b"{")
        resource = request.url.path.rsplit("/", 1)[-1]
        rows = {
            "study_plans": self.plan_rows,
            "courses": self.course_rows,
            "study_plan_courses": self.plan_course_rows,
            "course_dependency_groups": self.group_rows,
            "course_dependency_options": self.option_rows,
        }[resource]
        return httpx.Response(200, json=rows)


def load(data: FixtureData, target_code: str = "1501112"):
    async def operation():
        async with httpx.AsyncClient(transport=httpx.MockTransport(data.handler)) as client:
            repository = SupabaseAcademicCatalogRepository(
                "https://catalog.example",
                SERVER_KEY,
                client,
            )
            return await repository.load_target_rules(PLAN_ID, target_code)

    return asyncio.run(operation())


def test_not_applicable_target_maps_without_dependencies() -> None:
    data = FixtureData()
    data.plan_course_rows[0]["prerequisite_logic_status"] = "not_applicable"
    data.plan_course_rows[0]["raw_prerequisite_text"] = None
    data.group_rows = []
    catalog = load(data)
    target = catalog.plan_courses[0]
    assert target.prerequisite_logic_status is PrerequisiteLogicStatus.NOT_APPLICABLE
    assert target.dependency_groups == ()


def test_verified_target_maps_single_prerequisite() -> None:
    catalog = load(FixtureData())
    assert catalog.plan_courses[0].dependency_groups[0].option_course_codes == ("1501110",)


def test_verified_or_group_maps_all_options_in_code_order() -> None:
    data = FixtureData()
    data.option_rows.extend(
        [
            {
                "dependency_group_id": GROUP_ID,
                "courses": {
                    "course_code": "0100001",
                    "catalog_status": "referenced_only",
                    "university_id": UNIVERSITY_ID,
                },
            },
            {
                "dependency_group_id": GROUP_ID,
                "courses": {
                    "course_code": "0900001",
                    "catalog_status": "known",
                    "university_id": UNIVERSITY_ID,
                },
            },
        ]
    )
    catalog = load(data)
    assert catalog.plan_courses[0].dependency_groups[0].option_course_codes == (
        "0100001",
        "0900001",
        "1501110",
    )


def test_multiple_and_groups_sort_by_group_number() -> None:
    data = FixtureData()
    data.group_rows = [
        {"id": "group-2", "dependency_type": "prerequisite", "group_number": 2},
        {"id": GROUP_ID, "dependency_type": "prerequisite", "group_number": 1},
    ]
    data.option_rows.append(
        {
            "dependency_group_id": "group-2",
            "courses": {
                "course_code": "1501221",
                "catalog_status": "known",
                "university_id": UNIVERSITY_ID,
            },
        }
    )
    catalog = load(data)
    assert [group.group_number for group in catalog.plan_courses[0].dependency_groups] == [1, 2]


@pytest.mark.parametrize("status", ["unresolved", "source_conflict"])
def test_non_executable_status_preserves_raw_text_without_groups(status: str) -> None:
    data = FixtureData()
    data.plan_course_rows[0]["prerequisite_logic_status"] = status
    data.plan_course_rows[0]["raw_prerequisite_text"] = "unparsed, official evidence"
    data.group_rows = []
    catalog = load(data)
    target = catalog.plan_courses[0]
    assert target.prerequisite_logic_status.value == status
    assert target.raw_prerequisite_text == "unparsed, official evidence"
    assert target.dependency_groups == ()


def test_referenced_only_dependency_option_is_accepted() -> None:
    data = FixtureData()
    data.option_rows[0]["courses"]["catalog_status"] = "referenced_only"
    catalog = load(data)
    assert {course.catalog_status.value for course in catalog.courses} == {"known", "referenced_only"}


def test_referenced_only_target_not_in_plan_raises_specific_error() -> None:
    data = FixtureData()
    data.course_rows[0]["catalog_status"] = "referenced_only"
    data.course_rows[0]["course_code"] = "0300103"
    data.plan_course_rows = []
    with pytest.raises(TargetCourseNotInStudyPlan):
        load(data, "0300103")


def test_unknown_target_raises_specific_error() -> None:
    data = FixtureData()
    data.course_rows = []
    with pytest.raises(TargetCourseNotFound):
        load(data, "9999999")


def test_unknown_study_plan_raises_specific_error() -> None:
    data = FixtureData()
    data.plan_rows = []
    with pytest.raises(StudyPlanNotFound):
        load(data)
    assert [request.method for request in data.calls] == ["GET"]


def test_invalid_persisted_status_is_integrity_error() -> None:
    data = FixtureData()
    data.plan_course_rows[0]["prerequisite_logic_status"] = "invented"
    with pytest.raises(CatalogIntegrityError, match="prerequisite_logic_status"):
        load(data)


def test_verified_target_without_groups_is_integrity_error() -> None:
    data = FixtureData()
    data.group_rows = []
    with pytest.raises(CatalogIntegrityError, match="no dependency group"):
        load(data)


def test_unsupported_dependency_type_is_integrity_error() -> None:
    data = FixtureData()
    data.group_rows[0]["dependency_type"] = "future_type"
    with pytest.raises(CatalogIntegrityError, match="dependency_type"):
        load(data)


def test_duplicate_group_numbers_are_integrity_error() -> None:
    data = FixtureData()
    data.group_rows.append(
        {"id": "another-group", "dependency_type": "prerequisite", "group_number": 1}
    )
    with pytest.raises(CatalogIntegrityError, match="Duplicate dependency group_number"):
        load(data)


def test_duplicate_dependency_option_is_integrity_error() -> None:
    data = FixtureData()
    data.option_rows.append(data.option_rows[0].copy())
    with pytest.raises(CatalogIntegrityError, match="duplicate option"):
        load(data)


def test_missing_dependency_course_is_integrity_error() -> None:
    data = FixtureData()
    data.option_rows[0]["courses"] = None
    with pytest.raises(CatalogIntegrityError, match="missing its referenced course"):
        load(data)


def test_cross_university_dependency_is_integrity_error() -> None:
    data = FixtureData()
    data.option_rows[0]["courses"]["university_id"] = "other-university"
    with pytest.raises(CatalogIntegrityError, match="another university"):
        load(data)


def test_non_2xx_response_becomes_safe_transport_error() -> None:
    data = FixtureData()
    data.status_code = 503
    with pytest.raises(CatalogTransportError, match="study_plans.*HTTP 503"):
        load(data)


def test_timeout_becomes_transport_error() -> None:
    data = FixtureData()
    data.exception_factory = lambda request: httpx.ReadTimeout("timeout", request=request)
    with pytest.raises(CatalogTransportError, match="Catalog GET failed"):
        load(data)


def test_malformed_json_becomes_safe_transport_error() -> None:
    data = FixtureData()
    data.malformed_json = True
    with pytest.raises(CatalogTransportError, match="decode response"):
        load(data)


def test_server_key_never_appears_in_raised_errors() -> None:
    data = FixtureData()
    data.status_code = 401
    with pytest.raises(CatalogTransportError) as raised:
        load(data)
    assert SERVER_KEY not in str(raised.value)


def test_repository_performs_only_get_requests() -> None:
    data = FixtureData()
    load(data)
    assert {request.method for request in data.calls} == {"GET"}


def test_repository_never_parses_raw_prerequisite_text() -> None:
    source = inspect.getsource(SupabaseAcademicCatalogRepository)
    assert ".split(" not in source
    assert "re." not in source


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [(AttemptOutcome.PASSED, Decision.ELIGIBLE), (AttemptOutcome.FAILED, Decision.NOT_ELIGIBLE)],
)
def test_repository_catalog_passes_directly_to_engine(
    outcome: AttemptOutcome,
    expected: Decision,
) -> None:
    catalog = load(FixtureData())
    result = evaluate_can_take(
        catalog,
        CanTakeRequest(
            study_plan_id=PLAN_ID,
            target_course_code="1501112",
            student_attempts=(StudentCourseAttempt("1501110", outcome),),
        ),
    )
    assert result.decision is expected


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("source_conflict", DecisionReason.PREREQUISITE_SOURCE_CONFLICT),
        ("unresolved", DecisionReason.PREREQUISITE_LOGIC_UNRESOLVED),
    ],
)
def test_repository_non_executable_catalog_passes_directly_to_engine(
    status: str,
    reason: DecisionReason,
) -> None:
    data = FixtureData()
    data.course_rows[0]["course_code"] = "1505320"
    data.plan_course_rows[0]["prerequisite_logic_status"] = status
    data.group_rows = []
    catalog = load(data, "1505320")
    result = evaluate_can_take(
        catalog,
        CanTakeRequest(PLAN_ID, "1505320", ()),
    )
    assert result.decision is Decision.REVIEW_REQUIRED
    assert reason in result.reasons
