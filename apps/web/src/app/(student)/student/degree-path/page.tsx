"use client";

import { useRef, useState } from "react";
import { useAuth } from "@/auth/auth-provider";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import { useCourseIdentities } from "@/lib/api/use-course-identities";
import { AcademicGraphExplanation } from "@/components/academic/AcademicGraphExplanation";
import { PathMap } from "@/components/ui/PathMap";
import { Button, FriendlyState } from "@/components/ui/DesignSystem";
import { Compass, Printer } from "lucide-react";
import { LoadingSkeletonCard } from "@/components/ui/LoadingSkeleton";
import { AcademicAnalysisProgress, type ProgressStep } from "@/components/academic/AcademicAnalysisProgress";
import type {
  AcademicExplanationGraph,
  AcademicProgressResponse,
  CreditComparisonResponse,
  CreditTimelineRequest,
  DegreePathOptionResponse,
  DegreePathRequest,
  DegreePathResponse,
} from "@/lib/api/student-types";

const STRATEGIES = {
  FASTEST: { name: "الأسرع", reason: "حمل أعلى لتقليل عدد الفصول المتوقعة ضمن حدود التخطيط." },
  BALANCED: { name: "المتوازن", reason: "يوزّع العبء بصورة متوازنة وقد يستفيد من الفصل الصيفي." },
  LOWER_LOAD: { name: "الأخف", reason: "يخفّض الحمل الفصلي مقابل مدة أطول وأكثر مرونة." },
} as const;

const AUTOMATIC_PATH_REQUEST: DegreePathRequest = {
  max_credit_hours_per_semester: 18,
  max_semesters_ahead: 16,
  max_paths: 3,
};

function remainingReported(progress: AcademicProgressResponse): number | null {
  return progress.reported_earned_credit_hours === null
    ? null
    : Math.max(0, progress.plan_total_required_credits - progress.reported_earned_credit_hours);
}

function termLabel(term: CreditTimelineRequest["start_term"]): string {
  if (term === "SUMMER") return "صيفي";
  return term === "FIRST_SEMESTER" ? "الأول" : "الثاني";
}

function formatCreditHours(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return Number.isInteger(num) ? num.toString() : num.toFixed(1).replace(/\.0$/, "");
}

