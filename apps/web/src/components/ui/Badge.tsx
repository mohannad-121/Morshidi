import type { ReactNode } from "react";

export type BadgeVariant =
  | "gold"
  | "success"
  | "warning"
  | "review"
  | "error"
  | "neutral";

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
  size?: "sm" | "md";
}

export function Badge({
  children,
  variant = "neutral",
  className = "",
  size = "md",
}: BadgeProps) {
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs font-semibold";

  const variantClasses = {
    gold: "bg-[#FFF4C7] text-[#805400] border border-[#EDE2C5]",
    success: "bg-emerald-50 text-emerald-800 border border-emerald-200",
    warning: "bg-amber-50 text-amber-800 border border-amber-200",
    review: "bg-amber-100/70 text-amber-900 border border-amber-300 font-bold",
    error: "bg-red-50 text-red-800 border border-red-200",
    neutral: "bg-[#FFF9E8] text-[#726B5E] border border-[#EDE2C5]",
  }[variant];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full ${sizeClasses} ${variantClasses} ${className}`}
    >
      {children}
    </span>
  );
}
