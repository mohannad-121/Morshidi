export function LoadingSkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-2xl border border-border bg-surface-muted p-6 shadow-xs ${className}`}
      role="status"
      aria-label="جاري التحميل"
    >
      <div className="h-4 w-1/3 rounded-lg bg-border/70" />
      <div className="mt-4 h-8 w-1/2 rounded-xl bg-accent-soft/80" />
      <div className="mt-3 h-3 w-3/4 rounded-lg bg-border/50" />
    </div>
  );
}

export function LoadingSkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <LoadingSkeletonCard key={index} />
      ))}
    </div>
  );
}

export function LoadingSkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div
      className="animate-pulse rounded-2xl border border-border bg-surface p-6"
      role="status"
      aria-label="جاري التحميل"
    >
      <div className="mb-6 flex justify-between">
        <div className="h-6 w-1/4 rounded-lg bg-border" />
        <div className="h-6 w-1/6 rounded-lg bg-border/60" />
      </div>
      <div className="space-y-4">
        {Array.from({ length: rows }).map((_, index) => (
          <div key={index} className="flex items-center justify-between border-b border-border/50 pb-3">
            <div className="h-4 w-1/3 rounded-md bg-border/70" />
            <div className="h-4 w-1/5 rounded-md bg-accent-soft" />
            <div className="h-4 w-1/6 rounded-md bg-border/50" />
          </div>
        ))}
      </div>
    </div>
  );
}
