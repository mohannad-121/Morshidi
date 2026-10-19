"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { AlertTriangle, ArrowDownLeft, BookOpenCheck, CheckCircle2, CircleGauge,
  Clock3, GraduationCap, RefreshCw, ShieldCheck, Sparkles, UsersRound } from "lucide-react";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { InstitutionalAnalyticsApi, type CourseMetric, type Dashboard, type Metric,
  type Simulation } from "@/lib/api/institutional-analytics";

export type InstitutionalView = "overview" | "programs" | "courses" | "bottlenecks" |
  "capacity" | "progress" | "review" | "what-if";

const number = new Intl.NumberFormat("ar-JO", { maximumFractionDigits: 1 });
const statusArabic: Record<string, string> = {
  AVAILABLE: "متاح", INSUFFICIENT_DATA: "بيانات غير كافية", SUPPRESSED: "محجوب للخصوصية",
  UNAVAILABLE: "غير متاح", UNDER_CAPACITY: "طاقة فائضة", HEALTHY: "متوازن",
  NEAR_CAPACITY: "قريب من الامتلاء", OVER_DEMAND: "الطلب يتجاوز الطاقة",
  NONE: "لا يوجد", WATCH: "للمراقبة", HIGH: "مرتفع", CRITICAL: "حرج",
};

function value(metric: Metric) {
  if (metric.status !== "AVAILABLE" || metric.value === null) return statusArabic[metric.status];
  return number.format(metric.value);
}

function Kpi({ label, metric, icon: Icon }: { label: string; metric: Metric;
  icon: typeof UsersRound }) {
  return <article className="surface-raised rounded-2xl border border-border p-4 shadow-sm">
    <div className="flex items-start justify-between gap-3">
      <div><p className="text-xs text-muted">{label}</p><strong className="mt-2 block text-2xl font-semibold tabular-nums">{value(metric)}</strong></div>
      <span className="grid size-10 place-items-center rounded-xl border border-amber-500/20 bg-amber-500/10 text-amber-300"><Icon className="size-5" aria-hidden="true"/></span>
    </div>
    {metric.reason_codes.length > 0 && <p className="mt-3 text-[11px] text-muted">{metric.reason_codes.join(" · ")}</p>}
  </article>;
}

function StateBadge({ state }: { state: string }) {
  const danger = state === "OVER_DEMAND" || state === "CRITICAL" || state === "REVIEW_REQUIRED";
  const warning = state === "NEAR_CAPACITY" || state === "HIGH" || state === "WATCH";
  return <span className={`inline-flex whitespace-nowrap rounded-full border px-2.5 py-1 text-[11px] font-semibold ${danger ? "border-red-400/25 bg-red-400/10 text-red-200" : warning ? "border-amber-400/25 bg-amber-400/10 text-amber-200" : "border-emerald-400/20 bg-emerald-400/10 text-emerald-200"}`}>
    {statusArabic[state] ?? state}
  </span>;
}

function CoursesTable({ courses }: { courses: CourseMetric[] }) {
  return <div className="overflow-x-auto rounded-2xl border border-border bg-surface">
    <table className="w-full min-w-[980px] text-right text-sm">
      <thead><tr><th className="p-3">المادة</th><th className="p-3">المؤهلون</th><th className="p-3">الحاجة المخططة</th><th className="p-3">الطلب المتوقع</th><th className="p-3">المقاعد</th><th className="p-3">الفجوة</th><th className="p-3">الطاقة</th><th className="p-3">الاختناق</th><th className="p-3">البرامج</th></tr></thead>
      <tbody>{courses.map(course => <tr key={course.course_code} className="border-t border-border align-top">
        <td className="p-3"><strong dir="ltr" className="font-mono text-amber-200">{course.course_code}</strong><span className="mt-1 block max-w-56">{course.name_ar ?? course.name_en ?? "—"}</span><small className="text-muted">ثقة الإسقاط: {statusArabic[course.projection_confidence] ?? course.projection_confidence}</small></td>
        <td className="p-3 tabular-nums">{value(course.eligible_not_registered)}</td>
        <td className="p-3 tabular-nums">{value(course.planned_need)}</td>
        <td className="p-3"><strong className="tabular-nums">{value(course.projected_demand)}</strong><small className="mt-1 block text-muted">مسار قريب {course.projection_components.degree_path_upcoming}</small></td>
        <td className="p-3 tabular-nums">{value(course.offered_seats)}</td>
        <td className="p-3 tabular-nums">{value(course.demand_capacity_gap)}</td>
        <td className="p-3"><StateBadge state={course.capacity_state}/></td>
        <td className="p-3"><div className="flex items-center gap-2"><strong className="tabular-nums">{course.bottleneck_score}</strong><StateBadge state={course.bottleneck_level}/></div><small className="mt-1 block text-muted">{course.downstream_course_count} مواد لاحقة</small></td>
        <td className="p-3"><span>{course.programs.length}</span><small className="mt-1 block max-w-52 text-muted">{course.programs.slice(0, 3).join("، ")}{course.programs.length > 3 ? "…" : ""}</small></td>
      </tr>)}</tbody>
    </table>
  </div>;
}

