"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/auth/auth-provider";
import { EyeIcon, EyeOffIcon } from "@/components/ui/Icons";

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
    setError(null);

    if (auth.status === "configuration_error") {
      setError("تعذّر تهيئة تسجيل الدخول. تواصل مع مسؤول النظام.");
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await auth.signIn(email.trim(), password);
      if (!result.ok) {
        setError("تعذّر تسجيل الدخول. تأكد من البريد الإلكتروني وكلمة المرور.");
        return;
      }
      router.replace(destination);
      router.refresh();
    } catch {
      setError("تعذّر تسجيل الدخول. تحقق من الاتصال وحاول مجددًا.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form method="post" className="mt-8 space-y-5" onSubmit={handleSubmit} aria-busy={isSubmitting}>
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
          placeholder="student@example.com"
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
        disabled={isSubmitting || auth.isLoading || auth.status === 'configuration_error'}
        type="submit"
      >
        {isSubmitting ? "جاري تسجيل الدخول…" : "تسجيل الدخول"}
      </button>
    </form>
  );
}
