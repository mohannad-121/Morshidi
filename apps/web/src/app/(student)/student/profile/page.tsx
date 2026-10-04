"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/auth/auth-provider";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type { AcademicProfileResponse, DashboardError } from "@/lib/api/student-types";
import { Badge } from "@/components/ui/Badge";
import { ErrorAlert, isRetryableError } from "@/components/ui/ErrorAlert";
import { LoadingSkeletonCard } from "@/components/ui/LoadingSkeleton";
import { ChevronDownIcon, ProfileIcon, SparklesIcon } from "@/components/ui/Icons";

function displayValue(value: string | number | null | undefined): string {
  return value === null || value === undefined ? "غير متوفر" : String(value);
}

export default function ProfilePage() {
  const auth = useAuth();
  const client = useAuthenticatedApi();
  const [profile, setProfile] = useState<AcademicProfileResponse | null>(null);
  const [error, setError] = useState<DashboardError | null>(null);
  const [loading, setLoading] = useState(true);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  const fetchProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new StudentApiService(client);
      const data = await api.getProfile();
      setProfile(data);
    } catch (err: unknown) {
      if (err instanceof Error && err.message === "NOT_FOUND") {
        setError("NOT_FOUND");
      } else {
        setError("SERVER_ERROR");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (auth.isAuthenticated) {
      void fetchProfile();
    }
  }, [auth.isAuthenticated]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 border-b border-[#344739] pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-[#D9884A]/10 px-2.5 py-0.5 text-xs font-bold text-[#D9884A]">
              بيانات الطالب
            </span>
            <span className="text-xs text-[#AEBCB3]">السجل الأكاديمي الرقمي</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#F3E9D8]">
            ملفي الأكاديمي
          </h1>
          <p className="text-xs text-[#AEBCB3]">
            استعراض البيانات الأكاديمية الرسمية والخطة المعتمدة في النظام.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="gold">حساب معتمد</Badge>
        </div>
      </div>

      {/* Error state */}
      {error ? (
        <ErrorAlert
          error={error}
          onRetry={isRetryableError(error) ? fetchProfile : undefined}
        />
      ) : null}

      {/* Loading state */}
      {loading ? (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <LoadingSkeletonCard />
          <LoadingSkeletonCard />
        </div>
      ) : null}

      {/* Loaded Profile Content */}
      {!loading && !error && profile ? (
        <div className="space-y-6">
          {/* Main Info Card */}
          <div className="rounded-3xl border border-[#344739] bg-surface p-7 shadow-xs">
            <div className="flex items-center gap-4 border-b border-[#344739]/60 pb-6">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#15271F] text-[#D9884A]">
                <ProfileIcon className="h-7 w-7" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-[#F3E9D8]">
                  {auth.user?.user_metadata?.full_name ?? "طالب مرشدي"}
                </h2>
                <p className="font-mono text-xs text-[#AEBCB3]" dir="ltr">
                  {auth.user?.email ?? "غير متوفر"}
                </p>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-3">
              <div className="rounded-2xl border border-[#344739] bg-[#0F1A17] p-5 text-center">
                <span className="block text-xs font-semibold text-[#AEBCB3]">
                  المعدل التراكمي
                </span>
                <span className="mt-2 block font-mono text-3xl font-extrabold text-[#F3E9D8]">
                  {displayValue(profile.reported_cumulative_gpa)}
                </span>
                <span className="mt-1 block text-[11px] text-[#AEBCB3]">
                  من أصل {displayValue(profile.reported_gpa_scale)}
                </span>
              </div>

              <div className="rounded-2xl border border-[#344739] bg-[#0F1A17] p-5 text-center">
                <span className="block text-xs font-semibold text-[#AEBCB3]">
                  الساعات المكتسبة المسجلة
                </span>
                <span className="mt-2 block font-mono text-3xl font-extrabold text-[#F3E9D8]">
                  {displayValue(profile.reported_earned_credit_hours)}
                </span>
                <span className="mt-1 block text-[11px] text-[#AEBCB3]">
                  ساعة معتمدة
                </span>
              </div>

              <div className="rounded-2xl border border-[#344739] bg-[#0F1A17] p-5 text-center">
                <span className="block text-xs font-semibold text-[#AEBCB3]">
                  حالة الملف
                </span>
                <span className="mt-3 inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
                  نشط ومعتمد
                </span>
                <span className="mt-2 block text-[11px] text-[#AEBCB3]">
                  مربوط بالخطة الدراسية
                </span>
              </div>
            </div>

            <div className="mt-6 rounded-2xl bg-[#0B1210] p-5 border border-[#344739]/70 text-xs">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <span className="font-semibold text-[#AEBCB3]">تاريخ إنشاء السجل: </span>
                  <span className="font-mono text-[#F3E9D8]">
                    {profile.created_at ? new Date(profile.created_at).toLocaleDateString("ar-SA") : "غير متوفر"}
                  </span>
                </div>
                <div>
                  <span className="font-semibold text-[#AEBCB3]">آخر تحديث: </span>
                  <span className="font-mono text-[#F3E9D8]">
                    {profile.updated_at ? new Date(profile.updated_at).toLocaleDateString("ar-SA") : "غير متوفر"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Secondary Expandable Technical Details */}
          <div className="rounded-2xl border border-[#344739] bg-surface p-5 shadow-xs">
            <button
              type="button"
              onClick={() => setShowTechnicalDetails((prev) => !prev)}
              className="flex w-full items-center justify-between text-xs font-bold text-[#AEBCB3] hover:text-[#F3E9D8]"
            >
              <div className="flex items-center gap-2">
                <SparklesIcon className="h-4 w-4 text-[#D9884A]" />
                <span>المعرفات الفنية والتقنية (لأغراض التدقيق والمطابقة)</span>
              </div>
              <ChevronDownIcon
                className={`h-4 w-4 transition-transform duration-200 ${
                  showTechnicalDetails ? "rotate-180" : ""
                }`}
              />
            </button>

            {showTechnicalDetails ? (
              <div className="mt-4 space-y-3 border-t border-[#344739]/60 pt-4 text-xs font-mono">
                <div>
                  <span className="block text-[10px] font-sans font-bold text-[#AEBCB3]">
                    معرّف الملف الأكاديمي (Profile UUID):
                  </span>
                  <span className="text-[#F3E9D8] break-all select-all" dir="ltr">
                    {profile.id}
                  </span>
                </div>
                <div>
                  <span className="block text-[10px] font-sans font-bold text-[#AEBCB3]">
                    معرّف الخطة الدراسية (Study Plan UUID):
                  </span>
                  <span className="text-[#F3E9D8] break-all select-all" dir="ltr">
                    {profile.study_plan_id}
                  </span>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
