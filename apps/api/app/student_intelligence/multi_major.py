"""Registry-ready deterministic definitions for the 14 additional curricula."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable, Mapping

from app.student_intelligence.diagnostic import (
    ASSESSMENT_VERSION,
    DIFFICULTY_WEIGHT,
    MIN_RESPONSE_TIME_MS,
    TARGET_QUESTIONS,
    AnswerEvidence,
    DiagnosticDomainResult,
    DiagnosticQuestion,
    Option,
)
from app.student_intelligence.multi_major_content import MULTI_MAJOR_CONTENT
from app.student_intelligence.taxonomy import (
    CourseSkillDefinition,
    SkillId,
    SkillWeight,
)

MULTI_MAJOR_MAPPING_VERSION = "MULTI_MAJOR_PLAN12_COURSE_SKILLS_V1"


@dataclass(frozen=True, slots=True)
class MultiMajorDefinition:
    major_code: str
    plan_key: str
    study_plan_id: str
    mapping_version: str
    course_codes: frozenset[str]
    course_skills: Mapping[str, CourseSkillDefinition]
    competency_ids: tuple[str, ...]
    domains: tuple[str, ...]
    diagnostic_bridge: Mapping[str, tuple[str, ...]]
    question_bank: tuple[DiagnosticQuestion, ...]
    questions_by_id: Mapping[str, DiagnosticQuestion]


def _shared_skill(code: str) -> SkillId:
    if code in {"0200105", "0200106", "0200153", "0200215"}:
        return SkillId.COMMUNICATION
    if code in {"0200127"}:
        return SkillId.ETHICS
    if code in {"0300152", "0300153", "0300157"}:
        return SkillId.DIGITAL_LITERACY
    if code in {"0300101", "0300102", "0300103", "0300104", "0301245"}:
        return SkillId.QUANTITATIVE_MATH
    if code == "0400202":
        return SkillId.PROJECT_WORK
    return SkillId.THEORY_COMPREHENSION


def _build_course_mapping(content: Mapping[str, object], skills: tuple[str, ...]) -> Mapping[str, CourseSkillDefinition]:
    rows = tuple(content["courses"])
    mapped: dict[str, CourseSkillDefinition] = {}
    discipline_index = 0
    for row in rows:
        code = str(row["course_code"])
        group = str(row["group_code"])
        if group.startswith("UNIVERSITY_"):
            weighted = (SkillWeight(_shared_skill(code), 1.0),)
        else:
            primary = skills[discipline_index % len(skills)]
            secondary = skills[(discipline_index + 1) % len(skills)]
            discipline_index += 1
            weighted = (SkillWeight(primary, 1.0), SkillWeight(secondary, 0.6))  # type: ignore[arg-type]
        mapped[code] = CourseSkillDefinition(
            course_code=code,
            skills=weighted,
            provenance="MODELED_FROM_CANONICAL_PLAN12_TITLE_AND_REQUIREMENT_CATEGORY",
            version=MULTI_MAJOR_MAPPING_VERSION,
        )
    if len(mapped) != len(rows):
        raise ValueError(f"Duplicate canonical course code for {content['plan_key']}")
    return mapped


def _question_prompt(index: int, definition_en: str, definition_ar: str) -> tuple[str, str]:
    prompts = (
        (f"أي كفاءة أكاديمية تتوافق بدقة مع الوصف الآتي: {definition_ar}؟",
         f"Which academic competency precisely matches this description: {definition_en}?"),
        (f"اختر المفهوم الذي يتمحور حول القدرة على {definition_ar}.",
         f"Choose the concept centered on the ability to {definition_en}."),
        (f"يحتاج طالب إلى {definition_ar}. ما الكفاءة التي ينبغي أن يطبقها؟",
         f"A student needs to {definition_en}. Which competency should be applied?"),
        (f"أي مجال يوفر الأدوات الأنسب من أجل {definition_ar}؟",
         f"Which area provides the most appropriate tools to {definition_en}?"),
        (f"عند التمييز بين كفاءات هذا التخصص، أيها يركز تحديداً على {definition_ar}؟",
         f"When distinguishing competencies in this discipline, which one specifically focuses on how to {definition_en}?"),
        (f"في مسألة متعددة الخطوات تتطلب {definition_ar}، ما الأساس الأكاديمي الأكثر صلة؟",
         f"In a multi-step problem requiring the ability to {definition_en}, which academic foundation is most relevant?"),
    )
    return prompts[index]


def _build_questions(content: Mapping[str, object]) -> tuple[DiagnosticQuestion, ...]:
    domains = tuple(content["domains"])
    concepts = tuple(concept for _, domain_concepts in domains for concept in domain_concepts)
    answer_positions = ("A", "B", "C", "D", "A", "C")
    difficulties = ("EASY", "EASY", "MEDIUM", "MEDIUM", "HARD", "HARD")
    questions: list[DiagnosticQuestion] = []
    prefix = str(content["question_prefix"])
    for domain_index, (domain, domain_concepts) in enumerate(domains):
        for local_index in range(6):
            target = domain_concepts[local_index % 2]
            target_global = concepts.index(target)
            distractors = [concepts[(target_global + step) % len(concepts)] for step in (1, 3, 5)]
            answer = answer_positions[local_index]
            correct_position = ord(answer) - 65
            arranged: list[tuple[object, ...] | None] = [None] * 4
            arranged[correct_position] = target
            for position, distractor in zip(
                (pos for pos in range(4) if pos != correct_position), distractors, strict=True
            ):
                arranged[position] = distractor
            prompt_ar, prompt_en = _question_prompt(local_index, str(target[3]), str(target[4]))
            options = tuple(
                Option(chr(65 + option_index), str(concept[2]), str(concept[1]))
                for option_index, concept in enumerate(arranged)
                if concept is not None
            )
            qid = f"{prefix}{domain_index * 6 + local_index + 1:02d}"
            wrong_ids = tuple(option.option_id for option in options if option.option_id != answer)
            questions.append(DiagnosticQuestion(
                question_id=qid,
                domain=str(domain),  # type: ignore[arg-type]
                skill=str(target[0]),
                subskill=str(target[0]),
                difficulty=difficulties[local_index],
                prompt_ar=prompt_ar,
                prompt_en=prompt_en,
                options=options,
                correct_option=answer,
                distractor_reasoning={key: "The option names a different governed competency." for key in wrong_ids},
                cognitive_operation=("CONCEPT_IDENTIFICATION" if local_index < 2 else
                                     "SCENARIO_APPLICATION" if local_index < 4 else "CONCEPTUAL_DISCRIMINATION"),
                evidence_weight=1.0 + (0.05 * (local_index // 2)),
                expected_solving_behavior="Match the academic task to the most specific curriculum competency.",
                estimated_time_seconds=30 + local_index * 5,
            ))
    return tuple(questions)


def _build_definition(major: str, content: Mapping[str, object]) -> MultiMajorDefinition:
    domains = tuple(str(domain) for domain, _ in content["domains"])
    bridge = {
        str(domain): tuple(str(concept[0]) for concept in concepts)
        for domain, concepts in content["domains"]
    }
    skills = tuple(skill for domain_skills in bridge.values() for skill in domain_skills)
    questions = _build_questions(content)
    course_skills = _build_course_mapping(content, skills)
    if len(domains) != 5 or len(set(domains)) != 5:
        raise ValueError(f"{major} must define five unique diagnostic domains")
    if len(skills) != 10 or len(set(skills)) != 10:
        raise ValueError(f"{major} must define ten unique curriculum competencies")
    if len(questions) != TARGET_QUESTIONS or len({q.question_id for q in questions}) != TARGET_QUESTIONS:
        raise ValueError(f"{major} diagnostic bank must contain 30 unique questions")
    return MultiMajorDefinition(
        major_code=major,
        plan_key=str(content["plan_key"]),
        study_plan_id=str(content["study_plan_id"]),
        mapping_version=MULTI_MAJOR_MAPPING_VERSION,
        course_codes=frozenset(course_skills),
        course_skills=course_skills,
        competency_ids=skills,
        domains=domains,
        diagnostic_bridge=bridge,
        question_bank=questions,
        questions_by_id={question.question_id: question for question in questions},
    )


MULTI_MAJOR_DEFINITIONS: tuple[MultiMajorDefinition, ...] = tuple(
    _build_definition(major, content) for major, content in MULTI_MAJOR_CONTENT.items()
)
MULTI_MAJOR_BY_PLAN_ID = {item.study_plan_id: item for item in MULTI_MAJOR_DEFINITIONS}
MULTI_MAJOR_BY_QUESTION_ID = {
    question_id: item
    for item in MULTI_MAJOR_DEFINITIONS
    for question_id in item.questions_by_id
}


def score_multi_major_domain(
    definition: MultiMajorDefinition,
    domain: str,
    responses: Iterable[AnswerEvidence],
) -> DiagnosticDomainResult:
    all_rows = tuple(responses)
    rows = tuple(
        row for row in all_rows
        if definition.questions_by_id[row.question_id].domain == domain
    )
    possible = sum(
        DIFFICULTY_WEIGHT[definition.questions_by_id[row.question_id].difficulty]
        * definition.questions_by_id[row.question_id].evidence_weight
        for row in rows
    )
    earned = sum(
        DIFFICULTY_WEIGHT[definition.questions_by_id[row.question_id].difficulty]
        * definition.questions_by_id[row.question_id].evidence_weight
        for row in rows if row.is_correct
    )
    base = 50.0 if not possible else 100 * earned / possible
    fast_count = sum(
        row.response_time_ms < max(
            MIN_RESPONSE_TIME_MS,
            definition.questions_by_id[row.question_id].estimated_time_seconds * 250,
        ) for row in rows
    )
    timing_reliability = max(0.7, 1 - fast_count * 0.05)
    halves = (rows[:3], rows[3:])
    rates = [sum(row.is_correct for row in half) / len(half) for half in halves if half]
    consistency = 1.0 if len(rates) < 2 else max(0.75, 1 - abs(rates[0] - rates[1]) * 0.25)
    score = round(50 + (base - 50) * timing_reliability * consistency)
    complete = len(rows) == 6 and {
        definition.questions_by_id[row.question_id].difficulty for row in rows
    } == {"EASY", "MEDIUM", "HARD"}
    total_time = sum(row.response_time_ms for row in all_rows)
    option_values = [row.selected_option for row in all_rows]
    repetitive = bool(option_values) and max(option_values.count(value) for value in set(option_values)) / len(option_values) >= 0.7
    if not complete or total_time < 180_000 or repetitive:
        confidence = "LOW"
    elif len(rates) == 2 and abs(rates[0] - rates[1]) <= (1 / 3) and fast_count == 0:
        confidence = "HIGH"
    else:
        confidence = "MEDIUM"
    patterns: list[str] = []
    if len(rows) == 6 and sum(row.is_correct for row in rows) >= 5:
        patterns.append("STRONG_SYSTEMATIC_REASONING")
    if rows and mean(row.response_time_ms for row in rows) > 75_000 and sum(row.is_correct for row in rows) >= 4:
        patterns.append("CAREFUL_BUT_SLOWER")
    if fast_count >= 2 and sum(row.is_correct for row in rows) <= 3:
        patterns.append("FAST_BUT_ERROR_PRONE")
    if sum(not row.is_correct and row.self_confidence == "HIGH" for row in rows) >= 2:
        patterns.append("SELF_CONFIDENCE_ABOVE_EVIDENCE")
    reasons = [
        "MODELED_DIAGNOSTIC_BASELINE",
        f"VALID_RESPONSES_{len(rows)}",
        "FULL_DIFFICULTY_COVERAGE" if complete else "INCOMPLETE_DIFFICULTY_COVERAGE",
    ]
    if total_time < 180_000:
        reasons.append("UNREALISTICALLY_FAST")
    if repetitive:
        reasons.append("REPETITIVE_OPTION_PATTERN")
    return DiagnosticDomainResult(
        domain, max(0, min(100, score)), confidence, len(rows),  # type: ignore[arg-type]
        tuple(reasons), tuple(patterns),
    )


def validate_multi_major_definitions() -> None:
    question_ids: set[str] = set()
    plan_ids: set[str] = set()
    for definition in MULTI_MAJOR_DEFINITIONS:
        if definition.study_plan_id in plan_ids:
            raise ValueError("Duplicate multi-major study plan id")
        plan_ids.add(definition.study_plan_id)
        if definition.course_codes != frozenset(definition.course_skills):
            raise ValueError(f"Course mapping mismatch for {definition.major_code}")
        domain_counts = {domain: 0 for domain in definition.domains}
        difficulty_counts = {"EASY": 0, "MEDIUM": 0, "HARD": 0}
        answer_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        for question in definition.question_bank:
            if question.question_id in question_ids:
                raise ValueError(f"Duplicate diagnostic question id: {question.question_id}")
            question_ids.add(question.question_id)
            domain_counts[str(question.domain)] += 1
            difficulty_counts[question.difficulty] += 1
            answer_counts[question.correct_option] += 1
            if len(question.options) != 4 or question.correct_option not in {o.option_id for o in question.options}:
                raise ValueError(f"Invalid options for {question.question_id}")
        if set(domain_counts.values()) != {6}:
            raise ValueError(f"Unbalanced domains for {definition.major_code}: {domain_counts}")
        if difficulty_counts != {"EASY": 10, "MEDIUM": 10, "HARD": 10}:
            raise ValueError(f"Unbalanced difficulty for {definition.major_code}")
        if max(answer_counts.values()) > 10:
            raise ValueError(f"Unbalanced answer positions for {definition.major_code}")


validate_multi_major_definitions()
