"""Deterministic Student Intelligence Profile V2 evidence fusion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Mapping

from app.rules.models import AttemptOutcome
from app.student.models import (PerformanceProvenance, PerformanceVerificationState,
                                StudentAcademicState, StudentCourseAttemptRecord)
from app.student_intelligence.adaptive import GradePolicy
from app.student_intelligence.diagnostic import DiagnosticDomain, DiagnosticDomainResult
from app.student_intelligence.taxonomy import (PLAN12_COURSE_SKILLS, TAXONOMY_VERSION,
                                                SkillId)

INTELLIGENCE_MODEL_VERSION = "STUDENT_INTELLIGENCE_PROFILE_V2"
FUSION_POLICY_VERSION = "EVIDENCE_FUSION_V1"
COLD_START_POLICY_VERSION = "COLD_START_POLICY_V1"


@dataclass(frozen=True)
class SkillDimensionV2:
    skill_id: str
    score: int | None
    confidence: str
    evidence_quality: str
    university_evidence_count: int
    diagnostic_evidence_count: int
    contributing_courses: tuple[str, ...]
    contributing_question_domains: tuple[str, ...]
    source_types: tuple[str, ...]
    reason_codes: tuple[str, ...]
    reasoning_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class StudentIntelligenceProfileV2:
    student_id: str
    institution_id: str
    study_plan_id: str
    intelligence_model_version: str
    taxonomy_version: str
    fusion_policy_version: str
    generated_at: datetime
    source_snapshot_version: str
    cumulative_gpa: Decimal | None
    gpa_scale: Decimal | None
    earned_credits: Decimal
    verified_grade_count: int
    completed_course_count: int
    failed_course_count: int
    repeated_course_count: int
    current_course_count: int
    academic_progress_band: str
    performance_trend: str
    evidence_quality: str
    cold_start_status: str
    diagnostic_recommended: bool
    diagnostic_completed: bool
    latest_assessment_version: str | None
    latest_completed_at: datetime | None
    skills: tuple[SkillDimensionV2, ...]
    strengths: tuple[str, ...]
    development_areas: tuple[str, ...]
    preferences: Mapping[str, object]
    limitations: tuple[str, ...]


DIAGNOSTIC_SKILL_BRIDGE: Mapping[DiagnosticDomain, tuple[SkillId, ...]] = {
    DiagnosticDomain.PROGRAMMING_REASONING: (SkillId.PROGRAMMING, SkillId.PYTHON,
                                               SkillId.OBJECT_ORIENTED_PROGRAMMING),
    DiagnosticDomain.LOGICAL_PROBLEM_SOLVING: (SkillId.LOGICAL_REASONING, SkillId.ALGORITHMS,
                                                SkillId.DISCRETE_MATH),
    DiagnosticDomain.QUANTITATIVE_MATH: (SkillId.QUANTITATIVE_MATH, SkillId.LINEAR_ALGEBRA),
    DiagnosticDomain.STATISTICS_DATA_REASONING: (SkillId.STATISTICS, SkillId.DATA_ANALYSIS),
    DiagnosticDomain.THEORY_CONCEPTUAL_UNDERSTANDING: (SkillId.THEORY_COMPREHENSION,
                                                       SkillId.MEMORIZATION),
}


def _order(record: StudentCourseAttemptRecord) -> tuple[object, ...]:
    return (record.attempted_on or record.created_at.date(), record.raw_academic_year or "",
            record.raw_term or "", record.attempt_sequence or 0, record.updated_at, record.attempt_id)


def _snapshot(state: StudentAcademicState, institution_id: str,
              records: tuple[StudentCourseAttemptRecord, ...], diagnostic_version: str | None,
              diagnostic_completed_at: datetime | None) -> str:
    values = [institution_id, state.profile_id, state.study_plan_id, str(state.updated_at),
              str(state.reported_cumulative_gpa), str(state.reported_gpa_scale),
              str(state.reported_earned_credit_hours), diagnostic_version or "",
              str(diagnostic_completed_at or "")]
    values.extend(f"{r.attempt_id}:{r.updated_at}:{r.raw_numeric_grade}:{r.outcome.value}:"
                  f"{r.performance_provenance.value}:{r.performance_verification_state.value}:"
                  f"{r.performance_source_reference or ''}"
                  for r in sorted(records, key=_order))
    return sha256("|".join(values).encode()).hexdigest()


def build_student_intelligence_profile_v2(
    state: StudentAcademicState,
    institution_id: str,
    records: tuple[StudentCourseAttemptRecord, ...],
    grade_policy: GradePolicy | None,
    *,
    diagnostic_results: tuple[DiagnosticDomainResult, ...] = (),
    diagnostic_version: str | None = None,
    diagnostic_completed_at: datetime | None = None,
    preferences: Mapping[str, object] | None = None,
    generated_at: datetime | None = None,
) -> StudentIntelligenceProfileV2:
    if grade_policy and (grade_policy.institution_id != institution_id
                         or grade_policy.study_plan_id != state.study_plan_id):
        raise ValueError("Grade policy scope mismatch")
    for record in records:
        if record.profile_id != state.profile_id:
            raise ValueError("Cross-student performance evidence")
    now = generated_at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("generated_at must be timezone aware")

    histories: dict[str, list[StudentCourseAttemptRecord]] = {}
    verified_count = 0
    for record in sorted(records, key=_order):
        histories.setdefault(record.course_code, []).append(record)
        if grade_policy and grade_policy.normalize(record) is not None:
            verified_count += 1
    latest = {code: rows[-1] for code, rows in histories.items()}
    university: dict[SkillId, list[tuple[str, int, float]]] = {}
    chronological_scores: list[tuple[tuple[object, ...], int]] = []
    for code, record in latest.items():
        normalized = grade_policy.normalize(record) if grade_policy else None
        definition = PLAN12_COURSE_SKILLS.get(code)
        if normalized is None or definition is None:
            continue
        chronological_scores.append((_order(record), normalized))
        for weighted in definition.skills:
            university.setdefault(weighted.skill_id, []).append((code, normalized, weighted.weight))

    diagnostic: dict[SkillId, list[DiagnosticDomainResult]] = {}
    for result in diagnostic_results:
        for skill in DIAGNOSTIC_SKILL_BRIDGE[result.domain]:
            diagnostic.setdefault(skill, []).append(result)

    all_skills = sorted(set(university) | set(diagnostic), key=lambda item: item.value)
    dimensions: list[SkillDimensionV2] = []
    for skill in all_skills:
        university_rows = university.get(skill, [])
        diagnostic_rows = diagnostic.get(skill, [])
        university_score = (round(sum(score * weight for _, score, weight in university_rows)
                                  / sum(weight for _, _, weight in university_rows))
                            if university_rows else None)
        diagnostic_score = (round(sum(row.score for row in diagnostic_rows) / len(diagnostic_rows))
                            if diagnostic_rows else None)
        reasons: list[str] = []
        if university_score is None:
            score = diagnostic_score
            if score is not None:
                reasons.append("DIAGNOSTIC_BASELINE_ONLY")
        elif diagnostic_score is None:
            score = university_score
            reasons.append("OFFICIAL_VERIFIED_UNIVERSITY_ONLY")
        else:
            university_weight = .7 if len(university_rows) <= 2 else .9
            score = round(university_score * university_weight + diagnostic_score * (1 - university_weight))
            reasons.append("OFFICIAL_EVIDENCE_DOMINANT")
            reasons.append("DIAGNOSTIC_RETAINED_AS_BASELINE")
        sources = tuple(source for source, present in (
            ("OFFICIAL_VERIFIED_UNIVERSITY_PERFORMANCE", bool(university_rows)),
            ("COMPLETED_QUICK_DIAGNOSTIC", bool(diagnostic_rows))) if present)
        if len(university_rows) >= 3:
            confidence, quality = "HIGH", "AUTHORITATIVE"
        elif university_rows:
            confidence, quality = ("MEDIUM" if len(university_rows) == 2 else "LOW"), "AUTHORITATIVE_LIMITED"
        elif diagnostic_rows:
            confidence = min((row.confidence for row in diagnostic_rows),
                             key=lambda value: {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[value])
            quality = "MODELED_DIAGNOSTIC"
        else:
            confidence, quality = "LOW", "INSUFFICIENT"
        dimensions.append(SkillDimensionV2(
            skill.value, score, confidence, quality, len(university_rows), len(diagnostic_rows),
            tuple(sorted(code for code, _, _ in university_rows)),
            tuple(sorted({row.domain.value for row in diagnostic_rows})), sources, tuple(reasons),
            tuple(sorted({pattern for row in diagnostic_rows for pattern in row.reasoning_patterns}))))

    covered = sum(bool(rows) for rows in university.values())
    if verified_count == 0:
        cold_start = "COLD_START_NO_PERFORMANCE_EVIDENCE"
    elif verified_count < 4 or covered < 5:
        cold_start = "LOW_ACADEMIC_EVIDENCE"
    else:
        cold_start = "ESTABLISHED_ACADEMIC_EVIDENCE"
    earned = state.reported_earned_credit_hours or Decimal("0")
    progress_band = "NEW" if earned == 0 else "EARLY" if earned < 36 else "MID" if earned < 90 else "ADVANCED"
    trend = "INSUFFICIENT_EVIDENCE"
    if len(chronological_scores) >= 4:
        ordered = [score for _, score in sorted(chronological_scores)]
        midpoint = len(ordered) // 2
        delta = sum(ordered[midpoint:]) / len(ordered[midpoint:]) - sum(ordered[:midpoint]) / midpoint
        trend = "IMPROVING" if delta >= 5 else "DECLINING" if delta <= -5 else "STABLE"
    strengths = tuple(row.skill_id for row in dimensions if row.score is not None and row.score >= 75
                      and row.confidence != "LOW")
    development = tuple(row.skill_id for row in dimensions if row.score is not None and row.score < 60)
    completed = {code for code, row in latest.items() if row.outcome is AttemptOutcome.PASSED}
    failed = {code for code, rows in histories.items() if any(r.outcome is AttemptOutcome.FAILED for r in rows)}
    current = {attempt.course_code for attempt in state.attempts if attempt.outcome is AttemptOutcome.IN_PROGRESS}
    repeated = {code for code, rows in histories.items() if len(rows) > 1}
    limitations = [
        "Modeled intelligence is not an official university evaluation.",
        "Diagnostic and preferences never change eligibility, prerequisites, progress, or graduation truth.",
        "User-stated preferences are kept separate and never increase mastery.",
    ]
    if grade_policy is None:
        limitations.append(
            "official_grade_mastery=UNAVAILABLE_UNVERIFIED_POLICY; an explicit institution/plan "
            "grade policy is required."
        )
    return StudentIntelligenceProfileV2(
        state.profile_id, institution_id, state.study_plan_id, INTELLIGENCE_MODEL_VERSION,
        TAXONOMY_VERSION, FUSION_POLICY_VERSION, now,
        _snapshot(state, institution_id, records, diagnostic_version, diagnostic_completed_at),
        state.reported_cumulative_gpa, state.reported_gpa_scale, earned, verified_count,
        len(completed), len(failed), len(repeated), len(current), progress_band, trend,
        "AUTHORITATIVE" if verified_count >= 4 else "MIXED_OR_LIMITED" if verified_count or diagnostic_results else "INSUFFICIENT",
        cold_start, cold_start != "ESTABLISHED_ACADEMIC_EVIDENCE" and not diagnostic_results,
        bool(diagnostic_results), diagnostic_version, diagnostic_completed_at,
        tuple(dimensions), strengths, development, dict(preferences or {}), tuple(limitations))
