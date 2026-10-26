"""Deterministic query understanding for governed institutional-policy retrieval.

This module does not decide academic outcomes.  It only normalizes a user's
words and produces bounded lexical variants that can retrieve verified policy
evidence from the caller's university tenant.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


_ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\-]+", re.UNICODE)
_TRANSLATION = str.maketrans(
    {
        "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي",
        "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
        "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
    }
)


@dataclass(frozen=True, slots=True)
class PolicyQueryConcept:
    name: str
    triggers: tuple[str, ...]
    expansion: str


@dataclass(frozen=True, slots=True)
class PolicyQueryPlan:
    original_text: str
    normalized_text: str
    language: str
    intent: str
    concepts: tuple[str, ...]
    lexical_queries: tuple[str, ...]


_CONCEPTS = (
    PolicyQueryConcept(
        "incomplete",
        ("غير مكتمل", "عذر طبي", "العذر الطبي", "عذر مرضي", "العذر المرضي", "عذر غياب", "امتحان تعويضي", "امتحان تكميلي", "incomplete", "medical excuse", "make-up exam", "makeup exam"),
        "غير مكتمل عذر طبي امتحان تعويضي incomplete medical excuse makeup exam",
    ),
    PolicyQueryConcept(
        "course_repeat",
        ("اعادة مادة", "اعادة مساق", "اعيد مادة", "اعيد مساق", "تحسين معدل", "تكرار مساق", "repeat course", "retake course", "retake"),
        "إعادة المساق إعادة المادة تحسين المعدل repeat course retake",
    ),
    PolicyQueryConcept(
        "postponement",
        ("تاجيل", "تأجيل", "ااجل", "أأجل", "اجل", "وقف تسجيل", "انقطاع", "leave of absence", "postponement", "deferral"),
        "تأجيل الدراسة انقطاع وقف التسجيل postponement deferral leave of absence",
    ),
    PolicyQueryConcept(
        "academic_standing",
        ("انذار", "فصل اكاديمي", "مراقبة", "probation", "academic warning", "academic standing", "suspension", "dismissal"),
        "الانذار الاكاديمي الفصل الاكاديمي المراقبة academic warning probation academic standing",
    ),
    PolicyQueryConcept(
        "course_load",
        ("العبء الدراسي", "عبء", "ساعات الفصل", "تنزيل ساعات", "الحد الاعلى", "الحد الادنى", "course load", "credit load", "overload", "underload"),
        "العبء الدراسي الحد الاعلى الحد الادنى للساعات course load credit load",
    ),
    PolicyQueryConcept(
        "withdrawal",
        ("انسحاب", "اسحب", "اسقط", "اسقاط", "احذف الماده", "drop course", "withdrawal", "withdraw"),
        "انسحاب اسقاط المساق المادة withdrawal drop course",
    ),
    PolicyQueryConcept(
        "attendance",
        ("غياب", "غبت", "اغيب", "حضور", "حرمان", "absence", "attendance", "miss class", "missed class"),
        "الغياب الحضور الحرمان attendance absence",
    ),
    PolicyQueryConcept(
        "examinations",
        ("امتحان", "اختبار", "فاينل", "ميد", "exam", "final", "midterm"),
        "الامتحانات الاختبارات exam examination",
    ),
    PolicyQueryConcept(
        "grades",
        ("علامه", "علامة", "درجه", "تقدير", "معدل", "grade", "mark", "gpa"),
        "العلامات الدرجات التقدير grade grading",
    ),
    PolicyQueryConcept(
        "registration",
        ("تسجيل", "سجل", "الشعبه", "الشعبة", "registration", "register", "enrol", "enroll", "enrollment"),
        "التسجيل المساقات الشعب registration enrollment",
    ),
    PolicyQueryConcept(
        "graduation",
        ("تخرج", "التخرج", "graduation", "graduate", "degree requirement"),
        "التخرج متطلبات الدرجة graduation requirements",
    ),
    PolicyQueryConcept(
        "transfer",
        ("معادله", "معادلة", "اعادل", "تحويل", "ساعات منقوله", "الساعات المنقولة", "transfer credit", "equivalency"),
        "معادلة المواد الساعات المنقولة transfer credit equivalency",
    ),
    PolicyQueryConcept(
        "discipline",
        ("عقوبه", "عقوبة", "العقوبات", "مخالفه", "مخالفة", "discipline", "misconduct", "penalty"),
        "العقوبات المخالفات disciplinary penalty misconduct",
    ),
    PolicyQueryConcept(
        "fees",
        ("رسوم", "مصاري", "دفع", "fee", "fees", "payment", "tuition"),
        "الرسوم الدفع tuition fees payment",
    ),
)
CONCEPTS_BY_NAME = {concept.name: concept for concept in _CONCEPTS}


def normalize_policy_query(value: str) -> str:
    """Normalize Arabic, English, mixed text, digits, and punctuation."""
    normalized = unicodedata.normalize("NFKC", value).casefold().replace("ـ", "")
    normalized = _ARABIC_DIACRITICS.sub("", normalized).translate(_TRANSLATION)
    normalized = _PUNCTUATION.sub(" ", normalized)
    return _WHITESPACE.sub(" ", normalized).strip()


def _matches(normalized: str, trigger: str) -> bool:
    candidate = normalize_policy_query(trigger)
    if not candidate:
        return False
    if re.fullmatch(r"[a-z0-9\- ]+", candidate):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(candidate)}(?![a-z0-9])", normalized))
    norm_th = normalized.replace("ة", "ه")
    cand_th = candidate.replace("ة", "ه")
    return candidate in normalized or cand_th in norm_th


def plan_policy_query(value: str, *, max_variants: int = 4) -> PolicyQueryPlan:
    """Create a small, deterministic, auditable retrieval plan."""
    original = _WHITESPACE.sub(" ", value).strip()
    normalized = normalize_policy_query(original)
    if not normalized:
        raise ValueError("policy query cannot be empty")
    if not 1 <= max_variants <= 6:
        raise ValueError("max_variants must be between 1 and 6")

    matched = tuple(
        concept for concept in _CONCEPTS
        if any(_matches(normalized, trigger) for trigger in concept.triggers)
    )
    language = "ar" if re.search(r"[\u0600-\u06ff]", original) else "en"
    variants: list[str] = [original]
    if normalized != original.casefold():
        variants.append(normalized)
    variants.extend(concept.expansion for concept in matched)
    lexical_queries = tuple(dict.fromkeys(query for query in variants if query))[:max_variants]
    return PolicyQueryPlan(
        original_text=original,
        normalized_text=normalized,
        language=language,
        intent=matched[0].name if matched else "general_policy",
        concepts=tuple(concept.name for concept in matched),
        lexical_queries=lexical_queries,
    )

