"""High-confidence deterministic academic pre-router for Morshidi AI.

Directly routes clear academic requests to deterministic academic intents
before trusting ungrounded LLM provider classifications.
"""

from __future__ import annotations

import re
import unicodedata

from app.advisor.models import AdvisorIntent
from app.advisor.provider import RawAdvisorInterpretation


def normalize_academic_text(value: str) -> str:
    """Normalize Arabic and English query text for robust intent matching."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[\u064b-\u065f\u0670]", "", normalized)
    normalized = normalized.translate(str.maketrans("أإآى", "اااي"))
    normalized = normalized.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return normalized


def extract_course_codes(text: str) -> tuple[str, ...]:
    """Find 6 to 8 digit course codes in text."""
    matches = re.findall(r"(?<!\d)\d{6,8}(?!\d)", text)
    return tuple(dict.fromkeys(matches))


def extract_context_courses(conversation_context: str) -> tuple[str, ...]:
    """Extract candidate course names and codes from recent conversation context."""
    if not conversation_context:
        return ()

    courses: list[str] = []

    # 1. Look for explicit course title patterns in context like مساق (...) or مادة (...)
    for match in re.finditer(
        r"(?:مساق|مادة|كورس|course)\s+([^\(\)\n\r,،:؛\.]{2,40})",
        conversation_context,
        re.IGNORECASE,
    ):
        name = match.group(1).strip()
        if name and name not in courses:
            courses.append(name)

    # 2. Look for course codes
    codes = extract_course_codes(conversation_context)
    for code in codes:
        if code not in courses:
            courses.append(code)

    return tuple(courses)


def _has_pronoun_reference(normalized: str) -> bool:
    """Check if query uses an Arabic pronoun or indirect reference to a course."""
    pronoun_patterns = [
        r"(?:انزلها|اسجلها|اخذها|اخذها|انزلهم|اسجلهم)",
        r"(?:متطلباتها|متطلبها|شروطها)",
        r"(?:صعوبتها|صعبة\s+علي|صعبة\s+ولا\s+سهلة|سهلة\s+ولا\s+صعبة|صعبه\s+علي|صعب\s+علي)",
        r"(?:علامتها|درجتها|علامتي\s+فيها|جبت\s+فيها)",
        r"(?:عنها|فيها|عليها|لها)\s*[\?؟]?$",
    ]
    return any(re.search(pat, normalized) for pat in pronoun_patterns)


def _map_span_to_raw(raw_text: str, norm_span: tuple[int, int]) -> str:
    """Map character span from normalized text back to original raw text."""
    start_norm, end_norm = norm_span
    raw_idx = 0
    norm_idx = 0
    start_raw = 0
    end_raw = len(raw_text)

    while raw_idx < len(raw_text) and norm_idx <= end_norm:
        if norm_idx == start_norm:
            start_raw = raw_idx
        if norm_idx == end_norm:
            end_raw = raw_idx
            break
        c = raw_text[raw_idx]
        if "\u064b" <= c <= "\u065f" or c == "\u0670":
            raw_idx += 1
            continue
        raw_idx += 1
        norm_idx += 1

    if norm_idx == end_norm:
        end_raw = raw_idx

    return raw_text[start_raw:end_raw]


def _clean_course_reference(name: str) -> str:
    """Clean query prefixes, prepositions, and punctuation from course mention."""
    cleaned = name.strip()
    cleaned = re.sub(
        r"^(?:هل\s+بقدر\s+[اأإآ]نزل|هل\s+بقدر\s+[اأإآ]سجل|بقدر\s+[اأإآ]نزل|بقدر\s+[اأإآ]سجل|[اأإآ]قدر\s+[اأإآ]نزل|[اأإآ]قدر\s+[اأإآ]سجل|"
        r"ليش\s+ما\s+بقدر\s+[اأإآ]نزل|ليش\s+ما\s+بقدر\s+[اأإآ]سجل|ليش\s+مش\s+قادر\s+[اأإآ]نزل|ليش\s+مش\s+قادر\s+[اأإآ]سجل|"
        r"شو\s+متطلبات|ما\s+هي\s+متطلبات|ماهي\s+متطلبات|متطلبات\s+مساق|متطلبات\s+مادة|متطلبات|"
        r"شو\s+صعوبة|ما\s+صعوبة|صعوبة\s+مساق|صعوبة\s+مادة|صعوبة|"
        r"كم\s+علامتي\s+بـ?|كم\s+علامتي\s+في|شو\s+جبت\s+بـ?|شو\s+جبت\s+في|علامتي\s+في|علامتي\s+بـ?|"
        r"كم\s+علامة\s+النجاح\s+في|كم\s+علامة\s+النجاح\s+بـ?|علامة\s+النجاح\s+في|علامة\s+النجاح\s+بـ?|"
        r"مساق|مادة|كورس|course)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    if cleaned.startswith("ب") and len(cleaned) > 3 and not (cleaned.startswith("برمج") or cleaned.startswith("بيان")):
        cleaned = cleaned[1:].strip()
    elif cleaned.startswith("في ") or cleaned.startswith("في\t"):
        cleaned = cleaned[2:].strip()
    elif cleaned.startswith("لـ") or cleaned.startswith("ل "):
        cleaned = cleaned[2:].strip()

    cleaned = re.sub(r"[\?؟!\.،,\s]+$", "", cleaned).strip()
    return cleaned


def _assign_mentions_and_codes(target: str, existing_codes: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Helper to route target string to either codes or mentions."""
    target_clean = _clean_course_reference(target)
    codes = list(existing_codes)
    mentions: list[str] = []
    if re.match(r"^\d{6,8}$", target_clean):
        if target_clean not in codes:
            codes.append(target_clean)
    elif target_clean:
        mentions.append(target_clean)
    return tuple(mentions), tuple(codes)


