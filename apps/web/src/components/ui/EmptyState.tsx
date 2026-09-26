import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-2xl border border-dashed border-[#EDE2C5] bg-[#FFF9E8]/60 p-8 text-center sm:p-12 ${className}`}
    >
      {icon ? (
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00] shadow-xs">
          {icon}
        </div>
      ) : null}
      <h3 className="text-base font-bold text-[#28241C] sm:text-lg">{title}</h3>
      <p className="mt-2 max-w-md text-xs leading-relaxed text-[#726B5E] sm:text-sm">
        {description}
      </p>
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  );
}
