import Link from "next/link";
import Image from "next/image";
import { SparklesIcon } from "@/components/ui/Icons";

export function GlobalFooter() {
  return (
    <footer className="border-t border-[#EDE2C5] bg-[#FFF9E8]/70 text-[#28241C]" dir="rtl">
      {/* Top Banner / Governance Notice */}
      <div className="border-b border-[#EDE2C5]/70 bg-[#FFF4C7]/50 py-3">
        <div className="mx-auto flex max-w-7xl items-center justify-center gap-2 px-4 text-center text-xs font-medium text-[#805400] sm:px-6 lg:px-8">
          <SparklesIcon className="h-4 w-4 shrink-0 text-[#A66F00]" />
          <span>
            المبدأ الحاكم لمرشدي: <strong>الذكاء الاصطناعي يشرح — القواعد الأكاديمية واللوائح المعتمدة تقرر.</strong>
          </span>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
          {/* Brand Column */}
          <div className="space-y-4 md:col-span-1">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl border border-[#EDE2C5] bg-[#FFF4C7] shadow-2xs">
                <Image
                  src="/brand/morshidi-guide.png"
                  alt="مرشدي"
                  width={36}
                  height={36}
                  className="object-contain p-0.5"
                />
              </div>
              <div>
                <span className="block text-lg font-bold text-[#28241C]">مرشدي</span>
                <span className="block text-xs text-[#726B5E]">نظام الذكاء الأكاديمي</span>
              </div>
            </Link>
            <p className="text-xs leading-relaxed text-[#726B5E]">
              منصة ذكية موحدة لمساعدة طلبة الجامعات على فهم متطلبات خططهم الدراسية، فحص الأهلية المسبقة، والتخطيط الأكاديمي الشفاف.
            </p>
          </div>

          {/* Academic Tools Column */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#A66F00]">
              الأدوات الأكاديمية
            </h3>
            <ul className="mt-3 space-y-2 text-xs">
              <li>
                <Link href="/student/progress" className="text-[#726B5E] hover:text-[#805400] transition-colors">
                  متابعة التقدم في الخطة
                </Link>
              </li>
              <li>
                <Link href="/student/eligibility" className="text-[#726B5E] hover:text-[#805400] transition-colors">
                  فحص أهلية المواد
                </Link>
              </li>
              <li>
                <Link href="/student/planner" className="text-[#726B5E] hover:text-[#805400] transition-colors">
                  مخطط الفصل الدراسي
                </Link>
              </li>
              <li>
                <Link href="/student/degree-path" className="text-[#726B5E] hover:text-[#805400] transition-colors">
                  مسار التخرج المتوقع
                </Link>
              </li>
              <li>
                <Link href="/student/mock-registration" className="text-[#726B5E] hover:text-[#805400] transition-colors">
                  محاكاة التسجيل الفصلي
                </Link>
              </li>
            </ul>
          </div>

          {/* Governance & Policies */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#A66F00]">
              المعرفة والشفافية
            </h3>
            <ul className="mt-3 space-y-2 text-xs">
              <li>
                <Link href="/student/advisor" className="text-[#726B5E] hover:text-[#805400] transition-colors">
                  المرشد الأكاديمي الذكي
                </Link>
              </li>
              <li>
                <Link href="/student/policies" className="text-[#726B5E] hover:text-[#805400] transition-colors">
                  اللوائح والسياسات الجامعية
                </Link>
              </li>
              <li>
                <Link href="/student/decision-history" className="text-[#726B5E] hover:text-[#805400] transition-colors">
                  سجل القرارات والتدقيق
                </Link>
              </li>
              <li>
                <Link href="/#how-it-works" className="text-[#726B5E] hover:text-[#805400] transition-colors">
                  كيف يعمل محرك القواعد
                </Link>
              </li>
            </ul>
          </div>

          {/* Academic Disclaimer */}
          <div className="rounded-2xl border border-[#EDE2C5] bg-white p-4 shadow-2xs">
            <h4 className="text-xs font-bold text-[#28241C]">إخلاء مسؤولية أكاديمي</h4>
            <p className="mt-2 text-[11px] leading-relaxed text-[#726B5E]">
              مرشدي أداة استرشادية ذكية ولا يُعد بديلاً عن بوابة القبول والتسجيل الرسمية المعتمدة لدى الجامعة. يتم اعتماد تسجيل المواد والقرارات النهائية وفق الأنظمة والجهات المختصة.
            </p>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-[#EDE2C5] pt-6 text-xs text-[#726B5E] sm:flex-row">
          <p>© 2026 مرشدي (Morshidi). جميع الحقوق محفوظة.</p>
          <div className="flex gap-4">
            <span className="text-[11px] text-[#A66F00] font-semibold">
              إصدار البوابة: 2.0 (الموحدة)
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}