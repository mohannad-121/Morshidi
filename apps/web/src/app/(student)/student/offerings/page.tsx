"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Clock3,
  MapPin,
  Search,
  UsersRound,
  X,
} from "lucide-react";
import { CourseIdentity, CourseReferences, localizedCourseName } from "@/components/academic/CourseIdentity";
import {
  P10OfferingsApi,
  type OfferingPeriodsView,
  type OfferingPlannerView,
  type OfferingView,
  type PeriodOfferingsView,
  type SectionView,
} from "@/lib/api/p10-offerings";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { useCourseIdentities, type CourseDisplayIdentity } from "@/lib/api/use-course-identities";
import {
  normalizeCourseSearch,
  normalizeRelaxedSearch,
  rankCourseSuggestions,
} from "./course-search";
import {
  formatMeetingSchedule,
  formatTime12h,
  formatTimeRange,
  formatWeekday,
  getAcademicDecisionLabel,
  getCapacityStateLabel,
  getConflictReasonLabel,
  getModalityLabel,
  getOperationalStateLabel,
  getPlannerStatusLabel,
} from "./offerings-formatting";

export { normalizeCourseSearch, normalizeRelaxedSearch, rankCourseSuggestions } from "./course-search";
export {
  formatMeetingSchedule,
  formatTime12h,
  formatTimeRange,
  formatWeekday,
  getAcademicDecisionLabel,
  getCapacityStateLabel,
  getConflictReasonLabel,
  getModalityLabel,
  getOperationalStateLabel,
  getPlannerStatusLabel,
} from "./offerings-formatting";

const messages = {
  ar: {
    title: "العروض والجدول الدراسي",
    intro: "التحقق الأكاديمي مستقل عن توفر الشُعب والمقاعد.",
    search: "ابحث عن مادة",
    searchHint: "اكتب اسم المادة (مثال: التربية، الذكاء، البرمجة) أو رمزها",
    year: "العام الأكاديمي",
    semester: "الفصل الدراسي",
    loading: "جارٍ التحميل…",
    error: "تعذّر تحميل بيانات العروض. لا يعني ذلك عدم طرح المادة.",
    noSemesterCourses: "لا يوجد مواد لهذا الفصل",
    noSearchMatches: "لا توجد مواد مطابقة لبحثك",
    incomplete: "بيانات هذا الفصل غير مكتملة؛ لا يمكن تأكيد جميع المواد المطروحة.",
    unavailable: "مزود العروض غير متاح. لا يمكن تأكيد توفر المواد.",
    synthetic: "SANDBOX / SYNTHETIC DATA — بيانات تجريبية غير رسمية",
    academic: "الأهلية الأكاديمية",
    operational: "الحالة التشغيلية",
    capacity: "المقاعد",
    campus: "الحرم / القاعة",
    unknown: "غير محدد",
    stale: "تحذير: بيانات العروض قديمة.",
    planner: "مقارنة الخطة الأكاديمية بالعروض",
    credits: "الحد الأقصى للساعات",
    offeredCourses: "مواد الفصل المطروحة",
    details: "تفاصيل المادة والشُعب",
    openRegistration: "التسجيل مفتوح",
    offeredThisSemester: "مطروحة هذا الفصل",
    inCatalog: "في الخطة الدراسية",
    clearSearch: "مسح البحث",
    noScheduledMeetings: "لا توجد مواعيد محددة للمحاضرات",
    locationUnspecified: "الموقع والقاعة غير محددة",
    enrolledSeats: "مقعد مسجل",
    seatsAvailable: "متاح",
    totalCapacity: "السعة الإجمالية",
    sectionsCount: "شُعب مطروحة",
    selectedSections: "الشُعب المقترحة:",
    conflictWarning: "تنبيه تعارض في الجدول:",
  },
  en: {
    title: "Offerings / Schedule",
    intro: "Academic eligibility is separate from section and seat availability.",
    search: "Search courses",
    searchHint: "Type a course name (e.g. Programming, Education) or code",
    year: "Academic year",
    semester: "Semester",
    loading: "Loading…",
    error: "Offering data could not be loaded. This does not mean the course is not offered.",
    noSemesterCourses: "No courses are offered for this semester",
    noSearchMatches: "No courses match your search",
    incomplete: "This semester snapshot is incomplete; all offered courses cannot be confirmed.",
    unavailable: "Offering provider unavailable; course availability cannot be confirmed.",
    synthetic: "SANDBOX / SYNTHETIC DATA — not official",
    academic: "Academic eligibility",
    operational: "Operational state",
    capacity: "Seats",
    campus: "Campus / Location",
    unknown: "Unspecified",
    stale: "Warning: offering snapshot is stale.",
    planner: "Overlay offerings on academic plan",
    credits: "Maximum credits",
    offeredCourses: "Offered semester courses",
    details: "Course and section details",
    openRegistration: "Registration open",
    offeredThisSemester: "Offered this semester",
    inCatalog: "In catalog",
    clearSearch: "Clear search",
    noScheduledMeetings: "No scheduled meeting times",
    locationUnspecified: "Location unspecified",
    enrolledSeats: "seats enrolled",
    seatsAvailable: "available",
    totalCapacity: "Total capacity",
    sectionsCount: "offered sections",
    selectedSections: "Suggested sections:",
    conflictWarning: "Schedule conflict warning:",
  },
} as const;

