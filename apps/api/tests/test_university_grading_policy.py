from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.rules.models import AttemptOutcome, StudentCourseAttempt
from app.student.models import (
    PerformanceProvenance,
    PerformanceVerificationState,
    StudentAcademicState,
    StudentCourseAttemptRecord,
)
from app.student_intelligence.adaptive import FAKE_UNIVERSITY_GRADING_POLICY_V1
from app.student_intelligence.profile_v2 import build_student_intelligence_profile_v2
from app.student_intelligence.diagnostic import DiagnosticDomain, DiagnosticDomainResult
from app.university_sync.errors import UniversityProtocolError
from app.university_sync.grading_policy import grading_policy_source_reference
from app.university_sync.models import (
    UniversityGradesResponse,
    UniversityGradesSnapshot,
    UniversityStudentProfile,
)
from app.university_sync.service import _validate_snapshot_consistency


INSTITUTION = "10000000-0000-0000-0000-000000000001"
OTHER_INSTITUTION = "20000000-0000-0000-0000-000000000001"
PLAN = "10000000-0000-0000-0000-000000000005"
VERSION = "FAKE_UNIVERSITY_GRADING_POLICY_V1"
NOW = datetime(2026, 10, 12, tzinfo=timezone.utc)


def _wire() -> dict[str, object]:
    return {
        "success": True,
        "cumulativeGpa": 93.6,
        "gpaScale": 100,
        "gradingPolicy": {
            "version": VERSION,
            "gpa": {"numericMin": 0, "numericMax": 100, "scale": 100},
            "courseGrade": {"numericMin": 0, "numericMax": 100},
        },
        "semesters": [{
            "term": "2025-1", "termLabel": "First Semester 2025",
            "registeredHours": 3, "passedHours": 3,
            "semesterGpa": 93.6, "cumulativeGpa": 93.6,
            "courses": [{
                "courseCode": "1501110", "name": "Programming", "credits": 3,
                "grade": 54, "letterGrade": "D", "status": "passed",
            }],
        }],
    }


def _reject(payload: dict[str, object]) -> None:
    with pytest.raises((ValidationError, UniversityProtocolError, ValueError)):
        UniversityGradesResponse.model_validate(payload)


def test_valid_v1_contract_accepts_exact_percentage_semantics_and_authoritative_outcome() -> None:
    result = UniversityGradesResponse.model_validate(_wire())
    assert Decimal(str(result.cumulative_gpa)) == Decimal("93.6")
    assert Decimal(str(result.gpa_scale)) == Decimal("100")
    assert result.semesters[0].courses[0].grade == 54
    assert result.semesters[0].courses[0].status == "passed"


def test_missing_grading_policy_fails_closed() -> None:
    payload = _wire(); payload.pop("gradingPolicy")
    _reject(payload)


def test_unsupported_policy_version_fails_closed() -> None:
    payload = _wire(); payload["gradingPolicy"]["version"] = "UNKNOWN_V2"  # type: ignore[index]
    _reject(payload)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("gpa", "numericMin", 1),
        ("gpa", "numericMax", 4),
        ("gpa", "scale", 4),
        ("courseGrade", "numericMin", 1),
        ("courseGrade", "numericMax", 4),
    ],
)
def test_v1_with_altered_semantics_fails_closed(section: str, field: str, value: int) -> None:
    payload = _wire(); payload["gradingPolicy"][section][field] = value  # type: ignore[index]
    _reject(payload)


def test_gpa_outside_bounds_fails_closed() -> None:
    payload = _wire(); payload["cumulativeGpa"] = 101
    _reject(payload)


def test_course_numeric_grade_outside_bounds_fails_closed() -> None:
    payload = _wire(); payload["semesters"][0]["courses"][0]["grade"] = -1  # type: ignore[index]
    _reject(payload)


@pytest.mark.parametrize(("path", "value"), [("gpa", float("nan")), ("grade", float("inf"))])
def test_non_finite_values_fail_closed(path: str, value: float) -> None:
    payload = _wire()
    if path == "gpa":
        payload["cumulativeGpa"] = value
    else:
        payload["semesters"][0]["courses"][0]["grade"] = value  # type: ignore[index]
    _reject(payload)


def test_malformed_policy_and_missing_gpa_scale_fail_closed() -> None:
    malformed = _wire(); malformed["gradingPolicy"] = {"version": VERSION}
    _reject(malformed)
    missing_scale = _wire(); missing_scale.pop("gpaScale")
    _reject(missing_scale)


