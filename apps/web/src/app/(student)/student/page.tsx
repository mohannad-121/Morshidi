import { SignOutButton } from "@/auth/sign-out-button";

export default function StudentPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 p-6 dark:bg-zinc-950">
      <section className="w-full max-w-2xl rounded-3xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">منطقة محمية</p>
        <h1 className="mt-2 text-3xl font-semibold">منطقة الطالب</h1>
        <p className="mt-3 leading-7 text-zinc-600 dark:text-zinc-300">
          تم إنشاء جلسة مصادقة صالحة. ستبقى صلاحيات الوصول إلى البيانات الأكاديمية والتحقق من ملكيتها لدى الخادم.
        </p>
        <div className="mt-7">
          <SignOutButton />
        </div>
      </section>
    </main>
  );
}
