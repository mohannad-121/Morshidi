"""Multi-Major Student Intelligence Expansion: Software Engineering Validation.

Verifies:
1. Canonical Software Engineering Plan 12 (ZU:IT:SE:P12, 1b709940-4279-560b-88ff-dacd5da636f2) taxonomy mapping.
2. 30-question balanced SE diagnostic question bank across 5 core undergraduate domains.
3. Clean cold-start behavior for fresh student 209900002 with zero fabricated mastery or GPA.
4. Correct post-diagnostic scoring, strengths, and development areas strictly from SE competencies.
5. Zero AI skill leakage (except the single curriculum course 1505201 Intro to AI).
6. Non-supported curricula (CS, Cyber, Math, etc.) strictly remain unsupported.
7. AI and Nursing behaviors completely preserved.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

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
from app.student_intelligence.profile_v2 import (
    SE_DIAGNOSTIC_SKILL_BRIDGE,
    build_student_intelligence_profile_v2,
)
from app.student_intelligence.se_diagnostic import (
    SE_QUESTION_BANK,
    SE_QUESTIONS_BY_ID,
    SoftwareEngineeringDiagnosticDomain,
    score_se_domain,
    select_next_se_question,
)
from app.student_intelligence.taxonomy import (
    NURSING_PLAN12_ID,
    PLAN12_ID,
    SE_PLAN12_COURSE_SKILLS,
    SE_PLAN12_ID,
    SUPPORTED_SE_PLAN12_COURSE_CODES,
    SkillId,
)

INSTITUTION_ID = "10000000-0000-0000-0000-000000000001"
SE_OWNER = "209900002-0000-0000-0000-000000000002"
CS_PLAN_ID = "33333333-3333-3333-3333-333333333333"
CYBER_PLAN_ID = "44444444-4444-4444-4444-444444444444"
NOW = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)

AI_DISCIPLINE_EXCLUSIVE_SKILLS = frozenset({
    SkillId.MACHINE_LEARNING,
    SkillId.DEEP_LEARNING,
    SkillId.COMPUTER_VISION,
    SkillId.NATURAL_LANGUAGE_PROCESSING,
    SkillId.ROBOTICS,
})


def _fresh_se_state() -> StudentAcademicState:
    return StudentAcademicState(
        profile_id="profile-se-209900002",
        owner_user_id=SE_OWNER,
        study_plan_id=SE_PLAN12_ID,
        reported_cumulative_gpa=None,
        reported_gpa_scale=None,
        reported_earned_credit_hours=Decimal("0"),
        attempts=(),
        created_at=NOW,
        updated_at=NOW,
    )


# --- 1. SE TAXONOMY AND MAPPING ISOLATION ---

def test_se_taxonomy_covers_canonical_seed_and_no_ai_leakage() -> None:
    assert len(SE_PLAN12_COURSE_SKILLS) == 65
    assert frozenset(SE_PLAN12_COURSE_SKILLS.keys()) == SUPPORTED_SE_PLAN12_COURSE_CODES

    # Verify each course has valid skill weights (0 < weight <= 1.0)
    for code, defn in SE_PLAN12_COURSE_SKILLS.items():
        assert len(defn.skills) >= 1
        for weighted in defn.skills:
            assert 0 < weighted.weight <= 1.0

    # Verify NO AI-discipline exclusive skills (ML, Deep Learning, CV, NLP, Robotics)
    # exist anywhere in the SE Plan 12 curriculum mapping
    for code, defn in SE_PLAN12_COURSE_SKILLS.items():
        skills = {w.skill_id for w in defn.skills}
        leaked_ai = skills & AI_DISCIPLINE_EXCLUSIVE_SKILLS
        assert not leaked_ai, f"Course {code} contains leaked AI skills: {leaked_ai}"

    # Verify course 1505201 (Introduction to Artificial Intelligence) is the only course with AI_FOUNDATIONS
    ai_foundations_courses = {
        code for code, defn in SE_PLAN12_COURSE_SKILLS.items()
        if any(w.skill_id == SkillId.AI_FOUNDATIONS for w in defn.skills)
    }
    assert ai_foundations_courses == {"1505201"}


def test_curriculum_registry_resolves_se_nursing_and_ai_and_blocks_unsupported() -> None:
    ai_mapping = DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(PLAN12_ID)
    assert ai_mapping is not None
    assert ai_mapping.study_plan_id == PLAN12_ID

    nursing_mapping = DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(NURSING_PLAN12_ID)
    assert nursing_mapping is not None
    assert nursing_mapping.study_plan_id == NURSING_PLAN12_ID

    se_mapping = DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(SE_PLAN12_ID)
    assert se_mapping is not None
    assert se_mapping.study_plan_id == SE_PLAN12_ID

    # Other majors remain unsupported
    assert DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(CS_PLAN_ID) is None
    assert DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(CYBER_PLAN_ID) is None


# --- 2. SE DIAGNOSTIC QUESTION BANK INTEGRITY ---

def test_se_question_bank_is_balanced_and_academic() -> None:
    assert len(SE_QUESTION_BANK) == 30
    assert len(SE_QUESTIONS_BY_ID) == 30

    # Exactly 5 domains, 6 questions each
    domain_counts: dict[SoftwareEngineeringDiagnosticDomain, int] = {}
    for q in SE_QUESTION_BANK:
        domain_counts[q.domain] = domain_counts.get(q.domain, 0) + 1
    assert len(domain_counts) == 5
    for domain, count in domain_counts.items():
        assert count == 6, f"Domain {domain} does not have exactly 6 questions"

    # Difficulty balance: exactly 10 EASY, 10 MEDIUM, 10 HARD (2 of each per domain)
    difficulty_counts = {"EASY": 0, "MEDIUM": 0, "HARD": 0}
    for domain in SoftwareEngineeringDiagnosticDomain:
        domain_qs = [q for q in SE_QUESTION_BANK if q.domain == domain]
        d_diffs = [q.difficulty for q in domain_qs]
        assert d_diffs.count("EASY") == 2
        assert d_diffs.count("MEDIUM") == 2
        assert d_diffs.count("HARD") == 2
        for diff in d_diffs:
            difficulty_counts[diff] += 1
    assert difficulty_counts == {"EASY": 10, "MEDIUM": 10, "HARD": 10}

    # Option keys: exactly 4 choices per question (A, B, C, D)
    option_key_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for q in SE_QUESTION_BANK:
        assert len(q.options) == 4
        assert q.correct_option in {"A", "B", "C", "D"}
        option_key_counts[q.correct_option] += 1
        # Exactly 3 distractor explanations for the 3 wrong choices
        assert len(q.distractor_reasoning) == 3
        assert q.correct_option not in q.distractor_reasoning
        # Prompts exist and are non-empty
        assert len(q.prompt_ar) > 10
        assert len(q.prompt_en) > 10
        # Check option texts exist in both languages
        for opt in q.options:
            assert len(opt.text_ar) > 0
            assert len(opt.text_en) > 0

    # Option key distribution: balanced (no single key >= 70% to avoid psychometric flag)
    for key, count in option_key_counts.items():
        assert count <= 10, f"Option key {key} is over-represented: {count}/30"


# --- 3. COLD-START BEHAVIOR (STUDENT 209900002) ---

def test_fresh_se_student_cold_start_has_no_fabricated_mastery() -> None:
    state = _fresh_se_state()
    profile = build_student_intelligence_profile_v2(
        state,
        INSTITUTION_ID,
        (),
        None,
        generated_at=NOW,
    )

    # 1. Plan and Identity verification
    assert profile.study_plan_id == SE_PLAN12_ID
    assert profile.institution_id == INSTITUTION_ID
    assert profile.student_id == "profile-se-209900002"

    # 2. Cold-start status
    assert profile.diagnostic_recommended is True
    assert profile.cold_start_status == "COLD_START_NO_PERFORMANCE_EVIDENCE"
    assert profile.diagnostic_completed is False

    # 3. No fabricated mastery, strengths, or development areas
    assert len(profile.skills) == 0
    assert len(profile.strengths) == 0
    assert len(profile.development_areas) == 0

    # 4. No fabricated GPA or credit hours
    assert profile.cumulative_gpa is None
    assert profile.earned_credits == Decimal("0")
    assert profile.completed_course_count == 0
    assert profile.failed_course_count == 0


# --- 4. QUICK TEST COMPLETION AND EVIDENCE FUSION ---

def test_completed_se_diagnostic_produces_pure_se_competencies() -> None:
    state = _fresh_se_state()

    # Create 30 diagnostic responses (controlled performance: 20 correct, 10 incorrect)
    # 4 correct in domain 1, 4 in domain 2, 4 in domain 3, 4 in domain 4, 4 in domain 5
    responses: list[AnswerEvidence] = []
    for index, q in enumerate(SE_QUESTION_BANK):
        is_correct = (index % 6) < 4  # 4 out of 6 correct per domain
        selected = q.correct_option if is_correct else ("B" if q.correct_option != "B" else "C")
        responses.append(
            AnswerEvidence(
                question_id=q.question_id,
                selected_option=selected,
                is_correct=is_correct,
                response_time_ms=30_000,
                self_confidence="HIGH",
            )
        )

    # Score each domain
    domain_results = [
        score_se_domain(domain, responses)
        for domain in SoftwareEngineeringDiagnosticDomain
    ]
    assert len(domain_results) == 5
    for dr in domain_results:
        assert 0 <= dr.score <= 100
        assert dr.response_count == 6
        assert dr.confidence in {"HIGH", "MEDIUM"}

    # Build profile with diagnostic results
    profile = build_student_intelligence_profile_v2(
        state,
        INSTITUTION_ID,
        (),
        None,
        diagnostic_results=tuple(domain_results),
        diagnostic_version=ASSESSMENT_VERSION,
        diagnostic_completed_at=NOW,
        generated_at=NOW,
    )

    assert profile.diagnostic_completed is True
    assert profile.diagnostic_recommended is False

    # Verify skills are populated
    assert len(profile.skills) > 0

    # Verify zero AI-discipline skills exist in profile
    profile_skill_names = {s.skill_id for s in profile.skills}
    leaked_ai = profile_skill_names & {s.value for s in AI_DISCIPLINE_EXCLUSIVE_SKILLS}
    assert not leaked_ai, f"Profile contains leaked AI skills: {leaked_ai}"

    # Verify all skills mapped come from the SE bridge
    expected_possible_skills = set()
    for domain_skills in SE_DIAGNOSTIC_SKILL_BRIDGE.values():
        for skill in domain_skills:
            expected_possible_skills.add(skill.value)
    assert profile_skill_names.issubset(expected_possible_skills)


# --- 5. DIAGNOSTIC SERVICE E2E MOCK TEST ---

class SEStudentFake:
    async def get_profile(self, owner: str):
        return _fresh_se_state()

    async def resolve_student_university_id(self, owner: str):
        return INSTITUTION_ID

    async def get_student_intelligence_v2(self, owner: str):
        return {"student_id": "profile-se-209900002", "study_plan_id": SE_PLAN12_ID}


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
            "id": "session-se-001",
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


def test_diagnostic_service_runs_se_assessment_end_to_end() -> None:
    async def _run():
        repo = InMemoryDiagnosticRepo()
        service = DiagnosticService(repo, SEStudentFake())  # type: ignore[arg-type]

        # 1. Start session: should issue SE01 (Software Engineering question 1)
        session = await service.start(SE_OWNER, requested_version=ASSESSMENT_VERSION)
        assert session["session_id"] == "session-se-001"
        assert session["status"] == "IN_PROGRESS"
        assert session["maximum_questions"] == 30
        assert session["answered_count"] == 0
        assert session["question"]["question_id"] == "SE01"
        assert "نطاق" in session["question"]["prompt_ar"]

        # 2. Answer first 29 questions sequentially
        for q in SE_QUESTION_BANK[:-1]:
            res = await service.answer(
                SE_OWNER,
                "session-se-001",
                q.question_id,
                q.correct_option,
                25_000,
                "HIGH",
            )
            assert res["status"] == "IN_PROGRESS"
            assert res["question"] is not None

        # 3. Answer 30th question: should complete assessment and return results
        last_q = SE_QUESTION_BANK[-1]
        final = await service.answer(
            SE_OWNER,
            "session-se-001",
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
        expected_domains = {d.value for d in SoftwareEngineeringDiagnosticDomain}
        assert result_domains == expected_domains

    asyncio.run(_run())
