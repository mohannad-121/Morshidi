from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.rules.models import AttemptOutcome, StudentCourseAttempt
from app.services.student import StudentService
from app.student.models import (PerformanceProvenance, PerformanceVerificationState,
                                StudentAcademicState, StudentCourseAttemptRecord)
from app.student_intelligence.adaptive import (FAKE_UNIVERSITY_GRADE_POLICY_V1,
                                               GradePolicyRegistry)
from app.student_intelligence.diagnostic import (QUESTION_BANK, QUESTIONS_BY_ID, AnswerEvidence,
                                                 DiagnosticDomain, public_question, score_domain,
                                                 select_next_question)
from app.student_intelligence.profile_v2 import build_student_intelligence_profile_v2
from app.student_intelligence.taxonomy import (PLAN12_COURSE_SKILLS,
                                               SUPPORTED_PLAN12_COURSE_CODES,
                                               CourseSkillDefinition, SkillId, SkillWeight,
                                               validate_course_skill_definitions)
from app.university_sync.grading_policy import grading_policy_source_reference

PLAN = "10000000-0000-0000-0000-000000000005"
INSTITUTION = "10000000-0000-0000-0000-000000000001"
NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)


def _record(identifier: str, code: str, outcome: AttemptOutcome, grade: str,
            attempted: date, sequence: int) -> StudentCourseAttemptRecord:
    return StudentCourseAttemptRecord(
        identifier, "profile-1", code, outcome, sequence, None, attempted, None,
        "FAKE_UNIVERSITY_SYNC", NOW, NOW, raw_numeric_grade=Decimal(grade),
        performance_provenance=PerformanceProvenance.OFFICIAL_VERIFIED,
        performance_verification_state=PerformanceVerificationState.VERIFIED,
        performance_source_reference=grading_policy_source_reference(
            INSTITUTION, "FAKE_UNIVERSITY_GRADING_POLICY_V1"),
    )


def _state() -> StudentAcademicState:
    return StudentAcademicState(
        "profile-1", "owner-1", PLAN, Decimal("93.6"), Decimal("100"), Decimal("96"),
        (StudentCourseAttempt("1501110", AttemptOutcome.PASSED),
         StudentCourseAttempt("1505311", AttemptOutcome.FAILED),
         StudentCourseAttempt("1505415", AttemptOutcome.IN_PROGRESS)),
        NOW, NOW,
    )


def test_plan12_mapping_covers_the_live_seed_deliberately() -> None:
    seed = (Path(__file__).parents[3] / "supabase" / "migrations" /
            "20260916230222_seed_ai_plan12_courses.sql").read_text(encoding="utf-8")
    codes = set(re.findall(r"\('([0-9]{7})',", seed))
    assert len(codes) == 68
    assert SUPPORTED_PLAN12_COURSE_CODES == codes
    assert set(PLAN12_COURSE_SKILLS) == codes
    assert all(definition.skills for definition in PLAN12_COURSE_SKILLS.values())
    assert all(isinstance(weighted.skill_id, SkillId) and 0 < weighted.weight <= 1
               for definition in PLAN12_COURSE_SKILLS.values()
               for weighted in definition.skills)
    assert all(len({weighted.skill_id for weighted in definition.skills})
               == len(definition.skills) for definition in PLAN12_COURSE_SKILLS.values())
    assert all(definition.provenance == "MODELED_MORSHIDI_CURRICULUM_CLASSIFICATION"
               for definition in PLAN12_COURSE_SKILLS.values())


def test_taxonomy_validation_rejects_invalid_skill_weight() -> None:
    invalid = CourseSkillDefinition(
        "ONLY001", (SkillWeight(SkillId.PROGRAMMING, 0),))
    with pytest.raises(ValueError, match="Invalid taxonomy skill weight"):
        validate_course_skill_definitions((invalid,), expected_course_codes=frozenset({"ONLY001"}))


def test_taxonomy_validation_rejects_duplicate_course_and_skill_mappings() -> None:
    first = CourseSkillDefinition(
        "ONLY001", (SkillWeight(SkillId.PROGRAMMING, 1),))
    duplicate_course = replace(first, skills=(SkillWeight(SkillId.PYTHON, 1),))
    with pytest.raises(ValueError, match="Duplicate taxonomy course code"):
        validate_course_skill_definitions(
            (first, duplicate_course), expected_course_codes=frozenset({"ONLY001"}))

    duplicate_skill = replace(first, skills=(
        SkillWeight(SkillId.PROGRAMMING, 1), SkillWeight(SkillId.PROGRAMMING, .5)))
    with pytest.raises(ValueError, match="Duplicate taxonomy skill"):
        validate_course_skill_definitions(
            (duplicate_skill,), expected_course_codes=frozenset({"ONLY001"}))


def test_taxonomy_has_no_runtime_course_name_inference() -> None:
    source = (Path(__file__).parents[1] / "app" / "student_intelligence" /
              "taxonomy.py").read_text(encoding="utf-8")
    assert "name_ar" not in source and "name_en" not in source
    assert "casefold(" not in source and "startswith(" not in source


def test_question_bank_is_balanced_and_never_projects_answer_keys() -> None:
    assert len(QUESTION_BANK) == 25
    assert {domain: sum(q.domain is domain for q in QUESTION_BANK) for domain in DiagnosticDomain} == {
        domain: 5 for domain in DiagnosticDomain}
    for question in QUESTION_BANK:
        payload = public_question(question)
        assert "correct_option" not in payload
        assert "difficulty" not in payload
        assert all("correct" not in option for option in payload["options"])


