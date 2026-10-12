"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type { StudentIntelligenceProfileV2 } from "@/lib/api/student-types";

const labels: Record<string, string> = {
  PROGRAMMING: "البرمجة", PYTHON: "بايثون", LOGICAL_REASONING: "التفكير المنطقي",
  QUANTITATIVE_MATH: "الرياضيات الكمية", STATISTICS: "الإحصاء",
  DATA_ANALYSIS: "تحليل البيانات", THEORY_COMPREHENSION: "الفهم النظري",
  MEMORIZATION: "الاستيعاب والتذكر", PRACTICAL_LAB: "المهارات العملية",
};

export default function StudentIntelligencePage() {
  const client = useAuthenticatedApi();
  const api = useMemo(() => new StudentApiService(client), [client]);
  const [profile, setProfile] = useState<StudentIntelligenceProfileV2 | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let live = true;
    void api.getStudentIntelligence()
      .then(value => { if (live) setProfile(value); })
      .catch(() => { if (live) setError(true); });
    return () => { live = false; };
  }, [api]);

  if (error) return <main dir="rtl" className="mx-auto max-w-5xl p-6"><p role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-5">تعذّر تحميل بصمتك الأكاديمية حالياً.</p></main>;
  if (!profile) return <main dir="rtl" className="mx-auto max-w-5xl p-6"><p role="status" className="text-accent">جارٍ بناء بصمتك الأكاديمية…</p></main>;

  return <main id="main-content" dir="rtl" className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header className="overflow-hidden rounded-3xl border border-amber-500/30 bg-stone-950 p-6 text-white shadow-xl sm:p-8">
      <p className="text-sm font-bold text-amber-400">ذكاء مرشدي الأكاديمي</p>
      <h1 className="mt-2 text-3xl font-black sm:text-4xl">بصمتي الأكاديمية</h1>
      <p className="mt-3 max-w-3xl text-sm leading-7 text-stone-300">ملف تفسيري مبني على أدلة موثقة ونموذج تشخيصي. لا يُعد تقييماً رسمياً ولا يغيّر أي شرط أكاديمي.</p>
      <div className="mt-5 flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-white/10 px-3 py-2">{profile.verified_grade_count} علامة جامعية موثقة</span>
        <span className="rounded-full bg-white/10 px-3 py-2">الثقة: {profile.evidence_quality}</span>
        <span className="rounded-full bg-white/10 px-3 py-2">آخر تحديث: {new Date(profile.generated_at).toLocaleDateString("ar-JO")}</span>
      </div>
    </header>

    {profile.diagnostic_recommended && <section className="rounded-3xl border border-amber-300 bg-amber-50 p-6">
      <h2 className="text-xl font-black text-stone-950">خلّينا نتعرّف عليك</h2>
      <p className="mt-2 max-w-3xl leading-7 text-stone-700">لسا ما عندنا سجل جامعي كافي حتى نفهم أسلوبك الأكاديمي. اختبار سريع يساعد مرشدي يعطيك توصيات أنسب.</p>
      <div className="mt-4 flex flex-wrap gap-3 text-sm font-semibold text-stone-700"><span>حوالي 7 دقائق</span><span>10–16 سؤال</span><span>لا يؤثر على معدلك أو سجلك الجامعي</span></div>
      <Link href="/student/diagnostic" className="mt-5 inline-flex min-h-11 items-center rounded-xl bg-stone-950 px-5 py-3 font-bold text-amber-300 focus-visible:ring-2 focus-visible:ring-amber-500">ابدأ الاختبار السريع</Link>
    </section>}

    <section aria-labelledby="skills-heading">
      <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-sm font-bold text-amber-700">الأدلة والقدرات</p><h2 id="skills-heading" className="text-2xl font-black">ملف المهارات</h2></div>
      {profile.diagnostic_completed && <Link href="/student/diagnostic" className="font-semibold text-amber-800 underline underline-offset-4">عرض/إعادة التشخيص</Link>}</div>
      {profile.skills.length === 0 ? <p className="mt-4 rounded-2xl border p-5">لا تتوفر أدلة قدرة كافية بعد. تبقى القرارات الأكاديمية الأساسية متاحة كالمعتاد.</p> :
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{profile.skills.map(skill => <article key={skill.skill_id} className="rounded-2xl border border-border bg-surface p-5 shadow-xs">
        <div className="flex items-start justify-between gap-3"><h3 className="font-bold">{labels[skill.skill_id] ?? skill.skill_id}</h3><strong className="text-2xl text-amber-700">{skill.score ?? "—"}</strong></div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-stone-200" role="meter" aria-label={`درجة ${skill.score ?? "غير متوفرة"} من 100`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={skill.score ?? undefined}><div className="h-full rounded-full bg-amber-500" style={{ width: `${skill.score ?? 0}%` }} /></div>
        <dl className="mt-4 grid grid-cols-2 gap-2 text-xs"><div><dt className="text-muted">الثقة</dt><dd className="font-bold">{skill.confidence}</dd></div><div><dt className="text-muted">جودة الدليل</dt><dd className="font-bold">{skill.evidence_quality}</dd></div></dl>
        <p className="mt-3 text-xs leading-6 text-muted">جامعة: {skill.university_evidence_count} · تشخيص: {skill.diagnostic_evidence_count}</p>
      </article>)}</div>}
    </section>

    <section className="grid gap-4 md:grid-cols-2"><article className="rounded-2xl border p-5"><h2 className="font-black">نقاط القوة المدعومة</h2><p className="mt-2 text-sm leading-7">{profile.strengths.map(x => labels[x] ?? x).join("، ") || "لا توجد أدلة كافية لعرضها بعد."}</p></article>
      <article className="rounded-2xl border p-5"><h2 className="font-black">مجالات التطوير</h2><p className="mt-2 text-sm leading-7">{profile.development_areas.map(x => labels[x] ?? x).join("، ") || "لا توجد إشارة مدعومة حالياً."}</p></article></section>
    <aside className="rounded-2xl bg-stone-100 p-5 text-sm leading-7 text-stone-700"><h2 className="font-black text-stone-950">حدود النموذج</h2><ul className="mt-2 list-disc space-y-1 pe-5">{profile.limitations.map(item => <li key={item}>{item}</li>)}</ul></aside>
  </main>;
}
