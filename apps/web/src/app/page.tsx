"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import { useAuth } from "@/auth/auth-provider";
import {
  AdvisorIcon,
  DegreePathIcon,
  EligibilityIcon,
  PlannerIcon,
  ProgressIcon,
  SparklesIcon,
  MockRegistrationIcon,
} from "@/components/ui/Icons";

interface DemoTrack {
  id: string;
  name: string;
  courseCompleted: { code: string; name: string; grade: string; state: "منجزة بنجاح" };
  courseEligible: { code: string; name: string; credits: number; state: "مؤهل للتسجيل الآن" };
  courseLocked: { code: string; name: string; missing: string; state: "غير متاحة حالياً" };
  explanation: string;
}

const DEMO_TRACKS: DemoTrack[] = [
  {
    id: "ai",
    name: "مسار الذكاء الاصطناعي والخوارزميات",
    courseCompleted: { code: "CS-101", name: "مقدمة في البرمجة", grade: "A", state: "منجزة بنجاح" },
    courseEligible: { code: "CS-201", name: "تراكيب البيانات والخوارزميات", credits: 3, state: "مؤهل للتسجيل الآن" },
    courseLocked: { code: "CS-401", name: "تعلم الآلة والذكاء الاصطناعي", missing: "يتطلب اجتياز CS-201 أولاً", state: "غير متاحة حالياً" },
    explanation: "قررت القواعد الحتمية أهلية CS-201 لاجتياز المتطلب السابق (CS-101)، بينما قُفلت CS-401 حتى استيفاء تراكيب البيانات بنجاح.",
  },
  {
    id: "data",
    name: "مسار قواعد البيانات وهندسة النظم",
    courseCompleted: { code: "CS-105", name: "أساسيات نظم المعلومات", grade: "B+", state: "منجزة بنجاح" },
    courseEligible: { code: "CS-220", name: "إدارة قواعد البيانات ونمذجتها", credits: 3, state: "مؤهل للتسجيل الآن" },
    courseLocked: { code: "CS-350", name: "الأنظمة الموزعة والسحابية", missing: "يتطلب اجتياز CS-220 أولاً", state: "غير متاحة حالياً" },
    explanation: "المادة CS-220 متاحة لأن متطلبها الأساسي مستوفى، ولا يمكن الانتقال للأنظمة السحابية قبل تسجيل واجتياز قواعد البيانات.",
  },
  {
    id: "security",
    name: "مسار الأمن السيبراني والشبكات",
    courseCompleted: { code: "CS-110", name: "مبادئ شبكات الحاسب", grade: "A-", state: "منجزة بنجاح" },
    courseEligible: { code: "CS-230", name: "أمن الشبكات والبروتوكولات", credits: 3, state: "مؤهل للتسجيل الآن" },
    courseLocked: { code: "CS-440", name: "التحليل الجنائي الرقمي واختبار الاختراق", missing: "يتطلب اجتياز CS-230 أولاً", state: "غير متاحة حالياً" },
    explanation: "استوفيت متطلب شبكات الحاسب ففتحت لك مادة أمن الشبكات، وتبقى مادة الاختبار الجنائي مقفلة نظامياً حتى إتمام متطلبها.",
  },
];

