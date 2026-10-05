"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/auth/auth-provider";
import { EyeIcon, EyeOffIcon } from "@/components/ui/Icons";

export type LoginMode = "student" | "staff";

function safeReturnTo(value: string | null): string {
  return value && (value === "/student" || value.startsWith("/student/")
    || value === "/institutional/change-impact" || value === "/institutional/ai-query" || value === "/institutional/cohorts")
    ? value
    : "/student";
}

export function LoginForm() {
  const auth = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [mode, setMode] = useState<LoginMode>("student");
  // Student fields
  const [studentId, setStudentId] = useState("");
  const [universityPassword, setUniversityPassword] = useState("");

  // Staff fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const destination = safeReturnTo(searchParams.get("returnTo"));

  useEffect(() => {
    if (auth.isAuthenticated) router.replace(destination);
  }, [auth.isAuthenticated, destination, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    setError(null);

    if (auth.status === "configuration_error") {
      setError("تعذّر تهيئة تسجيل الدخول. تواصل مع مسؤول النظام.");
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === "student") {
        const cleanStudentId = studentId.trim();
        if (!cleanStudentId || !universityPassword) {
          setError("تأكد من الرقم الجامعي وكلمة المرور.");
          setIsSubmitting(false);
          return;
        }

        const result = await auth.signInWithUniversity(cleanStudentId, universityPassword);
        if (!result.ok) {
          setError(result.error || "تعذر تسجيل الدخول. حاول مرة أخرى.");
          setUniversityPassword("");
          return;
        }
        setUniversityPassword("");
        router.replace(destination);
        router.refresh();
      } else {
        const cleanEmail = email.trim();
        if (!cleanEmail || !password) {
          setError("تعذّر تسجيل الدخول. تأكد من البريد الإلكتروني وكلمة المرور.");
          setIsSubmitting(false);
          return;
        }

        const result = await auth.signIn(cleanEmail, password);
        if (!result.ok) {
          setError("تعذّر تسجيل الدخول. تأكد من البريد الإلكتروني وكلمة المرور.");
          setPassword("");
          return;
        }
        setPassword("");
        router.replace(destination);
        router.refresh();
      }
    } catch {
      setError("تعذر تسجيل الدخول. حاول مرة أخرى.");
      if (mode === "student") setUniversityPassword("");
      else setPassword("");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mt-8 space-y-6">
      {/* Mode Switcher */}
      <div
        className="grid grid-cols-2 gap-1 rounded-2xl bg-[#0B1210] p-1 border border-[#344739]"
        role="tablist"
        aria-label="نوع تسجيل الدخول"
      >
        <button
          type="button"
          role="tab"
          aria-selected={mode === "student"}
          onClick={() => {
            setMode("student");
            setError(null);
          }}
          className={`rounded-xl py-2.5 text-xs font-bold transition-all ${
            mode === "student"
              ? "bg-[#D9884A] text-white shadow-xs"
              : "text-[#AEBCB3] hover:text-[#F3E9D8]"
          }`}
        >
          تسجيل دخول الطالب
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "staff"}
          onClick={() => {
            setMode("staff");
            setError(null);
          }}
          className={`rounded-xl py-2.5 text-xs font-bold transition-all ${
            mode === "staff"
              ? "bg-[#D9884A] text-white shadow-xs"
              : "text-[#AEBCB3] hover:text-[#F3E9D8]"
          }`}
        >
          تسجيل دخول المرشد أو الموظف
        </button>
      </div>

      {mode === "student" && (
        <p className="text-xs text-[#AEBCB3] leading-relaxed">
          استخدم نفس بيانات الدخول الخاصة ببوابة جامعتك.
        </p>
      )}

      <form method="post" className="space-y-5" onSubmit={handleSubmit} aria-busy={isSubmitting}>
        {mode === "student" ? (
          <>
            <div>
              <label className="mb-2 block text-xs font-bold text-[#F3E9D8]" htmlFor="studentId">
                الرقم الجامعي
              </label>
              <input
                className="min-h-12 w-full rounded-xl border border-[#344739] bg-surface px-4 text-left font-mono text-sm text-[#F3E9D8] placeholder:text-[#AEBCB3]/50 focus:border-[#D9884A] focus:ring-1 focus:ring-[#D9884A] disabled:opacity-60"
                dir="ltr"
                id="studentId"
                name="studentId"
                type="text"
                autoComplete="username"
                placeholder="202310001"
                required
                disabled={isSubmitting || auth.isLoading}
                value={studentId}
                onChange={(event) => setStudentId(event.target.value)}
              />
            </div>

            <div>
              <label className="mb-2 block text-xs font-bold text-[#F3E9D8]" htmlFor="universityPassword">
                كلمة مرور الجامعة
              </label>
              <div className="relative">
                <input
                  className="min-h-12 w-full rounded-xl border border-[#344739] bg-surface px-4 pl-12 text-left font-mono text-sm text-[#F3E9D8] placeholder:text-[#AEBCB3]/50 focus:border-[#D9884A] focus:ring-1 focus:ring-[#D9884A] disabled:opacity-60"
                  dir="ltr"
                  id="universityPassword"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  disabled={isSubmitting || auth.isLoading}
                  value={universityPassword}
                  onChange={(event) => setUniversityPassword(event.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[#AEBCB3] hover:text-[#F3E9D8] transition-colors p-1"
                  aria-label={showPassword ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}
                  tabIndex={0}
                >
                  {showPassword ? <EyeOffIcon className="h-5 w-5" /> : <EyeIcon className="h-5 w-5" />}
                </button>
              </div>
            </div>
          </>
        ) : (
          <>
            <div>
              <label className="mb-2 block text-xs font-bold text-[#F3E9D8]" htmlFor="email">
                البريد الإلكتروني
              </label>
              <input
                className="min-h-12 w-full rounded-xl border border-[#344739] bg-surface px-4 text-left font-mono text-sm text-[#F3E9D8] placeholder:text-[#AEBCB3]/50 focus:border-[#D9884A] focus:ring-1 focus:ring-[#D9884A] disabled:opacity-60"
                dir="ltr"
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="advisor@example.com"
                required
                disabled={isSubmitting || auth.isLoading}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>

            <div>
              <label className="mb-2 block text-xs font-bold text-[#F3E9D8]" htmlFor="password">
                كلمة المرور
              </label>
              <div className="relative">
                <input
                  className="min-h-12 w-full rounded-xl border border-[#344739] bg-surface px-4 pl-12 text-left font-mono text-sm text-[#F3E9D8] placeholder:text-[#AEBCB3]/50 focus:border-[#D9884A] focus:ring-1 focus:ring-[#D9884A] disabled:opacity-60"
                  dir="ltr"
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  disabled={isSubmitting || auth.isLoading}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[#AEBCB3] hover:text-[#F3E9D8] transition-colors p-1"
                  aria-label={showPassword ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}
                  tabIndex={0}
                >
                  {showPassword ? <EyeOffIcon className="h-5 w-5" /> : <EyeIcon className="h-5 w-5" />}
                </button>
              </div>
            </div>
          </>
        )}

        {error ? (
          <p
            className="rounded-xl border border-red-200 bg-red-50 p-3.5 text-xs font-semibold leading-relaxed text-red-900"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        <button
          className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-[#D9884A] px-5 py-3 text-sm font-bold text-white shadow-xs transition-all hover:bg-[#E5AC7C] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting || auth.isLoading || auth.status === "configuration_error"}
          type="submit"
        >
          {isSubmitting ? "جاري تسجيل الدخول…" : "تسجيل الدخول"}
        </button>

        {/* Secondary Switch Link */}
        <div className="text-center pt-1">
          {mode === "student" ? (
            <button
              type="button"
              onClick={() => {
                setMode("staff");
                setError(null);
              }}
              className="text-xs font-medium text-[#AEBCB3] hover:text-[#E5AC7C] transition-colors"
            >
              مرشد أكاديمي أو موظف؟{" "}
              <span className="font-bold underline text-[#E5AC7C]">تسجيل الدخول بالبريد الإلكتروني</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                setMode("student");
                setError(null);
              }}
              className="text-xs font-medium text-[#AEBCB3] hover:text-[#E5AC7C] transition-colors"
            >
              طالب جامعي؟{" "}
              <span className="font-bold underline text-[#E5AC7C]">تسجيل الدخول بالرقم الجامعي</span>
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
