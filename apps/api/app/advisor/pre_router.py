"""High-confidence deterministic academic pre-router for Morshidi AI.

Directly routes clear academic requests to deterministic academic intents
before trusting ungrounded LLM provider classifications.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import replace

from app.advisor.models import AdvisorIntent
from app.advisor.provider import RawAdvisorInterpretation


def normalize_academic_text(value: str) -> str:
    """Normalize Arabic and English query text for robust intent matching."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[\u064b-\u065f\u0670]", "", normalized)
    normalized = normalized.translate(str.maketrans("أإآى", "اااي"))
    normalized = normalized.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return normalized


def is_student_intelligence_query(message: str) -> bool:
    """Recognize self-understanding questions without relying on exact phrases."""
    normalized = normalize_academic_text(message)
    strength_or_growth = re.search(
        r"(?:اقو[ىي]|افضل).{0,20}(?:مهارات|قدرات)|(?:نقاط\s+)?(?:قوتي|ضعفي)|"
        r"(?:بشو|في\s+ماذا).{0,12}(?:انا\s+)?قوي|(?:شو|ايش|ماذا).{0,18}(?:اطور|احسن)|"
        r"(?:حلل|تحليل|قيم|تقييم).{0,24}(?:ادائي|مستواي|مهاراتي|سجلي)|"
        r"(?:strongest|best)\s+(?:skills?|abilities)|strengths?|weaknesses?|"
        r"what\s+should\s+i\s+improve|analy[sz]e.{0,20}(?:strengths?|performance)",
        normalized,
    )
    evidence_basis = re.search(
        r"(?:علي|على)\s+شو\s+بنيت|(?:شو|ايش|ما).{0,15}(?:الدليل|الادله|الادلة|ادلتك)|"
        r"(?:كيف|ليش).{0,18}(?:قيمتني|تقييمك)|what\s+evidence|basis\s+for\s+(?:your\s+)?assessment",
        normalized,
    )
    return bool(strength_or_growth or evidence_basis)


def is_personalized_course_fit_query(message: str) -> bool:
    """Recognize requests to personalize/rank an otherwise legal course set."""
    normalized = normalize_academic_text(message)
    if not re.search(r"(?:مواد|المواد|مساقات|المساقات|ماده|مساق|فصل|courses?|classes?|semester)", normalized):
        return False
    return bool(re.search(
        r"(?:انسب|مناسب|بتناسب).{0,28}(?:الي|لي|ني)|(?:رتب|ترتيب).{0,30}(?:المواد|المساقات)|"
        r"(?:اسهل|اقل\s+صعوبه).{0,20}(?:علي|الي|لي)|"
        r"(?:بناء|حسب).{0,28}(?:ادائي|علاماتي|مستواي|قدراتي|مهاراتي)|"
        r"(?:best\s+fit|most\s+suitable|rank).{0,35}(?:eligible|allowed|courses?)|"
        r"courses?.{0,35}(?:based\s+on\s+my|for\s+me)|(?:ضعف|قوت).{0,35}(?:الفصل\s+الجاي|الفصل\s+القادم)",
        normalized,
    ))


def requests_full_eligible_list(message: str) -> bool:
    """Return whether the student explicitly requested the complete eligible set."""
    normalized = normalize_academic_text(message)
    return bool(re.search(
        r"(?:كل|جميع).{0,18}(?:المواد|المساقات).{0,18}(?:المسموح|المؤهل)|"
        r"(?:القائم[ةه]).{0,12}(?:الكامل[ةه]|كامل[ةه])|"
        r"(?:اعرض|اظهر|احكي).{0,18}(?:كل|جميع).{0,12}(?:المواد|المساقات)|"
        r"(?:full|complete)\s+(?:eligible[- ]course\s+)?list|all\s+eligible\s+courses?",
        normalized,
    ))


def extract_course_codes(text: str) -> tuple[str, ...]:
    """Find 6 to 8 digit course codes in text."""
    matches = re.findall(r"(?<!\d)\d{6,8}(?!\d)", text)
    return tuple(dict.fromkeys(matches))


