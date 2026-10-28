"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, CalendarDays, CheckCircle2, Clock3, MapPin, Search, Trash2, UserRound } from "lucide-react";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { RegistrationApi, type RegistrationContext, type RegistrationPreview, type RegistrationSection } from "@/lib/api/registration";

const stateStyle: Record<string, string> = {
  ELIGIBLE: "border-emerald-200 bg-emerald-50 text-emerald-800",
  REVIEW_REQUIRED: "border-amber-200 bg-amber-50 text-amber-900",
  NOT_ELIGIBLE: "border-red-200 bg-red-50 text-red-800",
};

const idempotencyKey = (action: string) => `${action}-${crypto.randomUUID()}`;

function SectionFacts({ section }: { section: RegistrationSection }) {
  return <div className="grid gap-2 text-xs text-muted sm:grid-cols-2">
    <span className="inline-flex items-center gap-1.5"><Clock3 className="h-4 w-4" aria-hidden="true" />
      {section.meetings?.length
        ? section.meetings.map((meeting) => `${meeting.day} ${meeting.startTime}–${meeting.endTime}`).join("، ")
        : `${section.days}، ${section.startTime}–${section.endTime}`}
    </span>
    <span className="inline-flex items-center gap-1.5"><MapPin className="h-4 w-4" aria-hidden="true" />{section.room || "غير محدد"}</span>
    <span className="inline-flex items-center gap-1.5"><UserRound className="h-4 w-4" aria-hidden="true" />{section.instructor || "غير محدد"}</span>
    <span>{Math.max(0, section.capacity - section.enrolled)} مقعد متاح من {section.capacity}</span>
  </div>;
}

