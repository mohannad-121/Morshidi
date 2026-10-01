"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { useAuth } from "@/auth/auth-provider";
import { SignOutButton } from "@/auth/sign-out-button";
import { AuthenticatedApiClient } from "@/lib/api/authenticated-client";
import { institutionNavVisible, institutionThemeClass, type CurrentInstitution } from "@/lib/institution-shell";
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

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#EDE2C5] bg-[#FFFCF4]/95 backdrop-blur-md transition-colors">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8" dir="rtl">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link href="/" className="group flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl border border-[#EDE2C5] bg-[#FFF4C7] shadow-2xs transition-transform group-hover:scale-105">
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
              <span className="block text-lg font-bold tracking-tight text-[#28241C] transition-colors group-hover:text-[#A66F00]">
                مرشدي
              </span>
              <span className="block text-[10px] font-medium text-[#726B5E]">
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
                      ? "bg-[#FFF4C7] text-[#805400]"
                      : "text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#A66F00]"
                  }`}
                >
                  الرئيسية
                </Link>
                <Link
                  href="/student/progress"
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    pathname.startsWith("/student/progress")
                      ? "bg-[#FFF4C7] text-[#805400]"
                      : "text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#A66F00]"
                  }`}
                >
                  خطتي
                </Link>
                <Link
                  href="/student/courses"
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    pathname.startsWith("/student/courses")
                      ? "bg-[#FFF4C7] text-[#805400]"
                      : "text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#A66F00]"
                  }`}
                >
                  المواد
                </Link>
                <Link
                  href="/student/planner"
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    pathname.startsWith("/student/planner")
                      ? "bg-[#FFF4C7] text-[#805400]"
                      : "text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#A66F00]"
                  }`}
                >
                  خطط لفصلك
                </Link>
                <Link
                  href="/student/advisor"
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    pathname.startsWith("/student/advisor")
                      ? "bg-[#FFF4C7] text-[#805400]"
                      : "text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#A66F00]"
                  }`}
                >
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#E2AD27] animate-pulse" />
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
                        ? "bg-[#FFF4C7] text-[#805400]"
                        : "text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#A66F00]"
                    }`}
                  >
                    <span>المزيد من الأدوات</span>
                    <ChevronDownIcon
                      className={`h-3 w-3 text-[#726B5E] transition-transform ${
                        moreDropdownOpen ? "rotate-180" : ""
                      }`}
                    />
                  </button>

                  {moreDropdownOpen && (
                    <div id="student-more-tools" className="absolute right-0 mt-2 w-64 rounded-2xl border border-[#EDE2C5] bg-white p-2 shadow-lg z-50">
                      <Link href="/student/intelligence" className="flex rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]">الذكاء الأكاديمي · عرض تجريبي</Link>
                      {institutionNavVisible(institution, "plan_transition") && <Link href="/student/plan-transition" className="flex rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]">مقارنة الخطط · نمذجة غير رسمية</Link>}
                      <div className="px-3 py-1.5 text-[10px] font-bold text-[#726B5E]">
                        الأدوات الأكاديمية الذكية
                      </div>
                      <Link href="/student/roadmap" className="flex rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]">الخارطة الأكاديمية</Link>
                      {institutionNavVisible(institution, "offerings") && <Link href="/student/offerings" className="flex rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]">العروض والجدول · بيانات تجريبية</Link>}
                      <Link href="/student/report" className="flex rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]">التقرير المُنمذج غير الرسمي</Link>
                      <Link
                        href="/student/eligibility"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#805400] transition-colors"
                      >
                        <EligibilityIcon className="h-4 w-4 text-[#A66F00]" />
                        <div>
                          <div>أهلية المواد</div>
                          <div className="text-[10px] font-normal text-[#726B5E]">فحص المتطلبات المسبقة</div>
                        </div>
                      </Link>
                      <Link
                        href="/student/recommendations"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#805400] transition-colors"
                      >
                        <RecommendationsIcon className="h-4 w-4 text-[#A66F00]" />
                        <div>
                          <div>التوصيات الذكية</div>
                          <div className="text-[10px] font-normal text-[#726B5E]">باقة المواد الأكثر تأثيراً</div>
                        </div>
                      </Link>
                      <Link
                        href="/student/degree-path"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#805400] transition-colors"
                      >
                        <DegreePathIcon className="h-4 w-4 text-[#A66F00]" />
                        <div>
                          <div>مسار التخرج</div>
                          <div className="text-[10px] font-normal text-[#726B5E]">توقع الفصول حتى التخرج</div>
                        </div>
                      </Link>
                      <Link
                        href="/student/mock-registration"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#805400] transition-colors"
                      >
                        <MockRegistrationIcon className="h-4 w-4 text-[#A66F00]" />
                        <div>
                          <div>التسجيل التجريبي</div>
                          <div className="text-[10px] font-normal text-[#726B5E]">محاكاة رغبات غير ملزمة</div>
                        </div>
                      </Link>
                      <div className="my-1 border-t border-[#EDE2C5]/60" />
                      <Link
                        href="/student/policies"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#805400] transition-colors"
                      >
                        <PoliciesIcon className="h-4 w-4 text-[#A66F00]" />
                        <div>
                          <div>اللوائح والسياسات</div>
                          <div className="text-[10px] font-normal text-[#726B5E]">الأنظمة والتعليمات</div>
                        </div>
                      </Link>
                      <Link
                        href="/student/decision-history"
                        className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#805400] transition-colors"
                      >
                        <DecisionHistoryIcon className="h-4 w-4 text-[#A66F00]" />
                        <div>
                          <div>سجل القرارات</div>
                          <div className="text-[10px] font-normal text-[#726B5E]">سجل التدقيق والتتبع</div>
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
                      ? "bg-[#FFF4C7] text-[#805400]"
                      : "text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#A66F00]"
                  }`}
                >
                  الرئيسية
                </Link>
                <Link
                  href="/#how-it-works"
                  className="rounded-lg px-3 py-1.5 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#A66F00] transition-colors"
                >
                  كيف يعمل مرشدي
                </Link>
                <Link
                  href="/#features"
                  className="rounded-lg px-3 py-1.5 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#A66F00] transition-colors"
                >
                  المزايا الأكاديمية
                </Link>
                <Link
                  href="/#demo"
                  className="rounded-lg px-3 py-1.5 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#A66F00] transition-colors"
                >
                  محاكي الأهلية
                </Link>
                <Link
                  href="/#about"
                  className="rounded-lg px-3 py-1.5 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#A66F00] transition-colors"
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
                className="flex items-center gap-2.5 rounded-xl border border-[#EDE2C5] bg-white px-3 py-1.5 text-xs font-semibold text-[#28241C] shadow-2xs hover:bg-[#FFF9E8] transition-colors"
                aria-expanded={accountDropdownOpen}
                aria-haspopup="true"
              >
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#FFF4C7] text-[#805400]">
                  <ProfileIcon className="h-4 w-4" />
                </div>
                <div className="text-right">
                  <span className="block text-xs font-bold leading-tight text-[#28241C]">حسابي</span>
                  <span className="block max-w-[120px] truncate text-[10px] text-[#726B5E]" dir="ltr">
                    {auth.user?.email ?? "الطالب"}
                  </span>
                </div>
                <ChevronDownIcon
                  className={`h-3 w-3 text-[#726B5E] transition-transform ${
                    accountDropdownOpen ? "rotate-180" : ""
                  }`}
                />
              </button>

              {accountDropdownOpen && (
                <div className="absolute left-0 mt-2 w-56 rounded-2xl border border-[#EDE2C5] bg-white p-2 shadow-lg z-50">
                  <div className="border-b border-[#EDE2C5]/60 px-3 py-2 text-right">
                    <span className="inline-block rounded-full bg-[#FFF4C7] px-2 py-0.5 text-[10px] font-bold text-[#805400]">
                      طالب مسجل
                    </span>
                    <p className="mt-1 truncate font-mono text-xs text-[#28241C]" dir="ltr">
                      {auth.user?.email}
                    </p>
                  </div>
                  <div className="mt-1 space-y-0.5">
                    <Link
                      href="/student"
                      className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#805400] transition-colors"
                    >
                      <ProfileIcon className="h-4 w-4 text-[#A66F00]" />
                      <span>نظرة عامة على حسابي</span>
                    </Link>
                    <Link
                      href="/student/profile"
                      className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#805400] transition-colors"
                    >
                      <ProgressIcon className="h-4 w-4 text-[#A66F00]" />
                      <span>الملف الأكاديمي</span>
                    </Link>
                    <Link
                      href="/student/courses"
                      className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8] hover:text-[#805400] transition-colors"
                    >
                      <CoursesIcon className="h-4 w-4 text-[#A66F00]" />
                      <span>سجل موادي</span>
                    </Link>
                  </div>
                  <div className="my-1 border-t border-[#EDE2C5]/60" />
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
              className="inline-flex min-h-9 items-center justify-center gap-2 rounded-xl bg-[#A66F00] px-4 py-1.5 text-xs font-semibold text-white shadow-xs transition-colors hover:bg-[#805400]"
            >
              <span>دخول الطالب</span>
            </Link>
          )}

          {/* Mobile Menu Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#EDE2C5] bg-white text-[#28241C] hover:bg-[#FFF9E8] md:hidden transition-colors"
            aria-label="قائمة التنقل"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <CloseIcon className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="border-t border-[#EDE2C5] bg-[#FFFCF4] px-4 py-4 md:hidden" dir="rtl">
          <nav className="flex flex-col gap-2" aria-label="التنقل في الهاتف">
            {auth.isAuthenticated ? (
              <>
                <div className="rounded-xl border border-[#EDE2C5] bg-[#FFF9E8] p-3">
                  <div className="text-[10px] font-bold text-[#726B5E]">مرحباً بك:</div>
                  <div className="truncate font-mono text-xs font-semibold text-[#28241C]" dir="ltr">
                    {auth.user?.email}
                  </div>
                </div>
                <Link
                  href="/"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname === "/" ? "bg-[#FFF4C7] text-[#805400]" : "text-[#28241C] hover:bg-[#FFF9E8]"
                  }`}
                >
                  الرئيسية
                </Link>
                <Link
                  href="/student"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname === "/student" ? "bg-[#FFF4C7] text-[#805400]" : "text-[#28241C] hover:bg-[#FFF9E8]"
                  }`}
                >
                  نظرة عامة على حسابي
                </Link>
                <Link
                  href="/student/progress"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname.startsWith("/student/progress") ? "bg-[#FFF4C7] text-[#805400]" : "text-[#28241C] hover:bg-[#FFF9E8]"
                  }`}
                >
                  خطتي الأكاديمية
                </Link>
                <Link href="/student/roadmap" className="rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]">الخارطة الأكاديمية</Link>
                {institutionNavVisible(institution, "offerings") && <Link href="/student/offerings" className="rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]">العروض والجدول · بيانات تجريبية</Link>}
                <Link href="/student/report" className="rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]">التقرير غير الرسمي</Link>
                <Link
                  href="/student/courses"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname.startsWith("/student/courses") ? "bg-[#FFF4C7] text-[#805400]" : "text-[#28241C] hover:bg-[#FFF9E8]"
                  }`}
                >
                  المواد والدرجات
                </Link>
                <Link
                  href="/student/planner"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname.startsWith("/student/planner") ? "bg-[#FFF4C7] text-[#805400]" : "text-[#28241C] hover:bg-[#FFF9E8]"
                  }`}
                >
                  خطط لفصلك
                </Link>
                <Link
                  href="/student/advisor"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname.startsWith("/student/advisor") ? "bg-[#FFF4C7] text-[#805400]" : "text-[#28241C] hover:bg-[#FFF9E8]"
                  }`}
                >
                  مرشدي AI
                </Link>
                <Link
                  href="/student/eligibility"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]"
                >
                  فحص أهلية مادة
                </Link>
                <Link
                  href="/student/recommendations"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]"
                >
                  التوصيات الذكية
                </Link>
                <Link
                  href="/student/degree-path"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]"
                >
                  مسار التخرج
                </Link>
                <Link
                  href="/student/mock-registration"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]"
                >
                  التسجيل التجريبي
                </Link>
                <div className="my-2 border-t border-[#EDE2C5]" />
                <SignOutButton className="button-secondary w-full" />
              </>
            ) : (
              <>
                <Link
                  href="/"
                  className={`rounded-xl px-3 py-2 text-xs font-semibold ${
                    pathname === "/" ? "bg-[#FFF4C7] text-[#805400]" : "text-[#28241C] hover:bg-[#FFF9E8]"
                  }`}
                >
                  الرئيسية
                </Link>
                <Link
                  href="/#how-it-works"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]"
                >
                  كيف يعمل مرشدي
                </Link>
                <Link
                  href="/#features"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]"
                >
                  المزايا الأكاديمية
                </Link>
                <Link
                  href="/#demo"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]"
                >
                  محاكي الأهلية
                </Link>
                <Link
                  href="/#about"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-[#28241C] hover:bg-[#FFF9E8]"
                >
                  عن المنصة
                </Link>
                <div className="my-2 border-t border-[#EDE2C5]" />
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
