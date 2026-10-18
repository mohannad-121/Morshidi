"""Explicit, versioned curriculum-to-skill mapping registry.

Only the owner-approved Artificial Intelligence Plan 12 mapping exists today.
Unknown curricula never inherit it through shared course codes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.student_intelligence.multi_major import MULTI_MAJOR_DEFINITIONS
from app.student_intelligence.taxonomy import (
    COURSE_SKILL_MAPPING_VERSION,
    NURSING_COURSE_SKILL_MAPPING_VERSION,
    NURSING_PLAN12_COURSE_SKILLS,
    NURSING_PLAN12_ID,
    PLAN12_COURSE_SKILLS,
    PLAN12_ID,
    SE_COURSE_SKILL_MAPPING_VERSION,
    SE_PLAN12_COURSE_SKILLS,
    SE_PLAN12_ID,
    CourseSkillDefinition,
)


class UnsupportedCurriculumIntelligenceError(ValueError):
    """The curriculum has no governed discipline-specific intelligence mapping."""


@dataclass(frozen=True, slots=True)
class CurriculumSkillMapping:
    study_plan_id: str
    version: str
    courses: Mapping[str, CourseSkillDefinition]


@dataclass(frozen=True, slots=True)
class CurriculumSkillMappingRegistry:
    mappings: tuple[CurriculumSkillMapping, ...]

    def __post_init__(self) -> None:
        plan_ids = [mapping.study_plan_id for mapping in self.mappings]
        if len(plan_ids) != len(set(plan_ids)):
            raise ValueError("Duplicate curriculum skill mapping")

    def resolve(self, study_plan_id: str) -> CurriculumSkillMapping | None:
        return next((item for item in self.mappings if item.study_plan_id == study_plan_id), None)


AI_PLAN12_SKILL_MAPPING = CurriculumSkillMapping(
    study_plan_id=PLAN12_ID,
    version=COURSE_SKILL_MAPPING_VERSION,
    courses=PLAN12_COURSE_SKILLS,
)

NURSING_PLAN12_SKILL_MAPPING = CurriculumSkillMapping(
    study_plan_id=NURSING_PLAN12_ID,
    version=NURSING_COURSE_SKILL_MAPPING_VERSION,
    courses=NURSING_PLAN12_COURSE_SKILLS,
)

SE_PLAN12_SKILL_MAPPING = CurriculumSkillMapping(
    study_plan_id=SE_PLAN12_ID,
    version=SE_COURSE_SKILL_MAPPING_VERSION,
    courses=SE_PLAN12_COURSE_SKILLS,
)

MULTI_MAJOR_SKILL_MAPPINGS = tuple(
    CurriculumSkillMapping(
        study_plan_id=definition.study_plan_id,
        version=definition.mapping_version,
        courses=definition.course_skills,
    )
    for definition in MULTI_MAJOR_DEFINITIONS
)

DEFAULT_CURRICULUM_SKILL_MAPPINGS = CurriculumSkillMappingRegistry((
    AI_PLAN12_SKILL_MAPPING,
    NURSING_PLAN12_SKILL_MAPPING,
    SE_PLAN12_SKILL_MAPPING,
    *MULTI_MAJOR_SKILL_MAPPINGS,
))

