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

    # Nursing & Health Sciences Competencies
    NURSING_FUNDAMENTALS = "NURSING_FUNDAMENTALS"
    CLINICAL_ASSESSMENT = "CLINICAL_ASSESSMENT"
    PATIENT_SAFETY = "PATIENT_SAFETY"
    PHARMACOLOGY = "PHARMACOLOGY"
    ANATOMY_PHYSIOLOGY = "ANATOMY_PHYSIOLOGY"
    PATHOPHYSIOLOGY = "PATHOPHYSIOLOGY"
    MICROBIOLOGY = "MICROBIOLOGY"
    BIOCHEMISTRY = "BIOCHEMISTRY"
    ADULT_HEALTH_NURSING = "ADULT_HEALTH_NURSING"
    CRITICAL_CARE_NURSING = "CRITICAL_CARE_NURSING"
    MATERNAL_HEALTH_NURSING = "MATERNAL_HEALTH_NURSING"
    CHILD_HEALTH_NURSING = "CHILD_HEALTH_NURSING"
    COMMUNITY_HEALTH_NURSING = "COMMUNITY_HEALTH_NURSING"
    MENTAL_HEALTH_NURSING = "MENTAL_HEALTH_NURSING"
    CLINICAL_NUTRITION = "CLINICAL_NUTRITION"
    HEALTH_INFORMATICS = "HEALTH_INFORMATICS"
    PALLIATIVE_CARE = "PALLIATIVE_CARE"
    GERIATRIC_NURSING = "GERIATRIC_NURSING"
    NURSING_LEADERSHIP = "NURSING_LEADERSHIP"
    BIOSTATISTICS = "BIOSTATISTICS"

    # Software Engineering Competencies
    SOFTWARE_ENGINEERING_FOUNDATIONS = "SOFTWARE_ENGINEERING_FOUNDATIONS"
    SOFTWARE_REQUIREMENTS = "SOFTWARE_REQUIREMENTS"
    SOFTWARE_MODELING_ANALYSIS = "SOFTWARE_MODELING_ANALYSIS"
    SOFTWARE_DESIGN_ARCHITECTURE = "SOFTWARE_DESIGN_ARCHITECTURE"
    DESIGN_PATTERNS = "DESIGN_PATTERNS"
    SOFTWARE_TESTING_METRICS = "SOFTWARE_TESTING_METRICS"
    SOFTWARE_QUALITY_ENGINEERING = "SOFTWARE_QUALITY_ENGINEERING"
    SOFTWARE_MAINTENANCE_EVOLUTION = "SOFTWARE_MAINTENANCE_EVOLUTION"
    SOFTWARE_PROJECT_MANAGEMENT = "SOFTWARE_PROJECT_MANAGEMENT"
    SOFTWARE_DOCUMENTATION = "SOFTWARE_DOCUMENTATION"
    HUMAN_COMPUTER_INTERACTION = "HUMAN_COMPUTER_INTERACTION"
    SOFTWARE_ENGINEERING_TOOLS = "SOFTWARE_ENGINEERING_TOOLS"
    SOFTWARE_ENGINEERING_PRACTICES = "SOFTWARE_ENGINEERING_PRACTICES"
    APPLICATION_DEVELOPMENT = "APPLICATION_DEVELOPMENT"
    MOBILE_APP_DEVELOPMENT = "MOBILE_APP_DEVELOPMENT"
    ENTERPRISE_SYSTEMS = "ENTERPRISE_SYSTEMS"
    COMPUTER_ARCHITECTURE = "COMPUTER_ARCHITECTURE"
    DIGITAL_LOGIC = "DIGITAL_LOGIC"
    CYBERSECURITY_FOUNDATIONS = "CYBERSECURITY_FOUNDATIONS"
    DATA_MODELING = "DATA_MODELING"


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

