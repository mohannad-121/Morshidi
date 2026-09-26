"use client";

import { useState } from "react";
import { useAuth } from "@/auth/auth-provider";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type {
  DegreePathOptionResponse,
  DegreePathRequest,
  DegreePathResponse,
  ModeledSemesterResponse,
  PlannedCourseEntryResponse,
} from "@/lib/api/student-types";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { LoadingSkeletonCard } from "@/components/ui/LoadingSkeleton";
import { StatCard } from "@/components/ui/StatCard";
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  CoursesIcon,
  DegreePathIcon,
  InfoIcon,
  SparklesIcon,
} from "@/components/ui/Icons";

export default function DegreePathPage() {
  const auth = useAuth();
  const client = useAuthenticatedApi();

  // Constraints
  const [maxCreditsPerSemester, setMaxCreditsPerSemester] = useState<number>(15);
  const [maxSemestersAhead, setMaxSemestersAhead] = useState<number>(8);
  const [maxPaths, setMaxPaths] = useState<number>(2);

  // States
  const [result, setResult] = useState<DegreePathResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedPathIndex, setSelectedPathIndex] = useState<number>(0);

  const handleGeneratePath = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    setErrorMessage(null);
    setResult(null);

    try {
      const api = new StudentApiService(client);
      const req: DegreePathRequest = {
        max_credit_hours_per_semester: maxCreditsPerSemester,
        max_semesters_ahead: maxSemestersAhead,
        max_paths: maxPaths,
      };
      const data = await api.createDegreePaths(req);
      setResult(data);
      setSelectedPathIndex(0);
    } catch {
      setErrorMessage("تعذر توليد مسار التخرج. يرجى التحقق من توفر الخطة الدراسية وسجل المواد.");
    } finally {
      setLoading(false);
    }
  };

  const selectedPath: DegreePathOptionResponse | null =
    result?.paths && result.paths.length > selectedPathIndex
      ? result.paths[selectedPathIndex]
      : null;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-[#EDE2C5] pb-5">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[#A66F00]/10 px-2.5 py-0.5 text-xs font-bold text-[#A66F00]">
            محاكاة التخرج المتعددة الفصول
          </span>
          <span className="text-xs text-[#726B5E]">تخطيط مسار الدرجة العلمية</span>
        </div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#28241C]">
          المسار الدراسي حتى التخرج
        </h1>
        <p className="text-xs text-[#726B5E]">
          محاكاة حتمية متكاملة لخطواتك الدراسية فصلاً بفصل، تضمن استيفاء كافة المتطلبات حتى التخرج بأقل عدد فصول ممكن.
        </p>
      </div>

      {/* Constraints Box */}
      <div className="rounded-3xl border border-[#EDE2C5] bg-white p-7 shadow-xs">
        <form onSubmit={handleGeneratePath} className="space-y-6">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            {/* Max Credits */}
            <div>
              <label className="block text-xs font-bold text-[#28241C] mb-2">
                سقف الساعات لكل فصل *
              </label>
              <div className="flex items-center gap-2">
                {[12, 15, 18].map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setMaxCreditsPerSemester(preset)}
                    className={`rounded-xl px-3 py-1.5 font-mono text-xs font-bold transition-colors ${
                      maxCreditsPerSemester === preset
                        ? "bg-[#E2AD27] text-[#28241C] shadow-xs"
                        : "bg-[#FFF9E8] text-[#726B5E] border border-[#EDE2C5] hover:bg-[#FFF4C7]"
                    }`}
                  >
                    {preset} س
                  </button>
                ))}
                <input
                  type="number"
                  min={6}
                  max={21}
                  value={maxCreditsPerSemester}
                  onChange={(e) => setMaxCreditsPerSemester(Number(e.target.value))}
                  className="w-16 rounded-xl border border-[#EDE2C5] bg-white p-2 font-mono text-xs font-bold text-center text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
                />
              </div>
            </div>

            {/* Max Semesters Ahead */}
            <div>
              <label className="block text-xs font-bold text-[#28241C] mb-2">
                المدى الزمني للمحاكاة (أقصى فصول)
              </label>
              <select
                value={maxSemestersAhead}
                onChange={(e) => setMaxSemestersAhead(Number(e.target.value))}
                className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 text-xs text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
              >
                <option value={4}>4 فصول دراسية (سنتان)</option>
                <option value={6}>6 فصول دراسية (3 سنوات)</option>
                <option value={8}>8 فصول دراسية (4 سنوات - موصى به)</option>
                <option value={10}>10 فصول دراسية (5 سنوات)</option>
              </select>
            </div>

            {/* Max Paths */}
            <div>
              <label className="block text-xs font-bold text-[#28241C] mb-2">
                عدد سيناريوهات المسار
              </label>
              <select
                value={maxPaths}
                onChange={(e) => setMaxPaths(Number(e.target.value))}
                className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 text-xs text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
              >
                <option value={1}>مسار واحد (المسار الأسرع)</option>
                <option value={2}>مساران للمقارنة</option>
                <option value={3}>3 مسارات بديلة</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end pt-2 border-t border-[#EDE2C5]/60">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#E2AD27] px-7 py-3 text-xs font-bold text-[#28241C] shadow-xs hover:bg-[#A66F00] hover:text-white transition-all disabled:opacity-50"
            >
              <SparklesIcon className="h-4 w-4" />
              <span>{loading ? "جاري محاكاة مسار التخرج..." : "توليد ومحاكاة مسار التخرج"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Error */}
      {errorMessage ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-xs text-red-800">
          <p className="font-bold">{errorMessage}</p>
        </div>
      ) : null}

      {/* Loading */}
      {loading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <LoadingSkeletonCard />
            <LoadingSkeletonCard />
            <LoadingSkeletonCard />
            <LoadingSkeletonCard />
          </div>
          <LoadingSkeletonCard />
        </div>
      ) : null}

      {/* Result Path */}
      {!loading && result && result.paths.length > 0 ? (
        <div className="space-y-8">
          {/* Paths Selection */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-[#726B5E]">سيناريوهات المسار المتاحة:</span>
              {result.paths.map((p, idx) => (
                <button
                  key={p.rank}
                  type="button"
                  onClick={() => setSelectedPathIndex(idx)}
                  className={`rounded-2xl px-4 py-2 text-xs font-bold transition-all ${
                    selectedPathIndex === idx
                      ? "bg-[#E2AD27] text-[#28241C] shadow-xs font-extrabold"
                      : "bg-white text-[#726B5E] border border-[#EDE2C5] hover:bg-[#FFF9E8]"
                  }`}
                >
                  المسار #{p.rank} ({p.semester_count} فصول)
                </button>
              ))}
            </div>

            <div className="text-xs text-[#726B5E]">
              الساعات المكتسبة الحالية:{" "}
              <strong className="font-mono text-[#28241C]">{result.initial_completed_credits} س</strong>
            </div>
          </div>

          {selectedPath ? (
            <div className="space-y-6">
              {/* Path Overview Cards */}
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <StatCard
                  title="حالة المسار"
                  value={selectedPath.status === "COMPLETE" ? "تخرج كامل" : selectedPath.status}
                  subtitle={
                    selectedPath.status === "COMPLETE"
                      ? "يضمن استيفاء متطلبات التخرج 100%"
                      : "مسار جزئي ضمن سقف الفصول"
                  }
                  icon={<CheckCircleIcon className="h-5 w-5" />}
                  variant={selectedPath.status === "COMPLETE" ? "gold" : "warm"}
                />
                <StatCard
                  title="عدد الفصول المتوقعة"
                  value={`${selectedPath.semester_count} فصول`}
                  subtitle="لإتمام كافة المواد المتبقية"
                  icon={<ClockIcon className="h-5 w-5" />}
                />
                <StatCard
                  title="إجمالي الساعات المخططة"
                  value={`${selectedPath.total_planned_credits} س`}
                  subtitle={`موزعة على ${selectedPath.total_planned_courses} مادة`}
                  icon={<CoursesIcon className="h-5 w-5" />}
                />
                <StatCard
                  title="الرصيد المتبقي عند الانتهاء"
                  value={`${selectedPath.final_remaining_plan_credits} س`}
                  subtitle={
                    selectedPath.final_remaining_plan_credits === 0
                      ? "تصفير كامل لمتطلبات الخطة"
                      : "ساعات متبقية بعد أقصى مدى"
                  }
                  icon={<SparklesIcon className="h-5 w-5" />}
                />
              </div>

              {/* Semester Stepper Timeline */}
              <div className="space-y-6">
                <div className="border-b border-[#EDE2C5] pb-3">
                  <h2 className="text-base font-bold text-[#28241C]">
                    التوزيع الفصلي المقترح للمسار #{selectedPath.rank}
                  </h2>
                  <p className="text-xs text-[#726B5E]">
                    تسلسل الفصول القادمة والمواد المجدولة في كل فصل وفق شجرة المتطلبات السابقة.
                  </p>
                </div>

                <div className="relative space-y-6 before:absolute before:right-6 before:top-4 before:bottom-4 before:w-0.5 before:bg-[#EDE2C5]">
                  {selectedPath.semesters.map((sem: ModeledSemesterResponse) => (
                    <div key={sem.semester_index} className="relative pr-14">
                      {/* Timeline Dot */}
                      <div className="absolute right-3.5 top-5 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full bg-[#E2AD27] font-mono text-xs font-bold text-[#28241C] ring-4 ring-white shadow-xs">
                        {sem.semester_index}
                      </div>

                      {/* Semester Card */}
                      <div className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-xs space-y-4">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-[#EDE2C5]/60 pb-3">
                          <div>
                            <span className="font-mono text-xs font-bold text-[#A66F00]">
                              الفصل الدراسي القادم #{sem.semester_index}
                            </span>
                            <h3 className="text-sm font-bold text-[#28241C]">
                              عبء فصلي: {sem.plan_option.total_credit_hours} ساعات معتمدة ({sem.plan_option.total_courses} مواد)
                            </h3>
                          </div>

                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-[#726B5E]">الرصيد بعد هذا الفصل:</span>
                            <span className="font-mono font-bold text-emerald-800">
                              {sem.completed_plan_credits_after} س منجزة
                            </span>
                            <span className="text-[11px] text-[#726B5E]">
                              (المتبقي: {sem.remaining_plan_credits_after} س)
                            </span>
                          </div>
                        </div>

                        {/* Courses in this semester */}
                        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                          {sem.plan_option.courses.map((course: PlannedCourseEntryResponse) => (
                            <div
                              key={course.course_code}
                              className="flex items-center justify-between rounded-2xl border border-[#EDE2C5] bg-[#FFFCF4] p-3 text-xs"
                            >
                              <div>
                                <span className="font-mono font-bold text-[#28241C]" dir="ltr">
                                  {course.course_code}
                                </span>
                                {course.course_name_ar ? (
                                  <span className="block text-[11px] text-[#726B5E] truncate max-w-[160px]">
                                    {course.course_name_ar}
                                  </span>
                                ) : null}
                              </div>

                              <div className="text-left font-mono">
                                <span className="rounded-md bg-[#FFF4C7] px-2 py-0.5 text-[10px] font-bold text-[#805400]">
                                  {course.credit_hours} س
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>

                        {sem.newly_satisfied_requirement_group_codes.length > 0 ? (
                          <div className="flex items-center gap-2 pt-2 text-xs text-emerald-800">
                            <CheckCircleIcon className="h-4 w-4 shrink-0" />
                            <span>
                              يستوفي هذا الفصل مجموعات المتطلبات:{" "}
                              <strong>{sem.newly_satisfied_requirement_group_codes.join(", ")}</strong>
                            </span>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Disclaimer */}
              <div className="rounded-2xl border border-[#EDE2C5] bg-[#FFF9E8] p-4 text-xs text-[#726B5E] flex items-center gap-3">
                <InfoIcon className="h-5 w-5 text-[#A66F00] shrink-0" />
                <p>
                  <strong>إخلاء مسؤولية تنظيمي:</strong> مسار الدرجة العلمية هو نموذج محاكاة استرشادي مبني على التسلسل المنطقي لفتح المتطلبات السابقة. قد يتغير ترتيب التسجيل الفعلي تبعاً للمواد المطروحة في الجداول الدراسية لكل فصل.
                </p>
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        !loading && (
          <EmptyState
            title="ابدأ محاكاة مسار التخرج"
            description="حدد سقف الساعات الفصلي وعدد الفصول المرغوبة واضغط على 'توليد ومحاكاة مسار التخرج' لحساب الخطة حتى التخرج."
            icon={<DegreePathIcon className="h-7 w-7" />}
          />
        )
      )}
    </div>
  );
}
