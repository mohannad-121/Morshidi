"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { BarChart3, Blocks, Bot, Building2, ClipboardCheck, Gauge, GraduationCap,
  LayoutDashboard, Scale, SlidersHorizontal } from "lucide-react";
import { Logo } from "@/components/ui/Logo";
import { SignOutButton } from "@/auth/sign-out-button";

const links = [
  ["/institutional", "نظرة عامة", LayoutDashboard],
  ["/institutional/programs", "البرامج", GraduationCap],
  ["/institutional/courses", "المواد والطلب", BarChart3],
  ["/institutional/bottlenecks", "الاختناقات", Blocks],
  ["/institutional/capacity-intelligence", "الطاقة الاستيعابية", Gauge],
  ["/institutional/progress", "التقدم", Building2],
  ["/institutional/review-queue", "طابور المراجعة", ClipboardCheck],
  ["/institutional/what-if", "ماذا لو؟", SlidersHorizontal],
  ["/institutional/copilot", "المساعد المؤسسي", Bot],
] as const;

export function InstitutionalShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return <div dir="rtl" className="min-h-screen bg-background text-foreground">
    <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur-xl">
      <div className="mx-auto flex min-h-16 max-w-[1600px] items-center justify-between gap-4 px-4 lg:px-8">
        <Link href="/institutional" aria-label="مرشدي للذكاء المؤسسي" className="flex items-center gap-3">
          <Logo/><span className="hidden border-r border-border pr-3 text-sm text-muted sm:inline">الذكاء المؤسسي</span>
        </Link>
        <div className="flex items-center gap-2">
          <span className="hidden rounded-full border border-amber-500/25 bg-amber-500/10 px-3 py-1 text-xs text-amber-200 md:inline-flex">
            <Scale className="ml-1.5 size-4" aria-hidden="true"/> الذكاء يشرح، والقواعد تقرر
          </span>
          <SignOutButton/>
        </div>
      </div>
    </header>
    <div className="mx-auto grid max-w-[1600px] lg:grid-cols-[15rem_1fr]">
      <aside className="border-b border-border bg-surface p-3 lg:sticky lg:top-16 lg:h-[calc(100vh-4rem)] lg:border-b-0 lg:border-l lg:p-4" aria-label="أقسام الذكاء المؤسسي">
        <nav className="flex gap-2 overflow-x-auto pb-1 lg:grid lg:gap-1 lg:overflow-visible">
          {links.map(([href, label, Icon]) => {
            const active = pathname === href;
            return <Link key={href} href={href} aria-current={active ? "page" : undefined}
              className={`flex min-h-11 shrink-0 items-center gap-2 rounded-xl px-3 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-400 ${active ? "border border-amber-500/25 bg-amber-500/10 text-amber-100" : "text-muted hover:bg-white/5 hover:text-foreground"}`}>
              <Icon className="size-[18px]" strokeWidth={1.7} aria-hidden="true"/><span>{label}</span>
            </Link>;
          })}
        </nav>
      </aside>
      <div className="min-w-0">{children}</div>
    </div>
  </div>;
}