NURSING_PLAN12_ID = "2a78bbbb-0dc0-5c46-8630-7a46e4179830"
NURSING_COURSE_SKILL_MAPPING_VERSION = "NURSING_PLAN12_COURSE_SKILLS_V1"

SUPPORTED_NURSING_PLAN12_COURSE_CODES = frozenset({
    "0200104", "0200105", "0200106", "0200110", "0200111", "0200113",
    "0200114", "0200115", "0200122", "0200125", "0200127", "0200130",
    "0200152", "0200153", "0200154", "0200156", "0300123", "0300124",
    "0300131", "0300141", "0300157", "0400202", "0701262", "0701314",
    "0701364", "0801111", "0801114", "0801221", "0801222", "0801223",
    "0801224", "0801225", "0801226", "0801227", "0801233", "0801244",
    "0801251", "0801286", "0801322", "0801331", "0801332", "0801341",
    "0801342", "0801351", "0801352", "0801363", "0801364", "0801365",
    "0801369", "0801374", "0801420", "0801421", "0801461", "0801462",
    "0801469", "0801470", "0801471", "0801472", "0801491", "0801493",
    "0801494", "0809999", "1101399",
})

NF = SkillId.NURSING_FUNDAMENTALS
CA = SkillId.CLINICAL_ASSESSMENT
PS = SkillId.PATIENT_SAFETY
PH = SkillId.PHARMACOLOGY
AP = SkillId.ANATOMY_PHYSIOLOGY
PP = SkillId.PATHOPHYSIOLOGY
MB = SkillId.MICROBIOLOGY
BC = SkillId.BIOCHEMISTRY
AH = SkillId.ADULT_HEALTH_NURSING
CC = SkillId.CRITICAL_CARE_NURSING
MH = SkillId.MATERNAL_HEALTH_NURSING
CH = SkillId.CHILD_HEALTH_NURSING
CM = SkillId.COMMUNITY_HEALTH_NURSING
MN = SkillId.MENTAL_HEALTH_NURSING
CN = SkillId.CLINICAL_NUTRITION
HI = SkillId.HEALTH_INFORMATICS
PC = SkillId.PALLIATIVE_CARE
GN = SkillId.GERIATRIC_NURSING
NL = SkillId.NURSING_LEADERSHIP
BS = SkillId.BIOSTATISTICS
R = SkillId.RESEARCH
C = SkillId.COMMUNICATION
E = SkillId.ETHICS
D = SkillId.DIGITAL_LITERACY

