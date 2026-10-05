"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/auth/auth-provider";
import { EyeIcon, EyeOffIcon } from "@/components/ui/Icons";

function safeReturnTo(value: string | null): string {
  return value && (
    value === "/student" ||
    value.startsWith("/student/") ||
    value === "/institutional/change-impact" ||
    value === "/institutional/ai-query" ||
    value === "/institutional/cohorts"
  )
    ? value
    : "/student";
}

export function normalizeStudentId(rawInput: string): string | null {
  const raw = rawInput.trim().toLowerCase();
  const match = raw.match(/^(\d{9})(?:@std\.morshidi\.edu\.jo)?$/);
  return match?.[1] ?? null;
}

export function LoginForm() {
  const auth = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [studentId, setStudentId] = useState("");
  const [universityPassword, setUniversityPassword] = useState("");
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
      setError("\u062a\u0639\u0630\u0651\u0631 \u062a\u0647\u064a\u0626\u0629 \u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644. \u062a\u0648\u0627\u0635\u0644 \u0645\u0639 \u0645\u0633\u0624\u0648\u0644 \u0627\u0644\u0646\u0638\u0627\u0645.");
      return;
    }

    const cleanStudentId = normalizeStudentId(studentId);

    if (!cleanStudentId) {
      setError("\u0623\u062f\u062e\u0644 \u0627\u0644\u0631\u0642\u0645 \u0627\u0644\u062c\u0627\u0645\u0639\u064a \u0627\u0644\u0645\u0643\u0648\u0651\u0646 \u0645\u0646 9 \u0623\u0631\u0642\u0627\u0645.");
      return;
    }

    if (!universityPassword) {
      setError("\u062a\u0623\u0643\u062f \u0645\u0646 \u0627\u0644\u0631\u0642\u0645 \u0627\u0644\u062c\u0627\u0645\u0639\u064a \u0648\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631.");
      return;
    }

    setIsSubmitting(true);

    try {
      const result = await auth.signInWithUniversity(
        cleanStudentId,
        universityPassword,
      );

      if (!result.ok) {
        setError(
          result.error ||
            "\u062a\u0639\u0630\u0631 \u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644. \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.",
        );
        setUniversityPassword("");
        return;
      }

      setUniversityPassword("");
      router.replace(destination);
      router.refresh();
    } catch {
      setError("\u062a\u0639\u0630\u0631 \u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644. \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.");
      setUniversityPassword("");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mt-8 space-y-6">
      <p className="text-xs text-[#AEBCB3] leading-relaxed">
        {"\u0627\u0633\u062a\u062e\u062f\u0645 \u0646\u0641\u0633 \u0627\u0644\u0631\u0642\u0645 \u0627\u0644\u062c\u0627\u0645\u0639\u064a \u0648\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631 \u0627\u0644\u062e\u0627\u0635\u0629 \u0628\u0628\u0648\u0627\u0628\u0629 \u062c\u0627\u0645\u0639\u062a\u0643."}
      </p>

      <form
        method="post"
        className="space-y-5"
        onSubmit={handleSubmit}
        aria-busy={isSubmitting}
      >
        <div>
          <label
            className="mb-2 block text-xs font-bold text-[#F3E9D8]"
            htmlFor="studentId"
          >
            {"\u0627\u0644\u0631\u0642\u0645 \u0627\u0644\u062c\u0627\u0645\u0639\u064a"}
          </label>

          <input
            className="min-h-12 w-full rounded-xl border border-[#344739] bg-surface px-4 text-left font-mono text-sm text-[#F3E9D8] placeholder:text-[#AEBCB3]/50 focus:border-[#D9884A] focus:ring-1 focus:ring-[#D9884A] disabled:opacity-60"
            dir="ltr"
            id="studentId"
            name="studentId"
            type="text"
            inputMode="numeric"
            autoComplete="off"
            placeholder="202310001"
            required
            disabled={isSubmitting || auth.isLoading}
            value={studentId}
            onChange={(event) => setStudentId(event.target.value)}
          />
        </div>

        <div>
          <label
            className="mb-2 block text-xs font-bold text-[#F3E9D8]"
            htmlFor="universityPassword"
          >
            {"\u0643\u0644\u0645\u0629 \u0645\u0631\u0648\u0631 \u0627\u0644\u062c\u0627\u0645\u0639\u0629"}
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
              aria-label={
                showPassword
                  ? "\u0625\u062e\u0641\u0627\u0621 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631"
                  : "\u0625\u0638\u0647\u0627\u0631 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631"
              }
              tabIndex={0}
            >
              {showPassword ? (
                <EyeOffIcon className="h-5 w-5" />
              ) : (
                <EyeIcon className="h-5 w-5" />
              )}
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
          disabled={
            isSubmitting ||
            auth.isLoading ||
            auth.status === "configuration_error"
          }
          type="submit"
        >
          {isSubmitting
            ? "\u062c\u0627\u0631\u064a \u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644\u2026"
            : "\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644"}
        </button>
      </form>
    </div>
  );
}
