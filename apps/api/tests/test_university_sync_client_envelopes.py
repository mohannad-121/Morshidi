from __future__ import annotations

from collections.abc import Awaitable, Callable

import httpx
import pytest

from app.university_sync.client import UniversityContractClient
from app.university_sync.errors import UniversityProtocolError


ClientCall = Callable[[UniversityContractClient], Awaitable[object]]


async def _call_with_response(payload: object, call: ClientCall) -> object:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        return await call(UniversityContractClient(http_client))


@pytest.mark.anyio
async def test_real_login_response_extracts_access_token_and_verified_student_id() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": True,
                "accessToken": "opaque-test-token",
                "tokenType": "Bearer",
                "expiresIn": 900,
                "student": {
                    "studentId": "0020310001",
                    "email": "student@example.edu",
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await UniversityContractClient(
            http_client,
            client_secret="test-client-secret",
        ).authenticate_student("0020310001", "test-password")

    assert result.token == "opaque-test-token"
    assert result.student_id == "0020310001"


def _grade_course(
    *,
    course_code: str = "0200104",
    name: str = "Calculus 1",
    credits: int | float = 3,
    grade: int | float = 95,
    letter_grade: str = "A",
    status: str = "passed",
) -> dict[str, object]:
    return {
        "courseCode": course_code,
        "name": name,
        "credits": credits,
        "grade": grade,
        "letterGrade": letter_grade,
        "status": status,
    }


def _grade_semester(
    *,
    term: str = "2023-1",
    courses: object | None = None,
) -> dict[str, object]:
    return {
        "term": term,
        "termLabel": "First Semester",
        "registeredHours": 15,
        "passedHours": 15,
        "semesterGpa": 3.5,
        "cumulativeGpa": 3.4,
        "courses": [_grade_course()] if courses is None else courses,
    }


def _grades_response(*, semesters: object | None = None) -> dict[str, object]:
    return {
        "success": True,
        "cumulativeGpa": 3.4,
        "semesters": [_grade_semester()] if semesters is None else semesters,
    }


def _student_response() -> dict[str, object]:
    return {
        "success": True,
        "student": {
            "studentId": "0020310001",
            "name": "Test Student",
            "email": "student@example.edu",
            "faculty": "Information Technology",
            "major": "Artificial Intelligence",
            "degree": "Bachelor",
            "studyType": "Regular",
            "admissionYear": 2023,
            "academicAdvisor": "Test Advisor",
            "academicStatus": "active",
            "gpa": 3.4,
            "earnedCredits": 45,
        },
    }


def _grouped_course(
    course_code: str,
    status: str,
    *,
    name: str = "Course",
) -> dict[str, object]:
    return {
        "courseCode": course_code,
        "name": name,
        "credits": 3,
        "status": status,
    }


def _courses_response(
    *,
    completed: object | None = None,
    current: object | None = None,
    remaining: object | None = None,
) -> dict[str, object]:
    return {
        "success": True,
        "courses": {
            "completed": [] if completed is None else completed,
            "current": [] if current is None else current,
            "remaining": [] if remaining is None else remaining,
        },
    }


def _enrollment() -> dict[str, object]:
    return {
        "courseCode": "0300103",
        "courseName": "Data Structures",
        "sectionId": "SEC-01",
        "sectionNumber": 1,
        "credits": 3,
        "days": "Sun/Tue",
        "daysArray": ["Sun", "Tue"],
        "startTime": "10:00",
        "endTime": "11:30",
        "room": "LAB-1",
        "instructor": "Test Instructor",
    }


def _enrollments_response(*, enrollments: object | None = None) -> dict[str, object]:
    return {
        "success": True,
        "term": "2024-1",
        "termLabel": "First Semester 2024",
        "enrollments": [_enrollment()] if enrollments is None else enrollments,
    }


def _plan_course() -> dict[str, object]:
    return {
        "courseCode": "0200104",
        "name": "Calculus 1",
        "credits": 3,
        "group": "University Requirements",
        "type": "required",
        "prerequisites": [],
        "status": "completed",
    }


def _plan_response(*, courses: object | None = None) -> dict[str, object]:
    return {
        "success": True,
        "plan": {
            "planId": "12",
            "major": "Artificial Intelligence",
            "totalRequiredCredits": 132,
            "earnedCredits": 45,
            "remainingCredits": 87,
            "courses": [_plan_course()] if courses is None else courses,
        },
    }


@pytest.mark.anyio
async def test_student_me_unwraps_student_envelope() -> None:
    result = await _call_with_response(
        _student_response(),
        lambda client: client.get_student_me("token"),
    )

    assert result.student_id == "0020310001"
    assert result.name == "Test Student"
    assert result.cumulative_gpa == 3.4
    assert result.earned_credits == 45


@pytest.mark.anyio
async def test_student_me_rejects_malformed_real_student() -> None:
    response = _student_response()
    response["student"].pop("gpa")
    with pytest.raises(UniversityProtocolError, match="Malformed university student profile"):
        await _call_with_response(response, lambda client: client.get_student_me("token"))


@pytest.mark.anyio
async def test_courses_unwraps_courses_envelope() -> None:
    result = await _call_with_response(
        _courses_response(
            completed=[_grouped_course("0200104", "completed", name="Calculus 1")],
            current=[_grouped_course("0300103", "enrolled", name="Data Structures")],
            remaining=[_grouped_course("1501110", "remaining", name="Computer Science 1")],
        ),
        lambda client: client.get_student_courses("token"),
    )

    assert [(course.course_code, course.status) for course in result] == [
        ("0200104", "completed"),
        ("0300103", "enrolled"),
        ("1501110", "remaining"),
    ]
    assert result[0].title == "Calculus 1"
    assert result[0].credit_hours == 3


@pytest.mark.anyio
async def test_courses_all_groups_empty() -> None:
    result = await _call_with_response(
        _courses_response(),
        lambda client: client.get_student_courses("token"),
    )

    assert result == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("group", "status"),
    [("completed", "completed"), ("current", "enrolled"), ("remaining", "remaining")],
)
async def test_courses_one_group_populated(group: str, status: str) -> None:
    response = _courses_response(**{group: [_grouped_course("0200104", status)]})
    result = await _call_with_response(response, lambda client: client.get_student_courses("token"))

    assert [(course.course_code, course.status) for course in result] == [("0200104", status)]


