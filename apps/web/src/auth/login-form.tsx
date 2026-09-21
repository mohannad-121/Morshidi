"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { useAuth } from "@/auth/auth-provider";

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
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const destination = safeReturnTo(searchParams.get("returnTo"));

  useEffect(() => {
    if (auth.isAuthenticated) router.replace(destination);
  }, [auth.isAuthenticated, destination, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
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
        <label className="mb-2 block text-sm font-semibold" htmlFor="email">
          البريد الإلكتروني
        </label>
        <input
          className="min-h-12 w-full rounded-xl border border-zinc-300 bg-white px-4 text-left text-zinc-950 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50"
          dir="ltr"
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          disabled={isSubmitting}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </div>
      <div>
        <label className="mb-2 block text-sm font-semibold" htmlFor="password">
          كلمة المرور
        </label>
        <input
          className="min-h-12 w-full rounded-xl border border-zinc-300 bg-white px-4 text-left text-zinc-950 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50"
          dir="ltr"
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          disabled={isSubmitting}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </div>
      {error ? (
        <p className="rounded-xl bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200" role="alert">
          {error}
        </p>
      ) : null}
      <button className="button-primary w-full" disabled={isSubmitting} type="submit">
        {isSubmitting ? "جاري تسجيل الدخول…" : "تسجيل الدخول"}
      </button>
    </form>
  );
}
