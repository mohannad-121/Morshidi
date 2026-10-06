import React from "react";
import { CheckCircle2, Loader2, Clock, AlertCircle } from "lucide-react";

export type StepStatus = "WAITING" | "ACTIVE" | "COMPLETE" | "ERROR";

export interface ProgressStep {
  id: string;
  title: string;
  description?: string;
  status: StepStatus;
}

export interface AcademicAnalysisProgressProps {
  title?: string;
  subtitle?: string;
  steps: ProgressStep[];
  className?: string;
}

export function AcademicAnalysisProgress({
  title = "جاري التحليل الأكاديمي الحتمي",
  subtitle = "يقوم النظام بمعالجة القواعد الأكاديمية وسجلات المواد",
  steps,
  className = "",
}: AcademicAnalysisProgressProps) {
  const completedCount = steps.filter((s) => s.status === "COMPLETE").length;
  const totalCount = steps.length;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
  const hasError = steps.some((s) => s.status === "ERROR");

  return (
    <div
      role="status"
      aria-live="polite"
      dir="rtl"
      className={`relative overflow-hidden rounded-2xl border border-border/80 bg-surface/90 p-6 shadow-card backdrop-blur-md transition-all ${className}`}
    >
      {/* Background ambient gold glow */}
      <div
        className="pointer-events-none absolute -top-12 -right-12 h-36 w-36 rounded-full bg-accent/5 blur-2xl"
        aria-hidden="true"
      />

      {/* Header with Title and Overall Percentage */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-5">
        <div>
          <span className="eyebrow text-accent font-semibold text-xs tracking-wider">
            المعالجة الحتمية
          </span>
          <h2 className="text-base font-bold text-foreground mt-0.5">{title}</h2>
          {subtitle ? (
            <p className="text-xs text-muted mt-1 leading-relaxed">{subtitle}</p>
          ) : null}
        </div>
        <div className="flex items-center gap-2 self-start sm:self-center">
          <span className="font-mono text-sm font-bold text-accent">
            {hasError ? "تعثر التحليل" : `${progressPercent}%`}
          </span>
        </div>
      </div>

      {/* Golden Progress Bar */}
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-surface-muted border border-border/40 mb-6"
        role="progressbar"
        aria-valuenow={progressPercent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={title}
      >
        <div
          className={`h-full transition-all duration-500 ease-out ${
            hasError
              ? "bg-danger"
              : "bg-gradient-to-r from-accent/80 via-accent to-accent-strong"
          }`}
          style={{ width: `${Math.max(5, progressPercent)}%` }}
        />
      </div>

      {/* Step List */}
      <ul className="space-y-3" aria-label="خطوات التحليل الأكاديمي">
        {steps.map((step, idx) => {
          const isActive = step.status === "ACTIVE";
          const isComplete = step.status === "COMPLETE";
          const isError = step.status === "ERROR";

          return (
            <li
              key={step.id}
              className={`flex items-start gap-3 rounded-xl p-3 transition-all ${
                isActive
                  ? "border border-accent/30 bg-accent-soft text-foreground shadow-xs"
                  : isError
                  ? "border border-danger/30 bg-danger/5 text-foreground"
                  : isComplete
                  ? "border border-border/30 bg-surface/50 text-foreground"
                  : "border border-transparent text-muted opacity-60"
              }`}
            >
              {/* Status Icon */}
              <div className="mt-0.5 shrink-0" aria-hidden="true">
                {isActive ? (
                  <Loader2 className="h-5 w-5 animate-spin text-accent" />
                ) : isComplete ? (
                  <CheckCircle2 className="h-5 w-5 text-accent" />
                ) : isError ? (
                  <AlertCircle className="h-5 w-5 text-danger" />
                ) : (
                  <Clock className="h-5 w-5 text-muted/60" />
                )}
              </div>

              {/* Step Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`text-xs font-bold leading-tight ${
                      isActive
                        ? "text-accent-strong"
                        : isComplete
                        ? "text-foreground"
                        : isError
                        ? "text-danger"
                        : "text-muted"
                    }`}
                  >
                    <span className="font-mono text-[10px] ml-1.5 opacity-70">
                      0{idx + 1}
                    </span>
                    {step.title}
                  </span>
                  <span
                    className={`text-[10px] font-mono shrink-0 px-2 py-0.5 rounded-full ${
                      isActive
                        ? "bg-accent/20 text-accent font-bold animate-pulse"
                        : isComplete
                        ? "bg-surface-muted text-accent font-medium"
                        : isError
                        ? "bg-danger/20 text-danger font-bold"
                        : "text-muted/60"
                    }`}
                  >
                    {isActive
                      ? "جاري المعالجة..."
                      : isComplete
                      ? "مكتمل"
                      : isError
                      ? "تعذر"
                      : "في الانتظار"}
                  </span>
                </div>
                {step.description ? (
                  <p className="text-[11px] text-muted mt-1 leading-normal">
                    {step.description}
                  </p>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
