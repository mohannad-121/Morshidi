"""Server-authoritative deterministic academic reasoning diagnostic.

This is an initial modeled evidence source, not an IQ, personality, medical,
psychological, or official university assessment. Answer keys, distractor
interpretations, weights, and scoring internals never cross the public API.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import mean
from typing import Iterable, Mapping

ASSESSMENT_VERSION = "QUICK_DIAGNOSTIC_V2"
SCORING_POLICY_VERSION = "DIAGNOSTIC_SCORING_V2"
SELECTION_POLICY_VERSION = "DIAGNOSTIC_FIXED_SEQUENCE_V2"
TARGET_QUESTIONS = 30
MIN_RESPONSE_TIME_MS = 1_000
MAX_RESPONSE_TIME_MS = 1_800_000


class DiagnosticDomain(str, Enum):
    PROGRAMMING_REASONING = "PROGRAMMING_REASONING"
    LOGICAL_PROBLEM_SOLVING = "LOGICAL_PROBLEM_SOLVING"
    QUANTITATIVE_MATH = "QUANTITATIVE_MATH"
    STATISTICS_DATA_REASONING = "STATISTICS_DATA_REASONING"
    THEORY_CONCEPTUAL_UNDERSTANDING = "THEORY_CONCEPTUAL_UNDERSTANDING"


@dataclass(frozen=True)
class Option:
    option_id: str
    text_ar: str
    text_en: str


@dataclass(frozen=True)
class DiagnosticQuestion:
    question_id: str
    domain: DiagnosticDomain
    skill: str
    subskill: str
    difficulty: str
    prompt_ar: str
    prompt_en: str
    options: tuple[Option, ...]
    correct_option: str
    distractor_reasoning: Mapping[str, str]
    cognitive_operation: str
    evidence_weight: float
    expected_solving_behavior: str
    estimated_time_seconds: int
    assessment_version: str = ASSESSMENT_VERSION


def _q(qid: str, domain: DiagnosticDomain, skill: str, subskill: str,
       difficulty: str, ar: str, en: str, choices: tuple[tuple[str, str], ...],
       answer: str, distractors: tuple[str, str, str], operation: str,
       weight: float, behavior: str, seconds: int) -> DiagnosticQuestion:
    option_ids = tuple(chr(65 + index) for index in range(4))
    wrong_ids = tuple(option_id for option_id in option_ids if option_id != answer)
    return DiagnosticQuestion(
        qid, domain, skill, subskill, difficulty, ar, en,
        tuple(Option(option_ids[index], *choice) for index, choice in enumerate(choices)),
        answer, dict(zip(wrong_ids, distractors, strict=True)), operation, weight, behavior, seconds,
    )


P = DiagnosticDomain.PROGRAMMING_REASONING
L = DiagnosticDomain.LOGICAL_PROBLEM_SOLVING
M = DiagnosticDomain.QUANTITATIVE_MATH
S = DiagnosticDomain.STATISTICS_DATA_REASONING
T = DiagnosticDomain.THEORY_CONCEPTUAL_UNDERSTANDING

QUESTION_BANK: tuple[DiagnosticQuestion, ...] = (
    _q("P01", P, "PROGRAM_FLOW", "VARIABLE_TRACING", "EASY",
       "ابدأ بـ x = 3، ثم نفّذ x = x + 4 وبعدها x = x × 2. ما قيمة x؟",
       "Start with x = 3, then x = x + 4, then x = x × 2. What is x?",
       (("10", "10"), ("11", "11"), ("14", "14"), ("17", "17")), "C",
       ("applies multiplication before the assignment sequence", "adds only one operation", "adds all operands without tracing"),
       "SEQUENTIAL_TRACE", 1.0, "Updates the variable in stated order.", 25),
    _q("P02", P, "PROGRAM_FLOW", "CONDITION_LOGIC", "EASY",
       "إذا كانت الدرجة 72، فما الناتج؟ إذا الدرجة ≥ 60 اطبع «ناجح»، وإلا اطبع «يحتاج إعادة».",
       "If the grade is 72, what prints? If grade ≥ 60 print 'pass'; otherwise print 'retake'.",
       (("ناجح", "pass"), ("يحتاج إعادة", "retake"), ("72 فقط", "72 only"), ("لا شيء", "nothing")), "A",
       ("reverses the comparison branch", "confuses input with output", "assumes no branch runs"),
       "APPLY_CONDITION", .95, "Evaluates the condition and selects one branch.", 20),
    _q("P03", P, "PROGRAM_FLOW", "LOOP_ACCUMULATION", "MEDIUM",
       "المتغير total يبدأ من 0. تكرّر الحلقة للأعداد 1، 2، 3 وتضيف كل عدد إلى total. ما الناتج؟",
       "total starts at 0. A loop visits 1, 2, 3 and adds each number to total. Result?",
       (("3", "3"), ("5", "5"), ("6", "6"), ("7", "7")), "C",
       ("counts iterations instead of accumulating", "omits one loop value", "introduces an off-by-one value"),
       "LOOP_TRACE", 1.05, "Tracks the accumulator across every iteration.", 35),
    _q("P04", P, "PROGRAM_DESIGN", "DECOMPOSITION", "MEDIUM",
       "مطلوب برنامج يحسب متوسط العلامات ثم يعرض فقط العلامات الأعلى من المتوسط. ما أفضل تقسيم؟",
       "A program must calculate the average, then show only grades above it. Best decomposition?",
       (("اعرض العلامات ثم احسب المتوسط", "show grades then calculate average"),
        ("احسب المتوسط، ثم افحص كل علامة، ثم اعرض المطابق", "calculate average, inspect each grade, display matches"),
        ("رتّب الأسماء فقط", "sort names only"), ("اختر علامة عشوائية", "choose a random grade")), "B",
       ("uses a result before computing it", "solves an unrelated surface task", "replaces the rule with randomness"),
       "DECOMPOSE_PROCEDURE", 1.0, "Orders dependent subtasks before filtering.", 40),
    _q("P05", P, "PROGRAM_QUALITY", "DEBUGGING_REASONING", "HARD",
       "حلقة يفترض أن تعالج 5 عناصر، لكنها تعالج 4 فقط لأنها تستخدم i < 4 مع i يبدأ من 0. ما التصحيح الأدق؟",
       "A loop should process 5 items but processes 4 because it uses i < 4 from i = 0. Best fix?",
       (("غيّرها إلى i ≤ 4", "change to i ≤ 4"), ("ابدأ من i = 1 واترك الشرط", "start at i = 1, keep condition"),
        ("احذف زيادة i", "remove the increment"), ("غيّرها إلى i < 3", "change to i < 3")), "A",
       ("still processes fewer indices", "creates a non-terminating loop", "reduces the range further"),
       "DIAGNOSE_OFF_BY_ONE", 1.1, "Maps five zero-based indices to a correct boundary.", 50),
    _q("P06", P, "ALGORITHMIC_REASONING", "SEARCH_STRATEGY", "HARD",
       "قائمة مرتبة من 1 إلى 64. في كل خطوة تفحص المنتصف وتتجاهل النصف غير المناسب. ما أكبر عدد تقريبي من الفحوص؟",
       "A sorted list contains 1 to 64. Each step checks the middle and discards the wrong half. Approximate maximum checks?",
       (("6", "6"), ("16", "16"), ("32", "32"), ("64", "64")), "A",
       ("assumes quartering rather than halving", "stops after only one halving", "models a linear scan"),
       "RECOGNIZE_HALVING", 1.15, "Counts repeated halvings until one candidate remains.", 55),

    _q("L01", L, "DEDUCTIVE_REASONING", "CATEGORY_INFERENCE", "EASY",
       "كل مشاريع التخرّج تحتاج مشرفاً. مشروع سارة مشروع تخرّج. ماذا يلزم؟",
       "All graduation projects need a supervisor. Sara's project is a graduation project. What follows?",
       (("مشروع سارة يحتاج مشرفاً", "Sara's project needs a supervisor"), ("كل مشروع له مشرفان", "every project has two supervisors"),
        ("سارة هي المشرفة", "Sara is the supervisor"), ("لا يمكن الاستنتاج", "nothing follows")), "A",
       ("adds an unsupported quantity", "confuses project owner and supervisor", "ignores a direct syllogism"),
       "DEDUCTIVE_APPLICATION", 1.0, "Applies the general rule to the stated member.", 25),
    _q("L02", L, "PATTERN_REASONING", "SEQUENCE_PATTERN", "EASY",
       "ما العدد التالي: 3، 6، 12، 24، ؟", "What comes next: 3, 6, 12, 24, ?",
       (("27", "27"), ("30", "30"), ("36", "36"), ("48", "48")), "D",
       ("continues by adding three", "uses an inconsistent increment", "adds the previous difference once"),
       "INFER_PATTERN", .95, "Identifies repeated doubling.", 20),
    _q("L03", L, "CONSTRAINT_REASONING", "SEQUENCING", "MEDIUM",
       "يجب إنهاء A قبل B، وC بعد B. أي ترتيب صالح؟", "A must finish before B, and C after B. Which order is valid?",
       (("B ثم A ثم C", "B then A then C"), ("A ثم C ثم B", "A then C then B"),
        ("C ثم B ثم A", "C then B then A"), ("A ثم B ثم C", "A then B then C")), "D",
       ("violates A before B", "violates C after B", "reverses both constraints"),
       "SATISFY_CONSTRAINTS", 1.05, "Checks every ordering constraint together.", 35),
    _q("L04", L, "ELIMINATION", "SET_CONSTRAINTS", "MEDIUM",
       "ثلاث مواد: X وY وZ. لا يمكن أخذ X مع Y، ويجب اختيار مادتين. أي خيار ممكن؟",
       "Three courses: X, Y, Z. X and Y cannot be taken together, and exactly two must be chosen. Which is possible?",
       (("X وY", "X and Y"), ("X وZ", "X and Z"), ("X فقط", "X only"), ("X وY وZ", "X, Y, and Z")), "B",
       ("ignores the incompatibility", "ignores the required count", "ignores both count and incompatibility"),
       "ELIMINATE_INVALID_OPTIONS", 1.0, "Eliminates options against both constraints.", 40),
    _q("L05", L, "MULTI_STEP_INFERENCE", "CONDITIONAL_CHAIN", "HARD",
       "إذا نجح الطالب في A يستطيع أخذ B. وإذا أخذ B يستطيع التقدّم لـ C. نجح عمر في A ولم يأخذ B بعد. ماذا نعرف الآن؟",
       "Passing A permits B; taking B permits applying for C. Omar passed A but has not taken B. What is known now?",
       (("مؤهل لـB فقط وفق المعطيات", "eligible for B only from the facts"), ("مؤهل مباشرة لـC", "immediately eligible for C"),
        ("نجح في C", "passed C"), ("غير مؤهل لأي شيء", "eligible for nothing")), "A",
       ("skips a required intermediate step", "turns eligibility into completion", "ignores satisfied A"),
       "CHAIN_WITHOUT_SKIPPING", 1.1, "Stops the inference at the last supported step.", 55),
    _q("L06", L, "DEDUCTIVE_REASONING", "NECESSARY_VS_SUFFICIENT", "HARD",
       "دخول المختبر يتطلب بطاقة صالحة. ليان معها بطاقة صالحة. ما الاستنتاج المضمون؟",
       "Lab entry requires a valid card. Layan has a valid card. What is guaranteed?",
       (("دخلت المختبر", "she entered the lab"), ("يمكنها استيفاء شرط البطاقة، لكن قد توجد شروط أخرى", "she satisfies the card condition, but others may exist"),
        ("لا تحتاج أي شرط آخر حتماً", "no other condition can exist"), ("بطاقتها غير صالحة", "her card is invalid")), "B",
       ("treats a necessary condition as sufficient", "assumes the rule is exhaustive", "contradicts the stated fact"),
       "DISTINGUISH_NECESSITY", 1.15, "Avoids affirming an outcome from one necessary condition.", 60),

    _q("M01", M, "PROPORTIONAL_REASONING", "PERCENTAGE", "EASY",
       "أنجز طالب 18 من 24 مهمة. ما النسبة؟", "A student completed 18 of 24 tasks. What percentage is that?",
       (("60%", "60%"), ("70%", "70%"), ("75%", "75%"), ("80%", "80%")), "C",
       ("uses an incorrect denominator", "rounds an incorrect ratio", "confuses remaining with completed"),
       "COMPUTE_PROPORTION", 1.0, "Forms completed/total and converts to percent.", 25),
    _q("M02", M, "ALGEBRAIC_REASONING", "ONE_STEP_EQUATION", "EASY",
       "إذا كان 5x = 35، فما x؟", "If 5x = 35, what is x?",
       (("5", "5"), ("7", "7"), ("30", "30"), ("40", "40")), "B",
       ("uses the coefficient as the answer", "subtracts instead of dividing", "adds instead of isolating x"),
       "ISOLATE_VARIABLE", .95, "Uses inverse division to isolate x.", 20),
    _q("M03", M, "RATE_REASONING", "UNIT_RATE", "MEDIUM",
       "تنجز آلة 120 عملية في 4 دقائق بمعدل ثابت. كم تنجز في 7 دقائق؟",
       "A machine completes 120 operations in 4 minutes at a constant rate. How many in 7 minutes?",
       (("180", "180"), ("200", "200"), ("210", "210"), ("240", "240")), "C",
       ("adds a rough increment without unit rate", "uses an incorrect per-minute rate", "scales by doubling"),
       "DERIVE_AND_APPLY_RATE", 1.05, "Finds 30 per minute, then scales to seven minutes.", 40),
    _q("M04", M, "FUNCTION_REASONING", "FUNCTION_EVALUATION", "MEDIUM",
       "إذا كانت f(x) = 2x + 3، فما f(4)؟", "If f(x) = 2x + 3, what is f(4)?",
       (("8", "8"), ("10", "10"), ("11", "11"), ("14", "14")), "C",
       ("omits the constant", "adds before multiplying incorrectly", "multiplies the whole expression by x"),
       "SUBSTITUTE_AND_EVALUATE", 1.0, "Substitutes the input and respects operation order.", 30),
    _q("M05", M, "MATHEMATICAL_DECOMPOSITION", "SYSTEM_REASONING", "HARD",
       "مجموع عددين 26 والفرق بين الأكبر والأصغر 8. ما العددان؟",
       "Two numbers sum to 26 and the larger minus the smaller is 8. What are they?",
       (("17 و9", "17 and 9"), ("18 و8", "18 and 8"), ("16 و10", "16 and 10"), ("20 و6", "20 and 6")), "A",
       ("matches the sum but not the difference", "matches neither constraint exactly", "matches the sum but gives difference 14"),
       "SOLVE_TWO_CONSTRAINTS", 1.1, "Tests both sum and difference together.", 55),
    _q("M06", M, "PROPORTIONAL_REASONING", "COMPOUND_CHANGE", "HARD",
       "ارتفع سعر 200 بنسبة 20% ثم انخفض السعر الجديد 20%. ما السعر النهائي؟",
       "A price of 200 rises by 20%, then the new price falls by 20%. Final price?",
       (("192", "192"), ("200", "200"), ("204", "204"), ("160", "160")), "A",
       ("assumes equal percentages cancel", "applies the decrease to the original inconsistently", "keeps only the decrease"),
       "APPLY_COMPOUND_PERCENTAGES", 1.15, "Applies each percentage to its current base.", 60),

    _q("S01", S, "DATA_SUMMARY", "MEAN", "EASY", "ما متوسط القيم 4، 6، 8؟", "What is the mean of 4, 6, 8?",
       (("4", "4"), ("6", "6"), ("8", "8"), ("18", "18")), "B",
       ("chooses the minimum", "chooses the maximum", "reports the total rather than mean"),
       "CALCULATE_MEAN", 1.0, "Sums values and divides by their count.", 20),
    _q("S02", S, "PROBABILITY", "SIMPLE_PROBABILITY", "EASY",
       "صندوق فيه 2 كرة زرقاء و6 حمراء. ما احتمال اختيار كرة زرقاء عشوائياً؟",
       "A box has 2 blue and 6 red balls. Probability of choosing blue?",
       (("1/8", "1/8"), ("1/4", "1/4"), ("1/3", "1/3"), ("3/4", "3/4")), "B",
       ("uses one favorable item instead of two", "divides favorable by unfavorable", "reports red probability"),
       "FORM_PROBABILITY_RATIO", .95, "Divides favorable outcomes by all outcomes.", 25),
    _q("S03", S, "DISTRIBUTION_REASONING", "OUTLIER_EFFECT", "MEDIUM",
       "العلامات 70، 72، 74، 76، 98. أي عبارة أدق؟", "Scores are 70, 72, 74, 76, 98. Which statement is most accurate?",
       (("98 ترفع المتوسط أكثر من الوسيط", "98 raises the mean more than the median"), ("98 تخفض المتوسط", "98 lowers the mean"),
        ("المتوسط والوسيط متساويان حتماً", "mean and median must be equal"), ("لا يمكن حساب الوسيط", "median cannot be found")), "A",
       ("reverses the outlier direction", "assumes robust and sensitive measures match", "ignores the ordered middle value"),
       "INTERPRET_OUTLIER", 1.05, "Compares how an extreme value affects mean and median.", 40),
    _q("S04", S, "DATA_INTERPRETATION", "TABLE_COMPARISON", "MEDIUM",
       "في جدول: المجموعة A درست ساعتين ومتوسطها 70، وB أربع ساعات ومتوسطها 78، وC ست ساعات ومتوسطها 79. ما الوصف المدعوم؟",
       "Table: A studied 2h and averaged 70; B 4h and 78; C 6h and 79. What is supported?",
       (("الزيادة من 4 إلى 6 ساعات رافقها تحسن صغير", "the increase from 4h to 6h accompanied a small gain"),
        ("ست ساعات تضمن 79 لكل طالب", "six hours guarantees 79 for every student"),
        ("الدراسة تسبب العلامة وحدها", "study time alone causes the grade"), ("المجموعة A هي الأعلى", "group A is highest")), "A",
       ("turns an average into an individual guarantee", "claims causation from an observational table", "misreads the ranking"),
       "COMPARE_TABULAR_VALUES", 1.0, "States only the bounded pattern visible in the table.", 45),
    _q("S05", S, "STATISTICAL_REASONING", "CORRELATION_CAUSATION", "HARD",
       "وجدت دراسة أن الطلاب الذين يحضرون جلسات مراجعة أكثر يحصلون غالباً على علامات أعلى. ما الاستنتاج الآمن؟",
       "A study finds students attending more review sessions often have higher grades. Safest conclusion?",
       (("الجلسات هي السبب المؤكد الوحيد", "sessions are the only proven cause"), ("يوجد ارتباط، وقد توجد عوامل أخرى", "there is an association; other factors may exist"),
        ("العلامات العالية تسبب الحضور حتماً", "high grades definitely cause attendance"), ("لا توجد أي علاقة", "there is no relationship")), "B",
       ("confuses association with exclusive causation", "reverses causation without evidence", "denies the observed association"),
       "BOUND_CAUSAL_CLAIM", 1.15, "Separates observed association from unproven causation.", 55),
    _q("S06", S, "DATA_DECISION", "BASE_RATE_REASONING", "HARD",
       "اختبار إنذار صحيح في 90% من الحالات، لكن الحالة نفسها نادرة جداً (1%). قبل الجزم بعد إنذار واحد، ما المعلومة الأهم أيضاً؟",
       "An alert is correct in 90% of cases, but the condition is rare (1%). Before concluding from one alert, what else matters?",
       (("لون الشاشة", "screen color"), ("معدل الإنذارات الكاذبة ومعدل انتشار الحالة", "false-positive rate and base rate"),
        ("اسم المصمم فقط", "only the designer's name"), ("عدد صفحات التقرير", "report page count")), "B",
       ("uses irrelevant presentation detail", "substitutes authority for needed data", "uses an irrelevant size measure"),
       "INTEGRATE_BASE_RATE", 1.2, "Recognizes that accuracy alone is insufficient for a rare event.", 65),

    _q("T01", T, "CONCEPTUAL_COMPREHENSION", "MAIN_IDEA", "EASY",
       "النص: «تقسيم الدراسة على عدة أيام يساعد على تثبيت المعرفة أكثر من جلسة طويلة واحدة». ما الفكرة الرئيسة؟",
       "Text: 'Spreading study over several days supports retention better than one long session.' Main idea?",
       (("الدراسة الموزعة تدعم التذكر", "distributed study supports retention"), ("يجب إلغاء الجلسات القصيرة", "short sessions should be removed"),
        ("عدد الأيام غير مهم", "number of days never matters"), ("جلسة واحدة أفضل دائماً", "one session is always better")), "A",
       ("reverses the recommendation", "overgeneralizes beyond the statement", "contradicts the stated comparison"),
       "EXTRACT_MAIN_IDEA", 1.0, "Selects the passage's central claim.", 25),
    _q("T02", T, "CONCEPT_COMPARISON", "DISTINGUISH_CONCEPTS", "EASY",
       "أي عبارة تميّز «الفهم» عن «الحفظ» بشكل أفضل؟", "Which best distinguishes understanding from memorization?",
       (("الفهم يتيح شرح الفكرة وتطبيقها، والحفظ يسترجعها كما هي", "understanding supports explanation/application; memorization recalls"),
        ("هما الشيء نفسه دائماً", "they are always identical"), ("الحفظ يضمن التطبيق الجديد", "memorization guarantees novel application"),
        ("الفهم لا يحتاج معنى", "understanding needs no meaning")), "A",
       ("collapses distinct operations", "turns recall into guaranteed transfer", "removes meaning from comprehension"),
       "COMPARE_CONCEPTS", .95, "Contrasts recall with explanation and transfer.", 25),
    _q("T03", T, "CAUSAL_COMPREHENSION", "MECHANISM", "MEDIUM",
       "قاعدة: الضغط على النظام يزداد عندما تصل طلبات أكثر مما يستطيع معالجته. وصلت الطلبات أسرع من المعالجة. ماذا نتوقع؟",
       "Rule: system load grows when requests arrive faster than processing. Requests now arrive faster. Expected result?",
       (("ينخفض الضغط", "load falls"), ("يبقى الضغط صفراً", "load stays zero"), ("يتراكم الضغط", "load accumulates"), ("تختفي الطلبات", "requests disappear")), "C",
       ("reverses the causal direction", "ignores the imbalance", "invents deletion not in the rule"),
       "APPLY_CAUSAL_RULE", 1.05, "Applies the stated mechanism to a matching case.", 35),
    _q("T04", T, "CONCEPTUAL_TRANSFER", "ANALOGY_APPLICATION", "MEDIUM",
       "تعلمت أن تقسيم مشكلة كبيرة إلى أجزاء صغيرة يسهل حلها. أين تطبق المبدأ نفسه؟",
       "Breaking a large problem into smaller parts helps solve it. Where is the same principle applied?",
       (("كتابة مشروع على وحدات واختبار كل وحدة", "building a project in modules and testing each"),
        ("تجاهل نصف المتطلبات", "ignoring half the requirements"), ("اختيار أول جواب بلا قراءة", "choosing the first answer unread"),
        ("حفظ اسم المشكلة فقط", "memorizing only the problem name")), "A",
       ("removes requirements instead of decomposing", "avoids analysis", "keeps a label without structure"),
       "TRANSFER_PRINCIPLE", 1.0, "Recognizes the same structure in a new context.", 40),
    _q("T05", T, "CONCEPTUAL_STRUCTURE", "DEPENDENCY_MODEL", "HARD",
       "مفهوم B يعتمد على A، وC يعتمد على B. إذا كان فهم A غير ثابت، ما خطة التعلم الأكثر منطقية؟",
       "B depends on A, and C depends on B. If A is unstable, what is the most logical learning plan?",
       (("ابدأ بـC وتجاهل A", "start with C and ignore A"), ("ثبّت A ثم B ثم C", "stabilize A, then B, then C"),
        ("ادرس C وA فقط", "study C and A only"), ("احفظ أسماء المفاهيم", "memorize concept names")), "B",
       ("reverses the dependency chain", "skips the intermediate dependency", "substitutes labels for structure"),
       "ORDER_DEPENDENT_CONCEPTS", 1.1, "Uses prerequisite structure to sequence learning.", 50),
    _q("T06", T, "CONCEPTUAL_TRANSFER", "BOUNDARY_CONDITIONS", "HARD",
       "مبدأ يقول: «التغذية الراجعة السريعة تحسن التعلم عندما يستطيع الطالب مراجعة خطئه». أي حالة لا يضمن فيها المبدأ التحسن؟",
       "Principle: rapid feedback improves learning when the learner can review the error. Where is improvement not guaranteed?",
       (("تصل الملاحظة ويُسمح بالمراجعة", "feedback arrives and review is allowed"),
        ("تصل الملاحظة لكن لا يعرف الطالب الخطأ ولا يستطيع مراجعته", "feedback arrives but the learner cannot identify or review the error"),
        ("يراجع الطالب سبب الخطأ", "the learner reviews the error's cause"), ("يطبق الطالب التصحيح", "the learner applies the correction")), "B",
       ("satisfies the stated condition", "supports the mechanism", "applies the mechanism"),
       "TEST_BOUNDARY_CONDITION", 1.15, "Checks whether the principle's enabling condition holds.", 60),
)

QUESTIONS_BY_ID = {question.question_id: question for question in QUESTION_BANK}
DIFFICULTY_WEIGHT = {"EASY": 1.0, "MEDIUM": 1.5, "HARD": 2.0}


@dataclass(frozen=True)
class AnswerEvidence:
    question_id: str
    selected_option: str
    is_correct: bool
    response_time_ms: int
    self_confidence: str


@dataclass(frozen=True)
class DiagnosticDomainResult:
    domain: DiagnosticDomain
    score: int
    confidence: str
    response_count: int
    reason_codes: tuple[str, ...]
    reasoning_patterns: tuple[str, ...] = ()


def _quality_flags(responses: tuple[AnswerEvidence, ...]) -> set[str]:
    flags: set[str] = set()
    if len(responses) < TARGET_QUESTIONS:
        flags.add("INCOMPLETE_RESPONSES")
    if responses and sum(row.response_time_ms for row in responses) < 180_000:
        flags.add("UNREALISTICALLY_FAST")
    options = [row.selected_option for row in responses]
    if options and max(options.count(option) for option in set(options)) / len(options) >= .7:
        flags.add("REPETITIVE_OPTION_PATTERN")
    domain_accuracy: list[float] = []
    for domain in DiagnosticDomain:
        rows = [row for row in responses if QUESTIONS_BY_ID[row.question_id].domain is domain]
        if rows:
            domain_accuracy.append(sum(row.is_correct for row in rows) / len(rows))
    if len(domain_accuracy) == 5 and max(domain_accuracy) - min(domain_accuracy) >= .85:
        flags.add("CONTRADICTORY_PERFORMANCE")
    transitions = sum(a.selected_option != b.selected_option for a, b in zip(responses, responses[1:]))
    accuracy = sum(row.is_correct for row in responses) / len(responses) if responses else 0
    if (len(responses) >= 20 and transitions / (len(responses) - 1) > .9
            and .3 <= accuracy <= .7):
        flags.add("RANDOM_LOOKING_PATTERN")
    return flags


def score_domain(domain: DiagnosticDomain, responses: Iterable[AnswerEvidence]) -> DiagnosticDomainResult:
    """Difficulty/evidence weighted score, shrunk toward neutral when quality is weak."""
    all_rows = tuple(responses)
    rows = tuple(row for row in all_rows if QUESTIONS_BY_ID[row.question_id].domain is domain)
    possible = sum(DIFFICULTY_WEIGHT[QUESTIONS_BY_ID[row.question_id].difficulty]
                   * QUESTIONS_BY_ID[row.question_id].evidence_weight for row in rows)
    earned = sum(DIFFICULTY_WEIGHT[QUESTIONS_BY_ID[row.question_id].difficulty]
                 * QUESTIONS_BY_ID[row.question_id].evidence_weight
                 for row in rows if row.is_correct)
    base = 50.0 if not possible else 100 * earned / possible
    fast_count = sum(row.response_time_ms < max(MIN_RESPONSE_TIME_MS,
                     QUESTIONS_BY_ID[row.question_id].estimated_time_seconds * 250) for row in rows)
    timing_reliability = max(.7, 1 - fast_count * .05)
    halves = (rows[:3], rows[3:])
    half_rates = [sum(row.is_correct for row in half) / len(half) for half in halves if half]
    consistency = 1.0 if len(half_rates) < 2 else max(.75, 1 - abs(half_rates[0] - half_rates[1]) * .25)
    score = round(50 + (base - 50) * timing_reliability * consistency)
    flags = _quality_flags(all_rows)
    difficulty_coverage = {QUESTIONS_BY_ID[row.question_id].difficulty for row in rows}
    complete = len(rows) == 6 and difficulty_coverage == {"EASY", "MEDIUM", "HARD"}
    domain_consistent = len(half_rates) == 2 and abs(half_rates[0] - half_rates[1]) <= (1 / 3)
    if not complete or "UNREALISTICALLY_FAST" in flags or "REPETITIVE_OPTION_PATTERN" in flags:
        confidence = "LOW"
    elif domain_consistent and fast_count == 0 and not flags:
        confidence = "HIGH"
    else:
        confidence = "MEDIUM"
    high_wrong = sum(not row.is_correct and row.self_confidence == "HIGH" for row in rows)
    low_correct = sum(row.is_correct and row.self_confidence == "LOW" for row in rows)
    patterns: list[str] = []
    if len(rows) == 6 and sum(row.is_correct for row in rows) >= 5:
        patterns.append("STRONG_SYSTEMATIC_REASONING")
    if rows and mean(row.response_time_ms for row in rows) > 75_000 and sum(row.is_correct for row in rows) >= 4:
        patterns.append("CAREFUL_BUT_SLOWER")
    if fast_count >= 2 and sum(row.is_correct for row in rows) <= 3:
        patterns.append("FAST_BUT_ERROR_PRONE")
    if high_wrong >= 2:
        patterns.append("SELF_CONFIDENCE_ABOVE_EVIDENCE")
    if low_correct >= 2:
        patterns.append("SELF_CONFIDENCE_BELOW_PERFORMANCE")
    if len(rows) == 6 and sum(row.is_correct for row in rows[3:]) <= 1:
        patterns.append("DIFFICULTY_WITH_MULTI_STEP_PROBLEMS")
    reasons = ["MODELED_DIAGNOSTIC_BASELINE", f"VALID_RESPONSES_{len(rows)}",
               "FULL_DIFFICULTY_COVERAGE" if complete else "INCOMPLETE_DIFFICULTY_COVERAGE"]
    reasons.extend(sorted(flags))
    return DiagnosticDomainResult(domain, max(0, min(100, score)), confidence, len(rows),
                                  tuple(dict.fromkeys(reasons)), tuple(patterns))


def select_next_question(responses: tuple[AnswerEvidence, ...]) -> DiagnosticQuestion | None:
    """Return the next fixed item; all 30 items are required exactly once."""
    answered = {row.question_id for row in responses}
    return next((question for question in QUESTION_BANK if question.question_id not in answered), None)


def public_question(question: DiagnosticQuestion) -> dict[str, object]:
    """Return only visible content; measured domain and grading internals stay hidden."""
    return {
        "question_id": question.question_id,
        "assessment_version": question.assessment_version,
        "prompt_ar": question.prompt_ar,
        "prompt_en": question.prompt_en,
        "options": [{"option_id": option.option_id, "text_ar": option.text_ar, "text_en": option.text_en}
                    for option in question.options],
    }
