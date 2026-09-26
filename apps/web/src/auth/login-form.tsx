"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/auth/auth-provider";
import { EyeIcon, EyeOffIcon } from "@/components/ui/Icons";

function safeReturnTo(value: string | null): string {
  return value && (value === "/student" || value.startsWith("/student/"))
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
    const result = await auth.signIn(email.trim(), password);
    setIsSubmitting(false);

    if (!result.ok) {
      setError("تعذّر تسجيل الدخول. تأكد من البريد الإلكتروني وكلمة المرور.");
      return;
    }
    router.replace(destination);
    router.refresh();
  }

  return (
    <form className="mt-8 space-y-5" onSubmit={handleSubmit} aria-busy={isSubmitting}>
      <div>
        <label className="mb-2 block text-xs font-bold text-[#28241C]" htmlFor="email">
          البريد الإلكتروني
        </label>
        <input
          className="min-h-12 w-full rounded-xl border border-[#EDE2C5] bg-white px-4 text-left font-mono text-sm text-[#28241C] placeholder:text-[#726B5E]/50 focus:border-[#A66F00] focus:ring-1 focus:ring-[#A66F00] disabled:opacity-60"
          dir="ltr"
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="student@example.com"
          required
          disabled={isSubmitting}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </div>

      <div>
        <label className="mb-2 block text-xs font-bold text-[#28241C]" htmlFor="password">
          كلمة المرور
        </label>
        <div className="relative">
          <input
            className="min-h-12 w-full rounded-xl border border-[#EDE2C5] bg-white px-4 pl-12 text-left font-mono text-sm text-[#28241C] placeholder:text-[#726B5E]/50 focus:border-[#A66F00] focus:ring-1 focus:ring-[#A66F00] disabled:opacity-60"
            dir="ltr"
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            required
            disabled={isSubmitting}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[#726B5E] hover:text-[#28241C] transition-colors p-1"
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
        className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-[#A66F00] px-5 py-3 text-sm font-bold text-white shadow-xs transition-all hover:bg-[#805400] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? "جاري تسجيل الدخول…" : "تسجيل الدخول"}
      </button>
    </form>
  );
}