_NURSING_DEFINITIONS = (
    # University Required
    _d("0200104", (T, .8), (M, .8)),
    _d("0200105", (C, 1.0), (T, .6)),
    _d("0200106", (C, 1.0), (T, .6)),
    _d("0200110", (T, .8), (M, 1.0)),
    _d("0200111", (T, .9), (E, .8), (M, .7)),
    _d("0200115", (CM, .7), (C, .7)),
    _d("0200153", (C, .8), (T, .6)),
    _d("0200154", (NL, .7), (C, .8)),
    _d("0400202", (P, .7), (T, .6)),
    # University Electives
    _d("0200113", (T, .8), (M, 1.0)),
    _d("0200114", (T, .8), (M, 1.0)),
    _d("0200122", (T, 1.0), (C, .6)),
    _d("0200125", (T, .8), (M, 1.0)),
    _d("0200127", (E, 1.0), (T, .8)),
    _d("0200130", (T, .8), (M, 1.0)),
    _d("0200152", (D, 1.0), (L, .8)),
    _d("0200156", (CM, .7), (T, .7)),
    _d("0300123", (T, 1.0), (M, .8)),
    _d("0300124", (T, 1.0), (R, .6)),
    _d("0300157", (D, 1.0), (HI, .6)),
    # Faculty Required
    _d("0300131", (BC, .8), (T, .8)),
    _d("0300141", (AP, .8), (T, .8)),
    _d("0701314", (BC, 1.0), (T, .8)),
    _d("0801225", (PP, 1.0), (AP, .8)),
    _d("0801244", (MB, 1.0), (PS, .8)),
    _d("0801251", (CH, .7), (T, .9)),
    _d("0801286", (BS, 1.0), (R, .8)),
    _d("0809999", (R, 1.0), (C, .8)),
    _d("1101399", (C, .9), (PS, .8), (E, .8)),
    # Major Required
    _d("0801111", (NF, 1.0), (PS, .8)),
    _d("0801114", (NF, 1.0), (L, 1.0), (PS, .9)),
    _d("0801221", (AH, 1.0), (CA, .8)),
    _d("0801222", (AH, 1.0), (L, 1.0), (PS, .9)),
    _d("0801223", (AH, 1.0), (PP, .8)),
    _d("0801224", (AH, 1.0), (L, 1.0), (CA, .9)),
    _d("0801226", (CA, 1.0), (AP, .7)),
    _d("0801227", (CA, 1.0), (L, 1.0)),
    _d("0801331", (CC, 1.0), (CA, .9)),
    _d("0801332", (CC, 1.0), (L, 1.0), (PS, .9)),
    _d("0801341", (MH, 1.0), (CA, .8)),
    _d("0801342", (MH, 1.0), (L, 1.0)),
    _d("0801351", (CH, 1.0), (CA, .8)),
    _d("0801352", (CH, 1.0), (L, 1.0)),
    _d("0801364", (CM, 1.0), (C, .9)),
    _d("0801365", (R, 1.0), (T, .8)),
    _d("0801461", (CM, 1.0), (PS, .8)),
    _d("0801462", (CM, 1.0), (L, 1.0)),
    _d("0801470", (E, 1.0), (HI, .8)),
    _d("0801471", (MN, 1.0), (C, .9)),
    _d("0801472", (MN, 1.0), (L, 1.0)),
    _d("0801491", (NL, 1.0), (C, .8)),
    _d("0801493", (AH, .8), (L, 1.0), (PS, 1.0), (CA, 1.0)),
    _d("0801494", (NL, 1.0), (L, .9)),
    # Major Electives
    _d("0801322", (PC, 1.0), (C, .8)),
    _d("0801363", (NF, .8), (R, .8)),
    _d("0801369", (HI, 1.0), (D, .8)),
    _d("0801374", (MN, .8), (C, .8)),
    _d("0801421", (GN, 1.0), (CA, .8)),
    _d("0801469", (PS, 1.0), (CC, .8)),
    # Supporting Required
    _d("0701262", (AP, 1.0), (T, .8)),
    _d("0701364", (AP, 1.0), (T, .8)),
    _d("0801233", (CN, 1.0), (T, .8)),
    _d("0801420", (PH, 1.0), (PS, .8)),
)

NURSING_PLAN12_COURSE_SKILLS = validate_course_skill_definitions(
    _NURSING_DEFINITIONS,
    expected_course_codes=SUPPORTED_NURSING_PLAN12_COURSE_CODES,
)

SE_PLAN12_ID = "1b709940-4279-560b-88ff-dacd5da636f2"
SE_COURSE_SKILL_MAPPING_VERSION = "SE_PLAN12_COURSE_SKILLS_V1"

SUPPORTED_SE_PLAN12_COURSE_CODES = frozenset({
    "0200104", "0200105", "0200106", "0200110", "0200111", "0200113",
    "0200114", "0200115", "0200122", "0200125", "0200127", "0200130",
    "0200153", "0200154", "0200156", "0200215", "0300104", "0300123",
    "0300124", "0300153", "0300154", "0300155", "0300157", "0300161",
    "0300220", "0301245", "0400202", "1501110", "1501111", "1501112",
    "1501113", "1501212", "1501221", "1501222", "1501231", "1501321",
    "1501340", "1501385", "1501430", "1503212", "1503270", "1503271",
    "1503272", "1503273", "1503274", "1503275", "1503335", "1503365",
    "1503370", "1503371", "1503372", "1503374", "1503380", "1503434",
    "1503436", "1503465", "1503466", "1503473", "1503475", "1505201",
    "1505480", "1506180", "1506181", "1506493", "1509999",
})

