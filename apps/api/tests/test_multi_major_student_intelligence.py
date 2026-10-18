"""All-17-curriculum Student Intelligence conformance and synthetic E2E tests."""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.student.models import StudentAcademicState
from app.student_intelligence.curriculum_diagnostic_registry import (
    DEFAULT_CURRICULUM_DIAGNOSTICS,
    CurriculumDiagnosticDefinition,
)
from app.student_intelligence.curriculum_mapping import DEFAULT_CURRICULUM_SKILL_MAPPINGS
from app.student_intelligence.diagnostic import (
    ASSESSMENT_VERSION,
    AnswerEvidence,
    DiagnosticDomainResult,
    get_diagnostic_question_by_id,
)
from app.student_intelligence.diagnostic_service import DiagnosticConflict, DiagnosticService
from app.student_intelligence.profile_v2 import build_student_intelligence_profile_v2

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
INSTITUTION_ID = "10000000-0000-0000-0000-000000000001"
EXPECTED_COURSES = {
    "AI": 68, "SE": 65, "CS": 66, "CYBER": 67, "MATH": 76, "PHYS": 75,
    "ARABIC": 66, "ENGLISH": 62, "HISTORY": 61, "TRANS": 63,
    "ECON": 65, "BBA": 74, "ACC": 69, "DJOURN": 67, "RTV": 66,
    "LAW": 82, "NURS": 63,
}


def _state(definition: CurriculumDiagnosticDefinition) -> StudentAcademicState:
    return StudentAcademicState(
        profile_id=f"profile-{definition.major_code.lower()}",
        owner_user_id=f"owner-{definition.major_code.lower()}",
        study_plan_id=definition.study_plan_id,
        reported_cumulative_gpa=None,
        reported_gpa_scale=None,
        reported_earned_credit_hours=Decimal("0"),
        attempts=(),
        created_at=NOW,
        updated_at=NOW,
    )


def _mixed_answers(definition: CurriculumDiagnosticDefinition) -> tuple[AnswerEvidence, ...]:
    correct_per_domain = (6, 1, 4, 2, 5)
    answers: list[AnswerEvidence] = []
    for domain_index, domain in enumerate(definition.domains):
        questions = [q for q in definition.question_bank if q.domain == domain]
        for local_index, question in enumerate(questions):
            is_correct = local_index < correct_per_domain[domain_index]
            wrong = next(option.option_id for option in question.options
                         if option.option_id != question.correct_option)
            answers.append(AnswerEvidence(
                question.question_id,
                question.correct_option if is_correct else wrong,
                is_correct,
                40_000,
                "HIGH" if is_correct else "MEDIUM",
            ))
    return tuple(answers)


@pytest.mark.parametrize("definition", DEFAULT_CURRICULUM_DIAGNOSTICS.definitions,
                         ids=lambda item: item.major_code)
def test_all_curricula_resolve_with_complete_valid_course_mappings(
    definition: CurriculumDiagnosticDefinition,
) -> None:
    mapping = DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(definition.study_plan_id)
    assert mapping is not None
    assert len(mapping.courses) == EXPECTED_COURSES[definition.major_code]
    assert len(mapping.courses) == len(set(mapping.courses))
    for code, course in mapping.courses.items():
        assert course.course_code == code
        assert course.skills
        assert len({str(getattr(row.skill_id, "value", row.skill_id)) for row in course.skills}) == len(course.skills)
        assert all(0 < row.weight <= 1 for row in course.skills)


def test_registry_has_exactly_17_banks_and_510_globally_unique_questions() -> None:
    definitions = DEFAULT_CURRICULUM_DIAGNOSTICS.definitions
    assert len(definitions) == 17
    assert len(DEFAULT_CURRICULUM_SKILL_MAPPINGS.mappings) == 17
    question_ids = [q.question_id for definition in definitions for q in definition.question_bank]
    assert len(question_ids) == 510
    assert len(set(question_ids)) == 510
    assert set(EXPECTED_COURSES) == {definition.major_code for definition in definitions}


@pytest.mark.parametrize("definition", DEFAULT_CURRICULUM_DIAGNOSTICS.definitions,
                         ids=lambda item: item.major_code)
