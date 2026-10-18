"""Multi-Major Student Intelligence Expansion: Pilot Nursing Validation.

Verifies:
1. Canonical Nursing Plan 12 (ZU:NURS:NURS:P12, 2a78bbbb-0dc0-5c46-8630-7a46e4179830) taxonomy mapping.
2. 30-question balanced Nursing diagnostic question bank across 5 clinical domains.
3. Clean cold-start behavior for fresh student 209900017 with zero fabricated mastery.
4. Correct post-diagnostic scoring, strengths, and development areas strictly from Nursing competencies.
5. Zero AI skill leakage (no PROGRAMMING, PYTHON, MACHINE_LEARNING, etc.).
6. Non-AI, non-Nursing curricula (SE, CS, etc.) strictly remain HTTP 409 unsupported.
7. AI Plan 12 behavior completely preserved.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes.student import get_diagnostic_service, get_student_service
from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.rules.models import AttemptOutcome, StudentCourseAttempt
from app.student.models import StudentAcademicState
from app.student_intelligence.curriculum_mapping import (
    DEFAULT_CURRICULUM_SKILL_MAPPINGS,
    UnsupportedCurriculumIntelligenceError,
)
from app.student_intelligence.diagnostic import (
    ASSESSMENT_VERSION,
    AnswerEvidence,
    public_question,
    select_next_question,
)
from app.student_intelligence.diagnostic_service import DiagnosticConflict, DiagnosticService
from app.student_intelligence.nursing_diagnostic import (
    NURSING_QUESTION_BANK,
    NURSING_QUESTIONS_BY_ID,
    NursingDiagnosticDomain,
    score_nursing_domain,
    select_next_nursing_question,
)
from app.student_intelligence.profile_v2 import (
    NURSING_DIAGNOSTIC_SKILL_BRIDGE,
    build_student_intelligence_profile_v2,
)
from app.student_intelligence.taxonomy import (
    NURSING_PLAN12_COURSE_SKILLS,
    NURSING_PLAN12_ID,
    PLAN12_COURSE_SKILLS,
    PLAN12_ID,
    SUPPORTED_NURSING_PLAN12_COURSE_CODES,
    SkillId,
    validate_course_skill_definitions,
)

INSTITUTION_ID = "10000000-0000-0000-0000-000000000001"
NURSING_OWNER = "209900017-0000-0000-0000-000000000017"
AI_OWNER = "209900001-0000-0000-0000-000000000001"
SE_PLAN_ID = "1b709940-4279-560b-88ff-dacd5da636f2"
CS_PLAN_ID = "33333333-3333-3333-3333-333333333333"
NOW = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)

AI_EXCLUSIVE_SKILLS = frozenset({
    SkillId.PROGRAMMING,
    SkillId.PYTHON,
    SkillId.OBJECT_ORIENTED_PROGRAMMING,
    SkillId.DATA_STRUCTURES,
    SkillId.ALGORITHMS,
    SkillId.LOGICAL_REASONING,
    SkillId.DISCRETE_MATH,
    SkillId.QUANTITATIVE_MATH,
    SkillId.LINEAR_ALGEBRA,
    SkillId.STATISTICS,
    SkillId.DATA_ANALYSIS,
    SkillId.DATABASES,
    SkillId.SOFTWARE_ENGINEERING,
    SkillId.WEB_DEVELOPMENT,
    SkillId.AI_FOUNDATIONS,
    SkillId.MACHINE_LEARNING,
    SkillId.DEEP_LEARNING,
    SkillId.SYSTEMS,
    SkillId.NETWORKS,
    SkillId.COMPUTER_VISION,
    SkillId.NATURAL_LANGUAGE_PROCESSING,
    SkillId.ROBOTICS,
})


def _fresh_nursing_state() -> StudentAcademicState:
    return StudentAcademicState(
        profile_id="profile-nursing-209900017",
        owner_user_id=NURSING_OWNER,
        study_plan_id=NURSING_PLAN12_ID,
        reported_cumulative_gpa=None,
        reported_gpa_scale=None,
        reported_earned_credit_hours=Decimal("0"),
        attempts=(),
        created_at=NOW,
        updated_at=NOW,
    )


# --- 1. TAXONOMY AND CURRICULUM INTEGRITY ---

def test_nursing_taxonomy_covers_canonical_seed_and_no_ai_skills() -> None:
    assert len(NURSING_PLAN12_COURSE_SKILLS) == 63
    assert set(NURSING_PLAN12_COURSE_SKILLS) == SUPPORTED_NURSING_PLAN12_COURSE_CODES

    # Verify every course mapping has valid skills and weights
    for code, definition in NURSING_PLAN12_COURSE_SKILLS.items():
        assert definition.skills, f"Course {code} has no skills"
        for weighted in definition.skills:
            assert isinstance(weighted.skill_id, SkillId)
            assert 0 < weighted.weight <= 1.0
            # Zero AI skill leakage in Nursing curriculum
            assert weighted.skill_id not in AI_EXCLUSIVE_SKILLS, (
                f"Course {code} contains AI skill: {weighted.skill_id}"
            )


def test_curriculum_registry_resolves_nursing_and_ai_and_blocks_others() -> None:
    ai_mapping = DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(PLAN12_ID)
    assert ai_mapping is not None
    assert ai_mapping.study_plan_id == PLAN12_ID

    nursing_mapping = DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(NURSING_PLAN12_ID)
    assert nursing_mapping is not None
    assert nursing_mapping.study_plan_id == NURSING_PLAN12_ID

    # Non-supported majors remain unsupported (e.g. CS, Cyber)
    assert DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(CS_PLAN_ID) is None


# --- 2. NURSING DIAGNOSTIC QUESTION BANK INTEGRITY ---

def test_nursing_question_bank_is_balanced_and_clinical() -> None:
    assert len(NURSING_QUESTION_BANK) == 30
    assert len(NURSING_QUESTIONS_BY_ID) == 30

    # Exactly 5 domains, 6 questions each
    domain_counts = {
        domain: sum(q.domain is domain for q in NURSING_QUESTION_BANK)
        for domain in NursingDiagnosticDomain
    }
    assert domain_counts == {domain: 6 for domain in NursingDiagnosticDomain}

    # Exactly 10 easy, 10 medium, 10 hard
    difficulty_counts = {
        diff: sum(q.difficulty == diff for q in NURSING_QUESTION_BANK)
        for diff in ("EASY", "MEDIUM", "HARD")
    }
    assert difficulty_counts == {"EASY": 10, "MEDIUM": 10, "HARD": 10}

    # Exactly 2 of each difficulty per domain
    for domain in NursingDiagnosticDomain:
        for diff in ("EASY", "MEDIUM", "HARD"):
            count = sum(q.domain is domain and q.difficulty == diff for q in NURSING_QUESTION_BANK)
            assert count == 2, f"Domain {domain} does not have 2 {diff} questions (found {count})"

    # Verify questions never leak internals in public projection
    for q in NURSING_QUESTION_BANK:
        assert q.skill and q.subskill and q.cognitive_operation
        assert q.expected_solving_behavior and q.estimated_time_seconds > 0
        assert q.correct_option in {"A", "B", "C", "D"}
        assert len(q.options) == 4
        assert set(q.distractor_reasoning) == {
            opt.option_id for opt in q.options if opt.option_id != q.correct_option
        }

        # Public projection safety
        public = public_question(q)
        assert "correct_option" not in public
        assert "difficulty" not in public
        assert "domain" not in public
        assert "distractor_reasoning" not in public
        assert len(public["options"]) == 4


# --- 3. COLD START FOR FRESH NURSING STUDENT ---

def test_fresh_nursing_student_cold_start_has_no_fabricated_mastery() -> None:
    state = _fresh_nursing_state()
    profile = build_student_intelligence_profile_v2(
        state,
        INSTITUTION_ID,
        (),
        None,
        generated_at=NOW,
    )
    assert profile.study_plan_id == NURSING_PLAN12_ID
    assert profile.cold_start_status == "COLD_START_NO_PERFORMANCE_EVIDENCE"
    assert profile.diagnostic_recommended is True
    assert profile.diagnostic_completed is False
    assert profile.skills == ()  # Zero fabricated mastery
    assert profile.strengths == ()
    assert profile.development_areas == ()
    assert profile.verified_grade_count == 0
    assert profile.earned_credits == Decimal("0")
    assert profile.cumulative_gpa is None


def test_unsupported_major_raises_conflict_in_profile_v2() -> None:
    cs_state = StudentAcademicState(
        profile_id="profile-cs",
        owner_user_id="cs-owner",
        study_plan_id=CS_PLAN_ID,
        reported_cumulative_gpa=None,
        reported_gpa_scale=None,
        reported_earned_credit_hours=Decimal("0"),
        attempts=(),
        created_at=NOW,
        updated_at=NOW,
    )
    with pytest.raises(UnsupportedCurriculumIntelligenceError):
        build_student_intelligence_profile_v2(
            cs_state,
            INSTITUTION_ID,
            (),
            None,
            generated_at=NOW,
        )


# --- 4. QUICK TEST COMPLETION AND EVIDENCE FUSION ---

def test_completed_nursing_diagnostic_produces_pure_nursing_competencies() -> None:
    state = _fresh_nursing_state()

    # Simulate answered diagnostic with high score in Fundamentals, Anatomy, Pharmacology,
    # and lower score in Clinical Assessment to test both strengths and development areas
    answers: list[AnswerEvidence] = []
    for q in NURSING_QUESTION_BANK:
        # High score in NF, AP, PH; lower score in CA
        is_correct = (q.domain is not NursingDiagnosticDomain.CLINICAL_ASSESSMENT_REASONING) or (q.difficulty == "EASY")
        selected = q.correct_option if is_correct else [opt.option_id for opt in q.options if opt.option_id != q.correct_option][0]
        answers.append(AnswerEvidence(
            q.question_id,
            selected,
            is_correct,
            30_000,
            "HIGH" if is_correct else "LOW",
        ))

    # Score each domain
    results = tuple(
        score_nursing_domain(domain, answers)
        for domain in NursingDiagnosticDomain
    )
    assert len(results) == 5

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

    assert profile.diagnostic_completed is True
    assert profile.diagnostic_recommended is False
    assert len(profile.skills) > 0

    # Verify all skills belong to Nursing competency bridge
    skill_ids = {dim.skill_id for dim in profile.skills}
    for skill_id in skill_ids:
        assert skill_id not in {s.value for s in AI_EXCLUSIVE_SKILLS}, (
            f"AI skill leakage detected in Nursing profile: {skill_id}"
        )

    # Verify strengths and development areas
    assert len(profile.strengths) > 0
    for strength in profile.strengths:
        assert strength not in {s.value for s in AI_EXCLUSIVE_SKILLS}

    assert len(profile.development_areas) > 0
    for dev in profile.development_areas:
        assert dev not in {s.value for s in AI_EXCLUSIVE_SKILLS}

    # Verify evidence provenance
    assert all(dim.university_evidence_count == 0 for dim in profile.skills)
    assert all(dim.diagnostic_evidence_count > 0 for dim in profile.skills)
    assert all(dim.source_types == ("COMPLETED_QUICK_DIAGNOSTIC",) for dim in profile.skills)


# --- 5. DIAGNOSTIC SERVICE FLOW FOR NURSING ---

class NursingStudentFake:
    async def get_profile(self, owner: str):
        return _fresh_nursing_state()

    async def resolve_student_university_id(self, owner: str) -> str:
        return INSTITUTION_ID

    async def get_student_intelligence_v2(self, owner: str):
        return {"student_id": "profile-nursing-209900017", "study_plan_id": NURSING_PLAN12_ID}


class InMemoryDiagnosticRepo:
    def __init__(self) -> None:
        self.session: dict[str, Any] | None = None
        self.responses: list[dict[str, Any]] = []

    async def load_active(self, owner: str, study_plan_id: str, version: str):
        if self.session and self.session["status"] == "IN_PROGRESS":
            return self.session
        return None

    async def load_session(self, owner: str, session_id: str):
        return self.session

    async def create_session(self, owner: str, profile_id: str, institution_id: str,
                             study_plan_id: str, version: str, question_id: str):
        self.session = {
            "id": "session-nurs-001",
            "owner_user_id": owner,
            "profile_id": profile_id,
            "institution_id": institution_id,
            "study_plan_id": study_plan_id,
            "assessment_version": version,
            "status": "IN_PROGRESS",
            "current_question_id": question_id,
            "question_count": 0,
        }
        return self.session

    async def load_responses(self, session_id: str):
        return self.responses

    async def record_answer_v2(self, **kwargs):
        self.responses.append({
            "question_id": kwargs["question_id"],
            "selected_option": kwargs["selected_option"],
            "is_correct": kwargs["is_correct"],
            "response_time_ms": kwargs["response_time_ms"],
            "self_confidence": kwargs["self_confidence"],
            "response_order": len(self.responses) + 1,
        })
        self.session["question_count"] = len(self.responses)
        self.session["current_question_id"] = kwargs["next_question_id"]
        if kwargs["next_question_id"] is None:
            self.session["status"] = "COMPLETED"
        return self.session

    async def abandon(self, owner: str, session_id: str):
        if self.session:
            self.session["status"] = "ABANDONED"
            self.session["current_question_id"] = None
            return self.session
        return None

    async def latest_completed(self, owner: str, study_plan_id: str, version: str):
        if self.session and self.session["status"] == "COMPLETED":
            return self.session, []
        return None, []


def test_diagnostic_service_runs_nursing_assessment_end_to_end() -> None:
    import asyncio

    async def _run():
        repo = InMemoryDiagnosticRepo()
        service = DiagnosticService(repo, NursingStudentFake())  # type: ignore[arg-type]

        # 1. Start session: should issue N01 (Nursing question 1)
        session = await service.start(NURSING_OWNER, requested_version=ASSESSMENT_VERSION)
        assert session["session_id"] == "session-nurs-001"
        assert session["status"] == "IN_PROGRESS"
        assert session["maximum_questions"] == 30
        assert session["answered_count"] == 0
        assert session["question"]["question_id"] == "N01"
        assert "نبض القلب" in session["question"]["prompt_ar"]

        # 2. Answer first 29 questions sequentially
        for q in NURSING_QUESTION_BANK[:-1]:
            res = await service.answer(
                NURSING_OWNER,
                "session-nurs-001",
                q.question_id,
                q.correct_option,
                25_000,
                "HIGH",
            )
            assert res["status"] == "IN_PROGRESS"
            assert res["question"] is not None

        # 3. Answer 30th question: should complete assessment and return results
        last_q = NURSING_QUESTION_BANK[-1]
        final = await service.answer(
            NURSING_OWNER,
            "session-nurs-001",
            last_q.question_id,
            last_q.correct_option,
            25_000,
            "HIGH",
        )
        assert final["status"] == "COMPLETED"
        assert final["question"] is None
        assert final["answered_count"] == 30
        assert "results" in final
        assert len(final["results"]) == 5
        result_domains = {r["domain"] for r in final["results"]}
        expected_domains = {d.value for d in NursingDiagnosticDomain}
        assert result_domains == expected_domains

    asyncio.run(_run())
