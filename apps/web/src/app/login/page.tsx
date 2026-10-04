import { Suspense } from "react";
import Link from "next/link";
import { LoginForm } from "@/auth/login-form";
import { MorshidiLogo } from "@/components/ui/Icons";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0B1210] p-5" dir="rtl">
      <section className="w-full max-w-md rounded-3xl border border-[#344739] bg-[#0F1A17] p-8 shadow-sm">
        <div className="flex items-center gap-3">
          <MorshidiLogo className="h-10 w-10 shrink-0" />
          <div>
            <span className="block text-lg font-bold text-[#F3E9D8]">مرشدي</span>
            <span className="block text-[11px] text-[#AEBCB3]">نظام الذكاء الأكاديمي</span>
          </div>
        </div>

        <h1 className="mt-6 text-2xl font-extrabold text-[#F3E9D8]">تسجيل الدخول</h1>
        <p className="mt-2 text-xs leading-relaxed text-[#AEBCB3]">
          استخدم بيانات حساب الطالب المسجّل في نظام مرشدي للوصول إلى بوابتك الأكاديمية.
        </p>

        <Suspense fallback={<p className="mt-8 text-xs text-[#D9884A] animate-pulse" role="status">جاري تجهيز تسجيل الدخول…</p>}>
          <LoginForm />
        </Suspense>

        <div className="mt-6 border-t border-[#344739]/60 pt-4 text-center">
          <Link href="/" className="text-xs font-semibold text-[#E5AC7C] hover:underline">
            العودة إلى الصفحة الرئيسية
          </Link>
        </div>
      </section>
    </main>
  );
}