def pre_route_academic_intent(
    message: str,
    conversation_context: str = "",
) -> RawAdvisorInterpretation | None:
    """Deterministically pre-route high-confidence academic questions."""
    if not isinstance(message, str) or not message.strip():
        return None

    raw_message = message.strip()
    normalized = normalize_academic_text(raw_message)
    codes_in_message = extract_course_codes(raw_message)
    context_courses = extract_context_courses(conversation_context)

    # 1. Course Comparison: "قارنلي بين X و Y" / "مقارنة بين X و Y"
    comparison_match = re.search(
        r"(?:قارن(?:لي)?|مقارن[ةه]|compare)\s+(?:بين|between)\s+(.+?)\s+(?:و\s*|مع\s+|and\s+)(.+)",
        normalized,
    )
    if comparison_match:
        c1_raw = _map_span_to_raw(raw_message, comparison_match.span(1))
        c2_raw = _map_span_to_raw(raw_message, comparison_match.span(2))
        c1 = _clean_course_reference(c1_raw)
        c2 = _clean_course_reference(c2_raw)
        all_codes = codes_in_message
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.COURSE_COMPARISON.value,
            course_mentions=tuple(c for c in (c1, c2) if c and c not in all_codes),
            course_codes_mentioned=all_codes,
        )

    # 2. Recommendations / Available Courses (General): "شو المواد اللي بقدر أنزلها؟" / "شو بقدر أنزل؟"
    if re.search(
        r"(?:شو|ايش|ما|ماهي|what|which).{0,25}(?:المواد|المساقات|مواد|مساقات|courses?).{0,25}(?:بقدر|اقدر|ممكن|متاحة|can\s+i|available)",
        normalized,
    ) or re.search(
        r"(?:شو|ايش|ماذا)\s*(?:بقدر|اقدر|ممكن|مسموحلي)\s*(?:انزل|اسجل|اخذ)",
        normalized,
    ) or re.search(
        r"(?:شو|ايش|ماذا|what).{0,25}(?:بتنصحني|تنصحني|اقترح|ترشح|recommend|suggest)",
        normalized,
    ) or re.search(
        r"(?:شو|ايش).{0,20}(?:انزل|اسجل|اخذ).{0,20}(?:الفصل\s+الجاي|الفصل\s+القادم|السمستر\s+الجاي|next\s+semester)",
        normalized,
    ) or re.search(
        r"(?:شو\s+انزل|شو\s+اسجل|what\s+should\s+i\s+take|recommend\s+courses|اقترح\s+علي\s+مواد|رشحلي\s+مواد)",
        normalized,
    ):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.COURSE_RECOMMENDATIONS.value,
        )

    # 3. Individual Course Grade: "كم علامتي بتعلم الآلة؟" / "شو جبت ببرمجة الحاسوب 2؟"
    grade_match = re.search(
        r"(?:علامتي|درجتي|جبت|نتيجة|علام[ةه])\s*(?:مساق|مادة|كورس|course)?\s*(?:بـ?|في|for|in)?\s*(.+)",
        normalized,
    )
    if grade_match and not re.search(r"(?:معدلي|المعدل|تراكمي|النجاح)", normalize_academic_text(grade_match.group(0))):
        target = _map_span_to_raw(raw_message, grade_match.span(1))
        if not target and _has_pronoun_reference(normalized) and context_courses:
            target = context_courses[0]
        mentions, codes = _assign_mentions_and_codes(target, codes_in_message)
        if mentions or codes:
            return RawAdvisorInterpretation(
                intent=AdvisorIntent.COURSE_INFORMATION.value,
                course_mentions=mentions,
                course_codes_mentioned=codes,
                clarification_hint="COURSE_GRADE",
            )

    # 4. Course Prerequisites: "شو متطلبات تعلم الآلة؟" / "شو متطلباتها؟"
    prereq_match = re.search(
        r"(?:متطلب(?:ات)?|متطلب\s+سابق|شروط|prereq|prerequisites?)\s*(?:مساق|مادة|كورس|course)?\s*(?:لـ?|في|for|of)?\s*(.+)",
        normalized,
    )
    if prereq_match:
        target = _map_span_to_raw(raw_message, prereq_match.span(1))
        if not target and (_has_pronoun_reference(normalized) or "متطلباتها" in normalized) and context_courses:
            target = context_courses[0]
        mentions, codes = _assign_mentions_and_codes(target, codes_in_message)
        if mentions or codes:
            return RawAdvisorInterpretation(
                intent=AdvisorIntent.COURSE_INFORMATION.value,
                course_mentions=mentions,
                course_codes_mentioned=codes,
                clarification_hint="PREREQUISITES",
            )
    elif ("متطلب" in normalized or "prereq" in normalized) and (_has_pronoun_reference(normalized) or "متطلباتها" in normalized) and context_courses:
        mentions, codes = _assign_mentions_and_codes(context_courses[0], codes_in_message)
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.COURSE_INFORMATION.value,
            course_mentions=mentions,
            course_codes_mentioned=codes,
            clarification_hint="PREREQUISITES",
        )

    # 5. Course Difficulty: "شو صعوبة تعلم الآلة؟" / "هل تعلم الآلة صعبة علي؟" / "صعوبتها؟"
    diff_prefix_match = re.search(
        r"(?:صعوب[ةه]|difficulty|workload)\s*(?:مساق|مادة|كورس|course)?\s*(?:لـ?|في|for|of)?\s*(.+)",
        normalized,
    )
    diff_suffix_match = re.search(
        r"(?:هل|is)?\s*(?:مساق|مادة|كورس|course)?\s*(.+?)\s*(?:صعب|صعبة|صعبة\s+علي|صعبه|سهل|سهلة|difficult|hard)",
        normalized,
    )
    if diff_prefix_match:
        target = _map_span_to_raw(raw_message, diff_prefix_match.span(1))
        if not target and (_has_pronoun_reference(normalized) or "صعوبتها" in normalized) and context_courses:
            target = context_courses[0]
        mentions, codes = _assign_mentions_and_codes(target, codes_in_message)
        if mentions or codes:
            return RawAdvisorInterpretation(
                intent=AdvisorIntent.COURSE_INFORMATION.value,
                course_mentions=mentions,
                course_codes_mentioned=codes,
                clarification_hint="COURSE_DIFFICULTY",
            )
    elif diff_suffix_match:
        target = _map_span_to_raw(raw_message, diff_suffix_match.span(1))
        if not target and _has_pronoun_reference(normalized) and context_courses:
            target = context_courses[0]
        mentions, codes = _assign_mentions_and_codes(target, codes_in_message)
        if mentions or codes:
            return RawAdvisorInterpretation(
                intent=AdvisorIntent.COURSE_INFORMATION.value,
                course_mentions=mentions,
                course_codes_mentioned=codes,
                clarification_hint="COURSE_DIFFICULTY",
            )
    elif ("صعب" in normalized or "صعوب" in normalized or "سهل" in normalized or "difficult" in normalized) and (_has_pronoun_reference(normalized) or "صعوبتها" in normalized) and context_courses:
        mentions, codes = _assign_mentions_and_codes(context_courses[0], codes_in_message)
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.COURSE_INFORMATION.value,
            course_mentions=mentions,
            course_codes_mentioned=codes,
            clarification_hint="COURSE_DIFFICULTY",
        )

    # 6. Course Passing Grade: "كم علامة النجاح في تعلم الآلة؟"
    pass_grade_match = re.search(
        r"(?:علام[ةه]\s+النجاح|passing\s+grade)\s*(?:مساق|مادة|كورس|course)?\s*(?:بـ?|في|for)?\s*(.+)",
        normalized,
    )
    if pass_grade_match:
        target = _map_span_to_raw(raw_message, pass_grade_match.span(1))
        if not target and _has_pronoun_reference(normalized) and context_courses:
            target = context_courses[0]
        mentions, codes = _assign_mentions_and_codes(target, codes_in_message)
        if mentions or codes:
            return RawAdvisorInterpretation(
                intent=AdvisorIntent.COURSE_INFORMATION.value,
                course_mentions=mentions,
                course_codes_mentioned=codes,
                clarification_hint="PASSING_GRADE",
            )

    # 7. Course Eligibility: "هل بقدر أنزل تعلم الآلة؟" / "ليش ما بقدر أسجلها؟"
    eligibility_prefix_match = re.search(
        r"(?:بقدر|اقدر|استطيع|مسموحلي|مسموح\s+لي|مؤهل|can\s+i|am\s+i\s+eligible)\s+(?:انزل|اسجل|اخذ|تسجيل|تنزيل|take|register|enroll)\s*(?:مساق|مادة|كورس|course)?\s*(.*)",
        normalized,
    )
    eligibility_why_match = re.search(
        r"(?:ما\s+بقدر|مش\s+قادر|مش\s+مسموح|مش\s+مسموحلي|cant|cannot)\s+(?:انزل|اسجل|اخذ|take|register|enroll)\s*(?:مساق|مادة|كورس|course)?\s*(.*)",
        normalized,
    )
    eligibility_pronoun_match = re.search(
        r"(?:بقدر\s+انزلها|بقدر\s+اسجلها|اقدر\s+انزلها|اقدر\s+اسجلها|ليش\s+ما\s+بقدر\s+انزلها|ليش\s+ما\s+بقدر\s+اسجلها|بقدر\s+اخذها|ليش\s+مش\s+مسموحلي\s+انزلها)",
        normalized,
    )

    if eligibility_pronoun_match and context_courses:
        mentions, codes = _assign_mentions_and_codes(context_courses[0], codes_in_message)
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.COURSE_ELIGIBILITY.value,
            course_mentions=mentions,
            course_codes_mentioned=codes,
        )

    matched_eligibility = eligibility_prefix_match or eligibility_why_match
    if matched_eligibility:
        raw_target = _map_span_to_raw(raw_message, matched_eligibility.span(1)).strip()
        mentions, codes = _assign_mentions_and_codes(raw_target, codes_in_message)
        if mentions or codes:
            return RawAdvisorInterpretation(
                intent=AdvisorIntent.COURSE_ELIGIBILITY.value,
                course_mentions=mentions,
                course_codes_mentioned=codes,
            )
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.COURSE_RECOMMENDATIONS.value,
        )

    # 7. Recommendations / Available Courses: "شو المواد اللي بقدر أنزلها؟" / "شو بتنصحني أسجل؟"
    if re.search(
        r"(?:شو|ايش|ما|ماهي|what|which).{0,25}(?:المواد|المساقات|مواد|مساقات|courses?).{0,25}(?:بقدر|اقدر|ممكن|متاحة|can\s+i|available)",
        normalized,
    ) or re.search(
        r"(?:شو|ايش|ماذا|what).{0,25}(?:بتنصحني|تنصحني|اقترح|ترشح|recommend|suggest)",
        normalized,
    ) or re.search(
        r"(?:شو|ايش).{0,20}(?:انزل|اسجل|اخذ).{0,20}(?:الفصل\s+الجاي|الفصل\s+القادم|السمستر\s+الجاي|next\s+semester)",
        normalized,
    ) or re.search(
        r"(?:شو\s+انزل|شو\s+اسجل|what\s+should\s+i\s+take|recommend\s+courses|اقترح\s+علي\s+مواد|رشحلي\s+مواد)",
        normalized,
    ):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.COURSE_RECOMMENDATIONS.value,
        )

    # 8. Remaining Requirements / Credits: "كم ساعة مجتاز؟" / "كم ضايل علي؟" / "قديش باقي للتخرج؟"
    has_credits_term = bool(re.search(r"(?:ساع[ةه]|ساعات|credits?)", normalized))
    has_passed_credits_term = bool(re.search(r"(?:مجتاز|قطعت|خلصت|انهيت|passed|completed|منجز)", normalized))
    has_remaining_term = bool(re.search(r"(?:ضايل|باقي|متبقي|left|remaining)", normalized))
    has_graduation_term = bool(re.search(r"(?:علي|للتخرج|عالتخرج|تخرج|graduate|graduation)", normalized))

    if (has_credits_term and has_passed_credits_term) or \
       (has_credits_term and has_remaining_term) or \
       (has_remaining_term and has_graduation_term) or \
       re.search(r"\b(?:ساعاتي\s+المتبقية|ساعاتي\s+المجتازة|remaining\s+credits|credits\s+left|hours\s+remaining)\b", normalized):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.REMAINING_REQUIREMENTS.value,
        )

    # 9. Academic Status: Passed Courses / Currently Enrolled / GPA
    has_course_noun = bool(re.search(r"(?:المواد|المساقات|مواد|مساقات|courses?)", normalized))
    # 9a. Passed courses
    if has_course_noun and re.search(r"(?:خلصت|خلصتها|نجحت\s+فيها|نجحت|انهيتها|اجتزتها|passed|completed|المجتازة|المنجزة)", normalized):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.ACADEMIC_STATUS.value,
            clarification_hint="PASSED_COURSES",
        )
    if re.search(r"(?:المساقات\s+المجتازة|المواد\s+المجتازة|شو\s+خلصت\s+مواد)", normalized):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.ACADEMIC_STATUS.value,
            clarification_hint="PASSED_COURSES",
        )

    # 9b. Currently enrolled courses
    if (has_course_noun and re.search(r"(?:مسجلها|منزلها|مسجل|منزل|registered|enrolled)", normalized)) or \
       re.search(r"(?:شو\s+مسجل|شو\s+منزل).{0,20}(?:هسا|حاليا|الان|هذا\s+الفصل|الفصل\s+الحالي)", normalized) or \
       re.search(r"(?:جدولي\s+الحالي|موادي\s+الحالية|المواد\s+المسجلة|المساقات\s+المسجلة)", normalized):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.ACADEMIC_STATUS.value,
            clarification_hint="ENROLLED_COURSES",
        )

    # 9c. GPA / Academic Record
    if re.search(
        r"(?:كم|قديش|شو|ايش|ما|how\s+much|what\s+is).{0,20}(?:معدلي|ال\s*gpa|gpa|المعدل\s+التراكمي|معدلي\s+التراكمي|علاماتي|درجاتي|سجلي)",
        normalized,
    ) or re.search(
        r"\b(?:معدلي|معدل\s+تراكمي|المعدل\s+التراكمي|my\s+gpa|\bgpa\b|كشف\s+علاماتي|سجلي\s+الاكاديمي|علاماتي|درجاتي)\b",
        normalized,
    ):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.ACADEMIC_STATUS.value,
            clarification_hint="GPA",
        )

    # 10. Semester Planning & Degree Path Modeling
    if re.search(r"(?:مسار|خط[ةه]).{0,35}(?:تخرج|درج[ةه])|(?:degree|graduation)\s+path", normalized):
        hours_match = re.search(r"(\d{1,2})\s*(?:ساع|credit)", normalized)
        hours = int(hours_match.group(1)) if hours_match else None
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.DEGREE_PATH_MODELING.value,
            max_credit_hours_per_semester=hours,
        )
    if re.search(r"(?:خطة|خطه|تخطيط).{0,35}(?:فصل|سمستر)|(?:semester|term)\s+plan", normalized):
        hours_match = re.search(r"(\d{1,2})\s*(?:ساع|credit)", normalized)
        hours = int(hours_match.group(1)) if hours_match else None
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.SEMESTER_PLANNING.value,
            max_credit_hours_per_semester=hours,
        )

    return None
