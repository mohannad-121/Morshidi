import type { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  badge?: ReactNode;
  icon?: ReactNode;
  variant?: "default" | "warm" | "gold";
  className?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  badge,
  icon,
  variant = "default",
  className = "",
}: StatCardProps) {
  const bgStyles = {
    default: "bg-[#FFFFFF] border-[#EDE2C5]",
    warm: "bg-[#FFF9E8] border-[#EDE2C5]",
    gold: "bg-[#FFF4C7] border-[#E2AD27]/40",
  }[variant];

  return (
    <div
      className={`rounded-2xl border p-5 shadow-[0_2px_10px_rgba(40,36,28,0.03)] transition-all hover:shadow-[0_4px_16px_rgba(40,36,28,0.06)] ${bgStyles} ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold tracking-wide text-[#726B5E]">{title}</p>
        {icon ? (
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#FFF4C7] text-[#A66F00]">
            {icon}
          </div>
        ) : null}
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-[#28241C] sm:text-3xl">
          {value}
        </span>
        {badge}
      </div>
      {subtitle ? (
        <p className="mt-2 text-xs leading-relaxed text-[#726B5E]">{subtitle}</p>
      ) : null}
    </div>
  );
}
