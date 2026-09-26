"use client";

import { useState } from "react";
import { useAuth } from "@/auth/auth-provider";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type {
  CanTakeDecisionResponse,
  Decision,
  DecisionReason,
  DependencyGroupEvidenceResponse,
  PrerequisiteLogicStatus,
} from "@/lib/api/student-types";
import { Badge, type BadgeVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { LoadingSkeletonCard } from "@/components/ui/LoadingSkeleton";
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  CloseIcon,
  EligibilityIcon,
  InfoIcon,
  SearchIcon,
  SparklesIcon,
} from "@/components/ui/Icons";

function translateReason(reason: DecisionReason): string {
  switch (reason) {
    case "NO_PREREQUISITES":
      return "لا تتطلب هذه المادة أي متطلبات سابقة في الخطة الدراسية.";
    case "PREREQUISITES_SATISFIED":
      return "تم استيفاء جميع المتطلبات السابقة الأكاديمية بنجاح.";
    case "MISSING_PREREQUISITE_GROUP":
      return "توجد مجموعة متطلبات سابقة إلزامية لم يتم اجتيازها بعد.";
    case "PREREQUISITE_LOGIC_UNRESOLVED":
      return "منطق المتطلبات السابقة غير محسوم ويتطلب تدقيق المرشد الأكاديمي.";
    case "PREREQUISITE_SOURCE_CONFLICT":
      return "يوجد تعارض في توثيق المتطلبات السابقة بين المصادر.";
    case "VERIFIED_PREREQUISITE_MODEL_INCOMPLETE":
      return "نموذج المتطلبات السابقة المعتمد غير مكتمل لهذه المادة.";
    case "TARGET_ALREADY_COMPLETED":
      return "لقد اجتزت هذه المادة مسبقاً وسجلت في رصيدك الأكاديمي.";
    case "TARGET_CURRENTLY_ENROLLED":
      return "هذه المادة مسجلة ومدرجة قيد الدراسة في الفصل الجاري.";
    default:
      return String(reason);
  }
}

function translateLogicStatus(status: PrerequisiteLogicStatus): { label: string; variant: BadgeVariant } {
  switch (status) {
    case "verified":
      return { label: "موثق ومعتمد قطيعاً", variant: "success" };
    case "not_applicable":
      return { label: "لا توجد متطلبات", variant: "neutral" };
    case "unresolved":
      return { label: "غير محسوم", variant: "warning" };
    case "source_conflict":
      return { label: "تعارض مصادر", variant: "error" };
    default:
      return { label: status, variant: "neutral" };
  }
}