def test_every_bank_meets_domain_difficulty_bilingual_and_answer_quality_contract(
    definition: CurriculumDiagnosticDefinition,
) -> None:
    assert len(definition.question_bank) == 30
    assert len(definition.questions_by_id) == 30
    assert len(definition.domains) == 5
    assert Counter(q.domain for q in definition.question_bank) == Counter({domain: 6 for domain in definition.domains})
    assert Counter(q.difficulty for q in definition.question_bank) == Counter(
        {"EASY": 10, "MEDIUM": 10, "HARD": 10}
    )
    answer_counts = Counter(q.correct_option for q in definition.question_bank)
    assert set(answer_counts) == {"A", "B", "C", "D"}
    assert max(answer_counts.values()) <= 12
    for question in definition.question_bank:
        assert question.prompt_ar.strip() and question.prompt_en.strip()
        assert len(question.options) == 4
        assert {option.option_id for option in question.options} == {"A", "B", "C", "D"}
        assert all(option.text_ar.strip() and option.text_en.strip() for option in question.options)
        assert question.correct_option in {option.option_id for option in question.options}
        assert len(question.distractor_reasoning) == 3
        if definition.major_code not in {"AI", "NURS", "SE"}:
            assert question.skill in {
                str(getattr(skill, "value", skill))
                for skills in definition.skill_bridge.values() for skill in skills
            }


@pytest.mark.parametrize("definition", DEFAULT_CURRICULUM_DIAGNOSTICS.definitions,
                         ids=lambda item: item.major_code)
def test_every_fresh_curriculum_has_no_fabricated_mastery_or_academic_data(
    definition: CurriculumDiagnosticDefinition,
) -> None:
    state = _state(definition)
    profile = build_student_intelligence_profile_v2(
        state, INSTITUTION_ID, (), None, generated_at=NOW,
    )
    assert profile.study_plan_id == definition.study_plan_id
    assert profile.cold_start_status == "COLD_START_NO_PERFORMANCE_EVIDENCE"
    assert profile.diagnostic_recommended is True
    assert profile.diagnostic_completed is False
    assert profile.skills == ()
    assert profile.strengths == ()
    assert profile.development_areas == ()
    assert profile.cumulative_gpa is None
    assert profile.gpa_scale is None
    assert profile.earned_credits == Decimal("0")
    assert profile.completed_course_count == 0
    assert profile.failed_course_count == 0


@pytest.mark.parametrize("definition", DEFAULT_CURRICULUM_DIAGNOSTICS.definitions,
                         ids=lambda item: item.major_code)
def test_every_major_controlled_diagnostic_produces_only_its_bridge_skills(
    definition: CurriculumDiagnosticDefinition,
) -> None:
    state = _state(definition)
    state_before = state
    answers = _mixed_answers(definition)
    results = tuple(definition.scorer(domain, answers) for domain in definition.domains)
    assert len(results) == 5
    assert all(result.response_count == 6 for result in results)
    assert all(0 < result.score <= 100 for result in results)
    assert any(result.score < 60 for result in results)
    assert any(result.score >= 75 for result in results)
    profile = build_student_intelligence_profile_v2(
        state,
        INSTITUTION_ID,
        (),
        None,
        diagnostic_results=results,
        diagnostic_version=ASSESSMENT_VERSION,
        diagnostic_completed_at=NOW,
        generated_at=NOW,
    )
    allowed = {
        str(getattr(skill, "value", skill))
        for skills in definition.skill_bridge.values() for skill in skills
    }
    assert {skill.skill_id for skill in profile.skills}.issubset(allowed)
    assert profile.skills
    assert profile.strengths
    assert profile.development_areas
    assert state == state_before
    assert profile.cumulative_gpa is None
    assert profile.earned_credits == Decimal("0")


def test_score_and_confidence_remain_distinct_semantics() -> None:
    definition = DEFAULT_CURRICULUM_DIAGNOSTICS.definitions[3]
    answers = tuple(AnswerEvidence(
        question.question_id,
        next(option.option_id for option in question.options
             if option.option_id != question.correct_option),
        False,
        45_000,
        "LOW",
    ) for question in definition.question_bank)
    result = definition.scorer(definition.domains[0], answers)
    assert result.score < 60
    assert result.confidence in {"HIGH", "MEDIUM"}
    assert result.confidence != str(result.score)


def test_question_lookup_is_bound_to_session_curriculum() -> None:
    cs = next(item for item in DEFAULT_CURRICULUM_DIAGNOSTICS.definitions if item.major_code == "CS")
    cyber = next(item for item in DEFAULT_CURRICULUM_DIAGNOSTICS.definitions if item.major_code == "CYBER")
    assert get_diagnostic_question_by_id("CS01", study_plan_id=cs.study_plan_id) is not None
    assert get_diagnostic_question_by_id("CY01", study_plan_id=cs.study_plan_id) is None
    assert get_diagnostic_question_by_id("CS01", study_plan_id=cyber.study_plan_id) is None


