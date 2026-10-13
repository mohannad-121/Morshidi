"use client";

import Link from "next/link";
import {
  ArrowLeft, BookOpenCheck, Check, ChevronDown, CircleGauge, Compass,
  Fingerprint, GitBranch, GraduationCap, LockKeyhole, Route, ScanSearch,
  Sparkles, Target,
} from "lucide-react";
import { useAuth } from "@/auth/auth-provider";
import { getStudentDisplayName } from "@/lib/student-identity";
import styles from "./home.module.css";

const capabilities = [
  { icon: ScanSearch, eyebrow: "وضوح فوري", title: "افهم ما أنجزته فعلاً", description: "قراءة منظّمة لسجلك الأكاديمي تكشف المنجز والمتبقي، بلا جداول مربكة أو حسابات يدوية." },
  { icon: GitBranch, eyebrow: "أهلية دقيقة", title: "اعرف ماذا يمكنك تسجيله", description: "تُفحص المتطلبات السابقة والمتزامنة وفق قواعد خطتك، فتظهر لك الخيارات المتاحة وسبب كل نتيجة." },
  { icon: Route, eyebrow: "تخطيط واعٍ", title: "ابنِ فصلك بثقة", description: "وازن العبء الدراسي وتقدّمك نحو التخرج قبل أن يصبح القرار موعداً نهائياً في التقويم." },
];

const features = [
  ["01", "تحليل التقدّم", "صورة حيّة لمسارك: الساعات المكتسبة، المتبقية، وموقعك من متطلبات الخطة."],
  ["02", "فحص الأهلية", "قرار حتمي لكل مادة، يستند إلى سجلّك وقواعد جامعتك المعتمدة."],
  ["03", "بناء السيناريوهات", "اختبر أكثر من فصل محتمل وافهم أثره قبل تثبيت أي قرار."],
  ["04", "تفسير موثّق", "إجابة واضحة باللغة العربية، مرتبطة بالمادة والشرط والمصدر الذي بُنيت عليه."],
] as const;

const journey = [
  ["01", "اربط سجلك", "نبدأ من بياناتك الأكاديمية الفعلية، لا من افتراضات عامة."],
  ["02", "نقرأ القواعد", "يطبّق المحرك خطة تخصصك ومتطلباتها كما هي معتمدة."],
  ["03", "استكشف الخيارات", "شاهد المتاح، المقفل، وما يلزمك لفتح الخطوة التالية."],
  ["04", "تحرّك بيقين", "ابنِ قرارك ومعك تفسير واضح ومسار يمكن تتبعه."],
] as const;

function AcademicCore() {
  return (
    <figure className={styles.coreFigure} aria-label="تصور لمسار أكاديمي تحلله منظومة مرشدي">
      <div className={styles.coreGlow} aria-hidden="true" />
      <div className={styles.corePlane} aria-hidden="true" />
      <svg className={styles.routeMap} viewBox="0 0 640 640" aria-hidden="true">
        <defs><linearGradient id="routeGold" x1="0" x2="1"><stop offset="0" stopColor="#75611e" stopOpacity="0" /><stop offset=".5" stopColor="#f2d778" stopOpacity=".9" /><stop offset="1" stopColor="#75611e" stopOpacity="0" /></linearGradient></defs>
        <path className={styles.routePath} d="M56 424C164 424 138 220 280 248S438 446 586 296" />
        <path className={styles.routePathSoft} d="M76 502C220 528 272 404 314 340S434 128 574 160" />
      </svg>
      <div className={`${styles.orbit} ${styles.orbitOuter}`} aria-hidden="true">
        <span className={`${styles.orbitNode} ${styles.nodeTop}`}><i /> التخرج</span>
        <span className={`${styles.orbitNode} ${styles.nodeBottom}`}><i /> التقدّم</span>
      </div>
      <div className={`${styles.orbit} ${styles.orbitInner}`} aria-hidden="true">
        <span className={`${styles.orbitNode} ${styles.nodeRight}`}><i /> الأهلية</span>
        <span className={`${styles.orbitNode} ${styles.nodeLeft}`}><i /> الخطة</span>
      </div>
      <div className={styles.coreShell} aria-hidden="true">
        <div className={styles.coreHalo} />
        <div className={styles.coreMark}><Compass strokeWidth={1.25} /></div>
        <span>المسار الأكاديمي</span><strong>محسوب الآن</strong>
      </div>
      <div className={styles.coreReadout} aria-hidden="true">
        <span className={styles.liveDot} />
        <div><small>محرك القواعد</small><strong>متصل بخطتك</strong></div>
        <span className={styles.readoutCode}>M / 01</span>
      </div>
    </figure>
  );
}

