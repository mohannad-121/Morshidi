"""Bounded, non-authoritative context from explicitly stated planning preferences and long-term memories."""

import re
from typing import Any, Mapping

SUPPORTED_MEMORY_CATEGORIES = (
    "ACADEMIC_INTEREST",
    "WORKLOAD_PREFERENCE",
    "CAREER_GOAL",
    "SCHEDULE_CONSTRAINT",
)

ACADEMIC_FACT_BLOCKLIST = re.compile(
    r"(?:"
    r"معدل|معدلي|تراكمي|علامة|علامات|علامتي|درجة|درجات|درجتي|"
    r"gpa|grade|grades|credit|credits|ساعة|ساعات|مجتاز|مخلص|ناجح|راسب|"
    r"إنذار|انذار|مفصول|متطلب|متطلبات|prerequisite|prerequisites|eligible|eligibility"
    r")",
    re.IGNORECASE,
)

DAYS_MAP_AR = {
    "الخميس": "الخميس",
    "الأحد": "الأحد",
    "الاحد": "الأحد",
    "الاثنين": "الاثنين",
    "الإثنين": "الاثنين",
    "الثلاثاء": "الثلاثاء",
    "الأربعاء": "الأربعاء",
    "الاربعاء": "الأربعاء",
    "السبت": "السبت",
    "الجمعة": "الجمعة",
}

DAYS_MAP_EN = {
    "monday": "Monday",
    "tuesday": "Tuesday",
    "wednesday": "Wednesday",
    "thursday": "Thursday",
    "friday": "Friday",
    "saturday": "Saturday",
    "sunday": "Sunday",
}


def _contains_academic_facts(text: str) -> bool:
    """Strict guard: never let academic facts, grades, credits, or GPAs enter memory."""
    if re.search(r"\b\d+(?:\.\d+)?\b", text):
        return True
    return bool(ACADEMIC_FACT_BLOCKLIST.search(text))


def _extract_academic_interest(text: str) -> dict[str, str] | None:
    m_ar = re.search(
        r"(?:^|[\s،,])(?:و\s*)?(?:أنا\s+|انا\s+)?(?:مهتم|اهتمامي|أمiel|اميل)\s+(?:بـ?|في\s+|لـ?)?(?:مجال\s+)?([^،,\.\n\?!;]{3,50})",
        text,
        re.IGNORECASE,
    )
    if m_ar:
        raw_topic = m_ar.group(1).strip()
        cleaned = re.split(r"\s+(?:و\s*بدي|و\s*أريد|و\s*اريد|لأن|عشان|بس|لكن|and\s+i)\b", raw_topic)[0].strip()
        cleaned = re.sub(r"^(?:ب?مجال\s+|بـ?|في\s+)", "", cleaned).strip()
        if len(cleaned) >= 3 and not _contains_academic_facts(cleaned):
            return {
                "category": "ACADEMIC_INTEREST",
                "key": "academic_interest",
                "value": cleaned,
            }

    m_en = re.search(
        r"(?:i\s*am\s+|i'm\s+)?(?:interested\s+in|my\s+interest\s+is)\s+(?:the\s+field\s+of\s+)?([^,\.\n\?!;]{3,50})",
        text,
        re.IGNORECASE,
    )
    if m_en:
        raw_topic = m_en.group(1).strip()
        cleaned = re.split(r"\s+(?:and\s+i|because|but)\b", raw_topic, flags=re.IGNORECASE)[0].strip()
        if len(cleaned) >= 3 and not _contains_academic_facts(cleaned):
            return {
                "category": "ACADEMIC_INTEREST",
                "key": "academic_interest",
                "value": cleaned,
            }
    return None


def _extract_career_goal(text: str) -> dict[str, str] | None:
    m_ar = re.search(
        r"(?:^|[\s،,])(?:و\s*)?(?:بدي|أريد|اريد|أطمح|اطمح|هدفي(?:\s+هو|\s+المهني)?)\s+(?:أن\s+|ان\s+)?(?:أتخصص|اتخصص|أشتغل|اشتغل|أعمل|اعمل|أكون|اكون)\s+(?:كـ?|في\s+(?:مجال\s+)?|بـ?مجال\s+|بـ?|في\s+)?([^،,\.\n\?!;]{3,50})",
        text,
        re.IGNORECASE,
    )
    if m_ar:
        raw_goal = m_ar.group(1).strip()
        cleaned = re.split(r"\s+(?:و\s*بدي|و\s*أريد|و\s*اريد|لأن|عشان|بس|لكن|and\s+i)\b", raw_goal)[0].strip()
        cleaned = re.sub(r"^(?:ب?مجال\s+|بـ?|في\s+|كـ)", "", cleaned).strip()
        if len(cleaned) >= 3 and not _contains_academic_facts(cleaned):
            return {
                "category": "CAREER_GOAL",
                "key": "career_goal",
                "value": cleaned,
            }

    m_en = re.search(
        r"(?:i\s*(?:want|plan|hope)\s+to\s+(?:specialize\s+in|work\s+as)|my\s+career\s+goal\s+is)\s+(?:a\s+|an\s+|the\s+field\s+of\s+)?([^,\.\n\?!;]{3,50})",
        text,
        re.IGNORECASE,
    )
    if m_en:
        raw_goal = m_en.group(1).strip()
        cleaned = re.split(r"\s+(?:and\s+i|because|but)\b", raw_goal, flags=re.IGNORECASE)[0].strip()
        if len(cleaned) >= 3 and not _contains_academic_facts(cleaned):
            return {
                "category": "CAREER_GOAL",
                "key": "career_goal",
                "value": cleaned,
            }
    return None


