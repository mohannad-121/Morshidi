import { Suspense } from "react";
import Link from "next/link";
import { LoginForm } from "@/auth/login-form";
import { Logo } from "@/components/ui/Logo";

export default function LoginPage() {
  return (
    <main className="login-page flex min-h-screen items-center justify-center bg-background p-5" dir="rtl">
      <section className="w-full max-w-md rounded-[20px] border border-border bg-surface p-7 shadow-[0_24px_70px_rgba(25,24,22,0.08)] sm:p-9">
        <Logo />

        <h1 className="mt-8 text-2xl font-bold text-foreground">تسجيل الدخول</h1>
        <p className="mt-2 text-xs leading-relaxed text-muted">
          استخدم بيانات حساب الطالب المسجّل في نظام مرشدي للوصول إلى بوابتك الأكاديمية.
        </p>

        <Suspense fallback={<p className="mt-8 text-xs text-accent animate-pulse" role="status">جاري تجهيز تسجيل الدخول…</p>}>
          <LoginForm />
        </Suspense>

        <div className="mt-6 border-t border-border/60 pt-4 text-center">
          <Link href="/" className="text-xs font-semibold text-accent hover:underline">
            العودة إلى الصفحة الرئيسية
          </Link>
        </div>
      </section>
    </main>
  );
}
