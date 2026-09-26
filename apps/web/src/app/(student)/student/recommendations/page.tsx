"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/auth/auth-provider";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type {
  DashboardError,
  RecommendationCandidateResponse,
  RecommendationResponse,
  ReviewRequiredCourseResponse,
} from "@/lib/api/student-types";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert, isRetryableError } from "@/components/ui/ErrorAlert";
import { LoadingSkeletonCard } from "@/components/ui/LoadingSkeleton";
import { StatCard } from "@/components/ui/StatCard";
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  EligibilityIcon,
  InfoIcon,
  RecommendationsIcon,
  SparklesIcon,
} from "@/components/ui/Icons";

export default function RecommendationsPage() {
  const auth = useAuth();
  const client = useAuthenticatedApi();
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<DashboardError | null>(null);
  const [loading, setLoading] = useState(true);

  // Filter
  const [filterType, setFilterType] = useState<"ALL" | "UNLOCKS" | "COMPLETES">("ALL");

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new StudentApiService(client);
      const res = await api.getRecommendations();
      setData(res);
    } catch {
      setError("SERVER_ERROR");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (auth.isAuthenticated) {
      void fetchRecommendations();
    }
  }, [auth.isAuthenticated]);

  const stats = useMemo(() => {
    if (!data) return { total: 0, unlocks: 0, completes: 0, review: 0 };
    const total = data.ranked_recommendations.length;
    const unlocks = data.ranked_recommendations.filter((r) => r.newly_eligible_count > 0).length;
    const completes = data.ranked_recommendations.filter((r) => r.completes_requirement_group).length;
    const review = data.review_required_courses.length;
    return { total, unlocks, completes, review };
  }, [data]);

  const filteredRecommendations = useMemo(() => {
    if (!data?.ranked_recommendations) return [];
    return data.ranked_recommendations.filter((r) => {
      if (filterType === "UNLOCKS") return r.newly_eligible_count > 0;
      if (filterType === "COMPLETES") return r.completes_requirement_group;
      return true;
    });
  }, [data, filterType]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-2 border-b border-[#EDE2C5] pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-[#A66F00]/10 px-2.5 py-0.5 text-xs font-bold text-[#A66F00]">
              التوجيه الأكاديمي الحتمي
            </span>
            <span className="text-xs text-[#726B5E]">ترتيب خوارزمي معتمد</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#28241C]">
            التوصيات الأكاديمية الذكية
          </h1>
          <p className="text-xs text-[#726B5E]">
            ترتيب منهجي للمواد الموصى بتسجيلها وفق الأثر الأكاديمي، فتح المتطلبات اللاحقة، واستيفاء المجموعات.
          </p>
        </div>

        {data ? (
          <div className="flex items-center gap-2">
            <Badge variant="gold">
              سياسة التوصية: {data.recommendation_policy_version}
            </Badge>
          </div>
        ) : null}
      </div>

      {/* Error state */}
      {error ? (
        <ErrorAlert
          error={error}
          onRetry={isRetryableError(error) ? fetchRecommendations : undefined}
        />
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

      {/* Content */}
      {!loading && !error && data ? (
        <div className="space-y-8">
          {/* Summary Stat Cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard
              title="إجمالي الموصى بها"
              value={stats.total}
              subtitle="مواد جاهزة ومستوفاة للتسجيل"
              icon={<RecommendationsIcon className="h-5 w-5" />}
            />
            <StatCard
              title="تفتح مواداً لاحقة"
              value={stats.unlocks}
              subtitle="تفك تشابك شجرة المواد"
              icon={<SparklesIcon className="h-5 w-5" />}
            />
            <StatCard
              title="تُتم استيفاء مجموعة"
              value={stats.completes}
              subtitle="تغلق متطلب تخرج إلزامي"
              icon={<CheckCircleIcon className="h-5 w-5" />}
            />
            <StatCard
              title="تتطلب مراجعة"
              value={stats.review}
              subtitle="حالات بحاجة لموافقة المرشد"
              icon={<AlertTriangleIcon className="h-5 w-5" />}
            />
          </div>

          {/* Methodology Banner */}
          <div className="rounded-3xl border border-[#EDE2C5] bg-[#FFF9E8] p-5 text-xs text-[#726B5E]">
            <div className="flex items-start gap-3">
              <SparklesIcon className="h-5 w-5 text-[#A66F00] shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h3 className="font-bold text-[#28241C]">منهجية الترتيب الأكاديمي الحتمي</h3>
                <p className="leading-relaxed">
                  {data.methodology_note ||
                    "يتم ترتيب المواد بناءً على معايير صارمة: أولوية متطلبات التخصص الإجبارية، الأثر في فتح مواد لاحقة، والمساهمة في تقليص الساعات المتبقية للمجموعة."}
                </p>
              </div>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex flex-wrap items-center gap-2 border-b border-[#EDE2C5] pb-4">
            <span className="text-xs font-bold text-[#726B5E]">تصفية التوصيات:</span>
            {[
              { key: "ALL", label: `كافة المواد (${stats.total})` },
              { key: "UNLOCKS", label: `تفتح مواداً لاحقة (${stats.unlocks})` },
              { key: "COMPLETES", label: `تُتم مجموعة (${stats.completes})` },
            ].map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setFilterType(tab.key as typeof filterType)}
                className={`rounded-xl px-3.5 py-1.5 text-xs font-bold transition-colors ${
                  filterType === tab.key
                    ? "bg-[#E2AD27] text-[#28241C] shadow-xs"
                    : "bg-white text-[#726B5E] border border-[#EDE2C5] hover:bg-[#FFF9E8]"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Ranked List */}
          {filteredRecommendations.length === 0 ? (
            <EmptyState
              title="لا توجد توصيات مطابقة"
              description="لم يتم العثور على مواد مطابقة لمعيار التصفية الحالي."
            />
          ) : (
            <div className="space-y-4">
              {filteredRecommendations.map((rec: RecommendationCandidateResponse) => (
                <div
                  key={rec.course_code}
                  className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-xs transition-all hover:border-[#E2AD27]/70"
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex items-start gap-4">
                      {/* Rank Badge */}
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#FFF4C7] font-mono text-base font-extrabold text-[#A66F00] border border-[#EDE2C5]">
                        #{rec.rank}
                      </div>

                      <div className="space-y-1.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-sm font-bold text-[#28241C]" dir="ltr">
                            {rec.course_code}
                          </span>
                          {rec.course_name_ar ? (
                            <span className="text-sm font-bold text-[#28241C]">
                              • {rec.course_name_ar}
                            </span>
                          ) : null}
                          <span className="rounded-md bg-[#FFF9E8] px-2 py-0.5 text-[10px] font-mono font-bold text-[#A66F00] border border-[#EDE2C5]" dir="ltr">
                            {rec.credit_hours} ساعات
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          <span className="rounded-md bg-[#FFFCF4] px-2 py-0.5 text-xs text-[#726B5E] border border-[#EDE2C5]">
                            المجموعة: <strong className="font-mono" dir="ltr">{rec.requirement_group_code}</strong> (
                            {rec.requirement_type === "MANDATORY" ? "إجباري" : "اختياري"})
                          </span>

                          {rec.completes_requirement_group ? (
                            <Badge variant="success">تُتم استيفاء المجموعة بالكامل</Badge>
                          ) : null}

                          {rec.newly_eligible_count > 0 ? (
                            <Badge variant="gold">
                              تفتح {rec.newly_eligible_count} مواد لاحقة
                            </Badge>
                          ) : null}

                          {rec.previously_attempted ? (
                            <Badge variant="warning">إعادة لرفع المعدل</Badge>
                          ) : null}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <Link
                        href={`/student/eligibility`}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-[#EDE2C5] bg-[#FFF9E8] px-3.5 py-2 text-xs font-bold text-[#805400] hover:bg-[#FFF4C7] hover:border-[#E2AD27] transition-all"
                      >
                        <EligibilityIcon className="h-4 w-4" />
                        <span>فحص الأهلية</span>
                      </Link>
                    </div>
                  </div>

                  {/* Unlocked Courses / Impact Grid */}
                  <div className="mt-5 rounded-2xl bg-[#FFFCF4] p-4 border border-[#EDE2C5]/70 text-xs">
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <div>
                        <span className="text-[#726B5E]">المساهمة في رصيد الخطة: </span>
                        <strong className="font-mono text-[#28241C]">
                          {rec.effective_credit_contribution} ساعة
                        </strong>
                        <span className="text-[11px] text-[#726B5E] mr-1">
                          (المتبقي للمجموعة: من {rec.group_remaining_credits_before} إلى {rec.group_remaining_credits_after} س)
                        </span>
                      </div>

                      {rec.newly_eligible_course_codes.length > 0 ? (
                        <div className="flex items-center gap-2">
                          <span className="text-[#726B5E] shrink-0">المواد التي ستفتح بعدها:</span>
                          <div className="flex flex-wrap gap-1">
                            {rec.newly_eligible_course_codes.map((c) => (
                              <span
                                key={c}
                                className="rounded-md bg-white px-2 py-0.5 font-mono text-[11px] font-bold text-[#A66F00] border border-[#EDE2C5]"
                                dir="ltr"
                              >
                                {c}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="text-[#726B5E]">
                          لا تفتح متطلبات لاحقة مباشرة
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Review-Required Courses */}
          {data.review_required_courses.length > 0 ? (
            <div className="rounded-3xl border border-amber-300 bg-white p-6 shadow-xs space-y-4">
              <div className="flex items-center gap-2">
                <AlertTriangleIcon className="h-5 w-5 text-amber-700" />
                <h3 className="text-sm font-bold text-[#28241C]">
                  مواد تتطلب مراجعة وتنسيق مع المرشد الأكاديمي ({data.review_required_courses.length})
                </h3>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {data.review_required_courses.map((course: ReviewRequiredCourseResponse) => (
                  <div
                    key={course.course_code}
                    className="rounded-2xl border border-amber-200 bg-amber-50/50 p-4 text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-[#28241C]" dir="ltr">
                        {course.course_code} {course.course_name_ar ? `(${course.course_name_ar})` : ""}
                      </span>
                      <Badge variant="review" size="sm">مراجعة مرشد</Badge>
                    </div>
                    <p className="text-[11px] text-amber-900">
                      <strong>سبب المراجعة: </strong>
                      {course.review_reason}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {/* Limitations and Governance */}
          <div className="rounded-2xl border border-[#EDE2C5] bg-[#FFF9E8] p-4 text-xs text-[#726B5E] space-y-2">
            <div className="flex items-center gap-2 font-bold text-[#28241C]">
              <InfoIcon className="h-4 w-4 text-[#A66F00]" />
              <span>محددات خوارزمية التوصية والمسؤولية الأكاديمية:</span>
            </div>
            <ul className="list-disc list-inside space-y-1 pr-2 text-[11px]">
              {data.limitations.map((lim, idx) => (
                <li key={idx}>{lim}</li>
              ))}
              <li>هذه التوصيات ذات طابع إرشادي وتخضع للشعب المطروحة في جدول الفصل الرسمي.</li>
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  );
}