def extract_context_courses(conversation_context: str) -> tuple[str, ...]:
    """Extract candidate course names and codes from recent conversation context, prioritized by recency."""
    if not conversation_context:
        return ()

    positioned: list[tuple[int, str]] = []

    # 1. Names before explicit course codes in parentheses, e.g. "تعلم الآلة (1505311)" or "مساق تعلم الآلة (1505311)"
    for match in re.finditer(
        r"([^\(\)\n\r,،:؛\.]{2,40})\s*\((\d{6,8})\)",
        conversation_context,
    ):
        raw_name = match.group(1).strip()
        name = _clean_course_reference(raw_name)
        if name:
            positioned.append((match.end(), name))
        # Prefer the canonical code over surrounding assistant prose when both
        # describe the same most-recent reference.
        positioned.append((match.end() + 1, match.group(2)))

    # 2. Look for explicit course title patterns in context like مساق (...) or مادة (...)
    for match in re.finditer(
        r"(?:مساق|مادة|كورس|course)\s+([^\(\)\n\r,،:؛\.]{2,40})",
        conversation_context,
        re.IGNORECASE,
    ):
        raw_name = match.group(1).strip()
        name = _clean_course_reference(raw_name)
        if name:
            positioned.append((match.end(), name))

    # 3. Look for course queries in previous user messages like "احكيلي عن (...)"
    for match in re.finditer(
        r"(?:احكيلي\s+عن|معلومات\s+عن|اعطيني\s+معلومات\s+عن|بدي\s+اعرف\s+عن|tell\s+me\s+about)\s+([^\(\)\n\r,،:؛\.\?؟]{2,40})",
        conversation_context,
        re.IGNORECASE,
    ):
        raw_name = match.group(1).strip()
        name = _clean_course_reference(raw_name)
        if name:
            positioned.append((match.end(), name))

    # 4. Look for course codes
    for match in re.finditer(r"(?<!\d)\d{6,8}(?!\d)", conversation_context):
        positioned.append((match.end(), match.group(0)))

    # Sort descending by position so the most recently mentioned course in context comes first
    positioned.sort(key=lambda item: item[0], reverse=True)

    courses: list[str] = []
    for _, item in positioned:
        if item not in courses:
            courses.append(item)

    return tuple(courses)


def _latest_user_message(conversation_context: str) -> str | None:
    """Return only the newest bounded USER turn, never assistant prose."""
    for line in reversed(conversation_context.splitlines()):
        role, separator, content = line.partition(":")
        if separator and role.strip().upper() == "USER" and content.strip():
            return content.strip()
    return None


def _is_explanation_follow_up(normalized: str) -> bool:
    """Recognize short requests that explain the immediately preceding result."""
    return bool(re.fullmatch(
        r"(?:طيب\s+|طب\s+)?(?:ليش|لماذا|وضح(?:لي)?|اشرح(?:لي)?|"
        r"كيف\s+(?:هيك|عرفت)|why|why\s+is\s+that|explain(?:\s+why)?)\s*[?؟!]*",
        normalized.strip(),
    ))


def _is_deictic_course_reference(value: str) -> bool:
    normalized = normalize_academic_text(_clean_course_reference(value))
    return bool(re.fullmatch(
        r"(?:هاي|هذي|هذه|هالماد[ةه]|هالمساق|الماد[ةه]\s+هاي|المساق\s+هذا|"
        r"هاي\s+الماد[ةه]|هاي\s+المساق|this\s+(?:course|class)|it|ها|عنها|عنه)",
        normalized,
    ))


