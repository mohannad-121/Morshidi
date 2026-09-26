import { Suspense } from "react";
import Link from "next/link";
import { LoginForm } from "@/auth/login-form";
import { MorshidiLogo } from "@/components/ui/Icons";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#FFFCF4] p-5" dir="rtl">
      <section className="w-full max-w-md rounded-3xl border border-[#EDE2C5] bg-[#FFFFFF] p-8 shadow-sm">
        <div className="flex items-center gap-3">
          <MorshidiLogo className="h-10 w-10 shrink-0" />
          <div>
            <span className="block text-lg font-bold text-[#28241C]">مرشدي</span>
            <span className="block text-[11px] text-[#726B5E]">نظام الذكاء الأكاديمي</span>
          </div>
        </div>

        <h1 className="mt-6 text-2xl font-extrabold text-[#28241C]">تسجيل الدخول</h1>
        <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">
          استخدم بيانات حساب الطالب المسجّل في نظام مرشدي للوصول إلى بوابتك الأكاديمية.
        </p>

        <Suspense fallback={<p className="mt-8 text-xs text-[#A66F00] animate-pulse" role="status">جاري تجهيز تسجيل الدخول…</p>}>
          <LoginForm />
        </Suspense>

        <div className="mt-6 border-t border-[#EDE2C5]/60 pt-4 text-center">
          <Link href="/" className="text-xs font-semibold text-[#805400] hover:underline">
            العودة إلى الصفحة الرئيسية
          </Link>
        </div>
      </section>
    </main>
  );
}
