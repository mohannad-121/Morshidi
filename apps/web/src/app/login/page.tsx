import { Suspense } from "react";

import { LoginForm } from "@/auth/login-form";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 p-5 dark:bg-zinc-950">
      <section className="w-full max-w-md rounded-3xl border border-zinc-200 bg-white p-7 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">مرشدي</p>
        <h1 className="mt-2 text-3xl font-semibold">تسجيل الدخول</h1>
        <p className="mt-3 leading-7 text-zinc-600 dark:text-zinc-300">
          استخدم حساب الطالب المسجّل في نظام مرشدي.
        </p>
        <Suspense fallback={<p className="mt-8" role="status">جاري تجهيز تسجيل الدخول…</p>}>
          <LoginForm />
        </Suspense>
      </section>
    </main>
  );
}