SE_PRG = SkillId.PROGRAMMING
SE_OOP = SkillId.OBJECT_ORIENTED_PROGRAMMING
SE_DS = SkillId.DATA_STRUCTURES
SE_ALG = SkillId.ALGORITHMS
SE_DB = SkillId.DATABASES
SE_LR = SkillId.LOGICAL_REASONING
SE_DM = SkillId.DISCRETE_MATH
SE_LA = SkillId.LINEAR_ALGEBRA
SE_STA = SkillId.STATISTICS
SE_QM = SkillId.QUANTITATIVE_MATH
SE_WEB = SkillId.WEB_DEVELOPMENT
SE_SYS = SkillId.SYSTEMS
SE_NET = SkillId.NETWORKS

SE_SEF = SkillId.SOFTWARE_ENGINEERING_FOUNDATIONS
SE_REQ = SkillId.SOFTWARE_REQUIREMENTS
SE_MOD = SkillId.SOFTWARE_MODELING_ANALYSIS
SE_ARC = SkillId.SOFTWARE_DESIGN_ARCHITECTURE
SE_PAT = SkillId.DESIGN_PATTERNS
SE_TST = SkillId.SOFTWARE_TESTING_METRICS
SE_SQE = SkillId.SOFTWARE_QUALITY_ENGINEERING
SE_MNT = SkillId.SOFTWARE_MAINTENANCE_EVOLUTION
SE_SPM = SkillId.SOFTWARE_PROJECT_MANAGEMENT
SE_DOC = SkillId.SOFTWARE_DOCUMENTATION
SE_HCI = SkillId.HUMAN_COMPUTER_INTERACTION
SE_SET = SkillId.SOFTWARE_ENGINEERING_TOOLS
SE_SEP = SkillId.SOFTWARE_ENGINEERING_PRACTICES
SE_APP = SkillId.APPLICATION_DEVELOPMENT
SE_MOB = SkillId.MOBILE_APP_DEVELOPMENT
SE_ENT = SkillId.ENTERPRISE_SYSTEMS
SE_CAR = SkillId.COMPUTER_ARCHITECTURE
SE_DGL = SkillId.DIGITAL_LOGIC
SE_SEC = SkillId.CYBERSECURITY_FOUNDATIONS
SE_DTM = SkillId.DATA_MODELING
SE_AIF = SkillId.AI_FOUNDATIONS

