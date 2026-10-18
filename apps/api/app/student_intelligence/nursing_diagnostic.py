"""Server-authoritative deterministic academic reasoning diagnostic for Nursing.

This is an initial modeled evidence source, not an NCLEX, medical, psychological,
or official university licensing assessment. Answer keys, distractor interpretations,
weights, and scoring internals never cross the public API.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import mean
from typing import Iterable, Mapping

from app.student_intelligence.diagnostic import (
    ASSESSMENT_VERSION,
    DIFFICULTY_WEIGHT,
    MAX_RESPONSE_TIME_MS,
    MIN_RESPONSE_TIME_MS,
    SCORING_POLICY_VERSION,
    AnswerEvidence,
    DiagnosticDomainResult,
    DiagnosticQuestion,
    Option,
    public_question,
)

TARGET_QUESTIONS = 30


class NursingDiagnosticDomain(str, Enum):
    NURSING_FUNDAMENTALS = "NURSING_FUNDAMENTALS"
    ANATOMY_PHYSIOLOGY_FOUNDATIONS = "ANATOMY_PHYSIOLOGY_FOUNDATIONS"
    PHARMACOLOGY_FOUNDATIONS = "PHARMACOLOGY_FOUNDATIONS"
    PATIENT_SAFETY_INFECTION_CONTROL = "PATIENT_SAFETY_INFECTION_CONTROL"
    CLINICAL_ASSESSMENT_REASONING = "CLINICAL_ASSESSMENT_REASONING"


def _q(
    qid: str,
    domain: NursingDiagnosticDomain,
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
) -> DiagnosticQuestion:
    option_ids = tuple(chr(65 + index) for index in range(4))
    wrong_ids = tuple(option_id for option_id in option_ids if option_id != answer)
    return DiagnosticQuestion(
        qid,
        domain,  # type: ignore[arg-type]
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
        assessment_version=ASSESSMENT_VERSION,
    )


NF = NursingDiagnosticDomain.NURSING_FUNDAMENTALS
AP = NursingDiagnosticDomain.ANATOMY_PHYSIOLOGY_FOUNDATIONS
PH = NursingDiagnosticDomain.PHARMACOLOGY_FOUNDATIONS
PS = NursingDiagnosticDomain.PATIENT_SAFETY_INFECTION_CONTROL
CA = NursingDiagnosticDomain.CLINICAL_ASSESSMENT_REASONING

NURSING_QUESTION_BANK: tuple[DiagnosticQuestion, ...] = (
    # --- DOMAIN 1: NURSING FUNDAMENTALS (6 questions: 2 EASY, 2 MEDIUM, 2 HARD) ---
    _q(
        "N01", NF, "VITAL_SIGNS", "PULSE_ASSESSMENT", "EASY",
        "ما هو المدى الطبيعي لمعدل نبض القلب أثناء الراحة لدى شخص بالغ سليم؟",
        "What is the normal resting heart rate range for a healthy adult?",
        (("40 - 50 نبضة/دقيقة", "40 - 50 bpm"),
         ("60 - 100 نبضة/دقيقة", "60 - 100 bpm"),
         ("110 - 130 نبضة/دقيقة", "110 - 130 bpm"),
         ("140 - 160 نبضة/دقيقة", "140 - 160 bpm")),
        "B",
        ("bradycardic range confused with resting baseline",
         "tachycardic range confused with resting baseline",
         "severe tachycardia range confused with normal baseline"),
        "RECALL_NORMAL_RANGE", 0.95, "Recalls physiological resting heart rate reference values.", 20,
    ),
    _q(
        "N02", NF, "PATIENT_POSITIONING", "RESPIRATORY_COMFORT", "EASY",
        "ما هي الوضعية السريرية الأنسب لتسهيل التنفس وتمدد الرئتين لدى مريض يعاني من ضيق تنفس؟",
        "What clinical position best facilitates breathing and lung expansion for a patient experiencing dyspnea?",
        (("وضعية فاولر المرتفعة (High Fowler's)", "High Fowler's position"),
         ("وضعية الاستلقاء البطني (Prone)", "Prone position"),
         ("وضعية ترندلنبورغ (Trendelenburg)", "Trendelenburg position"),
         ("وضعية الاستلقاء الظهري المستوي (Supine)", "Supine position")),
        "A",
        ("compresses anterior chest wall hindering expansion",
         "shifts abdominal contents upward against the diaphragm",
         "flattens diaphragm reducing tidal volume"),
        "SELECT_POSITION", 0.95, "Identifies position maximizing thoracic excursion and diaphragm descent.", 25,
    ),
    _q(
        "N03", NF, "TISSUE_INTEGRITY", "PRESSURE_INJURY_PREVENTION", "MEDIUM",
        "لتجنب حدوث قرح الفراش (قرح الضغط) لدى مريض ملازم للسرير، ما هو الحد الأقصى للفترة الزمنية الموصى بها لتغيير وضعيته؟",
        "To prevent pressure injuries in a bedridden patient, what is the recommended maximum interval for repositioning?",
        (("كل 8 ساعات", "Every 8 hours"),
         ("كل 4 إلى 6 ساعات", "Every 4 to 6 hours"),
         ("كل ساعتين", "Every 2 hours"),
         ("مرة واحدة يومياً عند الاستحمام", "Once daily during bathing")),
        "C",
        ("prolonged interval causing irreversible tissue ischemia",
         "excessive interval risking deep tissue pressure damage",
         "grossly inadequate frequency failing preventive standards"),
        "APPLY_TIMING_PROTOCOL", 1.0, "Applies evidence-based repositioning frequency for tissue perfusion.", 30,
    ),
    _q(
        "N04", NF, "FLUID_BALANCE", "INTAKE_OUTPUT_CALCULATION", "MEDIUM",
        "مريض تلقى 1000 مل محلول وريدي، وشرب 400 مل ماء، وأخرج 900 مل بول و100 مل تصريف جراحي خلال 8 ساعات. ما هو صافي توازن السوائل؟",
        "A patient received 1000 mL IV fluids, drank 400 mL water, voided 900 mL urine, and had 100 mL surgical drainage over 8 hours. What is the net fluid balance?",
        (("-400 مل", "-400 mL"),
         ("+1400 مل", "+1400 mL"),
         ("0 مل (متوازن)", "0 mL (balanced)"),
         ("+400 مل", "+400 mL")),
        "D",
        ("inverts total intake and output differences",
         "considers intake only omitting all output values",
         "falsely assumes intake equals output without calculation"),
        "QUANTITATIVE_BALANCE", 1.05, "Computes intake minus output across multiple intake and loss routes.", 35,
    ),
    _q(
        "N05", NF, "ENTERAL_NUTRITION", "TUBE_PLACEMENT_VERIFICATION", "HARD",
        "ما هو الإجراء الأكثر موثوقية لتأكيد الموضع الصحيح لأنبوب التغذية الأنفي المعدي (NGT) قبل البدء بإعطاء التغذية لأول مرة؟",
        "What is the most definitive method to confirm correct placement of a nasogastric tube (NGT) prior to initial feeding?",
        (("حقن الهواء وسماع الصوت بالسماعة في الشرسوف", "Auscultating air bolus over epigastrium"),
         ("فحص التصوير بالأشعة السينية للصدر والبطن", "Radiographic X-ray confirmation"),
         ("غمر طرف الأنبوب في كوب ماء لمراقبة الفقاعات", "Aspirate tube tip bubbling in water"),
         ("سؤال المريض عما إذا كان يشعر بعدم ارتياح", "Asking patient for discomfort")),
        "B",
        ("auscultation is unreliable and cannot differentiate tracheal from gastric entry",
         "bubble test is outdated and risks aspiration if water is aspirated",
         "subjective patient feedback provides no anatomical verification"),
        "EVALUATE_BEST_EVIDENCE", 1.15, "Selects radiographic gold standard for tube placement verification.", 40,
    ),
    _q(
        "N06", NF, "CLINICAL_PRIORITIZATION", "TRIAGE_AIRWAY_PRIORITY", "HARD",
        "استلم الممرض أربعة مرضى، أي مريض يجب تقييمه أولاً وفقاً لقواعد أولوية الرعاية السريرية؟",
        "A nurse receives handoff for four patients; which patient must be assessed first based on clinical priority?",
        (("مريض بعد جراحة يطلب مسكن للألم بدرجة 6/10", "Post-op patient requesting pain medication (6/10)"),
         ("مريض سكري سكر الدم لديه صائم 140 ملغم/دسل", "Diabetic patient with fasting blood glucose 140 mg/dL"),
         ("مريض مصاب بالربو تدهور تنفسه وظهر لديه صرير حنجري (Stridor)", "Asthma patient with worsening stridor"),
         ("مريض جاهز للخروج وينتظر أوراق الخروج", "Patient ready for discharge awaiting paperwork")),
        "C",
        ("pain requires management but acute airway compromise takes precedence",
         "mild hyperglycemia is stable and secondary to acute airway risk",
         "discharge administrative tasks have lowest clinical urgency"),
        "ABC_PRIORITIZATION", 1.20, "Applies airway-breathing-circulation priority over stable or chronic findings.", 45,
    ),

    # --- DOMAIN 2: ANATOMY & PHYSIOLOGY FOUNDATIONS (6 questions: 2 EASY, 2 MEDIUM, 2 HARD) ---
    _q(
        "N07", AP, "CARDIOVASCULAR_SYSTEM", "CARDIAC_CONDUCTION", "EASY",
        "ما هو المنظم الطبيعي الأساسي لضربات القلب (Pacemaker) في الجهاز التوصيلي القلبي السليم؟",
        "What is the primary natural pacemaker of the heart in a normal cardiac conduction system?",
        (("العقدة الأذينية البطينية (AV Node)", "Atrioventricular (AV) node"),
         ("حزمة هس (Bundle of His)", "Bundle of His"),
         ("ألياف بيركنجي (Purkinje fibers)", "Purkinje fibers"),
         ("العقدة الجيبية الأذينية (SA Node)", "Sinoatrial (SA) node")),
        "D",
        ("AV node acts as secondary backup pacemaker at slower rate",
         "Bundle of His serves as conductory pathway not primary pacer",
         "Purkinje fibers are tertiary ventricular pacemakers of last resort"),
        "IDENTIFY_PACEMAKER", 0.90, "Identifies primary intrinsic pacemaker initiating cardiac action potentials.", 20,
    ),
    _q(
        "N08", AP, "HEMATOLOGY", "CELLULAR_TRANSPORT", "EASY",
        "ما هي الوظيفة الفسيولوجية الرئيسية لخلايا الدم الحمراء (Erythrocytes) في الدورة الدموية؟",
        "What is the primary physiological function of red blood cells (erythrocytes) in circulation?",
        (("إنتاج الأجسام المضادة لمكافحة العدوى", "Produce antibodies to fight infection"),
         ("نقل الأكسجين من الرئتين إلى أنسجة الجسم", "Transport oxygen from lungs to body tissues"),
         ("تكوين الخثرات الدموية لمنع النزيف", "Form blood clots to prevent bleeding"),
         ("تنظيم تركيز الجلوكوز في البلازما", "Regulate plasma glucose concentration")),
        "B",
        ("confuses erythrocytes with B-lymphocyte immune function",
         "confuses erythrocytes with platelets and clotting cascade",
         "confuses erythrocytes with pancreatic endocrine hormone action"),
        "RECALL_PHYSIOLOGICAL_ROLE", 0.90, "Recalls oxygen-carrying hemoglobin role of erythrocytes.", 20,
    ),
    _q(
        "N09", AP, "RENAL_PHYSIOLOGY", "ENDOCRINE_REGULATION", "MEDIUM",
        "لماذا يعاني مريض الفشل الكلوي المزمن من فقر دم مستمر؟ ما هو الهرمون الذي تنتجه الكلى ويحفز إنتاج خلايا الدم الحمراء؟",
        "Why do patients with chronic kidney failure develop persistent anemia? Which renal hormone stimulates red blood cell production?",
        (("الرينين (Renin)", "Renin"),
         ("الإريثروبويتين (Erythropoietin)", "Erythropoietin"),
         ("الألدوستيرون (Aldosterone)", "Aldosterone"),
         ("الكالسيتريول (Calcitriol)", "Calcitriol")),
        "B",
        ("renin regulates blood pressure through angiotensin pathway",
         "aldosterone is secreted by adrenal cortex regulating sodium",
         "calcitriol regulates calcium metabolism not bone marrow hematopoiesis"),
        "RELATE_ORGAN_PATHOLOGY", 1.05, "Links renal hormone deficiency with hematologic consequence.", 35,
    ),
    _q(
        "N10", AP, "RESPIRATORY_PHYSIOLOGY", "ALVEOLAR_DIFFUSION", "MEDIUM",
        "ما هي الآلية الفيزيائية الحيوية المسؤولة عن تبادل الغازات (O2 و CO2) عبر الغشاء السنخي الشعيري في الرئتين؟",
        "What biophysical mechanism is responsible for gas exchange (O2 and CO2) across the alveolar-capillary membrane?",
        (("النقل النشط المستهلك للطاقة", "Active transport consuming cellular energy"),
         ("التناضح الأسموزي للماء", "Osmotic movement across membrane"),
         ("الانتشار البسيط وفق تدرج الضغط الجزئي", "Simple diffusion along partial pressure gradient"),
         ("الترشيح الميكانيكي تحت الضغط الهيدروستاتيكي", "Hydrostatic mechanical filtration")),
        "C",
        ("gas exchange does not expend cellular ATP energy via pumps",
         "osmosis applies to water movement across semipermeable membranes",
         "hydrostatic filtration governs fluid movement in capillaries"),
        "EXPLAIN_TRANSPORT_MECHANISM", 1.0, "Applies partial-pressure passive diffusion principle to alveolar gas exchange.", 30,
    ),
    _q(
        "N11", AP, "ACID_BASE_PHYSIOLOGY", "ABG_INTERPRETATION", "HARD",
        "أظهرت نتائج غازات الدم الشرياني (ABG): pH = 7.28, PaCO2 = 56 mmHg, HCO3 = 24 mEq/L. ما هو التشخيص الفسيولوجي الدقيق لهذه الحالة؟",
        "ABG results show: pH = 7.28, PaCO2 = 56 mmHg, HCO3 = 24 mEq/L. What is the accurate acid-base interpretation?",
        (("حماض تنفسي غير معوض (Uncompensated respiratory acidosis)", "Uncompensated respiratory acidosis"),
         ("قلاء تنفسي معوض جزئياً", "Partially compensated respiratory alkalosis"),
         ("حماض استقلابي غير معوض", "Uncompensated metabolic acidosis"),
         ("غازات دم طبيعية ومتوازنة", "Normal balanced arterial blood gases")),
        "A",
        ("pH is acidotic below 7.35 and PaCO2 is elevated not alkalotic",
         "HCO3 is normal indicating metabolic system has not driven acidosis",
         "pH and PaCO2 are abnormal outside reference physiological ranges"),
        "ANALYZE_BLOOD_GASES", 1.20, "Interprets three-parameter ABG sequence to classify acid-base disturbance.", 50,
    ),
    _q(
        "N12", AP, "NEURO_CARDIO_PHYSIOLOGY", "AUTONOMIC_REGULATION", "HARD",
        "عند تنشيط الجهاز العصبي الودي (Sympathetic Nervous System)، ما هو التأثير الفسيولوجي المباشر على عضلة القلب والأوعية الدموية المحيطية؟",
        "When the sympathetic nervous system is stimulated, what is the direct physiological effect on the myocardium and peripheral vasculature?",
        (("انخفاض سرعة القلب وتوسع الأوعية المحيطية", "Decreased heart rate and peripheral vasodilation"),
         ("انخفاض ضغط الدم وتراجع النتاج القلبي", "Decreased blood pressure and cardiac output"),
         ("تثبيط إفراز الأدرينالين والنورأدرينالين", "Inhibition of adrenal catecholamine secretion"),
         ("زيادة سرعة وقوة انقباض القلب وتضيق الأوعية المحيطية", "Increased heart rate/contractility and peripheral vasoconstriction")),
        "D",
        ("describes parasympathetic cholinergic pathway effects",
         "sympathetic stimulation increases cardiac output and systemic vascular resistance",
         "sympathetic drive stimulates adrenal medullary catecholamine release"),
        "INTEGRATE_SYSTEMIC_RESPONSE", 1.15, "Integrates adrenergic receptor activation on heart and vascular smooth muscle.", 45,
    ),

    # --- DOMAIN 3: PHARMACOLOGY FOUNDATIONS (6 questions: 2 EASY, 2 MEDIUM, 2 HARD) ---
    _q(
        "N13", PH, "MEDICATION_SAFETY", "RIGHTS_OF_ADMINISTRATION", "EASY",
        "ما هي حقوق إعطاء الدواء الخمسة الأساسية (Five Rights) المعترف بها لضمان السلامة الدوائية؟",
        "What are the foundational 'Five Rights' of medication administration recognized to ensure medication safety?",
        (("المريض الصحيح، الدواء الصحيح، الجرعة الصحيحة، الطريق الصحيح، والوقت الصحيح",
          "Right patient, right drug, right dose, right route, right time"),
         ("السعر الصحيح، الشركة الصحيحة، الطبيب الصحيح، الجرعة، والوقت",
          "Right price, right company, right doctor, right dose, right time"),
         ("المريض الصحيح، الغرفة الصحيحة، السرير الصحيح، الصيدلي، والدواء",
          "Right patient, right room, right bed, right pharmacist, right drug"),
         ("الممرض الصحيح، المستشفى الصحيح، المريض، الدواء، والتاريخ",
          "Right nurse, right hospital, right patient, right drug, right date")),
        "A",
        ("includes administrative and purchasing factors unrelated to administration rights",
         "includes environmental room parameters rather than pharmacological administration rights",
         "substitutes hospital/nurse identities for clinical route and dosage rights"),
        "RECALL_SAFETY_PROTOCOL", 0.90, "Recalls core clinical verification rights before medication administration.", 20,
    ),
    _q(
        "N14", PH, "PHARMACOKINETICS", "ROUTES_OF_ADMINISTRATION", "EASY",
        "أي مسار من مسارات إعطاء الأدوية يوفر التوافر الحيوي الأسرع بنسبة 100% دون المرور بالاستقلاب الكبدي الأولي؟",
        "Which drug administration route provides the fastest 100% bioavailability bypassing first-pass hepatic metabolism?",
        (("الإعطاء عبر الفم (Oral - PO)", "Oral (PO) route"),
         ("الإعطاء عبر الوريد (Intravenous - IV)", "Intravenous (IV) route"),
         ("الإعطاء تحت الجلد (Subcutaneous - SC)", "Subcutaneous (SC) route"),
         ("الإعطاء عبر الجلد باللصقات (Transdermal)", "Transdermal patch route")),
        "B",
        ("oral route undergoes intestinal absorption and hepatic first-pass degradation",
         "subcutaneous absorption is slower due to adipose tissue blood flow",
         "transdermal route provides slow continuous systemic release over hours/days"),
        "COMPARE_BIOAVAILABILITY", 0.95, "Differentiates systemic routes by absorption speed and first-pass hepatic impact.", 25,
    ),
    _q(
        "N15", PH, "ENDOCRINE_PHARMACOLOGY", "HYPOGLYCEMIA_REVERSAL", "MEDIUM",
        "مريض سكري أخذ جرعته المعتادة من الإنسولين السريع ثم بدأ يعاني من تعرق بارد، رجفان، وشحوب. ما هو الإجراء التمريضي الفوري الأنسب إذا كان المريض واعياً وقادراً على البلع؟",
        "A diabetic patient took rapid-acting insulin and developed diaphoresis, tremors, and pallor. What is the immediate nursing action if the patient is conscious and able to swallow?",
        (("إعطاء جرعة إضافية من الإنسولين لخفض الجهد العصبي",
          "Administer an additional dose of insulin"),
         ("إبقاء المريض صائماً تماماً وانتظار الطبيب",
          "Keep patient NPO and wait for physician"),
         ("إعطاء 15 غراماً من الكربوهيدرات سريعة المفعول عن طريق الفم (كعصير فاكهة)",
          "Administer 15 g of fast-acting oral carbohydrates (e.g. fruit juice)"),
         ("وضع المريض في وضعية ترندلنبورغ ومتابعة العلامات الحيوية فقط",
          "Place in Trendelenburg and observe vital signs")),
        "C",
        ("giving insulin during hypoglycemia is fatal and causes severe neuroglycopenia",
         "delaying treatment in hypoglycemia risks hypoglycemic coma and seizure",
         "positioning alone does not restore blood glucose levels"),
        "APPLY_HYPOGLYCEMIA_RULE_OF_15", 1.05, "Applies Rule of 15 immediate oral glucose rescue for acute hypoglycemia.", 35,
    ),
    _q(
        "N16", PH, "DOSAGE_CALCULATION", "IV_DRIP_RATE", "MEDIUM",
        "مطلوب إعطاء 500 مل محلول ملحي وريدي على مدار 4 ساعات باستخدام جهاز تسريب بمعامل تنقيط 15 نقطة/مل. كم نقطة في الدقيقة يجب ضبط جهاز التسريب؟",
        "500 mL normal saline is ordered over 4 hours using a drip set with a drop factor of 15 gtt/mL. What is the required rate in drops per minute?",
        (("31 نقطة/دقيقة", "31 gtt/min"),
         ("62 نقطة/دقيقة", "62 gtt/min"),
         ("125 نقطة/دقيقة", "125 gtt/min"),
         ("15 نقطة/دقيقة", "15 gtt/min")),
        "A",
        ("doubles flow rate by failing to convert total hours to 240 minutes",
         "calculates total mL per hour omitting drop factor conversion",
         "uses drop factor as rate without factoring volume and infusion time"),
        "CALCULATE_FLOW_RATE", 1.10, "Solves (Volume in mL * Drop Factor) / (Time in minutes) to determine drip rate.", 45,
    ),
    _q(
        "N17", PH, "CARDIAC_PHARMACOLOGY", "DIGITALIS_SAFETY_MONITORING", "HARD",
        "قبل إعطاء دواء الديجوكسين (Digoxin) لمريض بالغ، ما هو التقييم التمريضي الحرج الذي يستوجب حجب الدواء وإبلاغ الطبيب فوراً؟",
        "Before administering digoxin to an adult patient, which critical nursing assessment requires withholding the medication and notifying the provider?",
        (("ضغط دم انقباضي 130 ملم زئبق", "Systolic blood pressure 130 mmHg"),
         ("درجة حرارة الجسم 37.1 درجة مئوية", "Body temperature 37.1 C"),
         ("سرعة تنفس 18 نفساً في الدقيقة", "Respiratory rate 18 breaths/min"),
         ("نبض القلب القمي أقل من 60 نبضة في الدقيقة", "Apical pulse less than 60 bpm")),
        "D",
        ("systolic pressure of 130 is normal and not a contraindication for digoxin",
         "temperature of 37.1 is afebrile and does not affect digitalis toxicity",
         "respiratory rate of 18 is within normal adult physiological limits"),
        "EVALUATE_SAFETY_THRESHOLD", 1.20, "Checks apical heart rate contraindication threshold before cardiac glycoside dose.", 45,
    ),
    _q(
        "N18", PH, "ANALGESIC_PHARMACOLOGY", "OPIOID_TOXICITY_REVERSAL", "HARD",
        "مريض يتلقى مسكن المورفين عبر الوريد، وُجد في حالة خمول شديد مع سرعة تنفس 7 أنفاس/دقيقة وبؤبؤ عين ضيق جداً (Pinpoint pupils). ما هو التقييم والتدخل التمريضي العاجل؟",
        "A patient receiving IV morphine becomes somnolent with a respiratory rate of 7 breaths/min and pinpoint pupils. What is the urgent assessment and intervention?",
        (("تشجيع المريض على شرب الماء وممارسة التنفس العميق",
          "Encourage water intake and deep breathing"),
         ("تمييز التسمم الأفيوني الحاد والاستعداد لإعطاء النالوكسون (Naloxone)",
          "Recognize acute opioid toxicity and prepare naloxone"),
         ("زيادة جرعة المسكن للسيطرة على الألم المسبب للخمول",
          "Increase opioid dose to control pain"),
         ("وضع كمادات باردة على الرأس وترك المريض ليرتاح",
          "Apply cold compresses and allow rest")),
        "B",
        ("somnolent patient with severe hypoventilation cannot drink safely and risks aspiration",
         "increasing opioid dosage during respiratory depression is catastrophic",
         "supportive cooling ignores life-threatening opioid-induced central respiratory arrest"),
        "MANAGE_PHARMACOLOGICAL_EMERGENCY", 1.25, "Recognizes triad of opioid toxicity and prepares opioid receptor antagonist.", 50,
    ),

    # --- DOMAIN 4: PATIENT SAFETY & INFECTION CONTROL (6 questions: 2 EASY, 2 MEDIUM, 2 HARD) ---
    _q(
        "N19", PS, "INFECTION_CONTROL", "HAND_HYGIENE", "EASY",
        "ما هو الإجراء الوحيد الأكثر فعالية وأهمية الذي يمارسه الكادر الصحي للحد من انتقال العدوى المكتسبة في المستشفيات؟",
        "What single action is the most effective measure practiced by healthcare personnel to reduce healthcare-associated infections (HAIs)?",
        (("ارتداء قفازين معاً طوال فترة المناوبة دون تغييرهما", "Double-gloving without changing gloves throughout shift"),
         ("إعطاء مضادات حيوية وقائية لجميع المرضى المنومين", "Routine prophylactic antibiotics for all admitted patients"),
         ("نظافة اليدين بانتظام وبالطريقة الصحيحة", "Consistent and correct hand hygiene"),
         ("تعقيم جدران الغرفة كل ساعة", "Hourly surface disinfection of hospital walls")),
        "C",
        ("reusing unwashed gloves causes cross-contamination between patients",
         "routine prophylactic antibiotics create antimicrobial resistance and toxicity",
         "surface wall disinfection does not prevent direct transmission via hands"),
        "IDENTIFY_PRIMARY_PREVENTION", 0.90, "Identifies hand hygiene as the primary cornerstone of infection control.", 20,
    ),
    _q(
        "N20", PS, "INFECTION_CONTROL", "STANDARD_PRECAUTIONS", "EASY",
        "متى يجب على الممرض تطبيق الاحتياطات القياسية (Standard Precautions) لمكافحة العدوى أثناء تقديم الرعاية التمريضية؟",
        "When must a nurse apply Standard Precautions for infection control during clinical care?",
        (("مع جميع المرضى في جميع الأوقات بغض النظر عن تشخيصهم", "With all patients at all times regardless of diagnosis"),
         ("فقط مع المرضى الذين تم تأكيد إصابتهم بفيروس نقص المناعة أو التهاب الكبد", "Only with confirmed HIV or hepatitis patients"),
         ("فقط في غرف العناية الحثيثة والعمليات الجراحية", "Only in ICU and surgical operating rooms"),
         ("عند التعامل مع المرضى المسنين فقط", "Only when caring for elderly patients")),
        "A",
        ("standard precautions apply universally not solely to confirmed bloodborne pathogens",
         "standard precautions are required in all clinical settings not just ICUs",
         "standard precautions apply to all age groups without demographic restriction"),
        "APPLY_UNIVERSAL_POLICY", 0.90, "Applies universal barrier and hygiene principles across all clinical contacts.", 20,
    ),
    _q(
        "N21", PS, "TRANSMISSION_BASED_PRECAUTIONS", "AIRBORNE_ISOLATION", "MEDIUM",
        "مريض مشتبه بإصابته بالسل الرئوي النشط (Pulmonary Tuberculosis). ما هو نوع جهاز حماية الجهاز التنفسي والبيئة الإلزامية لرعايته؟",
        "A patient is suspected of active pulmonary tuberculosis. What type of respiratory protection and environment is required?",
        (("كمامة جراحية ورقية عادية وغرفة مشتركة مع مرضى آخرين", "Standard surgical mask and semi-private shared room"),
         ("كمامة N95 وغرفة عزل ذات ضغط هوائي سلبي", "N95 respirator and negative-pressure airborne isolation room"),
         ("قناع أكسجين بوجه كامل وغرفة ذات ضغط إيجابي", "Full face oxygen mask and positive-pressure room"),
         ("ارتداء نظارات حماية فقط وفتح نوافذ الغرفة الخارجية", "Eye protection only and open external windows")),
        "B",
        ("surgical masks do not filter droplet nuclei and shared rooms spread airborne bacilli",
         "positive pressure rooms drive contaminated air into hospital corridors",
         "eye protection does not filter inhaled airborne mycobacteria"),
        "SELECT_APPROPRIATE_PPE", 1.05, "Selects particulate respirator and negative air pressure for airborne transmission.", 35,
    ),
    _q(
        "N22", PS, "OCCUPATIONAL_SAFETY", "SHARPS_DISPOSAL", "MEDIUM",
        "ما هو الإجراء الصحيح لمنع الإصابة بوخز الإبر بعد سحب عينة دم أو إعطاء حقنة عضلية؟",
        "What is the correct procedure to prevent needle-stick injury after drawing blood or administering an injection?",
        (("إعادة تغطية الإبرة باليدين معاً قبل رميها في سلة النفايات العادية",
          "Two-handed recapping before discarding in general trash"),
         ("فصل الإبرة عن الحقنة بالأصابع ثم رميها في كيس النفايات الأصفر",
          "Detach needle from syringe with fingers before bagging"),
         ("ثني الإبرة بمساعدة سطح الطاولة لضمان عدم إعادة استخدامها",
          "Bend needle against table edge to prevent reuse"),
         ("التخلص فوراً من الإبرة دون إعادة تغطيتها في حاوية الأدوات الحادة المقاومة للثقب",
          "Immediately dispose uncapped needle into puncture-resistant sharps container")),
        "D",
        ("two-handed recapping is a leading cause of accidental needle-stick punctures",
         "manipulating needles manually exposes bare fingers to contaminated sharp tips",
         "bending needles creates aerosolization and puncture risk"),
        "ADHERE_TO_SAFETY_STANDARD", 1.05, "Adheres to OSHA needle-stick safety prohibiting two-handed recapping.", 30,
    ),
    _q(
        "N23", PS, "ASEPTIC_TECHNIQUE", "STERILE_FIELD_INTEGRITY", "HARD",
        "أثناء تحضير الأدوات لتركيب قسطرة بولية معقمة، لمس طرف قفاز الممرض المعقم حافة السرير غير المعقمة. ما هو الإجراء السليم الواجب اتخاذه؟",
        "During sterile catheter preparation, the tip of the nurse's sterile glove touches the non-sterile bed rail. What is the immediate correct action?",
        (("التوقف فوراً، خلع القفازين، وإعادة ارتداء قفازات معقمة جديدة قبل متابعة الإجراء",
          "Stop immediately, remove gloves, and don new sterile gloves before proceeding"),
         ("مسح طرف القفاز بكحول طبي سريع ثم متابعة تركيب القسطرة",
          "Wipe glove tip with alcohol swab and continue"),
         ("إكمال الإجراء بحذر دون لمس القسطرة بنفس الإصبع الذي لمس السرير",
          "Continue carefully without touching catheter with contaminated finger"),
         ("تجاهل التلامس إذا لم يظهر أي اتساخ مرئي على القفاز",
          "Ignore contact if no visible dirt is present")),
        "A",
        ("alcohol does not re-sterilize contaminated gloves for invasive sterile procedures",
         "sterile field integrity is breached and cannot be compensated by partial finger positioning",
         "microbial contamination is invisible and presence of visible dirt is irrelevant"),
        "MANAGE_CONTAMINATION_BREACH", 1.15, "Recognizes sterile field breach and takes zero-tolerance corrective asepsis action.", 40,
    ),
    _q(
        "N24", PS, "FALL_PREVENTION", "FALL_RISK_PROTOCOL", "HARD",
        "مريض مسن يعاني من تشوش ذهني وتاريخ سقوط متكرر، ويأخذ أدوية مدرة للبول ومهدئة. ما هي الحزمة التدخلية التمريضية الأكثر شمولاً وأماناً للحد من خطر سقوطه؟",
        "An elderly patient with confusion and a history of falls takes diuretics and sedatives. What comprehensive nursing protocol best mitigates fall risk?",
        (("ربط المريض بالسرير بأربطة فيزيائية محكمة طوال الليل لمنعه من الحركة نهائياً",
          "Strict four-point physical restraints throughout night"),
         ("إبقاء جوانب السرير الأربعة مرفوعة وإطفاء جميع الأضواء لمساعدته على النوم",
          "Raise all four bedrails and extinguish all room lights"),
         ("وضع السرير بأدنى ارتفاع، تشغيل جهاز إنذار السرير، وضع جرس النداء بمتناول يده، وإضاءة ليلية كافية",
          "Bed in lowest position, bed alarm on, call bell in reach, adequate night lighting"),
         ("منع المريض من النهوض مطلقاً وحرمانه من السوائل ليلاً لتجنب الذهاب للحمام",
          "Total bed restriction and withhold nocturnal fluids")),
        "C",
        ("physical restraints increase agitation, injury severity, and ethical violations",
         "four raised side rails act as an illegal restraint and increase fall heights when climbing over",
         "fluid deprivation causes dehydration, orthostasis, and increased delirium"),
        "FORMULATE_SAFETY_PLAN", 1.20, "Selects multi-factorial non-restrictive fall prevention bundle.", 45,
    ),

    # --- DOMAIN 5: CLINICAL ASSESSMENT & REASONING (6 questions: 2 EASY, 2 MEDIUM, 2 HARD) ---
    _q(
        "N25", CA, "PHYSICAL_EXAMINATION", "ABDOMINAL_ASSESSMENT", "EASY",
        "ما هو الترتيب الصحيح لتقنيات الفحص السريري للبطن لتجنب تحفيز أو تغيير الأصوات المعوية؟",
        "What is the correct sequence of physical assessment techniques for the abdomen to avoid altering bowel sounds?",
        (("الجس، ثم القرع، ثم التسمع، ثم المعاينة", "Palpation, Percussion, Auscultation, Inspection"),
         ("المعاينة، ثم التسمع، ثم القرع، ثم الجس", "Inspection, Auscultation, Percussion, Palpation"),
         ("المعاينة، ثم الجس، ثم القرع، ثم التسمع", "Inspection, Palpation, Percussion, Auscultation"),
         ("التسمع، ثم المعاينة، ثم الجس، ثم القرع", "Auscultation, Inspection, Palpation, Percussion")),
        "B",
        ("palpation and percussion before auscultation stimulate false hyperactive bowel sounds",
         "palpating before auscultating distorts natural peristaltic acoustic patterns",
         "inspection must always precede auscultation to observe visible contours and distension"),
        "ORDER_ASSESSMENT_SEQUENCE", 0.90, "Orders inspection before auscultation before percussion and palpation.", 25,
    ),
    _q(
        "N26", CA, "NEUROLOGICAL_ASSESSMENT", "PUPILLARY_LIGHT_REFLEX", "EASY",
        "عند فحص استجابة حدقتي العين للضوء باستخدام المصباح اليدوي، ما هي الاستجابة الفسيولوجية الطبيعية المتوقعة؟",
        "When assessing pupil response to light with a penlight, what is the expected normal physiological reaction?",
        (("توسع الحدقتين معاً (Dilation)", "Bilateral pupillary dilation"),
         ("تضيق حدقة واحدة وبقاء الأخرى متسعة تماماً بشكل غير متطابق", "Unilateral constriction with persistent opposite dilation"),
         ("عدم حدوث أي تغيير في حجم الحدقة عند تسليط الضوء", "Fixed unreactive pupils without caliber change"),
         ("تضيق الحدقتين معاً بشكل متناظر وفوري (Constriction)", "Bilateral symmetrical brisk pupillary constriction")),
        "D",
        ("light stimulates pupillary constriction not sympathetic mydriatic dilation",
         "asymmetric pupillary response suggests neurological pathology",
         "unresponsive fixed pupils indicate cranial nerve or brainstem dysfunction"),
        "RECOGNIZE_NORMAL_REFLEX", 0.90, "Identifies normal direct and consensual pupillary light response.", 20,
    ),
    _q(
        "N27", CA, "VASCULAR_ASSESSMENT", "THROMBOSIS_RECOGNITION", "MEDIUM",
        "مريض بعد جراحة استبدال مفصل الركبة بيومين يشكو من ألم مستمر في ربلة الساق مع وجود دفء موضعي، تورم، واحمرار في طرف واحد. ما هو التقييم السريري الأكثر احتمالاً؟",
        "Two days after knee replacement, a patient reports unilateral calf pain with localized warmth, erythema, and edema. What is the most likely clinical concern?",
        (("خثار وريدي عميق (Deep Vein Thrombosis - DVT)", "Deep Vein Thrombosis (DVT)"),
         ("تمزق عضلي خفيف ناتج عن العلاج الطبيعي", "Mild muscle strain from physical therapy"),
         ("نقص تروية شرياني حاد في الأطراف السفلية", "Acute lower limb arterial occlusion"),
         ("التهاب مفاصل روماتويدي مزمن", "Chronic rheumatoid arthritis")),
        "A",
        ("unilateral warm erythema with edema after orthopedic surgery strongly indicates DVT over minor strain",
         "acute arterial occlusion presents with cold pallor, pulselessness, and numbness not warm erythema",
         "rheumatoid arthritis is systemic, symmetric, and chronic, not acute postoperative unilateral swelling"),
        "DIFFERENTIATE_VASCULAR_SIGNS", 1.05, "Differentiates postoperative venous thrombosis from arterial or musculoskeletal causes.", 35,
    ),
    _q(
        "N28", CA, "NEUROLOGICAL_ASSESSMENT", "GCS_SCORING", "MEDIUM",
        "مريض مصاب برضوض في الرأس يفتح عينيه عند مناداته بصوت عالٍ (3)، ويتحدث بكلمات مشوشة غير مترابطة (3)، ويسحب يده مبتعداً عند فحص الاستجابة للألم (4). ما هي درجة مقياس غلاسكو للغيبوبة (GCS)؟",
        "A head injury patient opens eyes to verbal command (3), utters confused words (3), and localizes/withdraws to pain (4). What is the patient's Glasgow Coma Scale (GCS) score?",
        (("7 من 15", "7 out of 15"),
         ("12 من 15", "12 out of 15"),
         ("10 من 15", "10 out of 15"),
         ("15 من 15 (طبيعي كامل)", "15 out of 15 (fully intact)")),
        "C",
        ("under-sums the eye, verbal, and motor component responses",
         "inflates the score beyond the component findings",
         "scores a fully alert and oriented patient"),
        "CALCULATE_COMA_SCALE", 1.10, "Sums Eye (3) + Verbal (3) + Motor (4) = 10 on the 15-point Glasgow scale.", 40,
    ),
    _q(
        "N29", CA, "HEMODYNAMIC_MONITORING", "SHOCK_RECOGNITION", "HARD",
        "مريض يعاني من نزيف باطني خفي بعد عملية جراحية. ما هي العلامة السريرية التمريضية المبكرة الأكثر دلالة على بدء مرحلة الصدمة النزفية التعويضية؟",
        "A postoperative patient develops occult internal bleeding. Which clinical sign is the earliest and most sensitive indicator of compensatory hypovolemic shock?",
        (("هبوط حاد في ضغط الدم الانقباضي لأقل من 70 ملم زئبق", "Profound systolic hypotension below 70 mmHg"),
         ("تسرع نبض القلب وتضيق الضغط النبضي مع قلق المريض", "Tachycardia and narrowed pulse pressure with restlessness"),
         ("فقدان كامل للوعي وتوقف إنتاج البول تماماً", "Complete unresponsiveness and anuria"),
         ("تباطؤ شديد في نبض القلب ودفء الجلد", "Bradycardia and warm dry skin")),
        "B",
        ("severe hypotension occurs in late decompensated shock when compensatory mechanisms fail",
         "unconsciousness and anuria represent late irreversible shock organ failure",
         "bradycardia and warm skin contradict sympathetic vasoconstrictive response"),
        "IDENTIFY_EARLY_DETERIORATION", 1.20, "Identifies compensatory tachycardia and narrowed pulse pressure before overt hypotension.", 45,
    ),
    _q(
        "N30", CA, "CLINICAL_REASONING", "ACUTE_CORONARY_SYNDROME_TRIAGE", "HARD",
        "حضر مريض لقسم الطوارئ يشكو من ألم ضاغط خلف عظم القص يمتد للفك السفلي والذراع الأيسر ومصحوب بغثيان وضيق تنفس. ما هو الاستدلال السريري والأولوية التمريضية الفورية؟",
        "A patient arrives with retrosternal crushing pressure radiating to the left jaw and arm, accompanied by diaphoresis and nausea. What is the clinical reasoning and immediate priority?",
        (("إعطاء مضاد حموضة عن طريق الفم للاشتباه بارتجاع مريئي معوي والانتظار",
          "Administer oral antacid for suspected gastroesophageal reflux and wait"),
         ("تدليك عضلات الصدر والكتف لاحتمال وجود إجهاد عضلي هيكلي",
          "Massage chest wall muscles for musculoskeletal strain"),
         ("طمأنة المريض بأنه قلق نفسي وإعطاؤه موعداً في العيادة الخارجية غداً",
          "Reassure as anxiety and schedule outpatient clinic visit"),
         ("الاشتباه بمتلازمة الشريان التاجي الحادة (ACS) وإجراء تخطيط قلب خلال 10 دقائق",
          "Suspect Acute Coronary Syndrome (ACS) and obtain 12-lead ECG within 10 minutes")),
        "D",
        ("treating crushing radiating pain as reflux delays urgent reperfusion therapy",
         "massaging chest wall ignores life-threatening acute myocardial ischemia",
         "dismissing typical anginal radiation as anxiety risks catastrophic cardiac arrest"),
        "EXECUTE_EMERGENCY_REASONING", 1.25, "Executes rapid triage protocol for acute myocardial ischemia within door-to-ECG window.", 50,
    ),
)

NURSING_QUESTIONS_BY_ID: Mapping[str, DiagnosticQuestion] = {
    q.question_id: q for q in NURSING_QUESTION_BANK
}


def _nursing_quality_flags(responses: Iterable[AnswerEvidence]) -> set[str]:
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
    for domain in NursingDiagnosticDomain:
        rows = [row for row in responses if NURSING_QUESTIONS_BY_ID[row.question_id].domain is domain]
        if rows:
            domain_accuracy.append(sum(row.is_correct for row in rows) / len(rows))
    if len(domain_accuracy) == 5 and max(domain_accuracy) - min(domain_accuracy) >= 0.85:
        flags.add("CONTRADICTORY_PERFORMANCE")
    transitions = sum(a.selected_option != b.selected_option for a, b in zip(responses, responses[1:]))
    accuracy = sum(row.is_correct for row in responses) / len(responses) if responses else 0
    if len(responses) >= 20 and transitions / (len(responses) - 1) > 0.9 and 0.3 <= accuracy <= 0.7:
        flags.add("RANDOM_LOOKING_PATTERN")
    return flags


def score_nursing_domain(
    domain: NursingDiagnosticDomain,
    responses: Iterable[AnswerEvidence],
) -> DiagnosticDomainResult:
    all_rows = tuple(responses)
    rows = tuple(row for row in all_rows if NURSING_QUESTIONS_BY_ID[row.question_id].domain is domain)
    possible = sum(
        DIFFICULTY_WEIGHT[NURSING_QUESTIONS_BY_ID[row.question_id].difficulty]
        * NURSING_QUESTIONS_BY_ID[row.question_id].evidence_weight
        for row in rows
    )
    earned = sum(
        DIFFICULTY_WEIGHT[NURSING_QUESTIONS_BY_ID[row.question_id].difficulty]
        * NURSING_QUESTIONS_BY_ID[row.question_id].evidence_weight
        for row in rows
        if row.is_correct
    )
    base = 50.0 if not possible else 100 * earned / possible
    fast_count = sum(
        row.response_time_ms
        < max(
            MIN_RESPONSE_TIME_MS,
            NURSING_QUESTIONS_BY_ID[row.question_id].estimated_time_seconds * 250,
        )
        for row in rows
    )
    timing_reliability = max(0.7, 1 - fast_count * 0.05)
    halves = (rows[:3], rows[3:])
    half_rates = [sum(row.is_correct for row in half) / len(half) for half in halves if half]
    consistency = 1.0 if len(half_rates) < 2 else max(0.75, 1 - abs(half_rates[0] - half_rates[1]) * 0.25)
    score = round(50 + (base - 50) * timing_reliability * consistency)
    flags = _nursing_quality_flags(all_rows)
    difficulty_coverage = {NURSING_QUESTIONS_BY_ID[row.question_id].difficulty for row in rows}
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


def select_next_nursing_question(responses: tuple[AnswerEvidence, ...]) -> DiagnosticQuestion | None:
    answered = {row.question_id for row in responses}
    return next((q for q in NURSING_QUESTION_BANK if q.question_id not in answered), None)