export default function DegreePathPage() {
  const auth = useAuth();
  const client = useAuthenticatedApi();
  const identities = useCourseIdentities(auth.isAuthenticated);
  const [result, setResult] = useState<DegreePathResponse | null>(null);
  const [progress, setProgress] = useState<AcademicProgressResponse | null>(null);
  const [comparison, setComparison] = useState<CreditComparisonResponse | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [graph, setGraph] = useState<AcademicExplanationGraph | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState(false);
  const INITIAL_DEGREE_PATH_STEPS: ProgressStep[] = [
    { id: "audit_credits", title: "مطابقة سجل الساعات المعتمدة ومتطلبات الخطة", description: "فحص الساعات المتبقية وفق سجل الجامعة والحدود الأكاديمية", status: "ACTIVE" },
    { id: "critical_path", title: "تحليل المسارات الحرجة وسلاسل المتطلبات", description: "فحص شجرة المواد الإلزامية والمتطلبات السابقة المتتابعة", status: "WAITING" },
    { id: "scenarios", title: "توليد استراتيجيات التخرج والمقارنة الزمنية", description: "احتساب خطط المسارات: الأسرع، المتوازن، والأخف", status: "WAITING" },
    { id: "journey_map", title: "تجهيز خريطة التخرج والتفسير البياني", description: "بناء المحطات الفصلية وشجرة التعليل الحتمي", status: "WAITING" },
  ];
  const [pathSteps, setPathSteps] = useState<ProgressStep[]>(INITIAL_DEGREE_PATH_STEPS);
  const requestId = useRef(0);

  const loadGraph = async () => {
    setGraphLoading(true);
    setGraphError(false);
    try {
      setGraph(await new StudentApiService(client).createDegreePathGraph(AUTOMATIC_PATH_REQUEST));
      setPathSteps([
        { ...INITIAL_DEGREE_PATH_STEPS[0], status: "COMPLETE" },
        { ...INITIAL_DEGREE_PATH_STEPS[1], status: "COMPLETE" },
        { ...INITIAL_DEGREE_PATH_STEPS[2], status: "COMPLETE" },
        { ...INITIAL_DEGREE_PATH_STEPS[3], status: "COMPLETE" },
      ]);
    } catch {
      setGraphError(true);
    } finally {
      setGraphLoading(false);
    }
  };

  const handleGeneratePath = async () => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setErrorMessage(null);
    setResult(null);
    setComparison(null);
    setGraph(null);
    setGraphError(false);
    setPathSteps(INITIAL_DEGREE_PATH_STEPS);
    const signal = AbortSignal.timeout(60_000);
    const now = new Date();
    try {
      const api = new StudentApiService(client);
      setPathSteps([
        { ...INITIAL_DEGREE_PATH_STEPS[0], status: "COMPLETE" },
        { ...INITIAL_DEGREE_PATH_STEPS[1], status: "ACTIVE" },
        { ...INITIAL_DEGREE_PATH_STEPS[2], status: "WAITING" },
        { ...INITIAL_DEGREE_PATH_STEPS[3], status: "WAITING" },
      ]);
      const [paths, academicProgress, scenarios] = await Promise.all([
        api.createDegreePaths(AUTOMATIC_PATH_REQUEST, signal),
        api.getProgress(),
        api.compareCreditTimelines({ start_year: now.getFullYear(), start_term: "FIRST_SEMESTER" }),
      ]);
      if (currentRequest !== requestId.current) return;
      setResult(paths);
      setProgress(academicProgress);
      setComparison(scenarios);
      setSelectedIndex(0);
      setPathSteps([
        { ...INITIAL_DEGREE_PATH_STEPS[0], status: "COMPLETE" },
        { ...INITIAL_DEGREE_PATH_STEPS[1], status: "COMPLETE" },
        { ...INITIAL_DEGREE_PATH_STEPS[2], status: "COMPLETE" },
        { ...INITIAL_DEGREE_PATH_STEPS[3], status: "ACTIVE" },
      ]);
      void loadGraph();
    } catch {
      if (currentRequest !== requestId.current) return;
      setErrorMessage(signal.aborted
        ? "استغرق إنشاء مسارات التخرج وقتًا أطول من المتوقع. حاول مرة أخرى."
        : "تعذر إنشاء مسارات التخرج الآن. حاول مرة أخرى.");
      setPathSteps((prev) =>
        prev.map((step) =>
          step.status === "ACTIVE" ? { ...step, status: "ERROR" } : step
        )
      );
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  };

  const selectedPath: DegreePathOptionResponse | null = result?.paths[selectedIndex] ?? null;
  const reportedRemaining = progress ? remainingReported(progress) : null;
  const selectedScenario = comparison ? comparison.scenarios[selectedIndex] : null;
  const selectedScenarioPlannedCredits = selectedScenario
    ? selectedScenario.timeline.terms.reduce((sum, term) => sum + Number(term.planned_credits), 0)
    : 0;
  const selectedScenarioStudyTerms = selectedScenario
    ? (selectedScenario.scheduled_term_count ?? selectedScenario.total_modeled_terms)
    : 0;

  return <div className="space-y-8 degree-page">
    <div className="page-heading">
      <span className="eyebrow">ثلاث طرق واضحة نحو هدفك</span>
      <h1>مسار التخرج</h1>
      <p className="text-sm text-muted mt-3">مرشدي يحسب تلقائيًا الأسرع والمتوازن والأخف، مع إبقاء قرارات المتطلبات والتسلسل للمحركات الأكاديمية الحتمية.</p>
    </div>
    <div className="engraved p-6 flex items-center justify-between gap-5 flex-wrap">
      <div><h2 className="text-lg">جاهز لرؤية الخيارات؟</h2><p className="text-xs text-muted mt-2">لا حاجة لاختيار عدد الفصول أو المسارات.</p></div>
      <Button type="button" disabled={loading} onClick={() => void handleGeneratePath()}>
        <Compass size={18}/>{loading ? "جارٍ رسم 3 مسارات…" : "ارسم المسار"}
      </Button>
    </div>
    {errorMessage && <FriendlyState error title={errorMessage} onRetry={() => void handleGeneratePath()}/>}
    {loading && (
      <div className="space-y-6">
        <AcademicAnalysisProgress
          title="جاري رسم مسارات التخرج الحتمية"
          subtitle="يقوم المحرك بمطابقة الساعات المتبقية، تحليل المسار الحرج، وتوليد السيناريوهات المعتمدة"
          steps={pathSteps}
        />
        <LoadingSkeletonCard className="min-h-48"/>
      </div>
    )}
    {!loading && result && comparison && progress && <>
      <div className="strategy-grid" aria-label="خيارات مسار التخرج">
        {comparison.scenarios.map((scenario, index) => {
          const strategy = STRATEGIES[scenario.mode];
          const path = result.paths[index];
          const plannedCredits = scenario.timeline.terms.reduce((sum, term) => sum + Number(term.planned_credits), 0);
          const studyTerms = scenario.scheduled_term_count ?? scenario.total_modeled_terms;
          return <button key={scenario.mode} type="button" className="strategy-card engraved"
            data-selected={selectedIndex === index} aria-pressed={selectedIndex === index}
            onClick={() => setSelectedIndex(index)}>
            <span className="eyebrow">الخيار {index + 1}</span><h2>{strategy.name}</h2>
            <strong>{studyTerms}</strong><span> فصول متوقعة</span>
            <div className="strategy-loads">{scenario.timeline.terms.map((term, termIndex) =>
              <span key={`${term.academic_year}-${term.term}-${termIndex}`} data-summer={term.term === "SUMMER"}>
                {termLabel(term.term)} · <span dir="ltr">{formatCreditHours(term.planned_credits)}</span> ساعة
              </span>)}</div>
            <dl>
              <div><dt>إجمالي العبء الموزع</dt><dd dir="ltr">{formatCreditHours(plannedCredits)}</dd></div>
              <div><dt>المتبقي حسب سجل الجامعة</dt><dd dir="ltr">{reportedRemaining !== null ? formatCreditHours(reportedRemaining) : "غير متاح"}</dd></div>
            </dl>
            <p>{strategy.reason}</p>
            {!path && <small>لم ينتج المحرك مسار مقررات كاملًا لهذا الخيار؛ يظهر تقدير الساعات فقط.</small>}
          </button>;
        })}
      </div>
      {reportedRemaining !== null && reportedRemaining !== result.initial_remaining_credits &&
        <details className="engraved p-5">
          <summary>تفاصيل نموذج الخطة</summary>
          <p className="text-xs text-muted mt-3">
            نموذج مرشدي يحتسب {result.initial_remaining_credits} ساعة ضمن متطلبات الخطة بسبب اختلاف وزن بعض المقررات التاريخية، بينما سجل الجامعة الرسمي يثبت أن المتبقي للتخرج هو {reportedRemaining} ساعة. نستخدم النموذج الحتمي لتسلسل المقررات والمتطلبات فقط.
          </p>
        </details>}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-xl">بديل تسلسل المقررات {selectedIndex + 1}{selectedScenario ? ` (${STRATEGIES[selectedScenario.mode].name})` : ""}</h2>
          <p className="text-xs text-muted mt-2">بدائل المقررات مرتبة من المحرك الحتمي بسقف 18 ساعة، وهي منفصلة عن توزيع العبء الزمني لخيار {selectedScenario ? STRATEGIES[selectedScenario.mode].name : ""} أعلاه.</p>
        </div>
        <button className="button-secondary" onClick={() => window.print()}><Printer size={16}/>تصدير PDF</button>
      </div>
      {selectedPath ? <>
        <div className="journey-kpis">
          <div className="engraved">
            <strong dir="ltr">{selectedScenarioStudyTerms}</strong>
            <span>الفصول المخططة</span>
          </div>
          <div className="engraved">
            <strong dir="ltr">{reportedRemaining !== null ? formatCreditHours(reportedRemaining) : "—"}</strong>
            <span>الساعات المتبقية حسب سجل الجامعة</span>
          </div>
          <div className="engraved">
            <strong dir="ltr">{formatCreditHours(selectedScenarioPlannedCredits)}</strong>
            <span>الساعات الموزعة في السيناريو</span>
          </div>
        </div>
        <PathMap key={selectedPath.rank} stations={selectedPath.semesters.map((semester) => ({
          id: String(semester.semester_index), title: `الفصل ${semester.semester_index}`,
          hours: semester.plan_option.total_credit_hours,
          courses: semester.plan_option.courses.map((course) => ({
            code: course.course_code, name: course.course_name_ar, hours: course.credit_hours,
          })),
        }))}/>
        {selectedPath.status !== "MODELED_COMPLETE" && <p className="text-xs text-copper">هذا أفضل مسار صالح وجده المحرك ضمن الحدود الآمنة، وقد يكون جزئيًا.</p>}
        {reportedRemaining !== null && selectedPath.total_planned_credits !== reportedRemaining && (
          <div className="p-3 rounded-lg border border-gold/30 bg-gold/5 text-xs text-muted">
            ملاحظة توضيحية: يعرض هذا المسار تسلسلًا حتميًا لـ <span dir="ltr">{formatCreditHours(selectedPath.total_planned_credits)}</span> ساعة من المقررات المؤهلة حاليًا، بينما الساعات الرسمية المتبقية للتخرج وفق سجل الجامعة هي <span dir="ltr">{formatCreditHours(reportedRemaining)}</span> ساعة.
          </div>
        )}
        <details className="engraved p-5">
          <summary>تفاصيل نموذج تسلسل المواد ({formatCreditHours(selectedPath.total_planned_credits)} ساعة مقررات)</summary>
          <div className="space-y-2 text-xs text-muted mt-3">
            <p>
              وزّع محرك تسلسل المقررات الحتمي <strong dir="ltr">{formatCreditHours(selectedPath.total_planned_credits)}</strong> ساعة موزعة على {selectedPath.semester_count} فصول بناءً على شبكة المتطلبات السابقة وشروط فتح المواد.
            </p>
            {reportedRemaining !== null && reportedRemaining !== selectedPath.total_planned_credits && (
              <p>
                يختلف هذا الرقم (<span dir="ltr">{formatCreditHours(selectedPath.total_planned_credits)}</span> ساعة مقررات مجدولة) عن العبء الأكاديمي الرسمي المتبقي للتخرج (<span dir="ltr">{formatCreditHours(reportedRemaining)}</span> ساعة) بسبب حزم الساعات المعتمدة للمقررات واشتراطات السقف الفصلي. الساعات الرسمية المعتمدة هي <span dir="ltr">{formatCreditHours(reportedRemaining)}</span> ساعة.
              </p>
            )}
            <p>
              المتطلبات المتبقية في نموذج الخطة بعد هذا البديل: <strong dir="ltr">{formatCreditHours(selectedPath.final_remaining_plan_credits)}</strong> ساعة.
            </p>
          </div>
        </details>
        <details className="engraved p-5"><summary>لماذا هذا التسلسل؟</summary>
          <AcademicGraphExplanation graph={graph} focusId={`degree-path:${selectedPath.rank}`}
            identities={identities} loading={graphLoading} error={graphError} onRetry={() => void loadGraph()}/>
        </details>
      </> : <FriendlyState title="يتوفر تقدير ساعات لهذا الخيار، لكن لم يتوفر مسار مقررات حتمي كامل."/>}
      <p className="text-xs text-muted">هذه سيناريوهات تخطيطية وليست موعد تخرج أو موافقة تسجيل معتمدة. لا تُنشأ مقررات وهمية، وقد تؤثر الإتاحة والسعة والنجاح الفعلي في المدة.</p>
    </>}
    {!loading && !errorMessage && !result && <FriendlyState title="اضغط «ارسم المسار» للحصول على 3 خيارات تلقائية"/>}
  </div>;
}