@pytest.mark.anyio
async def test_courses_reject_invalid_group_type() -> None:
    with pytest.raises(UniversityProtocolError, match="Malformed university courses"):
        await _call_with_response(
            _courses_response(current={}),
            lambda client: client.get_student_courses("token"),
        )


@pytest.mark.anyio
async def test_courses_reject_malformed_course() -> None:
    course = _grouped_course("0200104", "completed")
    course.pop("credits")
    with pytest.raises(UniversityProtocolError, match="Malformed university courses"):
        await _call_with_response(
            _courses_response(completed=[course]),
            lambda client: client.get_student_courses("token"),
        )


@pytest.mark.anyio
async def test_courses_reject_invalid_status() -> None:
    with pytest.raises(UniversityProtocolError, match="Malformed university courses"):
        await _call_with_response(
            _courses_response(completed=[_grouped_course("0200104", "passed")]),
            lambda client: client.get_student_courses("token"),
        )


@pytest.mark.anyio
async def test_courses_reject_status_that_contradicts_group() -> None:
    with pytest.raises(UniversityProtocolError, match="contradicts group"):
        await _call_with_response(
            _courses_response(current=[_grouped_course("0200104", "completed")]),
            lambda client: client.get_student_courses("token"),
        )


@pytest.mark.anyio
async def test_courses_reject_duplicate_course_codes() -> None:
    with pytest.raises(UniversityProtocolError, match="duplicate courseCode"):
        await _call_with_response(
            _courses_response(
                completed=[_grouped_course("0200104", "completed")],
                remaining=[_grouped_course("0200104", "remaining")],
            ),
            lambda client: client.get_student_courses("token"),
        )


@pytest.mark.anyio
async def test_grades_unwraps_real_semesters_envelope() -> None:
    result = await _call_with_response(
        {"success": True, "cumulativeGpa": 0, "semesters": []},
        lambda client: client.get_student_grades("token"),
    )

    assert result == []


@pytest.mark.anyio
async def test_real_nested_grade_maps_only_existing_record_fields() -> None:
    result = await _call_with_response(
        _grades_response(),
        lambda client: client.get_student_grades("token"),
    )

    assert len(result) == 1
    grade = result[0]
    assert grade.course_code == "0200104"
    assert grade.course_name == "Calculus 1"
    assert grade.term == "2023-1"
    assert grade.academic_year is None
    assert grade.letter_grade == "A"
    assert grade.numeric_grade == 95
    assert grade.grade_points is None
    assert grade.credit_hours == 3
    assert grade.status == "PASSED"


