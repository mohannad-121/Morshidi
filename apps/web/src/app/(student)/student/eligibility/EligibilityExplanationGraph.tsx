import type {
  Decision, EligibilityExplanationGraph, EligibilityGraphMode,
} from "@/lib/api/student-types";
import { CourseIdentity } from "@/components/academic/CourseIdentity";
import type { CourseIdentityMap } from "@/lib/api/use-course-identities";

const decisionLabels: Record<Decision, string> = {
  ELIGIBLE: "مؤهل",
  NOT_ELIGIBLE: "غير مؤهل",
  REVIEW_REQUIRED: "تتطلب مراجعة",
};

const knownReasons: Record<string, string> = {
  NO_PREREQUISITES: "لا توجد متطلبات سابقة لهذه المادة",
  PREREQUISITES_SATISFIED: "استوفيت المتطلبات السابقة",
  MISSING_PREREQUISITE_GROUP: "توجد مجموعة متطلبات سابقة غير مستوفاة",
  PREREQUISITE_LOGIC_UNRESOLVED: "منطق المتطلبات السابقة غير محسوم",
  PREREQUISITE_SOURCE_CONFLICT: "مصادر المتطلبات السابقة متعارضة",
  VERIFIED_PREREQUISITE_MODEL_INCOMPLETE: "نموذج المتطلبات المعتمد غير مكتمل",
  TARGET_ALREADY_COMPLETED: "اجتزت المادة المستهدفة سابقاً",
  TARGET_CURRENTLY_ENROLLED: "المادة المستهدفة قيد الدراسة حالياً",
};

const limitationLabels: Record<string, string> = {
  CURRENT_STORED_STATE: "يعكس هذا الشرح الحالة الأكاديمية المخزنة حالياً.",
  NOT_OFFICIAL_REGISTRATION: "هذا الشرح ليس إجراء تسجيل رسمياً.",
  EXACT_SOURCE_VERSION_UNAVAILABLE: "لا يتضمن ناتج الأهلية الحالي معرف نسخة مصدر دقيقاً؛ لم تُنشأ إحالة بديلة.",
  PREREQUISITE_LOGIC_UNRESOLVED: "يلزم تدقيق منطق المتطلبات السابقة.",
  PREREQUISITE_SOURCE_CONFLICT: "يلزم حسم تعارض مصادر المتطلبات.",
  VERIFIED_MODEL_INCOMPLETE: "يلزم استكمال نموذج المتطلبات المعتمد.",
};

type Props = {
  graph: EligibilityExplanationGraph | null;
  mode: EligibilityGraphMode;
  loading: boolean;
  error: boolean;
  onModeChange: (mode: EligibilityGraphMode) => void;
  onRetry: () => void;
  canAskWhyNot: boolean;
  identities?: CourseIdentityMap;
};

