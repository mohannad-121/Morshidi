import type { ReactNode } from "react";
import { SparklesIcon } from "@/components/ui/Icons";

interface UnderDevelopmentProps {
  title?: string;
  badge?: string;
  message: string;
  details?: string;
  features?: string[];
  children?: ReactNode;
}

export function UnderDevelopmentState({
  title = "الخدمة قيد التجهيز",
  badge = "قريباً",
  message,
  details,
  features,
  children,
}: UnderDevelopmentProps) {
  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-3xl border border-[#EDE2C5] bg-gradient-to-b from-[#FFF4C7]/60 via-[#FFF9E8] to-[#FFFFFF] p-8 text-center shadow-xs sm:p-12">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00] shadow-sm">
          <SparklesIcon className="h-7 w-7" />
        </div>

        <div className="mt-4 flex items-center justify-center gap-2">
          <span className="rounded-full bg-[#A66F00]/10 px-3 py-1 text-xs font-bold text-[#A66F00]">
            {badge}
          </span>
          <h2 className="text-xl font-bold text-[#28241C] sm:text-2xl">{title}</h2>
        </div>

        <p className="mx-auto mt-4 max-w-xl text-sm leading-relaxed font-semibold text-[#805400] sm:text-base">
          {message}
        </p>

        {details ? (
          <p className="mx-auto mt-2 max-w-xl text-xs leading-relaxed text-[#726B5E] sm:text-sm">
            {details}
          </p>
        ) : null}

        {features && features.length > 0 ? (
          <div className="mx-auto mt-8 max-w-lg rounded-2xl border border-[#EDE2C5] bg-white p-5 text-right shadow-xs">
            <h4 className="text-xs font-bold text-[#726B5E]">ما ستتضمنه هذه الخدمة:</h4>
            <ul className="mt-3 space-y-2 text-xs text-[#28241C]">
              {features.map((item, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#E2AD27]" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="mt-6 text-[11px] font-medium text-[#726B5E]">
          المبدأ الحاكم: <span className="font-semibold text-[#28241C]">الذكاء الاصطناعي يشرح — القواعد الأكاديمية تقرر.</span>
        </div>
      </div>

      {children ? <div className="opacity-60 pointer-events-none select-none">{children}</div> : null}
    </div>
  );
}
