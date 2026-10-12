"""Bounded Student Intelligence projections and deterministic advisor prose."""

from __future__ import annotations

from dataclasses import dataclass

from app.recommendations.models import RecommendationResult
from app.student_intelligence.adaptive import AdaptiveCourseResult
from app.student_intelligence.profile_v2 import StudentIntelligenceProfileV2


_SKILL_AR = {
    "PROGRAMMING": "البرمجة", "PYTHON": "بايثون",
    "OBJECT_ORIENTED_PROGRAMMING": "البرمجة كائنية التوجه",
    "DATA_STRUCTURES": "هياكل البيانات", "ALGORITHMS": "الخوارزميات",
    "LOGICAL_REASONING": "الاستدلال المنطقي", "DISCRETE_MATH": "الرياضيات المتقطعة",
    "QUANTITATIVE_MATH": "الرياضيات الكمية", "LINEAR_ALGEBRA": "الجبر الخطي",
    "STATISTICS": "الإحصاء", "DATA_ANALYSIS": "تحليل البيانات",
    "DATABASES": "قواعد البيانات", "SOFTWARE_ENGINEERING": "هندسة البرمجيات",
    "WEB_DEVELOPMENT": "تطوير الويب", "AI_FOUNDATIONS": "أساسيات الذكاء الاصطناعي",
    "MACHINE_LEARNING": "تعلم الآلة", "DEEP_LEARNING": "التعلم العميق",
    "THEORY_COMPREHENSION": "الفهم النظري", "MEMORIZATION": "الحفظ والاستيعاب",
    "PRACTICAL_LAB": "العمل المخبري", "PROJECT_WORK": "العمل على المشاريع",
    "RESEARCH": "البحث", "COMMUNICATION": "التواصل", "DIGITAL_LITERACY": "المهارات الرقمية",
    "SYSTEMS": "الأنظمة", "NETWORKS": "الشبكات", "COMPUTER_VISION": "الرؤية الحاسوبية",
    "NATURAL_LANGUAGE_PROCESSING": "معالجة اللغة الطبيعية", "ROBOTICS": "الروبوتات",
    "ETHICS": "الأخلاقيات",
}


@dataclass(frozen=True)
class BoundedSkillSummary:
    skill_id: str
    label_ar: str
    score: int
    confidence: str
    university_evidence_count: int
    diagnostic_evidence_count: int
    evidence_limitation: str
    classification: str


@dataclass(frozen=True)
class BoundedStudentIntelligenceContext:
    skills: tuple[BoundedSkillSummary, ...]
    evidence_quality: str
    cold_start_status: str
    diagnostic_recommended: bool
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class BoundedCourseFit:
    course_code: str
    rank: int
    progression_rank: int
    fit_score: int
    confidence: str
    personalized_difficulty: str
    contributing_skills: tuple[str, ...]
    risk_factors: tuple[str, ...]


def _label(skill_id: str) -> str:
    return _SKILL_AR.get(skill_id, skill_id.replace("_", " ").title())


def project_student_intelligence(
    profile: StudentIntelligenceProfileV2, *, limit: int = 8,
) -> BoundedStudentIntelligenceContext:
    """Project only explanation-safe V2 fields; raw evidence never crosses."""
    strength_ids = set(profile.strengths)
    development_ids = set(profile.development_areas)
    ranked = sorted(
        (skill for skill in profile.skills if skill.score is not None),
        key=lambda skill: (-int(skill.score or 0), -skill.university_evidence_count, skill.skill_id),
    )[:limit]
    skills = tuple(BoundedSkillSummary(
        skill.skill_id,
        _label(skill.skill_id),
        int(skill.score),
        skill.confidence,
        skill.university_evidence_count,
        skill.diagnostic_evidence_count,
        ("أدلة جامعية محدودة" if skill.university_evidence_count < 3
         else "مدعوم بعدة أدلة جامعية مستقلة"),
        ("STRENGTH" if skill.skill_id in strength_ids else
         "DEVELOPMENT" if skill.skill_id in development_ids else "OBSERVED"),
    ) for skill in ranked)
    return BoundedStudentIntelligenceContext(
        skills, profile.evidence_quality, profile.cold_start_status,
        profile.diagnostic_recommended,
        tuple(profile.limitations),
    )