export function InstitutionalDashboard({ initialView = "overview" }: { initialView?: InstitutionalView }) {
  const client = useAuthenticatedApi();
  const api = useMemo(() => new InstitutionalAnalyticsApi(client), [client]);
  const [data, setData] = useState<Dashboard | null>(null);
  const [options, setOptions] = useState<Dashboard | null>(null);
  const [university, setUniversity] = useState("");
  const [term, setTerm] = useState("CURRENT");
  const [faculty, setFaculty] = useState("");
  const [major, setMajor] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<"denied" | "unavailable" | null>(null);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [simulationCourse, setSimulationCourse] = useState("");
  const [seats, setSeats] = useState(30);

  async function load(scope: string, nextTerm = term, nextFaculty = faculty, nextMajor = major) {
    setBusy(true); setError(null);
    try {
      const dashboard = await api.dashboard({ universityId: scope, termKey: nextTerm,
        faculty: nextFaculty || undefined, major: nextMajor || undefined });
      setData(dashboard); setOptions(current => current ?? dashboard);
      setSimulationCourse(current => current || dashboard.courses[0]?.course_code || "");
    } catch { setError("unavailable"); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    let live = true;
    void api.access().then(scopes => {
      if (!live) return;
      const id = scopes[0]?.university_id;
      if (!id) { setError("denied"); setBusy(false); return; }
      setUniversity(id);
      return load(id, "CURRENT", "", "");
    }).catch(() => { if (live) { setError("denied"); setBusy(false); } });
    return () => { live = false; };
    // API identity is stable for the authenticated session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  const faculties = [...new Map((options?.programs ?? []).map(item => [item.faculty_code, item.faculty_name_ar])).entries()];
  const majors = (options?.programs ?? []).filter(item => !faculty || item.faculty_code === faculty);
  const visibleCourses = initialView === "bottlenecks" ? (data?.courses ?? []).filter(item => item.bottleneck_level === "HIGH" || item.bottleneck_level === "CRITICAL")
    : initialView === "capacity" ? (data?.courses ?? []).filter(item => item.capacity_state === "NEAR_CAPACITY" || item.capacity_state === "OVER_DEMAND")
    : data?.courses ?? [];

  async function runSimulation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSimulation(null);
    try { setSimulation(await api.simulate({ university_id: university, term_key: term,
      course_code: simulationCourse, kind: "ADD_SECTION", seats })); }
    catch { setError("unavailable"); }
  }

  return <main className="mx-auto max-w-[1360px] space-y-6 p-4 sm:p-6 lg:p-8">
    <header className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
      <div className="max-w-3xl">
        <span className="inline-flex items-center gap-2 text-xs font-semibold text-amber-300"><Sparkles className="size-4" aria-hidden="true"/> طبقة القرار الأكاديمي المؤسسي</span>
        <h1 className="mt-2 text-balance text-3xl font-bold tracking-tight sm:text-4xl">ما الذي يحدث أكاديميًا، ولماذا؟</h1>
        <p className="mt-2 text-sm leading-7 text-muted">مؤشرات حتمية قابلة للتدقيق عبر البرامج والمواد والتسجيل. لا تُستخدم نماذج اللغة لحساب أي رقم.</p>
      </div>
      {data && <div className="flex flex-wrap items-center gap-2 text-xs"><StateBadge state={data.role_scope}/><span className="rounded-full border border-border px-3 py-1.5 text-muted">إصدار العقد {data.contract_version}</span></div>}
    </header>

    <form onSubmit={event => { event.preventDefault(); void load(university); }} className="surface-raised grid gap-3 rounded-2xl border border-border p-4 sm:grid-cols-2 xl:grid-cols-[1fr_1fr_1fr_auto]" aria-label="مرشحات لوحة الذكاء المؤسسي">
      <label className="grid gap-1.5 text-xs text-muted">الفصل الأكاديمي<input value={term} onChange={event => setTerm(event.target.value)} className="min-h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"/></label>
      <label className="grid gap-1.5 text-xs text-muted">الكلية<select value={faculty} onChange={event => { setFaculty(event.target.value); setMajor(""); }} className="min-h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"><option value="">كل الكليات</option>{faculties.map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label>
      <label className="grid gap-1.5 text-xs text-muted">التخصص<select value={major} onChange={event => setMajor(event.target.value)} className="min-h-11 rounded-xl border border-border bg-background px-3 text-sm text-foreground"><option value="">كل التخصصات</option>{majors.map(item => <option key={item.plan_key} value={item.major_code}>{item.major_name_ar}</option>)}</select></label>
      <button disabled={busy || !university} className="button-primary min-h-11 self-end rounded-xl px-5 font-semibold disabled:opacity-50"><RefreshCw className={`ml-2 inline size-4 ${busy ? "animate-spin motion-reduce:animate-none" : ""}`} aria-hidden="true"/>تحديث</button>
    </form>

    {busy && !data && <div role="status" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="جارٍ تحميل المؤشرات">{Array.from({ length: 8 }, (_, index) => <div key={index} className="loading-skeleton h-28 rounded-2xl border border-border"/>)}</div>}
    {error === "denied" && <section role="alert" className="friendly-state rounded-2xl border p-8 text-center"><ShieldCheck className="mx-auto size-10 text-amber-300"/><h2 className="mt-3 text-xl font-bold">هذه المساحة مخصصة للمخولين</h2><p className="mt-2 text-muted">يلزم دور محلل مؤسسي فعال أو عضوية مرشد أكاديمي مع تعيينات صريحة.</p></section>}
    {error === "unavailable" && <p role="alert" className="rounded-xl border border-red-400/25 bg-red-400/10 p-4 text-red-100">تعذر تحميل البيانات المؤسسية. لم تُستبدل القيم المفقودة بأصفار.</p>}

    {data && <>
      {initialView === "overview" && <>
        <section aria-label="المؤشرات الرئيسية" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Kpi label="الطلبة النشطون" metric={data.overview.total_active_students} icon={UsersRound}/>
          <Kpi label="التسجيلات الحالية" metric={data.overview.current_registrations} icon={BookOpenCheck}/>
          <Kpi label="فرص المواد المؤهلة" metric={data.overview.eligible_course_opportunities} icon={CheckCircle2}/>
          <Kpi label="محجوبون بمتطلبات سابقة" metric={data.overview.blocked_by_prerequisite} icon={ArrowDownLeft}/>
          <Kpi label="قواعد تتطلب مراجعة" metric={data.overview.review_required} icon={AlertTriangle}/>
          <Kpi label="مواد تحت ضغط طاقة" metric={data.overview.capacity_pressure_courses} icon={CircleGauge}/>
          <Kpi label="اختناقات أكاديمية" metric={data.overview.academic_bottlenecks} icon={Clock3}/>
          <Kpi label="قريبون من التخرج" metric={data.overview.approaching_graduation} icon={GraduationCap}/>
        </section>
        <section className="grid gap-4 xl:grid-cols-2">
          <article className="surface-raised rounded-2xl border border-border p-5"><h2 className="text-lg font-bold">أعلى المواد طلبًا</h2><p className="mb-4 mt-1 text-sm text-muted">اتحاد طلابي فريد، وليس جمعًا أعمى للمكونات.</p><CoursesTable courses={data.courses.slice(0, 5)}/></article>
          <article className="surface-raised rounded-2xl border border-border p-5"><h2 className="text-lg font-bold">توزيع الطلبة حسب الكلية</h2><div className="mt-4 space-y-3">{Object.entries(data.overview.students_by_faculty).map(([label, count]) => { const total = Number(data.overview.total_active_students.value || 1); return <div key={label}><div className="mb-1 flex justify-between text-sm"><span>{label}</span><strong>{count}</strong></div><div className="progress-track h-2 overflow-hidden rounded-full"><div className="progress-fill h-full rounded-full" style={{ width: `${Math.min(100, count / total * 100)}%` }}/></div></div>; })}</div></article>
        </section>
      </>}

      {(initialView === "courses" || initialView === "bottlenecks" || initialView === "capacity") && <section className="space-y-4"><div><h2 className="text-2xl font-bold">{initialView === "bottlenecks" ? "الاختناقات الأكاديمية" : initialView === "capacity" ? "ضغط الطاقة الاستيعابية" : "ذكاء المواد والطلب"}</h2><p className="mt-1 text-sm text-muted">كل قيمة مرتبطة بمكوناتها الحتمية وحالة مصدرها.</p></div>{visibleCourses.length ? <CoursesTable courses={visibleCourses}/> : <p className="empty-state rounded-2xl border p-8 text-center text-muted">لا توجد نتائج مؤكدة ضمن المرشحات الحالية.</p>}</section>}

      {initialView === "programs" && <section className="space-y-4"><h2 className="text-2xl font-bold">البرامج الأكاديمية ({data.programs.length})</h2><div className="overflow-x-auto rounded-2xl border border-border bg-surface"><table className="w-full min-w-[900px] text-right text-sm"><thead><tr><th className="p-3">البرنامج</th><th className="p-3">هوية الخطة</th><th className="p-3">الطلبة</th><th className="p-3">متوسط التقدم</th><th className="p-3">الساعات المكتسبة</th><th className="p-3">مسارات محجوبة</th><th className="p-3">مواد عالية الطلب</th></tr></thead><tbody>{data.programs.map(program => <tr key={program.plan_key} className="border-t border-border"><td className="p-3"><strong>{program.major_name_ar}</strong><small className="block text-muted">{program.faculty_name_ar}</small></td><td className="p-3 font-mono text-xs" dir="ltr">{program.plan_key}</td><td className="p-3">{program.student_count}<small className="block text-muted">{statusArabic[program.data_status]}</small></td><td className="p-3">{program.average_progress_percent === null ? statusArabic[program.data_status] : `${program.average_progress_percent}%`}</td><td className="p-3">{program.average_earned_credits ?? statusArabic[program.data_status]}</td><td className="p-3">{program.blocked_student_count ?? statusArabic[program.data_status]}</td><td className="p-3 font-mono text-xs" dir="ltr">{program.high_demand_courses.join(", ") || "—"}</td></tr>)}</tbody></table></div></section>}

      {initialView === "progress" && <section className="space-y-4"><h2 className="text-2xl font-bold">توزيع التقدم الأكاديمي</h2><div className="grid gap-4 lg:grid-cols-2">{data.programs.map(program => <article key={program.plan_key} className="surface-raised rounded-2xl border border-border p-5"><div className="flex justify-between gap-3"><div><h3 className="font-bold">{program.major_name_ar}</h3><p className="font-mono text-xs text-muted" dir="ltr">{program.plan_key}</p></div><strong>{program.average_progress_percent === null ? statusArabic[program.data_status] : `${program.average_progress_percent}%`}</strong></div><dl className="mt-4 grid grid-cols-5 gap-2 text-center text-xs">{program.progress_distribution.map(band => <div key={band.band} className="rounded-xl border border-border p-2"><dt dir="ltr">{band.band.replace("_", "–")}%</dt><dd className="mt-1 font-bold">{band.student_count ?? "—"}</dd></div>)}</dl></article>)}</div></section>}

      {initialView === "review" && <section className="space-y-4"><div><h2 className="text-2xl font-bold">طابور مراجعة القواعد</h2><p className="mt-1 text-sm text-muted">العلاقات غير المحسومة تُغلق المسار احترازيًا ولا تتحول إلى حواف مفترضة.</p></div>{data.review_queue.length ? <div className="grid gap-3">{data.review_queue.map(item => <article key={item.course_code} className="surface-raised rounded-2xl border border-amber-500/20 p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><strong className="font-mono text-amber-200" dir="ltr">{item.course_code}</strong><p className="mt-1 text-sm text-muted">رموز غير محسومة: {item.unresolved_prerequisite_codes.join("، ") || "لم يحدد المصدر الرمز"}</p></div><StateBadge state="REVIEW_REQUIRED"/></div><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3"><div><dt className="text-muted">الخطط المتأثرة</dt><dd>{item.affected_plans.length}</dd></div><div><dt className="text-muted">الطلبة المتأثرون</dt><dd>{item.affected_student_count ?? "محجوب"}</dd></div><div><dt className="text-muted">السلوك الحالي</dt><dd dir="ltr">{item.system_behavior}</dd></div></dl></article>)}</div> : <p className="empty-state rounded-2xl border p-8 text-center">لا توجد قواعد معلقة ضمن النطاق الحالي.</p>}</section>}

      {initialView === "what-if" && <section className="grid gap-5 xl:grid-cols-[.8fr_1.2fr]"><form onSubmit={runSimulation} className="surface-raised space-y-4 rounded-2xl border border-border p-5"><div><h2 className="text-2xl font-bold">محاكاة إضافة شعبة</h2><p className="mt-1 text-sm text-muted">حساب افتراضي فقط؛ لا ينشئ شعبة ولا يغير التسجيل.</p></div><label className="grid gap-1.5 text-sm">المادة<select required value={simulationCourse} onChange={event => setSimulationCourse(event.target.value)} className="min-h-11 rounded-xl border border-border bg-background px-3">{data.courses.map(course => <option key={course.course_code} value={course.course_code}>{course.course_code} — {course.name_ar}</option>)}</select></label><label className="grid gap-1.5 text-sm">مقاعد الشعبة الافتراضية<input type="number" min={1} max={500} value={seats} onChange={event => setSeats(Number(event.target.value))} className="min-h-11 rounded-xl border border-border bg-background px-3"/></label><button className="button-primary min-h-11 w-full rounded-xl px-4 font-semibold">شغّل المحاكاة</button></form><article className="surface-raised rounded-2xl border border-border p-5" aria-live="polite">{simulation ? <><div className="flex items-center justify-between"><h2 className="text-xl font-bold">الأثر المحسوب</h2><span className="badge badge-warning">SIMULATION ONLY</span></div><dl className="mt-5 grid gap-3 sm:grid-cols-2"><div className="rounded-xl border border-border p-4"><dt className="text-xs text-muted">الطاقة قبل / بعد</dt><dd className="mt-1 text-xl font-bold">{simulation.capacity_before ?? "غير متاح"} ← {simulation.capacity_after ?? "غير متاح"}</dd></div><div className="rounded-xl border border-border p-4"><dt className="text-xs text-muted">فجوة الطلب قبل / بعد</dt><dd className="mt-1 text-xl font-bold">{simulation.demand_gap_before ?? "غير متاح"} ← {simulation.demand_gap_after ?? "غير متاح"}</dd></div><div className="rounded-xl border border-border p-4"><dt className="text-xs text-muted">طلبة يُحتمل خدمتهم حسابيًا</dt><dd className="mt-1 text-xl font-bold">{simulation.estimated_students_helped}</dd></div><div className="rounded-xl border border-border p-4"><dt className="text-xs text-muted">درجة الاختناق قبل / بعد</dt><dd className="mt-1 text-xl font-bold">{simulation.bottleneck_score_before} ← {simulation.bottleneck_score_after}</dd></div></dl><p className="mt-4 text-xs text-muted">{simulation.assumptions.join(" · ")}</p></> : <div className="grid min-h-64 place-items-center text-center text-muted"><div><CircleGauge className="mx-auto mb-3 size-10"/><p>اختر مادة وعدد المقاعد لعرض الأثر قبل وبعد.</p></div></div>}</article></section>}

      <details className="rounded-2xl border border-border bg-surface p-4 text-sm"><summary className="cursor-pointer font-semibold">كيف حُسبت هذه المؤشرات؟</summary><div className="mt-4 grid gap-3 text-muted md:grid-cols-3">{Object.entries(data.methodology).map(([key, explanation]) => <p key={key}><strong className="block text-foreground" dir="ltr">{key}</strong>{explanation}</p>)}</div></details>
    </>}
  </main>;
}
