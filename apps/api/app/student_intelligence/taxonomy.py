"""Versioned Morshidi curriculum classification for the supported Plan 12 catalog.

These mappings are modeled product metadata, not institutional learning outcomes.
Runtime course-name inference is intentionally forbidden.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

PLAN12_ID = "10000000-0000-0000-0000-000000000005"
TAXONOMY_VERSION = "MORSHIDI_SKILL_TAXONOMY_V2"
COURSE_SKILL_MAPPING_VERSION = "PLAN12_COURSE_SKILLS_V2"

# Exact supported course-code contract copied from the canonical active Plan 12
# seed. Keeping this separate from the definitions prevents duplicate keys or a
# substituted course from passing a count-only check.
SUPPORTED_PLAN12_COURSE_CODES = frozenset({
    "0200104", "0200105", "0200106", "0200110", "0200111", "0200113",
    "0200114", "0200115", "0200122", "0200125", "0200127", "0200130",
    "0200153", "0200154", "0200156", "0200215", "0300101", "0300104",
    "0300123", "0300124", "0300153", "0300154", "0300155", "0300157",
    "0300161", "0300220", "0301245", "0400202", "1501110", "1501111",
    "1501112", "1501113", "1501212", "1501221", "1501222", "1501321",
    "1501340", "1501360", "1501385", "1501430", "1503270", "1505101",
    "1505201", "1505211", "1505223", "1505303", "1505311", "1505320",
    "1505333", "1505351", "1505365", "1505366", "1505367", "1505381",
    "1505414", "1505415", "1505435", "1505436", "1505441", "1505461",
    "1505467", "1505468", "1505480", "1505482", "1506180", "1506181",
    "1506493", "1509999",
})


class SkillId(str, Enum):
    PROGRAMMING = "PROGRAMMING"
    PYTHON = "PYTHON"
    OBJECT_ORIENTED_PROGRAMMING = "OBJECT_ORIENTED_PROGRAMMING"
    DATA_STRUCTURES = "DATA_STRUCTURES"
    ALGORITHMS = "ALGORITHMS"
    LOGICAL_REASONING = "LOGICAL_REASONING"
    DISCRETE_MATH = "DISCRETE_MATH"
    QUANTITATIVE_MATH = "QUANTITATIVE_MATH"
    LINEAR_ALGEBRA = "LINEAR_ALGEBRA"
    STATISTICS = "STATISTICS"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    DATABASES = "DATABASES"
    SOFTWARE_ENGINEERING = "SOFTWARE_ENGINEERING"
    WEB_DEVELOPMENT = "WEB_DEVELOPMENT"
    AI_FOUNDATIONS = "AI_FOUNDATIONS"
    MACHINE_LEARNING = "MACHINE_LEARNING"
    DEEP_LEARNING = "DEEP_LEARNING"
    THEORY_COMPREHENSION = "THEORY_COMPREHENSION"
    MEMORIZATION = "MEMORIZATION"
    PRACTICAL_LAB = "PRACTICAL_LAB"
    PROJECT_WORK = "PROJECT_WORK"
    RESEARCH = "RESEARCH"
    COMMUNICATION = "COMMUNICATION"
    DIGITAL_LITERACY = "DIGITAL_LITERACY"
    SYSTEMS = "SYSTEMS"
    NETWORKS = "NETWORKS"
    COMPUTER_VISION = "COMPUTER_VISION"
    NATURAL_LANGUAGE_PROCESSING = "NATURAL_LANGUAGE_PROCESSING"
    ROBOTICS = "ROBOTICS"
    ETHICS = "ETHICS"


@dataclass(frozen=True)
class SkillWeight:
    skill_id: SkillId
    weight: float


@dataclass(frozen=True)
class CourseSkillDefinition:
    course_code: str
    skills: tuple[SkillWeight, ...]
    provenance: str = "MODELED_MORSHIDI_CURRICULUM_CLASSIFICATION"
    version: str = COURSE_SKILL_MAPPING_VERSION


def _d(code: str, *skills: tuple[SkillId, float]) -> CourseSkillDefinition:
    return CourseSkillDefinition(code, tuple(SkillWeight(skill, weight) for skill, weight in skills))


T = SkillId.THEORY_COMPREHENSION
M = SkillId.MEMORIZATION
P = SkillId.PROJECT_WORK
L = SkillId.PRACTICAL_LAB

# Deliberate coverage of all 68 active courses in the canonical Plan 12 seed.
_DEFINITIONS = (
    _d("0200104", (T, .8), (M, .8)), _d("0200105", (SkillId.COMMUNICATION, 1), (T, .6)),
    _d("0200106", (SkillId.COMMUNICATION, 1), (T, .6)), _d("0200110", (T, .8), (M, 1)),
    _d("0200111", (T, .9), (SkillId.ETHICS, .8), (M, .7)), _d("0200113", (T, .8), (M, 1)),
    _d("0200114", (T, .8), (M, 1)), _d("0200115", (P, .7), (SkillId.COMMUNICATION, .7)),
    _d("0200122", (T, 1), (M, .5)), _d("0200125", (T, .8), (M, 1)),
    _d("0200127", (SkillId.ETHICS, 1), (T, .8)), _d("0200130", (T, .8), (M, 1)),
    _d("0200153", (SkillId.COMMUNICATION, .8), (T, .6)), _d("0200154", (SkillId.COMMUNICATION, .8), (P, .6)),
    _d("0200156", (T, .8), (M, .7)), _d("0200215", (SkillId.COMMUNICATION, 1), (T, .5)),
    _d("0300101", (SkillId.QUANTITATIVE_MATH, 1), (SkillId.LOGICAL_REASONING, .6)),
    _d("0300104", (SkillId.STATISTICS, 1), (SkillId.QUANTITATIVE_MATH, .7), (SkillId.DATA_ANALYSIS, .6)),
    _d("0300123", (SkillId.QUANTITATIVE_MATH, .7), (T, .8)), _d("0300124", (T, 1), (M, .5)),
    _d("0300153", (SkillId.DIGITAL_LITERACY, 1), (T, .5)), _d("0300154", (SkillId.SYSTEMS, .7), (T, .8)),
    _d("0300155", (SkillId.LOGICAL_REASONING, 1), (L, .7)), _d("0300157", (SkillId.DIGITAL_LITERACY, 1), (T, .6)),
    _d("0300161", (T, .7), (M, .8)), _d("0300220", (SkillId.DISCRETE_MATH, 1), (SkillId.LOGICAL_REASONING, .9)),
    _d("0301245", (SkillId.LINEAR_ALGEBRA, 1), (SkillId.QUANTITATIVE_MATH, .8)),
    _d("0400202", (P, .8), (SkillId.COMMUNICATION, .7)),
    _d("1501110", (SkillId.PROGRAMMING, 1), (SkillId.LOGICAL_REASONING, .7)),
    _d("1501111", (SkillId.PROGRAMMING, 1), (L, 1)),
    _d("1501112", (SkillId.PROGRAMMING, 1), (SkillId.OBJECT_ORIENTED_PROGRAMMING, .9)),
    _d("1501113", (SkillId.PROGRAMMING, 1), (SkillId.OBJECT_ORIENTED_PROGRAMMING, .8), (L, 1)),
    _d("1501212", (SkillId.PROGRAMMING, .8), (P, 1)),
    _d("1501221", (SkillId.DATA_STRUCTURES, 1), (SkillId.ALGORITHMS, .8), (SkillId.PROGRAMMING, .7)),
    _d("1501222", (SkillId.DATABASES, 1), (P, .7)),
    _d("1501321", (SkillId.ALGORITHMS, 1), (SkillId.DATA_STRUCTURES, .8), (SkillId.LOGICAL_REASONING, .8)),
    _d("1501340", (SkillId.NETWORKS, 1), (SkillId.SYSTEMS, .7)),
    _d("1501360", (SkillId.RESEARCH, 1), (SkillId.ETHICS, .8), (P, .7)),
    _d("1501385", (SkillId.PROGRAMMING, .8), (P, 1)),
    _d("1501430", (SkillId.SYSTEMS, 1), (SkillId.PROGRAMMING, .5)),
    _d("1503270", (SkillId.SOFTWARE_ENGINEERING, 1), (P, .7)),
    _d("1505101", (SkillId.PYTHON, 1), (SkillId.PROGRAMMING, .9), (L, .6)),
    _d("1505201", (SkillId.AI_FOUNDATIONS, 1), (SkillId.LOGICAL_REASONING, .6), (T, .6)),
    _d("1505211", (SkillId.PROGRAMMING, 1), (SkillId.LOGICAL_REASONING, .7)),
    _d("1505223", (SkillId.AI_FOUNDATIONS, .9), (SkillId.PYTHON, .9), (P, .7)),
    _d("1505303", (SkillId.LOGICAL_REASONING, 1), (SkillId.AI_FOUNDATIONS, .7)),
    _d("1505311", (SkillId.MACHINE_LEARNING, 1), (SkillId.PYTHON, .7), (SkillId.STATISTICS, .7)),
    _d("1505320", (SkillId.MACHINE_LEARNING, 1), (SkillId.PYTHON, .7), (P, .7)),
    _d("1505333", (SkillId.DATA_ANALYSIS, 1), (SkillId.STATISTICS, .8), (SkillId.PYTHON, .7)),
    _d("1505351", (SkillId.AI_FOUNDATIONS, .7), (T, 1)),
    _d("1505365", (SkillId.DATA_ANALYSIS, .7), (SkillId.ALGORITHMS, .7), (SkillId.DATABASES, .6)),
    _d("1505366", (SkillId.COMPUTER_VISION, 1), (SkillId.PYTHON, .7), (SkillId.LINEAR_ALGEBRA, .6)),
    _d("1505367", (L, 1), (P, 1), (SkillId.COMMUNICATION, .5)),
    _d("1505381", (SkillId.ROBOTICS, 1), (SkillId.AI_FOUNDATIONS, .7)),
    _d("1505414", (SkillId.MACHINE_LEARNING, 1), (P, 1), (SkillId.PYTHON, .7)),
    _d("1505415", (SkillId.DEEP_LEARNING, 1), (SkillId.MACHINE_LEARNING, .8), (SkillId.PYTHON, .7)),
    _d("1505435", (SkillId.AI_FOUNDATIONS, .8), (T, .7), (P, .6)),
    _d("1505436", (SkillId.AI_FOUNDATIONS, .8), (T, .7), (P, .6)),
    _d("1505441", (SkillId.NATURAL_LANGUAGE_PROCESSING, 1), (SkillId.MACHINE_LEARNING, .8), (SkillId.PYTHON, .6)),
    _d("1505461", (SkillId.COMPUTER_VISION, 1), (SkillId.DEEP_LEARNING, .7), (SkillId.PYTHON, .6)),
    _d("1505467", (P, 1), (SkillId.RESEARCH, .7), (SkillId.SOFTWARE_ENGINEERING, .7)),
    _d("1505468", (P, 1), (SkillId.RESEARCH, .8), (SkillId.SOFTWARE_ENGINEERING, .8)),
    _d("1505480", (SkillId.DATA_ANALYSIS, 1), (SkillId.DATABASES, .8), (SkillId.SYSTEMS, .6)),
    _d("1505482", (SkillId.ROBOTICS, 1), (SkillId.PROGRAMMING, .8), (L, .7)),
    _d("1506180", (SkillId.WEB_DEVELOPMENT, 1), (SkillId.PROGRAMMING, .8)),
    _d("1506181", (SkillId.WEB_DEVELOPMENT, 1), (L, 1)),
    _d("1506493", (SkillId.NETWORKS, .8), (SkillId.SYSTEMS, .8), (P, .7)),
    _d("1509999", (SkillId.RESEARCH, 1), (SkillId.COMMUNICATION, .7)),
)


def validate_course_skill_definitions(
    definitions: Iterable[CourseSkillDefinition],
    *,
    expected_course_codes: frozenset[str] = SUPPORTED_PLAN12_COURSE_CODES,
) -> Mapping[str, CourseSkillDefinition]:
    """Validate and index explicit course-code mappings without name inference."""
    indexed: dict[str, CourseSkillDefinition] = {}
    for definition in definitions:
        if definition.course_code in indexed:
            raise ValueError(f"Duplicate taxonomy course code: {definition.course_code}")
        if not definition.skills:
            raise ValueError(f"Taxonomy course has no skills: {definition.course_code}")
        seen_skills: set[SkillId] = set()
        for weighted in definition.skills:
            if not isinstance(weighted.skill_id, SkillId):
                raise ValueError(
                    f"Unknown taxonomy skill for {definition.course_code}: {weighted.skill_id!r}"
                )
            if weighted.skill_id in seen_skills:
                raise ValueError(
                    f"Duplicate taxonomy skill for {definition.course_code}: "
                    f"{weighted.skill_id.value}"
                )
            if not 0 < weighted.weight <= 1:
                raise ValueError(
                    f"Invalid taxonomy skill weight for {definition.course_code}: "
                    f"{weighted.weight!r}"
                )
            seen_skills.add(weighted.skill_id)
        indexed[definition.course_code] = definition

    actual_codes = frozenset(indexed)
    if actual_codes != expected_course_codes:
        missing = sorted(expected_course_codes - actual_codes)
        unexpected = sorted(actual_codes - expected_course_codes)
        raise ValueError(
            "Taxonomy course set differs from supported Plan 12 "
            f"(missing={missing}, unexpected={unexpected})"
        )
    return indexed


PLAN12_COURSE_SKILLS = validate_course_skill_definitions(_DEFINITIONS)