export function EligibilityExplanationGraphPanel({
  graph, mode, loading, error, onModeChange, onRetry, canAskWhyNot, identities,
}: Props) {
  const valid = graph && Array.isArray(graph.nodes) && Array.isArray(graph.edges);
  const decision = valid
    ? graph.nodes.find((node) => node.id === graph.root_node_id && node.type === "DECISION")?.decision
    : null;
  const groups = valid ? graph.nodes.filter((node) => node.type === "PREREQUISITE_GROUP") : [];
  const reasons = valid ? graph.nodes.filter((node) => node.type === "REASON") : [];
  const states = valid ? graph.nodes.filter((node) => node.type === "ACADEMIC_STATE") : [];
  const limits = valid ? graph.limitations : [];

  return (
    <section aria-labelledby="eligibility-explanation-heading" dir="rtl"
      className="rounded-3xl border border-[#EDE2C5] bg-white p-5 shadow-xs sm:p-7">
      <div className="flex flex-col gap-3 border-b border-[#EDE2C5] pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 id="eligibility-explanation-heading" className="text-lg font-bold text-[#28241C]">
            لماذا هذا القرار؟
          </h2>
          <p className="mt-1 text-xs text-[#726B5E]">رسم تفسيري من أسباب وحقائق المحرك الحتمي، وليس تفكيراً خفياً أو قراراً جديداً.</p>
        </div>
        <div role="group" aria-label="طريقة عرض التفسير" className="flex gap-2">
          <button type="button" onClick={() => onModeChange("why")}
            aria-pressed={mode === "why"}
            className={`rounded-xl border px-3 py-2 text-xs font-bold ${mode === "why" ? "border-[#E2AD27] bg-[#FFF9E8]" : "border-[#EDE2C5]"}`}>
            لماذا؟
          </button>
          <button type="button" onClick={() => onModeChange("why_not")}
            disabled={!canAskWhyNot} aria-pressed={mode === "why_not"}
            className={`rounded-xl border px-3 py-2 text-xs font-bold disabled:opacity-50 ${mode === "why_not" ? "border-[#E2AD27] bg-[#FFF9E8]" : "border-[#EDE2C5]"}`}>
            لماذا ليس مؤهلاً؟
          </button>
        </div>
      </div>

      {loading ? <p role="status" className="py-5 text-sm text-[#726B5E]">جارٍ تحميل التفسير...</p> : null}
      {!loading && error ? (
        <div role="alert" className="space-y-3 py-5 text-sm text-red-800">
          <p>تعذر تحميل التفسير. تبقى نتيجة الأهلية أعلاه هي النتيجة المعتمدة.</p>
          <button type="button" onClick={onRetry} className="rounded-xl border border-red-200 px-3 py-2 font-bold">إعادة المحاولة</button>
        </div>
      ) : null}
      {!loading && !error && (!valid || !decision) ? (
        <p className="py-5 text-sm text-[#726B5E]">لا يتوفر رسم تفسيري لهذا الفحص.</p>
      ) : null}
      {!loading && !error && valid && decision ? (
        <div className="space-y-5 pt-5">
          <div className="rounded-2xl border border-[#EDE2C5] bg-[#FFF9E8] p-4">
            <p className="text-xs font-bold text-[#726B5E]">القرار الحتمي للمادة <bdi dir="ltr">{graph.subject_reference}</bdi></p>
            <p className="mt-1 text-base font-bold text-[#28241C]">{decisionLabels[decision]}</p>
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#28241C]">سبب القرار</h3>
            {reasons.length ? (
              <ul className="mt-2 space-y-2">
                {reasons.map((node) => <li key={node.id} className="rounded-xl border border-[#EDE2C5] p-3 text-sm">
                  {node.reason ? knownReasons[node.reason] ?? "سبب غير متاح للعرض" : "سبب غير متاح للعرض"}
                </li>)}
              </ul>
            ) : <p className="mt-2 text-sm text-[#726B5E]">لا توجد أسباب مفصلة متاحة.</p>}
          </div>
          {groups.length ? <div>
            <h3 className="text-sm font-bold text-[#28241C]">مجموعات المتطلبات السابقة</h3>
            <p className="mt-1 text-xs text-[#726B5E]">يلزم استيفاء كل مجموعة؛ داخل المجموعة يكفي اجتياز أحد الخيارات.</p>
            <ol className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
              {groups.map((group) => {
                const blocked = graph.edges.some((edge) => edge.to_node_id === group.id && edge.relation === "BLOCKED_BY");
                return <li key={group.id} className={`rounded-2xl border p-4 ${blocked ? "border-red-200 bg-red-50/40" : "border-emerald-200 bg-emerald-50/40"}`}>
                  <h4 className="font-bold text-[#28241C]">مجموعة {group.group_number}: {blocked ? "غير مستوفاة" : "مستوفاة"}</h4>
                  <p className="mt-1 text-xs text-[#726B5E]">{group.option_course_codes.length > 1 ? "خيارات بديلة (أو)" : "متطلب واحد"}</p>
                  <ul className="mt-2 space-y-1 text-sm">
                    {group.option_course_codes.map((code) => <li key={code} className="flex flex-wrap items-center gap-2">
                      <CourseIdentity courseCode={code} identities={identities} compact />
                      <span>{group.passed_option_course_codes.includes(code) ? "مجتاز" : "غير مجتاز"}</span>
                    </li>)}
                  </ul>
                </li>;
              })}
            </ol>
          </div> : null}
          {states.some((node) => node.academic_state === "TARGET_COMPLETED" || node.academic_state === "TARGET_IN_PROGRESS") ? (
            <p className="rounded-xl border border-[#EDE2C5] p-3 text-sm">
              حالة المادة المستهدفة: {states.some((node) => node.academic_state === "TARGET_COMPLETED") ? "مجتازة سابقاً" : ""}
              {states.some((node) => node.academic_state === "TARGET_IN_PROGRESS") ? " قيد الدراسة حالياً" : ""}
            </p>
          ) : null}
          {limits.length ? <div>
            <h3 className="text-sm font-bold text-[#28241C]">حدود التفسير والمصدر</h3>
            <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-[#726B5E]">
              {limits.map((item) => <li key={item}>{limitationLabels[item] ?? "يوجد حد غير متاح للعرض."}</li>)}
            </ul>
          </div> : null}
        </div>
      ) : null}
    </section>
  );
}