def _has_pronoun_reference(normalized: str) -> bool:
    """Check if query uses an Arabic pronoun or indirect reference to a course."""
    pronoun_patterns = [
        r"(?:انزلها|اسجلها|اخذها|انزلهم|اسجلهم)",
        r"(?:متطلباتها|متطلبها|شروطها)",
        r"(?:صعوبتها|صعبة\s+علي|صعبة\s+ولا\s+سهلة|سهلة\s+ولا\s+صعبة|صعبه\s+علي|صعب\s+علي)",
        r"(?:علامتها|درجتها|علامتي\s+فيها|جبت\s+فيها)",
        r"(?:رسبت\s+فيها|رسبت\s+فيه|سقطت\s+فيها|اعدتها|اعدته|فشلت\s+فيها)",
        r"(?:أجلتها|اجلتها|أجلته|اجلته|حذفتها|حذفته|اسقطتها|اسقطته)",
        r"(?:بخطتي|خطتي|تاثيرها|تأثيرها|اثرها|أثرها)",
        r"(?:عنها|عنه|فيها|فيه|عليها|عليه|لها|له)\s*[\?؟]?$",
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
    prefix_pattern = (
        r"^(?:"
        r"هل\s+بقدر\s+[اأإآ]نزل|هل\s+بقدر\s+[اأإآ]سجل|بقدر\s+[اأإآ]نزل|بقدر\s+[اأإآ]سجل|[اأإآ]قدر\s+[اأإآ]نزل|[اأإآ]قدر\s+[اأإآ]سجل|"
        r"ليش\s+ما\s+بقدر\s+[اأإآ]نزل|ليش\s+ما\s+بقدر\s+[اأإآ]سجل|ليش\s+مش\s+قادر\s+[اأإآ]نزل|ليش\s+مش\s+قادر\s+[اأإآ]سجل|"
        r"شو\s+متطلبات|ما\s+هي\s+متطلبات|ماهي\s+متطلبات|متطلبات\s+مساق|متطلبات\s+مادة|متطلبات|"
        r"شو\s+صعوبة|ما\s+صعوبة|صعوبة\s+مساق|صعوبة\s+مادة|صعوبة|"
        r"كم\s+علامتي\s+بـ?|كم\s+علامتي\s+في|شو\s+جبت\s+بـ?|شو\s+جبت\s+في|علامتي\s+في|علامتي\s+بـ?|"
        r"كم\s+علامة\s+النجاح\s+في|كم\s+علامة\s+النجاح\s+بـ?|علامة\s+النجاح\s+في|علامة\s+النجاح\s+بـ?|"
        r"احكيلي\s+(?:اكثر\s+)?(?:عن|ع)|احكيلي|"
        r"اعطيني\s+(?:معلومات|تفاصيل|نبذة|فكره|فكرة)\s*(?:عن|ع)?|"
        r"بدي\s+(?:اعرف|معلومات|تفاصيل|نبذة)\s*(?:عن|ع)?|"
        r"معلومات\s+(?:عن|ع)?|تفاصيل\s+(?:عن|ع)?|نبذة\s+(?:عن|ع)?|"
        r"عرفني\s+(?:علي|على|عن|ع)|"
        r"شو\s+(?:هي|هو)\s*(?:مادة|مساق|كورس)?|"
        r"ما\s+(?:هي|هو)\s*(?:مادة|مساق|كورس)?|"
        r"ماهي\s*(?:مادة|مساق|كورس)?|ماهو\s*(?:مادة|مساق|كورس)?|"
        r"شو\s+(?:مادة|مساق|كورس)|"
        r"tell\s+me\s+(?:more\s+)?about|"
        r"what\s+is(?:\s+the\s+course)?|"
        r"give\s+me\s+(?:information|info|details)\s+about|"
        r"information\s+about|info\s+about|details\s+about|"
        r"(?:ال)?(?:مساق|مادة|كورس)|the\s+course|course"
        r")\s*"
    )
    while True:
        new_cleaned = re.sub(prefix_pattern, "", cleaned, flags=re.IGNORECASE).strip()
        if new_cleaned == cleaned:
            break
        cleaned = new_cleaned

    if cleaned.startswith("ب") and len(cleaned) > 3 and not (cleaned.startswith("برمج") or cleaned.startswith("بيان")):
        cleaned = cleaned[1:].strip()
    elif cleaned.startswith("في ") or cleaned.startswith("في\t"):
        cleaned = cleaned[2:].strip()
    elif cleaned.startswith("عن ") or cleaned.startswith("عن\t"):
        cleaned = cleaned[2:].strip()
    elif cleaned.startswith("لـ") or cleaned.startswith("ل "):
        cleaned = cleaned[2:].strip()

    cleaned = re.sub(r"[\?؟!\.،,\s]+$", "", cleaned).strip()
    if cleaned in ("المساق", "المادة", "الكورس", "مساق", "مادة", "كورس", "course", "the course"):
        cleaned = ""
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

    # Guard 1: General non-academic conversational/history/trivia topics (e.g. "احكيلي عن الحرب العالمية الثانية")
    if re.search(r"(?:حرب|سياس[ةه]|طقس|طبخ|افلام|أفلام|اغاني|أغاني|مسلسل|رياض[ةه]|كر[ةه]\s+قدم|نكت[ةه]|war|weather|movie|song)", normalized):
        return None

    # A compact "why?" should keep the last deterministic academic intent and
    # request its evidence explanation. We intentionally inspect only the most
    # recent USER turn, never model-authored prose, and recurse without context
    # so an ambiguous chain still falls back to the semantic provider.
    if _is_explanation_follow_up(normalized):
        previous_message = _latest_user_message(conversation_context)
        if previous_message:
            previous = pre_route_academic_intent(previous_message)
            if previous is not None:
                return replace(
                    previous,
                    requested_facets=tuple(dict.fromkeys(
                        (*previous.requested_facets, "EVIDENCE_EXPLANATION")
                    )),
                )

    # Guard 2: Definition inquiries (e.g. "شو يعني prerequisite؟") are general academic info, not course inquiries
    if re.search(r"(?:شو\s+يعني|ما\s+معنى|معنى|ماذا\s+يعني|what\s+does\s+.+mean|meaning\s+of)", normalized) or re.fullmatch(
        r"(?:what\s+(?:is|are)\s+(?:an?\s+|the\s+)?|(?:explain|define)\s+)(?:prerequisites?|course\s+requirements?)\s*[?؟]?",
        normalized,
    ):
        return None

    # Course fit takes precedence for a compound strengths + suitable-courses
    # request so the deterministic eligible set remains the structured carrier.
    if is_personalized_course_fit_query(raw_message):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.COURSE_RECOMMENDATIONS.value,
            clarification_hint="PERSONALIZED_ELIGIBLE_COURSE_FIT",
        )

    # Student self-understanding is distinct from GPA/progress. The existing
    # ACADEMIC_STATUS route remains the structured academic carrier while the
    # service composes the bounded V2 intelligence explanation.
    if is_student_intelligence_query(raw_message):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.ACADEMIC_STATUS.value,
            clarification_hint="STUDENT_INTELLIGENCE",
        )

    # Personal record questions are direct authenticated reads. Route them
    # before the broad English "what is ..." course-information expression.
    if re.search(
        r"(?:what\s+is|show|tell\s+me).{0,24}(?:my\s+)?(?:gpa|academic\s+record|transcript)|"
        r"(?:my\s+gpa|my\s+academic\s+record|my\s+transcript)",
        normalized,
    ):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.ACADEMIC_STATUS.value,
            clarification_hint="GPA" if "gpa" in normalized else "ACADEMIC_RECORD",
        )

    # 0. Option Comparison: "طيب قارنلي الحلين" / "قارن بين الخيارين" / "compare the two options"
    if re.search(
        r"(?:طيب\s+|طب\s+)?(?:قارن(?:لي)?|مقارن[ةه])\s*(?:بين\s+)?(?:الحلين|الخيارين|الخطتين|المسارين|options?|solutions?|paths?|plans?)",
        normalized,
    ) or re.search(
        r"compare\s+(?:the\s+)?(?:two\s+)?(?:options?|solutions?|paths?|plans?)",
        normalized,
    ):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.OPTION_COMPARISON.value,
            option_references=(1, 2),
            requested_facets=("COMPARISON",),
        )

    # 0b. Compound Multi-Tool Academic Request
    if (
        ("ضايل" in normalized or "باقي" in normalized or "remaining" in normalized)
        and ("جدول" in normalized or "خطة" in normalized or "plan" in normalized or "انزل" in normalized or "schedule" in normalized)
        and ("تخرج" in normalized or "اتخرج" in normalized or "graduate" in normalized or "سنة" in normalized or "سنه" in normalized or "مسار" in normalized)
    ):
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.SEMESTER_PLANNING.value,
            clarification_hint="COMPOUND_ACADEMIC_PLANNING",
            requested_facets=("REMAINING_REQUIREMENTS", "SEMESTER_PLAN", "DEGREE_PATH", "COMPARISON"),
        )

    # 0c. What-If and Plan Impact Follow-ups with context courses
    if re.search(
        r"(?:و?إذا|و?اذا|و?لو|what\s+if)\s+(?:رسبت|فشلت|اعدت|تأخرت|تاخرت|أجلت|اجلت|fail|retake|drop|delay)",
        normalized,
    ) or re.search(
        r"(?:شو|ايش|ماذا|how).{0,20}(?:يت[اأ]ثر|رح\s+يت[اأ]ثر|بت[اأ]ثر|ت[اأ]ثير).{0,20}(?:بخطتي|خطتي|مساري|plan|degree)",
        normalized,
    ):
        target_course = context_courses[0] if context_courses else ""
        mentions, codes = _assign_mentions_and_codes(target_course, codes_in_message)
        if mentions or codes:
            return RawAdvisorInterpretation(
                intent=AdvisorIntent.DEGREE_PATH_MODELING.value,
                course_mentions=mentions,
                course_codes_mentioned=codes,
                clarification_hint="PLAN_IMPACT_WHAT_IF",
                requested_facets=("WHAT_IF", "PREREQUISITE_IMPACT"),
            )

    # 1. Course Comparison: "قارنلي بين X و Y" / "مقارنة بين X و Y"
    comparison_match = re.search(
        r"(?:قارن(?:لي)?|مقارن[ةه])\s+(?:بين\s+)?(.+?)\s+(?:و\s*|مع\s+)(.+)|"
        r"compare\s+(?:between\s+)?(.+?)\s+(?:and|with|versus|vs\.?)\s+(.+)",
        normalized,
    )
    if comparison_match:
        first_group, second_group = ((1, 2) if comparison_match.group(1) is not None else (3, 4))
        c1_raw = _map_span_to_raw(raw_message, comparison_match.span(first_group))
        c2_raw = _map_span_to_raw(raw_message, comparison_match.span(second_group))
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
    ) or re.search(
        r"what\s+(?:courses?|classes?)\s+should\s+i\s+take(?:\s+(?:next|this)\s+(?:semester|term))?",
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
        if (not target or _is_deictic_course_reference(target)) and _has_pronoun_reference(normalized) and context_courses:
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
        if (not target or _is_deictic_course_reference(target)) and (_has_pronoun_reference(normalized) or "متطلباتها" in normalized or _is_deictic_course_reference(target)) and context_courses:
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
        r"(?:صعوب[ةه]|(?:how\s+)?(?:difficult|hard)|difficulty|workload)\s*(?:مساق|مادة|كورس|course)?\s*(?:is|لـ?|في|for|of)?\s*(.+)",
        normalized,
    )
    diff_suffix_match = re.search(
        r"(?:هل|is)?\s*(?:مساق|مادة|كورس|course)?\s*(.+?)\s*(?:صعب|صعبة|صعبة\s+علي|صعبه|سهل|سهلة|difficult|hard)",
        normalized,
    )
    if diff_prefix_match:
        target = _map_span_to_raw(raw_message, diff_prefix_match.span(1))
        if (not target or _is_deictic_course_reference(target)) and (_has_pronoun_reference(normalized) or "صعوبتها" in normalized or _is_deictic_course_reference(target)) and context_courses:
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
        if (not target or _is_deictic_course_reference(target)) and _has_pronoun_reference(normalized) and context_courses:
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
        r"(?:بقدر|اقدر|استطيع|مسموحلي|مسموح\s+لي|مؤهل|can\s+i|am\s+i\s+eligible)\s+(?:to\s+)?(?:انزل|اسجل|اخذ|تسجيل|تنزيل|take|register|enroll)\s*(?:in\s+)?(?:مساق|مادة|كورس|course)?\s*(.*)",
        normalized,
    )
    eligibility_why_match = re.search(
        r"(?:ما\s+بقدر|مش\s+قادر|مش\s+مسموح|مش\s+مسموحلي|(?:النظام\s+)?مش\s+سامحلي|cant|cannot)\s+(?:انزل|اسجل|اخذ|take|register|enroll)\s*(?:مساق|مادة|كورس|course)?\s*(.*)",
        normalized,
    )
    eligibility_pronoun_match = re.search(
        r"(?:بقدر|اقدر|استطيع|ممكن|مسموحلي|ليش\s+ما\s+بقدر|ليش\s+مش\s+قادر|ليش\s+مش\s+مسموحلي|ليش\s+ما\s+اقدر)\s+(?:انزلها|اسجلها|اخذها)",
        normalized,
    ) or re.search(
        r"(?:انزلها|اسجلها|اخذها)\s*[\?؟]?$",
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
        if _is_deictic_course_reference(raw_target) and context_courses:
            raw_target = context_courses[0]
        mentions, codes = _assign_mentions_and_codes(raw_target, codes_in_message)
        if mentions or codes:
            return RawAdvisorInterpretation(
                intent=AdvisorIntent.COURSE_ELIGIBILITY.value,
                course_mentions=mentions,
                course_codes_mentioned=codes,
            )
        if raw_target and _clean_course_reference(raw_target) == "":
            return RawAdvisorInterpretation(
                intent=AdvisorIntent.COURSE_ELIGIBILITY.value,
                course_mentions=(),
                course_codes_mentioned=(),
            )
        return RawAdvisorInterpretation(
            intent=AdvisorIntent.COURSE_RECOMMENDATIONS.value,
        )

    # 8. Generic Course Information:
    # "احكيلي عن تعلم الآلة" / "شو هي تعلم الآلة؟" / "اعطيني معلومات عن تعلم الآلة" / "Tell me about Machine Learning"
    if not re.search(r"(?:بشكل\s+عام|in\s+general)", normalized):
        info_match = re.search(
            r"(?:"
            r"احكيلي\s+(?:اكثر\s+)?(?:عن|ع)|"
            r"اعطيني\s+(?:معلومات|تفاصيل|نبذة|فكره|فكرة)\s*(?:عن|ع)?|"
            r"بدي\s+(?:اعرف|معلومات|تفاصيل|نبذة)\s*(?:عن|ع)?|"
            r"معلومات\s+(?:عن|ع)?|"
            r"تفاصيل\s+(?:عن|ع)?|"
            r"نبذة\s+(?:عن|ع)?|"
            r"عرفني\s+(?:علي|على|عن|ع)|"
            r"شو\s+(?:هي|هو)\s*(?:مادة|مساق|كورس)?|"
            r"ما\s+(?:هي|هو)\s*(?:مادة|مساق|كورس)?|"
            r"ماهي\s*(?:مادة|مساق|كورس)?|"
            r"ماهو\s*(?:مادة|مساق|كورس)?|"
            r"شو\s+(?:مادة|مساق|كورس)|"
            r"tell\s+me\s+(?:more\s+)?about|"
            r"what\s+is(?:\s+the\s+course)?|"
            r"give\s+me\s+(?:information|info|details)\s+about|"
            r"information\s+about|info\s+about|details\s+about"
            r")\s*(.+)",
            normalized,
        )
        if info_match:
            target = _map_span_to_raw(raw_message, info_match.span(1))
            target_clean = _clean_course_reference(target)
            if (not target_clean or _has_pronoun_reference(normalized) or _is_deictic_course_reference(target_clean)) and context_courses:
                target = context_courses[0]
            mentions, codes = _assign_mentions_and_codes(target, codes_in_message)
            if mentions or codes:
                return RawAdvisorInterpretation(
                    intent=AdvisorIntent.COURSE_INFORMATION.value,
                    course_mentions=mentions,
                    course_codes_mentioned=codes,
                    clarification_hint="GENERAL_COURSE_INFORMATION",
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
