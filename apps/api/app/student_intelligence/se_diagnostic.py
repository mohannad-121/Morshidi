"""Software Engineering diagnostic question bank and scoring engine.

30-item fixed-form diagnostic across 5 core undergraduate SE domains:
1. SE_PROGRAMMING_OOP_DATA_STRUCTURES (SE01 - SE06)
2. SE_REQUIREMENTS_MODELING_ANALYSIS (SE07 - SE12)
3. SE_DESIGN_ARCHITECTURE_PATTERNS (SE13 - SE18)
4. SE_TESTING_QUALITY_MAINTENANCE (SE19 - SE24)
5. SE_LIFECYCLE_PROJECT_MANAGEMENT (SE25 - SE30)

Academic diagnostic only; questions assess foundational conceptual reasoning and principles.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from statistics import mean

from app.student_intelligence.diagnostic import (
    ASSESSMENT_VERSION,
    AnswerEvidence,
    DiagnosticDomainResult,
    Option,
    DIFFICULTY_WEIGHT,
    MIN_RESPONSE_TIME_MS,
    TARGET_QUESTIONS,
)


class SoftwareEngineeringDiagnosticDomain(str, Enum):
    SE_PROGRAMMING_OOP_DATA_STRUCTURES = "SE_PROGRAMMING_OOP_DATA_STRUCTURES"
    SE_REQUIREMENTS_MODELING_ANALYSIS = "SE_REQUIREMENTS_MODELING_ANALYSIS"
    SE_DESIGN_ARCHITECTURE_PATTERNS = "SE_DESIGN_ARCHITECTURE_PATTERNS"
    SE_TESTING_QUALITY_MAINTENANCE = "SE_TESTING_QUALITY_MAINTENANCE"
    SE_LIFECYCLE_PROJECT_MANAGEMENT = "SE_LIFECYCLE_PROJECT_MANAGEMENT"


@dataclass(frozen=True)
class SEDiagnosticQuestion:
    question_id: str
    domain: SoftwareEngineeringDiagnosticDomain
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


def _q(
    qid: str,
    domain: SoftwareEngineeringDiagnosticDomain,
    skill: str,
    subskill: str,
    difficulty: str,
    ar: str,
    en: str,
    choices: tuple[tuple[str, str], ...],
    answer: str,
    distractors: tuple[str, str, str],
    operation: str,
    weight: float,
    behavior: str,
    seconds: int,
) -> SEDiagnosticQuestion:
    option_ids = tuple(chr(65 + index) for index in range(4))
    wrong_ids = tuple(option_id for option_id in option_ids if option_id != answer)
    return SEDiagnosticQuestion(
        qid,
        domain,
        skill,
        subskill,
        difficulty,
        ar,
        en,
        tuple(Option(option_ids[index], *choice) for index, choice in enumerate(choices)),
        answer,
        dict(zip(wrong_ids, distractors, strict=True)),
        operation,
        weight,
        behavior,
        seconds,
    )


# Short aliases for domains
D1 = SoftwareEngineeringDiagnosticDomain.SE_PROGRAMMING_OOP_DATA_STRUCTURES
D2 = SoftwareEngineeringDiagnosticDomain.SE_REQUIREMENTS_MODELING_ANALYSIS
D3 = SoftwareEngineeringDiagnosticDomain.SE_DESIGN_ARCHITECTURE_PATTERNS
D4 = SoftwareEngineeringDiagnosticDomain.SE_TESTING_QUALITY_MAINTENANCE
D5 = SoftwareEngineeringDiagnosticDomain.SE_LIFECYCLE_PROJECT_MANAGEMENT

SE_QUESTION_BANK: tuple[SEDiagnosticQuestion, ...] = (
    # =========================================================================
    # DOMAIN 1: Programming, OOP & Data Structures (SE01 - SE06)
    # =========================================================================
    _q(
        "SE01", D1, "PROGRAMMING", "VARIABLE_SCOPE", "EASY",
        "ما هو النطاق (Scope) للمتغير المعرّف داخل دالة معينة (Local Variable)؟",
        "What is the scope of a variable declared inside a specific function (local variable)?",
        (
            ("متاح في كامل البرنامج وجميع الدوال", "Accessible across the entire program and all functions"),
            ("متاح فقط داخل نطاق الدالة التي عُرّف فيها", "Accessible only within the scope of the function where it is declared"),
            ("متاح في جميع الملفات التابعة للمشروع", "Accessible across all project source files"),
            ("يتم حذفه تلقائياً قبل تنفيذ الدالة", "Automatically deleted before the function executes"),
        ),
        "B",
        (
            "خلط بين المتغيرات العامة (Global) والمتغيرات المحلية",
            "اعتقاد خاطئ بأن النطاق يشمل جميع ملفات المشروع",
            "افتراض غير منطقي حول دورة حياة المتغير في الذاكرة",
        ),
        "CONCEPTUAL_RECALL", 1.0, "recognize_local_scope_boundaries", 35,
    ),
    _q(
        "SE02", D1, "OBJECT_ORIENTED_PROGRAMMING", "ENCAPSULATION", "EASY",
        "ما هو المبدأ الأساسي للكبسلة (Encapsulation) في البرمجة كائنية التوجه؟",
        "What is the primary principle of encapsulation in object-oriented programming?",
        (
            ("إخفاء التفاصيل الداخلية للبيانات والتحكم بالوصول إليها عبر واجهات محددة", "Hiding internal data details and restricting access via defined interfaces"),
            ("إمكانية وراثة الخصائص من أصناف متعددة في وقت واحد", "Enabling inheritance of properties from multiple classes simultaneously"),
            ("تنفيذ الدوال بأسماء مختلفة لتأدية نفس الوظيفة", "Implementing functions with different names to achieve the same task"),
            ("تحويل البيانات إلى كود تنفيذي مباشر بدون أصناف", "Converting data directly into executable code without classes"),
        ),
        "A",
        (
            "خلط بين الكبسلة والوراثة المتعددة (Multiple Inheritance)",
            "خلط بين الكبسلة والتحميل الزائد للدوال (Overloading)",
            "وصف يناقض مفهوم البرمجة كائنية التوجه",
        ),
        "PRINCIPLE_IDENTIFICATION", 1.0, "identify_encapsulation_goal", 40,
    ),
    _q(
        "SE03", D1, "OBJECT_ORIENTED_PROGRAMMING", "POLYMORPHISM", "MEDIUM",
        "عند إعادة كتابة دالة (Method Overriding) في صنف مشتق (Subclass)، ما هي الخاصية التي يتم تطبيقها عند الاستدعاء وقت التشغيل؟",
        "When method overriding is used in a derived subclass, which mechanism is applied during runtime invocation?",
        (
            ("الربط الساكن في وقت الترجمة (Static Binding)", "Static binding at compile-time"),
            ("التحميل الزائد للمعاملات (Operator Overloading)", "Operator overloading"),
            ("الربط الديناميكي وتعدد الأشكال (Dynamic Dispatch / Polymorphism)", "Dynamic dispatch / runtime polymorphism"),
            ("تغليف المتغيرات الثابتة (Static Encapsulation)", "Static encapsulation"),
        ),
        "C",
        (
            "الربط الساكن يحدث في وقت الترجمة قبل تنفيذ البرنامج ولا يدعم الـ overriding الديناميكي",
            "التحميل الزائد للمعاملات يتعلق بتغيير سلوك المعاملات الرياضية والمنطقية",
            "مصطلح غير صحيح لوصف استدعاء الدوال المشتقة في وقت التشغيل",
        ),
        "MECHANISM_ANALYSIS", 1.0, "trace_polymorphic_runtime_dispatch", 50,
    ),
    _q(
        "SE04", D1, "DATA_STRUCTURES", "QUEUE_STACK", "MEDIUM",
        "ما هو الفرق الجوهري بين بنية الطابور (Queue) والمكدس (Stack) في ترتيب معالجة العناصر؟",
        "What is the essential difference between a Queue and a Stack regarding processing order?",
        (
            ("الطابور يعتمد LIFO بينما المكدس يعتمد FIFO", "Queue follows LIFO while Stack follows FIFO"),
            ("كلاهما يعتمد مبدأ الوصول العشوائي المباشر (Random Access)", "Both rely on direct random access to elements"),
            ("الطابور يسمح بالإدراج والحذف من نفس النهاية فقط", "Queue allows insertion and deletion only at the same end"),
            ("الطابور يعتمد FIFO (الأول دخولا أول خروجاً) بينما المكدس يعتمد LIFO", "Queue follows FIFO (first-in, first-out) while Stack follows LIFO"),
        ),
        "D",
        (
            "عكس خاطئ لمبادئ التشغيل لكل من المكدس والطابور",
            "الطابور والمكدس هما هياكل بيانات خطية تسلسلية وليست ذات وصول عشوائي مباشر",
            "الإدراج والحذف من نفس النهاية يصف المكدس (Stack) وليس الطابور",
        ),
        "DATA_STRUCTURE_COMPARISON", 1.0, "distinguish_fifo_from_lifo", 45,
    ),
    _q(
        "SE05", D1, "DATA_STRUCTURES", "BST_TRAVERSAL", "HARD",
        "في شجرة البحث الثنائية (Binary Search Tree)، ما هو نوع المرور (Traversal) الذي ينتج قيماً مرتبة تصاعدياً؟",
        "In a Binary Search Tree (BST), which traversal produces values in sorted ascending order?",
        (
            ("المرور المسبق (Pre-order Traversal)", "Pre-order Traversal"),
            ("المرور الداخلي (In-order Traversal)", "In-order Traversal (Left, Root, Right)"),
            ("المرور اللاحق (Post-order Traversal)", "Post-order Traversal"),
            ("المرور بالمستويات (Level-order Traversal)", "Level-order Traversal"),
        ),
        "B",
        (
            "المرور المسبق يزور الجذر أولاً ثم الأبناء ولا ينتج قيماً مرتبة",
            "المرور اللاحق يزور الأبناء أولاً ثم الجذر ويستخدم في حذف الأشجار وتفريغها",
            "المرور بالمستويات يعتمد خوارزمية BFS ولا يضمن الترتيب المتصاعد للقيم",
        ),
        "ALGORITHM_REASONING", 1.0, "evaluate_tree_traversal_properties", 55,
    ),
    _q(
        "SE06", D1, "DATA_STRUCTURES", "HASHING_COMPLEXITY", "HARD",
        "في جدول التجزئة (Hash Table)، ما هو التعقيد الزمني لعملية البحث في أسوأ الحالات (Worst-case Time Complexity) عند حدوث تصادمات متكررة في سلسلة واحدة؟",
        "In a Hash Table, what is the worst-case search time complexity when repeated collisions collapse into a single chain?",
        (
            ("O(n) حيث تتدهور السلسلة إلى بنية شبيهة بالقائمة المترابطة", "O(n) where the bucket degrades into a linked-list search"),
            ("O(1) بغض النظر عن عدد التصادمات", "O(1) regardless of collision frequency"),
            ("O(log n) لأن التجزئة تعتمد بنية بحث ثنائية دائماً", "O(log n) because hashing always maintains a binary structure"),
            ("O(n^2) بسبب إعادة حساب دالة التجزئة لكل عنصر", "O(n^2) due to re-hashing all elements iteratively"),
        ),
        "A",
        (
            "التعقيد O(1) هو الحالة المثالية المتوسطة (Average Case) وليس أسوأ الحالات",
            "جداول التجزئة القياسية المعتمدة على Chaining لا تبني شجرة بحث ثنائية تلقائياً",
            "البحث الخطي في السلسلة المتدهورة يستغرق O(n) وليس O(n^2)",
        ),
        "COMPLEXITY_ANALYSIS", 1.0, "assess_hash_collision_degradation", 60,
    ),

    # =========================================================================
    # DOMAIN 2: Software Requirements, Modeling & Analysis (SE07 - SE12)
    # =========================================================================
    _q(
        "SE07", D2, "SOFTWARE_REQUIREMENTS", "REQUIREMENT_TYPES", "EASY",
        "أي من العبارات التالية تمثل متطلباً غير وظيفي (Non-Functional Requirement) لنظام برمجي؟",
        "Which of the following statements represents a Non-Functional Requirement for a software system?",
        (
            ("يجب أن يتمكن المستخدم من استرجاع كلمة المرور عبر البريد الإلكتروني", "The user must be able to reset their password via email"),
            ("يجب أن يقوم النظام بتسجيل بيانات الطالب وحفظ سجله الأكاديمي", "The system must register student details and persist academic records"),
            ("يجب ألا يتجاوز زمن استجابة النظام ثانيتين تحت حمولة 1000 مستخدم متزامن", "System response time must not exceed 2 seconds under 1,000 concurrent users"),
            ("يجب أن يُصدر النظام فاتورة إلكترونية بصيغة PDF عند إتمام الدفع", "The system must generate an electronic PDF invoice upon payment completion"),
        ),
        "C",
        (
            "استرجاع كلمة المرور هو وظيفة مباشرة يقدمها النظام للمستخدم (Functional Requirement)",
            "تسجيل وحفظ بيانات الطالب هو سلوك وظيفي أساسي للنظام",
            "إصدار الفاتورة عند الدفع هو ميزة وظيفية تنفيذية",
        ),
        "REQUIREMENT_CLASSIFICATION", 1.0, "distinguish_functional_from_quality_attributes", 40,
    ),
    _q(
        "SE08", D2, "SOFTWARE_MODELING_ANALYSIS", "USE_CASE_ACTORS", "EASY",
        "في مخطط حالات الاستخدام (Use Case Diagram)، ماذا يمثل 'الفاعل' (Actor)؟",
        "In a Use Case Diagram, what does an 'Actor' represent?",
        (
            ("فئة بيانات داخل قاعدة البيانات تخزن السجلات", "A database table entity that stores records"),
            ("دالة داخلية في النظام تقوم بالمعالجة الحسابية", "An internal system method performing computation"),
            ("مرحلة في دورة حياة تطوير البرمجيات", "A phase within the software development lifecycle"),
            ("كيان خارجي (مستخدم بشري أو نظام خارجي) يتفاعل مع النظام", "An external entity (human user or external system) interacting with the system"),
        ),
        "D",
        (
            "الفاعل ليس عنصراً تخزينياً أو جدولاً في قاعدة البيانات بل كياناً متفاعلاً",
            "الفاعل كيان خارجي عن حدود النظام (outside system boundary) وليس دالة داخلية",
            "الفاعل عنصر نمذجة سلوكية وليس مرحلة زمنية في دورة التطوير",
        ),
        "UML_NOTATION_RECOGNITION", 1.0, "identify_actor_role_in_use_cases", 35,
    ),
    _q(
        "SE09", D2, "SOFTWARE_REQUIREMENTS", "VERIFICATION_VS_VALIDATION", "MEDIUM",
        "ما هو الفرق المعياري بين التحقق البرمجي (Verification) والصلاحية البرمجية (Validation)؟",
        "What is the standard distinction between software Verification and software Validation?",
        (
            ("التحقق يعني فحص النظام أثناء التشغيل، والصلاحية تعني فحص الكود المصدري يدوياً", "Verification means runtime testing, Validation means manual code review"),
            ("التحقق: هل نبني المنتج بصورة صحيحة؟ والصلاحية: هل نبني المنتج الصحيح الذي يلبي حاجة العميل؟", "Verification: Are we building the product right? Validation: Are we building the right product?"),
            ("التحقق والصلاحية هما اسمان مترادفان لنفس النشاط في اختبار الوحدات", "Verification and Validation are identical synonyms for unit testing"),
            ("التحقق يخص الجوانب الأمنية فقط بينما الصلاحية تخص واجهات المستخدم فقط", "Verification concerns security only while Validation concerns UI only"),
        ),
        "B",
        (
            "التحقق يشمل مراجعات الكود والفحوصات الساكنة بينما الصلاحية تختبر مطابقة متطلبات المستخدم",
            "الخلط بين المفهومين يتجاهل الفرق الأساسي بين المطابقة للمواصفات وملاءمة الغرض الفعلي",
            "حصر المفهومين في مجالات ضيقة كالأمن أو الواجهات يخالف المبادئ الهندسية القياسية",
        ),
        "CONCEPTUAL_DISTINCTION", 1.0, "differentiate_verification_from_validation", 45,
    ),
    _q(
        "SE10", D2, "SOFTWARE_MODELING_ANALYSIS", "UML_RELATIONSHIPS", "MEDIUM",
        "في مخطط الأصناف (Class Diagram)، ما الذي يميز علاقة التكوين (Composition) عن علاقة التجميع (Aggregation)؟",
        "In a UML Class Diagram, what distinguishes a Composition relationship from an Aggregation relationship?",
        (
            ("في التكوين، تنتهي حياة الجزء تلقائياً بانتهاء حياة الكل (دورة حياة مشتركة)", "In Composition, the part's lifecycle strictly depends on the whole's lifecycle"),
            ("في التكوين، يمكن للجزء أن يستمر في الوجود والارتباط بكائنات أخرى بعد حذف الكل", "In Composition, the part can outlive the whole and reattach to other objects"),
            ("التجميع يمثل وراثة تامة بينما التكوين يمثل واجهة مشتركة", "Aggregation represents pure inheritance while Composition represents interfaces"),
            ("العلاقتان متطابقتان تماماً في المخطط ودلالات البرمجة كائنية التوجه", "The two relationships are completely identical in UML syntax and semantics"),
        ),
        "A",
        (
            "استمرار الجزء بعد حذف الكل يصف علاقة التجميع (Aggregation) وليس التكوين (Composition)",
            "التجميع والتكوين هما علاقات امتلاك واحتواء (has-a) وليستا علاقات وراثة (is-a)",
            "هناك فارق دلالي صريح في قوة الارتباط وإدارة دورة حياة الكائنات التابعة",
        ),
        "RELATIONSHIP_ANALYSIS", 1.0, "evaluate_composition_lifecycle_coupling", 50,
    ),
    _q(
        "SE11", D2, "SOFTWARE_MODELING_ANALYSIS", "SEQUENCE_DIAGRAMS", "HARD",
        "في مخطط التتابع (Sequence Diagram)، ماذا يمثل شريط التنشيط (Activation Bar) العمودي على خط حياة الكائن (Lifeline)؟",
        "In a UML Sequence Diagram, what does a vertical Activation Bar on an object's lifeline represent?",
        (
            ("الفترة التي يكون فيها الكائن غير موجود في الذاكرة", "The time period when the object does not exist in memory"),
            ("عدد الرسائل المرسلة من الكائن إلى قاعدة البيانات", "The total count of messages emitted toward the database"),
            ("الفترة الزمنية التي يقوم فيها الكائن بتنفيذ عملية أو ينتظر نتيجة عملية أخرى", "The duration during which the object is actively executing an operation or awaiting control"),
            ("نوع لغة البرمجة المستخدمة في بناء الكائن", "The underlying programming language used to construct the object"),
        ),
        "C",
        (
            "شريط التنشيط يدل على النشاط الفعلي والتنفيذ وليس انعدام وجود الكائن",
            "شريط التنشيط يمثل البُعد الزمني وليس عدداً كمياً للرسائل المنبثقة",
            "مخططات UML مستقلة عن لغة البرمجة التحتية ولا تعبر عن نوع اللغة",
        ),
        "DIAGRAM_SYNTAX_EVALUATION", 1.0, "interpret_sequence_diagram_execution_bars", 55,
    ),
    _q(
        "SE12", D2, "SOFTWARE_REQUIREMENTS", "SRS_SPECIFICATION", "HARD",
        "أي من الخصائص التالية تُعد أساسية لجعل المتطلب البرمجي في وثيقة المواصفات (SRS) 'قابلاً للاختبار' (Testable)؟",
        "Which characteristic is essential to make a requirement in an SRS document 'Testable'?",
        (
            ("استخدام عبارات وصفية عامة مثل 'سريع جداً' و'سهل الاستخدام للغاية'", "Using subjective qualifiers such as 'very fast' and 'extremely user-friendly'"),
            ("تجنب تحديد أي أرقام أو معايير قياس حتى لا تُقيّد المبرمجين", "Omitting quantitative metrics to avoid constraining developer creativity"),
            ("كتابة المتطلب بفقرات أدبية طويلة دون ترقيم أو فصل للمفاهيم", "Drafting requirements as dense prose without numbering or atomic clauses"),
            ("تحديد معيار كمي محدد وقابل للقياس والتحقق الموضوعي (Measurable & Quantifiable)", "Specifying clear, measurable, and unambiguous criteria that can be objectively evaluated"),
        ),
        "D",
        (
            "المصطلحات العامة الذاتية تجعل من المستحيل كتابة اختبار موضوعي بنتيجة نجاح أو فشل واضحة",
            "غياب الأرقام والحدود الملموسة يمنع وضع شروط قبول محددة (Acceptance Criteria)",
            "الفقرات الطويلة غير المفصولة تؤدي إلى الغموض وصعوبة تتبع وفحص المتطلبات الفردية",
        ),
        "REQUIREMENT_ENGINEERING_REASONING", 1.0, "assess_testable_requirement_criteria", 60,
    ),

    # =========================================================================
    # DOMAIN 3: Software Design, Architecture & Patterns (SE13 - SE18)
    # =========================================================================
    _q(
        "SE13", D3, "SOFTWARE_DESIGN_ARCHITECTURE", "COUPLING_COHESION", "EASY",
        "ما هو الهدف التصميمي الموصى به دائماً في هندسة البرمجيات المعيارية فيما يخص التماسك (Cohesion) والاقتران (Coupling)؟",
        "What is the recommended design objective regarding Cohesion and Coupling in modular software engineering?",
        (
            ("تماسك منخفض (Low Cohesion) واقتران مرتفع (High Coupling)", "Low Cohesion and High Coupling"),
            ("تماسك مرتفع (High Cohesion) واقتران منخفض (Loose/Low Coupling)", "High Cohesion and Low/Loose Coupling"),
            ("إلغاء التماسك والاقتران بالكامل عبر دمج جميع الوحدات في صنف واحد", "Eliminating modularity by consolidating everything into a single monolithic class"),
            ("اقتران مرتفع بين جميع المكونات لضمان التبعية المشتركة", "High Coupling across all components to force tight mutual dependencies"),
        ),
        "B",
        (
            "التماسك المنخفض يجعل الوحدة غير محددة الهدف والاقتران المرتفع يجعل النظام هشاً وصعب التعديل",
            "دمج كل شيء في صنف واحد يخلق كائناً ضخماً (God Object) ويناقض مبادئ التصميم السليم",
            "الاقتران المرتفع يؤدي إلى تأثير الدومينو حيث يسبب أي تغيير في مكون انهيار مكونات أخرى",
        ),
        "DESIGN_PRINCIPLE_RECALL", 1.0, "recognize_cohesion_coupling_ideal", 35,
    ),
    _q(
        "SE14", D3, "SOFTWARE_DESIGN_ARCHITECTURE", "MVC_ARCHITECTURE", "EASY",
        "في معمارية النمط (Model-View-Controller - MVC)، ما هو الدور الأساسي لطبقة المتحكم (Controller)؟",
        "In the MVC architectural pattern, what is the primary role of the Controller?",
        (
            ("تخزين البيانات والتعامل المباشر مع استعلامات قاعدة البيانات", "Storing data state and issuing direct database queries"),
            ("رسم واجهة المستخدم وتنسيق العناصر البصرية في الشاشة", "Rendering the graphical UI and styling visual presentation elements"),
            ("استقبال مدخلات المستخدم وتنسيق التفاعل بين النموذج (Model) والعرض (View)", "Receiving user input and coordinating interactions between Model and View"),
            ("إدارة شبكة الاتصال وضبط محولات التوجيه المادية", "Managing physical network hardware and routing switches"),
        ),
        "C",
        (
            "تخزين البيانات وإدارة قواعد البيانات هو مسؤولية النموذج (Model)",
            "رسم واجهة المستخدم وعرض المعلومات للمستخدم هو مسؤولية العرض (View)",
            "إدارة محولات الشبكة المادية تقع في نطاق البنية التحتية وليس معمارية التطبيق البرمجي",
        ),
        "ARCHITECTURAL_ROLE_IDENTIFICATION", 1.0, "identify_mvc_controller_responsibility", 40,
    ),
    _q(
        "SE15", D3, "DESIGN_PATTERNS", "SINGLETON_PATTERN", "MEDIUM",
        "ما هو الغرض التصميمي لنمط التصميم المفرد (Singleton Pattern)؟",
        "What is the core design intent of the Singleton Pattern?",
        (
            ("ضمان وجود نسخة واحدة فقط من الصنف وتوفير نقطة وصول عامة إليها", "Ensuring a class has only one instance while providing a global access point to it"),
            ("إنشاء عائلات من الكائنات المترابطة دون تحديد أصنافها الملموسة", "Creating families of related objects without specifying their concrete classes"),
            ("تحويل واجهة صنف موجود إلى واجهة أخرى متوافقة مع متطلبات العميل", "Converting the interface of a class into another interface clients expect"),
            ("السماح للكائن بتغيير سلوكه بالكامل عندما تتغير حالته الداخلية", "Allowing an object to alter its behavior when its internal state changes"),
        ),
        "A",
        (
            "إنشاء عائلات الكائنات المترابطة يصف نمط المصنع المجرد (Abstract Factory Pattern)",
            "تحويل الواجهات لتلائم متطلبات العميل يصف نمط المحول (Adapter Pattern)",
            "تغيير السلوك بتغير الحالة يصف نمط الحالة (State Pattern)",
        ),
        "PATTERN_IDENTIFICATION", 1.0, "recognize_singleton_pattern_intent", 45,
    ),
    _q(
        "SE16", D3, "DESIGN_PATTERNS", "FACTORY_PATTERN", "MEDIUM",
        "أي نمط تصميم إنشائي (Creational Pattern) يُستخدم لتفويض عملية إنشاء الكائنات للأصناف المشتقة بدلاً من استدعاء المنشئ المباشر؟",
        "Which creational pattern delegates object instantiation to subclasses instead of invoking concrete constructors directly?",
        (
            ("نمط المراقب (Observer Pattern)", "Observer Pattern"),
            ("نمط الديكور (Decorator Pattern)", "Decorator Pattern"),
            ("نمط الإستراتيجية (Strategy Pattern)", "Strategy Pattern"),
            ("نمط طريقة المصنع (Factory Method Pattern)", "Factory Method Pattern"),
        ),
        "D",
        (
            "نمط المراقب هو نمط سلوكي (Behavioral Pattern) لإعلام الكائنات بالتغييرات",
            "نمط الديكور هو نمط هيكلي (Structural Pattern) لإضافة سلوكيات ديناميكية للكائنات",
            "نمط الإستراتيجية هو نمط سلوكي لتبديل الخوارزميات في وقت التشغيل",
        ),
        "CREATIONAL_PATTERN_SELECTION", 1.0, "select_factory_method_for_instantiation", 50,
    ),
    _q(
        "SE17", D3, "SOFTWARE_DESIGN_ARCHITECTURE", "SOLID_PRINCIPLES", "HARD",
        "وفقاً لمبادئ SOLID، ما هو المعنى الدقيق لمبدأ الفتح والإغلاق (Open/Closed Principle - OCP)؟",
        "According to SOLID principles, what is the precise meaning of the Open/Closed Principle (OCP)?",
        (
            ("يجب إغلاق الكود ضد أي فحص خارجي وفتحه فقط لقسم تقنية المعلومات", "Source code must be closed to external audit and opened only to IT departments"),
            ("يجب أن تكون الكيانات البرمجية مفتوحة للتوسعة (Extension) ومغلقة أمام التعديل المباشر (Modification)", "Software entities should be open for extension but closed for modification"),
            ("يجب أن تُغلق الاتصالات بالشبكة فور الانتهاء من استعلام قاعدة البيانات", "Network connections must be closed immediately after database query completion"),
            ("يجب ألا يحتوي الصنف على أكثر من دالة مفتوحة للعامة (Public Method)", "A class should not expose more than a single public method"),
        ),
        "B",
        (
            "تفسير أمني خاطئ لمعنى الإغلاق البرمجي لا علاقة له بهندسة التصميم كائني التوجه",
            "إغلاق الاتصالات بالشبكة قاعدة تشغيلية في إدارة الموارد وليس مبدأ OCP في SOLID",
            "حصر الدوال العامة بدالة واحدة يخلط بين OCP ومفاهيم الواجهات الوظيفية البسيطة",
        ),
        "SOLID_PRINCIPLE_EVALUATION", 1.0, "evaluate_open_closed_principle", 55,
    ),
    _q(
        "SE18", D3, "SOFTWARE_DESIGN_ARCHITECTURE", "MICROSERVICES_VS_MONOLITH", "HARD",
        "ما هي المقايضة المعمارية (Architectural Trade-off) الأساسية عند الانتقال من المعمارية الموحدة (Monolith) إلى الخدمات المصغرة (Microservices)؟",
        "What is the primary architectural trade-off when moving from a Monolithic architecture to Microservices?",
        (
            ("الخدمات المصغرة تلغي الحاجة إلى شبكات الاتصال وإدارة السيرفرات", "Microservices eliminate the need for network connectivity and server operations"),
            ("المعمارية الموحدة تستهلك دائماً خطوط إنترنت أعلى من الخدمات المصغرة", "Monoliths always consume significantly higher network bandwidth than microservices"),
            ("اكتساب استقلالية النشر وقابلية التوسع لكل خدمة مقابل زيادة التعقيد التشغيلي والشبكي وتناسق البيانات", "Gaining independent deployment and scalability at the cost of increased operational, network, and data consistency complexity"),
            ("الخدمات المصغرة تضمن تناسق البيانات الفوري المتبادل دون الحاجة لأي بروتوكول موزع", "Microservices guarantee immediate ACID consistency across services without distributed protocols"),
        ),
        "C",
        (
            "الخدمات المصغرة تزيد بشكل حاد من الاعتماد على استقرار الشبكة وعمليات الاتصال بين الخدمات",
            "استهلاك الشبكة يعتمد على طبيعة الحمولات وليس قاعدة ثابتة ترجح المعمارية الموحدة",
            "الخدمات المصغرة تعتمد التناسق النهائي (Eventual Consistency) ويصعب فيها تحقيق ACID الفوري عبر قواعد بيانات موزعة",
        ),
        "ARCHITECTURAL_TRADEOFF_ANALYSIS", 1.0, "analyze_microservices_tradeoffs", 65,
    ),

    # =========================================================================
    # DOMAIN 4: Software Testing, Quality Assurance & Maintenance (SE19 - SE24)
    # =========================================================================
    _q(
        "SE19", D4, "SOFTWARE_TESTING_METRICS", "TESTING_TYPES", "EASY",
        "ما هو الفارق الجوهري بين فحص الصندوق الأسود (Black-Box Testing) وفحص الصندوق الأبيض (White-Box Testing)؟",
        "What is the fundamental difference between Black-Box and White-Box Testing?",
        (
            ("الصندوق الأسود يركز على المدخلات والمخرجات دون معرفة الكود الداخلي، بينما الصندوق الأبيض يفحص البنية البرمجية الداخلية والمسارات", "Black-box tests inputs/outputs without internal code knowledge; white-box inspects internal structure and execution paths"),
            ("الصندوق الأسود يُنفذ يدوياً فقط بينما الصندوق الأبيض مؤتمت بالكامل دائماً", "Black-box is exclusively manual while white-box is always fully automated"),
            ("الصندوق الأبيض يتم إجراؤه من قبل المستخدم النهائي فقط بعد إطلاق النظام", "White-box is performed exclusively by end users following production release"),
            ("الصندوق الأسود يفحص الأداء العتادي فقط بينما الصندوق الأبيض يفحص شفرات الويب فقط", "Black-box evaluates hardware performance only while white-box evaluates web scripts only"),
        ),
        "A",
        (
            "كلا النوعين يمكن أتمتتهما بواسطة أدوات الاختبار المختلفة كـ Selenium و JUnit",
            "الفحص الذي يُجريه المستخدم النهائي بعد الإطلاق يسمى فحص القبول (Acceptance Testing) أو بيتا",
            "كلا النوعين يفحصان البرمجيات وتطبيقاتها وليس عتاد الأجهزة فقط",
        ),
        "TESTING_PARADIGM_RECOGNITION", 1.0, "differentiate_black_from_white_box_testing", 40,
    ),
    _q(
        "SE20", D4, "SOFTWARE_TESTING_METRICS", "UNIT_TESTING", "EASY",
        "ما هو الهدف المباشر لاختبار الوحدة (Unit Testing) في المشاريع البرمجية؟",
        "What is the direct purpose of Unit Testing in software projects?",
        (
            ("التأكد من أن جميع الخوادم وقواعد البيانات تعمل بتناغم تحت أقصى ضغط", "Verifying all server clusters and databases operate harmoniously under peak stress"),
            ("تدريب مستخدمي النظام على خطوات الشراء والدفع الإلكتروني", "Training end users on checkout workflows and digital payment processing"),
            ("قياس سرعة استجابة الشبكة بين السيرفر والواجهة الأمامية", "Measuring network latency between servers and client frontends"),
            ("التحقق من صحة عمل أصغر جزء برمجي قابل للاختبار (كدالة أو صنف) بشكل معزول", "Verifying the correctness of the smallest testable piece of code (function/class) in isolation"),
        ),
        "D",
        (
            "فحص عمل الخوادم بتناغم تحت أقصى ضغط هو اختبار الإجهاد والتكامل (Stress & System Integration Testing)",
            "تدريب المستخدمين نشاط تشغيلي ودعم فني وليس اختبار وحدة برمجية",
            "قياس سرعة استجابة الشبكة هو اختبار أداء وبنية تحتية (Performance/Network Benchmark)",
        ),
        "TEST_OBJECTIVE_IDENTIFICATION", 1.0, "identify_unit_test_objective", 35,
    ),
    _q(
        "SE21", D4, "SOFTWARE_TESTING_METRICS", "REGRESSION_TESTING", "MEDIUM",
        "متى يُعد اختبار الانحدار (Regression Testing) ضرورياً في دورة حياة النظام؟",
        "When is Regression Testing essential within the software lifecycle?",
        (
            ("فقط عند كتابة الفكرة الأولى للمشروع وقبل كتابة أي كود مصدري", "Only during initial project ideation before any source code is written"),
            ("بعد إجراء أي تعديل برمجى أو إصلاح أخطاء للتأكد من عدم تعطل وظائف سابقة كانت تعمل بنجاح", "After applying code modifications or bug fixes to ensure existing functionality remains intact"),
            ("فقط عندما يطلب العميل تغيير لغة البرمجة المستخدمة في السيرفر", "Only when a client formally requests changing the backend language stack"),
            ("عند حذف قاعدة البيانات بالكامل لبدء مشروع جديد", "When clearing the database completely to initiate a greenfield project"),
        ),
        "B",
        (
            "قبل كتابة الكود لا توجد وظائف قائمة يُخشى انحدارها أو تعطلها",
            "اختبار الانحدار يرافق كل تغيير وإصلاح مستمر ولا يقتصر على تغيير لغات البرمجة",
            "بدء مشروع جديد لا يتضمن وظائف قديمة يجري التحقق من استمرار عملها",
        ),
        "REGRESSION_TRIGGER_ANALYSIS", 1.0, "identify_regression_testing_triggers", 45,
    ),
    _q(
        "SE22", D4, "SOFTWARE_QUALITY_ENGINEERING", "CODE_COVERAGE", "MEDIUM",
        "لماذا لا يُعد تحقيق تغطية تعليمات برمجية بنسبة 100% (100% Statement Coverage) دليلاً قاطعاً على خلو البرنامج من الأخطاء؟",
        "Why does achieving 100% Statement Coverage not guarantee that a program is bug-free?",
        (
            ("لأن تغطية التعليمات تفحص المتغيرات العامة فقط وتهمل الدوال المحلية", "Because statement coverage evaluates global variables only and ignores functions"),
            ("لأن أدوات التغطية لا تعمل بشكل صحيح إلا على أنظمة لينكس فقط", "Because code coverage engines operate reliably only on Linux environments"),
            ("لأنها تضمن فقط تنفيذ كل سطر مرة واحدة دون فحص جميع التفرعات المنطقية والمدخلات الحدودية والحالات الاستثنائية", "Because it only ensures each line executes once without testing all logical branch conditions, edge cases, and unexpected inputs"),
            ("لأن تغطية الكود مخصصة لقياس سرعة المعالج وليس جودة الكود البرمجي", "Because code coverage measures CPU execution clock speeds rather than logic correctness"),
        ),
        "C",
        (
            "تغطية التعليمات تمر على جميع الأسطر والدوال المنفذة ولا تنحصر بالمتغيرات العامة",
            "أدوات التغطية متعددة المنصات وتعمل على مختلف بيئات التشغيل القياسية",
            "تغطية الكود مقياس لاختبار الشفرة البرمجية وليس لاستهلاك عتاد المعالج",
        ),
        "QUALITY_METRIC_CRITIQUE", 1.0, "critique_statement_coverage_limits", 50,
    ),
    _q(
        "SE23", D4, "SOFTWARE_MAINTENANCE_EVOLUTION", "MAINTENANCE_TYPES", "HARD",
        "تعديل النظام البرمجي ليتوافق مع تحديث في نظام التشغيل أو تعديل في القوانين الحكومية يُصنف تحت أي نوع من أنواع صيانة البرمجيات؟",
        "Modifying a software system to comply with an OS platform upgrade or revised government regulation falls under which maintenance category?",
        (
            ("الصيانة التكيفية (Adaptive Maintenance)", "Adaptive Maintenance"),
            ("الصيانة التصحيحية (Corrective Maintenance)", "Corrective Maintenance"),
            ("الصيانة التحسينية / التكميلية (Perfective Maintenance)", "Perfective Maintenance"),
            ("الصيانة الوقائية (Preventive Maintenance)", "Preventive Maintenance"),
        ),
        "A",
        (
            "الصيانة التصحيحية تهدف لإصلاح أخطاء وثغرات برمجية ظهرت أثناء التشغيل الفعلي (Bug Fixing)",
            "الصيانة التحسينية تهدف لإضافة ميزات جديدة أو تحسين سرعة الأداء لتلبية رغبات إضافية",
            "الصيانة الوقائية تهدف لإعادة هيكلة الكود لتسهيل صيانته مستقبلاً قبل ظهور مشاكل",
        ),
        "MAINTENANCE_TYPE_CLASSIFICATION", 1.0, "classify_adaptive_software_maintenance", 55,
    ),
    _q(
        "SE24", D4, "SOFTWARE_QUALITY_ENGINEERING", "CYCLOMATIC_COMPLEXITY", "HARD",
        "ماذا يقيس مقياس التعقيد الدوري (McCabe Cyclomatic Complexity) في الشفرة البرمجية؟",
        "What does McCabe Cyclomatic Complexity measure in source code?",
        (
            ("عدد السطور الإجمالية في الملف المصدري متضمناً التعليقات والأسطر الفارغة", "The total line count of the source file including blank lines and comments"),
            ("حجم الذاكرة المستهلكة عند تحميل الكائن في الـ Heap", "The physical heap memory consumed when loading objects at runtime"),
            ("عدد مستخدمي النظام المتزامنين القادرين على الوصول للدالة", "The peak concurrent user quota supported by the routine"),
            ("عدد المسارات الخطية المستقلة (Independent Execution Paths) عبر المخطط الانسيابي للكود لتحديد الحد الأدنى من حالات الاختبار المطلوبة", "The number of linearly independent paths through the control-flow graph to determine the minimum test cases needed"),
        ),
        "D",
        (
            "عدد السطور مقياس حجمي بسيط (LOC) ولا يعكس التعقيد المنطقي أو مسارات التفرع",
            "الذاكرة المستهلكة تقاس بوحدات البايت والبروفايل ولا علاقة لها بالتعقيد الدوري",
            "عدد المستخدمين مقياس لسعة النظام وقابليته للتوسع وليس لمسارات الشفرة البرمجية",
        ),
        "COMPLEXITY_METRIC_ANALYSIS", 1.0, "evaluate_cyclomatic_complexity_formula", 60,
    ),

    # =========================================================================
    # DOMAIN 5: Software Lifecycle, Project Management & Practices (SE25 - SE30)
    # =========================================================================
    _q(
        "SE25", D5, "SOFTWARE_ENGINEERING_FOUNDATIONS", "SDLC_WATERFALL", "EASY",
        "ما هي نقطة الضعف الرئيسية لنموذج الشلال التقليدي (Waterfall Model) في مشاريع البرمجيات الحديثة؟",
        "What is the primary weakness of the traditional Waterfall Model in modern software projects?",
        (
            ("صعوبة وسرعة كتابة متطلباته الأولية", "Requirements are too brief and written too quickly"),
            ("عدم حاجته لأي مبرمجين ذوي خبرة", "It completely eliminates the need for experienced software engineers"),
            ("صعوبة التكيف مع التغييرات في المتطلبات بعد بدء مراحل التصميم والتنفيذ", "High inflexibility when accommodating requirement changes after design and implementation commence"),
            ("إلزامه بتسليم برمجية شغالة للمستخدم في نهاية كل أسبوع", "Mandating working software delivery to customers at the end of every week"),
        ),
        "C",
        (
            "نموذج الشلال يتطلب توثيقاً واسعاً وشاقاً ومكثفاً في مرحلة البداية",
            "نموذج الشلال يحتاج إلى مهندسين ومحللين متخصصين في كل مرحلة",
            "التسليم المتكرر أسبوعياً هو سمة من سمات منهجيات أجايل (Agile) وليس نموذج الشلال التتابعي",
        ),
        "SDLC_MODEL_CRITIQUE", 1.0, "identify_waterfall_inflexibility", 35,
    ),
    _q(
        "SE26", D5, "SOFTWARE_PROJECT_MANAGEMENT", "AGILE_SCRUM", "EASY",
        "في إطار عمل سكروم (Scrum Framework)، ما هو مفهوم 'السباق' (Sprint)؟",
        "In the Scrum Framework, what is a 'Sprint'?",
        (
            ("اجتماع سنوي لمجلس إدارة الشركة لمراجعة الميزانية المالية", "An annual executive board meeting to audit financial budgets"),
            ("فترة زمنية محددة وثابتة (Time-box عادة من أسبوعين إلى أربعة) يُنجز خلالها الفريق جزءاً قابلاً للتسليم من المنتج", "A fixed time-boxed iteration (typically 2-4 weeks) during which the team builds a shippable increment"),
            ("عملية تسريح للمبرمجين الذين لم يحققوا أعلى سرعة في كتابة الأسطر", "A termination process for developers writing the fewest lines of code"),
            ("برنامج حاسوبي تلقائي يقوم بكتابة الشفرات البرمجية للمشروع كاملاً", "An autonomous tool that synthesizes all application source code without humans"),
        ),
        "B",
        (
            "السباق هو دورة عمل متكررة مستمرة على مدار السنة وليس اجتماعاً إدارياً سنوياً",
            "إطار سكروم يركز على التعاون والتحسين المستمر للفريق وليس عقوبات التنافس الفردي",
            "السباق إطار تنظيمي بشري لإدارة الأولويات وتسليم البرمجيات وليس برنامجاً آلياً",
        ),
        "SCRUM_TERMINOLOGY_RECOGNITION", 1.0, "define_scrum_sprint_cycle", 40,
    ),
    _q(
        "SE27", D5, "SOFTWARE_ENGINEERING_PRACTICES", "VERSION_CONTROL_GIT", "MEDIUM",
        "في نظام إدارة النسخ (Git)، ماذا يحدث عند حدوث 'تعارض دمج' (Merge Conflict)؟",
        "In a version control system like Git, what causes a 'Merge Conflict'?",
        (
            ("تعديل نفس الأسطر في نفس الملف بتغييرات متعارضة في فرعين مختلفين ويحتاج للتدخل البشري لحله", "Opposing edits applied to the identical lines of the same file across branches requiring human resolution"),
            ("انتهاء مساحة القرص الصلب المخصصة للمستودع المحلي", "Local disk storage exhaustion on the developer's development machine"),
            ("نسيان المبرمج لكلمة المرور الخاصة بحسابه على منصة الاستضافة", "Developer forgotten password on the remote repository hosting provider"),
            ("تشغيل الكود على جهازين لهما أحجام شاشات مختلفة", "Running the compiled application on two workstations with disparate monitor resolutions"),
        ),
        "A",
        (
            "تعارض الدمج مشكلة منطقية في محتوى الشفرة المتقاطعة وليس مشكلة امتلاء سعة القرص",
            "فشل المصادقة يسبب خطأ صلاحيات (Auth error) وليس تعارض دمج (Merge Conflict)",
            "أحجام الشاشات لا تؤثر على تتبع التغييرات النصية في نظام Git",
        ),
        "GIT_WORKFLOW_REASONING", 1.0, "diagnose_git_merge_conflict", 45,
    ),
    _q(
        "SE28", D5, "SOFTWARE_ENGINEERING_PRACTICES", "CI_CD", "MEDIUM",
        "ما هي الميزة الجوهرية لتطبيق التكامل المستمر (Continuous Integration - CI) في فرق البرمجة؟",
        "What is the primary advantage of adopting Continuous Integration (CI) in software teams?",
        (
            ("إلغاء الحاجة تماماً لكتابة الاختبارات المؤتمتة بواسطة الفريق", "Completely removing the need for developers to author automated tests"),
            ("منع المستخدمين من تقديم أي شكاوى أو ملاحظات على النظام", "Preventing end-users from lodging any bug complaints or tickets"),
            ("زيادة زمن إصدار النسخ إلى فترات تباعدية تصل لعدة سنوات", "Lengthening release cycle latency to multi-year horizons"),
            ("دمج الشفرات البرمجية واختبارها وبناؤها تلقائياً وبشكل دوري لاكتشاف أخطاء التكامل مبكراً", "Automating code integration, builds, and test runs regularly to catch integration failures early"),
        ),
        "D",
        (
            "أنظمة CI تعتمد في جوهرها ونجاحها على وجود اختبارات مؤتمتة وموثوقة",
            "التكامل المستمر يحسن جودة المنتج لكنه لا يمنع التغذية الراجعة من المستخدمين",
            "الهدف الرئيسي من CI هو تقصير فترات التسليم وزيادة وتيرة الإصدار الموثوق وليس إبطاءها",
        ),
        "DEVOPS_PRACTICE_UNDERSTANDING", 1.0, "evaluate_ci_early_integration_benefit", 50,
    ),
    _q(
        "SE29", D5, "SOFTWARE_PROJECT_MANAGEMENT", "ESTIMATION_BURNDOWN", "HARD",
        "في لوحة حرق العمل (Burndown Chart) ضمن مشروع أجايل، ماذا يشير الخط الفعلي إذا كان يقع 'فوق' الخط المثالي للتقدم؟",
        "In an Agile Sprint Burndown Chart, what does it signify when the actual remaining effort line trends 'above' the ideal progress line?",
        (
            ("الفريق يسبق الجدول الزمني المحدد وسينتهي قبل موعد نهاية السباق", "The team is ahead of schedule and will complete tasks early"),
            ("المشروع متأخر عن الجدول الزمني، والعمل المتبقي أكثر مما كان مخططاً له في هذه المرحلة", "The sprint is behind schedule; remaining work exceeds the planned baseline at this point in time"),
            ("جميع أعضاء الفريق توقفوا عن العمل وغادروا المشروع نهائياً", "All team members have abandoned work and permanently exited the team"),
            ("النظام البرمجي أصبح أسرع في التنفيذ بنسبة 50%", "The software runtime performance improved by exactly 50 percent"),
        ),
        "B",
        (
            "الوقوع فوق الخط المثالي يعني بقاء مهام متبقية أكثر من المتوقع وليس التقدم المسبق",
            "الافتراض الدرامي بمغادرة الفريق قراءة عاطفية خاطئة لمؤشر إداري يعبر عن تأخر الوتيرة",
            "مخطط الحرق يقيس الجهد والزمن المتبقي لتنفيذ المهام وليس أداء وسرعة المعالج وقت التشغيل",
        ),
        "METRIC_INTERPRETATION", 1.0, "interpret_burndown_chart_variance", 55,
    ),
    _q(
        "SE30", D5, "SOFTWARE_ENGINEERING_FOUNDATIONS", "TECHNICAL_DEBT", "HARD",
        "ما هو المفهوم الهندسي لـ 'الدين الفني' (Technical Debt) في المشاريع البرمجية؟",
        "What is the engineering definition of 'Technical Debt' in software projects?",
        (
            ("المبالغ المالية المستحقة لمزودي خدمات السحابة والإنترنت", "Unpaid monetary invoices owed to cloud infrastructure providers"),
            ("تكلفة شراء رخص برامج التشغيل ومعدات الحواسيب المكتبية", "The procurement cost of commercial OS licenses and desktop hardware"),
            ("التكلفة الضمنية التراكمية الناتجة عن اختيار حلول برمجية سريعة وسهلة بدلاً من النهج الهندسي الأمثل، مما يزيد صعوبة التطوير مستقبلاً", "The implied cumulative cost of opting for quick, suboptimal code workarounds over solid engineering, making future modifications harder"),
            ("الفارق بين رواتب كبار المهندسين والمبرمجين المبتدئين في الشركة", "The net compensation delta between principal architects and junior developers"),
        ),
        "C",
        (
            "الدين الفني مجاز هندسي وليس ديناً مالياً نقدياً مستحقاً لمزودي الخدمات",
            "شراء المعدات يمثل أصولاً رأسمالية وتكاليف عتادية (CapEx) وليس ديناً برمجياً",
            "هيكل الرواتب والمكافآت موضوع إداري لا علاقة له بجودة وتصميم الشفرات المصدرية",
        ),
        "CONCEPTUAL_SYNTHESIS", 1.0, "synthesize_technical_debt_impact", 60,
    ),
)

SE_QUESTIONS_BY_ID: Mapping[str, SEDiagnosticQuestion] = {
    q.question_id: q for q in SE_QUESTION_BANK
}


def _se_quality_flags(responses: Iterable[AnswerEvidence]) -> set[str]:
    flags: set[str] = set()
    responses = tuple(responses)
    if len(responses) < TARGET_QUESTIONS:
        flags.add("INCOMPLETE_RESPONSES")
    if responses and sum(row.response_time_ms for row in responses) < 180_000:
        flags.add("UNREALISTICALLY_FAST")
    options = [row.selected_option for row in responses]
    if options and max(options.count(option) for option in set(options)) / len(options) >= 0.7:
        flags.add("REPETITIVE_OPTION_PATTERN")
    domain_accuracy: list[float] = []
    for domain in SoftwareEngineeringDiagnosticDomain:
        rows = [row for row in responses if SE_QUESTIONS_BY_ID[row.question_id].domain is domain]
        if rows:
            domain_accuracy.append(sum(row.is_correct for row in rows) / len(rows))
    if len(domain_accuracy) == 5 and max(domain_accuracy) - min(domain_accuracy) >= 0.85:
        flags.add("CONTRADICTORY_PERFORMANCE")
    transitions = sum(a.selected_option != b.selected_option for a, b in zip(responses, responses[1:]))
    accuracy = sum(row.is_correct for row in responses) / len(responses) if responses else 0
    if len(responses) >= 20 and transitions / (len(responses) - 1) > 0.9 and 0.3 <= accuracy <= 0.7:
        flags.add("RANDOM_LOOKING_PATTERN")
    return flags


def score_se_domain(
    domain: SoftwareEngineeringDiagnosticDomain,
    responses: Iterable[AnswerEvidence],
) -> DiagnosticDomainResult:
    all_rows = tuple(responses)
    rows = tuple(row for row in all_rows if SE_QUESTIONS_BY_ID[row.question_id].domain is domain)
    possible = sum(
        DIFFICULTY_WEIGHT[SE_QUESTIONS_BY_ID[row.question_id].difficulty]
        * SE_QUESTIONS_BY_ID[row.question_id].evidence_weight
        for row in rows
    )
    earned = sum(
        DIFFICULTY_WEIGHT[SE_QUESTIONS_BY_ID[row.question_id].difficulty]
        * SE_QUESTIONS_BY_ID[row.question_id].evidence_weight
        for row in rows
        if row.is_correct
    )
    base = 50.0 if not possible else 100 * earned / possible
    fast_count = sum(
        row.response_time_ms
        < max(
            MIN_RESPONSE_TIME_MS,
            SE_QUESTIONS_BY_ID[row.question_id].estimated_time_seconds * 250,
        )
        for row in rows
    )
    timing_reliability = max(0.7, 1 - fast_count * 0.05)
    halves = (rows[:3], rows[3:])
    half_rates = [sum(row.is_correct for row in half) / len(half) for half in halves if half]
    consistency = 1.0 if len(half_rates) < 2 else max(0.75, 1 - abs(half_rates[0] - half_rates[1]) * 0.25)
    score = round(50 + (base - 50) * timing_reliability * consistency)
    flags = _se_quality_flags(all_rows)
    difficulty_coverage = {SE_QUESTIONS_BY_ID[row.question_id].difficulty for row in rows}
    complete = len(rows) == 6 and difficulty_coverage == {"EASY", "MEDIUM", "HARD"}
    domain_consistent = len(half_rates) == 2 and abs(half_rates[0] - half_rates[1]) <= (1 / 3 + 1e-9)
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
    reasons = [
        "MODELED_DIAGNOSTIC_BASELINE",
        f"VALID_RESPONSES_{len(rows)}",
        "FULL_DIFFICULTY_COVERAGE" if complete else "INCOMPLETE_DIFFICULTY_COVERAGE",
    ]
    reasons.extend(sorted(flags))
    return DiagnosticDomainResult(
        domain,  # type: ignore[arg-type]
        max(0, min(100, score)),
        confidence,
        len(rows),
        tuple(dict.fromkeys(reasons)),
        tuple(patterns),
    )


def select_next_se_question(responses: tuple[AnswerEvidence, ...]) -> SEDiagnosticQuestion | None:
    answered = {row.question_id for row in responses}
    return next((q for q in SE_QUESTION_BANK if q.question_id not in answered), None)
