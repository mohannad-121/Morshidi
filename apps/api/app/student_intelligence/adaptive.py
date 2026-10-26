"""P15.5 auditable, modeled difficulty and eligible-only student course fit.

No trained model, institutional grade conversion, or academic decision lives here.
The existing progress, eligibility, and recommendation engines remain upstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Mapping

from app.progress.models import AcademicProgress, AcademicProgressCatalog
from app.recommendations.models import RecommendationResult
from app.rules.models import CanTakeCatalog, PrerequisiteLogicStatus
from app.rules.project_credits import passed_plan_credits
from app.student.models import (PerformanceProvenance, PerformanceVerificationState,
                                StudentAcademicState, StudentCourseAttemptRecord)
from app.student_intelligence.taxonomy import COURSE_SKILL_MAPPING_VERSION, PLAN12_ID
from app.student_intelligence.curriculum_mapping import DEFAULT_CURRICULUM_SKILL_MAPPINGS
from app.university_sync.grading_policy import (
    FAKE_UNIVERSITY_COURSE_GRADE_MAX,
    FAKE_UNIVERSITY_COURSE_GRADE_MIN,
    FAKE_UNIVERSITY_GRADING_POLICY_V1 as FAKE_UNIVERSITY_GRADING_POLICY_VERSION,
    SUPPORTED_POLICY_VERSIONS,
    parse_grading_policy_source_reference,
)

GENERAL_MODEL_VERSION = "GENERAL_DIFFICULTY_MODEL_V1"
MASTERY_MODEL_VERSION = "STUDENT_MASTERY_MODEL_V1"
PERSONAL_MODEL_VERSION = "PERSONAL_DIFFICULTY_MODEL_V1"
RECOMMENDER_MODEL_VERSION = "COURSE_RECOMMENDER_V1"
SKILL_PROFILE_VERSION = COURSE_SKILL_MAPPING_VERSION
FRESHNESS_POLICY_VERSION = "SOURCE_FRESHNESS_EXPLICIT_V1"

# Deliberate, normalized factors. Required/progress have more weight than ease.
WEIGHTS: Mapping[str, int] = {
    "required": 25, "progress": 25, "unlock": 15,
    "fit": 20, "readiness": 10, "workload": 5,
}
assert sum(WEIGHTS.values()) == 100


@dataclass(frozen=True)
class GradePolicy:
    institution_id: str
    study_plan_id: str
    version: str
    provenance: str
    numeric_min: Decimal
    numeric_max: Decimal

    def applies_to(self, study_plan_id: str) -> bool:
        return self.study_plan_id == "*" or self.study_plan_id == study_plan_id

    def normalize(self, record: StudentCourseAttemptRecord) -> int | None:
        reference = parse_grading_policy_source_reference(record.performance_source_reference)
        if (record.performance_provenance is not PerformanceProvenance.OFFICIAL_VERIFIED
                or record.performance_verification_state is not PerformanceVerificationState.VERIFIED
                or record.raw_numeric_grade is None
                or reference is None
                or reference.university_id != self.institution_id
                or reference.version != self.version):
            return None
        value = record.raw_numeric_grade
        if (not value.is_finite() or self.numeric_max <= self.numeric_min
                or not self.numeric_min <= value <= self.numeric_max):
            return None
        return round((value - self.numeric_min) * 100 / (self.numeric_max - self.numeric_min))


@dataclass(frozen=True)
class GradePolicyRegistry:
    """Explicit governed policies keyed by the exact institution and study plan."""

    policies: tuple[GradePolicy, ...] = ()

    def __post_init__(self) -> None:
        scopes: set[tuple[str, str]] = set()
        for policy in self.policies:
            scope = (policy.institution_id, policy.study_plan_id)
            if scope in scopes:
                raise ValueError(f"Duplicate grade policy scope: {scope!r}")
            if (not policy.version.strip() or not policy.provenance.strip()
                    or not policy.numeric_min.is_finite()
                    or not policy.numeric_max.is_finite()
                    or policy.numeric_max <= policy.numeric_min):
                raise ValueError(f"Invalid grade policy contract: {scope!r}")
            if policy.version not in SUPPORTED_POLICY_VERSIONS:
                raise ValueError(f"Unsupported grade policy contract: {scope!r}")
            if (policy.version == FAKE_UNIVERSITY_GRADING_POLICY_VERSION
                    and (policy.numeric_min != FAKE_UNIVERSITY_COURSE_GRADE_MIN
                         or policy.numeric_max != FAKE_UNIVERSITY_COURSE_GRADE_MAX)):
                raise ValueError(f"Unsupported grade policy contract: {scope!r}")
            scopes.add(scope)

    def resolve(self, institution_id: str, study_plan_id: str) -> GradePolicy | None:
        exact = next((policy for policy in self.policies
                      if policy.institution_id == institution_id
                      and policy.study_plan_id == study_plan_id), None)
        return exact or next((policy for policy in self.policies
                              if policy.institution_id == institution_id
                              and policy.study_plan_id == "*"), None)


FAKE_UNIVERSITY_GRADING_POLICY_V1 = GradePolicy(
    institution_id="10000000-0000-0000-0000-000000000001",
    study_plan_id=PLAN12_ID,
    version=FAKE_UNIVERSITY_GRADING_POLICY_VERSION,
    provenance="AUTHORITATIVE_FAKE_UNIVERSITY_GRADING_CONTRACT",
    numeric_min=Decimal("0"),
    numeric_max=Decimal("100"),
)

FAKE_UNIVERSITY_INSTITUTION_GRADING_POLICY_V1 = GradePolicy(
    institution_id="10000000-0000-0000-0000-000000000001",
    study_plan_id="*",
    version=FAKE_UNIVERSITY_GRADING_POLICY_VERSION,
    provenance="AUTHORITATIVE_FAKE_UNIVERSITY_GRADING_CONTRACT",
    numeric_min=Decimal("0"),
    numeric_max=Decimal("100"),
)

# Backward-compatible import name for the uncommitted V2 test tree.
FAKE_UNIVERSITY_GRADE_POLICY_V1 = FAKE_UNIVERSITY_GRADING_POLICY_V1


@dataclass(frozen=True)
class SkillEvidence:
    skill_id: str
    mastery_score: int | None
    evidence_count: int
    confidence: str
    contributing_courses: tuple[str, ...]
    version: str = MASTERY_MODEL_VERSION


@dataclass(frozen=True)
class AcademicIntelligenceProfile:
    student_id: str
    institution_id: str
    study_plan_id: str
    generated_at: datetime
    source_snapshot_version: str
    cumulative_gpa: Decimal | None
    gpa_scale: Decimal | None
    gpa_provenance: str
    grade_scale_version: str | None
    grade_scale_provenance: str
    earned_completed_credits: Decimal
    completed_courses: tuple[str, ...]
    failed_courses: tuple[str, ...]
    repeated_courses: tuple[str, ...]
    strong_courses: tuple[str, ...]
    weak_courses: tuple[str, ...]
    academic_stage: str
    skills: tuple[SkillEvidence, ...]
    freshness: str


@dataclass(frozen=True)
class CourseSkillProfile:
    course_code: str
    skills: tuple[str, ...]
    provenance: str
    version: str = SKILL_PROFILE_VERSION


@dataclass(frozen=True)
class GeneralDifficulty:
    score: int
    level: str
    provenance: str
    model_version: str = GENERAL_MODEL_VERSION


@dataclass(frozen=True)
class PersonalizedDifficulty:
    score: int
    level: str
    confidence: str
    provenance: str
    reason_codes: tuple[str, ...]
    contributing_skills: tuple[str, ...]
    risk_factors: tuple[str, ...]
    model_version: str = PERSONAL_MODEL_VERSION


@dataclass(frozen=True)
class CourseDifficulty:
    course_code: str
    course_name_ar: str | None
    general: GeneralDifficulty
    personalized: PersonalizedDifficulty
    skill_profile: CourseSkillProfile


@dataclass(frozen=True)
class AdaptiveRecommendation:
    course_code: str
    rank: int
    recommendation_score: int
    eligible: bool
    general_difficulty: GeneralDifficulty
    personalized_difficulty: PersonalizedDifficulty
    fit_score: int
    progress_value: int
    prerequisite_readiness: int
    workload_risk: int
    confidence: str
    key_strengths: tuple[str, ...]
    risk_factors: tuple[str, ...]
    deterministic_reasons: tuple[str, ...]
    factor_scores: tuple[tuple[str, int], ...]
    trace_version: str = RECOMMENDER_MODEL_VERSION


@dataclass(frozen=True)
class AdaptiveCourseResult:
    profile: AcademicIntelligenceProfile
    courses: tuple[CourseDifficulty, ...]
    recommendations: tuple[AdaptiveRecommendation, ...]
    eligible_set_version: str
    model_version: str
    weights: Mapping[str, int]
    limitations: tuple[str, ...]


def _level(score: int) -> str:
    return ("VERY_EASY" if score < 20 else "EASY" if score < 40 else
            "MODERATE" if score < 60 else "HARD" if score < 80 else "VERY_HARD")


def _skills(code: str, plan_id: str) -> CourseSkillProfile:
    mapping = DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(plan_id)
    definition = mapping.courses.get(code) if mapping else None
    domain = tuple(item.skill_id.value for item in definition.skills) if definition else ()
    return CourseSkillProfile(code, (f"COURSE:{code}", *domain),
                              "MODELED_CURRICULUM_CODE_MAPPING" if domain else "MODELED_FALLBACK")


def evaluate_general_course_difficulty(course_code: str, credit_hours: Decimal,
                                       eligibility_catalog: CanTakeCatalog) -> GeneralDifficulty:
    """Return the existing structural difficulty model for one canonical course."""
    rules = {rule.course_code: rule for rule in eligibility_catalog.plan_courses}
    if course_code not in rules:
        raise ValueError("Course is outside the eligibility catalog")

    def depth(code: str, visited: frozenset[str] = frozenset()) -> int:
        if code in visited or len(visited) > 8:
            return 0
        rule = rules[code]
        if rule.prerequisite_logic_status is not PrerequisiteLogicStatus.VERIFIED:
            return 0
        options = [option for group in rule.dependency_groups
                   for option in group.option_course_codes if option in rules]
        return 1 + min(5, max((depth(option, visited | {code}) for option in options), default=0))

    rule = rules[course_code]
    options = {option for group in rule.dependency_groups for option in group.option_course_codes}
    structured = rule.prerequisite_logic_status in {
        PrerequisiteLogicStatus.VERIFIED, PrerequisiteLogicStatus.NOT_APPLICABLE}
    score = max(0, min(100, 38 + min(25, round(float(credit_hours) * 5))
                       + min(20, len(options) * 6) + min(20, depth(course_code) * 4)))
    return GeneralDifficulty(score, _level(score),
                             "MODEL_BASED" if structured else "MODELED_FALLBACK")


def _snapshot_version(state: StudentAcademicState, records: tuple[StudentCourseAttemptRecord, ...],
                      institution_id: str) -> str:
    parts = [institution_id, state.profile_id, state.study_plan_id, str(state.updated_at),
             str(state.reported_cumulative_gpa), str(state.reported_gpa_scale),
             str(state.reported_earned_credit_hours),
             *sorted(f"{item.course_code}:{item.outcome.value}" for item in state.attempts),
             *sorted(f"{row.attempt_id}:{row.updated_at}:{row.outcome.value}:{row.raw_numeric_grade}:"
                     f"{row.performance_provenance.value}:{row.performance_verification_state.value}:"
                     f"{row.performance_source_reference or ''}" for row in records)]
    return sha256("|".join(parts).encode()).hexdigest()


def build_adaptive_courses(state: StudentAcademicState, institution_id: str,
                           progress_catalog: AcademicProgressCatalog,
                           eligibility_catalog: CanTakeCatalog,
                           progress: AcademicProgress,
                           recommendations: RecommendationResult,
                           records: tuple[StudentCourseAttemptRecord, ...], *,
                           generated_at: datetime | None = None,
                           grade_policy: GradePolicy | None = None,
                           fused_skill_scores: Mapping[str, int] | None = None,
                           source_fresh_until: datetime | None = None) -> AdaptiveCourseResult:
    if (not institution_id or state.study_plan_id != progress_catalog.study_plan.study_plan_id
            or state.study_plan_id != eligibility_catalog.study_plan_id
            or state.study_plan_id != progress.study_plan_id
            or state.study_plan_id != recommendations.study_plan_id
            or (grade_policy is not None and (grade_policy.institution_id != institution_id
                                              or not grade_policy.applies_to(state.study_plan_id)))):
        raise ValueError("Adaptive intelligence scope mismatch")
    now = generated_at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Generation time must be timezone aware")
    if source_fresh_until is not None and (
            source_fresh_until.tzinfo is None or source_fresh_until.utcoffset() is None):
        raise ValueError("Freshness timestamp must be timezone aware")
    freshness = ("UNKNOWN" if source_fresh_until is None else
                 "FRESH" if now <= source_fresh_until else "STALE_INPUT")
    rules = {rule.course_code: rule for rule in eligibility_catalog.plan_courses}
    codes = {course.course_code for course in progress_catalog.plan_courses}
    if len(codes) != len(progress_catalog.plan_courses) or codes - rules.keys():
        raise ValueError("Incomplete canonical course rules")
    normalized: dict[str, list[tuple[tuple[object, ...], int]]] = {}
    seen: dict[str, int] = {}
    failed: set[str] = set()
    for record in records:
        if record.profile_id != state.profile_id:
            raise ValueError("Cross-student attempt evidence")
        seen[record.course_code] = seen.get(record.course_code, 0) + 1
        if record.outcome.value == "FAILED":
            failed.add(record.course_code)
        grade = grade_policy.normalize(record) if grade_policy else None
        if grade is not None:
            chronological_key = (
                record.attempted_on or record.created_at.date(), record.raw_academic_year or "",
                record.raw_term or "", record.attempt_sequence or 0, record.updated_at,
                record.attempt_id,
            )
            normalized.setdefault(record.course_code, []).append((chronological_key, grade))
    latest_grade = {code: sorted(values, key=lambda item: item[0])[-1][1]
                    for code, values in normalized.items()}
    completed = tuple(sorted(course.course_code for course in progress.courses
                             if course.state.value == "COMPLETED"))
    strong = tuple(sorted(code for code, grade in latest_grade.items() if grade >= 80))
    weak = tuple(sorted(code for code, grade in latest_grade.items() if grade < 60))
    repeated = tuple(sorted(code for code, count in seen.items() if count > 1))
    profiles = {code: _skills(code, state.study_plan_id) for code in codes}
    skill_grades: dict[str, list[tuple[str, int]]] = {}
    for code, grade in latest_grade.items():
        if code in profiles:
            for skill in profiles[code].skills:
                skill_grades.setdefault(skill, []).append((code, grade))
    skill_evidence = tuple(SkillEvidence(
        skill, round(sum(value for _, value in values) / len(values)), len(values),
        "HIGH" if len(values) >= 3 else "MEDIUM" if len(values) == 2 else "LOW",
        tuple(sorted(code for code, _ in values)),
    ) for skill, values in sorted(skill_grades.items()))
    mastery = {item.skill_id: item for item in skill_evidence}
    fused_skill_scores = dict(fused_skill_scores or {})
    profile = AcademicIntelligenceProfile(
        state.profile_id, institution_id, state.study_plan_id, now,
        _snapshot_version(state, records, institution_id), state.reported_cumulative_gpa,
        state.reported_gpa_scale, "REPORTED_NOT_RECALCULATED",
        grade_policy.version if grade_policy else None,
        grade_policy.provenance if grade_policy else "UNVERIFIED_GRADE_SCALE",
        passed_plan_credits(progress), completed, tuple(sorted(failed)), repeated,
        strong, weak, "UNKNOWN_NO_CANONICAL_PERIOD_ORDER", skill_evidence, freshness,
    )

    course_rows: list[CourseDifficulty] = []
    for course in sorted(progress_catalog.plan_courses, key=lambda item: (item.display_order, item.course_code)):
        rule = rules[course.course_code]
        options = {option for group in rule.dependency_groups for option in group.option_course_codes}
        general = evaluate_general_course_difficulty(
            course.course_code, course.credit_hours, eligibility_catalog)
        general_score = general.score
        relevant = tuple(sorted(skill for skill in profiles[course.course_code].skills
                                if not skill.startswith("COURSE:")
                                and (skill in mastery or skill in fused_skill_scores)))
        values = [fused_skill_scores.get(skill, mastery[skill].mastery_score if skill in mastery else None)
                  for skill in relevant]
        values = [value for value in values if value is not None]
        risk = tuple(sorted({"RELATED_FAILED_ATTEMPT" for option in options if option in failed}
                            | {"REPEATED_RELATED_COURSE" for option in options if option in repeated}))
        if values:
            adjustment = round((70 - sum(values) / len(values)) * 0.65)
            score = max(0, min(100, general_score + adjustment + len(risk) * 7))
            evidence_count = sum(mastery[skill].evidence_count for skill in relevant if skill in mastery)
            confidence = "LOW" if freshness != "FRESH" else (
                "HIGH" if evidence_count >= 3
                else "MEDIUM" if len(relevant) >= 2 else "LOW")
            reasons = (("RELEVANT_VERIFIED_PERFORMANCE",) if evidence_count else
                       ("COMPLETED_DIAGNOSTIC_BASELINE",))
            if fused_skill_scores:
                reasons += ("STUDENT_INTELLIGENCE_V2_FUSION",)
            provenance = ("MODELED_FUSED_STUDENT_INTELLIGENCE_V2" if fused_skill_scores else
                          "MODELED_VERIFIED_GRADE_AND_CURRICULUM_EVIDENCE")
        else:
            score = max(0, min(100, general_score + len(risk) * 7))
            confidence = "LOW"
            reasons = ("INSUFFICIENT_VERIFIED_GRADE_EVIDENCE",)
            if grade_policy is None:
                reasons += ("UNVERIFIED_GRADE_SCALE",)
            provenance = "MODELED_STRUCTURAL_FALLBACK_NO_GRADE_MASTERY"
        if freshness != "FRESH":
            reasons += ("STALE_INPUT" if freshness == "STALE_INPUT" else "UNKNOWN_SOURCE_FRESHNESS",)
        personal = PersonalizedDifficulty(score, _level(score), confidence, provenance, reasons,
                                          relevant, risk)
        course_rows.append(CourseDifficulty(course.course_code, rule.target_name_ar,
                                            general, personal, profiles[course.course_code]))
    by_code = {item.course_code: item for item in course_rows}
    ranked: list[AdaptiveRecommendation] = []
    for base in recommendations.ranked_recommendations:
        if base.eligibility_decision != "ELIGIBLE" or base.course_code not in by_code:
            raise ValueError("Adaptive rank received an ineligible or foreign course")
        difficulty = by_code[base.course_code]
        fit = (100 - difficulty.personalized.score
               if ({"RELEVANT_VERIFIED_PERFORMANCE", "COMPLETED_DIAGNOSTIC_BASELINE"}
                   & set(difficulty.personalized.reason_codes)) else 50)
        progress_value = min(100, round(float(base.effective_credit_contribution) * 25)
                             + (25 if base.completes_requirement_group else 0))
        readiness = 100 if not difficulty.personalized.risk_factors else 60
        workload_risk = min(100, difficulty.personalized.score + max(0, round(float(base.credit_hours) - 3)) * 10)
        factors = {"required": 100 if base.requirement_type == "required" else 35,
                   "progress": progress_value,
                   "unlock": min(100, base.newly_eligible_count * 35),
                   "fit": fit, "readiness": readiness,
                   "workload": 100 - workload_risk}
        score = round(sum(factors[key] * weight for key, weight in WEIGHTS.items()) / 100)
        ranked.append(AdaptiveRecommendation(
            base.course_code, 0, score, True, difficulty.general,
            difficulty.personalized, fit, progress_value, readiness, workload_risk,
            difficulty.personalized.confidence,
            tuple(skill for skill in difficulty.personalized.contributing_skills
                  if ((fused_skill_scores.get(skill) if skill in fused_skill_scores else
                       mastery[skill].mastery_score if skill in mastery else None) or 0) >= 80),
            difficulty.personalized.risk_factors,
            tuple(reason.value for reason in base.reason_codes),
            tuple((key, factors[key]) for key in WEIGHTS),
        ))
    ranked.sort(key=lambda item: (-item.recommendation_score, item.course_code))
    from dataclasses import replace
    ranked = [replace(item, rank=index) for index, item in enumerate(ranked, 1)]
    eligible_set_version = sha256((recommendations.recommendation_policy_version + "|" +
                                  "|".join(sorted(item.course_code for item in ranked))).encode()).hexdigest()
    return AdaptiveCourseResult(profile, tuple(course_rows), tuple(ranked),
                                eligible_set_version,
                                RECOMMENDER_MODEL_VERSION, dict(WEIGHTS),
                                ("Modeled scoring, not trained outcome prediction or registration approval.",
                                 "Unverified or unscaled grades never create mastery scores.",
                                 "Missing freshness evidence lowers personalization confidence."))
