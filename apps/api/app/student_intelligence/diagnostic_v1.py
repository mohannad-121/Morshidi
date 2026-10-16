"""Server-authoritative, deterministic quick diagnostic policy.

This is a modeled cold-start baseline, not a certified psychometric examination.
Answer keys and item weights must never be serialized by API schemas.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

ASSESSMENT_VERSION = "QUICK_DIAGNOSTIC_V1"
SCORING_POLICY_VERSION = "DIAGNOSTIC_SCORING_V1"
SELECTION_POLICY_VERSION = "DIAGNOSTIC_SELECTION_V1"
MIN_QUESTIONS = 10
TARGET_QUESTIONS = 12
MAX_QUESTIONS = 16
DIAGNOSTIC_REASON_CODES = frozenset({
    "MODELED_DIAGNOSTIC_BASELINE",
    "RESPONSES_1", "RESPONSES_2", "RESPONSES_3", "RESPONSES_4", "RESPONSES_5",
    "LIMITED_ITEM_COUNT",
    "MIXED_RESPONSE_PATTERN",
})


class DiagnosticDomain(str, Enum):
    PROGRAMMING_REASONING = "PROGRAMMING_REASONING"
    LOGICAL_PROBLEM_SOLVING = "LOGICAL_PROBLEM_SOLVING"
    QUANTITATIVE_MATH = "QUANTITATIVE_MATH"
    STATISTICS_DATA_REASONING = "STATISTICS_DATA_REASONING"
    THEORY_COMPREHENSION_MEMORY = "THEORY_COMPREHENSION_MEMORY"


@dataclass(frozen=True)
class Option:
    option_id: str
    text_ar: str
    text_en: str


@dataclass(frozen=True)
class DiagnosticQuestion:
    question_id: str
    domain: DiagnosticDomain
    difficulty: str
    prompt_ar: str
    prompt_en: str
    options: tuple[Option, ...]
    correct_option: str
    assessment_version: str = ASSESSMENT_VERSION


def _q(qid: str, domain: DiagnosticDomain, difficulty: str, ar: str, en: str,
       choices: tuple[tuple[str, str], ...], answer: str) -> DiagnosticQuestion:
    return DiagnosticQuestion(qid, domain, difficulty, ar, en,
                              tuple(Option(chr(65 + i), a, e) for i, (a, e) in enumerate(choices)), answer)


P, G, Q, S, T = tuple(DiagnosticDomain)
QUESTION_BANK: tuple[DiagnosticQuestion, ...] = (
    _q("P01", P, "EASY", "إذا كانت x = 2 ثم x = x + 3، فما قيمة x؟", "If x = 2 then x = x + 3, what is x?", (("3", "3"), ("5", "5"), ("6", "6"), ("لا تتغير", "unchanged")), "B"),
    _q("P02", P, "EASY", "كم مرة تُنفذ حلقة من 1 إلى 4 شاملة؟", "How many times does a loop from 1 through 4 inclusive run?", (("3", "3"), ("4", "4"), ("5", "5"), ("مرة", "once")), "B"),
    _q("P03", P, "MEDIUM", "إذا كان الشرط (العمر >= 18) كاذباً، فأي قيمة ممكنة؟", "If (age >= 18) is false, which value is possible?", (("18", "18"), ("21", "21"), ("17", "17"), ("30", "30")), "C"),
    _q("P04", P, "MEDIUM", "قائمة [2،4،6]. ما ناتج جمع عناصرها؟", "For [2,4,6], what is the sum?", (("8", "8"), ("10", "10"), ("12", "12"), ("14", "14")), "C"),
    _q("P05", P, "HARD", "تبدأ n=1 وتتضاعف ثلاث مرات. ما الناتج؟", "n starts at 1 and is doubled three times. Result?", (("3", "3"), ("6", "6"), ("8", "8"), ("9", "9")), "C"),
    _q("L01", G, "EASY", "كل الروبوتات آلات. رامي روبوت. ماذا يلزم؟", "All robots are machines. Rami is a robot. What follows?", (("رامي آلة", "Rami is a machine"), ("كل الآلات روبوتات", "All machines are robots"), ("لا شيء", "Nothing"), ("رامي إنسان", "Rami is human")), "A"),
    _q("L02", G, "EASY", "ما العدد التالي: 2، 4، 6، ؟", "Next number: 2, 4, 6, ?", (("7", "7"), ("8", "8"), ("9", "9"), ("10", "10")), "B"),
    _q("L03", G, "MEDIUM", "إذا كان المطر يعني أن الطريق مبتل، والطريق غير مبتل، فماذا نستنتج؟", "If rain implies a wet road, and the road is not wet, what follows?", (("أمطرت", "It rained"), ("لم تمطر", "It did not rain"), ("الطريق مغلق", "Road closed"), ("لا علاقة", "No relation")), "B"),
    _q("L04", G, "MEDIUM", "A قبل B وB قبل C. أي ترتيب صحيح؟", "A before B and B before C. Which order is valid?", (("CBA", "CBA"), ("BAC", "BAC"), ("ABC", "ABC"), ("ACB", "ACB")), "C"),
    _q("L05", G, "HARD", "عدد يقبل القسمة على 2 و3 معاً. أي خيار؟", "Which number is divisible by both 2 and 3?", (("8", "8"), ("9", "9"), ("12", "12"), ("15", "15")), "C"),
    _q("M01", Q, "EASY", "ما 25% من 80؟", "What is 25% of 80?", (("15", "15"), ("20", "20"), ("25", "25"), ("40", "40")), "B"),
    _q("M02", Q, "EASY", "إذا كان 3x = 12، فما x؟", "If 3x = 12, what is x?", (("3", "3"), ("4", "4"), ("6", "6"), ("9", "9")), "B"),
    _q("M03", Q, "MEDIUM", "زاد سعر 50 بنسبة 10%. السعر الجديد؟", "A price of 50 increases by 10%. New price?", (("51", "51"), ("55", "55"), ("60", "60"), ("65", "65")), "B"),
    _q("M04", Q, "MEDIUM", "حل: 2x + 4 = 14", "Solve: 2x + 4 = 14", (("4", "4"), ("5", "5"), ("7", "7"), ("9", "9")), "B"),
    _q("M05", Q, "HARD", "مستطيل مساحته 24 وطوله 6. عرضه؟", "Rectangle area 24, length 6. Width?", (("3", "3"), ("4", "4"), ("6", "6"), ("18", "18")), "B"),
    _q("S01", S, "EASY", "ما متوسط 2، 4، 6؟", "Mean of 2, 4, 6?", (("3", "3"), ("4", "4"), ("5", "5"), ("6", "6")), "B"),
    _q("S02", S, "EASY", "احتمال صورة عند رمي قطعة نقد عادلة؟", "Probability of heads on a fair coin?", (("0", "0"), ("1/4", "1/4"), ("1/2", "1/2"), ("1", "1")), "C"),
    _q("S03", S, "MEDIUM", "القيم 1،1،2،8. أي مقياس أقل تأثراً بالقيمة 8؟", "For 1,1,2,8, which measure is less affected by 8?", (("المتوسط", "mean"), ("الوسيط", "median"), ("المجموع", "sum"), ("المدى", "range")), "B"),
    _q("S04", S, "MEDIUM", "من 20 طالباً نجح 15. نسبة النجاح؟", "15 of 20 students passed. Pass rate?", (("60%", "60%"), ("70%", "70%"), ("75%", "75%"), ("80%", "80%")), "C"),
    _q("S05", S, "HARD", "كيس فيه 3 حمراء و1 زرقاء. احتمال الزرقاء؟", "Bag: 3 red and 1 blue. Probability of blue?", (("1/4", "1/4"), ("1/3", "1/3"), ("1/2", "1/2"), ("3/4", "3/4")), "A"),
    _q("T01", T, "EASY", "النص: التكرار المتباعد يحسن التذكر. ما الفكرة الرئيسة؟", "Text: Spaced repetition improves recall. Main idea?", (("التكرار المتباعد مفيد", "Spaced repetition helps"), ("الدراسة غير مفيدة", "Study is useless"), ("الذاكرة ثابتة", "Memory is fixed"), ("الاختبار ممنوع", "Testing is forbidden")), "A"),
    _q("T02", T, "EASY", "أي ترتيب يساعد الفهم: اقرأ، لخّص، راجع؟", "Which sequence supports comprehension: read, summarize, review?", (("راجع ثم اقرأ", "review then read"), ("اقرأ ثم لخّص ثم راجع", "read, summarize, review"), ("لخّص دون قراءة", "summarize without reading"), ("لا ترتيب", "no order")), "B"),
    _q("T03", T, "MEDIUM", "مفهوم A سبب لـB. ما العلاقة؟", "Concept A causes B. What is the relation?", (("B يسبق A", "B precedes A"), ("A يؤدي إلى B", "A leads to B"), ("لا علاقة", "unrelated"), ("متطابقان", "identical")), "B"),
    _q("T04", T, "MEDIUM", "قرأ طالب فقرة ثم كتب فكرتها بلغته. ما المهارة؟", "A student restates a paragraph in their own words. Skill?", (("الحفظ فقط", "rote memory only"), ("الفهم والتلخيص", "comprehension and summarization"), ("الحساب", "calculation"), ("التخمين", "guessing")), "B"),
    _q("T05", T, "HARD", "دليل جديد يناقض ملخصاً سابقاً. الإجراء الأفضل؟", "New evidence contradicts an earlier summary. Best action?", (("تجاهله", "ignore it"), ("تحديث الملخص مع ذكر التعارض", "update and note conflict"), ("حذف الدليل", "delete evidence"), ("تثبيت الرأي", "keep the opinion")), "B"),
)

QUESTIONS_BY_ID = {question.question_id: question for question in QUESTION_BANK}
DIFFICULTY_WEIGHT = {"EASY": .85, "MEDIUM": 1.0, "HARD": 1.15}


@dataclass(frozen=True)
class AnswerEvidence:
    question_id: str
    selected_option: str
    is_correct: bool


@dataclass(frozen=True)
class DiagnosticDomainResult:
    domain: DiagnosticDomain
    score: int
    confidence: str
    response_count: int
    reason_codes: tuple[str, ...]


def score_domain(domain: DiagnosticDomain, responses: Iterable[AnswerEvidence]) -> DiagnosticDomainResult:
    rows = [r for r in responses if QUESTIONS_BY_ID[r.question_id].domain is domain]
    possible = sum(DIFFICULTY_WEIGHT[QUESTIONS_BY_ID[r.question_id].difficulty] for r in rows)
    earned = sum(DIFFICULTY_WEIGHT[QUESTIONS_BY_ID[r.question_id].difficulty] for r in rows if r.is_correct)
    score = round(100 * earned / possible) if possible else 50
    correct = sum(r.is_correct for r in rows)
    mixed = 0 < correct < len(rows)
    confidence = "LOW" if len(rows) <= 2 else "MEDIUM" if len(rows) == 3 or mixed else "HIGH"
    reasons = ["MODELED_DIAGNOSTIC_BASELINE", f"RESPONSES_{len(rows)}"]
    if len(rows) <= 2:
        reasons.append("LIMITED_ITEM_COUNT")
    if mixed:
        reasons.append("MIXED_RESPONSE_PATTERN")
    return DiagnosticDomainResult(domain, score, confidence, len(rows), tuple(reasons))


def select_next_question(responses: tuple[AnswerEvidence, ...]) -> DiagnosticQuestion | None:
    """Reproducible selection: balanced base, then lowest-evidence/ambiguous domains."""
    answered = {row.question_id for row in responses}
    if len(answered) >= MAX_QUESTIONS:
        return None
    counts = {domain: sum(QUESTIONS_BY_ID[r.question_id].domain is domain for r in responses)
              for domain in DiagnosticDomain}
    if min(counts.values()) < 2:
        domain = min(DiagnosticDomain, key=lambda item: (counts[item], list(DiagnosticDomain).index(item)))
    else:
        results = {domain: score_domain(domain, responses) for domain in DiagnosticDomain}
        ambiguous = [domain for domain, result in results.items()
                     if result.response_count < 4 and 35 <= result.score <= 65]
        if len(responses) >= TARGET_QUESTIONS and not ambiguous:
            return None
        candidates = ambiguous or list(DiagnosticDomain)
        domain = min(candidates, key=lambda item: (counts[item], abs(results[item].score - 50),
                                                   list(DiagnosticDomain).index(item)))
    return next((question for question in QUESTION_BANK
                 if question.domain is domain and question.question_id not in answered), None)


def public_question(question: DiagnosticQuestion) -> dict[str, object]:
    return {
        "question_id": question.question_id,
        "assessment_version": question.assessment_version,
        "domain": question.domain.value,
        "prompt_ar": question.prompt_ar,
        "prompt_en": question.prompt_en,
        "options": [{"option_id": o.option_id, "text_ar": o.text_ar, "text_en": o.text_en}
                    for o in question.options],
    }
