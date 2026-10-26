"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Check, Search, X } from "lucide-react";
import { CourseIdentity, CourseReferences, localizedCourseName } from "@/components/academic/CourseIdentity";
import { P10OfferingsApi, type OfferingPeriodsView, type OfferingPlannerView,
  type OfferingView, type PeriodOfferingsView, type SectionView } from "@/lib/api/p10-offerings";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { useCourseIdentities, type CourseDisplayIdentity } from "@/lib/api/use-course-identities";
import {
  normalizeCourseSearch,
  normalizeRelaxedSearch,
  rankCourseSuggestions,
} from "./course-search";

export { normalizeCourseSearch, normalizeRelaxedSearch, rankCourseSuggestions } from "./course-search";

const messages = {
  ar: {
    title: "العروض والجدول الدراسي", intro: "التحقق الأكاديمي مستقل عن توفر الشُعب والمقاعد.",
    search: "ابحث عن مادة", searchHint: "اكتب اسم المادة (مثال: التربية، الذكاء، البرمجة) أو رمزها",
    year: "العام الأكاديمي", semester: "الفصل الدراسي", loading: "جارٍ التحميل…",
    error: "تعذّر تحميل بيانات العروض. لا يعني ذلك عدم طرح المادة.",
    noSemesterCourses: "لا يوجد مواد لهذا الفصل", noSearchMatches: "لا توجد مواد مطابقة لبحثك",
    incomplete: "بيانات هذا الفصل غير مكتملة؛ لا يمكن تأكيد جميع المواد المطروحة.",
    unavailable: "مزود العروض غير متاح. لا يمكن تأكيد توفر المواد.",
    synthetic: "SANDBOX / SYNTHETIC DATA — بيانات تجريبية غير رسمية",
    academic: "الأهلية الأكاديمية", operational: "الحالة التشغيلية", capacity: "المقاعد",
    campus: "الحرم / الموقع", unknown: "غير معروف", stale: "تحذير: بيانات العروض قديمة.",
    planner: "مقارنة الخطة الأكاديمية بالعروض", credits: "الحد الأقصى للساعات",
    offeredCourses: "مواد الفصل", details: "تفاصيل المادة", openRegistration: "التسجيل مفتوح",
    offeredThisSemester: "مطروحة هذا الفصل", inCatalog: "في الخطة الدراسية",
    clearSearch: "مسح البحث",
  },
  en: {
    title: "Offerings / Schedule", intro: "Academic eligibility is separate from section and seat availability.",
    search: "Search courses", searchHint: "Type a course name (e.g. Programming, Education) or code",
    year: "Academic year", semester: "Semester", loading: "Loading…",
    error: "Offering data could not be loaded. This does not mean the course is not offered.",
    noSemesterCourses: "No courses are offered for this semester", noSearchMatches: "No courses match your search",
    incomplete: "This semester snapshot is incomplete; all offered courses cannot be confirmed.",
    unavailable: "Offering provider unavailable; course availability cannot be confirmed.",
    synthetic: "SANDBOX / SYNTHETIC DATA — not official",
    academic: "Academic eligibility", operational: "Operational state", capacity: "Seats",
    campus: "Campus / location", unknown: "Unknown", stale: "Warning: offering snapshot is stale.",
    planner: "Overlay offerings on academic plan", credits: "Maximum credits",
    offeredCourses: "Semester courses", details: "Course details", openRegistration: "Registration open",
    offeredThisSemester: "Offered this semester", inCatalog: "In catalog",
    clearSearch: "Clear search",
  },
} as const;

function yearFor(period: OfferingPeriodsView["periods"][number]): string {
  return period.starts_on?.slice(0, 4) || period.period_key.match(/(?:19|20)\d{2}/)?.[0] || "—";
}

