"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Bot, Send, ShieldCheck, UserRound } from "lucide-react";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { InstitutionalAnalyticsApi, type CopilotAnswer } from "@/lib/api/institutional-analytics";

type Turn = { question: string; answer: CopilotAnswer };

export default function InstitutionalCopilotPage() {
  const client = useAuthenticatedApi();
  const api = useMemo(() => new InstitutionalAnalyticsApi(client), [client]);
  const [university, setUniversity] = useState("");
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  useEffect(() => { let live = true; void api.access().then(scopes => {
    if (live) setUniversity(scopes[0]?.university_id ?? "");
  }).catch(() => { if (live) setError(true); }); return () => { live = false; }; }, [api]);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!question.trim() || !university) return;
    setBusy(true); setError(false);
    const previous = turns.at(-1)?.answer;
    try {
      const answer = await api.ask({ question: question.trim(), university_id: university,
        term_key: "CURRENT", ...(previous?.tool ? { previous_tool: previous.tool } : {}),
        ...(previous?.course_code ? { previous_course_code: previous.course_code } : {}) });
      setTurns(items => [...items, { question: question.trim(), answer }]); setQuestion("");
    } catch { setError(true); }
    finally { setBusy(false); }
  }
  return <main className="mx-auto max-w-5xl space-y-5 p-4 sm:p-6 lg:p-8">
    <header><span className="text-xs font-semibold text-amber-300">مساعد مؤسسي مؤسس على أدوات حتمية</span><h1 className="mt-2 text-3xl font-bold">اسأل مرشدي عن الجامعة</h1><p className="mt-2 text-sm leading-7 text-muted">النموذج يختار أداة معتمدة فقط. الأرقام تُعاد كما حسبتها الخدمات الحتمية، ولا ينفذ المساعد أي تغيير.</p></header>
    <div className="flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/10 p-3 text-xs text-emerald-100"><ShieldCheck className="size-4" aria-hidden="true"/> تجميعات فقط · لا بيانات شخصية · لا تسجيل أو إنشاء شعب</div>
    <section aria-live="polite" className="min-h-80 space-y-4 rounded-2xl border border-border bg-surface p-4 sm:p-6">
      {!turns.length && <div className="grid min-h-64 place-items-center text-center text-muted"><div><Bot className="mx-auto mb-3 size-10 text-amber-300"/><p>جرّب: شو أكثر المواد عليها طلب حاليًا؟</p><p>أو: إذا فتحنا شعبة إضافية 30 مقعد للمادة 0200104 شو بصير؟</p></div></div>}
      {turns.map((turn, index) => <div key={index} className="space-y-3"><div className="mr-auto flex max-w-[85%] items-start gap-2 rounded-2xl bg-white/5 p-3"><UserRound className="mt-0.5 size-4"/><p>{turn.question}</p></div><div className="ml-auto max-w-[90%] rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4"><div className="mb-2 flex items-center gap-2 text-xs text-amber-200"><Bot className="size-4"/>{turn.answer.tool ?? "امتناع آمن"}</div><p className="leading-7">{turn.answer.answer_text}</p>{turn.answer.result && <details className="mt-3 text-xs text-muted"><summary className="cursor-pointer">عرض بنية الأداة الحتمية</summary><pre dir="ltr" className="mt-2 max-h-72 overflow-auto rounded-lg bg-black/30 p-3 text-left">{JSON.stringify(turn.answer.result, null, 2)}</pre></details>}</div></div>)}
      {busy && <p role="status" className="text-sm text-muted">جارٍ اختيار الأداة المؤسسية المعتمدة…</p>}
      {error && <p role="alert" className="text-sm text-red-200">المساعد غير متاح أو أن الدور غير مخول.</p>}
    </section>
    <form onSubmit={submit} className="flex gap-2"><label className="sr-only" htmlFor="institutional-question">السؤال المؤسسي</label><textarea id="institutional-question" required minLength={8} maxLength={400} value={question} onChange={event => setQuestion(event.target.value)} placeholder="اكتب سؤالك المؤسسي…" className="min-h-14 flex-1 resize-none rounded-2xl border border-border bg-surface px-4 py-3 focus-visible:outline-2 focus-visible:outline-amber-400"/><button disabled={busy || !university} aria-label="إرسال السؤال" className="button-primary grid min-h-14 min-w-14 place-items-center rounded-2xl disabled:opacity-50"><Send className="size-5"/></button></form>
  </main>;
}
