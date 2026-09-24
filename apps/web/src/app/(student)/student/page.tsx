"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { SignOutButton } from "@/auth/sign-out-button";
import { useAuth } from "@/auth/auth-provider";
import {
  AuthenticatedApiClient,
  AuthenticatedApiError,
} from "@/lib/api/authenticated-client";
import type {
  AcademicProfileResponse,
  AcademicProgressResponse,
} from "@/lib/api/student-types";

type DashboardError =
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "VALIDATION_ERROR"
  | "SERVICE_UNAVAILABLE"
  | "SERVER_ERROR"
  | "NETWORK_ERROR"
  | "CONFIGURATION_ERROR"
  | "UNKNOWN";

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
  const [loading, setLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState<DashboardError | null>(null);

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

  const load = useCallback(async () => {
    if (!auth.isAuthenticated || !client) return;

    setLoading(true);
    setDashboardError(null);

    try {
      const [profileResponse, progressResponse] = await Promise.all([
        client.request("/api/v1/me/academic-profile"),
        client.request("/api/v1/me/academic-progress"),
      ]);

      const [nextProfile, nextProgress] = await Promise.all([
        parseResponse<AcademicProfileResponse>(profileResponse),
        parseResponse<AcademicProgressResponse>(progressResponse),
      ]);

      setProfile(nextProfile);
      setProgress(nextProgress);
    } catch (error) {
      setProfile(null);
      setProgress(null);

      if (error instanceof Error && error.message === "NOT_FOUND") {
        setDashboardError("NOT_FOUND");
      } else {
        setDashboardError(mapClientError(error));
      }
    } finally {
      setLoading(false);
    }
  }, [auth.isAuthenticated, client]);

  useEffect(() => {
    if (auth.status === "authenticated") {
      if (!client) {
        setDashboardError("CONFIGURATION_ERROR");
        return;
      }
      void load();
    }
  }, [auth.status, client, load]);

  if (auth.isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-950 p-6" dir="rtl">
        <p role="status" className="text-zinc-300">
          جاري التحقق من جلسة الدخول…
        </p>
      </main>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-950 p-6" dir="rtl">
        <section className="w-full max-w-2xl rounded-3xl border border-zinc-800 bg-zinc-900 p-8">
          <p className="text-zinc-200">يجب تسجيل الدخول للوصول إلى لوحة الطالب.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-zinc-950 px-4 py-8 text-zinc-100 sm:px-6 lg:px-8" dir="rtl">
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <header className="flex flex-col gap-4 rounded-3xl border border-zinc-800 bg-zinc-900 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-emerald-400">مرشدي</p>
            <h1 className="mt-1 text-3xl font-semibold">لوحة الطالب</h1>
            <p className="mt-2 text-sm text-zinc-400" dir="ltr">
              {auth.user?.email ?? "غير متوفر"}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading || !client}
              className="rounded-xl border border-zinc-700 px-4 py-2 text-sm font-medium disabled:opacity-50"
            >
              تحديث البيانات
            </button>
            <SignOutButton />
          </div>
        </header>

        {loading ? (
          <section className="rounded-3xl border border-zinc-800 bg-zinc-900 p-8">
            <p role="status" className="text-zinc-300">
              جاري تحميل البيانات الأكاديمية…
            </p>
          </section>
        ) : null}

        {!loading && dashboardError ? (
          <section
            role={dashboardError === "NOT_FOUND" ? undefined : "alert"}
            className="rounded-3xl border border-zinc-800 bg-zinc-900 p-8"
          >
            <p className="text-zinc-200">{errorMessage(dashboardError)}</p>
            {isRetryable(dashboardError) ? (
              <button
                type="button"
                onClick={() => void load()}
                className="mt-5 rounded-xl bg-emerald-500 px-4 py-2 font-semibold text-zinc-950"
              >
                إعادة المحاولة
              </button>
            ) : null}
          </section>
        ) : null}

        {!loading && !dashboardError && profile && progress ? (
          <>
            <section className="grid gap-4 lg:grid-cols-2">
              <article className="rounded-3xl border border-zinc-800 bg-zinc-900 p-6">
                <h2 className="text-xl font-semibold">الملف الأكاديمي</h2>
                <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-sm text-zinc-400">معرّف الخطة الدراسية</dt>
                    <dd className="mt-1 break-all" dir="ltr">{displayValue(profile.study_plan_id)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-zinc-400">المعدل التراكمي المسجل</dt>
                    <dd className="mt-1">{displayValue(profile.reported_cumulative_gpa)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-zinc-400">مقياس المعدل</dt>
                    <dd className="mt-1">{displayValue(profile.reported_gpa_scale)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-zinc-400">الساعات المكتسبة المسجلة</dt>
                    <dd className="mt-1">{displayValue(profile.reported_earned_credit_hours)}</dd>
                  </div>
                </dl>
              </article>

              <article className="rounded-3xl border border-zinc-800 bg-zinc-900 p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-xl font-semibold">التقدم الأكاديمي</h2>
                  {progress.all_modeled_plan_requirements_satisfied ? (
                    <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-sm font-semibold text-emerald-300">
                      مستوفاة بالكامل
                    </span>
                  ) : null}
                </div>
                <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                  <div><dt className="text-sm text-zinc-400">إجمالي ساعات الخطة</dt><dd className="mt-1">{displayValue(progress.plan_total_required_credits)}</dd></div>
                  <div><dt className="text-sm text-zinc-400">الساعات المنجزة</dt><dd className="mt-1">{displayValue(progress.completed_plan_credits)}</dd></div>
                  <div><dt className="text-sm text-zinc-400">الساعات قيد التسجيل</dt><dd className="mt-1">{displayValue(progress.in_progress_plan_credits)}</dd></div>
                  <div><dt className="text-sm text-zinc-400">الساعات المتبقية</dt><dd className="mt-1">{displayValue(progress.remaining_plan_credits)}</dd></div>
                  <div>
                    <dt className="text-sm text-zinc-400">المجموعات المستوفاة</dt>
                    <dd className="mt-1">
                      {progress.satisfied_requirement_group_count} من {progress.total_requirement_group_count}
                    </dd>
                  </div>
                </dl>
              </article>
            </section>

            <section className="rounded-3xl border border-zinc-800 bg-zinc-900 p-6">
              <h2 className="text-xl font-semibold">تفاصيل متطلبات الخطة</h2>
              <div className="mt-5 grid gap-4">
                {progress.requirement_groups.map((group) => (
                  <article key={group.group_id} className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h3 className="font-semibold">{group.name_ar}</h3>
                        <p className="mt-1 text-sm text-zinc-500" dir="ltr">
                          ({group.group_code})
                        </p>
                      </div>
                      <span className={group.is_satisfied ? "text-sm font-semibold text-emerald-400" : "text-sm font-semibold text-amber-300"}>
                        {group.is_satisfied ? "مستوفاة" : "غير مستوفاة"}
                      </span>
                    </div>
                    <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
                      <div><dt className="text-zinc-500">المطلوبة</dt><dd className="mt-1">{displayValue(group.required_credits)}</dd></div>
                      <div><dt className="text-zinc-500">المحتسبة</dt><dd className="mt-1">{displayValue(group.credited_toward_requirement)}</dd></div>
                      <div><dt className="text-zinc-500">المتبقية</dt><dd className="mt-1">{displayValue(group.remaining_required_credits)}</dd></div>
                    </dl>
                  </article>
                ))}
              </div>
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}