_SE_DEFINITIONS = (
    # University Required
    _d("0200104", (T, .8), (E, .6)),
    _d("0200105", (C, 1.0)),
    _d("0200106", (C, 1.0)),
    _d("0200110", (T, .8), (E, .6)),
    _d("0200111", (E, 1.0), (T, .7)),
    _d("0200115", (E, .8), (P, .6)),
    _d("0200153", (C, .8), (P, .6)),
    _d("0200154", (E, .8), (P, .7)),
    _d("0400202", (P, .9), (SE_ENT, .7)),
    # University Electives
    _d("0200113", (T, .8), (R, .6)),
    _d("0200114", (T, .8), (R, .6)),
    _d("0200122", (T, .8), (C, .6)),
    _d("0200125", (T, .8), (E, .7)),
    _d("0200127", (E, 1.0)),
    _d("0200130", (T, .8), (E, .7)),
    _d("0200156", (T, .8), (E, .6)),
    _d("0300123", (T, .8), (SE_QM, .6)),
    _d("0300124", (T, .8), (R, .6)),
    _d("0300157", (D, 1.0)),
    _d("0300161", (L, .8), (T, .7)),
    # Faculty Required
    _d("0300153", (D, 1.0), (SE_SYS, .7)),
    _d("0300154", (SE_SEC, 1.0), (SE_SYS, .8)),
    _d("0300155", (SE_DGL, 1.0), (SE_LR, .8)),
    _d("0300220", (SE_DM, 1.0), (SE_LR, .8)),
    _d("1501110", (SE_PRG, 1.0), (SE_LR, .8)),
    _d("1501112", (SE_OOP, 1.0), (SE_PRG, .8)),
    _d("1501221", (SE_DS, 1.0), (SE_ALG, .8)),
    _d("1509999", (R, 1.0), (C, .8)),
    # Supporting Required
    _d("0200215", (C, 1.0), (D, .7)),
    _d("0300104", (SE_STA, 1.0), (SE_QM, .8)),
    _d("0301245", (SE_LA, 1.0), (SE_QM, .8)),
    # Major Required
    _d("1501111", (SE_PRG, .9), (L, 1.0)),
    _d("1501113", (SE_OOP, .9), (L, 1.0)),
    _d("1501212", (SE_APP, 1.0), (SE_OOP, .8)),
    _d("1501222", (SE_DB, 1.0), (SE_DTM, .8)),
    _d("1501231", (SE_CAR, 1.0), (SE_SYS, .8)),
    _d("1501321", (SE_ALG, 1.0), (SE_LR, .8)),
    _d("1501340", (SE_NET, 1.0), (SE_SYS, .8)),
    _d("1501430", (SE_SYS, 1.0), (SE_SEP, .7)),
    _d("1503270", (SE_SEF, 1.0), (T, .7)),
    _d("1503271", (SE_REQ, 1.0), (SE_MOD, .8)),
    _d("1503272", (SE_MOD, 1.0), (SE_ARC, .8)),
    _d("1503274", (SE_PAT, 1.0), (SE_OOP, .8)),
    _d("1503275", (SE_SPM, 1.0), (P, .8)),
    _d("1503365", (SE_SEP, 1.0), (P, .9)),
    _d("1503370", (SE_ARC, 1.0), (SE_PAT, .8)),
    _d("1503374", (SE_DOC, 1.0), (C, .8)),
    _d("1503434", (SE_DB, 1.0), (SE_SYS, .8)),
    _d("1503465", (P, 1.0), (SE_REQ, .8), (SE_ARC, .8)),
    _d("1503466", (P, 1.0), (SE_TST, .8), (SE_SEP, .8)),
    _d("1503473", (SE_TST, 1.0), (SE_SQE, .8)),
    _d("1503475", (SE_MNT, 1.0), (SE_SQE, .8)),
    _d("1505201", (SE_AIF, .8), (T, .7)),
    _d("1506180", (SE_WEB, 1.0), (SE_PRG, .8)),
    _d("1506181", (SE_WEB, .9), (L, 1.0)),
    # Major Electives
    _d("1501385", (SE_MOB, 1.0), (SE_APP, .8)),
    _d("1503212", (SE_PRG, 1.0), (SE_SEP, .8)),
    _d("1503273", (SE_HCI, 1.0), (SE_APP, .7)),
    _d("1503335", (SE_SEP, 1.0), (R, .7)),
    _d("1503371", (SE_SET, 1.0), (SE_SEP, .8)),
    _d("1503372", (SE_ENT, 1.0), (SE_SPM, .7)),
    _d("1503380", (SE_SQE, 1.0), (SE_TST, .8)),
    _d("1503436", (SE_SEP, 1.0), (R, .7)),
    _d("1505480", (SE_DB, .9), (SE_SYS, .8)),
    _d("1506493", (SE_SYS, .8), (SE_NET, .8)),
)

SE_PLAN12_COURSE_SKILLS = validate_course_skill_definitions(
    _SE_DEFINITIONS,
    expected_course_codes=SUPPORTED_SE_PLAN12_COURSE_CODES,
)