function SectionCard({ section, t }: { section: SectionView;
  t: typeof messages.ar | typeof messages.en }) {
  return <li className="rounded-lg border border-border bg-card p-4 shadow-sm">
    <h3 className="font-semibold"><bdi>{section.section_id}</bdi> · {section.modality}</h3>
    <p>{t.campus}: {section.campus ?? t.unknown} / {section.location ?? t.unknown}</p>
    <p>{t.capacity}: {section.capacity_state} ({section.capacity ?? t.unknown})</p>
    <ul>{section.meetings.map((block, index) => <li key={index}>
      {block.day}: <bdi>{block.starts_at}–{block.ends_at}</bdi> ({block.timezone})
    </li>)}</ul>
  </li>;
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

  return <main dir={language === "ar" ? "rtl" : "ltr"} className="mx-auto max-w-5xl space-y-6 p-4 text-foreground sm:p-6">
    <button type="button" onClick={() => setLanguage(language === "ar" ? "en" : "ar")}
      className="min-h-11 rounded border border-border px-4 py-2 focus-visible:outline-2 focus-visible:outline-offset-2"
      aria-label="Switch language">{language === "ar" ? "English" : "العربية"}</button>
    <header className="space-y-2"><h1 className="text-2xl font-bold">{t.title}</h1><p>{t.intro}</p></header>

    <section aria-label={t.offeredCourses} className="space-y-4 rounded-xl border border-border bg-card p-4 sm:p-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1">{t.year}<select required value={year} onChange={event => chooseYear(event.target.value)}
          className="min-h-11 rounded border border-border bg-background p-2 focus-visible:outline-2">
          <option value="" disabled>{periods?.status === "SOURCE_UNAVAILABLE" ? t.unavailable : t.loading}</option>
          {years.map(item => <option key={item} value={item}>{item}</option>)}
        </select></label>
        <label className="grid gap-1">{t.semester}<select required value={period}
          onChange={event => setPeriod(event.target.value)} className="min-h-11 rounded border border-border bg-background p-2 focus-visible:outline-2">
          <option value="" disabled>{periods?.status === "SOURCE_UNAVAILABLE" ? t.unavailable : t.loading}</option>
          {yearPeriods.map(item => <option key={item.period_key} value={item.period_key}>
            {language === "ar" ? item.name_ar : (item.name_en ?? item.name_ar)}{item.registration_open ? ` · ${t.openRegistration}` : ""}
          </option>)}
        </select></label>
      </div>

      <div className="relative" ref={comboboxRef}>
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
            onChange={event => {
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
            className="absolute z-30 mt-1.5 max-h-80 w-full overflow-y-auto rounded-xl border border-border bg-card p-1.5 shadow-xl transition-all"
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
                  onMouseDown={event => event.preventDefault()}
                  onMouseEnter={() => setActiveOption(index)}
                  onClick={() => void chooseCourse(row)}
                  className={`flex cursor-pointer items-center justify-between gap-3 rounded-lg px-3.5 py-2.5 transition-colors ${
                    isSelected ? "bg-muted" : "hover:bg-muted/60"
                  } ${isCurrentCourse ? "ring-1 ring-primary/30" : ""}`}
                >
                  <div className="min-w-0 flex-1">
                    <CourseIdentity
                      courseCode={row.course_code}
                      nameAr={row.name_ar}
                      nameEn={row.name_en}
                      locale={language}
                    />
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {isOffered ? (
                      <span className="inline-flex items-center rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-400">
                        {t.offeredThisSemester}
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded-full border border-border bg-muted/50 px-2 py-0.5 text-xs text-muted-foreground">
                        {t.inCatalog}
                      </span>
                    )}
                    {isCurrentCourse && (
                      <Check size={16} className="text-primary" aria-hidden="true" />
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

      {catalogBusy && <p role="status">{t.loading}</p>}
      {error && <p role="alert">{t.error}</p>}
      {catalog?.source_type === "SYNTHETIC" && <p className="rounded bg-amber-100 p-3 font-semibold text-amber-950">{t.synthetic}</p>}
      {catalog?.operational_state === "PROVIDER_UNAVAILABLE" && <p role="status">{t.unavailable}</p>}
      {catalog?.operational_state === "OFFERING_COVERAGE_INCOMPLETE" && <p role="status">{t.incomplete}</p>}
      {catalog?.operational_state === "SNAPSHOT_STALE" && <p role="alert">{t.stale}</p>}
      {catalog?.operational_state === "NO_OFFERINGS" && <p>{t.noSemesterCourses}</p>}
      {catalog && catalog.operational_state !== "PROVIDER_UNAVAILABLE" && catalog.sections.length > 0 && <div className="space-y-4">
        <h2 className="text-xl font-semibold">{t.offeredCourses}</h2>
        {shownCodes.length === 0 && query.trim() && <p>{t.noSearchMatches}</p>}
        <div className="grid gap-4 md:grid-cols-2">{shownCodes.map(code => <article key={code} className="rounded-lg border border-border p-4">
          <h3><CourseIdentity courseCode={code} identities={identities} locale={language} /></h3>
          <p className="mt-2 text-sm text-muted-foreground">{catalog.sections.filter(section => section.course_code === code).length} sections</p>
          <button type="button" onClick={() => {
            const row = identities.get(code) ?? { course_id: code, course_code: code, name_ar: null, name_en: null };
            void chooseCourse(row);
          }} className="mt-3 min-h-11 rounded bg-amber-800 px-4 py-2 text-white focus-visible:outline-2 focus-visible:outline-offset-2">
            {t.details}
          </button>
        </article>)}</div>
      </div>}
    </section>

    {busy && <p role="status">{t.loading}</p>}
    {result && selectedCourse && <section aria-live="polite" className="space-y-3">
      <h2 className="text-xl font-semibold">{t.details}</h2>
      <CourseIdentity courseCode={result.course_code} identities={identities} locale={language} />
      {result.source_type === "SYNTHETIC" && <p className="rounded bg-amber-100 p-3 font-semibold text-amber-950">{t.synthetic}</p>}
      <p>{t.academic}: {result.academic_decision} · {t.operational}: {result.operational_state}</p>
      <p>{result.source_version ?? t.unknown} · {result.fresh_until ?? t.unknown}</p>
      {result.operational_state === "SNAPSHOT_STALE" && <p role="alert">{t.stale}</p>}
      {result.operational_state === "PROVIDER_UNAVAILABLE" && <p role="status">{t.unavailable}</p>}
      {result.operational_state === "OFFERING_COVERAGE_INCOMPLETE" && <p role="status">{t.incomplete}</p>}
      {result.sections.length === 0 && result.coverage_complete === true && <p>{t.noSemesterCourses}</p>}
      <ul className="grid gap-3 md:grid-cols-2">{result.sections.map(section =>
        <SectionCard key={section.section_id} section={section} t={t} />)}</ul>
    </section>}

    <section className="space-y-3 rounded-xl border border-border p-4 sm:p-5">
      <h2 className="font-semibold">{t.planner}</h2><p>{t.intro}</p>
      <label className="grid max-w-xs gap-1">{t.credits}<input type="number" min="0" max="30" value={maxCredits}
        onChange={event => setMaxCredits(Number(event.target.value))} className="min-h-11 rounded border border-border bg-background p-2" /></label>
      <button type="button" disabled={busy || !period} onClick={() => void plan()}
        className="min-h-11 rounded bg-stone-800 px-4 py-2 text-white disabled:opacity-50">{t.planner}</button>
      {planner && <div aria-live="polite" className="space-y-2">
        {planner.source_type === "SYNTHETIC" && <p className="rounded bg-amber-100 p-3 font-semibold text-amber-950">{t.synthetic}</p>}
        {planner.offering_overlay.map(option => <div key={option.academic_rank} className="rounded border border-border p-3">
          <p>#{option.academic_rank} · <CourseReferences codes={option.course_codes} identities={identities} locale={language} /></p>
          <p>{option.operational_status}</p><p>{option.selected_section_ids?.join(", ") ?? t.unknown}</p>
          {option.possible_pair_conflicts?.map((item, index) => <p key={index}>
            {item.reason}: {item.first_section_id} / {item.second_section_id} · {item.day} ·
            {item.starts_at ?? t.unknown}–{item.ends_at ?? t.unknown} ({item.timezone ?? t.unknown})
          </p>)}
        </div>)}
      </div>}
    </section>
  </main>;
}
