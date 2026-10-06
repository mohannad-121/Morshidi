"""Tests for the high-confidence deterministic academic pre-router."""

from __future__ import annotations

import pytest

from app.advisor.models import AdvisorIntent
from app.advisor.pre_router import (
    extract_context_courses,
    extract_course_codes,
    normalize_academic_text,
    pre_route_academic_intent,
)


def test_gpa_variations_route_to_academic_status() -> None:
    queries = [
        "كم معدلي؟",
        "قديش معدلي؟",
        "شو ال GPA تبعي؟",
        "شو معدلي التراكمي؟",
        "معدلي التراكمي",
        "شو معدلي",
        "كم معدلي التراكمي؟",
        "my GPA",
        "gpa",
        "سجلي الأكاديمي",
        "كشف علاماتي",
    ]
    for q in queries:
        routed = pre_route_academic_intent(q)
        assert routed is not None, f"Failed to pre-route: {q}"
        assert routed.intent == AdvisorIntent.ACADEMIC_STATUS.value, f"Wrong intent for {q}: {routed.intent}"


def test_credits_and_remaining_route_to_remaining_requirements() -> None:
    queries = [
        "كم ساعة مجتاز؟",
        "قديش قطعت ساعات؟",
        "كم ساعة باقي؟",
        "كم ضايل علي؟",
        "قديش باقي للتخرج؟",
        "كم ضايل للتخرج",
        "ساعاتي المتبقية",
        "كم ساعة ضايل؟",
        "remaining credits",
        "how many credits left",
    ]
    for q in queries:
        routed = pre_route_academic_intent(q)
        assert routed is not None, f"Failed to pre-route: {q}"
        assert routed.intent == AdvisorIntent.REMAINING_REQUIREMENTS.value, f"Wrong intent for {q}: {routed.intent}"


def test_passed_and_enrolled_courses_route_to_academic_status() -> None:
    passed_queries = [
        "شو المواد اللي خلصتها؟",
        "شو المواد اللي نجحت فيها؟",
        "المساقات المجتازة",
        "شو خلصت مواد؟",
    ]
    for q in passed_queries:
        routed = pre_route_academic_intent(q)
        assert routed is not None, f"Failed to pre-route: {q}"
        assert routed.intent == AdvisorIntent.ACADEMIC_STATUS.value
        assert routed.clarification_hint == "PASSED_COURSES"

    enrolled_queries = [
        "شو المواد اللي مسجلها هسا؟",
        "شو مسجل هذا الفصل؟",
        "المواد المسجلة حالياً",
        "شو منزل هسا",
    ]
    for q in enrolled_queries:
        routed = pre_route_academic_intent(q)
        assert routed is not None, f"Failed to pre-route: {q}"
        assert routed.intent == AdvisorIntent.ACADEMIC_STATUS.value
        assert routed.clarification_hint == "ENROLLED_COURSES"


def test_recommendations_and_available_courses() -> None:
    queries = [
        "شو المواد اللي بقدر أنزلها؟",
        "شو بقدر أنزل؟",
        "شو بتنصحني أسجل الفصل الجاي؟",
        "شو أنزل الفصل الجاي",
        "شو بتنصحني أنزل",
        "اقترح علي مواد",
        "recommend courses",
    ]
    for q in queries:
        routed = pre_route_academic_intent(q)
        assert routed is not None, f"Failed to pre-route: {q}"
        assert routed.intent == AdvisorIntent.COURSE_RECOMMENDATIONS.value, f"Wrong intent for {q}: {routed.intent}"


def test_course_eligibility_with_named_course() -> None:
    queries = [
        ("هل بقدر أنزل تعلم الآلة؟", "تعلم الآلة"),
        ("ليش ما بقدر أسجل تعلم الآلة؟", "تعلم الآلة"),
        ("بقدر أنزل برمجة الحاسوب 2؟", "برمجة الحاسوب 2"),
        ("هل أستطيع تسجيل مساق 0101410؟", "0101410"),
    ]
    for q, expected in queries:
        routed = pre_route_academic_intent(q)
        assert routed is not None, f"Failed to pre-route: {q}"
        assert routed.intent == AdvisorIntent.COURSE_ELIGIBILITY.value
        all_mentions = routed.course_mentions + routed.course_codes_mentioned
        assert any(expected in m for m in all_mentions), f"Expected {expected} in {all_mentions}"


def test_course_eligibility_with_pronoun_and_context() -> None:
    context = "تحدثنا سابقاً عن مساق تعلم الآلة (0101410) في الخطة."
    queries = [
        "هل بقدر أنزلها؟",
        "ليش ما بقدر أسجلها؟",
        "بقدر أخذها؟",
    ]
    for q in queries:
        routed = pre_route_academic_intent(q, conversation_context=context)
        assert routed is not None, f"Failed to pre-route pronoun query: {q}"
        assert routed.intent == AdvisorIntent.COURSE_ELIGIBILITY.value
        all_mentions = routed.course_mentions + routed.course_codes_mentioned
        assert "0101410" in all_mentions or any("تعلم الآلة" in m for m in all_mentions)


def test_course_information_prerequisites_and_difficulty() -> None:
    prereq = pre_route_academic_intent("شو متطلبات تعلم الآلة؟")
    assert prereq is not None
    assert prereq.intent == AdvisorIntent.COURSE_INFORMATION.value
    assert any("تعلم الآلة" in m for m in prereq.course_mentions)

    diff = pre_route_academic_intent("شو صعوبة تعلم الآلة؟")
    assert diff is not None
    assert diff.intent == AdvisorIntent.COURSE_INFORMATION.value

    diff_personal = pre_route_academic_intent("هل تعلم الآلة صعبة علي؟")
    assert diff_personal is not None
    assert diff_personal.intent == AdvisorIntent.COURSE_INFORMATION.value

    # Pronoun with context
    context = "مساق برمجة الحاسوب 2 (0101211)"
    diff_pronoun = pre_route_academic_intent("شو صعوبتها؟", conversation_context=context)
    assert diff_pronoun is not None
    assert diff_pronoun.intent == AdvisorIntent.COURSE_INFORMATION.value
    assert "0101211" in diff_pronoun.course_codes_mentioned or any("برمجة الحاسوب" in m for m in diff_pronoun.course_mentions)


def test_course_grade_inquiry() -> None:
    q1 = pre_route_academic_intent("كم علامتي بتعلم الآلة؟")
    assert q1 is not None
    assert q1.intent == AdvisorIntent.COURSE_INFORMATION.value
    assert any("تعلم الآلة" in m for m in q1.course_mentions)
    assert q1.clarification_hint == "COURSE_GRADE"

    q2 = pre_route_academic_intent("شو جبت ببرمجة الحاسوب 2؟")
    assert q2 is not None
    assert q2.intent == AdvisorIntent.COURSE_INFORMATION.value
    assert any("برمجة الحاسوب 2" in m for m in q2.course_mentions)


def test_course_comparison() -> None:
    comp = pre_route_academic_intent("قارنلي بين تعلم الآلة وعلم البيانات")
    assert comp is not None
    assert comp.intent == AdvisorIntent.COURSE_COMPARISON.value
    assert len(comp.course_mentions) == 2
    assert any("تعلم الآلة" in m for m in comp.course_mentions)
    assert any("علم البيانات" in m for m in comp.course_mentions)


def test_unrelated_chat_returns_none_for_llm_fallback() -> None:
    non_academic = [
        "مرحبا كيفك؟",
        "شو اسمك؟",
        "شكراً جزيلاً",
        "مين طورك؟",
    ]
    for q in non_academic:
        assert pre_route_academic_intent(q) is None

