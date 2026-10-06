"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { Logo } from "@/components/ui/Logo";
import { useAuth } from "@/auth/auth-provider";
import { SignOutButton } from "@/auth/sign-out-button";
import { AuthenticatedApiClient } from "@/lib/api/authenticated-client";
import { institutionNavVisible, institutionThemeClass, type CurrentInstitution } from "@/lib/institution-shell";
import { getStudentDisplayName } from "@/lib/student-identity";
import {
  ChevronDownIcon,
  MenuIcon,
  CloseIcon,
  ProfileIcon,
  EligibilityIcon,
  RecommendationsIcon,
  DegreePathIcon,
  MockRegistrationIcon,
  PoliciesIcon,
  DecisionHistoryIcon,
  ProgressIcon,
  CoursesIcon,
} from "@/components/ui/Icons";

export function GlobalNavbar() {
  const auth = useAuth();
  const displayName = getStudentDisplayName(auth.user);
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [moreDropdownOpen, setMoreDropdownOpen] = useState(false);
  const [accountDropdownOpen, setAccountDropdownOpen] = useState(false);
  const [institutionResult, setInstitutionResult] = useState<{ userId: string; context: CurrentInstitution } | null>(null);
  const institution = auth.isAuthenticated && institutionResult && institutionResult.userId === auth.user?.id
    ? institutionResult.context : null;

  const moreRef = useRef<HTMLDivElement>(null);
  const accountRef = useRef<HTMLDivElement>(null);

  const ownerId = auth.user?.id;
  const authenticated = auth.isAuthenticated;
  const isStudentRoute = pathname.startsWith("/student");
  const getAccessToken = auth.getAccessToken;
  const refreshAccessToken = auth.refreshAccessToken;
  const invalidateSession = auth.invalidateSession;
  useEffect(() => {
    // Opt in only after a governed server registry is installed; avoid default 503 traffic.
    if (process.env.NEXT_PUBLIC_INSTITUTION_CONTEXT_ENABLED !== "true" ||
        !authenticated || !ownerId || !isStudentRoute) return;
    const controller = new AbortController();
    const client = new AuthenticatedApiClient({ getAccessToken, refreshAccessToken, invalidateSession });
    void client.request("/api/v1/me/institution-context", { signal: controller.signal })
      .then(async (response) => {
        if (response.ok && !controller.signal.aborted) {
          const context = await response.json() as CurrentInstitution;
          if (!controller.signal.aborted) setInstitutionResult({ userId: ownerId, context });
        }
      })
      .catch(() => { /* No governed context: retain the existing neutral shell. */ });
    return () => controller.abort();
  }, [authenticated, ownerId, isStudentRoute, getAccessToken, refreshAccessToken, invalidateSession]);

  // Close dropdowns on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(event.target as Node)) {
        setMoreDropdownOpen(false);
      }
      if (accountRef.current && !accountRef.current.contains(event.target as Node)) {
        setAccountDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Close menus on route change
  useEffect(() => {
    setMobileMenuOpen(false);
    setMoreDropdownOpen(false);
    setAccountDropdownOpen(false);
  }, [pathname]);

  const isMoreActive =
    pathname.startsWith("/student/eligibility") ||
    pathname.startsWith("/student/recommendations") ||
    pathname.startsWith("/student/degree-path") ||
    pathname.startsWith("/student/roadmap") ||
    pathname.startsWith("/student/report") ||
    pathname.startsWith("/student/mock-registration") ||
    pathname.startsWith("/student/policies") ||
    pathname.startsWith("/student/decision-history");

  if (isStudentRoute || pathname === '/login') return null;
  if (!pathname.startsWith('/institutional')) return <header className="public-nav" dir="rtl"><Logo/><nav aria-label="التنقل الرئيسي"><Link href="/#the-path">الرحلة</Link><Link href="/#the-plan">التخطيط</Link><Link href="https://morshidi-university-portal.vercel.app/">الجامعة</Link></nav><Link className="button-secondary" href={auth.isAuthenticated?'/student':'/login'}>{auth.isAuthenticated?'حسابي':'دخول'} <span aria-hidden="true">↖</span></Link></header>;
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur-md transition-colors">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8" dir="rtl">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link href="/" className="group flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl border border-border bg-accent-soft shadow-2xs transition-transform group-hover:scale-105">
              <Image
                src="/brand/morshidi-guide.png"
                alt="مرشدي"
                width={36}
                height={36}
                className="object-contain p-0.5"
                priority
              />
            </div>
            <div>
              <span className="block text-lg font-bold tracking-tight text-foreground transition-colors group-hover:text-accent">
                مرشدي
              </span>
              <span className="block text-[10px] font-medium text-muted">
                نظام الذكاء الأكاديمي
              </span>
              {institution && <span className={`block max-w-40 truncate rounded px-1 text-[10px] ${institutionThemeClass(institution.theme_key)}`}>
                {institution.display_name}
              </span>}
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden items-center gap-1 md:flex" aria-label="التنقل الرئيسي">
            {auth.isAuthenticated ? (
              <>
                <Link
                  href="/"
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    pathname === "/"
                      ? "bg-accent-soft text-accent"
                      : "text-foreground hover:bg-surface-muted hover:text-accent"
                  }`}
                >
                  الرئيسية
                </Link>
                <Link
                  href="/student/progress"
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    pathname.startsWith("/student/progress")
                      ? "bg-accent-soft text-accent"
                      : "text-foreground hover:bg-surface-muted hover:text-accent"
                  }`}
                >
                  خطتي
                </Link>
                <Link
                  href="/student/courses"
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    pathname.startsWith("/student/courses")
                      ? "bg-accent-soft text-accent"
                      : "text-foreground hover:bg-surface-muted hover:text-accent"
                  }`}
                >
                  المواد
                </Link>
                <Link
                  href="/student/planner"
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    pathname.startsWith("/student/planner")
                      ? "bg-accent-soft text-accent"
                      : "text-foreground hover:bg-surface-muted hover:text-accent"
                  }`}
                >
                  خطط لفصلك
                </Link>
                <Link
                  href="/student/advisor"
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    pathname.startsWith("/student/advisor")
                      ? "bg-accent-soft text-accent"
                      : "text-foreground hover:bg-surface-muted hover:text-accent"
                  }`}
                >
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
                  <span>مرشدي AI</span>
                </Link>

                {/* More Tools Dropdown */}
                <div className="relative" ref={moreRef}>
                  <button
                    type="button"
                    onClick={() => setMoreDropdownOpen((prev) => !prev)}
                    aria-expanded={moreDropdownOpen}
                    aria-controls="student-more-tools"
                    className={`flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                      isMoreActive || moreDropdownOpen
                        ? "bg-accent-soft text-accent"
                        : "text-foreground hover:bg-surface-muted hover:text-accent"
                    }`}
                  >
                    <span>المزيد من الأدوات</span>
                    <ChevronDownIcon
                      className={`h-3 w-3 text-muted transition-transform ${
                        moreDropdownOpen ? "rotate-180" : ""
                      }`}
                    />
                  </button>

                  {moreDropdownOpen && (
                    <div id="student-more-tools" className="absolute right-0 mt-2 w-64 rounded-2xl border border-border bg-surface p-2 shadow-lg z-50">
                      <Link href="/student/intelligence" className="flex rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted">الذكاء الأكاديمي · عرض تجريبي</Link>
                      <Link href="/student/privacy" className="flex rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted">الخصوصية والتحكم بالبيانات</Link>
                      {institutionNavVisible(institution, "plan_transition") && <Link href="/student/plan-transition" className="flex rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted">مقارنة الخطط · نمذجة غير رسمية</Link>}
                      <div className="px-3 py-1.5 text-[10px] font-bold text-muted">
                        الأدوات الأكاديمية الذكية
                      </div>
                      <Link href="/student/roadmap" className="flex rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted">الخارطة الأكاديمية</Link>
                      {institutionNavVisible(institution, "offerings") && <Link href="/student/offerings" className="flex rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted">العروض والجدول · بيانات تجريبية</Link>}
                      <Link href="/student/report" className="flex rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted">التقرير المُنمذج غير الرسمي</Link>
                      <Link
                        href="/student/eligibility"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                      >
                        <EligibilityIcon className="h-4 w-4 text-accent" />
                        <div>
                          <div>أهلية المواد</div>
                          <div className="text-[10px] font-normal text-muted">فحص المتطلبات المسبقة</div>
                        </div>
                      </Link>
                      <Link
                        href="/student/recommendations"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                      >
                        <RecommendationsIcon className="h-4 w-4 text-accent" />
                        <div>
                          <div>التوصيات الذكية</div>
                          <div className="text-[10px] font-normal text-muted">باقة المواد الأكثر تأثيراً</div>
                        </div>
                      </Link>
                      <Link
                        href="/student/degree-path"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                      >
                        <DegreePathIcon className="h-4 w-4 text-accent" />
                        <div>
                          <div>مسار التخرج</div>
                          <div className="text-[10px] font-normal text-muted">توقع الفصول حتى التخرج</div>
                        </div>
                      </Link>
                      <Link
                        href="/student/mock-registration"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                      >
                        <MockRegistrationIcon className="h-4 w-4 text-accent" />
                        <div>
                          <div>التسجيل التجريبي</div>
                          <div className="text-[10px] font-normal text-muted">محاكاة رغبات غير ملزمة</div>
                        </div>
                      </Link>
                      <div className="my-1 border-t border-border/60" />
                      <Link
                        href="/student/policies"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                      >
                        <PoliciesIcon className="h-4 w-4 text-accent" />
                        <div>
                          <div>اللوائح والسياسات</div>
                          <div className="text-[10px] font-normal text-muted">الأنظمة والتعليمات</div>
                        </div>
                      </Link>
                      <Link
                        href="/student/decision-history"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                      >
                        <DecisionHistoryIcon className="h-4 w-4 text-accent" />
                        <div>
                          <div>سجل القرارات</div>
                          <div className="text-[10px] font-normal text-muted">سجل التدقيق والتتبع</div>
                        </div>
                      </Link>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                <Link
                  href="/"
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    pathname === "/"
                      ? "bg-accent-soft text-accent"
                      : "text-foreground hover:bg-surface-muted hover:text-accent"
                  }`}
                >
                  الرئيسية
                </Link>
                <Link
                  href="/#how-it-works"
                  className="rounded-lg px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                >
                  كيف يعمل مرشدي
                </Link>
                <Link
                  href="/#features"
                  className="rounded-lg px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                >
                  المزايا الأكاديمية
                </Link>
                <Link
                  href="/#demo"
                  className="rounded-lg px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                >
                  محاكي الأهلية
                </Link>
                <Link
                  href="/#about"
                  className="rounded-lg px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                >
                  عن المنصة
                </Link>
              </>
            )}
          </nav>
        </div>

        {/* Left Side: Auth & User Actions */}
        <div className="flex items-center gap-3">
          {auth.isAuthenticated ? (
            <div className="relative" ref={accountRef}>
              <button
                type="button"
                onClick={() => setAccountDropdownOpen((prev) => !prev)}
                className="flex items-center gap-2.5 rounded-xl border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-foreground shadow-2xs hover:bg-surface-muted transition-colors"
                aria-expanded={accountDropdownOpen}
                aria-haspopup="true"
              >
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-soft text-accent">
                  <ProfileIcon className="h-4 w-4" />
                </div>
                <div className="text-right">
                  <span className="block text-xs font-bold leading-tight text-foreground">حسابي</span>
                  <span className="block max-w-[120px] truncate text-[10px] text-muted" dir="ltr">
                    {displayName}
                  </span>
                </div>
                <ChevronDownIcon
                  className={`h-3 w-3 text-muted transition-transform ${
                    accountDropdownOpen ? "rotate-180" : ""
                  }`}
                />
              </button>

              {accountDropdownOpen && (
                <div className="absolute left-0 mt-2 w-56 rounded-2xl border border-border bg-surface p-2 shadow-lg z-50">
                  <div className="border-b border-border/60 px-3 py-2 text-right">
                    <span className="inline-block rounded-full bg-accent-soft px-2 py-0.5 text-[10px] font-bold text-accent">
                      طالب مسجل
                    </span>
                    <p className="mt-1 truncate text-xs font-semibold text-foreground">{displayName}</p>
                  </div>
                  <div className="mt-1 space-y-0.5">
                    <Link
                      href="/student"
                      className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                    >
                      <ProfileIcon className="h-4 w-4 text-accent" />
                      <span>نظرة عامة على حسابي</span>
                    </Link>
                    <Link
                      href="/student/profile"
                      className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                    >
                      <ProgressIcon className="h-4 w-4 text-accent" />
                      <span>الملف الأكاديمي</span>
                    </Link>
                    <Link
                      href="/student/courses"
                      className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted hover:text-accent transition-colors"
                    >
                      <CoursesIcon className="h-4 w-4 text-accent" />
                      <span>سجل موادي</span>
                    </Link>
                  </div>
                  <div className="my-1 border-t border-border/60" />
                  <div className="px-1 py-0.5">
                    <SignOutButton
                      className="flex w-full items-center justify-center gap-2 rounded-xl border border-red-200 bg-red-50/80 px-3 py-1.5 text-xs font-semibold text-red-800 hover:bg-red-100 transition-colors"
                    />
                  </div>
                </div>
              )}
            </div>
          ) : (
            <Link
              href="/login"
              className="inline-flex min-h-9 items-center justify-center gap-2 rounded-xl bg-accent px-4 py-1.5 text-xs font-semibold text-white shadow-xs transition-colors hover:bg-accent-hover"
            >
              <span>دخول الطالب</span>
            </Link>
          )}

          {/* Mobile Menu Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-surface text-foreground hover:bg-surface-muted md:hidden transition-colors"
            aria-label="قائمة التنقل"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <CloseIcon className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="border-t border-border bg-background px-4 py-4 md:hidden" dir="rtl">
          <nav className="flex flex-col gap-2" aria-label="التنقل في الهاتف">
            {auth.isAuthenticated ? (
              <>
                <div className="rounded-xl border border-border bg-surface-muted p-3">
                  <div className="text-[10px] font-bold text-muted">مرحباً بك:</div>
                  <div className="truncate text-xs font-semibold text-foreground">{displayName}</div>
                </div>
                <Link
                  href="/"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname === "/" ? "bg-accent-soft text-accent" : "text-foreground hover:bg-surface-muted"
                  }`}
                >
                  الرئيسية
                </Link>
                <Link
                  href="/student"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname === "/student" ? "bg-accent-soft text-accent" : "text-foreground hover:bg-surface-muted"
                  }`}
                >
                  نظرة عامة على حسابي
                </Link>
                <Link
                  href="/student/progress"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname.startsWith("/student/progress") ? "bg-accent-soft text-accent" : "text-foreground hover:bg-surface-muted"
                  }`}
                >
                  خطتي الأكاديمية
                </Link>
                <Link href="/student/roadmap" className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted">الخارطة الأكاديمية</Link>
                {institutionNavVisible(institution, "offerings") && <Link href="/student/offerings" className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted">العروض والجدول · بيانات تجريبية</Link>}
                <Link href="/student/report" className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted">التقرير غير الرسمي</Link>
                <Link href="/student/privacy" className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted">الخصوصية والتحكم بالبيانات</Link>
                <Link
                  href="/student/courses"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname.startsWith("/student/courses") ? "bg-accent-soft text-accent" : "text-foreground hover:bg-surface-muted"
                  }`}
                >
                  المواد والدرجات
                </Link>
                <Link
                  href="/student/planner"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname.startsWith("/student/planner") ? "bg-accent-soft text-accent" : "text-foreground hover:bg-surface-muted"
                  }`}
                >
                  خطط لفصلك
                </Link>
                <Link
                  href="/student/advisor"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname.startsWith("/student/advisor") ? "bg-accent-soft text-accent" : "text-foreground hover:bg-surface-muted"
                  }`}
                >
                  مرشدي AI
                </Link>
                <Link
                  href="/student/eligibility"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted"
                >
                  فحص أهلية مادة
                </Link>
                <Link
                  href="/student/recommendations"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted"
                >
                  التوصيات الذكية
                </Link>
                <Link
                  href="/student/degree-path"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted"
                >
                  مسار التخرج
                </Link>
                <Link
                  href="/student/mock-registration"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted"
                >
                  التسجيل التجريبي
                </Link>
                <div className="my-2 border-t border-border" />
                <SignOutButton className="button-secondary w-full" />
              </>
            ) : (
              <>
                <Link
                  href="/"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname === "/" ? "bg-accent-soft text-accent" : "text-foreground hover:bg-surface-muted"
                  }`}
                >
                  الرئيسية
                </Link>
                <Link
                  href="/#how-it-works"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted"
                >
                  كيف يعمل مرشدي
                </Link>
                <Link
                  href="/#features"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted"
                >
                  المزايا الأكاديمية
                </Link>
                <Link
                  href="/#demo"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted"
                >
                  محاكي الأهلية
                </Link>
                <Link
                  href="/#about"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-foreground hover:bg-surface-muted"
                >
                  عن المنصة
                </Link>
                <div className="my-2 border-t border-border" />
                <Link
                  href="/login"
                  className="button-primary w-full text-center"
                >
                  دخول الطالب
                </Link>
              </>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
