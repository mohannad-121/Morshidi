"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { SignOutButton } from "@/auth/sign-out-button";
import { useAuth } from "@/auth/auth-provider";
import {
  AuthenticatedApiClient,
  AuthenticatedApiError,
} from "@/lib/api/authenticated-client";
import type {
  AcademicProfileResponse,
  AcademicProgressResponse,
  DashboardError,
} from "@/lib/api/student-types";
import { Badge } from "@/components/ui/Badge";
import { StatCard } from "@/components/ui/StatCard";
import { ProgressBar } from "@/components/ui/ProgressBar";
import {
  DegreePathIcon,
  EligibilityIcon,
  PlannerIcon,
  RecommendationsIcon,
  RefreshIcon,
  SparklesIcon,
} from "@/components/ui/Icons";

type StudentPageProps = {
  client?: AuthenticatedApiClient;
};

function displayValue(value: string | number | null | undefined): string {
  return value === null || value === undefined ? "غير متوفر" : String(value);
}

function errorMessage(error: DashboardError): string {
  switch (error) {
    case "FORBIDDEN":
      return "غير مصرح لك بالوصول إلى هذه البيانات الأكاديمية.";
    case "NOT_FOUND":
      return "لم يتم العثور على ملف أكاديمي";
    case "VALIDATION_ERROR":
      return "بيانات الطلب غير صالحة.";
    case "SERVICE_UNAVAILABLE":
      return "الخدمة غير متوفرة حالياً. يُرجى المحاولة لاحقاً.";
    case "SERVER_ERROR":
      return "حدث خطأ في الخادم أثناء تحميل البيانات الأكاديمية.";
    case "NETWORK_ERROR":
      return "تعذّر الاتصال بالخادم. تحقق من اتصال الإنترنت.";
    case "CONFIGURATION_ERROR":
      return "تعذّر تهيئة الاتصال بالخادم. تحقق من إعدادات النظام.";
    default:
      return "تعذّر تحميل البيانات الأكاديمية.";
  }
}

function isRetryable(error: DashboardError): boolean {
  return error !== "FORBIDDEN" && error !== "CONFIGURATION_ERROR";
}

function mapClientError(error: unknown): DashboardError {
  if (error instanceof AuthenticatedApiError) {
    switch (error.code) {
      case "FORBIDDEN":
        return "FORBIDDEN";
      case "VALIDATION_ERROR":
        return "VALIDATION_ERROR";
      case "SERVICE_UNAVAILABLE":
        return "SERVICE_UNAVAILABLE";
      case "SERVER_ERROR":
        return "SERVER_ERROR";
      case "NETWORK_ERROR":
        return "NETWORK_ERROR";
      default:
        return "UNKNOWN";
    }
  }
  return "UNKNOWN";
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 404) {
    throw new Error("NOT_FOUND");
  }
  if (!response.ok) {
    if (response.status === 403) throw new AuthenticatedApiError("FORBIDDEN", 403);
    if (response.status === 422) {
      throw new AuthenticatedApiError("VALIDATION_ERROR", 422);
    }
    if (response.status === 503) {
      throw new AuthenticatedApiError("SERVICE_UNAVAILABLE", 503);
    }
    if (response.status >= 500) {
      throw new AuthenticatedApiError("SERVER_ERROR", response.status);
    }
    throw new Error(`HTTP_${response.status}`);
  }
  return (await response.json()) as T;
}