def render_student_intelligence_ar(
    context: BoundedStudentIntelligenceContext, *, asks_for_development: bool = False,
) -> str:
    relevant = tuple(skill for skill in context.skills
                     if skill.classification == ("DEVELOPMENT" if asks_for_development else "STRENGTH"))
    if not relevant:
        if context.cold_start_status == "COLD_START_NO_PERFORMANCE_EVIDENCE":
            suffix = " يمكنك إجراء التشخيص السريع لبناء خط أساس مبدئي." if context.diagnostic_recommended else ""
            return "لا تتوفر لدي أدلة كافية لتحديد مهاراتك بأمان حتى الآن." + suffix
        return "الأدلة الحالية لا تكفي لتحديد " + ("نقاط تطوير واضحة" if asks_for_development else "نقاط قوة مؤكدة") + "."
    heading = "مجالات التطوير الحالية" if asks_for_development else "من أبرز نقاط قوتك"
    lines = [f"بناءً على أدائك الجامعي، {heading}:"]
    for skill in relevant[:6]:
        confidence = {"HIGH": "مرتفعة", "MEDIUM": "متوسطة", "LOW": "محدودة"}.get(
            skill.confidence, skill.confidence)
        evidence = (f"{skill.university_evidence_count} أدلة جامعية"
                    if skill.university_evidence_count else
                    f"{skill.diagnostic_evidence_count} أدلة تشخيصية")
        lines.append(f"- {skill.label_ar} — تقدير {skill.score}/100، ثقة {confidence}، ومدعوم بـ {evidence}.")
    lines.extend((
        "",
        "بنيت هذا التحليل على النتائج الجامعية الرسمية في المساقات المرتبطة بكل مهارة، وليس على المعدل التراكمي وحده. التقييم نفسه نموذج تفسيري من مرشدي وليس حكماً رسمياً من الجامعة.",
        "تزداد الثقة عندما تتوفر أدلة جامعية مستقلة أكثر؛ أما التشخيص السريع — إن وُجد — فهو دليل ثانوي ولا يغيّر الأهلية أو المتطلبات.",
    ))
    if any(skill.university_evidence_count < 3 for skill in relevant[:6]):
        lines.append("بعض التقديرات مبنية على أدلة محدودة، لذلك ينبغي قراءتها بدرجة حذر أعلى.")
    return "\n".join(lines)


def render_student_intelligence_en(
    context: BoundedStudentIntelligenceContext, *, asks_for_development: bool = False,
) -> str:
    target = "DEVELOPMENT" if asks_for_development else "STRENGTH"
    relevant = tuple(skill for skill in context.skills if skill.classification == target)
    if not relevant:
        suffix = " Complete the quick diagnostic to establish an initial baseline." if context.diagnostic_recommended else ""
        return "There is not enough evidence to identify this safely yet." + suffix
    heading = "Current development areas" if asks_for_development else "Your strongest modeled skills"
    lines = [f"Based on your university performance, {heading} are:"]
    for skill in relevant[:6]:
        evidence = (f"{skill.university_evidence_count} university observations"
                    if skill.university_evidence_count else
                    f"{skill.diagnostic_evidence_count} diagnostic observations")
        lines.append(f"- {skill.skill_id.replace('_', ' ').title()} — {skill.score}/100, "
                     f"{skill.confidence.lower()} confidence, supported by {evidence}.")
    lines.extend(("", "This is based on official results in courses mapped to each skill, not GPA alone. "
                  "The score is Morshidi's modeled interpretation, not an official university evaluation.",
                  "Diagnostic evidence is secondary and never changes eligibility or prerequisites."))
    return "\n".join(lines)


def project_course_fit(
    adaptive: AdaptiveCourseResult, deterministic: RecommendationResult,
) -> tuple[BoundedCourseFit, ...]:
    legal_by_code = {
        item.course_code: item for item in deterministic.ranked_recommendations
    }
    legal = set(legal_by_code)
    personalized = {item.course_code for item in adaptive.recommendations}
    if legal != personalized or any(not item.eligible for item in adaptive.recommendations):
        raise ValueError("Student Intelligence changed the deterministic eligible set")
    projected = tuple(BoundedCourseFit(
        item.course_code, 0, legal_by_code[item.course_code].rank,
        item.fit_score, item.confidence, item.personalized_difficulty.level,
        tuple(item.personalized_difficulty.contributing_skills), item.risk_factors,
    ) for item in adaptive.recommendations)
    ordered = sorted(
        projected,
        key=lambda item: (-item.fit_score, item.progression_rank, item.course_code),
    )
    return tuple(BoundedCourseFit(
        item.course_code, rank, item.progression_rank, item.fit_score,
        item.confidence, item.personalized_difficulty,
        item.contributing_skills, item.risk_factors,
    ) for rank, item in enumerate(ordered, 1))


