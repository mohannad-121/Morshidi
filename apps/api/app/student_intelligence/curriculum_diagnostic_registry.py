"""Single curriculum-aware registry for all deterministic Quick Test banks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from app.student_intelligence.diagnostic import (
    QUESTION_BANK,
    QUESTIONS_BY_ID,
    AnswerEvidence,
    DiagnosticDomain,
    DiagnosticDomainResult,
    DiagnosticQuestion,
    score_domain,
)
from app.student_intelligence.multi_major import (
    MULTI_MAJOR_DEFINITIONS,
    MultiMajorDefinition,
    score_multi_major_domain,
)
from app.student_intelligence.nursing_diagnostic import (
    NURSING_QUESTION_BANK,
    NURSING_QUESTIONS_BY_ID,
    NursingDiagnosticDomain,
    score_nursing_domain,
)
from app.student_intelligence.se_diagnostic import (
    SE_QUESTION_BANK,
    SE_QUESTIONS_BY_ID,
    SoftwareEngineeringDiagnosticDomain,
    score_se_domain,
)
from app.student_intelligence.taxonomy import NURSING_PLAN12_ID, PLAN12_ID, SE_PLAN12_ID, SkillId


@dataclass(frozen=True, slots=True)
class CurriculumDiagnosticDefinition:
    study_plan_id: str
    major_code: str
    domains: tuple[object, ...]
    question_bank: tuple[DiagnosticQuestion, ...]
    questions_by_id: Mapping[str, DiagnosticQuestion]
    skill_bridge: Mapping[object, tuple[object, ...]]
    scorer: Callable[[object, Iterable[AnswerEvidence]], DiagnosticDomainResult]


AI_BRIDGE: Mapping[object, tuple[object, ...]] = {
    DiagnosticDomain.PROGRAMMING_REASONING: (
        SkillId.PROGRAMMING, SkillId.PYTHON, SkillId.OBJECT_ORIENTED_PROGRAMMING,
    ),
    DiagnosticDomain.LOGICAL_PROBLEM_SOLVING: (
        SkillId.LOGICAL_REASONING, SkillId.ALGORITHMS, SkillId.DISCRETE_MATH,
    ),
    DiagnosticDomain.QUANTITATIVE_MATH: (SkillId.QUANTITATIVE_MATH, SkillId.LINEAR_ALGEBRA),
    DiagnosticDomain.STATISTICS_DATA_REASONING: (SkillId.STATISTICS, SkillId.DATA_ANALYSIS),
    DiagnosticDomain.THEORY_CONCEPTUAL_UNDERSTANDING: (
        SkillId.THEORY_COMPREHENSION, SkillId.MEMORIZATION,
    ),
}

NURSING_BRIDGE: Mapping[object, tuple[object, ...]] = {
    NursingDiagnosticDomain.NURSING_FUNDAMENTALS: (
        SkillId.NURSING_FUNDAMENTALS, SkillId.THEORY_COMPREHENSION, SkillId.PRACTICAL_LAB,
    ),
    NursingDiagnosticDomain.ANATOMY_PHYSIOLOGY_FOUNDATIONS: (
        SkillId.ANATOMY_PHYSIOLOGY, SkillId.PATHOPHYSIOLOGY,
    ),
    NursingDiagnosticDomain.PHARMACOLOGY_FOUNDATIONS: (
        SkillId.PHARMACOLOGY, SkillId.PATIENT_SAFETY,
    ),
    NursingDiagnosticDomain.PATIENT_SAFETY_INFECTION_CONTROL: (
        SkillId.PATIENT_SAFETY, SkillId.ETHICS,
    ),
    NursingDiagnosticDomain.CLINICAL_ASSESSMENT_REASONING: (
        SkillId.CLINICAL_ASSESSMENT, SkillId.COMMUNICATION,
    ),
}

SE_BRIDGE: Mapping[object, tuple[object, ...]] = {
    SoftwareEngineeringDiagnosticDomain.SE_PROGRAMMING_OOP_DATA_STRUCTURES: (
        SkillId.PROGRAMMING, SkillId.OBJECT_ORIENTED_PROGRAMMING, SkillId.DATA_STRUCTURES,
    ),
    SoftwareEngineeringDiagnosticDomain.SE_REQUIREMENTS_MODELING_ANALYSIS: (
        SkillId.SOFTWARE_REQUIREMENTS, SkillId.SOFTWARE_MODELING_ANALYSIS,
    ),
    SoftwareEngineeringDiagnosticDomain.SE_DESIGN_ARCHITECTURE_PATTERNS: (
        SkillId.SOFTWARE_DESIGN_ARCHITECTURE, SkillId.DESIGN_PATTERNS,
    ),
    SoftwareEngineeringDiagnosticDomain.SE_TESTING_QUALITY_MAINTENANCE: (
        SkillId.SOFTWARE_TESTING_METRICS, SkillId.SOFTWARE_QUALITY_ENGINEERING,
        SkillId.SOFTWARE_MAINTENANCE_EVOLUTION,
    ),
    SoftwareEngineeringDiagnosticDomain.SE_LIFECYCLE_PROJECT_MANAGEMENT: (
        SkillId.SOFTWARE_PROJECT_MANAGEMENT, SkillId.SOFTWARE_ENGINEERING_PRACTICES,
        SkillId.SOFTWARE_ENGINEERING_TOOLS,
    ),
}


def _ai_score(domain: object, responses: Iterable[AnswerEvidence]) -> DiagnosticDomainResult:
    return score_domain(DiagnosticDomain(domain), responses)


def _nursing_score(domain: object, responses: Iterable[AnswerEvidence]) -> DiagnosticDomainResult:
    return score_nursing_domain(NursingDiagnosticDomain(domain), responses)


def _se_score(domain: object, responses: Iterable[AnswerEvidence]) -> DiagnosticDomainResult:
    return score_se_domain(SoftwareEngineeringDiagnosticDomain(domain), responses)


def _multi_definition(item: MultiMajorDefinition) -> CurriculumDiagnosticDefinition:
    return CurriculumDiagnosticDefinition(
        study_plan_id=item.study_plan_id,
        major_code=item.major_code,
        domains=item.domains,
        question_bank=item.question_bank,
        questions_by_id=item.questions_by_id,
        skill_bridge=item.diagnostic_bridge,
        scorer=lambda domain, responses, definition=item: score_multi_major_domain(
            definition, str(domain), responses
        ),
    )


CURRICULUM_DIAGNOSTICS: tuple[CurriculumDiagnosticDefinition, ...] = (
    CurriculumDiagnosticDefinition(
        PLAN12_ID, "AI", tuple(DiagnosticDomain), QUESTION_BANK, QUESTIONS_BY_ID, AI_BRIDGE, _ai_score,
    ),
    CurriculumDiagnosticDefinition(
        NURSING_PLAN12_ID, "NURS", tuple(NursingDiagnosticDomain), NURSING_QUESTION_BANK,
        NURSING_QUESTIONS_BY_ID, NURSING_BRIDGE, _nursing_score,
    ),
    CurriculumDiagnosticDefinition(
        SE_PLAN12_ID, "SE", tuple(SoftwareEngineeringDiagnosticDomain), SE_QUESTION_BANK,
        SE_QUESTIONS_BY_ID, SE_BRIDGE, _se_score,
    ),
    *tuple(_multi_definition(item) for item in MULTI_MAJOR_DEFINITIONS),
)


class CurriculumDiagnosticRegistry:
    def __init__(self, definitions: tuple[CurriculumDiagnosticDefinition, ...]) -> None:
        self.definitions = definitions
        self._by_plan = {item.study_plan_id: item for item in definitions}
        self._by_question = {
            question_id: item
            for item in definitions
            for question_id in item.questions_by_id
        }
        if len(self._by_plan) != len(definitions):
            raise ValueError("Duplicate curriculum diagnostic plan id")
        expected_questions = sum(len(item.question_bank) for item in definitions)
        if len(self._by_question) != expected_questions:
            raise ValueError("Duplicate curriculum diagnostic question id")

    def resolve(self, study_plan_id: str) -> CurriculumDiagnosticDefinition | None:
        return self._by_plan.get(study_plan_id)

    def resolve_question(
        self, study_plan_id: str, question_id: str
    ) -> DiagnosticQuestion | None:
        definition = self.resolve(study_plan_id)
        return definition.questions_by_id.get(question_id) if definition else None

    def owner_of_question(self, question_id: str) -> CurriculumDiagnosticDefinition | None:
        return self._by_question.get(question_id)


DEFAULT_CURRICULUM_DIAGNOSTICS = CurriculumDiagnosticRegistry(CURRICULUM_DIAGNOSTICS)
