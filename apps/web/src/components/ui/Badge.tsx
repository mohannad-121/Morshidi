import type { ReactNode } from "react";

export type BadgeVariant =
  | "gold"
  | "success"
  | "warning"
  | "review"
  | "error"
  | "danger"
  | "info"
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
    gold: "badge-gold",
    success: "badge-success",
    warning: "badge-warning",
    review: "badge-review font-bold",
    error: "badge-danger",
    danger: "badge-danger",
    info: "badge-info",
    neutral: "badge-neutral",
  }[variant];

  return (
    <span
      className={`badge inline-flex items-center gap-1.5 rounded-full ${sizeClasses} ${variantClasses} ${className}`}
    >
      {children}
    </span>
  );
}