def render_personalized_recommendations_ar(
    deterministic: RecommendationResult, fits: tuple[BoundedCourseFit, ...],
    *, include_full_eligible_list: bool = False, shortlist_limit: int = 5,
) -> str:
    by_code = {item.course_code: item for item in deterministic.ranked_recommendations}
    eligible_count = len(deterministic.ranked_recommendations)
    lines = [f"عندك {eligible_count} مادة مؤهلة أكاديميًا."]
    if include_full_eligible_list:
        lines.extend(("", "القائمة الكاملة للمواد المؤهلة أكاديميًا:"))
        lines.extend(
            f"- {item.course_name_ar or item.course_code} ({item.course_code})"
            for item in deterministic.ranked_recommendations
        )
    lines.extend(("", "من ناحية ملاءمة قدراتك الحالية، أنسب المواد المؤهلة لك هي:"))
    shortlist = fits[:shortlist_limit]
    for fit in shortlist:
        course = by_code[fit.course_code]
        skills = "، ".join(_label(skill) for skill in fit.contributing_skills[:3]) or "أدلة المهارات المتاحة"
        confidence = {"HIGH": "مرتفعة", "MEDIUM": "متوسطة", "LOW": "محدودة"}.get(
            fit.confidence, fit.confidence)
        effort = {"VERY_EASY": "جهد أقل نسبيًا", "EASY": "جهد أقل نسبيًا",
                  "MODERATE": "جهد متوسط", "HARD": "جهد أكبر", "VERY_HARD": "جهد أكبر"}.get(
                      fit.personalized_difficulty, "جهد غير محسوم")
        lines.append(
            f"{fit.rank}. {course.course_name_ar or fit.course_code} ({fit.course_code}) — "
            f"ملاءمة شخصية {fit.fit_score}/100، وثقة {confidence}. "
            f"المهارات المساهمة: {skills}. عبء متوقع: {effort}. "
            f"سبب الملاءمة: أداؤك الجامعي الموثق في هذه المهارات يتقاطع مع متطلبات المادة."
        )
    progression = deterministic.ranked_recommendations[:3]
    if tuple(item.course_code for item in progression) != tuple(
            item.course_code for item in shortlist[:3]):
        lines.extend(("", "من ناحية أولوية التقدم في الخطة، تتقدم هذه المواد (وهذا ترتيب مختلف عن الملاءمة الشخصية):"))
        lines.extend(
            f"- {item.course_name_ar or item.course_code} ({item.course_code})"
            for item in progression
        )
    if not include_full_eligible_list:
        lines.extend(("", "إذا بدك، بعرض لك القائمة الكاملة للمواد المؤهلة."))
    lines.extend(("", "الملاءمة الشخصية تفسير مساعد فقط؛ لا تضيف مادة غير مؤهلة، ولا تلغي أهلية مادة، ولا تتجاوز المتطلبات السابقة أو قيود الخطة، ولا تضمن أن المادة ستكون سهلة."))
    return "\n".join(lines)


def render_personalized_recommendations_en(
    deterministic: RecommendationResult, fits: tuple[BoundedCourseFit, ...],
    *, include_full_eligible_list: bool = False, shortlist_limit: int = 5,
) -> str:
    by_code = {item.course_code: item for item in deterministic.ranked_recommendations}
    lines = [f"You have {len(deterministic.ranked_recommendations)} academically eligible courses."]
    if include_full_eligible_list:
        lines.extend(("", "Full academically eligible course list:"))
        lines.extend(
            f"- {item.course_name_en or item.course_name_ar or item.course_code} ({item.course_code})"
            for item in deterministic.ranked_recommendations
        )
    lines.extend(("", "For fit with your current abilities, your strongest eligible options are:"))
    shortlist = fits[:shortlist_limit]
    for fit in shortlist:
        course = by_code[fit.course_code]
        skills = ", ".join(skill.replace("_", " ").title() for skill in fit.contributing_skills[:3]) or "limited skill evidence"
        effort = {"VERY_EASY": "relatively lower", "EASY": "relatively lower",
                  "MODERATE": "moderate", "HARD": "higher", "VERY_HARD": "higher"}.get(
                      fit.personalized_difficulty, "uncertain")
        lines.append(f"{fit.rank}. {course.course_name_en or course.course_name_ar or fit.course_code} "
                     f"({fit.course_code}) — personal fit {fit.fit_score}/100, "
                     f"{fit.confidence.lower()} confidence. Contributing skills: {skills}. "
                     f"Expected workload: {effort}. Why it fits: your verified academic "
                     "performance in these skills overlaps with the course's demands.")
    progression = deterministic.ranked_recommendations[:3]
    if tuple(item.course_code for item in progression) != tuple(
            item.course_code for item in shortlist[:3]):
        lines.extend(("", "For degree-plan progression priority, these courses come first (a separate ranking from personal fit):"))
        lines.extend(
            f"- {item.course_name_en or item.course_name_ar or item.course_code} ({item.course_code})"
            for item in progression
        )
    if not include_full_eligible_list:
        lines.extend(("", "I can show the full eligible-course list if you want it."))
    lines.extend(("", "Personal fit is explanatory only: it never adds or removes eligibility, overrides prerequisites or plan constraints, or guarantees that a course will be easy."))
    return "\n".join(lines)
