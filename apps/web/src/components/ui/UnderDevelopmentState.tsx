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
      <div className="rounded-3xl border border-[#344739] bg-gradient-to-b from-[#15271F]/60 via-[#0F1A17] to-[#0F1A17] p-8 text-center shadow-xs sm:p-12">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#15271F] text-[#D9884A] shadow-sm">
          <SparklesIcon className="h-7 w-7" />
        </div>

        <div className="mt-4 flex items-center justify-center gap-2">
          <span className="rounded-full bg-[#D9884A]/10 px-3 py-1 text-xs font-bold text-[#D9884A]">
            {badge}
          </span>
          <h2 className="text-xl font-bold text-[#F3E9D8] sm:text-2xl">{title}</h2>
        </div>

        <p className="mx-auto mt-4 max-w-xl text-sm leading-relaxed font-semibold text-[#E5AC7C] sm:text-base">
          {message}
        </p>

        {details ? (
          <p className="mx-auto mt-2 max-w-xl text-xs leading-relaxed text-[#AEBCB3] sm:text-sm">
            {details}
          </p>
        ) : null}

        {features && features.length > 0 ? (
          <div className="mx-auto mt-8 max-w-lg rounded-2xl border border-[#344739] bg-surface p-5 text-right shadow-xs">
            <h4 className="text-xs font-bold text-[#AEBCB3]">ما ستتضمنه هذه الخدمة:</h4>
            <ul className="mt-3 space-y-2 text-xs text-[#F3E9D8]">
              {features.map((item, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#D9884A]" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="mt-6 text-[11px] font-medium text-[#AEBCB3]">
          المبدأ الحاكم: <span className="font-semibold text-[#F3E9D8]">الذكاء الاصطناعي يشرح — القواعد الأكاديمية تقرر.</span>
        </div>
      </div>

      {children ? <div className="opacity-60 pointer-events-none select-none">{children}</div> : null}
    </div>
  );
}