export default function StudentPage({ client: injectedClient }: StudentPageProps) {
  const auth = useAuth();
  const [profile, setProfile] = useState<AcademicProfileResponse | null>(null);
  const [progress, setProgress] = useState<AcademicProgressResponse | null>(null);
  const [dashboardError, setDashboardError] = useState<DashboardError | null>(null);
  const [isReloading, setIsReloading] = useState(false);
  const [refreshIndex, setRefreshIndex] = useState(0);

  const client = useMemo(() => {
    if (injectedClient) return injectedClient;
    try {
      return new AuthenticatedApiClient({
        getAccessToken: auth.getAccessToken,
        refreshAccessToken: auth.refreshAccessToken,
        invalidateSession: auth.invalidateSession,
      });
    } catch {
      return null;
    }
  }, [
    injectedClient,
    auth.getAccessToken,
    auth.refreshAccessToken,
    auth.invalidateSession,
  ]);

  const activeError: DashboardError | null =
    auth.status === "authenticated" && !client
      ? "CONFIGURATION_ERROR"
      : dashboardError;

  const loading =
    isReloading ||
    (auth.status === "authenticated" &&
      Boolean(client) &&
      !profile &&
      !progress &&
      !activeError);

  const handleRefresh = () => {
    setIsReloading(true);
    setDashboardError(null);
    setRefreshIndex((prev) => prev + 1);
  };

  useEffect(() => {
    if (auth.status !== "authenticated" || !client) return;

    let ignore = false;

    void Promise.all([
      client.request("/api/v1/me/academic-profile"),
      client.request("/api/v1/me/academic-progress"),
    ])
      .then(async ([profileRes, progressRes]) => {
        if (ignore) return;
        const [profileData, progressData] = await Promise.all([
          parseResponse<AcademicProfileResponse>(profileRes),
          parseResponse<AcademicProgressResponse>(progressRes),
        ]);
        if (ignore) return;
        setProfile(profileData);
        setProgress(progressData);
        setDashboardError(null);
        setIsReloading(false);
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setProfile(null);
          setProgress(null);
          if (error instanceof Error && error.message === "NOT_FOUND") {
            setDashboardError("NOT_FOUND");
          } else {
            setDashboardError(mapClientError(error));
          }
          setIsReloading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [auth.status, client, refreshIndex]);

  if (auth.isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#FFFCF4] p-6" dir="rtl">
        <p role="status" className="text-sm font-semibold text-[#A66F00] animate-pulse">
          جاري التحقق من جلسة الدخول…
        </p>
      </main>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#FFFCF4] p-6" dir="rtl">
        <section className="w-full max-w-2xl rounded-3xl border border-[#EDE2C5] bg-[#FFFFFF] p-8 shadow-sm">
          <p className="text-[#28241C] font-semibold">يجب تسجيل الدخول للوصول إلى لوحة الطالب.</p>
        </section>
      </main>
    );
  }

  return (
    <div className="space-y-8" dir="rtl">
      {/* Header & Welcome banner */}
      <div className="relative overflow-hidden rounded-3xl border border-[#EDE2C5] bg-gradient-to-l from-[#FFF4C7]/80 via-[#FFF9E8] to-[#FFFFFF] p-6 shadow-xs sm:p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-[#A66F00]/10 px-2.5 py-0.5 text-xs font-bold text-[#A66F00]">
                مرشدي
              </span>
              <span className="text-xs text-[#726B5E]">بوابة الطالب الأكاديمية</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-[#28241C] sm:text-3xl">
              لوحة الطالب
            </h1>
            <p className="mt-1 text-sm text-[#726B5E]">
              مرحباً،{" "}
              <span className="font-semibold text-[#28241C]" dir="ltr">
                {auth.user?.email ?? "غير متوفر"}
              </span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 self-start sm:self-center">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading || !client}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-[#EDE2C5] bg-white px-4 py-2 text-xs font-semibold text-[#28241C] shadow-xs transition-colors hover:bg-[#FFF9E8] disabled:opacity-60"
              aria-label="تحديث البيانات"
            >
              <RefreshIcon className={`h-3.5 w-3.5 text-[#A66F00] ${loading ? "animate-spin" : ""}`} />
              <span>تحديث البيانات</span>
            </button>
            <SignOutButton />
          </div>
        </div>

        {/* Governance banner */}
        <div className="mt-4 flex items-center gap-2 border-t border-[#EDE2C5]/60 pt-3 text-[11px] text-[#726B5E]">
          <SparklesIcon className="h-3.5 w-3.5 text-[#A66F00]" />
          <span>
            الذكاء الاصطناعي يشرح — القواعد الأكاديمية واللوائح المعتمدة تقرر.
          </span>
        </div>
      </div>

      {/* Loading state */}
      {loading ? (
        <section className="rounded-3xl border border-[#EDE2C5] bg-white p-8 shadow-xs" role="status">
          <p className="text-sm font-semibold text-[#A66F00] animate-pulse">
            جاري تحميل البيانات الأكاديمية…
          </p>
        </section>
      ) : null}

      {/* Active Error */}
      {!loading && activeError ? (
        <section
          role={activeError === "NOT_FOUND" ? undefined : "alert"}
          className="rounded-3xl border border-red-200 bg-red-50/80 p-8 shadow-xs"
        >
          <p className="text-red-900 font-semibold">{errorMessage(activeError)}</p>
          {isRetryable(activeError) ? (
            <div className="mt-5 flex items-center gap-3">
              <button
                type="button"
                onClick={handleRefresh}
                className="button-primary"
              >
                إعادة المحاولة
              </button>
            </div>
          ) : null}
        </section>
      ) : null}

      {/* Data Loaded */}
      {!loading && !activeError && profile && progress ? (
        <div className="space-y-8">
          {/* Quick Stats Grid */}
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="إجمالي ساعات الخطة"
              value={`${displayValue(progress.plan_total_required_credits)} ساعة`}
              subtitle="ساعة معتمدة مطلوبة للتخرج"
              variant="warm"
            />
            <StatCard
              title="الساعات المنجزة"
              value={`${displayValue(progress.completed_plan_credits)} ساعة`}
              subtitle="ساعة محتسبة ومستوفاة"
              badge={
                progress.all_modeled_plan_requirements_satisfied ? (
                  <Badge variant="success" size="sm">مكتمل</Badge>
                ) : undefined
              }
            />
            <StatCard
              title="الساعات قيد التسجيل"
              value={`${displayValue(progress.in_progress_plan_credits)} ساعة`}
              subtitle="مسجلة في الفصل الحالي"
            />
            <StatCard
              title="الساعات المتبقية"
              value={`${displayValue(progress.remaining_plan_credits)} ساعة`}
              subtitle="ساعة مطلوب إتمامها"
              variant="gold"
            />
          </div>

          {/* Profile & Progress Section */}
          <section className="grid gap-6 lg:grid-cols-2">
            {/* Academic Profile Card */}
            <article className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-xs">
              <div className="flex items-center justify-between border-b border-[#EDE2C5]/60 pb-4">
                <h2 className="text-xl font-bold text-[#28241C]">الملف الأكاديمي</h2>
                <Badge variant="gold" size="sm">معتمد</Badge>
              </div>
              <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-semibold text-[#726B5E]">معرّف الخطة الدراسية</dt>
                  <dd className="mt-1 font-mono text-xs break-all text-[#28241C]" dir="ltr">
                    {displayValue(profile.study_plan_id)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-[#726B5E]">المعدل التراكمي المسجل</dt>
                  <dd className="mt-1 font-mono text-lg font-bold text-[#28241C]">
                    {displayValue(profile.reported_cumulative_gpa)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-[#726B5E]">مقياس المعدل</dt>
                  <dd className="mt-1 font-mono text-sm font-semibold text-[#28241C]">
                    {displayValue(profile.reported_gpa_scale)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-[#726B5E]">الساعات المكتسبة المسجلة</dt>
                  <dd className="mt-1 font-mono text-sm font-semibold text-[#28241C]">
                    {displayValue(profile.reported_earned_credit_hours)}
                  </dd>
                </div>
              </dl>
            </article>

            {/* Academic Progress Card */}
            <article className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-xs">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#EDE2C5]/60 pb-4">
                <h2 className="text-xl font-bold text-[#28241C]">التقدم الأكاديمي</h2>
                {progress.all_modeled_plan_requirements_satisfied ? (
                  <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
                    مستوفاة بالكامل
                  </span>
                ) : (
                  <Badge variant="warning">قيد الإنجاز</Badge>
                )}
              </div>
              <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-semibold text-[#726B5E]">إجمالي ساعات الخطة</dt>
                  <dd className="mt-1 font-mono text-base font-bold text-[#28241C]">
                    {displayValue(progress.plan_total_required_credits)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-[#726B5E]">الساعات المنجزة</dt>
                  <dd className="mt-1 font-mono text-base font-bold text-[#28241C]">
                    {displayValue(progress.completed_plan_credits)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-[#726B5E]">الساعات قيد التسجيل</dt>
                  <dd className="mt-1 font-mono text-base font-bold text-[#28241C]">
                    {displayValue(progress.in_progress_plan_credits)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-[#726B5E]">الساعات المتبقية</dt>
                  <dd className="mt-1 font-mono text-base font-bold text-[#28241C]">
                    {displayValue(progress.remaining_plan_credits)}
                  </dd>
                </div>
                <div className="sm:col-span-2 rounded-xl bg-[#FFF9E8] p-3 border border-[#EDE2C5]">
                  <dt className="text-xs font-semibold text-[#726B5E]">المجموعات المستوفاة</dt>
                  <dd className="mt-1 font-mono text-sm font-bold text-[#28241C]">
                    {progress.satisfied_requirement_group_count} من {progress.total_requirement_group_count}
                  </dd>
                  <div className="mt-2">
                    <ProgressBar
                      completed={progress.satisfied_requirement_group_count}
                      total={progress.total_requirement_group_count}
                      showPercent={false}
                    />
                  </div>
                </div>
              </dl>
            </article>
          </section>

          {/* Quick Actions Panel */}
          <div className="rounded-2xl border border-[#EDE2C5] bg-[#FFF9E8]/80 p-6">
            <h3 className="text-sm font-bold text-[#28241C]">إجراءات سريعة</h3>
            <p className="mt-1 text-xs text-[#726B5E]">
              انتقل مباشرة إلى الأدوات الأكاديمية الذكية لاتخاذ قرارات مدروسة:
            </p>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Link
                href="/student/eligibility"
                className="flex items-center gap-3 rounded-xl border border-[#EDE2C5] bg-white p-3.5 text-xs font-semibold text-[#28241C] shadow-2xs transition-all hover:bg-[#FFF4C7] hover:border-[#E2AD27]"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#FFF4C7] text-[#A66F00]">
                  <EligibilityIcon className="h-4 w-4" />
                </div>
                <span>تحقق من أهلية مادة</span>
              </Link>

              <Link
                href="/student/planner"
                className="flex items-center gap-3 rounded-xl border border-[#EDE2C5] bg-white p-3.5 text-xs font-semibold text-[#28241C] shadow-2xs transition-all hover:bg-[#FFF4C7] hover:border-[#E2AD27]"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#FFF4C7] text-[#A66F00]">
                  <PlannerIcon className="h-4 w-4" />
                </div>
                <span>خطط لفصلك</span>
              </Link>

              <Link
                href="/student/recommendations"
                className="flex items-center gap-3 rounded-xl border border-[#EDE2C5] bg-white p-3.5 text-xs font-semibold text-[#28241C] shadow-2xs transition-all hover:bg-[#FFF4C7] hover:border-[#E2AD27]"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#FFF4C7] text-[#A66F00]">
                  <RecommendationsIcon className="h-4 w-4" />
                </div>
                <span>شاهد توصياتك</span>
              </Link>

              <Link
                href="/student/degree-path"
                className="flex items-center gap-3 rounded-xl border border-[#EDE2C5] bg-white p-3.5 text-xs font-semibold text-[#28241C] shadow-2xs transition-all hover:bg-[#FFF4C7] hover:border-[#E2AD27]"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#FFF4C7] text-[#A66F00]">
                  <DegreePathIcon className="h-4 w-4" />
                </div>
                <span>افتح المسار الدراسي</span>
              </Link>
            </div>
          </div>

          {/* Requirement Groups Breakdown */}
          <section className="rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-xs">
            <h2 className="text-xl font-bold text-[#28241C]">تفاصيل متطلبات الخطة</h2>
            <div className="mt-5 grid gap-4">
              {progress.requirement_groups.map((group) => (
                <article
                  key={group.group_id}
                  className="rounded-2xl border border-[#EDE2C5] bg-[#FFFCF4] p-5"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="font-bold text-[#28241C]">{group.name_ar}</h3>
                      <p className="mt-1 text-xs text-[#726B5E]" dir="ltr">
                        ({group.group_code})
                      </p>
                    </div>
                    <span
                      className={
                        group.is_satisfied
                          ? "text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200"
                          : "text-xs font-bold text-amber-800 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-200"
                      }
                    >
                      {group.is_satisfied ? "مستوفاة" : "غير مستوفاة"}
                    </span>
                  </div>

                  <div className="mt-3">
                    <ProgressBar
                      completed={Number(group.completed_listed_credits) || 0}
                      total={Number(group.required_credits) || 1}
                      label={`الساعات المنجزة: ${displayValue(group.completed_listed_credits)} من ${displayValue(group.required_credits)}`}
                    />
                  </div>

                  <dl className="mt-4 grid grid-cols-3 gap-3 text-xs border-t border-[#EDE2C5]/60 pt-3">
                    <div>
                      <dt className="text-[#726B5E] text-[10px]">المطلوبة</dt>
                      <dd className="mt-1 font-semibold text-[#28241C]">
                        {displayValue(group.required_credits)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[#726B5E] text-[10px]">المحتسبة</dt>
                      <dd className="mt-1 font-semibold text-[#28241C]">
                        {displayValue(group.credited_toward_requirement)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[#726B5E] text-[10px]">المتبقية</dt>
                      <dd className="mt-1 font-semibold text-[#28241C]">
                        {displayValue(group.remaining_required_credits)}
                      </dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