class _StudentFake:
    def __init__(self, definition: CurriculumDiagnosticDefinition) -> None:
        self.definition = definition
        self.state = _state(definition)

    async def get_profile(self, owner: str):
        return self.state

    async def resolve_student_university_id(self, owner: str) -> str:
        return INSTITUTION_ID

    async def get_student_intelligence_v2(self, owner: str):
        return {"student_id": self.state.profile_id, "study_plan_id": self.state.study_plan_id}


class _DiagnosticRepo:
    def __init__(self) -> None:
        self.session: dict[str, Any] | None = None
        self.responses: list[dict[str, Any]] = []
        self.results: list[dict[str, Any]] = []

    async def load_active(self, owner: str, study_plan_id: str, version: str):
        return self.session if self.session and self.session["status"] == "IN_PROGRESS" else None

    async def load_session(self, owner: str, session_id: str):
        return self.session

    async def create_session(self, owner: str, profile_id: str, institution_id: str,
                             study_plan_id: str, version: str, question_id: str):
        self.session = {
            "id": f"session-{profile_id}", "owner_user_id": owner, "profile_id": profile_id,
            "institution_id": institution_id, "study_plan_id": study_plan_id,
            "assessment_version": version, "status": "IN_PROGRESS",
            "current_question_id": question_id, "question_count": 0,
            "completed_at": NOW.isoformat(),
        }
        return self.session

    async def load_responses(self, session_id: str):
        return self.responses

    async def record_answer_v2(self, **kwargs):
        self.responses.append({
            "question_id": kwargs["question_id"], "selected_option": kwargs["selected_option"],
            "is_correct": kwargs["is_correct"], "response_time_ms": kwargs["response_time_ms"],
            "self_confidence": kwargs["self_confidence"], "response_order": len(self.responses) + 1,
        })
        assert self.session is not None
        self.session["question_count"] = len(self.responses)
        self.session["current_question_id"] = kwargs["next_question_id"]
        if kwargs["results"] is not None:
            self.results = kwargs["results"]
            self.session["status"] = "COMPLETED"
        return self.session

    async def abandon(self, owner: str, session_id: str):
        return None

    async def latest_completed(self, owner: str, study_plan_id: str, version: str):
        return (self.session, self.results) if self.session and self.session["status"] == "COMPLETED" else (None, [])


@pytest.mark.parametrize("definition", DEFAULT_CURRICULUM_DIAGNOSTICS.definitions,
                         ids=lambda item: item.major_code)
def test_all_17_full_service_flows_present_and_accept_exactly_30_questions(
    definition: CurriculumDiagnosticDefinition,
) -> None:
    async def run() -> None:
        repo = _DiagnosticRepo()
        service = DiagnosticService(repo, _StudentFake(definition))  # type: ignore[arg-type]
        current = await service.start("owner", requested_version=ASSESSMENT_VERSION)
        seen: list[str] = []
        while current["question"] is not None:
            question_id = current["question"]["question_id"]
            question = definition.questions_by_id[question_id]
            seen.append(question_id)
            use_correct = (len(seen) % 6) not in {0, 5}
            selected = (question.correct_option if use_correct else
                        next(option.option_id for option in question.options
                             if option.option_id != question.correct_option))
            current = await service.answer(
                "owner", current["session_id"], question_id, selected,
                response_time_ms=40_000, self_confidence="MEDIUM",
            )
        assert current["status"] == "COMPLETED"
        assert len(seen) == 30
        assert len(set(seen)) == 30
        assert len(repo.responses) == 30
        assert len(repo.results) == 5
        assert {row["domain"] for row in repo.results} == {
            str(getattr(domain, "value", domain)) for domain in definition.domains
        }

    asyncio.run(run())


def test_service_rejects_cross_curriculum_answer_even_when_question_id_exists() -> None:
    async def run() -> None:
        cs = next(item for item in DEFAULT_CURRICULUM_DIAGNOSTICS.definitions if item.major_code == "CS")
        repo = _DiagnosticRepo()
        service = DiagnosticService(repo, _StudentFake(cs))  # type: ignore[arg-type]
        current = await service.start("owner", requested_version=ASSESSMENT_VERSION)
        assert current["question"]["question_id"] == "CS01"
        with pytest.raises(DiagnosticConflict, match="Question is not currently issued"):
            await service.answer(
                "owner", current["session_id"], "CY01", "A",
                response_time_ms=40_000, self_confidence="MEDIUM",
            )

    asyncio.run(run())