def _extract_workload_preference(text: str) -> dict[str, str] | None:
    # 1. Study/explanation preference
    if re.search(r"(?:^|[\s،,])(?:و\s*)?(?:بفضل|أفضل|افضل)\s+(?:الشرح\s+العملي|الجانب\s+العملي|التطبيقي)", text):
        val = "الشرح العملي أكثر من النظري" if "نظري" in text else "الشرح العملي والتطبيقي"
        return {
            "category": "WORKLOAD_PREFERENCE",
            "key": "study_preference",
            "value": val,
        }
    if re.search(r"prefer\s+(?:practical|hands-on)\s+(?:explanation|work)", text, re.I):
        return {
            "category": "WORKLOAD_PREFERENCE",
            "key": "study_preference",
            "value": "practical explanations over theory" if "theory" in text.lower() else "hands-on and practical study",
        }

    # 2. General workload load style
    m_load_ar = re.search(
        r"(?:^|[\s،,])(?:و\s*)?(?:بدي|أريد|اريد|أفضل|بفضل)\s+(?:يكون\s+)?(?:الـ?)?(حمل\s+(?:خفيف|أخف|اخف|متوسط|مريح|مكثف|ثقيل))",
        text,
    )
    if m_load_ar:
        raw_val = m_load_ar.group(1).strip()
        val = "حمل خفيف" if any(w in raw_val for w in ("خفيف", "أخف", "اخف", "مريح")) else \
              ("حمل مكثف" if any(w in raw_val for w in ("مكثف", "ثقيل")) else "حمل متوسط")
        return {
            "category": "WORKLOAD_PREFERENCE",
            "key": "workload_preference",
            "value": val,
        }
    m_load_en = re.search(
        r"(?:i\s*want|i\s*prefer)\s+(?:a\s+)?(light|lighter|medium|moderate|heavy|intensive)\s+(?:workload|course\s*load)",
        text,
        re.IGNORECASE,
    )
    if m_load_en:
        pace = m_load_en.group(1).lower()
        val = "light workload" if pace in ("light", "lighter") else ("heavy workload" if pace in ("heavy", "intensive") else "moderate workload")
        return {
            "category": "WORKLOAD_PREFERENCE",
            "key": "workload_preference",
            "value": val,
        }
    return None


def _extract_schedule_constraint(text: str) -> dict[str, str] | None:
    # 1. Day restriction
    m_cant_ar = re.search(
        r"(?:^|[\s،,])(?:و\s*)?(?:ما\s+بقدر|بقدرش|ما\s+بستطيع|ما\s+بناسبني|صعب)\s+(?:أداوم|اداوم|أحضر|احضر|انزل|أنزل)\s+(?:يوم\s+|أيام\s+|ايام\s+)?(الخميس|الأحد|الاحد|الاثنين|الإثنين|الثلاثاء|الأربعاء|الاربعاء|السبت|الجمعة)",
        text,
    )
    if m_cant_ar:
        day = DAYS_MAP_AR.get(m_cant_ar.group(1), m_cant_ar.group(1))
        return {
            "category": "SCHEDULE_CONSTRAINT",
            "key": "schedule_constraint",
            "value": f"عدم الدوام يوم {day}",
        }

    m_cant_en = re.search(
        r"(?:can't|cannot|unable\s+to|no)\s+(?:attend|have\s+classes|classes\s+on)\s+(?:on\s+)?(mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|saturdays?|sundays?)",
        text,
        re.IGNORECASE,
    )
    if m_cant_en:
        day_raw = m_cant_en.group(1).rstrip("s").lower()
        day = DAYS_MAP_EN.get(day_raw, day_raw.capitalize())
        return {
            "category": "SCHEDULE_CONSTRAINT",
            "key": "schedule_constraint",
            "value": f"No attendance on {day}",
        }

    # 2. Timing preference (morning / evening)
    if re.search(r"(?:دوام\s+صباحي|الفترة\s+الصباحية|بفضل\s+الصبح)", text):
        return {
            "category": "SCHEDULE_CONSTRAINT",
            "key": "schedule_constraint",
            "value": "دوام صباحي",
        }
    if re.search(r"(?:دوام\s+مسائي|الفترة\s+المسائية|بفضل\s+المساء)", text):
        return {
            "category": "SCHEDULE_CONSTRAINT",
            "key": "schedule_constraint",
            "value": "دوام مسائي",
        }
    if re.search(r"\bmorning\s+classes\b", text, re.I):
        return {
            "category": "SCHEDULE_CONSTRAINT",
            "key": "schedule_constraint",
            "value": "Morning classes",
        }
    if re.search(r"\bevening\s+classes\b", text, re.I):
        return {
            "category": "SCHEDULE_CONSTRAINT",
            "key": "schedule_constraint",
            "value": "Evening classes",
        }
    return None