def test_diagnostic_selection_is_reproducible_and_typically_twelve_items() -> None:
    responses: tuple[AnswerEvidence, ...] = ()
    issued: list[str] = []
    while (question := select_next_question(responses)) is not None:
        issued.append(question.question_id)
        responses += (AnswerEvidence(question.question_id, question.correct_option, True),)
    assert len(issued) == 12
    assert issued == ["P01", "L01", "M01", "S01", "T01", "P02", "L02", "M02", "S02", "T02", "P03", "L03"]
    assert len(set(issued)) == len(issued)
    assert all(score_domain(domain, responses).confidence != "HIGH" or
               score_domain(domain, responses).response_count >= 4 for domain in DiagnosticDomain)


def test_latest_verified_attempt_drives_mastery_but_failure_and_repeat_remain_visible() -> None:
    records = (
        _record("a1", "1501110", AttemptOutcome.FAILED, "40", date(2025, 1, 1), 1),
        _record("a2", "1501110", AttemptOutcome.PASSED, "90", date(2025, 6, 1), 2),
        _record("a3", "1505311", AttemptOutcome.FAILED, "50", date(2026, 1, 1), 1),
    )
    profile = build_student_intelligence_profile_v2(
        _state(), INSTITUTION, tuple(reversed(records)), FAKE_UNIVERSITY_GRADE_POLICY_V1,
        preferences={"self_reported_math_strength": True}, generated_at=NOW)
    skills = {row.skill_id: row for row in profile.skills}
    assert skills["PROGRAMMING"].score == 90
    assert skills["MACHINE_LEARNING"].score == 50
    assert profile.failed_course_count == 2
    assert profile.repeated_course_count == 1
    assert profile.verified_grade_count == 3
    assert profile.preferences == {"self_reported_math_strength": True}
    assert "QUANTITATIVE_MATH" not in skills  # a preference is never ability evidence


def test_cold_start_recommends_but_does_not_require_diagnostic() -> None:
    state = replace(_state(), reported_cumulative_gpa=None, reported_gpa_scale=None,
                    reported_earned_credit_hours=None, attempts=())
    profile = build_student_intelligence_profile_v2(
        state, INSTITUTION, (), FAKE_UNIVERSITY_GRADE_POLICY_V1, generated_at=NOW)
    assert profile.cold_start_status == "COLD_START_NO_PERFORMANCE_EVIDENCE"
    assert profile.diagnostic_recommended is True
    assert profile.skills == ()
    assert profile.earned_credits == 0


def test_official_numeric_grade_without_configured_scale_creates_no_mastery() -> None:
    profile = build_student_intelligence_profile_v2(
        _state(), INSTITUTION,
        (_record("a1", "1501110", AttemptOutcome.PASSED, "95", date(2026, 1, 1), 1),),
        None, generated_at=NOW)
    assert profile.verified_grade_count == 0
    assert profile.skills == ()
    assert any("official_grade_mastery=UNAVAILABLE_UNVERIFIED_POLICY" in limitation
               for limitation in profile.limitations)


def test_grade_policy_registry_activates_only_for_exact_institution_and_plan() -> None:
    registry = GradePolicyRegistry((FAKE_UNIVERSITY_GRADE_POLICY_V1,))
    assert registry.resolve(INSTITUTION, PLAN) is FAKE_UNIVERSITY_GRADE_POLICY_V1
    assert registry.resolve("another-institution", PLAN) is None
    assert registry.resolve(INSTITUTION, "another-plan") is None
    assert GradePolicyRegistry().resolve(INSTITUTION, PLAN) is None
    service = StudentService(None, None, None, grade_policies=registry)  # type: ignore[arg-type]
    assert service._grade_policy_for(INSTITUTION, PLAN) is FAKE_UNIVERSITY_GRADE_POLICY_V1
    assert service._grade_policy_for(INSTITUTION, "another-plan") is None


def test_existing_student_shape_preserves_93_6_gpa_96_credits_32_grades_and_5_current() -> None:
    codes = tuple(PLAN12_COURSE_SKILLS)[:32]
    records = tuple(_record(f"a{i}", code, AttemptOutcome.PASSED, str(70 + i % 21),
                            date(2024 + i // 20, 1 + i % 12, 1), 1)
                    for i, code in enumerate(codes))
    state = replace(_state(), attempts=tuple(
        StudentCourseAttempt(code, AttemptOutcome.PASSED) for code in codes) + tuple(
        StudentCourseAttempt(code, AttemptOutcome.IN_PROGRESS) for code in tuple(PLAN12_COURSE_SKILLS)[32:37]))
    profile = build_student_intelligence_profile_v2(
        state, INSTITUTION, records, FAKE_UNIVERSITY_GRADE_POLICY_V1, generated_at=NOW)
    assert profile.cumulative_gpa == Decimal("93.6")
    assert profile.gpa_scale == Decimal("100")
    assert profile.earned_credits == Decimal("96")
    assert profile.verified_grade_count == 32
    assert profile.current_course_count == 5
    assert profile.cold_start_status == "ESTABLISHED_ACADEMIC_EVIDENCE"