export default function Home() {
  const auth = useAuth();
  const [activeTrack, setActiveTrack] = useState<DemoTrack>(DEMO_TRACKS[0]);

  return (
    <div className="space-y-20 pb-20">
      {/* 1. Hero Section with 3D Mascot */}
      <section className="relative overflow-hidden border-b border-[#EDE2C5]/60 bg-gradient-to-b from-[#FFF9E8]/70 via-[#FFFCF4] to-[#FFFCF4] pt-12 pb-20 sm:pt-16 sm:pb-28">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8" dir="rtl">
          {/* Personalized banner if logged in */}
          {auth.isAuthenticated && (
            <div className="mb-8 rounded-2xl border border-[#EDE2C5] bg-[#FFF4C7]/70 p-4 shadow-xs">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#A66F00] text-white">
                    <SparklesIcon className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-[#28241C]">
                      مرحباً بك مجدداً،{" "}
                      <span className="font-mono text-[#805400]" dir="ltr">
                        {auth.user?.email}
                      </span>
                    </h2>
                    <p className="text-xs text-[#726B5E]">
                      أدواتك الأكاديمية جاهزة ومحدثة وفق سجلك الفعلي في النظام.
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    href="/student"
                    className="inline-flex items-center gap-1.5 rounded-xl bg-[#A66F00] px-4 py-2 text-xs font-bold text-white shadow-2xs hover:bg-[#805400] transition-colors"
                  >
                    <span>افتح حسابي الأكاديمي</span>
                    <span>←</span>
                  </Link>
                  <Link
                    href="/student/planner"
                    className="inline-flex items-center gap-1.5 rounded-xl border border-[#EDE2C5] bg-white px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] transition-colors"
                  >
                    <span>خطط لفصلك</span>
                  </Link>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12 lg:gap-8">
            {/* Right Column: Copy & Value Proposition */}
            <div className="lg:col-span-7">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#EDE2C5] bg-[#FFF4C7] px-4 py-1.5 text-xs font-bold text-[#805400]">
                <SparklesIcon className="h-4 w-4 text-[#A66F00]" />
                <span>ذكاء أكاديمي يفهم مسارك، لا يخمّنه</span>
              </div>

              <h1 className="mt-5 text-3xl font-extrabold tracking-tight text-[#28241C] sm:text-4xl lg:text-5xl lg:leading-tight">
                مرشدي — قرارات أكاديمية أوضح، وتخطيط أذكى لمسارك الجامعي
              </h1>

              <p className="mt-5 text-base leading-relaxed text-[#726B5E] sm:text-lg">
                المنظومة الجامعية الأولى المبنية على <strong>القواعد الحتمية واللوائح المعتمدة</strong>.
                يفحص أهليتك للمواد بدقة قطعية، يوضح لك شجرة المتطلبات السابقة، ويقترح خطة فصولك بثقة كاملة وبلا أي احتمال للهلوسة.
              </p>

              {/* CTAs */}
              <div className="mt-8 flex flex-wrap items-center gap-4">
                {auth.isAuthenticated ? (
                  <>
                    <Link
                      href="/student"
                      className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#A66F00] px-6 py-3 text-sm font-bold text-white shadow-sm hover:bg-[#805400] transition-all active:scale-95"
                    >
                      <span>الانتقال إلى حسابي</span>
                      <span>←</span>
                    </Link>
                    <Link
                      href="/student/progress"
                      className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-[#EDE2C5] bg-white px-6 py-3 text-sm font-bold text-[#28241C] shadow-2xs hover:bg-[#FFF9E8] transition-colors"
                    >
                      <span>متابعة خطتي الأكاديمية</span>
                    </Link>
                  </>
                ) : (
                  <>
                    <Link
                      href="/login"
                      className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#A66F00] px-6 py-3 text-sm font-bold text-white shadow-sm hover:bg-[#805400] transition-all active:scale-95"
                    >
                      <span>دخول الطالب</span>
                      <span>←</span>
                    </Link>
                    <a
                      href="#demo"
                      className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-[#EDE2C5] bg-white px-6 py-3 text-sm font-bold text-[#28241C] shadow-2xs hover:bg-[#FFF9E8] transition-colors"
                    >
                      <span>جرّب محاكي الأهلية التفاعلي</span>
                    </a>
                  </>
                )}
              </div>

              {/* Trust Indicators */}
              <div className="mt-10 grid grid-cols-3 gap-4 border-t border-[#EDE2C5]/70 pt-6 text-right">
                <div>
                  <div className="text-xl font-extrabold text-[#A66F00] sm:text-2xl">100%</div>
                  <div className="mt-1 text-xs font-medium text-[#726B5E]">قواعد حتمية لا تهلوس</div>
                </div>
                <div>
                  <div className="text-xl font-extrabold text-[#A66F00] sm:text-2xl">SHA-256</div>
                  <div className="mt-1 text-xs font-medium text-[#726B5E]">سجل قرارات مشفر للتدقيق</div>
                </div>
                <div>
                  <div className="text-xl font-extrabold text-[#A66F00] sm:text-2xl">عربي أولاً</div>
                  <div className="mt-1 text-xs font-medium text-[#726B5E]">بنية جامعية مخصصة بالكامل</div>
                </div>
              </div>
            </div>

            {/* Left Column: Mascot & Interactive Floating Cards */}
            <div className="relative flex items-center justify-center lg:col-span-5">
              <div className="relative flex w-full max-w-sm flex-col items-center">
                {/* Glow ring */}
                <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-[#FFF4C7] to-[#E2AD27]/20 blur-2xl" />

                {/* 3D Mascot Character */}
                <div className="relative z-10 flex h-72 w-72 items-center justify-center overflow-hidden rounded-3xl border border-[#EDE2C5] bg-gradient-to-b from-[#FFF4C7] via-[#FFF9E8] to-white p-4 shadow-md sm:h-80 sm:w-80">
                  <Image
                    src="/brand/morshidi-guide.png"
                    alt="مرشدي - المساعد الأكاديمي الذكي"
                    width={280}
                    height={280}
                    className="h-full w-full object-contain drop-shadow-md"
                    priority
                  />
                </div>

                {/* Floating Card 1: Prerequisite Check Badge */}
                <div className="absolute -bottom-6 -right-4 z-20 w-60 rounded-2xl border border-[#EDE2C5] bg-white p-3.5 shadow-lg">
                  <div className="flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-800">
                      ✓
                    </span>
                    <div>
                      <div className="text-xs font-bold text-[#28241C]">مؤهل للتسجيل</div>
                      <div className="text-[10px] text-[#726B5E]">CS-301 الذكاء الاصطناعي</div>
                    </div>
                  </div>
                  <div className="mt-2 text-[10px] text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                    المتطلبات السابقة مستوفاة بالكامل
                  </div>
                </div>

                {/* Floating Card 2: Degree Progress Preview */}
                <div className="absolute -top-4 -left-4 z-20 w-52 rounded-2xl border border-[#EDE2C5] bg-white p-3 shadow-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-[#726B5E]">إنجاز الخطة</span>
                    <span className="text-[10px] font-bold text-[#A66F00]">55%</span>
                  </div>
                  <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-[#FFF4C7]">
                    <div className="h-full w-[55%] rounded-full bg-[#A66F00]" />
                  </div>
                  <div className="mt-1 text-[10px] text-right font-medium text-[#28241C]">
                    72 من 132 ساعة محتسبة
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Interactive Prerequisite Simulator Section */}
      <section id="demo" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8" dir="rtl">
        <div className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-sm sm:p-10">
          <div className="text-center">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-[#FFF4C7] px-3.5 py-1 text-xs font-bold text-[#805400]">
              <SparklesIcon className="h-3.5 w-3.5 text-[#A66F00]" />
              <span>محاكاة تفاعلية حية</span>
            </div>
            <h2 className="mt-3 text-2xl font-bold text-[#28241C] sm:text-3xl">
              شاهد كيف تحسب القواعد الحتمية أهليتك للمواد
            </h2>
            <p className="mx-auto mt-2 max-w-2xl text-xs leading-relaxed text-[#726B5E] sm:text-sm">
              اختر مساراً تخصصياً وشاهد كيف تترابط المواد تسلسلياً: مادة اجتزتها، ومادة فُتحت للتسجيل، ومادة أُغلقت لعدم اكتمال متطلبها.
            </p>
          </div>

          {/* Track selector buttons */}
          <div className="mt-8 flex flex-wrap justify-center gap-2">
            {DEMO_TRACKS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setActiveTrack(t)}
                className={`rounded-xl px-4 py-2 text-xs font-bold transition-all ${
                  activeTrack.id === t.id
                    ? "bg-[#A66F00] text-white shadow-xs"
                    : "border border-[#EDE2C5] bg-[#FFF9E8] text-[#28241C] hover:bg-[#FFF4C7]"
                }`}
              >
                {t.name}
              </button>
            ))}
          </div>

          {/* Dependency Chain Display */}
          <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
            {/* Step 1: Completed Course */}
            <div className="relative rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5">
              <div className="flex items-center justify-between">
                <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800">
                  {activeTrack.courseCompleted.state}
                </span>
                <span className="font-mono text-xs font-bold text-emerald-900" dir="ltr">
                  درجة: {activeTrack.courseCompleted.grade}
                </span>
              </div>
              <h3 className="mt-3 text-base font-bold text-[#28241C]">
                {activeTrack.courseCompleted.name}
              </h3>
              <p className="mt-1 font-mono text-xs font-semibold text-[#726B5E]" dir="ltr">
                {activeTrack.courseCompleted.code}
              </p>
              <div className="mt-3 text-[11px] text-emerald-800">
                ✓ متطلب أساسي تم إنجازه بنجاح.
              </div>
            </div>

            {/* Step 2: Eligible Course */}
            <div className="relative rounded-2xl border-2 border-[#E2AD27] bg-[#FFF4C7]/40 p-5 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="rounded-full bg-[#E2AD27]/30 px-2.5 py-0.5 text-[10px] font-bold text-[#805400]">
                  {activeTrack.courseEligible.state}
                </span>
                <span className="font-mono text-xs font-bold text-[#805400]">
                  {activeTrack.courseEligible.credits} ساعات
                </span>
              </div>
              <h3 className="mt-3 text-base font-bold text-[#28241C]">
                {activeTrack.courseEligible.name}
              </h3>
              <p className="mt-1 font-mono text-xs font-semibold text-[#726B5E]" dir="ltr">
                {activeTrack.courseEligible.code}
              </p>
              <div className="mt-3 text-[11px] font-semibold text-[#805400]">
                ★ مفتوحة للتسجيل الفصلي القادم مباشرة.
              </div>
            </div>

            {/* Step 3: Locked Course */}
            <div className="relative rounded-2xl border border-red-200 bg-red-50/50 p-5 opacity-90">
              <div className="flex items-center justify-between">
                <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-[10px] font-bold text-red-800">
                  {activeTrack.courseLocked.state}
                </span>
                <span className="text-xs font-bold text-red-700">مغلقة 🔒</span>
              </div>
              <h3 className="mt-3 text-base font-bold text-[#28241C]">
                {activeTrack.courseLocked.name}
              </h3>
              <p className="mt-1 font-mono text-xs font-semibold text-[#726B5E]" dir="ltr">
                {activeTrack.courseLocked.code}
              </p>
              <div className="mt-3 text-[11px] text-red-800">
                ⚠ {activeTrack.courseLocked.missing}
              </div>
            </div>
          </div>

          {/* Engine Rationale Banner */}
          <div className="mt-6 rounded-xl border border-[#EDE2C5] bg-[#FFF9E8] p-4 text-xs">
            <div className="flex items-center gap-2 font-bold text-[#805400]">
              <SparklesIcon className="h-4 w-4" />
              <span>حكم المحرك الحتمي:</span>
            </div>
            <p className="mt-1 leading-relaxed text-[#28241C]">
              {activeTrack.explanation}
            </p>
            <div className="mt-2 text-[10px] text-[#726B5E]">
              * هذه محاكاة تفاعلية تجريبية. عند تسجيل الدخول، يقرأ مرشدي سجلك الفعلي ويُطبّق القواعد على خطتك الدراسية مباشرة.
            </div>
          </div>
        </div>
      </section>

      {/* 3. Core Capabilities Section */}
      <section id="features" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8" dir="rtl">
        <div className="text-center">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-[#FFF4C7] px-3.5 py-1 text-xs font-bold text-[#805400]">
            <SparklesIcon className="h-3.5 w-3.5 text-[#A66F00]" />
            <span>منظومة متكاملة في مكان واحد</span>
          </div>
          <h2 className="mt-3 text-2xl font-bold text-[#28241C] sm:text-3xl">
            أدواتك الأكاديمية كجزء طبيعي من الموقع
          </h2>
          <p className="mx-auto mt-2 max-w-2xl text-xs leading-relaxed text-[#726B5E] sm:text-sm">
            لا داعي للتنقل بين أنظمة منفصلة ولوحات إدارة معقدة. كل أداة صُممت لتخدم رحلتك نحو التخرج.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {/* Feature 1 */}
          <div className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-2xs hover:shadow-xs transition-shadow">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
              <ProgressIcon className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-bold text-[#28241C]">
              متابعة التقدم في الخطة
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
              تحليل شامل لكل متطلبات كليتك وقسمك؛ يبيّن لك المجموعات المستوفاة، الساعات المتبقية، والنسبة المئوية لإنجاز الدرجة.
            </p>
            <div className="mt-4">
              <Link href="/student/progress" className="text-xs font-bold text-[#A66F00] hover:underline">
                استعرض خطتك الأكاديمية ←
              </Link>
            </div>
          </div>

          {/* Feature 2 */}
          <div className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-2xs hover:shadow-xs transition-shadow">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
              <EligibilityIcon className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-bold text-[#28241C]">
              فحص أهلية المواد قطيعاً
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
              أدخل رمز أي مادة ترغب بتسجيلها، وتلقَّ قراراً قطعياً مدعوماً بسند المتطلبات الأكاديمية واللوائح الجامعية.
            </p>
            <div className="mt-4">
              <Link href="/student/eligibility" className="text-xs font-bold text-[#A66F00] hover:underline">
                افحص أهلية مادة ←
              </Link>
            </div>
          </div>

          {/* Feature 3 */}
          <div className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-2xs hover:shadow-xs transition-shadow">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
              <PlannerIcon className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-bold text-[#28241C]">
              مخطط الفصل الدراسي الذكي
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
              حدد سقف الساعات والعبء الدراسي الأنسب لك، وسيقوم المحرك باقتراح أفضل باقة مواد متوافقة مع شجرة تخرجك.
            </p>
            <div className="mt-4">
              <Link href="/student/planner" className="text-xs font-bold text-[#A66F00] hover:underline">
                ابدأ تخطيط فصلك ←
              </Link>
            </div>
          </div>

          {/* Feature 4 */}
          <div className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-2xs hover:shadow-xs transition-shadow">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
              <DegreePathIcon className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-bold text-[#28241C]">
              مسار التخرج المتوقع
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
              توقع خط زمني فصلاً بفصل حتى التخرج. يحسب الفصول المطلوبة لتفادي التأخر ومعرفة المواد الحرجة في كل مرحلة.
            </p>
            <div className="mt-4">
              <Link href="/student/degree-path" className="text-xs font-bold text-[#A66F00] hover:underline">
                استكشف مسار التخرج ←
              </Link>
            </div>
          </div>

          {/* Feature 5 */}
          <div className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-2xs hover:shadow-xs transition-shadow">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
              <MockRegistrationIcon className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-bold text-[#28241C]">
              محاكاة التسجيل التجريبي
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
              جرّب باقاتك المفضلة وسجل رغباتك غير الملزمة، مما يتيح لك وللكلية معرفة حجم الإقبال على الشُعب مسبقاً.
            </p>
            <div className="mt-4">
              <Link href="/student/mock-registration" className="text-xs font-bold text-[#A66F00] hover:underline">
                جرّب التسجيل التجريبي ←
              </Link>
            </div>
          </div>

          {/* Feature 6 */}
          <div className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-2xs hover:shadow-xs transition-shadow">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
              <AdvisorIcon className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-bold text-[#28241C]">
              المرشد الأكاديمي الذكي
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
              مساعد تفاعلي يستند لنظام القواعد واللوائح الرسمية؛ يشرح لك أسباب الأهلية ويستشهد بمواد اللائحة المعتمدة.
            </p>
            <div className="mt-4">
              <Link href="/student/advisor" className="text-xs font-bold text-[#A66F00] hover:underline">
                تحدث مع مرشدي AI ←
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 4. How Morshidi Works (4 Steps) */}
      <section id="how-it-works" className="border-y border-[#EDE2C5] bg-[#FFF9E8]/50 py-16" dir="rtl">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-[#FFF4C7] px-3.5 py-1 text-xs font-bold text-[#805400]">
              <SparklesIcon className="h-3.5 w-3.5 text-[#A66F00]" />
              <span>خطوات واضحة وبسيطة</span>
            </div>
            <h2 className="mt-3 text-2xl font-bold text-[#28241C] sm:text-3xl">
              كيف يعمل مرشدي في رحلتك الدراسية؟
            </h2>
          </div>

          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-[#EDE2C5] bg-white p-6 shadow-2xs">
              <div className="text-2xl font-extrabold text-[#A66F00]">01</div>
              <h3 className="mt-3 text-base font-bold text-[#28241C]">سجل دخولك</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                ادخل إلى مرشدي باستخدام حسابك الجامعي؛ لتبقى داخل الموقع نفسه دون الانتقال إلى لوحة إدارة منفصلة.
              </p>
            </div>

            <div className="rounded-2xl border border-[#EDE2C5] bg-white p-6 shadow-2xs">
              <div className="text-2xl font-extrabold text-[#A66F00]">02</div>
              <h3 className="mt-3 text-base font-bold text-[#28241C]">قراءة مسارك</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                يقرأ مرشدي خطتك المعتمدة وسجل محاولاتك الأكاديمية المحتسبة مباشرة وبأمان تام.
              </p>
            </div>

            <div className="rounded-2xl border border-[#EDE2C5] bg-white p-6 shadow-2xs">
              <div className="text-2xl font-extrabold text-[#A66F00]">03</div>
              <h3 className="mt-3 text-base font-bold text-[#28241C]">التحليل الحتمي</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                تُحلل القواعد الصارمة شجرة المواد ومجموعات المتطلبات لتحديد أهليتك الحقيقية وخياراتك المتاحة.
              </p>
            </div>

            <div className="rounded-2xl border border-[#EDE2C5] bg-white p-6 shadow-2xs">
              <div className="text-2xl font-extrabold text-[#A66F00]">04</div>
              <h3 className="mt-3 text-base font-bold text-[#28241C]">اتخاذ القرار بثقة</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
                اختر مواد فصلك القادم مع تفسير قطعي يوضح سبب إتاحة كل مادة وأثرها على موعد تخرجك.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Governance & Invariant Section */}
      <section id="about" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8" dir="rtl">
        <div className="overflow-hidden rounded-3xl border border-[#EDE2C5] bg-gradient-to-l from-[#FFF4C7]/80 via-[#FFF9E8] to-[#FFFFFF] p-8 shadow-xs sm:p-12">
          <div className="max-w-3xl">
            <span className="rounded-full bg-[#A66F00]/10 px-3 py-1 text-xs font-bold text-[#A66F00]">
              المبدأ الحاكم لمنظومة مرشدي
            </span>
            <h2 className="mt-4 text-2xl font-extrabold text-[#28241C] sm:text-3xl lg:text-4xl">
              الذكاء الاصطناعي يشرح — والقواعد الأكاديمية واللوائح المعتمدة تقرر.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-[#726B5E] sm:text-base">
              لا نعتمد على نماذج الذكاء الاصطناعي الاحتمالية في البتّ في قرارات التخرج أو استيفاء المتطلبات السابقة، لأن القرارات الأكاديمية مصيرية ولا تحتمل الهلوسة أو التخمين.
              مرشدي يفصل تماماً بين <strong>محرك القواعد الرياضي الصارم</strong> الذي يُصدر القرارات، وبين <strong>الذكاء الاصطناعي</strong> الذي يشرحها لك بأسلوب سلس ومفهوم.
            </p>

            <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-red-200 bg-red-50/60 p-4">
                <div className="text-xs font-bold text-red-900">الأنظمة التوليدية العامة ✗</div>
                <p className="mt-1 text-xs text-red-800 leading-relaxed">
                  تعتمد على التخمين، تخلط بين متطلبات الجامعات المختلفة، وتفتقر للسند التشريعي المعتمد.
                </p>
              </div>

              <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4">
                <div className="text-xs font-bold text-emerald-900">منظومة مرشدي الحتمية ✓</div>
                <p className="mt-1 text-xs text-emerald-800 leading-relaxed">
                  تعتمد خطتك المعتمدة حرفياً، تتبع لوائح كليتك، وتوثق كل قرار بسجل غير قابل للتعديل.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Final Call to Action with Mascot */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8" dir="rtl">
        <div className="relative overflow-hidden rounded-3xl border border-[#EDE2C5] bg-[#FFF4C7] p-8 text-center shadow-sm sm:p-12">
          <div className="mx-auto flex h-24 w-24 items-center justify-center overflow-hidden rounded-2xl border border-[#EDE2C5] bg-white p-2 shadow-2xs">
            <Image
              src="/brand/morshidi-guide.png"
              alt="مرشدي"
              width={80}
              height={80}
              className="object-contain"
            />
          </div>
          <h2 className="mt-4 text-2xl font-bold text-[#28241C] sm:text-3xl">
            جاهز لبدء تجربة أكاديمية أوضح؟
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-xs text-[#726B5E] sm:text-sm">
            انضم لمرشدي اليوم، واجعل كل قرار دراسي مدعوماً باليقين والسند الموثق.
          </p>
          <div className="mt-6 flex justify-center gap-4">
            {auth.isAuthenticated ? (
              <Link
                href="/student"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[#A66F00] px-6 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-[#805400] transition-colors"
              >
                <span>الانتقال إلى حسابي</span>
                <span>←</span>
              </Link>
            ) : (
              <Link
                href="/login"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[#A66F00] px-6 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-[#805400] transition-colors"
              >
                <span>دخول الطالب الآن</span>
                <span>←</span>
              </Link>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}