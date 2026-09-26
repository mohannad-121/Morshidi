"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/auth/auth-provider";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type {
  DashboardError,
  StudentIntentResponse,
  SubmitIntentRequest,
  WithdrawIntentRequest,
} from "@/lib/api/student-types";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert, isRetryableError } from "@/components/ui/ErrorAlert";
import { LoadingSkeletonCard } from "@/components/ui/LoadingSkeleton";
import { StatCard } from "@/components/ui/StatCard";
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  CloseIcon,
  CoursesIcon,
  InfoIcon,
  MockRegistrationIcon,
  PlusIcon,
  SparklesIcon,
  TrashIcon,
} from "@/components/ui/Icons";

const DEFAULT_PERIOD = "2024-1";
const NOTICE_VERSION = "2026-v1";

export default function MockRegistrationPage() {
  const auth = useAuth();
  const client = useAuthenticatedApi();

  const [targetPeriod, setTargetPeriod] = useState<string>(DEFAULT_PERIOD);
  const [intent, setIntent] = useState<StudentIntentResponse | null>(null);
  const [error, setError] = useState<DashboardError | null>(null);
  const [loading, setLoading] = useState(true);

  // Form states for creating / editing revision
  const [isEditing, setIsEditing] = useState(false);
  const [courseList, setCourseList] = useState<string[]>([]);
  const [newCourseCode, setNewCourseCode] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [agreedTransparency, setAgreedTransparency] = useState(true);

  const fetchCurrentIntent = async (period: string) => {
    setLoading(true);
    setError(null);
    try {
      const api = new StudentApiService(client);
      const data = await api.getCurrentMockRegistration(period);
      setIntent(data);
      if (data && data.lifecycle_status !== "WITHDRAWN") {
        setCourseList(data.course_codes);
      } else {
        setCourseList([]);
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.message === "NOT_FOUND") {
        setIntent(null);
        setCourseList([]);
      } else {
        setError("SERVER_ERROR");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (auth.isAuthenticated) {
      void fetchCurrentIntent(targetPeriod);
    }
  }, [auth.isAuthenticated, targetPeriod]);

  const handleAddCourse = (e: React.FormEvent) => {
    e.preventDefault();
    const code = newCourseCode.trim().toUpperCase();
    if (!code) return;
    if (courseList.includes(code)) {
      setActionError("المادة مضافة بالفعل في قائمة الرغبات.");
      return;
    }
    setCourseList((prev) => [...prev, code]);
    setNewCourseCode("");
    setActionError(null);
  };

  const handleRemoveCourse = (code: string) => {
    setCourseList((prev) => prev.filter((c) => c !== code));
  };

  const handleSubmitRevision = async () => {
    if (courseList.length === 0) {
      setActionError("يرجى إضافة مادة واحدة على الأقل في رغبة التسجيل.");
      return;
    }
    if (!agreedTransparency) {
      setActionError("يجب الموافقة على إقرار الشفافية بأن التسجيل تجريبي وغير ملزم.");
      return;
    }

    setActionLoading(true);
    setActionError(null);
    try {
      const api = new StudentApiService(client);
      const req: SubmitIntentRequest = {
        target_period_id: targetPeriod,
        course_codes: courseList,
        expected_current_revision: intent?.revision ?? null,
        transparency_notice_version: NOTICE_VERSION,
      };
      const res = await api.submitMockRegistration(req);
      setIntent(res);
      setIsEditing(false);
    } catch {
      setActionError("تعذر حفظ رغبة التسجيل التجريبي. يرجى المحاولة مرة أخرى.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleWithdrawIntent = async () => {
    if (!intent) return;
    if (!confirm("هل أنت متأكد من رغبتك في سحب رغبة التسجيل التجريبي لهذا الفصل؟")) return;

    setActionLoading(true);
    setActionError(null);
    try {
      const api = new StudentApiService(client);
      const req: WithdrawIntentRequest = {
        target_period_id: targetPeriod,
        expected_current_revision: intent.revision,
        transparency_notice_version: NOTICE_VERSION,
      };
      const res = await api.withdrawMockRegistration(req);
      setIntent(res);
      setIsEditing(false);
      setCourseList([]);
    } catch {
      alert("تعذر سحب الرغبة. يرجى المحاولة لاحقاً.");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-2 border-b border-[#EDE2C5] pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-[#A66F00]/10 px-2.5 py-0.5 text-xs font-bold text-[#A66F00]">
              التسجيل التجريبي الذكي
            </span>
            <span className="text-xs text-[#726B5E]">رغبات تسجيل غير ملزمة</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#28241C]">
            التسجيل التجريبي والمحاكاة
          </h1>
          <p className="text-xs text-[#726B5E]">
            حصر مبكر لرغبات تسجيل المواد لمساعدة قسمك الأكاديمي في تخطيط وتوزيع الشعب الدراسية.
          </p>
        </div>

        {/* Period Selector */}
        <div className="flex items-center gap-2 text-xs">
          <span className="font-bold text-[#726B5E]">الفصل الدراسي المستهدف:</span>
          <select
            value={targetPeriod}
            onChange={(e) => setTargetPeriod(e.target.value)}
            className="rounded-xl border border-[#EDE2C5] bg-white px-3 py-1.5 font-mono text-xs font-bold text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
            dir="ltr"
          >
            <option value="2024-1">2024-1 (الفصل الأول)</option>
            <option value="2024-2">2024-2 (الفصل الثاني)</option>
            <option value="2024-3">2024-3 (الفصل الصيفي)</option>
          </select>
        </div>
      </div>

      {/* Non-binding Transparency Notice */}
      <div className="rounded-3xl border border-[#EDE2C5] bg-[#FFF9E8] p-5 text-xs text-[#726B5E] shadow-xs">
        <div className="flex items-start gap-3">
          <InfoIcon className="h-5 w-5 text-[#A66F00] shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="font-bold text-[#28241C]">إشعار الشفافية والمسؤولية الأكاديمية:</h3>
            <p className="leading-relaxed">
              هذا التسجيل استطلاعي وتجريبي (Non-binding Mock Registration). لا يُعد تسجيلاً رسمياً، ولا يمنح حقاً مكتسباً في الشعب، ولا تترتب عليه أي التزامات مالية. التسجيل الرسمي يتم حصراً عبر بوابة القبول والتسجيل الرسمية عند فتح فترات التسجيل.
            </p>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error ? (
        <ErrorAlert
          error={error}
          onRetry={isRetryableError(error) ? () => fetchCurrentIntent(targetPeriod) : undefined}
        />
      ) : null}

      {/* Loading Skeleton */}
      {loading ? (
        <div className="space-y-6">
          <LoadingSkeletonCard />
          <LoadingSkeletonCard />
        </div>
      ) : null}

      {/* Content */}
      {!loading && !error ? (
        <div className="space-y-6">
          {/* Active Intent View */}
          {intent && intent.lifecycle_status !== "WITHDRAWN" && !isEditing ? (
            <div className="rounded-3xl border border-[#EDE2C5] bg-white p-7 shadow-xs space-y-6">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-[#EDE2C5]/60 pb-5">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-[#A66F00]" dir="ltr">
                      الفصل {intent.target_period_id}
                    </span>
                    <span className="text-xs text-[#726B5E]">
                      • المراجعة #{intent.revision}
                    </span>
                  </div>
                  <h2 className="text-lg font-bold text-[#28241C] mt-1">
                    رغبة التسجيل التجريبي المسجلة
                  </h2>
                  <p className="text-xs text-[#726B5E]">
                    تم توثيق الرغبة بنجاح وإدراجها في حسابات الاحتياج الفصلي.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={intent.lifecycle_status === "SUBMITTED" ? "success" : "gold"}>
                    {intent.lifecycle_status === "SUBMITTED" ? "مرسلة ومعتمدة" : intent.lifecycle_status}
                  </Badge>
                  <Badge
                    variant={
                      intent.submission_validation_status === "VALID"
                        ? "success"
                        : intent.submission_validation_status === "REVIEW_REQUIRED"
                        ? "review"
                        : "error"
                    }
                  >
                    حالة المطابقة: {intent.submission_validation_status}
                  </Badge>
                </div>
              </div>

              {/* Course Badges List */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-[#28241C]">
                  المواد المختارة في هذه الرغبة ({intent.course_codes.length} مواد):
                </span>
                <div className="flex flex-wrap gap-2 pt-1">
                  {intent.course_codes.map((code) => (
                    <span
                      key={code}
                      className="rounded-2xl border border-[#EDE2C5] bg-[#FFF9E8] px-4 py-2 font-mono text-xs font-bold text-[#28241C] shadow-xs"
                      dir="ltr"
                    >
                      {code}
                    </span>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#EDE2C5]/60 pt-5">
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="rounded-2xl bg-[#E2AD27] px-6 py-2.5 text-xs font-bold text-[#28241C] hover:bg-[#A66F00] hover:text-white transition-all shadow-xs"
                >
                  تعديل الرغبات وإرسال مراجعة جديدة
                </button>

                <button
                  type="button"
                  onClick={() => void handleWithdrawIntent()}
                  disabled={actionLoading}
                  className="rounded-2xl border border-red-200 bg-red-50 px-5 py-2.5 text-xs font-bold text-red-800 hover:bg-red-100 transition-colors disabled:opacity-50"
                >
                  سحب رغبة التسجيل
                </button>
              </div>
            </div>
          ) : null}

          {/* Form to Create or Edit Intent */}
          {(!intent || intent.lifecycle_status === "WITHDRAWN" || isEditing) ? (
            <div className="rounded-3xl border border-[#EDE2C5] bg-white p-7 shadow-xs space-y-6">
              <div className="border-b border-[#EDE2C5] pb-4">
                <h2 className="text-base font-bold text-[#28241C]">
                  {intent && intent.lifecycle_status !== "WITHDRAWN"
                    ? `تعديل رغبة التسجيل (المراجعة القادمة #${intent.revision + 1})`
                    : `تسجيل رغبة فصلية تجريبية جديدة (${targetPeriod})`}
                </h2>
                <p className="text-xs text-[#726B5E]">
                  أضف رموز المواد التي ترغب في دراستها خلال الفصل القادم.
                </p>
              </div>

              {actionError ? (
                <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800">
                  {actionError}
                </div>
              ) : null}

              {/* Add Course Input Form */}
              <form onSubmit={handleAddCourse} className="space-y-2">
                <label className="block text-xs font-bold text-[#28241C]">
                  إضافة مادة إلى قائمة الرغبات:
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newCourseCode}
                    onChange={(e) => setNewCourseCode(e.target.value.toUpperCase())}
                    placeholder="أدخل رمز المادة (مثل: CS101 أو AI201)..."
                    className="flex-1 rounded-2xl border border-[#EDE2C5] bg-[#FFFCF4] px-4 py-2.5 font-mono text-xs uppercase text-[#28241C] focus:border-[#E2AD27] focus:bg-white focus:outline-hidden"
                    dir="ltr"
                  />
                  <button
                    type="submit"
                    className="inline-flex items-center gap-1.5 rounded-2xl bg-[#FFF9E8] border border-[#EDE2C5] px-5 py-2.5 text-xs font-bold text-[#805400] hover:bg-[#FFF4C7] hover:border-[#E2AD27] transition-all"
                  >
                    <PlusIcon className="h-4 w-4" />
                    <span>إضافة</span>
                  </button>
                </div>
              </form>

              {/* Current List in Draft */}
              <div className="space-y-3">
                <span className="text-xs font-bold text-[#28241C]">
                  المواد المضافة في القائمة الحالية ({courseList.length}):
                </span>
                {courseList.length === 0 ? (
                  <p className="rounded-2xl border border-dashed border-[#EDE2C5] p-5 text-center text-xs text-[#726B5E]">
                    لم تقم بإضافة أي مواد بعد. أضف المواد من الحقل أعلاه.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {courseList.map((code) => (
                      <span
                        key={code}
                        className="inline-flex items-center gap-2 rounded-2xl border border-[#EDE2C5] bg-[#FFF9E8] px-3.5 py-1.5 font-mono text-xs font-bold text-[#28241C]"
                        dir="ltr"
                      >
                        <span>{code}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveCourse(code)}
                          className="rounded-full p-0.5 text-stone-400 hover:bg-stone-200 hover:text-stone-700 transition-colors"
                        >
                          <CloseIcon className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Transparency Agreement */}
              <div className="rounded-2xl bg-[#FFFCF4] p-4 border border-[#EDE2C5]/70 text-xs text-[#726B5E]">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={agreedTransparency}
                    onChange={(e) => setAgreedTransparency(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-[#EDE2C5] text-[#A66F00] focus:ring-[#E2AD27]"
                  />
                  <span>
                    أقر بأن هذا التسجيل تجريبي وغير ملزم ومخصص لأغراض دراسة الاحتياج الفصلي والتخطيط الأكاديمي، ولا يغني عن التسجيل الرسمي.
                  </span>
                </label>
              </div>

              {/* Submit Buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#EDE2C5]/60">
                {isEditing ? (
                  <button
                    type="button"
                    onClick={() => {
                      setIsEditing(false);
                      if (intent) setCourseList(intent.course_codes);
                    }}
                    className="rounded-2xl border border-[#EDE2C5] px-5 py-2.5 text-xs font-bold text-[#726B5E] hover:bg-[#FFF9E8]"
                  >
                    إلغاء التعديل
                  </button>
                ) : null}

                <button
                  type="button"
                  onClick={() => void handleSubmitRevision()}
                  disabled={actionLoading || courseList.length === 0}
                  className="rounded-2xl bg-[#E2AD27] px-7 py-2.5 text-xs font-bold text-[#28241C] hover:bg-[#A66F00] hover:text-white transition-all shadow-xs disabled:opacity-50"
                >
                  {actionLoading ? "جاري الإرسال..." : "إرسال رغبة التسجيل التجريبي"}
                </button>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
