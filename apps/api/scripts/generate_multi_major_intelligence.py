"""Generate deterministic multi-major Student Intelligence content.

The canonical course list is read from the reviewed multi-plan release artifact.
The generated Python module is self-contained application content; runtime never
reads the release workspace or infers skills from mutable course names.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from pprint import pformat


# major: (question prefix, ((domain, ((skill, en, ar, en definition, ar definition), ...)), ...))
SPECS = {
    "CS": ("CS", (
        ("CS_PROGRAMMING_OOP_FOUNDATIONS", (
            ("CS_PROGRAMMING", "Programming foundations", "أساسيات البرمجة", "trace control flow, variables, and modular procedures", "تتبّع تدفق التنفيذ والمتغيرات والإجراءات المعيارية"),
            ("CS_OBJECT_ORIENTATION", "Object-oriented design", "التصميم كائني التوجه", "model state and behavior through encapsulated classes and objects", "نمذجة الحالة والسلوك من خلال الأصناف والكائنات المغلفة"))),
        ("CS_DATA_STRUCTURES_ALGORITHMS", (
            ("CS_DATA_STRUCTURES", "Data structures", "تراكيب البيانات", "select structures according to access, update, and memory trade-offs", "اختيار التراكيب وفق مفاضلات الوصول والتحديث والذاكرة"),
            ("CS_ALGORITHM_ANALYSIS", "Algorithm analysis", "تحليل الخوارزميات", "reason about correctness and time or space complexity", "الاستدلال على الصحة وتعقيد الزمن أو الذاكرة"))),
        ("CS_SYSTEMS_OPERATING_SYSTEMS", (
            ("CS_COMPUTER_SYSTEMS", "Computer systems", "أنظمة الحاسوب", "connect machine representation, architecture, and program execution", "ربط تمثيل الآلة والبنية المعمارية بتنفيذ البرامج"),
            ("CS_OPERATING_SYSTEMS", "Operating systems", "أنظمة التشغيل", "manage processes, concurrency, memory, and persistent resources", "إدارة العمليات والتزامن والذاكرة والموارد الدائمة"))),
        ("CS_DATABASES_DATA_MANAGEMENT", (
            ("CS_DATABASES", "Database design", "تصميم قواعد البيانات", "model normalized data and preserve integrity with constraints", "نمذجة بيانات مطبّعة وحفظ التكامل بالقيود"),
            ("CS_DATA_MANAGEMENT", "Data management", "إدارة البيانات", "query, index, transact, and govern stored data", "استعلام البيانات المخزنة وفهرستها ومعاملاتها وحوكمتها"))),
        ("CS_NETWORKS_COMPUTATIONAL_FOUNDATIONS", (
            ("CS_NETWORKS", "Computer networks", "شبكات الحاسوب", "explain layered communication, addressing, and reliable transfer", "تفسير الاتصال الطبقي والعنونة والنقل الموثوق"),
            ("CS_COMPUTATIONAL_THEORY", "Computational foundations", "الأسس الحاسوبية", "use discrete models, formal languages, and computability limits", "استخدام النماذج المتقطعة واللغات الصورية وحدود القابلية للحوسبة"))),
    )),
    "CYBER": ("CY", (
        ("CYBER_FOUNDATIONS_RISK", (
            ("CYBER_SECURITY_FOUNDATIONS", "Security foundations", "أسس الأمن السيبراني", "apply confidentiality, integrity, availability, and least privilege", "تطبيق السرية والتكامل والتوافر وأقل صلاحية"),
            ("CYBER_RISK_MANAGEMENT", "Risk management", "إدارة المخاطر", "evaluate assets, threats, vulnerabilities, likelihood, and impact", "تقييم الأصول والتهديدات والثغرات والاحتمال والأثر"))),
        ("CYBER_NETWORK_SECURITY", (
            ("CYBER_NETWORK_DEFENSE", "Network defense", "دفاع الشبكات", "segment, monitor, and filter network traffic defensively", "تقسيم حركة الشبكة ومراقبتها وترشيحها دفاعياً"),
            ("CYBER_SECURE_PROTOCOLS", "Secure protocols", "البروتوكولات الآمنة", "reason about authentication and protected data in transit", "الاستدلال على المصادقة وحماية البيانات أثناء النقل"))),
        ("CYBER_CRYPTOGRAPHY_COMMUNICATION", (
            ("CYBER_CRYPTOGRAPHY", "Cryptography", "التشفير", "choose primitives for confidentiality, integrity, and authenticity", "اختيار بدائيات تحقق السرية والتكامل والأصالة"),
            ("CYBER_KEY_MANAGEMENT", "Key management", "إدارة المفاتيح", "control cryptographic key generation, distribution, storage, and rotation", "ضبط توليد مفاتيح التشفير وتوزيعها وتخزينها وتدويرها"))),
        ("CYBER_SECURE_SYSTEMS_APPLICATIONS", (
            ("CYBER_SECURE_SYSTEMS", "Secure systems", "الأنظمة الآمنة", "harden platforms through isolation, patching, and secure configuration", "تحصين المنصات بالعزل والتحديث والتهيئة الآمنة"),
            ("CYBER_APPLICATION_SECURITY", "Application security", "أمن التطبيقات", "prevent input, identity, authorization, and dependency failures", "منع إخفاقات المدخلات والهوية والتفويض والاعتماديات"))),
        ("CYBER_FORENSICS_GOVERNANCE_OPERATIONS", (
            ("CYBER_FORENSICS_OPERATIONS", "Forensics and operations", "الأدلة الجنائية والعمليات", "preserve evidence and coordinate detection, containment, and recovery", "حفظ الأدلة وتنسيق الكشف والاحتواء والتعافي"),
            ("CYBER_GOVERNANCE_ETHICS", "Security governance and ethics", "حوكمة الأمن وأخلاقياته", "align controls with policy, law, accountability, and ethical limits", "مواءمة الضوابط مع السياسة والقانون والمساءلة والحدود الأخلاقية"))),
    )),
    "MATH": ("MATH", (
        ("MATH_CALCULUS_ANALYSIS", (
            ("MATH_CALCULUS", "Calculus", "التفاضل والتكامل", "reason with limits, derivatives, integrals, and rates of change", "الاستدلال بالنهايات والمشتقات والتكاملات ومعدلات التغير"),
            ("MATH_REAL_ANALYSIS", "Mathematical analysis", "التحليل الرياضي", "justify convergence and continuity from rigorous definitions", "تبرير التقارب والاستمرارية انطلاقاً من تعريفات دقيقة"))),
        ("MATH_LINEAR_ALGEBRA", (
            ("MATH_LINEAR_SYSTEMS", "Linear systems", "الأنظمة الخطية", "solve and interpret systems using matrices and elimination", "حل الأنظمة وتفسيرها بالمصفوفات والحذف"),
            ("MATH_VECTOR_SPACES", "Vector spaces", "الفضاءات المتجهية", "reason about bases, dimension, linear maps, and eigenstructure", "الاستدلال على الأسس والأبعاد والتحويلات الخطية والبنية الذاتية"))),
        ("MATH_DISCRETE_LOGIC", (
            ("MATH_LOGIC_PROOFS", "Logic and proof", "المنطق والبرهان", "construct valid direct, contradiction, and induction arguments", "بناء براهين مباشرة وبالتناقض والاستقراء"),
            ("MATH_DISCRETE_STRUCTURES", "Discrete structures", "البنى المتقطعة", "analyze sets, relations, graphs, and combinatorial objects", "تحليل المجموعات والعلاقات والرسوم والكائنات التوافقية"))),
        ("MATH_PROBABILITY_STATISTICS", (
            ("MATH_PROBABILITY", "Probability", "الاحتمالات", "model random events with conditional and distributional reasoning", "نمذجة الأحداث العشوائية بالاستدلال الشرطي والتوزيعي"),
            ("MATH_STATISTICS", "Mathematical statistics", "الإحصاء الرياضي", "estimate parameters and assess uncertainty from samples", "تقدير المعلمات وتقييم عدم اليقين من العينات"))),
        ("MATH_ALGEBRA_DIFFERENTIAL_REASONING", (
            ("MATH_ABSTRACT_ALGEBRA", "Abstract algebra", "الجبر المجرد", "reason about groups, rings, fields, and structure-preserving maps", "الاستدلال على الزمر والحلقات والحقول والتحويلات الحافظة للبنية"),
            ("MATH_DIFFERENTIAL_EQUATIONS", "Differential equations", "المعادلات التفاضلية", "model change and analyze solutions to ordinary or partial equations", "نمذجة التغير وتحليل حلول المعادلات العادية أو الجزئية"))),
    )),
    "PHYS": ("PHYS", (
        ("PHYS_CLASSICAL_MECHANICS", (
            ("PHYS_KINEMATICS_DYNAMICS", "Kinematics and dynamics", "الحركة والديناميكا", "connect motion measurements with forces and Newtonian models", "ربط قياسات الحركة بالقوى والنماذج النيوتنية"),
            ("PHYS_ENERGY_MOMENTUM", "Energy and momentum", "الطاقة والزخم", "apply conservation laws to interacting physical systems", "تطبيق قوانين الحفظ على الأنظمة الفيزيائية المتفاعلة"))),
        ("PHYS_ELECTRICITY_MAGNETISM", (
            ("PHYS_ELECTRIC_FIELDS", "Electricity", "الكهرباء", "relate charge, field, potential, current, and circuit behavior", "ربط الشحنة والمجال والجهد والتيار وسلوك الدوائر"),
            ("PHYS_MAGNETISM", "Magnetism", "المغناطيسية", "analyze magnetic forces, induction, and electromagnetic fields", "تحليل القوى المغناطيسية والحث والمجالات الكهرومغناطيسية"))),
        ("PHYS_WAVES_OPTICS", (
            ("PHYS_WAVES", "Waves", "الموجات", "reason about frequency, phase, interference, and propagation", "الاستدلال على التردد والطور والتداخل والانتشار"),
            ("PHYS_OPTICS", "Optics", "البصريات", "apply geometric and wave models to light and instruments", "تطبيق النماذج الهندسية والموجية على الضوء والأجهزة"))),
        ("PHYS_THERMODYNAMICS", (
            ("PHYS_THERMAL_SYSTEMS", "Thermal systems", "الأنظمة الحرارية", "distinguish temperature, heat, work, and state variables", "تمييز درجة الحرارة والحرارة والشغل ومتغيرات الحالة"),
            ("PHYS_THERMODYNAMIC_LAWS", "Thermodynamic laws", "قوانين الديناميكا الحرارية", "apply energy conservation and entropy constraints", "تطبيق حفظ الطاقة وقيود الإنتروبيا"))),
        ("PHYS_MODERN_EXPERIMENTAL", (
            ("PHYS_MODERN_PHYSICS", "Modern physics", "الفيزياء الحديثة", "use quantum and relativistic models beyond classical limits", "استخدام النماذج الكمومية والنسبية خارج حدود الكلاسيكيات"),
            ("PHYS_EXPERIMENTAL_METHODS", "Experimental physics", "الفيزياء التجريبية", "design measurements and quantify uncertainty and error", "تصميم القياسات وتكميم عدم اليقين والخطأ"))),
    )),
    "ARABIC": ("AR", (
        ("ARABIC_GRAMMAR_SYNTAX", (
            ("ARABIC_GRAMMAR", "Arabic grammar", "النحو العربي", "analyze grammatical roles, governance, and sentence structure", "تحليل الوظائف الإعرابية والعوامل وبنية الجملة"),
            ("ARABIC_SYNTAX", "Arabic syntax", "التركيب النحوي", "explain how constituent order and dependency shape meaning", "تفسير أثر ترتيب المكونات والعلاقات النحوية في المعنى"))),
        ("ARABIC_MORPHOLOGY", (
            ("ARABIC_MORPHOLOGY", "Arabic morphology", "الصرف العربي", "derive word forms through roots, patterns, and inflection", "اشتقاق صيغ الكلمات من الجذور والأوزان والتصريف"),
            ("ARABIC_LEXICAL_DERIVATION", "Lexical derivation", "الاشتقاق المعجمي", "relate derived forms to semantic and grammatical functions", "ربط الصيغ المشتقة بوظائفها الدلالية والنحوية"))),
        ("ARABIC_RHETORIC_STYLISTICS", (
            ("ARABIC_RHETORIC", "Arabic rhetoric", "البلاغة العربية", "identify figures of meaning, expression, and embellishment", "تمييز علوم المعاني والبيان والبديع"),
            ("ARABIC_STYLISTICS", "Stylistic analysis", "التحليل الأسلوبي", "interpret how linguistic choices create emphasis and effect", "تفسير كيفية صنع الاختيارات اللغوية للتوكيد والأثر"))),
        ("ARABIC_LITERATURE", (
            ("ARABIC_LITERARY_HISTORY", "Arabic literary history", "تاريخ الأدب العربي", "situate texts within periods, movements, and cultural contexts", "وضع النصوص ضمن عصورها واتجاهاتها وسياقاتها الثقافية"),
            ("ARABIC_LITERARY_CRITICISM", "Literary criticism", "النقد الأدبي", "support interpretations with textual and critical evidence", "دعم التأويلات بأدلة نصية ونقدية"))),
        ("ARABIC_LINGUISTICS_TEXT", (
            ("ARABIC_LINGUISTICS", "Arabic linguistics", "اللسانيات العربية", "analyze sound, form, structure, meaning, and language use", "تحليل الصوت والصيغة والتركيب والمعنى والاستعمال"),
            ("ARABIC_TEXTUAL_ANALYSIS", "Textual analysis", "تحليل النصوص", "connect cohesion, discourse structure, and context in Arabic texts", "ربط الاتساق وبنية الخطاب والسياق في النص العربي"))),
    )),
    "ENGLISH": ("EN", (
        ("ENGLISH_GRAMMAR_STRUCTURE", (
            ("ENGLISH_GRAMMAR", "English grammar", "قواعد اللغة الإنجليزية", "analyze clause structure, tense, agreement, and modification", "تحليل بنية الجملة والزمن والمطابقة والتعديل"),
            ("ENGLISH_LANGUAGE_STRUCTURE", "Language structure", "بنية اللغة", "relate form, function, and meaning across linguistic levels", "ربط الشكل والوظيفة والمعنى عبر المستويات اللغوية"))),
        ("ENGLISH_LINGUISTICS", (
            ("ENGLISH_LINGUISTICS", "Linguistics", "علم اللغة", "apply phonological, morphological, syntactic, and semantic analysis", "تطبيق التحليل الصوتي والصرفي والنحوي والدلالي"),
            ("ENGLISH_SOCIOLINGUISTICS", "Language in society", "اللغة والمجتمع", "explain variation and language choice in social contexts", "تفسير التنوع والاختيار اللغوي في السياقات الاجتماعية"))),
        ("ENGLISH_LITERATURE", (
            ("ENGLISH_LITERARY_HISTORY", "English literary history", "تاريخ الأدب الإنجليزي", "place works within periods, genres, and intellectual movements", "وضع الأعمال ضمن العصور والأجناس والتيارات الفكرية"),
            ("ENGLISH_LITERARY_CRITICISM", "Literary criticism", "النقد الأدبي", "develop evidence-based readings using critical approaches", "بناء قراءات مدعومة بالأدلة باستخدام مناهج نقدية"))),
        ("ENGLISH_ACADEMIC_WRITING", (
            ("ENGLISH_ACADEMIC_WRITING", "Academic writing", "الكتابة الأكاديمية", "build coherent claims with evidence, citation, and revision", "بناء حجج مترابطة بالأدلة والتوثيق والمراجعة"),
            ("ENGLISH_COMPOSITION", "Composition", "الإنشاء", "organize audience-aware prose at paragraph and essay level", "تنظيم نثر يراعي الجمهور على مستوى الفقرة والمقال"))),
        ("ENGLISH_CRITICAL_COMMUNICATION", (
            ("ENGLISH_CRITICAL_READING", "Critical reading", "القراءة النقدية", "evaluate argument, evidence, implication, and authorial choices", "تقييم الحجة والدليل والضمنيات واختيارات الكاتب"),
            ("ENGLISH_COMMUNICATION", "English communication", "التواصل باللغة الإنجليزية", "adapt spoken and written communication to purpose and audience", "تكييف التواصل الشفهي والكتابي مع الغرض والجمهور"))),
    )),
    "HISTORY": ("HIST", (
        ("HISTORY_METHOD_SOURCES", (
            ("HISTORY_METHOD", "Historical method", "المنهج التاريخي", "form questions and construct arguments from contextual evidence", "صياغة الأسئلة وبناء الحجج من أدلة موضوعة في سياقها"),
            ("HISTORY_SOURCE_CRITICISM", "Source criticism", "نقد المصادر", "assess provenance, purpose, bias, corroboration, and silence", "تقييم المصدر والغرض والتحيز والتعضيد وما يسكت عنه النص"))),
        ("HISTORY_ARAB_ISLAMIC_JORDAN", (
            ("HISTORY_ARAB_ISLAMIC", "Arab and Islamic history", "التاريخ العربي والإسلامي", "analyze institutions and change across Arab and Islamic societies", "تحليل المؤسسات والتحول في المجتمعات العربية والإسلامية"),
            ("HISTORY_JORDAN", "Jordanian history", "التاريخ الأردني", "connect Jordanian developments to regional and global contexts", "ربط التطورات الأردنية بالسياقات الإقليمية والعالمية"))),
        ("HISTORY_ANCIENT_MEDIEVAL", (
            ("HISTORY_ANCIENT", "Ancient history", "التاريخ القديم", "interpret states, societies, and material evidence in antiquity", "تفسير الدول والمجتمعات والأدلة المادية في العصور القديمة"),
            ("HISTORY_MEDIEVAL", "Medieval history", "تاريخ العصور الوسطى", "compare political, social, and intellectual formations in the medieval world", "مقارنة التكوينات السياسية والاجتماعية والفكرية في عالم العصور الوسطى"))),
        ("HISTORY_MODERN_CONTEMPORARY", (
            ("HISTORY_MODERN", "Modern history", "التاريخ الحديث", "explain state, empire, economy, and reform in the modern era", "تفسير الدولة والإمبراطورية والاقتصاد والإصلاح في العصر الحديث"),
            ("HISTORY_CONTEMPORARY", "Contemporary history", "التاريخ المعاصر", "evaluate recent transformations through multiple perspectives", "تقييم التحولات الحديثة من منظورات متعددة"))),
        ("HISTORY_WORLD_ANALYSIS", (
            ("HISTORY_WORLD", "World history", "تاريخ العالم", "compare connected developments across regions and periods", "مقارنة التطورات المترابطة عبر الأقاليم والعصور"),
            ("HISTORY_CAUSAL_ANALYSIS", "Historical analysis", "التحليل التاريخي", "weigh causation, continuity, change, and contingency", "موازنة السببية والاستمرار والتغير والاحتمال التاريخي"))),
    )),
    "TRANS": ("TR", (
        ("TRANS_THEORY", (
            ("TRANS_TRANSLATION_THEORY", "Translation theory", "نظرية الترجمة", "compare equivalence, purpose, audience, and translation strategies", "مقارنة التكافؤ والغرض والجمهور واستراتيجيات الترجمة"),
            ("TRANS_TRANSLATION_CRITICISM", "Translation criticism", "نقد الترجمة", "evaluate a translation against function, evidence, and alternatives", "تقييم الترجمة وفق الوظيفة والدليل والبدائل"))),
        ("TRANS_ARABIC_ENGLISH", (
            ("TRANS_AR_EN", "Arabic-English translation", "الترجمة العربية الإنجليزية", "transfer meaning between Arabic and English while respecting structure", "نقل المعنى بين العربية والإنجليزية مع مراعاة البنية"),
            ("TRANS_EN_AR", "English-Arabic translation", "الترجمة الإنجليزية العربية", "produce idiomatic Arabic from English source discourse", "إنتاج عربية سليمة وطبيعية من خطاب مصدر إنجليزي"))),
        ("TRANS_TERMINOLOGY_LEXICOGRAPHY", (
            ("TRANS_TERMINOLOGY", "Terminology management", "إدارة المصطلحات", "select consistent domain terms using authoritative evidence", "اختيار مصطلحات تخصصية متسقة بأدلة موثوقة"),
            ("TRANS_LEXICOGRAPHY", "Lexicography", "صناعة المعاجم", "analyze dictionary entries, sense, usage, and equivalence", "تحليل المداخل المعجمية والدلالة والاستعمال والتكافؤ"))),
        ("TRANS_SPECIALIZED_MEDIA_LITERARY", (
            ("TRANS_SPECIALIZED", "Specialized translation", "الترجمة المتخصصة", "handle legal, technical, media, and institutional conventions", "معالجة أعراف النصوص القانونية والتقنية والإعلامية والمؤسسية"),
            ("TRANS_LITERARY", "Literary translation", "الترجمة الأدبية", "recreate voice, imagery, rhythm, and ambiguity responsibly", "إعادة بناء الصوت والصورة والإيقاع والغموض بمسؤولية"))),
        ("TRANS_EDITING_LOCALIZATION", (
            ("TRANS_EDITING", "Translation editing", "تحرير الترجمة", "revise accuracy, fluency, coherence, and consistency", "مراجعة الدقة والطلاقة والترابط والاتساق"),
            ("TRANS_LOCALIZATION", "Localization and intercultural competence", "التوطين والكفاءة الثقافية", "adapt content to locale, culture, medium, and user expectations", "تكييف المحتوى مع البيئة والثقافة والوسيط وتوقعات المستخدم"))),
    )),
    "ECON": ("ECON", (
        ("ECON_MICROECONOMICS", (
            ("ECON_MICRO_THEORY", "Microeconomic theory", "النظرية الاقتصادية الجزئية", "analyze choice, scarcity, incentives, and marginal trade-offs", "تحليل الاختيار والندرة والحوافز والمفاضلات الحدية"),
            ("ECON_MARKET_ANALYSIS", "Market analysis", "تحليل الأسواق", "reason about supply, demand, elasticity, and market structure", "الاستدلال على العرض والطلب والمرونة وبنية السوق"))),
        ("ECON_MACROECONOMICS", (
            ("ECON_MACRO_THEORY", "Macroeconomic theory", "النظرية الاقتصادية الكلية", "connect output, inflation, unemployment, and aggregate demand", "ربط الناتج والتضخم والبطالة والطلب الكلي"),
            ("ECON_GROWTH_CYCLES", "Growth and cycles", "النمو والدورات", "analyze long-run growth and short-run economic fluctuations", "تحليل النمو طويل الأجل والتقلبات الاقتصادية قصيرة الأجل"))),
        ("ECON_QUANTITATIVE_ECONOMETRICS", (
            ("ECON_QUANTITATIVE", "Quantitative economics", "الاقتصاد الكمي", "represent economic relationships with mathematical models", "تمثيل العلاقات الاقتصادية بنماذج رياضية"),
            ("ECON_ECONOMETRICS", "Econometrics", "الاقتصاد القياسي", "estimate and interpret empirical models while checking assumptions", "تقدير النماذج التجريبية وتفسيرها وفحص افتراضاتها"))),
        ("ECON_MONETARY_PUBLIC", (
            ("ECON_MONETARY", "Monetary economics", "الاقتصاد النقدي", "explain money, banking, interest rates, and monetary transmission", "تفسير النقود والمصارف وأسعار الفائدة وانتقال السياسة النقدية"),
            ("ECON_PUBLIC", "Public economics", "الاقتصاد العام", "evaluate taxation, public spending, externalities, and welfare", "تقييم الضرائب والإنفاق العام والآثار الخارجية والرفاه"))),
        ("ECON_INTERNATIONAL_DEVELOPMENT", (
            ("ECON_INTERNATIONAL", "International economics", "الاقتصاد الدولي", "analyze trade, exchange rates, and cross-border adjustment", "تحليل التجارة وأسعار الصرف والتكيف عبر الحدود"),
            ("ECON_DEVELOPMENT", "Development economics", "اقتصاد التنمية", "evaluate institutions, poverty, inequality, and development policy", "تقييم المؤسسات والفقر وعدم المساواة وسياسات التنمية"))),
    )),
    "BBA": ("BBA", (
        ("BBA_MANAGEMENT_ORGANIZATION", (
            ("BBA_MANAGEMENT", "Management", "الإدارة", "plan, organize, lead, and control organizational work", "تخطيط العمل التنظيمي وتنظيمه وقيادته والرقابة عليه"),
            ("BBA_ORGANIZATIONAL_BEHAVIOR", "Organizational behavior", "السلوك التنظيمي", "analyze motivation, teams, leadership, and culture", "تحليل الدافعية والفرق والقيادة والثقافة"))),
        ("BBA_MARKETING", (
            ("BBA_MARKETING", "Marketing", "التسويق", "create value through segmentation, positioning, and the marketing mix", "صنع القيمة بالتجزئة والتموضع والمزيج التسويقي"),
            ("BBA_MARKET_RESEARCH", "Market research", "بحوث التسويق", "collect and interpret customer and market evidence", "جمع أدلة العملاء والسوق وتفسيرها"))),
        ("BBA_FINANCE_ACCOUNTING", (
            ("BBA_FINANCE", "Finance literacy", "الثقافة المالية", "evaluate cash flows, risk, return, and financing choices", "تقييم التدفقات النقدية والمخاطر والعائد وخيارات التمويل"),
            ("BBA_ACCOUNTING", "Accounting literacy", "الثقافة المحاسبية", "interpret financial statements and basic accounting relationships", "تفسير القوائم المالية والعلاقات المحاسبية الأساسية"))),
        ("BBA_HR_OPERATIONS", (
            ("BBA_HUMAN_RESOURCES", "Human resources", "الموارد البشرية", "align staffing, development, performance, and fair practice", "مواءمة التوظيف والتطوير والأداء والممارسة العادلة"),
            ("BBA_OPERATIONS", "Operations management", "إدارة العمليات", "design processes for capacity, quality, inventory, and flow", "تصميم العمليات للسعة والجودة والمخزون والتدفق"))),
        ("BBA_STRATEGY_ENTREPRENEURSHIP", (
            ("BBA_STRATEGY", "Business strategy", "استراتيجية الأعمال", "align capabilities and choices with competitive context", "مواءمة القدرات والخيارات مع السياق التنافسي"),
            ("BBA_ENTREPRENEURSHIP", "Entrepreneurship", "ريادة الأعمال", "test opportunities, value propositions, and viable business models", "اختبار الفرص وعروض القيمة ونماذج الأعمال القابلة للحياة"))),
    )),
    "ACC": ("ACC", (
        ("ACC_FINANCIAL_ACCOUNTING", (
            ("ACC_FINANCIAL_RECORDING", "Financial accounting", "المحاسبة المالية", "recognize and record transactions using the accounting equation", "الاعتراف بالمعاملات وتسجيلها وفق المعادلة المحاسبية"),
            ("ACC_FINANCIAL_STATEMENTS", "Financial statements", "القوائم المالية", "prepare and interpret statements and their relationships", "إعداد القوائم المالية وتفسيرها وربطها"))),
        ("ACC_MANAGERIAL_COST", (
            ("ACC_COST_ACCOUNTING", "Cost accounting", "محاسبة التكاليف", "trace and allocate costs for products, services, and activities", "تتبع التكاليف وتخصيصها للمنتجات والخدمات والأنشطة"),
            ("ACC_MANAGERIAL_DECISIONS", "Managerial accounting", "المحاسبة الإدارية", "use relevant costs, budgets, and variance evidence in decisions", "استخدام التكاليف الملائمة والموازنات والانحرافات في القرارات"))),
        ("ACC_AUDITING", (
            ("ACC_AUDIT_EVIDENCE", "Audit evidence", "أدلة التدقيق", "design procedures that obtain sufficient appropriate evidence", "تصميم إجراءات توفر أدلة كافية وملائمة"),
            ("ACC_INTERNAL_CONTROL", "Internal control", "الرقابة الداخلية", "evaluate control design, risk, and operating effectiveness", "تقييم تصميم الرقابة والمخاطر وفعالية التشغيل"))),
        ("ACC_TAXATION", (
            ("ACC_TAX_PRINCIPLES", "Tax principles", "مبادئ الضرائب", "apply tax rules to defined facts and taxable bases", "تطبيق القواعد الضريبية على وقائع وأوعية محددة"),
            ("ACC_TAX_COMPLIANCE", "Tax compliance", "الامتثال الضريبي", "document, calculate, and report obligations accurately", "توثيق الالتزامات وحسابها والإفصاح عنها بدقة"))),
        ("ACC_INFORMATION_REPORTING", (
            ("ACC_INFORMATION_SYSTEMS", "Accounting information systems", "نظم المعلومات المحاسبية", "control transaction cycles, data, and reporting workflows", "ضبط دورات المعاملات والبيانات ومسارات التقارير"),
            ("ACC_REPORTING_STANDARDS", "Reporting standards", "معايير التقارير", "apply recognition, measurement, presentation, and disclosure requirements", "تطبيق متطلبات الاعتراف والقياس والعرض والإفصاح"))),
    )),
    "DJOURN": ("DJ", (
        ("DJOURN_NEWS_REPORTING", (
            ("DJOURN_NEWS_WRITING", "News writing", "الكتابة الخبرية", "write accurate leads and structured stories for public understanding", "كتابة مقدمات دقيقة وأخبار منظمة لفهم الجمهور"),
            ("DJOURN_REPORTING", "Reporting", "العمل الصحفي الميداني", "gather, attribute, contextualize, and verify reportable facts", "جمع الوقائع القابلة للنشر ونسبها ووضعها في السياق والتحقق منها"))),
        ("DJOURN_DIGITAL", (
            ("DJOURN_DIGITAL_PUBLISHING", "Digital publishing", "النشر الرقمي", "adapt stories to web, mobile, platform, and accessibility needs", "تكييف القصص للويب والهاتف والمنصات وإتاحة الوصول"),
            ("DJOURN_DATA_JOURNALISM", "Data journalism", "صحافة البيانات", "analyze and communicate data without overstating evidence", "تحليل البيانات وتوصيلها دون مبالغة في الدليل"))),
        ("DJOURN_VERIFICATION_SOURCES", (
            ("DJOURN_VERIFICATION", "Verification", "التحقق الصحفي", "corroborate claims, media, location, time, and provenance", "تعضيد الادعاءات والوسائط والمكان والزمان والمصدر"),
            ("DJOURN_SOURCE_EVALUATION", "Source evaluation", "تقييم المصادر", "assess authority, independence, motive, and evidentiary limits", "تقييم السلطة والاستقلال والدافع وحدود الدليل"))),
        ("DJOURN_LAW_ETHICS", (
            ("DJOURN_MEDIA_LAW", "Media law", "قانون الإعلام", "recognize legal boundaries affecting publication and rights", "تمييز الحدود القانونية المؤثرة في النشر والحقوق"),
            ("DJOURN_ETHICS", "Journalism ethics", "أخلاقيات الصحافة", "balance accuracy, independence, harm, fairness, and accountability", "موازنة الدقة والاستقلال والضرر والإنصاف والمساءلة"))),
        ("DJOURN_MULTIMEDIA_AUDIENCE", (
            ("DJOURN_MULTIMEDIA", "Multimedia storytelling", "السرد متعدد الوسائط", "combine text, image, audio, video, and interaction coherently", "دمج النص والصورة والصوت والفيديو والتفاعل بترابط"),
            ("DJOURN_AUDIENCE", "Audience engagement", "تفاعل الجمهور", "use audience evidence while preserving editorial judgment", "استخدام أدلة الجمهور مع حفظ الحكم التحريري"))),
    )),
    "RTV": ("RTV", (
        ("RTV_BROADCAST_PRODUCTION", (
            ("RTV_BROADCAST_JOURNALISM", "Broadcast journalism", "الصحافة الإذاعية والتلفزيونية", "report clearly for time-bound audio and video formats", "إعداد تقارير واضحة لصيغ صوتية ومرئية محددة الزمن"),
            ("RTV_PRODUCTION_FOUNDATIONS", "Production foundations", "أسس الإنتاج", "coordinate editorial, technical, and performance roles", "تنسيق الأدوار التحريرية والتقنية والأدائية"))),
        ("RTV_SCRIPT_STORY", (
            ("RTV_SCRIPTWRITING", "Scriptwriting", "كتابة النصوص", "write for voice, image, timing, sequence, and cueing", "الكتابة للصوت والصورة والتوقيت والتسلسل والإشارات"),
            ("RTV_STORYTELLING", "Broadcast storytelling", "السرد الإذاعي والتلفزيوني", "shape narrative structure for audience attention and comprehension", "تشكيل بنية سردية لانتباه الجمهور وفهمه"))),
        ("RTV_CAMERA_AUDIO_EDITING", (
            ("RTV_CAMERA_AUDIO", "Camera and audio", "الكاميرا والصوت", "control framing, exposure, focus, microphone choice, and signal quality", "ضبط التكوين والتعريض والتركيز واختيار الميكروفون وجودة الإشارة"),
            ("RTV_EDITING", "Audio-video editing", "المونتاج الصوتي والمرئي", "construct continuity, pace, meaning, and clean transitions", "بناء الاستمرارية والإيقاع والمعنى والانتقالات السليمة"))),
        ("RTV_WORKFLOWS", (
            ("RTV_RADIO_WORKFLOW", "Radio production", "إنتاج الراديو", "plan studio, field, live, recorded, and post-production audio", "تخطيط صوت الاستوديو والميدان والبث الحي والتسجيل وما بعد الإنتاج"),
            ("RTV_TELEVISION_WORKFLOW", "Television production", "إنتاج التلفزيون", "coordinate pre-production, floor, control-room, and post-production stages", "تنسيق مراحل ما قبل الإنتاج والاستوديو وغرفة التحكم وما بعد الإنتاج"))),
        ("RTV_LAW_ETHICS_AUDIENCE", (
            ("RTV_MEDIA_ETHICS_LAW", "Broadcast law and ethics", "قانون وأخلاقيات البث", "apply rights, consent, fairness, accuracy, and harm standards", "تطبيق معايير الحقوق والموافقة والإنصاف والدقة والضرر"),
            ("RTV_AUDIENCE", "Broadcast audience", "جمهور البث", "interpret audience needs and metrics without surrendering editorial responsibility", "تفسير حاجات الجمهور ومقاييسه دون التخلي عن المسؤولية التحريرية"))),
    )),
    "LAW": ("LAW", (
        ("LAW_FOUNDATIONS_REASONING", (
            ("LAW_LEGAL_FOUNDATIONS", "Legal foundations", "الأسس القانونية", "distinguish sources, hierarchy, jurisdiction, and legal institutions", "تمييز مصادر القانون وهرميته والاختصاص والمؤسسات القانونية"),
            ("LAW_LEGAL_REASONING", "Legal reasoning", "الاستدلال القانوني", "identify issues and apply governing rules to material facts", "تحديد المسائل وتطبيق القواعد الحاكمة على الوقائع الجوهرية"))),
        ("LAW_CIVIL", (
            ("LAW_OBLIGATIONS", "Civil obligations", "الالتزامات المدنية", "analyze formation, performance, breach, and remedies", "تحليل نشوء الالتزام وتنفيذه والإخلال به والجزاءات"),
            ("LAW_PROPERTY_FAMILY", "Property and personal status", "الأموال والأحوال الشخصية", "reason about rights, ownership, family relations, and succession", "الاستدلال على الحقوق والملكية والعلاقات الأسرية والإرث"))),
        ("LAW_CRIMINAL", (
            ("LAW_CRIMINAL_SUBSTANCE", "Criminal law", "القانون الجنائي", "analyze elements, culpability, defenses, and proportional liability", "تحليل الأركان والقصد والدفوع وتناسب المسؤولية"),
            ("LAW_CRIMINAL_PROCEDURE", "Criminal procedure", "أصول المحاكمات الجزائية", "protect legality and due process from investigation through judgment", "حماية الشرعية وضمانات المحاكمة من التحقيق حتى الحكم"))),
        ("LAW_PUBLIC", (
            ("LAW_CONSTITUTIONAL", "Constitutional law", "القانون الدستوري", "reason about state powers, rights, and constitutional limits", "الاستدلال على سلطات الدولة والحقوق والقيود الدستورية"),
            ("LAW_ADMINISTRATIVE", "Administrative law", "القانون الإداري", "evaluate public authority, legality, discretion, and judicial review", "تقييم السلطة العامة والمشروعية والتقدير والرقابة القضائية"))),
        ("LAW_COMMERCIAL_INTERNATIONAL_PROCEDURE", (
            ("LAW_COMMERCIAL_INTERNATIONAL", "Commercial and international law", "القانون التجاري والدولي", "analyze transactions, entities, cross-border rules, and obligations", "تحليل المعاملات والكيانات والقواعد والالتزامات العابرة للحدود"),
            ("LAW_CIVIL_PROCEDURE", "Civil procedure", "أصول المحاكمات المدنية", "apply jurisdiction, pleadings, evidence, judgment, and enforcement rules", "تطبيق قواعد الاختصاص واللوائح والإثبات والحكم والتنفيذ"))),
    )),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-data", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    with (args.release_data / "morshidi_plan_ids.json").open(encoding="utf-8") as handle:
        plan_ids = json.load(handle)["new_plans"]
    rows_by_major: dict[str, list[dict[str, str]]] = {major: [] for major in SPECS}
    plan_key_by_major: dict[str, str] = {}
    with (args.release_data / "plan_courses.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            major = row["plan_key"].split(":")[2]
            if major in rows_by_major:
                plan_key_by_major[major] = row["plan_key"]
                rows_by_major[major].append({
                    "course_code": row["course_code"],
                    "name_ar": row["name_ar"],
                    "group_code": row["group_code"],
                })

    plans = {}
    for major, (prefix, domains) in SPECS.items():
        rows = rows_by_major[major]
        if not rows:
            raise SystemExit(f"No canonical courses for {major}")
        plan_key = plan_key_by_major[major]
        plans[major] = {
            "plan_key": plan_key,
            "study_plan_id": plan_ids[plan_key],
            "question_prefix": prefix,
            "courses": tuple(rows),
            "domains": domains,
        }

    output = (
        '"""Generated deterministic content for the 14 additional canonical curricula.\n\n'
        "Generated by scripts/generate_multi_major_intelligence.py. Do not hand edit.\n"
        '"""\n\nfrom __future__ import annotations\n\n'
        f"MULTI_MAJOR_CONTENT = {pformat(plans, width=120, sort_dicts=False)}\n"
    )
    args.output.write_text(output, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
