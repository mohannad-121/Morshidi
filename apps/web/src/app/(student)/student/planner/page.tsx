"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/auth/auth-provider";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type {
  PlannedCourseEntryResponse,
  SemesterPlanOptionResponse,
  SemesterPlanRequest,
  SemesterPlannerResponse,
} from "@/lib/api/student-types";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { LoadingSkeletonCard } from "@/components/ui/LoadingSkeleton";
import { StatCard } from "@/components/ui/StatCard";
import {
  CheckCircleIcon,
  CoursesIcon,
  EligibilityIcon,
  InfoIcon,
  PlannerIcon,
  SparklesIcon,
} from "@/components/ui/Icons";

export default function PlannerPage() {
  const auth = useAuth();
  const client = useAuthenticatedApi();

  // Constraints
  const [maxCreditHours, setMaxCreditHours] = useState<number>(15);
  const [maxCourses, setMaxCourses] = useState<number | undefined>(undefined);
  const [maxOptions, setMaxOptions] = useState<number>(3);

  // States
  const [result, setResult] = useState<SemesterPlannerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedOptionIndex, setSelectedOptionIndex] = useState<number>(0);

  const handleGeneratePlans = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    setErrorMessage(null);
    setResult(null);

    try {
      const api = new StudentApiService(client);
      const req: SemesterPlanRequest = {
        max_credit_hours: maxCreditHours,
        max_courses: maxCourses && maxCourses > 0 ? maxCourses : null,
        max_options: maxOptions,
      };
      const data = await api.createSemesterPlans(req);
      setResult(data);
      setSelectedOptionIndex(0);
    } catch {
      setErrorMessage("تعذر توليد خطة الفصل الدراسي. تأكد من توفر مواد مؤهلة في خطتك الأكاديمية.");
    } finally {
      setLoading(false);
    }
  };

  const selectedOption: SemesterPlanOptionResponse | null =
    result?.plan_options && result.plan_options.length > selectedOptionIndex
      ? result.plan_options[selectedOptionIndex]
      : null;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-[#EDE2C5] pb-5">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[#A66F00]/10 px-2.5 py-0.5 text-xs font-bold text-[#A66F00]">
            المخطط الفصلي الرياضي
          </span>
          <span className="text-xs text-[#726B5E]">توليد خيارات مثلى</span>
        </div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#28241C]">
          مخطط الفصل الدراسي
        </h1>
        <p className="text-xs text-[#726B5E]">
          توليد باقات تسجيل فصلي متوازنة ومثلى، تراعي حدود الساعات، الأثر الأكاديمي، والمتطلبات السابقة.
        </p>
      </div>

      {/* Constraints Config Card */}
      <div className="rounded-3xl border border-[#EDE2C5] bg-white p-7 shadow-xs">
        <form onSubmit={handleGeneratePlans} className="space-y-6">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            {/* Max Credits */}
            <div>
              <label className="block text-xs font-bold text-[#28241C] mb-2">
                الحد الأقصى للساعات المعتمدة *
              </label>
              <div className="flex items-center gap-2">
                {[12, 15, 18].map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setMaxCreditHours(preset)}
                    className={`rounded-xl px-3 py-1.5 font-mono text-xs font-bold transition-colors ${
                      maxCreditHours === preset
                        ? "bg-[#E2AD27] text-[#28241C] shadow-xs"
                        : "bg-[#FFF9E8] text-[#726B5E] border border-[#EDE2C5] hover:bg-[#FFF4C7]"
                    }`}
                  >
                    {preset} س
                  </button>
                ))}
                <input
                  type="number"
                  min={3}
                  max={24}
                  value={maxCreditHours}
                  onChange={(e) => setMaxCreditHours(Number(e.target.value))}
                  className="w-20 rounded-xl border border-[#EDE2C5] bg-white p-2 font-mono text-xs font-bold text-center text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
                />
              </div>
            </div>

            {/* Max Courses */}
            <div>
              <label className="block text-xs font-bold text-[#28241C] mb-2">
                الحد الأقصى لعدد المواد (اختياري)
              </label>
              <input
                type="number"
                min={1}
                max={8}
                placeholder="بدون حد (تلقائي)"
                value={maxCourses ?? ""}
                onChange={(e) =>
                  setMaxCourses(e.target.value ? Number(e.target.value) : undefined)
                }
                className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 font-mono text-xs text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
              />
            </div>

            {/* Max Options */}
            <div>
              <label className="block text-xs font-bold text-[#28241C] mb-2">
                عدد الخيارات البديلة المطلوبة
              </label>
              <select
                value={maxOptions}
                onChange={(e) => setMaxOptions(Number(e.target.value))}
                className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 text-xs text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
              >
                <option value={1}>خيار واحد فقط</option>
                <option value={2}>خياران (أساسي وبديل)</option>
                <option value={3}>3 خيارات (موصى به)</option>
                <option value={5}>5 خيارات متقدمة</option>
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
              <span>{loading ? "جاري احتساب الخيارات الفصلية..." : "توليد خيارات الفصل الدراسي"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Error State */}
      {errorMessage ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-xs text-red-800">
          <p className="font-bold">{errorMessage}</p>
        </div>
      ) : null}

      {/* Loading Skeleton */}
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

      {/* Results */}
      {!loading && result && result.plan_options.length > 0 ? (
        <div className="space-y-6">
          {/* Options Selection Header */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-[#726B5E]">خيارات الباقات المولدة:</span>
              {result.plan_options.map((option, idx) => (
                <button
                  key={option.rank}
                  type="button"
                  onClick={() => setSelectedOptionIndex(idx)}
                  className={`rounded-2xl px-4 py-2 text-xs font-bold transition-all ${
                    selectedOptionIndex === idx
                      ? "bg-[#E2AD27] text-[#28241C] shadow-xs font-extrabold"
                      : "bg-white text-[#726B5E] border border-[#EDE2C5] hover:bg-[#FFF9E8]"
                  }`}
                >
                  الخيار #{option.rank} {idx === 0 ? "(الأفضل تقييماً)" : ""}
                </button>
              ))}
            </div>

            <span className="text-xs font-mono text-[#726B5E]">
              تم فحص {result.evaluated_candidate_count} مادة محتملة
            </span>
          </div>

          {selectedOption ? (
            <div className="space-y-6">
              {/* Option Summary Card */}
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <StatCard
                  title="إجمالي الساعات"
                  value={`${selectedOption.total_credit_hours} س`}
                  subtitle={`من أصل حد ${maxCreditHours} ساعة`}
                  icon={<PlannerIcon className="h-5 w-5" />}
                  variant="gold"
                />
                <StatCard
                  title="عدد المواد"
                  value={selectedOption.total_courses}
                  subtitle={`${selectedOption.mandatory_course_count} مواد إجبارية`}
                  icon={<CoursesIcon className="h-5 w-5" />}
                />
                <StatCard
                  title="إضافة رصيد للخطة"
                  value={`${selectedOption.completed_plan_credit_delta} س`}
                  subtitle="مساهمة فعلية في متطلبات التخرج"
                  icon={<CheckCircleIcon className="h-5 w-5" />}
                />
                <StatCard
                  title="تفتح مواداً لاحقة"
                  value={selectedOption.newly_eligible_count}
                  subtitle="مواد ستصبح متاحة في الفصل القادم"
                  icon={<SparklesIcon className="h-5 w-5" />}
                />
              </div>

              {/* Course List in Selected Option */}
              <div className="overflow-hidden rounded-3xl border border-[#EDE2C5] bg-white shadow-xs">
                <div className="border-b border-[#EDE2C5] bg-[#FFF9E8]/80 px-6 py-4 flex items-center justify-between">
                  <h3 className="font-bold text-[#28241C] text-sm">
                    مواد الباقة المقترحة للخيار #{selectedOption.rank}
                  </h3>
                  <Badge variant="gold">
                    مجموع رتب التوصية: {selectedOption.recommendation_rank_sum}
                  </Badge>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-right text-xs">
                    <thead>
                      <tr className="border-b border-[#EDE2C5] bg-[#FFFDF7] text-[#726B5E]">
                        <th className="px-6 py-3.5 font-bold">رمز المادة</th>
                        <th className="px-6 py-3.5 font-bold">اسم المادة</th>
                        <th className="px-6 py-3.5 font-bold">الساعات</th>
                        <th className="px-6 py-3.5 font-bold">المجموعة التابعة</th>
                        <th className="px-6 py-3.5 font-bold">النوع</th>
                        <th className="px-6 py-3.5 font-bold">رتبة التوصية</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#EDE2C5]/50">
                      {selectedOption.courses.map((course: PlannedCourseEntryResponse) => (
                        <tr key={course.course_code} className="hover:bg-[#FFFDF7] transition-colors">
                          <td className="px-6 py-4 font-mono font-bold text-[#28241C]" dir="ltr">
                            {course.course_code}
                          </td>
                          <td className="px-6 py-4 font-bold text-[#28241C]">
                            {course.course_name_ar ?? "—"}
                          </td>
                          <td className="px-6 py-4 font-mono text-[#28241C]">
                            {course.credit_hours} ساعات
                          </td>
                          <td className="px-6 py-4 font-mono text-[#726B5E]" dir="ltr">
                            {course.requirement_group_code}
                          </td>
                          <td className="px-6 py-4">
                            <span className="rounded-md bg-[#FFF9E8] px-2 py-0.5 text-[10px] font-semibold text-[#805400] border border-[#EDE2C5]">
                              {course.requirement_type === "MANDATORY" ? "إجباري" : "اختياري"}
                            </span>
                          </td>
                          <td className="px-6 py-4 font-mono font-bold text-[#A66F00]">
                            #{course.phase7_rank}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Newly Eligible Courses */}
              {selectedOption.newly_eligible_course_codes.length > 0 ? (
                <div className="rounded-3xl border border-[#EDE2C5] bg-[#FFFCF4] p-5 text-xs">
                  <div className="flex items-center gap-2 mb-2 font-bold text-[#28241C]">
                    <SparklesIcon className="h-4 w-4 text-[#A66F00]" />
                    <span>المواد التي ستفتح للتسجيل عند اجتياز هذه الباقة:</span>
                  </div>
                  <div className="flex flex-wrap gap-2 pt-1">
                    {selectedOption.newly_eligible_course_codes.map((code) => (
                      <span
                        key={code}
                        className="rounded-xl bg-white px-3 py-1 font-mono text-xs font-bold text-[#A66F00] border border-[#EDE2C5] shadow-xs"
                        dir="ltr"
                      >
                        {code}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              {/* Non-Binding Notice */}
              <div className="rounded-2xl border border-[#EDE2C5] bg-[#FFF9E8] p-4 text-xs text-[#726B5E] flex items-center gap-3">
                <InfoIcon className="h-5 w-5 text-[#A66F00] shrink-0" />
                <p>
                  <strong>إخلاء مسؤولية تنظيمي:</strong> هذه الباقة مقترحة لأغراض التخطيط الاسترشادي والمحاكاة وليست تسجيلاً رسمياً. التسجيل النهائي يتم عبر بوابة التسجيل الجامعية الرسمية بناءً على الشعب المطروحة.
                </p>
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        !loading && (
          <EmptyState
            title="حدد المعايير لتوليد خيارات الفصل"
            description="اضبط الحد الأقصى للساعات المعتمدة وعدد الخيارات البديلة واضغط على 'توليد خيارات الفصل الدراسي' لبدء التخطيط."
            icon={<PlannerIcon className="h-7 w-7" />}
          />
        )
      )}
    </div>
  );
}