@pytest.mark.anyio
async def test_real_nested_grades_preserve_semester_term_association() -> None:
    semesters = [
        _grade_semester(term="2023-1", courses=[_grade_course(course_code="0200104")]),
        _grade_semester(term="2023-2", courses=[_grade_course(course_code="1501110")]),
    ]
    result = await _call_with_response(
        _grades_response(semesters=semesters),
        lambda client: client.get_student_grades("token"),
    )

    assert [(grade.course_code, grade.term) for grade in result] == [
        ("0200104", "2023-1"),
        ("1501110", "2023-2"),
    ]


@pytest.mark.anyio
async def test_real_nested_grades_flatten_multiple_courses_once_each() -> None:
    courses = [
        _grade_course(course_code="0200104"),
        _grade_course(course_code="1501110", name="Computer Science 1", grade=88, letter_grade="B+"),
    ]
    result = await _call_with_response(
        _grades_response(semesters=[_grade_semester(courses=courses)]),
        lambda client: client.get_student_grades("token"),
    )

    assert [grade.course_code for grade in result] == ["0200104", "1501110"]
    assert len(result) == len(courses)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("source_status", "expected_outcome"),
    [("passed", "PASSED"), ("failed", "FAILED"), ("withdrawn", "WITHDRAWN")],
)
async def test_real_nested_grade_status_mapping(source_status: str, expected_outcome: str) -> None:
    response = _grades_response(
        semesters=[_grade_semester(courses=[_grade_course(status=source_status)])]
    )
    result = await _call_with_response(response, lambda client: client.get_student_grades("token"))

    assert [grade.status for grade in result] == [expected_outcome]


@pytest.mark.anyio
async def test_real_semester_with_no_courses_maps_to_no_records() -> None:
    result = await _call_with_response(
        _grades_response(semesters=[_grade_semester(courses=[])]),
        lambda client: client.get_student_grades("token"),
    )

    assert result == []


@pytest.mark.anyio
async def test_real_grades_reject_semesters_that_are_not_a_list() -> None:
    with pytest.raises(UniversityProtocolError, match="Malformed university grades"):
        await _call_with_response(
            _grades_response(semesters={}),
            lambda client: client.get_student_grades("token"),
        )


@pytest.mark.anyio
async def test_real_grades_reject_missing_semester_field() -> None:
    semester = _grade_semester()
    semester.pop("termLabel")
    with pytest.raises(UniversityProtocolError, match="Malformed university grades"):
        await _call_with_response(
            _grades_response(semesters=[semester]),
            lambda client: client.get_student_grades("token"),
        )


@pytest.mark.anyio
async def test_real_grades_reject_courses_that_are_not_a_list() -> None:
    with pytest.raises(UniversityProtocolError, match="Malformed university grades"):
        await _call_with_response(
            _grades_response(semesters=[_grade_semester(courses={})]),
            lambda client: client.get_student_grades("token"),
        )


@pytest.mark.anyio
async def test_real_grades_reject_missing_course_field() -> None:
    course = _grade_course()
    course.pop("courseCode")
    with pytest.raises(UniversityProtocolError, match="Malformed university grades"):
        await _call_with_response(
            _grades_response(semesters=[_grade_semester(courses=[course])]),
            lambda client: client.get_student_grades("token"),
        )


@pytest.mark.anyio
async def test_real_grades_reject_unknown_status() -> None:
    with pytest.raises(UniversityProtocolError, match="Malformed university grades"):
        await _call_with_response(
            _grades_response(semesters=[_grade_semester(courses=[_grade_course(status="incomplete")])]),
            lambda client: client.get_student_grades("token"),
        )


@pytest.mark.anyio
@pytest.mark.parametrize("invalid_grade", ["95", True, None])
async def test_real_grades_reject_non_numeric_grade(invalid_grade: object) -> None:
    with pytest.raises(UniversityProtocolError, match="Malformed university grades"):
        await _call_with_response(
            _grades_response(semesters=[_grade_semester(courses=[_grade_course(grade=invalid_grade)])]),
            lambda client: client.get_student_grades("token"),
        )


@pytest.mark.anyio
async def test_real_grades_reject_missing_top_level_gpa() -> None:
    response = _grades_response()
    response.pop("cumulativeGpa")
    with pytest.raises(UniversityProtocolError, match="Malformed university grades"):
        await _call_with_response(response, lambda client: client.get_student_grades("token"))


