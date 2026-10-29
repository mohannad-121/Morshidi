"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { BadgeCheck, BookOpenCheck, Clock3, Gauge, RefreshCw, Sparkles } from "lucide-react";
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
  StudentIntelligenceProfileV2,
} from "@/lib/api/student-types";
import { Badge } from "@/components/ui/Badge";
import { StatCard } from "@/components/ui/StatCard";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { LoadingSkeletonGrid } from "@/components/ui/LoadingSkeleton";
import { Emoji } from "@/components/ui/Emoji";
import { getArabicGreeting, getStudentDisplayName } from "@/lib/student-identity";
import {
  DegreePathIcon,
  EligibilityIcon,
  PlannerIcon,
  RecommendationsIcon,
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
  const [intelligence, setIntelligence] = useState<StudentIntelligenceProfileV2 | null>(null);
  const [dashboardError, setDashboardError] = useState<DashboardError | null>(null);
  const [isReloading, setIsReloading] = useState(false);
  const [refreshIndex, setRefreshIndex] = useState(0);
  const greeting = useSyncExternalStore(
    () => () => undefined,
    () => getArabicGreeting(),
    () => "مرحباً",
  );
  const displayName = getStudentDisplayName(auth.user);

  const reportedEarnedCredits = profile?.reported_earned_credit_hours;
  const reportedRemainingCredits =
    progress && reportedEarnedCredits !== null && reportedEarnedCredits !== undefined
      ? Math.max(0, progress.plan_total_required_credits - reportedEarnedCredits)
      : null;
  const universityProgressPercent =
    progress &&
    progress.plan_total_required_credits > 0 &&
    reportedEarnedCredits !== null &&
    reportedEarnedCredits !== undefined
      ? (
          Math.round(
            (reportedEarnedCredits / progress.plan_total_required_credits) * 1000
          ) / 10
        ).toFixed(1)
      : null;

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

  useEffect(() => {
    if (auth.status !== "authenticated" || !client) return;
    let ignore = false;
    void client.request("/api/v1/me/student-intelligence", { cache: "no-store" })
      .then(parseResponse<StudentIntelligenceProfileV2>)
      .then(value => { if (!ignore) setIntelligence(value); })
      .catch(() => { if (!ignore) setIntelligence(null); });
    return () => { ignore = true; };
  }, [auth.status, client, refreshIndex]);

  if (auth.isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background p-6" dir="rtl">
        <p role="status" className="text-sm font-semibold text-accent animate-pulse">
          جاري التحقق من جلسة الدخول…
        </p>
      </main>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background p-6" dir="rtl">
        <section className="w-full max-w-2xl rounded-3xl border border-border bg-surface-muted p-8 shadow-sm">
          <p className="text-foreground font-semibold">يجب تسجيل الدخول للوصول إلى لوحة الطالب.</p>
        </section>
      </main>
    );
  }

  return (
    <div className="dashboard-page" dir="rtl">
      <header className="dashboard-heading">
        <div className="dashboard-heading-row">
          <div className="dashboard-greeting">
            <p className="eyebrow">لوحة الطالب <Emoji emoji="✨" decorative /></p>
            <h1 aria-label={`${greeting}، ${displayName}`}><span className="desktop-greeting">{greeting}، </span><span className="mobile-greeting">{greeting} <Emoji emoji="👋" decorative /></span><span className="desktop-student-name">{displayName} <Emoji emoji="👋" decorative /></span></h1>
            <p className="mobile-student-name">{displayName}</p>
            <p className="dashboard-prompt">جاهز ترتّب يومك الأكاديمي؟</p>
          </div>

          <div className="dashboard-header-actions">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading || !client}
              className="glass dashboard-refresh"
              aria-label="تحديث البيانات"
            >
              <RefreshCw aria-hidden="true" className={loading ? "animate-spin motion-reduce:animate-none" : ""} size={17} />
              <span className="refresh-label">تحديث البيانات</span>
            </button>
            <SignOutButton className="glass dashboard-signout" />
          </div>
        </div>

        {/* Account Sub-navigation Tabs */}
        <div className="dashboard-subnav">
          <Link
            href="/student"
            className="dashboard-subnav-active"
          >
            نظرة عامة
          </Link>
          <Link
            href="/student/profile"
            className="glass"
          >
            الملف الأكاديمي
          </Link>
          <Link
            href="/student/progress"
            className="glass"
          >
            التقدم الأكاديمي
          </Link>
          <Link
            href="/student/courses"
            className="glass"
          >
            سجل موادي
          </Link>
          <Link
            href="/student/planner"
            className="glass"
          >
            مخطط الفصل
          </Link>
        </div>

      </header>

      {/* Loading state */}
      {loading ? (
        <section className="dashboard-state space-y-4" role="status" aria-label="جاري تحميل البيانات الأكاديمية">
          <p className="text-sm font-semibold text-accent">
            جاري تحميل البيانات الأكاديمية…
          </p>
          <div aria-hidden="true"><LoadingSkeletonGrid count={4} /></div>
        </section>
      ) : null}

      {/* Active Error */}
      {!loading && activeError ? (
        <section
          role={activeError === "NOT_FOUND" ? undefined : "alert"}
          className="glass dashboard-state dashboard-error"
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
        <div className="dashboard-loaded">
          {intelligence ? <section className="glass diagnostic-banner">
            <div className="diagnostic-banner-content">
              <div><p><Sparkles size={14} aria-hidden="true" /> بصمتي الأكاديمية</p><h2>{intelligence.diagnostic_recommended ? "ساعد مرشدي يتعرّف عليك بشكل أفضل" : `مرشدي يعرف أداءك من ${intelligence.verified_grade_count} علامة أكاديمية موثقة`}</h2><p>تخصيص مفسّر لا يغيّر الأهلية أو المتطلبات الأكاديمية.</p></div>
              <Link href={intelligence.diagnostic_recommended ? "/student/diagnostic" : "/student/intelligence"} className="diagnostic-cta">{intelligence.diagnostic_recommended ? "ابدأ الاختبار السريع" : "عرض بصمتي"}</Link>
            </div>
          </section> : null}
          {/* Quick Stats Grid */}
          <div className="dashboard-journey" aria-label="ملخص الرحلة الأكاديمية">
            <StatCard
              title="إجمالي ساعات الخطة"
              value={<>{displayValue(progress.plan_total_required_credits)} <small>ساعة</small></>}
              subtitle="ساعة معتمدة مطلوبة للتخرج"
              icon={<Gauge size={20} />}
              variant="warm"
              className="dashboard-hero-stat glass"
            >
              <ProgressBar completed={Number(reportedEarnedCredits) || 0} total={progress.plan_total_required_credits} showPercent={false} />
            </StatCard>
            <StatCard
              title="الساعات المكتسبة (سجل الجامعة)"
              value={displayValue(reportedEarnedCredits)}
              subtitle="سجل الجامعة الرسمي"
              icon={<BadgeCheck size={19} />}
              className="glass"
              badge={
                universityProgressPercent !== null ? (
                  <Badge variant="gold" size="sm">
                    {`${universityProgressPercent}%`}
                  </Badge>
                ) : undefined
              }
            />
            <StatCard
              title="الساعات المتبقية (حسب سجل الجامعة)"
              value={displayValue(reportedRemainingCredits)}
              subtitle="متبقية حسب سجل الجامعة"
              icon={<BookOpenCheck size={19} />}
              variant="gold"
              className="glass"
            />
            <StatCard
              title="الساعات قيد التسجيل"
              value={displayValue(progress.in_progress_plan_credits)}
              subtitle="مسجلة في الفصل الحالي"
              icon={<Clock3 size={19} />}
              className="glass"
            />
            <StatCard
              title="نسبة الإنجاز (سجل الجامعة)"
              value={universityProgressPercent !== null ? `${universityProgressPercent}%` : "غير متوفر"}
              subtitle="نسبة الساعات المكتسبة إلى الخطة"
              icon={<Gauge size={19} />}
              className="glass"
            />
          </div>

          {/* Profile & Progress Section */}
          <section className="dashboard-foundation">
            {/* Academic Profile Card */}
            <article className="glass">
              <div className="flex items-center justify-between border-b border-border/60 pb-4">
                <h2 className="text-xl font-bold text-foreground">الملف الأكاديمي</h2>
                <Badge variant="gold" size="sm">معتمد</Badge>
              </div>
              <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-semibold text-muted">معرّف الخطة الدراسية</dt>
                  <dd className="mt-1 font-mono text-xs break-all text-foreground" dir="ltr">
                    {displayValue(profile.study_plan_id)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-muted">المعدل التراكمي المسجل</dt>
                  <dd className="mt-1 font-mono text-lg font-bold text-foreground">
                    {displayValue(profile.reported_cumulative_gpa)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-muted">مقياس المعدل</dt>
                  <dd className="mt-1 font-mono text-sm font-semibold text-foreground">
                    {displayValue(profile.reported_gpa_scale)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-muted">الساعات المكتسبة المسجلة</dt>
                  <dd className="mt-1 font-mono text-sm font-semibold text-foreground">
                    {displayValue(profile.reported_earned_credit_hours)}
                  </dd>
                </div>
              </dl>
            </article>

            {/* Academic Progress Card */}
            <article className="glass">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-4">
                <h2 className="text-xl font-bold text-foreground">التقدم الأكاديمي</h2>
                {progress.all_modeled_plan_requirements_satisfied ? (
                  <Badge variant="success">مستوفاة بالكامل</Badge>
                ) : (
                  <Badge variant="warning">قيد الإنجاز</Badge>
                )}
              </div>
              <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-semibold text-muted">إجمالي ساعات الخطة</dt>
                  <dd className="mt-1 font-mono text-base font-bold text-foreground">
                    {displayValue(progress.plan_total_required_credits)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-muted">الساعات المحتسبة ضمن متطلبات الخطة</dt>
                  <dd className="mt-1 font-mono text-base font-bold text-foreground">
                    {displayValue(progress.completed_plan_credits)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-muted">الساعات قيد التسجيل</dt>
                  <dd className="mt-1 font-mono text-base font-bold text-foreground">
                    {displayValue(progress.in_progress_plan_credits)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-muted">المتبقي حسب نموذج الخطة</dt>
                  <dd className="mt-1 font-mono text-base font-bold text-foreground">
                    {displayValue(progress.remaining_plan_credits)}
                  </dd>
                </div>
                <div className="glass foundation-progress sm:col-span-2">
                  <dt className="text-xs font-semibold text-muted">المجموعات المستوفاة</dt>
                  <dd className="mt-1 font-mono text-sm font-bold text-foreground">
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
          <div className="dashboard-actions glass">
            <h3 className="text-sm font-bold text-foreground">إجراءات سريعة</h3>
            <p className="mt-1 text-xs text-muted">
              انتقل مباشرة إلى الأدوات الأكاديمية الذكية لاتخاذ قرارات مدروسة:
            </p>

            <div className="dashboard-action-grid">
              <Link
                href="/student/eligibility"
                className="glass"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
                  <EligibilityIcon className="h-4 w-4" />
                </div>
                <span>تحقق من أهلية مادة</span>
              </Link>

              <Link
                href="/student/planner"
                className="glass"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
                  <PlannerIcon className="h-4 w-4" />
                </div>
                <span>خطط لفصلك</span>
              </Link>

              <Link
                href="/student/recommendations"
                className="glass"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
                  <RecommendationsIcon className="h-4 w-4" />
                </div>
                <span>شاهد توصياتك</span>
              </Link>

              <Link
                href="/student/degree-path"
                className="glass"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
                  <DegreePathIcon className="h-4 w-4" />
                </div>
                <span>افتح المسار الدراسي</span>
              </Link>
            </div>
          </div>

          {/* Requirement Groups Breakdown */}
          <section className="dashboard-requirements">
            <h2 aria-label="تفاصيل متطلبات الخطة"><Emoji emoji="🧩" decorative /> تفاصيل متطلبات الخطة</h2>
            <div>
              {progress.requirement_groups.map((group, index) => (
                <article
                  key={group.group_id}
                  className="glass"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="font-bold text-foreground"><Emoji emoji={['🏛️', '🩺', '💉', '🌍', '🔬', '⭐'][index % 6]} decorative /> {group.name_ar}</h3>
                      <p className="mt-1 text-xs text-muted" dir="ltr">
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

                  <dl className="mt-4 grid grid-cols-3 gap-3 text-xs border-t border-border/60 pt-3">
                    <div>
                      <dt className="text-muted text-[10px]">المطلوبة</dt>
                      <dd className="mt-1 font-semibold text-foreground">
                        {displayValue(group.required_credits)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted text-[10px]">المحتسبة</dt>
                      <dd className="mt-1 font-semibold text-foreground">
                        {displayValue(group.credited_toward_requirement)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted text-[10px]">المتبقية</dt>
                      <dd className="mt-1 font-semibold text-foreground">
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
