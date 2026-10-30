"use client";

import Image from "next/image";
import { Camera, LoaderCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ChangeEvent } from "react";
import { useAuth } from "@/auth/auth-provider";
import { getStudentDisplayName } from "@/lib/student-identity";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type { AcademicProfileResponse, DashboardError } from "@/lib/api/student-types";
import {
  downloadProfileAvatar,
  PROFILE_AVATAR_MIME_TYPES,
  uploadProfileAvatar,
  validateProfileAvatar,
} from "@/lib/profile-avatar-storage";
import { Badge } from "@/components/ui/Badge";
import { ErrorAlert, isRetryableError } from "@/components/ui/ErrorAlert";
import { LoadingSkeletonCard } from "@/components/ui/LoadingSkeleton";
import { ChevronDownIcon, ProfileIcon, SparklesIcon } from "@/components/ui/Icons";

function displayValue(value: string | number | null | undefined): string {
  return value === null || value === undefined ? "غير متوفر" : String(value);
}

export default function ProfilePage() {
  const auth = useAuth();
  const displayName = getStudentDisplayName(auth.user);
  const client = useAuthenticatedApi();
  const [profile, setProfile] = useState<AcademicProfileResponse | null>(null);
  const [error, setError] = useState<DashboardError | null>(null);
  const [loading, setLoading] = useState(true);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarMessage, setAvatarMessage] = useState<string | null>(null);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const avatarObjectUrlRef = useRef<string | null>(null);

  const showAvatarBlob = useCallback((blob: Blob) => {
    if (avatarObjectUrlRef.current) URL.revokeObjectURL(avatarObjectUrlRef.current);
    const objectUrl = URL.createObjectURL(blob);
    avatarObjectUrlRef.current = objectUrl;
    setAvatarUrl(objectUrl);
  }, []);

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

  useEffect(() => {
    const userId = auth.user?.id;
    if (!userId) return;
    let active = true;

    void downloadProfileAvatar(userId)
      .then((blob) => {
        if (active && blob) showAvatarBlob(blob);
      })
      .catch(() => {
        if (active) setAvatarError("تعذّر تحميل صورة الملف الشخصي حالياً.");
      });

    return () => {
      active = false;
    };
  }, [auth.user?.id, showAvatarBlob]);

  useEffect(() => () => {
    if (avatarObjectUrlRef.current) URL.revokeObjectURL(avatarObjectUrlRef.current);
  }, []);

  const handleAvatarChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    const userId = auth.user?.id;
    if (!file || !userId) return;

    setAvatarMessage(null);
    const validationError = validateProfileAvatar(file);
    if (validationError) {
      setAvatarError(validationError);
      input.value = "";
      return;
    }

    setAvatarError(null);
    setAvatarUploading(true);
    try {
      await uploadProfileAvatar(userId, file);
      showAvatarBlob(file);
      setAvatarMessage("تم تحديث صورة الملف الشخصي.");
    } catch {
      setAvatarError("تعذّر رفع الصورة. حاول مرة أخرى.");
    } finally {
      setAvatarUploading(false);
      input.value = "";
    }
  };

  return (
    <div className="profile-page space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 border-b border-border pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-bold text-accent">
              بيانات الطالب
            </span>
            <span className="text-xs text-slate-300 font-medium">السجل الأكاديمي الرقمي</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground">
            ملفي الأكاديمي
          </h1>
          <p className="text-xs text-slate-300 leading-relaxed">
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
          <div className="profile-identity-card surface-feature rounded-3xl border border-border p-7">
            <div className="flex items-center gap-4 border-b border-border/60 pb-6">
              <div className="shrink-0">
                <button
                  type="button"
                  className="group relative flex h-16 w-16 items-center justify-center overflow-hidden rounded-2xl border border-accent/30 bg-accent-soft text-accent shadow-sm transition hover:border-accent hover:shadow-[0_0_24px_rgba(255,210,119,0.16)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-wait disabled:opacity-70"
                  onClick={() => avatarInputRef.current?.click()}
                  disabled={avatarUploading}
                  aria-label="تغيير صورة الملف الشخصي"
                  title="تغيير صورة الملف الشخصي"
                >
                  {avatarUrl ? (
                    <Image
                      src={avatarUrl}
                      alt=""
                      fill
                      sizes="64px"
                      className="object-cover"
                      unoptimized
                    />
                  ) : (
                    <ProfileIcon className="h-7 w-7" aria-hidden="true" />
                  )}
                  <span className="absolute inset-x-0 bottom-0 z-10 flex h-6 items-center justify-center bg-black/70 text-champagne opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                    {avatarUploading ? <LoaderCircle className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none" aria-hidden="true" /> : <Camera className="h-3.5 w-3.5" aria-hidden="true" />}
                  </span>
                </button>
                <input
                  ref={avatarInputRef}
                  type="file"
                  accept={PROFILE_AVATAR_MIME_TYPES.join(",")}
                  className="sr-only"
                  onChange={handleAvatarChange}
                  aria-label="اختيار صورة الملف الشخصي من الجهاز"
                />
              </div>
              <div className="min-w-0">
                <h2 className="text-lg font-bold text-foreground">
                  {displayName}
                </h2>
                {auth.user?.user_metadata?.university_student_id ? (
                  <p className="font-mono text-xs text-slate-300 font-medium" dir="ltr">
                    {String(auth.user.user_metadata.university_student_id)}
                  </p>
                ) : null}
                <button
                  type="button"
                  className="mt-1 text-xs font-semibold text-accent transition hover:text-accent-hover disabled:cursor-wait disabled:opacity-60"
                  onClick={() => avatarInputRef.current?.click()}
                  disabled={avatarUploading}
                >
                  {avatarUploading ? "جارٍ رفع الصورة…" : "تغيير الصورة"}
                </button>
                {avatarMessage ? <p className="mt-1 text-xs text-emerald-400" role="status">{avatarMessage}</p> : null}
                {avatarError ? <p className="mt-1 text-xs text-red-400" role="alert">{avatarError}</p> : null}
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-3">
              <div className="profile-metric rounded-2xl border border-border bg-surface-muted p-5 text-center">
                <span className="block text-xs font-semibold text-slate-300">
                  المعدل التراكمي
                </span>
                <span className="mt-2 block font-mono text-3xl font-extrabold text-foreground">
                  {displayValue(profile.reported_cumulative_gpa)}
                </span>
                <span className="mt-1 block text-[11px] text-slate-400 font-medium">
                  من أصل {displayValue(profile.reported_gpa_scale)}
                </span>
              </div>

              <div className="profile-metric rounded-2xl border border-border bg-surface-muted p-5 text-center">
                <span className="block text-xs font-semibold text-slate-300">
                  الساعات المكتسبة المسجلة
                </span>
                <span className="mt-2 block font-mono text-3xl font-extrabold text-foreground">
                  {displayValue(profile.reported_earned_credit_hours)}
                </span>
                <span className="mt-1 block text-[11px] text-slate-400 font-medium">
                  ساعة معتمدة
                </span>
              </div>

              <div className="profile-metric rounded-2xl border border-border bg-surface-muted p-5 text-center">
                <span className="block text-xs font-semibold text-slate-300">
                  حالة الملف
                </span>
                <span className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-emerald-500/40 bg-emerald-950/80 px-3 py-1 text-xs font-bold text-emerald-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  نشط ومعتمد
                </span>
                <span className="mt-2 block text-[11px] text-slate-400 font-medium">
                  مربوط بالخطة الدراسية
                </span>
              </div>
            </div>

            <div className="mt-6 rounded-2xl bg-background p-5 border border-border/70 text-xs">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <span className="font-semibold text-slate-300">تاريخ إنشاء السجل: </span>
                  <span className="font-mono text-foreground font-medium">
                    {profile.created_at ? new Date(profile.created_at).toLocaleDateString("ar-SA") : "غير متوفر"}
                  </span>
                </div>
                <div>
                  <span className="font-semibold text-slate-300">آخر تحديث: </span>
                  <span className="font-mono text-foreground font-medium">
                    {profile.updated_at ? new Date(profile.updated_at).toLocaleDateString("ar-SA") : "غير متوفر"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Secondary Expandable Technical Details */}
          <div className="profile-technical-card surface-raised rounded-2xl border border-border p-5">
            <button
              type="button"
              onClick={() => setShowTechnicalDetails((prev) => !prev)}
              aria-expanded={showTechnicalDetails}
              aria-controls="profile-technical-details"
              className="flex w-full items-center justify-between text-xs font-bold text-slate-300 hover:text-white transition-colors"
            >
              <div className="flex items-center gap-2">
                <SparklesIcon className="h-4 w-4 text-accent" aria-hidden="true" />
                <span>المعرفات الفنية والتقنية (لأغراض التدقيق والمطابقة)</span>
              </div>
              <ChevronDownIcon
                aria-hidden="true"
                className={`h-4 w-4 transition-transform duration-200 ${
                  showTechnicalDetails ? "rotate-180" : ""
                }`}
              />
            </button>

            {showTechnicalDetails ? (
              <div id="profile-technical-details" className="mt-4 space-y-3 border-t border-border/60 pt-4 text-xs font-mono">
                {auth.user?.id ? (
                  <div>
                    <span className="block text-[10px] font-sans font-bold text-slate-400">
                      معرّف الحساب المعتمد (User Auth UUID):
                    </span>
                    <span className="text-foreground break-all select-all font-bold text-amber-400" dir="ltr">
                      {auth.user.id}
                    </span>
                  </div>
                ) : null}
                <div>
                  <span className="block text-[10px] font-sans font-bold text-slate-400">
                    معرّف الملف الأكاديمي (Profile UUID):
                  </span>
                  <span className="text-foreground break-all select-all" dir="ltr">
                    {profile.id}
                  </span>
                </div>
                <div>
                  <span className="block text-[10px] font-sans font-bold text-slate-400">
                    معرّف الخطة الدراسية (Study Plan UUID):
                  </span>
                  <span className="text-foreground break-all select-all" dir="ltr">
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
