"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type { DiagnosticSession } from "@/lib/api/student-types";

type SelfConfidence = "LOW" | "MEDIUM" | "HIGH";
type LegacyChoice = "PROMPT" | "CONTINUE";

const V1 = "QUICK_DIAGNOSTIC_V1";
const V2 = "QUICK_DIAGNOSTIC_V2";

const confidenceOptions: Array<{ value: SelfConfidence; label: string; hint: string }> = [
  { value: "LOW", label: "منخفضة", hint: "لست متأكداً" },
  { value: "MEDIUM", label: "متوسطة", hint: "أرجّح إجابتي" },
  { value: "HIGH", label: "مرتفعة", hint: "واثق من الحل" },
];

export default function DiagnosticPage() {
  const client = useAuthenticatedApi();
  const api = useMemo(() => new StudentApiService(client), [client]);
  const [session, setSession] = useState<DiagnosticSession | null>(null);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<SelfConfidence | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [legacyChoice, setLegacyChoice] = useState<LegacyChoice>("PROMPT");
  const [legacyAbandoned, setLegacyAbandoned] = useState(false);
  const questionStartedAt = useRef(0);

  useEffect(() => {
    let active = true;
    void api.getDiagnosticStatus().then(status => status.active_session_id
      ? api.resumeDiagnostic(status.active_session_id) : api.startDiagnostic())
      .then(value => {
        if (active) {
          setSession(value);
          questionStartedAt.current = Date.now();
          setBusy(false);
        }
      })
      .catch(() => {
        if (active) {
          setError("تعذّر فتح التشخيص. حاول مرة أخرى.");
          setBusy(false);
        }
      });
    return () => { active = false; };
  }, [api]);

  async function startNewDiagnostic() {
    if (!session || session.assessment_version !== V1 || busy) return;
    setBusy(true);
    setError(null);
    let abandoned = legacyAbandoned;
    try {
      if (!abandoned) {
        await api.abandonDiagnostic(session.session_id);
        abandoned = true;
        setLegacyAbandoned(true);
      }
      const next = await api.startDiagnostic();
      setSession(next);
      setSelectedOption(null);
      setConfidence(null);
      setLegacyChoice("PROMPT");
      setLegacyAbandoned(false);
      questionStartedAt.current = Date.now();
    } catch {
      setError(abandoned
        ? "تم إغلاق التشخيص القديم، لكن تعذّر بدء التشخيص الجديد. حاول مرة أخرى."
        : "تعذّر إغلاق التشخيص القديم. بقيت جلستك كما هي ويمكنك المحاولة مجدداً.");
    } finally {
      setBusy(false);
    }
  }

  async function submitAnswer() {
    if (!session?.question || !selectedOption || busy) return;
    const isV2 = session.assessment_version === V2;
    if (isV2 && !confidence) return;
    setBusy(true);
    setError(null);
    try {
      const next = isV2
        ? await api.answerDiagnostic(
          session.session_id, session.question.question_id, selectedOption,
          Math.min(1_800_000, Math.max(0, Date.now() - questionStartedAt.current)), confidence!,
        )
        : await api.answerDiagnostic(
          session.session_id, session.question.question_id, selectedOption,
        );
      setSession(next);
      setSelectedOption(null);
      setConfidence(null);
      questionStartedAt.current = Date.now();
    } catch {
      setError("لم يتم حفظ الإجابة. بقيت جلستك كما هي ويمكنك المحاولة مجدداً.");
    } finally {
      setBusy(false);
    }
  }

  if (busy && !session) {
    return <main dir="rtl" className="flex min-h-[70vh] items-center justify-center p-6">
      <p role="status" className="text-amber-700">جارٍ استعادة جلسة التشخيص…</p>
    </main>;
  }
  if (!session) {
    return <main dir="rtl" className="mx-auto max-w-2xl p-6"><p role="alert">{error}</p></main>;
  }
  const isV2 = session.assessment_version === V2;
  if (session.status === "COMPLETED") {
    return <main dir="rtl" className="mx-auto flex min-h-[75vh] max-w-4xl items-center p-4 sm:p-6">
      <section className="relative w-full overflow-hidden rounded-[2rem] border border-amber-300/40 bg-stone-950 p-7 text-center text-white shadow-2xl sm:p-12">
        <div aria-hidden="true" className="absolute inset-x-16 top-0 h-40 rounded-full bg-amber-400/15 blur-3xl motion-safe:animate-pulse" />
        <div className="relative">
          <p className="text-sm font-black text-amber-300">اكتملت {session.answered_count} من {session.maximum_questions}</p>
          <h1 className="mt-3 text-3xl font-black leading-tight sm:text-5xl">{isV2 ? "خط الأساس الأكاديمي جاهز" : "اكتمل التشخيص القديم"}</h1>
          <p className="mx-auto mt-5 max-w-2xl leading-8 text-stone-300">{isV2
            ? "حلّل مرشدي الدقة، صعوبة الأسئلة، وقت الاستجابة، واتساق الثقة بطريقة حتمية. النتيجة تشخيص أولي وليست علامة جامعية أو حكماً على الذكاء."
            : "حُفظت نتيجة النسخة السابقة كما هي، من دون تحويلها إلى دليل توقيت أو ثقة من النسخة الجديدة."}</p>
          <Link href="/student/intelligence" className="mt-8 inline-flex min-h-12 items-center rounded-xl bg-amber-300 px-6 py-3 font-black text-stone-950 transition hover:bg-amber-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white motion-reduce:transition-none">عرض ذكائي الأكاديمي</Link>
        </div>
      </section>
    </main>;
  }
  if (session.assessment_version === V1 && legacyChoice === "PROMPT") {
    return <main id="main-content" dir="rtl" className="mx-auto flex min-h-[75vh] max-w-3xl items-center p-4 sm:p-6">
      <section className="w-full rounded-[2rem] border border-amber-300/40 bg-stone-950 p-7 text-white shadow-2xl sm:p-10" aria-labelledby="legacy-diagnostic-heading">
        <p className="text-sm font-black text-amber-300">انتقال إلى التشخيص الجديد</p>
        <h1 id="legacy-diagnostic-heading" className="mt-3 text-3xl font-black leading-tight">لديك تشخيص قديم غير مكتمل</h1>
        <p className="mt-5 max-w-2xl leading-8 text-stone-300">بدأت نسخة سابقة من التشخيص. يمكنك إكمالها، أو إغلاقها والبدء بالتشخيص الجديد المكوّن من 30 سؤالاً.</p>
        <div className="mt-7 grid gap-3 sm:grid-cols-2">
          <button type="button" disabled={busy || legacyAbandoned} onClick={() => { setError(null); setLegacyChoice("CONTINUE"); }} className="inline-flex min-h-12 items-center justify-center rounded-xl border border-amber-300/60 px-5 py-3 font-black text-amber-200 transition hover:bg-amber-300/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300 disabled:cursor-not-allowed disabled:opacity-40 motion-reduce:transition-none">إكمال التشخيص القديم</button>
          <button type="button" disabled={busy} onClick={() => void startNewDiagnostic()} className="inline-flex min-h-12 items-center justify-center rounded-xl bg-amber-300 px-5 py-3 font-black text-stone-950 transition hover:bg-amber-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white disabled:cursor-not-allowed disabled:opacity-40 motion-reduce:transition-none">{busy ? "جارٍ بدء التشخيص الجديد…" : "ابدأ التشخيص الجديد — 30 سؤال"}</button>
        </div>
        {error ? <p role="alert" className="mt-5 rounded-xl border border-red-400/30 bg-red-400/10 p-4 text-sm leading-6 text-red-200">{error}</p> : null}
      </section>
    </main>;
  }

  const question = session.question!;
  const questionNumber = session.answered_count + 1;
  const progress = Math.round((session.answered_count / session.maximum_questions) * 100);
  const ready = Boolean(selectedOption && (!isV2 || confidence));

  return <main id="main-content" dir="rtl" className="mx-auto min-h-[78vh] max-w-5xl p-4 sm:p-6 lg:p-8">
    <header className="flex flex-wrap items-center justify-between gap-4">
      <div>
        <p className="text-xs font-black tracking-wide text-amber-700">التشخيص الأكاديمي السريع</p>
        <h1 className="mt-1 text-xl font-black text-stone-950">السؤال {questionNumber} من {session.maximum_questions}</h1>
      </div>
      <Link href="/student" className="inline-flex min-h-11 items-center rounded-xl border border-stone-300 px-4 py-2 text-sm font-bold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500">إكماله لاحقاً</Link>
    </header>

    <div className="mt-5 h-2.5 overflow-hidden rounded-full bg-stone-200" role="progressbar" aria-label="تقدم التشخيص" aria-valuenow={questionNumber} aria-valuemin={1} aria-valuemax={session.maximum_questions}>
      <div className="h-full rounded-full bg-gradient-to-l from-amber-300 to-amber-600 transition-[width] duration-300 motion-reduce:transition-none" style={{ width: `${progress}%` }} />
    </div>

    <section className="mt-7 overflow-hidden rounded-[2rem] border border-amber-500/20 bg-stone-950 text-white shadow-2xl" aria-labelledby="question-heading">
      <div className="border-b border-white/10 px-5 py-4 text-xs leading-6 text-stone-400 sm:px-9">لن نعرض المجال المقاس أو الصعوبة أو صحة الإجابة أثناء التشخيص.</div>
      <div className="p-5 sm:p-9">
        <h2 id="question-heading" className="text-2xl font-black leading-[1.7] sm:text-3xl">{question.prompt_ar}</h2>
        <fieldset disabled={busy} className="mt-7 grid gap-3">
          <legend className="sr-only">اختر إجابة واحدة</legend>
          {question.options.map(option => {
            const selected = selectedOption === option.option_id;
            return <button key={option.option_id} type="button" aria-pressed={selected} onClick={() => setSelectedOption(option.option_id)} className={`flex min-h-14 items-center gap-4 rounded-2xl border p-4 text-right font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300 disabled:opacity-50 motion-reduce:transition-none ${selected ? "border-amber-300 bg-amber-300/15" : "border-white/15 bg-white/5 hover:border-amber-300/70 hover:bg-white/10"}`}>
              <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-sm ${selected ? "border-amber-200 bg-amber-300 text-stone-950" : "border-amber-300/50 text-amber-200"}`}>{option.option_id}</span>
              <span>{option.text_ar}</span>
            </button>;
          })}
        </fieldset>

        {isV2 ? <fieldset disabled={busy} className="mt-8">
          <legend className="font-black">ما مدى ثقتك بإجابتك؟</legend>
          <p className="mt-1 text-xs leading-6 text-stone-400">هذه ليست علامة إضافية؛ تساعدنا على فهم معايرة ثقتك فقط.</p>
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
            {confidenceOptions.map(item => <button key={item.value} type="button" aria-pressed={confidence === item.value} onClick={() => setConfidence(item.value)} className={`min-h-14 rounded-xl border px-4 py-3 text-right transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300 motion-reduce:transition-none ${confidence === item.value ? "border-amber-300 bg-amber-300 text-stone-950" : "border-white/15 bg-white/5 hover:border-amber-300/70"}`}>
              <span className="block font-black">{item.label}</span><span className="block text-xs opacity-75">{item.hint}</span>
            </button>)}
          </div>
        </fieldset> : null}

        <div aria-live="polite" className="mt-4 min-h-6 text-sm text-red-300">{error}</div>
        <button type="button" disabled={!ready || busy} onClick={() => void submitAnswer()} className="mt-3 inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-amber-300 px-6 py-3 font-black text-stone-950 transition hover:bg-amber-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white disabled:cursor-not-allowed disabled:opacity-40 motion-reduce:transition-none sm:w-auto">{busy ? "جارٍ الحفظ…" : questionNumber === session.maximum_questions ? "إنهاء التشخيص" : "السؤال التالي"}</button>
        <p className="mt-5 text-xs leading-6 text-stone-400">{isV2
          ? "نسجّل زمن الاستجابة بهدوء لتحسين جودة الدليل، من دون مؤقت ضاغط. التشخيص لا يغيّر معدلك أو أهليتك أو متطلبات خطتك."
          : "تُحفظ إجابات هذه النسخة القديمة وفق قواعدها الأصلية، من دون إضافة دليل توقيت أو ثقة من النسخة الجديدة."}</p>
      </div>
    </section>
  </main>;
}