export default function EligibilityPage() {
  const auth = useAuth();
  const client = useAuthenticatedApi();

  const [courseCodeInput, setCourseCodeInput] = useState("");
  const [result, setResult] = useState<CanTakeDecisionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleCheck = async (codeToCheck?: string) => {
    const code = (codeToCheck ?? courseCodeInput).trim().toUpperCase();
    if (!code) {
      setErrorMessage("يرجى إدخال رمز المادة المراد فحص أهليتها.");
      return;
    }

    setCourseCodeInput(code);
    setLoading(true);
    setErrorMessage(null);
    setResult(null);

    try {
      const api = new StudentApiService(client);
      const data = await api.checkEligibility(code);
      setResult(data);
    } catch (err: unknown) {
      if (err instanceof Error && err.message === "NOT_FOUND") {
        setErrorMessage(`المادة ذات الرمز (${code}) غير موجودة في الخطة الدراسية الحالية.`);
      } else {
        setErrorMessage("تعذر الاتصال بمحرك التحقق الحتمي. يرجى المحاولة لاحقاً.");
      }
    } finally {
      setLoading(false);
    }
  };

  const quickPills = ["1501110", "1501211", "1501221", "1501332", "1501440"];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-[#EDE2C5] pb-5">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[#A66F00]/10 px-2.5 py-0.5 text-xs font-bold text-[#A66F00]">
            المحرك الحتمي للأهلية
          </span>
          <span className="text-xs text-[#726B5E]">قواعد أكاديمية قطعية</span>
        </div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#28241C]">
          فحص أهلية تسجيل مادة
        </h1>
        <p className="text-xs text-[#726B5E]">
          فحص استيفاء المتطلبات السابقة والشروط النظامية لتسجيل أي مادة دراسية وفق قواعد جامعتك.
        </p>
      </div>

      {/* Search / Check Box */}
      <div className="rounded-3xl border border-[#EDE2C5] bg-white p-7 shadow-xs">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleCheck();
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-xs font-bold text-[#28241C] mb-2">
              رمز المادة الأكاديمية (Course Code)
            </label>
            <div className="flex flex-col gap-3 sm:flex-row">
              <div className="relative flex-1">
                <SearchIcon className="pointer-events-none absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#726B5E]" />
                <input
                  type="text"
                  value={courseCodeInput}
                  onChange={(e) => setCourseCodeInput(e.target.value.toUpperCase())}
                  placeholder="أدخل رمز المادة هنا..."
                  className="w-full rounded-2xl border border-[#EDE2C5] bg-[#FFFDF7] py-3 pr-12 pl-4 font-mono text-sm font-bold uppercase text-[#28241C] placeholder-[#726B5E]/50 focus:border-[#E2AD27] focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-[#E2AD27]/20"
                  dir="ltr"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !courseCodeInput.trim()}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#E2AD27] px-7 py-3 text-xs font-bold text-[#28241C] shadow-xs hover:bg-[#A66F00] hover:text-white transition-all disabled:opacity-50"
              >
                <EligibilityIcon className="h-4 w-4" />
                <span>{loading ? "جاري الفحص..." : "فحص الأهلية"}</span>
              </button>
            </div>
          </div>

          {/* Quick suggestions */}
          <div className="flex flex-wrap items-center gap-2 pt-2 text-xs">
            <span className="text-[#726B5E]">مواد مقترحة للفحص السريع:</span>
            {quickPills.map((pill) => (
              <button
                key={pill}
                type="button"
                onClick={() => void handleCheck(pill)}
                className="rounded-xl border border-[#EDE2C5] bg-[#FFF9E8] px-3 py-1 font-mono text-[11px] font-bold text-[#805400] hover:bg-[#FFF4C7] hover:border-[#E2AD27] transition-colors"
                dir="ltr"
              >
                {pill}
              </button>
            ))}
          </div>
        </form>
      </div>

      {/* Error Message */}
      {errorMessage ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-xs text-red-800">
          <div className="flex items-center gap-2 font-bold mb-1">
            <AlertTriangleIcon className="h-4 w-4" />
            <span>تنبيه في فحص المادة</span>
          </div>
          <p>{errorMessage}</p>
        </div>
      ) : null}

      {/* Loading Skeleton */}
      {loading ? (
        <div className="space-y-4">
          <LoadingSkeletonCard />
          <LoadingSkeletonCard />
        </div>
      ) : null}

      {/* Decision Results */}
      {!loading && result ? (
        <div className="space-y-6">
          {/* Main Decision Banner */}
          <div
            className={`rounded-3xl border p-7 shadow-xs ${
              result.decision === "ELIGIBLE"
                ? "border-emerald-200 bg-emerald-50/50"
                : result.decision === "NOT_ELIGIBLE"
                ? "border-red-200 bg-red-50/40"
                : "border-amber-300 bg-amber-50/50"
            }`}
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-4">
                <div
                  className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl shadow-xs ${
                    result.decision === "ELIGIBLE"
                      ? "bg-emerald-100 text-emerald-800"
                      : result.decision === "NOT_ELIGIBLE"
                      ? "bg-red-100 text-red-800"
                      : "bg-amber-100 text-amber-900"
                  }`}
                >
                  {result.decision === "ELIGIBLE" ? (
                    <CheckCircleIcon className="h-7 w-7" />
                  ) : (
                    <AlertTriangleIcon className="h-7 w-7" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-[#A66F00]" dir="ltr">
                      {result.target_course_code}
                    </span>
                    {result.target_name_ar ? (
                      <span className="text-xs font-bold text-[#726B5E]">
                        • {result.target_name_ar}
                      </span>
                    ) : null}
                  </div>
                  <h2 className="text-xl font-bold tracking-tight text-[#28241C] mt-0.5">
                    {result.decision === "ELIGIBLE"
                      ? "مؤهل لتسجيل المادة (ELIGIBLE)"
                      : result.decision === "NOT_ELIGIBLE"
                      ? "غير مؤهل لتسجيل المادة (NOT_ELIGIBLE)"
                      : "تتطلب مراجعة المرشد (REVIEW_REQUIRED)"}
                  </h2>
                  <p className="text-xs text-[#726B5E] mt-1">
                    {result.decision === "ELIGIBLE"
                      ? "مستوفٍ لكافة المتطلبات السابقة والشروط الأكاديمية المقررة في الخطة."
                      : result.decision === "NOT_ELIGIBLE"
                      ? "توجد متطلبات سابقة أو قيود أكاديمية تحول دون التسجيل في الوقت الراهن."
                      : "الحالة تتطلب موافقة أو تدقيقاً استثنائياً من المرشد الأكاديمي."}
                  </p>
                </div>
              </div>

              <div>
                <Badge
                  variant={
                    result.decision === "ELIGIBLE"
                      ? "success"
                      : result.decision === "NOT_ELIGIBLE"
                      ? "error"
                      : "review"
                  }
                  size="md"
                >
                  {result.decision}
                </Badge>
              </div>
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Target & Attempt Details */}
            <div className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-xs space-y-4">
              <h3 className="text-sm font-bold text-[#28241C] border-b border-[#EDE2C5] pb-3">
                بيانات المادة وحالة المحاولة
              </h3>

              <div className="space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[#726B5E]">رمز المادة:</span>
                  <span className="font-mono font-bold text-[#28241C]" dir="ltr">
                    {result.target_course_code}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-[#726B5E]">حالة توثيق المتطلبات:</span>
                  <Badge variant={translateLogicStatus(result.prerequisite_logic_status).variant}>
                    {translateLogicStatus(result.prerequisite_logic_status).label}
                  </Badge>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-[#726B5E]">مجتازة مسبقاً:</span>
                  <span className="font-bold text-[#28241C]">
                    {result.target_attempt_state.has_passed_target ? "نعم (مجتازة)" : "لا"}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-[#726B5E]">قيد الدراسة حالياً:</span>
                  <span className="font-bold text-[#28241C]">
                    {result.target_attempt_state.has_in_progress_target ? "نعم (قيد الدراسة)" : "لا"}
                  </span>
                </div>

                {result.raw_prerequisite_text ? (
                  <div className="pt-2 border-t border-[#EDE2C5]/60">
                    <span className="block text-[11px] font-bold text-[#726B5E] mb-1">
                      النص الأصلي لشرط المتطلب في الخطة:
                    </span>
                    <span className="block rounded-xl bg-[#FFF9E8] p-2.5 font-mono text-[11px] text-[#805400] border border-[#EDE2C5]" dir="ltr">
                      {result.raw_prerequisite_text}
                    </span>
                  </div>
                ) : null}
              </div>
            </div>

            {/* Reasons List */}
            <div className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-xs space-y-4">
              <h3 className="text-sm font-bold text-[#28241C] border-b border-[#EDE2C5] pb-3">
                أسباب القرار الأكاديمي الحتمي
              </h3>

              {result.reasons.length === 0 ? (
                <p className="text-xs text-[#726B5E]">لا توجد أسباب مسجلة.</p>
              ) : (
                <ul className="space-y-2.5 text-xs">
                  {result.reasons.map((reason, idx) => (
                    <li
                      key={idx}
                      className="flex items-start gap-2.5 rounded-2xl bg-[#FFFCF4] p-3 border border-[#EDE2C5]/60"
                    >
                      <SparklesIcon className="h-4 w-4 shrink-0 text-[#A66F00] mt-0.5" />
                      <div>
                        <p className="font-bold text-[#28241C]">{translateReason(reason)}</p>
                        <p className="font-mono text-[10px] text-[#726B5E]" dir="ltr">
                          Code: {reason}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Satisfied Dependency Groups */}
          {result.satisfied_dependency_groups.length > 0 ? (
            <div className="rounded-3xl border border-emerald-200 bg-white p-6 shadow-xs space-y-4">
              <div className="flex items-center gap-2">
                <CheckCircleIcon className="h-5 w-5 text-emerald-600" />
                <h3 className="text-sm font-bold text-[#28241C]">
                  مجموعات المتطلبات المستوفاة بنجاح ({result.satisfied_dependency_groups.length})
                </h3>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {result.satisfied_dependency_groups.map((group: DependencyGroupEvidenceResponse) => (
                  <div
                    key={group.group_number}
                    className="rounded-2xl border border-emerald-100 bg-emerald-50/40 p-4 text-xs"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-emerald-900">
                        مجموعة {group.group_number} ({group.dependency_type === "prerequisite" ? "متطلب سابق" : "متطلب متزامن"})
                      </span>
                      <Badge variant="success" size="sm">مستوفاة</Badge>
                    </div>
                    <div className="space-y-1">
                      <span className="text-[11px] text-[#726B5E]">المواد المجتازة:</span>
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {group.passed_option_course_codes.map((code) => (
                          <span
                            key={code}
                            className="rounded-lg bg-white px-2 py-0.5 font-mono text-xs font-bold text-emerald-800 border border-emerald-200"
                            dir="ltr"
                          >
                            {code}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {/* Missing Dependency Groups */}
          {result.missing_dependency_groups.length > 0 ? (
            <div className="rounded-3xl border border-red-200 bg-white p-6 shadow-xs space-y-4">
              <div className="flex items-center gap-2">
                <AlertTriangleIcon className="h-5 w-5 text-red-600" />
                <h3 className="text-sm font-bold text-[#28241C]">
                  المتطلبات السابقة غير المستوفاة ({result.missing_dependency_groups.length})
                </h3>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {result.missing_dependency_groups.map((group: DependencyGroupEvidenceResponse) => (
                  <div
                    key={group.group_number}
                    className="rounded-2xl border border-red-100 bg-red-50/40 p-4 text-xs"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-red-900">
                        مجموعة {group.group_number} ({group.dependency_type === "prerequisite" ? "متطلب سابق" : "متطلب متزامن"})
                      </span>
                      <Badge variant="error" size="sm">مطلوب اجتيازها</Badge>
                    </div>
                    <div className="space-y-1">
                      <span className="text-[11px] text-[#726B5E]">المواد المطلوبة في هذه المجموعة:</span>
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {group.option_course_codes.map((code) => (
                          <span
                            key={code}
                            className="rounded-lg bg-white px-2 py-0.5 font-mono text-xs font-bold text-red-800 border border-red-200"
                            dir="ltr"
                          >
                            {code}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {/* Governance Notice */}
          <div className="rounded-2xl border border-[#EDE2C5] bg-[#FFF9E8] p-4 text-xs text-[#726B5E] flex items-center gap-3">
            <InfoIcon className="h-5 w-5 text-[#A66F00] shrink-0" />
            <p>
              <strong>مبدأ الحوكمة الأكاديمية:</strong> الذكاء الاصطناعي يشرح والقواعد الحتمية تقرر. تم إصدار نتيجة الأهلية أعلاه مباشرة من محرك القواعد الأكاديمية المعتمد.
            </p>
          </div>
        </div>
      ) : (
        !loading && (
          <EmptyState
            title="ابدأ بفحص أهلية أي مادة"
            description="أدخل رمز المادة في المربع أعلاه أو اختر إحدى المواد المقترحة للتحقق من أهليتك لتسجيلها واستيفائك لمتطلباتها."
            icon={<EligibilityIcon className="h-7 w-7" />}
          />
        )
      )}
    </div>
  );
}
