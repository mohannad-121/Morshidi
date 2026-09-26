import Link from "next/link";
import {
  AdvisorIcon,
  CheckCircleIcon,
  DegreePathIcon,
  EligibilityIcon,
  MorshidiLogo,
  PlannerIcon,
  ProgressIcon,
  RecommendationsIcon,
  SparklesIcon,
} from "@/components/ui/Icons";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#FFFCF4] text-[#28241C]" dir="rtl">
      {/* 1. Premium Navbar */}
      <header className="sticky top-0 z-30 border-b border-[#EDE2C5] bg-[#FFFFFF]/90 backdrop-blur-md">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6 lg:px-8">
          <div className="flex items-center gap-3.5">
            <MorshidiLogo className="h-10 w-10 shrink-0" />
            <div>
              <span className="block text-xl font-bold tracking-tight text-[#28241C]">
                مرشدي
              </span>
              <span className="block text-[11px] font-medium text-[#726B5E]">
                نظام الذكاء الأكاديمي
              </span>
            </div>
          </div>

          <nav className="hidden items-center gap-8 text-xs font-semibold text-[#726B5E] md:flex">
            <a href="#capabilities" className="transition-colors hover:text-[#A66F00]">
              القدرات الأكاديمية
            </a>
            <a href="#how-it-works" className="transition-colors hover:text-[#A66F00]">
              كيف يعمل مرشدي
            </a>
            <a href="#governance" className="transition-colors hover:text-[#A66F00]">
              حوكمة القرارات
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="inline-flex min-h-11 items-center justify-center rounded-xl bg-[#A66F00] px-5 py-2 text-xs font-bold text-white shadow-sm transition-all hover:bg-[#805400] active:scale-95"
            >
              دخول الطالب
            </Link>
          </div>
        </div>
      </header>

      {/* 2. Hero Section */}
      <section className="relative overflow-hidden px-6 pt-16 pb-20 lg:px-8 lg:pt-24 lg:pb-28">
        <div className="mx-auto max-w-4xl text-center">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-[#EDE2C5] bg-[#FFF4C7] px-4 py-1.5 text-xs font-bold text-[#805400]">
            <SparklesIcon className="h-4 w-4 text-[#A66F00]" />
            <span>نظام الذكاء الأكاديمي الجامعي الأول</span>
          </div>

          <h1 className="mt-8 text-3xl font-extrabold tracking-tight text-[#28241C] sm:text-5xl lg:text-6xl leading-[1.25]">
            قرارات أكاديمية أوضح، تخطيط أذكى،
            <span className="block text-[#A66F00] mt-2">ومسار دراسي يمكنك فهمه.</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-sm leading-relaxed text-[#726B5E] sm:text-base">
            منصة جامعية متقدمة تدمج دقة القواعد الأكاديمية واللوائح المعتمدة مع الذكاء الاصطناعي الشارح، لمساعدة الطلاب على اتخاذ قرارات دراسية دقيقة وموثوقة.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/login"
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#A66F00] px-8 py-3 text-sm font-bold text-white shadow-md transition-all hover:bg-[#805400] active:scale-95"
            >
              <span>دخول الطالب</span>
              <span dir="ltr">←</span>
            </Link>
            <a
              href="#capabilities"
              className="inline-flex min-h-12 items-center justify-center rounded-xl border border-[#EDE2C5] bg-white px-7 py-3 text-sm font-semibold text-[#28241C] shadow-sm transition-all hover:bg-[#FFF9E8] active:scale-95"
            >
              تعرف على المنصة
            </a>
          </div>

          <div className="mt-12 flex items-center justify-center gap-6 text-xs text-[#726B5E]">
            <span className="flex items-center gap-1.5">
              <CheckCircleIcon className="h-4 w-4 text-[#A66F00]" />
              قواعد أكاديمية حتمية
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircleIcon className="h-4 w-4 text-[#A66F00]" />
              تفسيرات معللة بالكامل
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircleIcon className="h-4 w-4 text-[#A66F00]" />
              أمان وعزل بيانات الطالب
            </span>
          </div>
        </div>
      </section>

      {/* 3. Academic Intelligence Preview */}
      <section id="capabilities" className="border-t border-[#EDE2C5] bg-white py-20 px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="text-center">
            <span className="text-xs font-bold text-[#A66F00]">قدرات ذكية متكاملة</span>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-[#28241C] sm:text-3xl">
              بوابة أكاديمية شاملة تدير مسيرتك الجامعية
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-xs leading-relaxed text-[#726B5E] sm:text-sm">
              محركات متخصصة تعمل معاً وفق خطتك الدراسية لتقديم رؤية واضحة ومسار موثق خطوة بخطوة.
            </p>
          </div>

          <div className="mt-14 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {/* Card 1 */}
            <div className="rounded-3xl border border-[#EDE2C5] bg-[#FFFCF4] p-7 transition-all hover:border-[#E2AD27] hover:shadow-sm">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
                <ProgressIcon className="h-6 w-6" />
              </div>
              <h3 className="mt-5 text-base font-bold text-[#28241C]">متابعة التقدم الأكاديمي</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                احتساب فوري للساعات المنجزة والمتبقية ومستوى استيفاء كل مجموعة متطلبات بدقة حتمية استناداً إلى الخطة.
              </p>
            </div>

            {/* Card 2 */}
            <div className="rounded-3xl border border-[#EDE2C5] bg-[#FFFCF4] p-7 transition-all hover:border-[#E2AD27] hover:shadow-sm">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
                <EligibilityIcon className="h-6 w-6" />
              </div>
              <h3 className="mt-5 text-base font-bold text-[#28241C]">فحص أهلية المواد</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                تقييم فوري وصارم لمتطلبات التسجيل السابقة والمتزامنة، مع توضيح أسباب الأهلية أو عدم الاستيفاء لكل مقرر.
              </p>
            </div>

            {/* Card 3 */}
            <div className="rounded-3xl border border-[#EDE2C5] bg-[#FFFCF4] p-7 transition-all hover:border-[#E2AD27] hover:shadow-sm">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
                <PlannerIcon className="h-6 w-6" />
              </div>
              <h3 className="mt-5 text-base font-bold text-[#28241C]">تخطيط الفصل الدراسي</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                اقتراح باقات مواد متوازنة تتوافق مع العبء الدراسي المسموح وساعات الخطة، لتقليل التعثر وضمان استمرارية التدرج.
              </p>
            </div>

            {/* Card 4 */}
            <div className="rounded-3xl border border-[#EDE2C5] bg-[#FFFCF4] p-7 transition-all hover:border-[#E2AD27] hover:shadow-sm">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
                <DegreePathIcon className="h-6 w-6" />
              </div>
              <h3 className="mt-5 text-base font-bold text-[#28241C]">المسار الدراسي متعدد الفصول</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                محاكاة للمسار الأكاديمي حتى التخرج، توضح تسلسل المواد المتوقعة فصلاً بفصل مع كشف المعوقات مبكراً.
              </p>
            </div>

            {/* Card 5 */}
            <div className="rounded-3xl border border-[#EDE2C5] bg-[#FFFCF4] p-7 transition-all hover:border-[#E2AD27] hover:shadow-sm">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
                <RecommendationsIcon className="h-6 w-6" />
              </div>
              <h3 className="mt-5 text-base font-bold text-[#28241C]">التوصيات الأكاديمية المصنفة</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                ترتيب ذكي للمواد المرشحة حسب أثرها في فتح مواد مستقبلية، واستيفاء المجموعات الإجبارية، ومستوى الأولوية.
              </p>
            </div>

            {/* Card 6 */}
            <div className="rounded-3xl border border-[#EDE2C5] bg-[#FFFCF4] p-7 transition-all hover:border-[#E2AD27] hover:shadow-sm">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
                <AdvisorIcon className="h-6 w-6" />
              </div>
              <h3 className="mt-5 text-base font-bold text-[#28241C]">المرشد الأكاديمي الذكي</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                مساعد حواري يجيب على استفساراتك الأكاديمية باللغة العربية، موثقاً كل إجابة بمصادر النظام ولوائح الجامعة.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 4. How It Works */}
      <section id="how-it-works" className="py-20 px-6 lg:px-8 bg-[#FFF9E8]/60 border-t border-[#EDE2C5]">
        <div className="mx-auto max-w-5xl">
          <div className="text-center">
            <span className="text-xs font-bold text-[#A66F00]">آلية العمل</span>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-[#28241C] sm:text-3xl">
              كيف يعمل مرشدي في 3 خطوات؟
            </h2>
          </div>

          <div className="mt-14 grid grid-cols-1 gap-8 md:grid-cols-3">
            <div className="relative rounded-3xl border border-[#EDE2C5] bg-white p-7 text-center shadow-xs">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#FFF4C7] font-mono text-sm font-bold text-[#A66F00]">
                1
              </span>
              <h3 className="mt-4 text-sm font-bold text-[#28241C]">استرجاع سجل الطالب</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                يتم قراءة بيانات الطالب وسجل المحاولات الأكاديمية والربط مع الخطة المعتمدة في بيئة آمنة.
              </p>
            </div>

            <div className="relative rounded-3xl border border-[#EDE2C5] bg-white p-7 text-center shadow-xs">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#FFF4C7] font-mono text-sm font-bold text-[#A66F00]">
                2
              </span>
              <h3 className="mt-4 text-sm font-bold text-[#28241C]">تطبيق المحركات الحتمية</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                تُفحص الشروط الأكاديمية عبر محركات قواعد حتمية لا مجال فيها للتخمين أو التوليد غير المنضبط.
              </p>
            </div>

            <div className="relative rounded-3xl border border-[#EDE2C5] bg-white p-7 text-center shadow-xs">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#FFF4C7] font-mono text-sm font-bold text-[#A66F00]">
                3
              </span>
              <h3 className="mt-4 text-sm font-bold text-[#28241C]">الشرح والتوجيه المعُلل</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                يقوم الذكاء الاصطناعي بصياغة الشرح الأكاديمي الواضح مستنداً بشكل حصري إلى نتائج المحرك الحتمي.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Trust / Explainability */}
      <section id="governance" className="border-t border-[#EDE2C5] bg-white py-20 px-6 lg:px-8">
        <div className="mx-auto max-w-4xl rounded-3xl border border-[#EDE2C5] bg-gradient-to-b from-[#FFF4C7]/50 via-[#FFF9E8] to-[#FFFFFF] p-8 text-center sm:p-14 shadow-xs">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
            <SparklesIcon className="h-7 w-7" />
          </div>

          <h2 className="mt-6 text-xl font-extrabold text-[#28241C] sm:text-3xl">
            الذكاء الاصطناعي يشرح، والقواعد الأكاديمية الموثقة تقرر.
          </h2>

          <p className="mx-auto mt-4 max-w-2xl text-xs leading-relaxed text-[#726B5E] sm:text-sm">
            في مرشدي، لا يُترك أي قرار دراسي لتوقعات نموذج لغوي حر. يُعتمد الفصل التام بين محركات القواعد الصارمة التي تقرر الأهلية والتقدم، وبين قدرات الذكاء الاصطناعي المكرسة للشرح والإرشاد اللغوي السليم.
          </p>

          <div className="mt-8 flex justify-center">
            <Link
              href="/login"
              className="inline-flex min-h-11 items-center justify-center rounded-xl bg-[#A66F00] px-7 py-2.5 text-xs font-bold text-white shadow-xs transition-colors hover:bg-[#805400]"
            >
              ابدأ الآن — تسجيل الدخول
            </Link>
          </div>
        </div>
      </section>

      {/* 6. Footer */}
      <footer className="border-t border-[#EDE2C5] bg-[#FFFCF4] py-10 px-6 text-center text-xs text-[#726B5E]">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2">
            <MorshidiLogo className="h-6 w-6" />
            <span className="font-bold text-[#28241C]">مرشدي</span>
            <span>— نظام الذكاء الأكاديمي</span>
          </div>

          <p className="text-[11px]">
            جميع الحقوق محفوظة © {new Date().getFullYear()} مرشدي. منصة أكاديمية مستقلة ومحمية.
          </p>

          <div className="flex items-center gap-4 text-[11px]">
            <Link href="/login" className="hover:text-[#A66F00]">بوابة الطالب</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