def extract_explicit_memories(message: str) -> list[dict[str, str]]:
    """Conservative extraction of durable personal preferences and goals.

    Extracts only supported categories:
      - ACADEMIC_INTEREST
      - WORKLOAD_PREFERENCE
      - CAREER_GOAL
      - SCHEDULE_CONSTRAINT

    Never extracts academic facts (GPA, credits, grades, prerequisites).
    """
    normalized = message.strip()
    if not normalized:
        return []

    # Proactively reject pure or predominant academic fact inquiries or declarations
    if re.search(r"^(?:كم|قديش|شو|هل)?\s*(?:معدلي|معدل|علامتي|ساعاتي|gpa|credits?)\b", normalized, re.I):
        return []

    found: list[dict[str, str]] = []

    interest = _extract_academic_interest(normalized)
    if interest:
        found.append(interest)

    goal = _extract_career_goal(normalized)
    if goal:
        found.append(goal)

    workload = _extract_workload_preference(normalized)
    if workload:
        found.append(workload)

    schedule = _extract_schedule_constraint(normalized)
    if schedule:
        found.append(schedule)

    return found


def extract_explicit_preferences(message: str) -> dict[str, str]:
    """Conservative extraction only; never derive academic facts or sensitive traits."""
    normalized = message.casefold().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    if not re.search(r"\b(i want|i prefer|i changed my mind|i'll take|اريد|أريد|بدي|أفضل)\b", normalized):
        return {}
    found: dict[str, str] = {}
    for regular in re.finditer(r"\b(\d{1,2})\s*(?:credits?|hours?|ساعة|ساعات)\b", normalized):
        prefix = normalized[max(0, regular.start() - 30):regular.start()]
        # A summer-only statement must not silently replace the regular load.
        if re.search(r"(?:summer|صيفي|الصيفي)\s*$", prefix):
            continue
        if 3 <= int(regular.group(1)) <= 30:
            found["regular_load"] = regular.group(1)
    summer = re.search(r"(?:summer|صيفي|الصيفي).{0,30}?(\d{1,2})(?:\s*(?:credits?|hours?|ساعة|ساعات))?", normalized)
    if summer and 3 <= int(summer.group(1)) <= 9:
        found["summer_enabled"] = "true"
        found["summer_load"] = summer.group(1)
    elif re.search(r"(?:no summer|without summer|بدون صيفي)", normalized):
        found["summer_enabled"] = "false"
    # Explicit pace statements only; no inference from grades or student traits.
    pace_patterns = {"FASTEST": r"fastest|أسرع|اسرع", "BALANCED": r"balanced|متوازن",
                     "LOWER_LOAD": r"lower load|lighter load|حمل أخف|حمل اخف"}
    matches = [(match.start(), pace) for pace, pattern in pace_patterns.items()
               for match in re.finditer(pattern, normalized)]
    if matches:
        found["graduation_pace"] = max(matches)[1]
    return found


def bounded_conversation_context(
    preferences: Mapping[str, str],
    recent: list[str] | list[dict[str, Any]],
    summary: str | None = None,
    memories: list[dict[str, Any]] | None = None,
) -> str:
    """No transcript dump, authoritative facts, hidden reasoning or raw logs."""
    safe = {key: value for key, value in preferences.items()
            if key in {"regular_load", "summer_enabled", "summer_load", "graduation_pace",
                       "academic_interest", "career_goal", "schedule_constraint",
                       "workload_preference", "study_preference"}}

    if memories:
        for m in memories:
            if not isinstance(m, dict):
                continue
            cat = m.get("memory_category")
            k = m.get("memory_key")
            v = m.get("memory_value")
            if cat in SUPPORTED_MEMORY_CATEGORIES and k and v:
                if not _contains_academic_facts(str(v)):
                    safe[str(k)] = str(v)

    preference_summary = "; ".join(f"{key}={safe[key]}" for key in sorted(safe))

    snippets: list[str] = []
    for item in recent[-20:]:
        if isinstance(item, dict):
            role = item.get("role", "USER")
            content = str(item.get("content", "")).replace("\n", " ")[:180]
            snippets.append(f"{role}: {content}")
        else:
            snippets.append(str(item).replace("\n", " ")[:180])

    safe_summary = (summary or "").replace("\n", " ")[:800]
    return (f"USER_STATED planning preferences: {preference_summary or 'none'}\n"
            f"CHAT_DERIVED bounded summary (not academic facts): {safe_summary or 'none'}\n"
            f"CHAT_DERIVED recent turns (not academic facts):\n" + "\n".join(snippets))[:1600]