@pytest.mark.anyio
async def test_enrollments_unwraps_enrollments_envelope() -> None:
    result = await _call_with_response(
        _enrollments_response(),
        lambda client: client.get_student_enrollments("token"),
    )

    assert [enrollment.course_code for enrollment in result] == ["0300103"]
    assert result[0].course_name == "Data Structures"
    assert result[0].section_id == "SEC-01"
    assert result[0].term == "2024-1"
    assert result[0].status == "ENROLLED"
    assert result[0].credit_hours == 3


@pytest.mark.anyio
async def test_enrollments_empty_list_preserves_valid_contract() -> None:
    result = await _call_with_response(
        _enrollments_response(enrollments=[]),
        lambda client: client.get_student_enrollments("token"),
    )

    assert result == []


@pytest.mark.anyio
async def test_enrollments_reject_malformed_record() -> None:
    enrollment = _enrollment()
    enrollment.pop("room")
    with pytest.raises(UniversityProtocolError, match="Malformed university enrollments"):
        await _call_with_response(
            _enrollments_response(enrollments=[enrollment]),
            lambda client: client.get_student_enrollments("token"),
        )


@pytest.mark.anyio
async def test_academic_plan_unwraps_plan_envelope() -> None:
    result = await _call_with_response(
        _plan_response(),
        lambda client: client.get_student_academic_plan("token"),
    )

    assert result.plan_id == "12"
    assert result.major == "Artificial Intelligence"
    assert result.total_credit_hours == 132
    assert result.courses[0]["courseCode"] == "0200104"


@pytest.mark.anyio
async def test_academic_plan_rejects_malformed_plan() -> None:
    response = _plan_response()
    response["plan"].pop("remainingCredits")
    with pytest.raises(UniversityProtocolError, match="Malformed university academic plan"):
        await _call_with_response(response, lambda client: client.get_student_academic_plan("token"))


@pytest.mark.anyio
async def test_academic_plan_rejects_malformed_course() -> None:
    course = _plan_course()
    course.pop("type")
    with pytest.raises(UniversityProtocolError, match="Malformed university academic plan"):
        await _call_with_response(
            _plan_response(courses=[course]),
            lambda client: client.get_student_academic_plan("token"),
        )


@pytest.mark.anyio
async def test_missing_payload_key_is_rejected() -> None:
    with pytest.raises(UniversityProtocolError, match="missing payload key"):
        await _call_with_response(
            {"success": True, "items": []},
            lambda client: client.get_student_courses("token"),
        )


@pytest.mark.anyio
async def test_wrong_payload_type_is_rejected() -> None:
    with pytest.raises(UniversityProtocolError, match="Malformed university grades"):
        await _call_with_response(
            {"success": True, "grades": {"courseCode": "0200104"}},
            lambda client: client.get_student_grades("token"),
        )


@pytest.mark.anyio
async def test_success_false_is_rejected() -> None:
    with pytest.raises(UniversityProtocolError, match="reported failure"):
        await _call_with_response(
            {"success": False, "enrollments": []},
            lambda client: client.get_student_enrollments("token"),
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("payload", "call"),
    [
        ({"success": True, "data": {"studentId": "202310001"}}, lambda client: client.get_student_me("token")),
        ({"success": True, "profile": {"studentId": "202310001"}}, lambda client: client.get_student_me("token")),
        ({"success": True, "data": [{"courseCode": "0200104"}]}, lambda client: client.get_student_courses("token")),
        ({"success": True, "data": [{"courseCode": "0200104"}]}, lambda client: client.get_student_grades("token")),
        ({"success": True, "data": [{"courseCode": "0200104"}]}, lambda client: client.get_student_enrollments("token")),
        ({"success": True, "academicPlan": {"planId": "12"}}, lambda client: client.get_student_academic_plan("token")),
        ({"success": True, "data": {"planId": "12"}}, lambda client: client.get_student_academic_plan("token")),
    ],
)
async def test_fallback_payload_keys_are_supported(payload: object, call: ClientCall) -> None:
    await _call_with_response(payload, call)


@pytest.mark.anyio
async def test_non_object_envelope_is_rejected() -> None:
    with pytest.raises(UniversityProtocolError, match="expected a JSON object"):
        await _call_with_response(
            [{"courseCode": "0200104"}],
            lambda client: client.get_student_courses("token"),
        )


@pytest.mark.anyio
async def test_non_boolean_success_is_rejected() -> None:
    with pytest.raises(UniversityProtocolError, match="success must be a boolean"):
        await _call_with_response(
            {"success": "true", "courses": []},
            lambda client: client.get_student_courses("token"),
        )