export default function Home() {
  const auth = useAuth();
  const displayName = getStudentDisplayName(auth.user);
  const primaryHref = auth.isAuthenticated ? "/student" : "/login";
  const primaryLabel = auth.isAuthenticated ? "افتح مركزك الأكاديمي" : "ابدأ من سجلك الجامعي";

  return (
    <main className={styles.page}>
      <section className={styles.hero} aria-labelledby="hero-title">
        <div className={styles.heroAtmosphere} aria-hidden="true" />
        <div className={styles.container}>
          <div className={styles.heroGrid}>
            <div className={styles.heroCopy}>
              <p className={styles.eyebrow}><span /> ذكاء أكاديمي مبني على اليقين</p>
              {auth.isAuthenticated && <p className={styles.welcome}>مرحباً بعودتك، {displayName}</p>}
              <h1 id="hero-title">اعرف طريقك الأكاديمي.<em>قبل أن تخطو الخطوة التالية.</em></h1>
              <p className={styles.heroLead}>مرشدي يحوّل سجلك وخطتك ولوائح جامعتك إلى قرارات واضحة، حتى تعرف أين أنت، وما المتاح لك، وكيف تصل إلى التخرج بثقة.</p>
              <div className={styles.heroActions}>
                <Link className={styles.primaryButton} href={primaryHref}><span>{primaryLabel}</span><ArrowLeft aria-hidden="true" /></Link>
                <Link className={styles.textLink} href="#insights">شاهد كيف يرى مرشدي مسارك <span aria-hidden="true">↙</span></Link>
              </div>
              <ul className={styles.trustLine} aria-label="مزايا أساسية">
                <li><Check aria-hidden="true" /> قرار واضح</li><li><Fingerprint aria-hidden="true" /> دليل قابل للتتبع</li><li><Target aria-hidden="true" /> خطة نحو التخرج</li>
              </ul>
            </div>
            <AcademicCore />
          </div>
          <a className={styles.scrollCue} href="#about" aria-label="انتقل إلى المحتوى التالي"><span>اكتشف المنظومة</span><ChevronDown aria-hidden="true" /></a>
        </div>
      </section>

      <section id="about" className={`${styles.section} ${styles.manifesto}`}>
        <div className={styles.container}>
          <div className={styles.sectionIndex} data-reveal><span>01</span><i /> ماهو مرشدي؟</div>
          <div className={styles.manifestoGrid}>
            <div data-reveal><p className={styles.kicker}>منصة قرار، لا مجرد شاشة معلومات</p><h2>طبقة ذكاء بينك وبين تعقيد خطتك الدراسية.</h2></div>
            <div className={styles.manifestoCopy} data-reveal>
              <p>صُمّم مرشدي ليجمع ما يتفرّق عادة بين السجل الأكاديمي، والخطة، والمتطلبات السابقة، واللوائح؛ ثم يعيد تقديمه كسياق واحد مفهوم.</p>
              <p>النتيجة ليست إجابة عامة، بل رؤية شخصية لمسارك أنت — قابلة للفهم، والمراجعة، والبناء عليها.</p>
              <div className={styles.signalRow}>
                <span><strong>سجلّك</strong><small>مصدر الحقيقة</small></span><i aria-hidden="true" /><span><strong>قواعد جامعتك</strong><small>منطق القرار</small></span><i aria-hidden="true" /><span><strong>خطوتك التالية</strong><small>نتيجة واضحة</small></span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className={`${styles.section} ${styles.helpSection}`}>
        <div className={styles.container}>
          <div className={styles.sectionIndex} data-reveal><span>02</span><i /> كيف يساعدك؟</div>
          <div className={styles.sectionHeading} data-reveal><p className={styles.kicker}>من الضبابية إلى قرار يمكن الدفاع عنه</p><h2>كل سؤال كبير، نفكّكه إلى خطوة واضحة.</h2></div>
          <div className={styles.capabilityRail}>
            {capabilities.map(({ icon: Icon, eyebrow, title, description }, index) => (
              <article className={styles.capability} data-reveal key={title}>
                <div className={styles.capabilityTop}><span className={styles.capabilityNumber}>0{index + 1}</span><Icon aria-hidden="true" /></div>
                <small>{eyebrow}</small><h3>{title}</h3><p>{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className={`${styles.section} ${styles.intelligenceSection}`}>
        <div className={styles.container}>
          <div className={styles.sectionIndex} data-reveal><span>03</span><i /> جوهر الذكاء</div>
          <div className={styles.intelligenceGrid}>
            <div className={styles.intelligenceIntro} data-reveal>
              <p className={styles.kicker}>أربع قدرات. رؤية أكاديمية واحدة.</p><h2>لا يعرض مرشدي البيانات فقط. بل يكشف العلاقة بينها.</h2>
              <div className={styles.intelligenceGlyph} aria-hidden="true"><span><CircleGauge /></span><i /><i /><i /></div>
            </div>
            <div className={styles.featureList}>
              {features.map(([number, title, description]) => (
                <article className={styles.featureRow} data-reveal key={number}><span>{number}</span><div><h3>{title}</h3><p>{description}</p></div><ArrowLeft aria-hidden="true" /></article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="the-path" className={`${styles.section} ${styles.journeySection}`}>
        <div className={styles.container}>
          <div className={styles.sectionIndex} data-reveal><span>04</span><i /> رحلة الطالب</div>
          <div className={styles.journeyHeading} data-reveal><p className={styles.kicker}>من أول تسجيل دخول إلى قرار الفصل</p><h2>مسار واحد متصل. بلا قفزات غامضة.</h2></div>
          <ol className={styles.journeyTrack}>
            {journey.map(([number, title, description]) => (
              <li data-reveal key={number}><span className={styles.journeyNumber}>{number}</span><div className={styles.journeyDot} aria-hidden="true" /><h3>{title}</h3><p>{description}</p></li>
            ))}
          </ol>
        </div>
      </section>

      <section id="the-plan" className={`${styles.section} ${styles.trustSection}`}>
        <div className={styles.container}>
          <div className={styles.trustPanel}>
            <div className={styles.trustCopy} data-reveal>
              <p className={styles.kicker}>هندسة ثقة من البداية</p><h2>الذكاء الاصطناعي يشرح. القواعد الأكاديمية تقرّر.</h2>
              <p>لأن مستقبلك الدراسي لا يحتمل التخمين، يفصل مرشدي بين التفسير الذكي وبين القرار الأكاديمي. الأهلية، والمتطلبات، والتقدّم تُحسم بمحرك قواعد حتمي؛ ثم تُشرح لك بلغة واضحة.</p>
              <ul><li><Check aria-hidden="true" /> كل نتيجة مرتبطة بسبب قابل للمراجعة</li><li><Check aria-hidden="true" /> لا استبدال لسياسات الجامعة أو المرشد الأكاديمي</li><li><Check aria-hidden="true" /> سجلك الرسمي يظل المرجع النهائي</li></ul>
            </div>
            <div className={styles.trustMachine} data-reveal aria-label="تدفق القرار في مرشدي">
              <div className={styles.machineHeader}><LockKeyhole aria-hidden="true" /><span>مسار القرار الموثّق</span><small>DETERMINISTIC</small></div>
              <div className={styles.machineFlow}>
                <div><BookOpenCheck aria-hidden="true" /><span>السجل والخطة</span><small>مدخلات معتمدة</small></div><i aria-hidden="true" /><div className={styles.machineCore}><CircleGauge aria-hidden="true" /><span>محرك القواعد</span><small>فحص حتمي</small></div><i aria-hidden="true" /><div><Sparkles aria-hidden="true" /><span>شرح مفهوم</span><small>بلغة الطالب</small></div>
              </div>
              <div className={styles.machineStamp}><span>نتيجة قابلة للتتبع</span><strong>موثّقة ✓</strong></div>
            </div>
          </div>
        </div>
      </section>

      <section id="insights" className={`${styles.section} ${styles.insightsSection}`}>
        <div className={styles.container}>
          <div className={styles.sectionIndex} data-reveal><span>05</span><i /> رؤيتك الشخصية</div>
          <div className={styles.insightsGrid}>
            <div className={styles.insightsCopy} data-reveal>
              <p className={styles.kicker}>ما الذي يحتاج انتباهك الآن؟</p><h2>رؤية تختصر عليك أسابيع من الأسئلة.</h2><p>بدلاً من تصفّح الخطة مادةً مادة، تحصل على قراءة مركّزة لما تغيّر، وما أصبح متاحاً، وأي قرار يستحق أن تبدأ به.</p>
              <Link className={styles.inlineLink} href={primaryHref}>اكتشف رؤيتك الأكاديمية <ArrowLeft aria-hidden="true" /></Link>
            </div>
            <div className={styles.insightConsole} data-reveal aria-label="مثال توضيحي لرؤية أكاديمية شخصية">
              <div className={styles.consoleTop}><span><i /> قراءة محدثة</span><small>مثال توضيحي</small></div>
              <div className={styles.progressInstrument}><div className={styles.progressRing}><span><strong>68%</strong><small>من الخطة</small></span></div><div className={styles.progressNarrative}><small>أقرب إنجاز مؤثر</small><strong>إكمال متطلب التخصص الإجباري</strong><p>3 مواد تفصلك عن فتح مشروع التخرج.</p></div></div>
              <div className={styles.consoleSignals}><span><b>04</b><small>مواد متاحة الآن</small></span><span><b>02</b><small>قرارات تحتاج مراجعة</small></span><span><b>21</b><small>ساعة متبقية</small></span></div>
              <div className={styles.consoleInsight}><Sparkles aria-hidden="true" /><p><strong>الخطوة المقترحة:</strong> راجع مادة «تحليل الخوارزميات»؛ اجتيازها يفتح مسارين في الفصل التالي.</p></div>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.finalCta}>
        <div className={styles.finalGlow} aria-hidden="true" />
        <div className={styles.container}><div className={styles.finalInner} data-reveal>
          <div className={styles.finalMark}><GraduationCap aria-hidden="true" /></div><p className={styles.kicker}>الوضوح يبدأ من سجلك</p><h2>خطتك ليست مجرد مواد.<br />إنها الطريق إلى ما بعد الجامعة.</h2><p>دع مرشدي يريك الطريق كاملاً، ويشرح لك كل خطوة فيه.</p>
          <Link className={styles.primaryButton} href={primaryHref}><span>{primaryLabel}</span><ArrowLeft aria-hidden="true" /></Link>
        </div></div>
      </section>
    </main>
  );
}