function yearFor(period: OfferingPeriodsView["periods"][number]): string {
  return period.starts_on?.slice(0, 4) || period.period_key.match(/(?:19|20)\d{2}/)?.[0] || "—";
}

function SectionCard({
  section,
  language,
  t,
}: {
  section: SectionView;
  language: "ar" | "en";
  t: (typeof messages)["ar"] | (typeof messages)["en"];
}) {
  const modalityLabel = getModalityLabel(section.modality, language);
  const capacityLabel = getCapacityStateLabel(section.capacity_state, language);

  const capacityBadgeClass =
    section.capacity_state === "KNOWN_OPEN" || section.capacity_state === "SECTION_OPEN"
      ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
      : section.capacity_state === "KNOWN_FULL" || section.capacity_state === "SECTION_FULL"
      ? "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20"
      : section.capacity_state === "WAITLIST_AVAILABLE"
      ? "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20"
      : "bg-muted text-muted-foreground border-border";

  const modalityBadgeClass =
    section.modality === "IN_PERSON"
      ? "bg-sky-500/10 text-sky-700 dark:text-sky-400 border-sky-500/20"
      : section.modality === "ONLINE"
      ? "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20"
      : section.modality === "HYBRID"
      ? "bg-teal-500/10 text-teal-700 dark:text-teal-400 border-teal-500/20"
      : "bg-muted text-muted-foreground border-border";

  return (
    <li className="rounded-xl border border-border/80 bg-card p-4 sm:p-5 shadow-xs transition-shadow hover:shadow-md" style={{ backgroundColor: "#121212" }}>
      {/* Header: Section Code + Modality + Capacity badge */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-muted px-2.5 py-1 text-xs sm:text-sm font-bold font-mono tracking-tight text-foreground">
            <bdi>{section.section_id}</bdi>
          </span>
          <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${modalityBadgeClass}`}>
            {modalityLabel}
          </span>
        </div>

        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${capacityBadgeClass}`}>
          <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />
          {capacityLabel}
        </span>
      </div>

      {/* Body details */}
      <div className="mt-3.5 space-y-2.5">
        {/* Meetings / Schedule */}
        <div className="space-y-1.5">
          {section.meetings && section.meetings.length > 0 ? (
            section.meetings.map((meeting, index) => (
              <div key={index} className="flex items-center gap-2 text-xs sm:text-sm text-foreground/90">
                <Clock3 size={15} className="shrink-0 text-muted-foreground" aria-hidden="true" />
                <span className="font-medium text-foreground">{formatWeekday(meeting.day, language)}</span>
                <span className="text-muted-foreground/60">·</span>
                <bdi dir="ltr" className="font-tabular-nums text-foreground/90">
                  {formatTime12h(meeting.starts_at, language)} – {formatTime12h(meeting.ends_at, language)}
                </bdi>
              </div>
            ))
          ) : (
            <div className="flex items-center gap-2 text-xs sm:text-sm text-muted-foreground">
              <Clock3 size={15} className="shrink-0 text-muted-foreground/70" aria-hidden="true" />
              <span>{t.noScheduledMeetings}</span>
            </div>
          )}
        </div>

        {/* Location / Campus */}
        <div className="flex items-center gap-2 text-xs sm:text-sm text-muted-foreground">
          <MapPin size={15} className="shrink-0 text-muted-foreground" aria-hidden="true" />
          <span>
            {section.campus || section.location ? (
              <>
                {section.campus ? <span className="font-medium text-foreground/80">{section.campus}</span> : null}
                {section.campus && section.location ? <span className="mx-1 text-muted-foreground/50">·</span> : null}
                {section.location ? <span>{section.location}</span> : null}
              </>
            ) : (
              <span>{t.locationUnspecified}</span>
            )}
          </span>
        </div>

        {/* Seats and Enrollment breakdown */}
        {(section.capacity != null || section.enrolled != null || section.available != null) && (
          <div className="flex items-center gap-2 border-t border-border/50 pt-2 text-xs sm:text-sm text-muted-foreground">
            <UsersRound size={15} className="shrink-0 text-muted-foreground" aria-hidden="true" />
            <span>
              {section.enrolled != null && section.capacity != null ? (
                language === "ar" ? (
                  <span>
                    <bdi className="font-semibold text-foreground">{section.enrolled} / {section.capacity}</bdi> {t.enrolledSeats}
                  </span>
                ) : (
                  <span>
                    <bdi className="font-semibold text-foreground">{section.enrolled} / {section.capacity}</bdi> {t.enrolledSeats}
                  </span>
                )
              ) : section.capacity != null ? (
                language === "ar" ? (
                  <span>
                    {t.totalCapacity}: <bdi className="font-semibold text-foreground">{section.capacity}</bdi> مقعد
                  </span>
                ) : (
                  <span>
                    {t.totalCapacity}: <bdi className="font-semibold text-foreground">{section.capacity}</bdi> seats
                  </span>
                )
              ) : null}
              {section.available != null && (
                <span className="ms-2 font-medium text-emerald-600 dark:text-emerald-400">
                  ({language === "ar" ? `${section.available} ${t.seatsAvailable}` : `${section.available} ${t.seatsAvailable}`})
                </span>
              )}
            </span>
          </div>
        )}
      </div>
    </li>
  );
}

