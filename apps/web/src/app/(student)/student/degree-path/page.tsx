"use client";

import { useRef, useState } from "react";
import { Compass, Printer } from "lucide-react";
import { useAuth } from "@/auth/auth-provider";
import { AcademicAnalysisProgress, type ProgressStep } from "@/components/academic/AcademicAnalysisProgress";
import { AcademicGraphExplanation } from "@/components/academic/AcademicGraphExplanation";
import { Button, FriendlyState } from "@/components/ui/DesignSystem";
import { LoadingSkeletonCard } from "@/components/ui/LoadingSkeleton";
import { PathMap } from "@/components/ui/PathMap";
import { StudentApiService } from "@/lib/api/student-api";
import type {
  DegreePathOptionResponse,
  DegreePathRequest,
  DegreePathResponse,
} from "@/lib/api/student-types";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { useCourseIdentities } from "@/lib/api/use-course-identities";

const AUTOMATIC_PATH_REQUEST: DegreePathRequest = {
  max_credit_hours_per_semester: 18,
  max_semesters_ahead: 16,
  max_paths: 3,
};

const DEGREE_PATH_REQUEST_TIMEOUT_MS = 120_000;

const INITIAL_DEGREE_PATH_STEPS: ProgressStep[] = [
  { id: "audit_credits", title: "مطابقة سجل الساعات المعتمدة ومتطلبات الخطة", description: "فحص الساعات المتبقية وفق سجل الجامعة والحدود الأكاديمية", status: "ACTIVE" },
  { id: "critical_path", title: "تحليل المسارات الحرجة وسلاسل المتطلبات", description: "فحص شجرة المواد الإلزامية والمتطلبات السابقة المتتابعة", status: "WAITING" },
  { id: "scenarios", title: "توليد بدائل مسار التخرج", description: "احتساب بدائل حتمية مختلفة من المحرك الأكاديمي نفسه", status: "WAITING" },
  { id: "journey_map", title: "تجهيز خريطة التخرج والتفسير البياني", description: "بناء المحطات الفصلية من البديل المختار نفسه", status: "WAITING" },
];

function formatCreditHours(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return Number.isInteger(num) ? num.toString() : num.toFixed(1).replace(/\.0$/, "");
}

function statusDescription(path: DegreePathOptionResponse): string {
  return path.status === "MODELED_COMPLETE"
    ? "يستوفي متطلبات الخطة ضمن الفصول المعروضة."
    : "أفضل تسلسل حتمي متاح ضمن القيود الحالية، وقد يحتاج بعض المتطلبات إلى مراجعة.";
}

