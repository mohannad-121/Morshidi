import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center bg-zinc-50 p-6 font-sans text-zinc-950 dark:bg-zinc-950 dark:text-zinc-50">
      <section className="w-full max-w-xl rounded-3xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">مرشدي</p>
        <h1 className="mt-2 text-3xl font-semibold">بوابة الطالب</h1>
        <p className="mt-3 leading-7 text-zinc-600 dark:text-zinc-300">
          سجّل دخولك للوصول إلى صفحات الطالب المحمية. تبقى صلاحيات البيانات الأكاديمية بيد الخادم.
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link className="button-primary" href="/login">
            تسجيل الدخول
          </Link>
          <Link className="button-secondary" href="/student">
            منطقة الطالب
          </Link>
        </div>
      </section>
    </main>
  );
}
