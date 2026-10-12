"""Versioned, deterministic Plan 12 workload estimates; never LLM classified."""

from dataclasses import dataclass

from app.student_intelligence.taxonomy import PLAN12_COURSE_SKILLS, PLAN12_ID, SkillId

MODEL_VERSION = "MODELED_COURSE_LOAD_PROFILE_V1"
MAX_MEMORIZATION_HEAVY = 2
MEMORIZATION_HEAVY_THRESHOLD = 70

@dataclass(frozen=True)
class CourseLearningProfile:
    course_code: str
    memorization_score: int | None
    primary_type: str
    provenance: str
    version: str = MODEL_VERSION

    @property
    def memorization_heavy(self) -> bool:
        return self.memorization_score is not None and self.memorization_score >= MEMORIZATION_HEAVY_THRESHOLD


def resolve_learning_profile(code: str, *, plan_id: str) -> CourseLearningProfile:
    if plan_id != PLAN12_ID or code not in PLAN12_COURSE_SKILLS:
        return CourseLearningProfile(code, None, "UNKNOWN", "MODELED_FALLBACK")
    skills = {item.skill_id: item.weight for item in PLAN12_COURSE_SKILLS[code].skills}
    if skills.get(SkillId.MEMORIZATION, 0) >= .7:
        return CourseLearningProfile(code, 80, "MEMORIZATION", "CURATED_PLAN12_CODE_MAPPING")
    if skills.get(SkillId.PRACTICAL_LAB, 0) >= .7 or skills.get(SkillId.PROJECT_WORK, 0) >= .8:
        return CourseLearningProfile(code, 10, "LAB_OR_PROJECT", "CURATED_PLAN12_CODE_MAPPING")
    if skills.get(SkillId.QUANTITATIVE_MATH, 0) >= .7 or skills.get(SkillId.LOGICAL_REASONING, 0) >= .8:
        return CourseLearningProfile(code, 30, "ANALYTICAL", "CURATED_PLAN12_CODE_MAPPING")
    return CourseLearningProfile(code, 45, "THEORY_OR_MIXED", "CURATED_PLAN12_CODE_MAPPING")