def test_profile_and_grades_scale_mismatch_fails_closed() -> None:
    response = UniversityGradesResponse.model_validate(_wire())
    snapshot = UniversityGradesSnapshot(
        cumulative_gpa=Decimal("93.6"), gpa_scale=Decimal("100"),
        grading_policy=response.grading_policy, records=[])
    profile = UniversityStudentProfile(
        studentId="202310001", cumulativeGpa=Decimal("93.6"), gpaScale=4)
    with pytest.raises(UniversityProtocolError, match="scales conflict"):
        _validate_snapshot_consistency(profile, snapshot)


def _record(source_reference: str | None) -> StudentCourseAttemptRecord:
    return StudentCourseAttemptRecord(
        "attempt-1", "profile-1", "1501110", AttemptOutcome.PASSED, 1, "2025-1",
        date(2025, 1, 1), "D", "university_integration", NOW, NOW,
        raw_numeric_grade=Decimal("54"), raw_letter_grade="D",
        performance_provenance=PerformanceProvenance.OFFICIAL_VERIFIED,
        performance_verification_state=PerformanceVerificationState.VERIFIED,
        performance_source_reference=source_reference,
    )


@pytest.mark.parametrize("reference", [
    None,
    "forged",
    f"university:{OTHER_INSTITUTION}:grading-policy:{VERSION}",
    f"university:{INSTITUTION}:grading-policy:FAKE_UNIVERSITY_GRADING_POLICY_V2",
])
def test_untrusted_policy_references_do_not_activate_mastery(reference: str | None) -> None:
    assert FAKE_UNIVERSITY_GRADING_POLICY_V1.normalize(_record(reference)) is None


def test_old_record_becomes_mastery_only_after_policy_bound_resync_and_changes_fingerprint() -> None:
    state = StudentAcademicState(
        "profile-1", "owner-1", PLAN, Decimal("93.6"), Decimal("100"), Decimal("96"),
        (StudentCourseAttempt("1501110", AttemptOutcome.PASSED),), NOW, NOW)
    old = build_student_intelligence_profile_v2(
        state, INSTITUTION, (_record(None),), FAKE_UNIVERSITY_GRADING_POLICY_V1,
        generated_at=NOW)
    trusted_reference = grading_policy_source_reference(INSTITUTION, VERSION)
    trusted = build_student_intelligence_profile_v2(
        state, INSTITUTION, (_record(trusted_reference),), FAKE_UNIVERSITY_GRADING_POLICY_V1,
        generated_at=NOW)
    assert old.verified_grade_count == 0
    assert old.skills == ()
    assert trusted.verified_grade_count == 1
    assert any(skill.skill_id == "PROGRAMMING" and skill.score == 54 for skill in trusted.skills)
    assert old.source_snapshot_version != trusted.source_snapshot_version


def test_zero_history_profile_keeps_null_gpa_distinct_from_zero() -> None:
    payload = _wire(); payload["cumulativeGpa"] = 0
    response = UniversityGradesResponse.model_validate(payload)
    assert response.cumulative_gpa == 0
    profile = UniversityStudentProfile(studentId="future", gpaScale=100)
    assert profile.cumulative_gpa is None


def test_official_evidence_dominates_diagnostic_and_preferences_never_change_mastery() -> None:
    state = StudentAcademicState(
        "profile-1", "owner-1", PLAN, Decimal("93.6"), Decimal("100"), Decimal("96"),
        (StudentCourseAttempt("1501110", AttemptOutcome.PASSED),), NOW, NOW)
    record = _record(grading_policy_source_reference(INSTITUTION, VERSION))
    diagnostic = (DiagnosticDomainResult(
        DiagnosticDomain.PROGRAMMING_REASONING, 100, "HIGH", 5, ("RESPONSES_5", "HIGH_ACCURACY")),)
    base = build_student_intelligence_profile_v2(
        state, INSTITUTION, (record,), FAKE_UNIVERSITY_GRADING_POLICY_V1,
        diagnostic_results=diagnostic, diagnostic_version="DIAGNOSTIC_V1", generated_at=NOW)
    stated = build_student_intelligence_profile_v2(
        state, INSTITUTION, (record,), FAKE_UNIVERSITY_GRADING_POLICY_V1,
        diagnostic_results=diagnostic, diagnostic_version="DIAGNOSTIC_V1",
        preferences={"claims_expert": True}, generated_at=NOW)
    programming = next(row for row in base.skills if row.skill_id == "PROGRAMMING")
    assert programming.score == 68  # 70% authoritative 54 + 30% diagnostic 100
    assert programming.university_evidence_count == 1
    assert programming.diagnostic_evidence_count == 1
    assert "OFFICIAL_EVIDENCE_DOMINANT" in programming.reason_codes
    assert {row.skill_id: row.score for row in base.skills} == {
        row.skill_id: row.score for row in stated.skills}