export default function DegreePathPage() {
  const auth = useAuth();
  const client = useAuthenticatedApi();
  const identities = useCourseIdentities(auth.isAuthenticated);
  const [result, setResult] = useState<DegreePathResponse | null>(null);
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [pathSteps, setPathSteps] = useState<ProgressStep[]>(INITIAL_DEGREE_PATH_STEPS);
  const requestId = useRef(0);

  const handleGeneratePath = async () => {
    const currentRequest = ++requestId.current;
    const signal = AbortSignal.timeout(DEGREE_PATH_REQUEST_TIMEOUT_MS);
    setLoading(true);
    setErrorMessage(null);
    setResult(null);
    setSelectedPathId(null);
    setPathSteps(INITIAL_DEGREE_PATH_STEPS);
    try {
      const paths = await new StudentApiService(client).createDegreePaths(AUTOMATIC_PATH_REQUEST, signal);
      if (currentRequest !== requestId.current) return;
      setResult(paths);
      setSelectedPathId(paths.paths[0]?.path_id ?? null);
      setPathSteps(INITIAL_DEGREE_PATH_STEPS.map((step) => ({ ...step, status: "COMPLETE" })));
    } catch {
      if (currentRequest !== requestId.current) return;
      setErrorMessage(signal.aborted
        ? "استغرق إنشاء مسارات التخرج وقتًا أطول من المتوقع. حاول مرة أخرى."
        : "تعذر إنشاء مسارات التخرج الآن. حاول مرة أخرى.");
      setPathSteps((steps) => steps.map((step) =>
        step.status === "ACTIVE" ? { ...step, status: "ERROR" } : step));
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  };

  const selectedPath = result?.paths.find((path) => path.path_id === selectedPathId) ?? null;
  const stations = selectedPath?.semesters.map((semester) => ({
    id: String(semester.semester_index),
    title: `الفصل ${semester.semester_index}`,
    hours: semester.plan_option.total_credit_hours,
    courses: semester.plan_option.courses.map((course) => ({
      code: course.course_code,
      name: course.course_name_ar,
      hours: course.credit_hours,
    })),
  })) ?? [];

  return <div className="space-y-8 degree-page">
    <div className="page-heading">
      <span className="eyebrow">بدائل واضحة من محرك أكاديمي واحد</span>
      <h1>مسار التخرج</h1>
      <p className="text-sm text-muted mt-3">كل بطاقة وخريطة فصلية وحساب ساعات أدناه تأتي من البديل الحتمي نفسه دون إعادة توزيع في المتصفح.</p>
    </div>
    <div className="engraved p-6 flex items-center justify-between gap-5 flex-wrap">
      <div><h2 className="text-lg">جاهز لرؤية الخيارات؟</h2><p className="text-xs text-muted mt-2">لا حاجة لاختيار عدد الفصول أو المسارات.</p></div>
      <Button type="button" disabled={loading} onClick={() => void handleGeneratePath()}>
        <Compass size={18}/>{loading ? "جارٍ رسم المسارات…" : "ارسم المسار"}
      </Button>
    </div>
    {errorMessage && <FriendlyState error title={errorMessage} onRetry={() => void handleGeneratePath()}/>}
    {loading && <div className="space-y-6">
      <AcademicAnalysisProgress title="جاري رسم مسارات التخرج الحتمية" subtitle="يطابق المحرك الساعات والمتطلبات ثم يولّد البدائل الفصلية" steps={pathSteps}/>
      <LoadingSkeletonCard className="min-h-48"/>
    </div>}
    {!loading && result && <>
      <div className="strategy-grid" aria-label="خيارات مسار التخرج">
        {result.paths.map((path, index) => {
          const averageLoad = path.semester_count > 0
            ? Number(path.total_planned_credits) / path.semester_count
            : 0;
          return <button key={path.path_id} type="button" className="strategy-card engraved"
            data-selected={selectedPathId === path.path_id} aria-pressed={selectedPathId === path.path_id}
            onClick={() => setSelectedPathId(path.path_id)}>
            <span className="eyebrow">الخيار {index + 1}</span><h2>مسار {index + 1}</h2>
            <strong>{path.semester_count}</strong><span> فصول مخططة</span>
            <div className="strategy-loads">{path.semesters.map((semester) =>
              <span key={semester.semester_index}>الفصل {semester.semester_index} · <bdi>{formatCreditHours(semester.plan_option.total_credit_hours)}</bdi> ساعة</span>)}</div>
            <dl>
              <div><dt>متوسط الساعات في الفصل</dt><dd dir="ltr">{formatCreditHours(averageLoad)}</dd></div>
              <div><dt>ساعات تحتاج مراجعة</dt><dd dir="ltr">{formatCreditHours(path.credit_summary.unplaced_credits)}</dd></div>
            </dl>
            <p>{statusDescription(path)}</p>
          </button>;
        })}
      </div>
      {selectedPath ? <>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div><h2 className="text-xl">خطة المقررات للخيار {selectedPath.rank}</h2><p className="text-xs text-muted mt-2">المسار المحدد: <bdi>{selectedPath.path_id}</bdi></p></div>
          <button className="button-secondary" onClick={() => window.print()}><Printer size={16}/>تصدير PDF</button>
        </div>
        <div className="journey-kpis" aria-label="حساب ساعات المسار المحدد">
          <div className="engraved"><strong dir="ltr">{formatCreditHours(selectedPath.credit_summary.degree_required_credits)}</strong><span>إجمالي ساعات الدرجة</span></div>
          <div className="engraved"><strong dir="ltr">{formatCreditHours(selectedPath.credit_summary.completed_credits)}</strong><span>ساعات مكتملة</span></div>
          <div className="engraved"><strong dir="ltr">{formatCreditHours(selectedPath.credit_summary.current_credits)}</strong><span>ساعات مسجلة حاليًا</span></div>
          <div className="engraved"><strong dir="ltr">{formatCreditHours(selectedPath.credit_summary.future_placed_credits)}</strong><span>ساعات مستقبلية موزعة</span></div>
          <div className="engraved"><strong dir="ltr">{formatCreditHours(selectedPath.credit_summary.unplaced_credits)}</strong><span>ساعات غير موزعة / للمراجعة</span></div>
        </div>
        {(selectedPath.free_elective_requirements ?? []).map((requirement) => <section
          key={requirement.group_code}
          className="engraved p-5"
          aria-label={`${requirement.name_ar} ${formatCreditHours(requirement.required_credits)} ساعات`}
        >
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <span className="eyebrow">متطلب درجة مستقل</span>
              <h3 className="text-lg mt-2">{requirement.name_ar} — <bdi>{formatCreditHours(requirement.required_credits)}</bdi> ساعات</h3>
            </div>
            <div className="text-xs text-muted">
              المتبقي بعد المسجل حاليًا: <bdi>{formatCreditHours(requirement.remaining_credits_after_current)}</bdi> ساعات
            </div>
          </div>
          {(requirement.completed_course_codes ?? []).length > 0 && <p className="text-xs text-muted mt-3">
            احتسبت مواد فعلية مكتملة: <bdi>{requirement.completed_course_codes.join("، ")}</bdi>
          </p>}
          {(requirement.current_course_codes ?? []).length > 0 && <p className="text-xs text-muted mt-3">
            مواد فعلية مسجلة حاليًا: <bdi>{requirement.current_course_codes.join("، ")}</bdi>
          </p>}
          {requirement.selection_state === "FREE_ELECTIVE_POLICY_REQUIRED" && <p className="text-xs text-copper mt-3">
            يلزم اعتماد سياسة الجامعة للمواد المسموح باحتسابها قبل عرض خيارات أو إنشاء تسجيل.
          </p>}
        </section>)}
        {stations.length > 0 ? <PathMap key={selectedPath.path_id} stations={stations}/> : <FriendlyState title="لا توجد فصول مستقبلية لهذا المسار."/>}
        {selectedPath.status !== "MODELED_COMPLETE" && <p className="text-xs text-copper">هذا أفضل مسار صالح ضمن القيود الآمنة، وما زالت بعض المتطلبات تحتاج إلى مراجعة.</p>}
        <details className="engraved p-5"><summary>تفاصيل مطابقة الساعات</summary>
          <p className="text-xs text-muted mt-3">{formatCreditHours(selectedPath.credit_summary.completed_credits)} مكتملة + {formatCreditHours(selectedPath.credit_summary.current_credits)} حالية + {formatCreditHours(selectedPath.credit_summary.future_placed_credits)} مستقبلية + {formatCreditHours(selectedPath.credit_summary.unplaced_credits)} للمراجعة = {formatCreditHours(selectedPath.credit_summary.degree_required_credits)} ساعة.</p>
        </details>
        <details className="engraved p-5"><summary>لماذا هذا التسلسل؟</summary>
          <AcademicGraphExplanation graph={result.explanation_graph} focusId={`degree-path:${selectedPath.path_id}`}
            identities={identities} loading={false} error={false} onRetry={() => void handleGeneratePath()}/>
        </details>
      </> : <FriendlyState title="لم ينتج المحرك مسارًا صالحًا ضمن القيود الحالية."/>}
      <p className="text-xs text-muted">هذه مسارات تخطيطية وليست موعد تخرج أو موافقة تسجيل معتمدة.</p>
    </>}
    {!loading && !errorMessage && !result && <FriendlyState title="اضغط «ارسم المسار» للحصول على البدائل الحتمية"/>}
  </div>;
}