export default function OfferingsPage() {
  const client = useAuthenticatedApi();
  const api = useMemo(() => new P10OfferingsApi(client), [client]);
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [period, setPeriod] = useState("");
  const [year, setYear] = useState("");
  const [periods, setPeriods] = useState<OfferingPeriodsView | null>(null);
  const [catalog, setCatalog] = useState<PeriodOfferingsView | null>(null);
  const [result, setResult] = useState<OfferingView | null>(null);
  const [planner, setPlanner] = useState<OfferingPlannerView | null>(null);
  const identities = useCourseIdentities(true);
  const [query, setQuery] = useState("");
  const [selectedCourse, setSelectedCourse] = useState("");
  const [comboboxOpen, setComboboxOpen] = useState(false);
  const [activeOption, setActiveOption] = useState(0);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const comboboxRef = useRef<HTMLDivElement>(null);
  const [maxCredits, setMaxCredits] = useState(15);
  const [busy, setBusy] = useState(false);
  const [catalogBusy, setCatalogBusy] = useState(false);
  const [error, setError] = useState(false);
  const t = messages[language];

  const identityRows = useMemo(() => [...identities]
    .filter(([key, row]) => key === row.course_code).map(([, row]) => row), [identities]);
  const offeredCodes = useMemo(() => [...new Set((catalog?.sections ?? []).map(section => section.course_code))], [catalog]);
  const offeredCodesSet = useMemo(() => new Set(offeredCodes), [offeredCodes]);

  const suggestions = useMemo(() =>
    query.trim() ? rankCourseSuggestions(identityRows, query, language, offeredCodesSet, 12) : [],
    [identityRows, query, language, offeredCodesSet]);

  const years = useMemo(() => [...new Set((periods?.periods ?? []).map(yearFor))], [periods]);
  const yearPeriods = useMemo(() => (periods?.periods ?? []).filter(item => yearFor(item) === year), [periods, year]);

  const shownCodes = useMemo(() => {
    if (!query.trim()) return offeredCodes;
    const matchingOffered = offeredCodes
      .map(code => identities.get(code) ?? { course_id: code, course_code: code, name_ar: null, name_en: null });
    return rankCourseSuggestions(matchingOffered, query, language, offeredCodesSet, 50).map(r => r.course_code);
  }, [identities, offeredCodes, offeredCodesSet, query, language]);

  useEffect(() => {
    let active = true;
    void api.periods().then((value) => {
      if (!active) return;
      setPeriods(value);
      const selected = value.periods.find(item => item.registration_open) ?? value.periods[0];
      setPeriod(selected?.period_key ?? "");
      setYear(selected ? yearFor(selected) : "");
    }).catch(() => {
      if (active) setPeriods({ status: "SOURCE_UNAVAILABLE", periods: [] });
    });
    return () => { active = false; };
  }, [api]);

  useEffect(() => {
    if (!period) return;
    let active = true;
    setCatalog(null); setCatalogBusy(true); setError(false); setResult(null); setSelectedCourse("");
    void api.periodOfferings(period).then(value => { if (active) setCatalog(value); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setCatalogBusy(false); });
    return () => { active = false; };
  }, [api, period]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (comboboxRef.current && !comboboxRef.current.contains(event.target as Node)) {
        setComboboxOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (comboboxOpen && suggestions.length > 0) {
      const el = document.getElementById(`offering-option-${activeOption}`);
      el?.scrollIntoView?.({ block: "nearest" });
    }
  }, [activeOption, comboboxOpen, suggestions.length]);

  function chooseYear(nextYear: string) {
    setYear(nextYear);
    const candidates = (periods?.periods ?? []).filter(item => yearFor(item) === nextYear);
    setPeriod((candidates.find(item => item.registration_open) ?? candidates[0])?.period_key ?? "");
  }

  async function chooseCourse(row: CourseDisplayIdentity) {
    if (blurTimer.current) clearTimeout(blurTimer.current);
    const fullName = localizedCourseName(row.name_ar, row.name_en, row.course_code, language);
    setQuery(fullName);
    setSelectedCourse(row.course_code);
    setComboboxOpen(false);
    setResult(null);
    setError(false);
    setBusy(true);
    try {
      setResult(await api.student(row.course_code, period));
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  function clearSelection() {
    setQuery("");
    setSelectedCourse("");
    setResult(null);
    setError(false);
    setComboboxOpen(false);
    setActiveOption(0);
    inputRef.current?.focus();
  }

  function onComboboxKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setComboboxOpen(false);
      return;
    }
    if (!suggestions.length) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setComboboxOpen(true);
      setActiveOption((index) =>
        (index + (event.key === "ArrowDown" ? 1 : -1) + suggestions.length) % suggestions.length,
      );
    } else if (event.key === "Enter" && comboboxOpen) {
      event.preventDefault();
      void chooseCourse(suggestions[activeOption] ?? suggestions[0]);
    }
  }

  async function plan() {
    setPlanner(null); setError(false); setBusy(true);
    try { setPlanner(await api.planner(period, maxCredits)); }
    catch { setError(true); }
    finally { setBusy(false); }
  }

  return (
    <main dir={language === "ar" ? "rtl" : "ltr"} className="mx-auto max-w-5xl space-y-6 p-4 text-foreground sm:p-6">
      <button
        type="button"
        onClick={() => setLanguage(language === "ar" ? "en" : "ar")}
        className="min-h-11 rounded-lg border border-border px-4 py-2 font-medium transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2"
        aria-label="Switch language"
      >
        {language === "ar" ? "English" : "العربية"}
      </button>

      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">{t.title}</h1>
        <p className="text-sm text-muted-foreground">{t.intro}</p>
      </header>

      <section aria-label={t.offeredCourses} className="space-y-4 rounded-xl border border-border bg-card p-4 sm:p-5 shadow-xs">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="grid gap-1.5 text-sm font-medium">
            {t.year}
            <select
              required
              value={year}
              onChange={(event) => chooseYear(event.target.value)}
              className="min-h-11 rounded-lg border border-border bg-background p-2.5 text-foreground transition-colors focus-visible:outline-2"
            >
              <option value="" disabled>
                {periods?.status === "SOURCE_UNAVAILABLE" ? t.unavailable : t.loading}
              </option>
              {years.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            {t.semester}
            <select
              required
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
              className="min-h-11 rounded-lg border border-border bg-background p-2.5 text-foreground transition-colors focus-visible:outline-2"
            >
              <option value="" disabled>
                {periods?.status === "SOURCE_UNAVAILABLE" ? t.unavailable : t.loading}
              </option>
              {yearPeriods.map((item) => (
                <option key={item.period_key} value={item.period_key}>
                  {language === "ar" ? item.name_ar : (item.name_en ?? item.name_ar)}
                  {item.registration_open ? ` · ${t.openRegistration}` : ""}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="relative z-30 isolate" ref={comboboxRef}>
          <label htmlFor="offering-course-search" className="mb-1.5 block text-sm font-medium">
            {t.search}
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-muted-foreground">
              <Search size={18} aria-hidden="true" />
            </span>
            <input
              ref={inputRef}
              id="offering-course-search"
              role="combobox"
              aria-autocomplete="list"
              aria-controls="offering-course-options"
              aria-expanded={comboboxOpen && suggestions.length > 0}
              aria-activedescendant={comboboxOpen && suggestions.length ? `offering-option-${activeOption}` : undefined}
              value={query}
              placeholder={t.searchHint}
              autoComplete="off"
              onChange={(event) => {
                setQuery(event.target.value);
                setSelectedCourse("");
                setResult(null);
                setActiveOption(0);
                setComboboxOpen(true);
              }}
              onFocus={() => setComboboxOpen(true)}
              onKeyDown={onComboboxKeyDown}
              onBlur={() => {
                blurTimer.current = setTimeout(() => setComboboxOpen(false), 200);
              }}
              className="min-h-11 w-full rounded-lg border border-border bg-background ps-10 pe-10 py-2.5 text-foreground transition-colors placeholder:text-muted-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            />
            {query.trim() && (
              <button
                type="button"
                aria-label={t.clearSearch}
                onClick={clearSelection}
                className="absolute end-3 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary"
              >
                <X size={16} aria-hidden="true" />
              </button>
            )}
          </div>

          {comboboxOpen && suggestions.length > 0 && (
            <ul
              id="offering-course-options"
              role="listbox"
              style={{ backgroundColor: "#141414", opacity: 1 }}
              className="absolute start-0 end-0 z-50 mt-2 max-h-84 w-full overflow-y-auto rounded-2xl border border-border-strong/40 bg-[#141414] p-2 shadow-2xl shadow-black/95 focus:outline-none divide-y divide-border/30"
            >
              {suggestions.map((row, index) => {
                const isOffered = offeredCodesSet.has(row.course_code);
                const isSelected = index === activeOption;
                const isCurrentCourse = selectedCourse === row.course_code;
                return (
                  <li
                    id={`offering-option-${index}`}
                    role="option"
                    aria-selected={isSelected}
                    key={row.course_id}
                    onMouseDown={(event) => event.preventDefault()}
                    onMouseEnter={() => setActiveOption(index)}
                    onClick={() => void chooseCourse(row)}
                    className={`group flex cursor-pointer items-start justify-between gap-3 rounded-xl px-4 py-3 transition-colors ${
                      isSelected ? "bg-white/[0.1] text-foreground" : "hover:bg-white/[0.05] text-foreground/90"
                    } ${isCurrentCourse ? "ring-1 ring-primary/40 bg-primary/10" : ""}`}
                  >
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex flex-wrap items-baseline gap-2">
                        <span className="text-sm font-semibold text-foreground leading-snug">
                          {localizedCourseName(row.name_ar, row.name_en, row.course_code, language)}
                        </span>
                        <span className="inline-flex items-center rounded bg-muted/80 px-2 py-0.5 font-mono text-xs font-medium text-muted-foreground border border-border/50" dir="ltr">
                          <bdi>{row.course_code}</bdi>
                        </span>
                      </div>
                      {language === "ar" && row.name_en && (
                        <p className="text-xs text-muted-foreground/75 font-normal truncate" dir="ltr">
                          {row.name_en}
                        </p>
                      )}
                      {language === "en" && row.name_ar && (
                        <p className="text-xs text-muted-foreground/75 font-normal truncate" dir="rtl">
                          {row.name_ar}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-2 pt-0.5">
                      {isOffered ? (
                        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                          {t.offeredThisSemester}
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full border border-border/80 bg-muted/50 px-2 py-0.5 text-xs font-medium text-muted-foreground">
                          {t.inCatalog}
                        </span>
                      )}
                      {isCurrentCourse && (
                        <Check size={16} className="text-primary shrink-0" aria-hidden="true" />
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          {query.trim() && suggestions.length === 0 && identityRows.length > 0 && (
            <p role="status" className="mt-2 text-sm text-muted-foreground">
              {t.noSearchMatches}
            </p>
          )}
        </div>

        {catalogBusy && <p role="status" className="text-sm text-muted-foreground">{t.loading}</p>}
        {error && <p role="alert" className="text-sm text-rose-600 dark:text-rose-400">{t.error}</p>}
        {catalog?.source_type === "SYNTHETIC" && (
          <p className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-3 text-sm font-semibold text-amber-900 dark:text-amber-300">
            {t.synthetic}
          </p>
        )}
        {catalog?.operational_state === "PROVIDER_UNAVAILABLE" && <p role="status" className="text-sm text-muted-foreground">{t.unavailable}</p>}
        {catalog?.operational_state === "OFFERING_COVERAGE_INCOMPLETE" && <p role="status" className="text-sm text-muted-foreground">{t.incomplete}</p>}
        {catalog?.operational_state === "SNAPSHOT_STALE" && <p role="alert" className="text-sm text-amber-700 dark:text-amber-400">{t.stale}</p>}
        {catalog?.operational_state === "NO_OFFERINGS" && <p className="text-sm text-muted-foreground">{t.noSemesterCourses}</p>}

        {catalog && catalog.operational_state !== "PROVIDER_UNAVAILABLE" && catalog.sections.length > 0 && (
          <div className="space-y-4 pt-2">
            <h2 className="text-lg font-bold tracking-tight">{t.offeredCourses}</h2>
            {shownCodes.length === 0 && query.trim() && <p className="text-sm text-muted-foreground">{t.noSearchMatches}</p>}
            <div className="grid gap-3.5 sm:grid-cols-2">
              {shownCodes.map((code) => {
                const sectionCount = catalog.sections.filter((section) => section.course_code === code).length;
                return (
                  <article
                    key={code}
                    className="flex flex-col justify-between rounded-xl border border-border bg-card p-4 shadow-xs transition-shadow hover:shadow-md" style={{ backgroundColor: "#121212" }}
                  >
                    <div>
                      <h3 className="font-semibold">
                        <CourseIdentity courseCode={code} identities={identities} locale={language} />
                      </h3>
                      <p className="mt-2 text-xs sm:text-sm text-muted-foreground">
                        {language === "ar"
                          ? `${sectionCount} ${sectionCount === 1 ? "شعبة مطروحة" : sectionCount === 2 ? "شعبتان مطروحتان" : "شُعب مطروحة"}`
                          : `${sectionCount} ${sectionCount === 1 ? "section offered" : "sections offered"}`}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        const row = identities.get(code) ?? { course_id: code, course_code: code, name_ar: null, name_en: null };
                        void chooseCourse(row);
                      }}
                      className="mt-4 inline-flex min-h-11 items-center justify-center rounded-lg bg-amber-800 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-800"
                    >
                      {t.details}
                    </button>
                  </article>
                );
              })}
            </div>
          </div>
        )}
      </section>

      {busy && <p role="status" className="text-sm text-muted-foreground">{t.loading}</p>}

      {result && selectedCourse && (
        <section aria-live="polite" className="space-y-4 rounded-xl border border-border bg-card p-4 sm:p-5 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
            <div>
              <h2 className="text-lg font-bold tracking-tight">{t.details}</h2>
              <div className="mt-1">
                <CourseIdentity courseCode={result.course_code} identities={identities} locale={language} />
              </div>
            </div>

            {/* Academic decision and operational state badges */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 text-xs">
                <span className="text-muted-foreground">{t.academic}:</span>
                <span
                  className={`inline-flex items-center gap-1 font-semibold ${
                    result.academic_decision === "ELIGIBLE"
                      ? "text-emerald-700 dark:text-emerald-400"
                      : result.academic_decision === "NOT_ELIGIBLE"
                      ? "text-rose-700 dark:text-rose-400"
                      : "text-foreground"
                  }`}
                >
                  {result.academic_decision === "ELIGIBLE" && <CheckCircle2 size={13} aria-hidden="true" />}
                  {result.academic_decision === "NOT_ELIGIBLE" && <AlertCircle size={13} aria-hidden="true" />}
                  {getAcademicDecisionLabel(result.academic_decision, language)}
                </span>
              </div>

              <div className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 text-xs">
                <span className="text-muted-foreground">{t.operational}:</span>
                <span className="font-semibold text-foreground">
                  {getOperationalStateLabel(result.operational_state, language)}
                </span>
              </div>
            </div>
          </div>

          {result.source_type === "SYNTHETIC" && (
            <p className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-3 text-sm font-semibold text-amber-900 dark:text-amber-300">
              {t.synthetic}
            </p>
          )}
          {result.operational_state === "SNAPSHOT_STALE" && <p role="alert" className="text-sm text-amber-700 dark:text-amber-400">{t.stale}</p>}
          {result.operational_state === "PROVIDER_UNAVAILABLE" && <p role="status" className="text-sm text-muted-foreground">{t.unavailable}</p>}
          {result.operational_state === "OFFERING_COVERAGE_INCOMPLETE" && <p role="status" className="text-sm text-muted-foreground">{t.incomplete}</p>}
          {result.sections.length === 0 && result.coverage_complete === true && <p className="text-sm text-muted-foreground">{t.noSemesterCourses}</p>}

          <ul className="grid gap-3.5 sm:grid-cols-2">
            {result.sections.map((section) => (
              <SectionCard key={section.section_id} section={section} language={language} t={t} />
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-4 rounded-xl border border-border bg-card p-4 sm:p-5 shadow-xs">
        <header className="space-y-1">
          <h2 className="text-lg font-bold tracking-tight">{t.planner}</h2>
          <p className="text-sm text-muted-foreground">{t.intro}</p>
        </header>

        <div className="flex flex-wrap items-end gap-3">
          <label className="grid max-w-xs gap-1.5 text-sm font-medium">
            {t.credits}
            <input
              type="number"
              min="0"
              max="30"
              value={maxCredits}
              onChange={(event) => setMaxCredits(Number(event.target.value))}
              className="min-h-11 rounded-lg border border-border bg-background p-2.5 text-foreground transition-colors focus-visible:outline-2"
            />
          </label>
          <button
            type="button"
            disabled={busy || !period}
            onClick={() => void plan()}
            className="min-h-11 rounded-lg bg-stone-800 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-stone-900 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stone-800"
          >
            {t.planner}
          </button>
        </div>

        {planner && (
          <div aria-live="polite" className="mt-4 space-y-3">
            {planner.source_type === "SYNTHETIC" && (
              <p className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-3 text-sm font-semibold text-amber-900 dark:text-amber-300">
                {t.synthetic}
              </p>
            )}
            {planner.offering_overlay.map((option) => (
              <div key={option.academic_rank} className="rounded-xl border border-border bg-background p-4 shadow-xs space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-primary/10 px-2.5 py-0.5 text-xs font-bold text-primary">
                      #{option.academic_rank}
                    </span>
                    <CourseReferences codes={option.course_codes} identities={identities} locale={language} />
                  </div>
                  <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-foreground">
                    {getPlannerStatusLabel(option.operational_status, language)}
                  </span>
                </div>

                {option.selected_section_ids && option.selected_section_ids.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">{t.selectedSections}</span>{" "}
                    <bdi className="font-mono">{option.selected_section_ids.join(", ")}</bdi>
                  </p>
                )}

                {option.possible_pair_conflicts && option.possible_pair_conflicts.length > 0 && (
                  <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 space-y-2 text-xs">
                    <p className="font-semibold text-amber-900 dark:text-amber-300">
                      {t.conflictWarning}
                    </p>
                    {option.possible_pair_conflicts.map((item, index) => (
                      <div key={index} className="flex flex-wrap items-center gap-1.5 text-muted-foreground">
                        <span className="font-medium text-foreground">{getConflictReasonLabel(item.reason, language)}:</span>
                        <span>
                          <bdi className="font-mono font-medium text-foreground">{item.first_section_id}</bdi>{" "}
                          {language === "ar" ? "مع" : "with"}{" "}
                          <bdi className="font-mono font-medium text-foreground">{item.second_section_id}</bdi>
                        </span>
                        <span className="text-muted-foreground/60">·</span>
                        <span>{formatWeekday(item.day, language)}</span>
                        {item.starts_at && item.ends_at && (
                          <>
                            <span className="text-muted-foreground/60">·</span>
                            <bdi dir="ltr" className="font-tabular-nums text-foreground">
                              {formatTime12h(item.starts_at, language)} – {formatTime12h(item.ends_at, language)}
                            </bdi>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
