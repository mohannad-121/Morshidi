"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type { DiagnosticSession } from "@/lib/api/student-types";

export default function DiagnosticPage() {
  const client = useAuthenticatedApi();
  const api = useMemo(() => new StudentApiService(client), [client]);
  const [session, setSession] = useState<DiagnosticSession | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void api.getDiagnosticStatus().then(status => status.active_session_id
      ? api.resumeDiagnostic(status.active_session_id) : api.startDiagnostic())
      .then(value => { if (active) { setSession(value); setBusy(false); } })
      .catch(() => { if (active) { setError("تعذّر فتح الاختبار. حاول مرة أخرى."); setBusy(false); } });
    return () => { active = false; };
  }, [api]);

  async function answer(optionId: string) {
    if (!session?.question || busy) return;
    setBusy(true); setError(null);
    try { setSession(await api.answerDiagnostic(session.session_id, session.question.question_id, optionId)); }
    catch { setError("لم يتم حفظ الإجابة. لم تتغير جلستك، ويمكنك المحاولة مجدداً."); }
    finally { setBusy(false); }
  }

  if (busy && !session) return <main dir="rtl" className="flex min-h-[70vh] items-center justify-center"><p role="status" className="text-amber-700">جارٍ استعادة جلسة الاختبار…</p></main>;
  if (!session) return <main dir="rtl" className="mx-auto max-w-2xl p-6"><p role="alert">{error}</p></main>;
  if (session.status === "COMPLETED") return <main dir="rtl" className="mx-auto flex min-h-[70vh] max-w-3xl items-center p-5"><section className="w-full rounded-3xl border border-amber-400/40 bg-stone-950 p-8 text-center text-white shadow-2xl"><p className="text-amber-400">اكتمل الاختبار</p><h1 className="mt-3 text-4xl font-black">بصمتك الأكاديمية جاهزة</h1><p className="mx-auto mt-4 max-w-xl leading-7 text-stone-300">هذه نتيجة تشخيصية نموذجية وليست علامة جامعية. ستظهر مع مصدرها وثقتها بوضوح.</p><Link href="/student/intelligence" className="mt-7 inline-flex min-h-11 items-center rounded-xl bg-amber-400 px-6 py-3 font-black text-stone-950 focus-visible:ring-2 focus-visible:ring-white">عرض بصمتي الأكاديمية</Link></section></main>;

  const question = session.question!;
  const progress = Math.min(100, Math.round((session.answered_count / session.maximum_questions) * 100));
  return <main id="main-content" dir="rtl" className="mx-auto min-h-[75vh] max-w-4xl p-4 sm:p-6 lg:p-8">
    <header className="flex items-center justify-between gap-4"><div><p className="text-xs font-bold text-amber-700">الاختبار التشخيصي السريع</p><p className="mt-1 text-sm text-muted">السؤال {session.answered_count + 1} · بحد أقصى {session.maximum_questions}</p></div><Link href="/student" className="min-h-11 rounded-xl border px-4 py-3 text-sm font-bold focus-visible:ring-2 focus-visible:ring-amber-500">إكماله لاحقاً</Link></header>
    <div className="mt-5 h-2 overflow-hidden rounded-full bg-stone-200" role="progressbar" aria-label="تقدم الاختبار" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}><div className="h-full rounded-full bg-amber-500 transition-all motion-reduce:transition-none" style={{ width: `${progress}%` }} /></div>
    <section className="mt-8 rounded-3xl border border-amber-500/20 bg-stone-950 p-6 text-white shadow-2xl sm:p-10" aria-labelledby="question-heading">
      <p className="text-xs font-bold tracking-wide text-amber-400">{question.domain.replaceAll("_", " ")}</p>
      <h1 id="question-heading" className="mt-4 text-2xl font-black leading-relaxed sm:text-3xl">{question.prompt_ar}</h1>
      <fieldset disabled={busy} className="mt-8 grid gap-3"><legend className="sr-only">اختر إجابة واحدة</legend>{question.options.map(option => <button key={option.option_id} type="button" onClick={() => void answer(option.option_id)} className="flex min-h-14 items-center gap-4 rounded-2xl border border-white/15 bg-white/5 p-4 text-right font-semibold transition hover:border-amber-400 hover:bg-amber-400/10 focus-visible:ring-2 focus-visible:ring-amber-400 disabled:opacity-50 motion-reduce:transition-none"><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-amber-400/50 text-amber-300">{option.option_id}</span><span>{option.text_ar}</span></button>)}</fieldset>
      <div aria-live="polite" className="mt-4 min-h-6 text-sm text-red-300">{error}</div>
      <p className="mt-4 text-xs leading-6 text-stone-400">لن نعرض صحة الإجابة أثناء الاختبار، ولا يؤثر الاختبار على معدلك أو أهليتك.</p>
    </section>
  </main>;
}