export default function RegistrationPage() {
  const client = useAuthenticatedApi();
  const api = useMemo(() => new RegistrationApi(client), [client]);
  const [context, setContext] = useState<RegistrationContext | null>(null);
  const [offerings, setOfferings] = useState<RegistrationSection[]>([]);
  const [cart, setCart] = useState<RegistrationSection[]>([]);
  const [preview, setPreview] = useState<RegistrationPreview | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const messageRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    setLoading(true); setMessage(null);
    try {
      const [nextContext, nextOfferings] = await Promise.all([api.context(), api.offerings()]);
      setContext(nextContext); setOfferings(nextOfferings);
    } catch { setMessage({ kind: "error", text: "تعذر تحميل بيانات التسجيل من الجامعة الافتراضية." }); }
    finally { setLoading(false); }
  }, [api]);

  useEffect(() => {
    let active = true;
    Promise.all([api.context(), api.offerings()])
      .then(([nextContext, nextOfferings]) => {
        if (!active) return;
        setContext(nextContext); setOfferings(nextOfferings);
      })
      .catch(() => { if (active) setMessage({ kind: "error", text: "تعذر تحميل بيانات التسجيل من الجامعة الافتراضية." }); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [api]);
  useEffect(() => { if (message) messageRef.current?.focus(); }, [message]);

  const filtered = offerings.filter((item) => {
    const needle = query.trim().toLowerCase();
    return !needle || item.courseCode.toLowerCase().includes(needle) || item.courseName.toLowerCase().includes(needle);
  });
  const cartCredits = cart.reduce((sum, item) => sum + item.credits, 0);

  const add = (section: RegistrationSection) => {
    setPreview(null); setMessage(null);
    setCart((items) => items.some((item) => item.id === section.id || item.courseCode === section.courseCode) ? items : [...items, section]);
  };

  const validate = async () => {
    setBusy(true); setMessage(null);
    try { setPreview(await api.preview(cart.map((item) => item.id))); }
    catch { setMessage({ kind: "error", text: "تعذر تنفيذ المعاينة الرسمية. لم يتم تغيير التسجيل." }); }
    finally { setBusy(false); }
  };

  const register = async () => {
    if (!preview?.canRegister) return;
    setBusy(true); setMessage(null);
    try {
      const result = await api.register(cart.map((item) => item.id), idempotencyKey("register"));
      if (!result.success) throw new Error("rejected");
      setCart([]); setPreview(null); await load();
      setMessage({ kind: "success", text: "أكدت الجامعة الافتراضية التسجيل وتم تحديث جدولك." });
    } catch { setMessage({ kind: "error", text: "رفضت الجامعة عملية التسجيل أو تعذر إتمامها. لم نعرض نجاحاً غير مؤكد." }); }
    finally { setBusy(false); }
  };

  const drop = async (section: RegistrationSection) => {
    if (!window.confirm(`تأكيد إسقاط ${section.courseCode} — ${section.courseName}؟`)) return;
    setBusy(true); setMessage(null);
    try {
      const result = await api.drop(section.id, idempotencyKey("drop"));
      if (!result.success) throw new Error("rejected");
      await load(); setMessage({ kind: "success", text: "أكدت الجامعة الافتراضية إسقاط المادة وتحرير المقعد." });
    } catch { setMessage({ kind: "error", text: "تعذر إسقاط المادة. بقي تسجيلك دون تغيير." }); }
    finally { setBusy(false); }
  };

  return <div className="space-y-6" dir="rtl">
    <header className="rounded-3xl border border-border bg-surface p-5 shadow-xs sm:p-7">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div><p className="text-xs font-bold text-accent">تسجيل فعلي عبر النظام الجامعي الافتراضي</p><h1 className="mt-1 text-2xl font-bold text-foreground">تسجيل المواد</h1><p className="mt-1 text-sm text-muted">المعاينة والقرار النهائي حتميان؛ لا يُعد أي مقرر مسجلاً قبل تأكيد الجامعة.</p></div>
        {context ? <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div className="rounded-2xl bg-surface-muted p-3"><span className="block text-xs text-muted">الفصل النشط</span><strong className="text-sm text-foreground">{context.term.label}</strong></div>
          <div className="rounded-2xl bg-surface-muted p-3"><span className="block text-xs text-muted">حالة التسجيل</span><strong className={context.registrationOpen ? "text-emerald-700" : "text-red-700"}>{context.registrationOpen ? "مفتوح" : "مغلق"}</strong></div>
          <div className="col-span-2 rounded-2xl bg-surface-muted p-3 sm:col-span-1"><span className="block text-xs text-muted">الساعات</span><strong>{context.registeredCredits} / {context.policy.maxCreditHours}</strong></div>
        </div> : null}
      </div>
    </header>

    {message ? <div ref={messageRef} tabIndex={-1} role={message.kind === "error" ? "alert" : "status"} className={`rounded-2xl border p-4 text-sm font-semibold ${message.kind === "error" ? "border-red-200 bg-red-50 text-red-900" : "border-emerald-200 bg-emerald-50 text-emerald-900"}`}>{message.text}</div> : null}
    {loading ? <div className="rounded-3xl border border-border bg-surface p-8 text-center text-sm text-muted">جاري تحميل سياق التسجيل الرسمي…</div> : null}

    {!loading && context ? <>
      <section aria-labelledby="schedule-title" className="rounded-3xl border border-border bg-surface p-5 shadow-xs sm:p-7">
        <div className="mb-4 flex items-center justify-between"><div><h2 id="schedule-title" className="text-lg font-bold">جدولي المسجل</h2><p className="text-xs text-muted">{context.currentEnrollments.length} مواد، {context.registeredCredits} ساعة</p></div><CalendarDays className="h-6 w-6 text-accent" aria-hidden="true" /></div>
        {context.currentEnrollments.length ? <div className="grid gap-3 lg:grid-cols-2">{context.currentEnrollments.map((section) => <article key={section.id} className="rounded-2xl border border-border p-4"><div className="mb-3 flex items-start justify-between gap-3"><div><strong className="font-mono text-sm" dir="ltr">{section.courseCode}</strong><h3 className="font-bold">{section.courseName}</h3><p className="text-xs text-muted">الشعبة {section.sectionNumber} · {section.credits} ساعات</p></div><button type="button" disabled={busy || !context.registrationOpen} onClick={() => void drop(section)} aria-label={`إسقاط ${section.courseName}`} className="inline-flex min-h-11 items-center gap-1.5 rounded-xl border border-red-200 px-3 text-xs font-bold text-red-700 hover:bg-red-50 disabled:opacity-50"><Trash2 className="h-4 w-4" aria-hidden="true" />إسقاط</button></div><SectionFacts section={section} /></article>)}</div> : <p className="rounded-2xl border border-dashed border-border p-6 text-center text-sm text-muted">لا توجد مواد مسجلة في الفصل النشط.</p>}
      </section>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section aria-labelledby="offerings-title" className="rounded-3xl border border-border bg-surface p-5 shadow-xs sm:p-7">
          <div className="mb-4"><h2 id="offerings-title" className="text-lg font-bold">الشعب المتاحة لخُطتك</h2><p className="text-xs text-muted">تُعرض شعب الخطة المركبة {context.planKey} فقط.</p></div>
          <label className="relative mb-5 block"><span className="sr-only">البحث في المواد والشعب</span><Search className="absolute right-3 top-3 h-5 w-5 text-muted" aria-hidden="true" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="ابحث بالرمز أو اسم المادة" className="min-h-11 w-full rounded-2xl border border-border bg-background pr-11 pl-4 text-sm outline-hidden focus:border-accent focus:ring-2 focus:ring-accent/20" /></label>
          <div className="space-y-3">{filtered.map((section) => { const state = section.eligibility?.state ?? "NOT_ELIGIBLE"; const selected = cart.some((item) => item.id === section.id); return <article key={section.id} className="rounded-2xl border border-border p-4"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><strong className="font-mono text-sm" dir="ltr">{section.courseCode}</strong><span className={`rounded-full border px-2.5 py-1 text-[11px] font-bold ${stateStyle[state]}`}>{state === "ELIGIBLE" ? "مؤهل" : state === "REVIEW_REQUIRED" ? "تتطلب مراجعة أكاديمية" : "غير مؤهل"}</span></div><h3 className="mt-1 font-bold">{section.courseName}</h3><p className="text-xs text-muted">{section.requirementGroup || "متطلب الخطة"} · الشعبة {section.sectionNumber} · {section.credits} ساعات</p></div><button type="button" onClick={() => add(section)} disabled={selected || state !== "ELIGIBLE" || section.enrolled >= section.capacity || !context.registrationOpen} className="min-h-11 rounded-xl bg-accent px-4 text-xs font-bold text-accent-text hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-45">{selected ? "في السلة" : "إضافة للسلة"}</button></div><div className="mt-3"><SectionFacts section={section} /></div>{section.eligibility?.reason ? <p className="mt-3 rounded-xl bg-surface-muted p-3 text-xs text-muted">{section.eligibility.reason}</p> : null}</article>; })}</div>
        </section>

        <aside aria-labelledby="cart-title" className="rounded-3xl border border-border bg-surface p-5 shadow-xs xl:sticky xl:top-6">
          <h2 id="cart-title" className="text-lg font-bold">سلة التسجيل</h2><p className="text-xs text-muted">{cart.length} مواد · {cartCredits} ساعات إضافية</p>
          <div className="my-4 space-y-2">{cart.length ? cart.map((section) => <div key={section.id} className="flex items-center justify-between rounded-xl bg-surface-muted p-3"><div><strong className="font-mono text-xs" dir="ltr">{section.courseCode}</strong><p className="text-xs">شعبة {section.sectionNumber}</p></div><button type="button" onClick={() => { setCart((items) => items.filter((item) => item.id !== section.id)); setPreview(null); }} className="min-h-11 min-w-11 rounded-lg text-rose-400 hover:bg-rose-950/50" aria-label={`إزالة ${section.courseName} من السلة`}><Trash2 className="mx-auto h-4 w-4" aria-hidden="true" /></button></div>) : <p className="rounded-xl border border-dashed border-border p-4 text-center text-xs text-muted">أضف شعبة محددة لبدء المعاينة.</p>}</div>
          <button type="button" onClick={() => void validate()} disabled={!cart.length || busy} className="min-h-11 w-full rounded-xl border border-accent bg-accent-soft text-sm font-bold text-accent hover:bg-accent/15 disabled:opacity-50">{busy ? "جاري التحقق…" : "معاينة رسمية"}</button>
          {preview ? <div className="mt-4 border-t border-border pt-4"><div className="flex items-center gap-2">{preview.canRegister ? <CheckCircle2 className="h-5 w-5 text-emerald-700" aria-hidden="true" /> : <AlertTriangle className="h-5 w-5 text-amber-700" aria-hidden="true" />}<strong className="text-sm">{preview.canRegister ? "المعاينة صالحة للتأكيد" : "توجد موانع تسجيل"}</strong></div><p className="mt-2 text-xs text-muted">الحمل الناتج: {preview.resultingCredits} / {preview.maxCredits} ساعة</p>{preview.issues.length ? <ul className="mt-3 space-y-2" role="alert">{preview.issues.map((issue, index) => <li key={`${issue.code}-${index}`} className="rounded-xl border border-amber-500/40 bg-amber-950/60 p-3 text-xs text-amber-200"><strong>{issue.code}</strong><br />{issue.messageAr}</li>)}</ul> : null}<button type="button" onClick={() => void register()} disabled={!preview.canRegister || busy} className="mt-4 min-h-11 w-full rounded-xl bg-accent px-4 text-sm font-bold text-accent-text hover:bg-accent-hover disabled:opacity-50">تأكيد التسجيل لدى الجامعة</button></div> : null}
        </aside>
      </div>
    </> : null}
  </div>;
}
