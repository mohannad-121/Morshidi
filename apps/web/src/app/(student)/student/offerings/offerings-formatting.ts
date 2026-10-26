/**
 * Offerings Schedule & Status Localization Formatter
 *
 * Provides typed, elegant Arabic and English formatting for course offerings,
 * section meetings, capacity states, and planner overlay statuses.
 * Follows the system-verified ISO weekday convention (1=Monday ... 7=Sunday).
 */

export const ISO_WEEKDAY_NAMES_AR: Record<number, string> = {
  1: "الاثنين",
  2: "الثلاثاء",
  3: "الأربعاء",
  4: "الخميس",
  5: "الجمعة",
  6: "السبت",
  7: "الأحد",
};

export const ISO_WEEKDAY_NAMES_EN: Record<number, string> = {
  1: "Monday",
  2: "Tuesday",
  3: "Wednesday",
  4: "Thursday",
  5: "Friday",
  6: "Saturday",
  7: "Sunday",
};

export function formatWeekday(day: number | null | undefined, locale: "ar" | "en" = "ar"): string {
  if (day == null || typeof day !== "number") {
    return locale === "ar" ? "يوم غير محدد" : "Unspecified day";
  }
  if (locale === "en") {
    return ISO_WEEKDAY_NAMES_EN[day] ?? `Day ${day}`;
  }
  return ISO_WEEKDAY_NAMES_AR[day] ?? `يوم ${day}`;
}

export function formatTime12h(timeStr: string | null | undefined, locale: "ar" | "en" = "ar"): string {
  if (!timeStr || typeof timeStr !== "string") {
    return locale === "ar" ? "غير محدد" : "Unspecified";
  }
  const clean = timeStr.trim();
  const parts = clean.split(":");
  if (parts.length < 2) {
    return clean;
  }
  const hours = parseInt(parts[0], 10);
  const minutes = parseInt(parts[1], 10);
  if (isNaN(hours) || isNaN(minutes)) {
    return clean;
  }

  const period = hours >= 12
    ? (locale === "ar" ? "م" : "PM")
    : (locale === "ar" ? "ص" : "AM");

  let h12 = hours % 12;
  if (h12 === 0) h12 = 12;

  const padH = h12.toString().padStart(2, "0");
  const padM = minutes.toString().padStart(2, "0");

  return `${padH}:${padM} ${period}`;
}

export function formatTimeRange(
  startsAt: string | null | undefined,
  endsAt: string | null | undefined,
  locale: "ar" | "en" = "ar"
): string {
  const unspecified = locale === "ar" ? "غير محدد" : "Unspecified";
  const start = formatTime12h(startsAt, locale);
  const end = formatTime12h(endsAt, locale);
  if (start === unspecified && end === unspecified) {
    return locale === "ar" ? "الوقت غير محدد" : "Time unspecified";
  }
  return `${start} – ${end}`;
}

export function formatMeetingSchedule(
  meeting: { day: number | null | undefined; starts_at: string | null | undefined; ends_at: string | null | undefined },
  locale: "ar" | "en" = "ar"
): string {
  const day = formatWeekday(meeting.day, locale);
  const time = formatTimeRange(meeting.starts_at, meeting.ends_at, locale);
  return `${day} · ${time}`;
}

export function getAcademicDecisionLabel(decision: string | null | undefined, locale: "ar" | "en" = "ar"): string {
  if (!decision) return locale === "ar" ? "غير محدد" : "Unspecified";
  switch (decision.toUpperCase()) {
    case "ELIGIBLE":
      return locale === "ar" ? "مؤهل أكاديمياً" : "Academically Eligible";
    case "NOT_ELIGIBLE":
      return locale === "ar" ? "غير مؤهل أكاديمياً" : "Not Academically Eligible";
    case "CONDITIONAL":
      return locale === "ar" ? "مؤهل مشروط" : "Conditionally Eligible";
    case "UNKNOWN":
      return locale === "ar" ? "غير محدد" : "Unspecified";
    default:
      return locale === "ar" ? "غير محدد" : decision;
  }
}

export function getCapacityStateLabel(state: string | null | undefined, locale: "ar" | "en" = "ar"): string {
  if (!state) return locale === "ar" ? "غير محدد" : "Unspecified";
  switch (state.toUpperCase()) {
    case "KNOWN_OPEN":
    case "SECTION_OPEN":
      return locale === "ar" ? "مقاعد متاحة" : "Seats Available";
    case "KNOWN_FULL":
    case "SECTION_FULL":
      return locale === "ar" ? "الشعبة ممتلئة" : "Section Full";
    case "WAITLIST_AVAILABLE":
      return locale === "ar" ? "قائمة انتظار متاحة" : "Waitlist Available";
    case "UNKNOWN_CAPACITY":
    case "UNKNOWN":
      return locale === "ar" ? "غير محدد" : "Unspecified";
    default:
      return locale === "ar" ? "غير محدد" : state;
  }
}

export function getOperationalStateLabel(state: string | null | undefined, locale: "ar" | "en" = "ar"): string {
  if (!state) return locale === "ar" ? "غير محدد" : "Unspecified";
  switch (state.toUpperCase()) {
    case "AVAILABLE":
      return locale === "ar" ? "متاحة للتسجيل" : "Available for Registration";
    case "SECTION_OPEN":
      return locale === "ar" ? "الشعبة مفتوحة" : "Section Open";
    case "SECTION_FULL":
      return locale === "ar" ? "الشعبة ممتلئة" : "Section Full";
    case "PROVIDER_UNAVAILABLE":
      return locale === "ar" ? "بيانات الجامعة غير متاحة حالياً" : "University data unavailable";
    case "SNAPSHOT_STALE":
      return locale === "ar" ? "البيانات بحاجة لتحديث" : "Data needs update";
    case "OFFERING_COVERAGE_INCOMPLETE":
      return locale === "ar" ? "بيانات الفصل غير مكتملة" : "Incomplete term data";
    case "NO_OFFERINGS":
      return locale === "ar" ? "لا توجد شُعب مطروحة" : "No offerings";
    case "UNKNOWN":
      return locale === "ar" ? "غير محدد" : "Unspecified";
    default:
      return locale === "ar" ? "غير محدد" : state;
  }
}

export function getModalityLabel(modality: string | null | undefined, locale: "ar" | "en" = "ar"): string {
  if (!modality) return locale === "ar" ? "غير محدد" : "Unspecified";
  switch (modality.toUpperCase()) {
    case "IN_PERSON":
      return locale === "ar" ? "وجاهي" : "In-Person";
    case "ONLINE":
      return locale === "ar" ? "عن بُعد" : "Online";
    case "HYBRID":
      return locale === "ar" ? "مدمج" : "Hybrid";
    case "UNKNOWN":
      return locale === "ar" ? "غير محدد" : "Unspecified";
    default:
      return locale === "ar" ? "غير محدد" : modality;
  }
}

export function getPlannerStatusLabel(status: string | null | undefined, locale: "ar" | "en" = "ar"): string {
  if (!status) return locale === "ar" ? "غير محدد" : "Unspecified";
  switch (status.toUpperCase()) {
    case "CONFIRMED_KNOWN_OPEN_NONCONFLICTING_SET":
      return locale === "ar" ? "جدول مؤكد بدون تعارض" : "Confirmed Non-Conflicting Schedule";
    case "NO_CONFIRMED_SET_OR_INCOMPLETE_DATA":
      return locale === "ar" ? "تعذّر تأكيد الجدول أو البيانات غير مكتملة" : "Schedule Unconfirmed or Incomplete Data";
    case "CONFLICT_DETECTED":
      return locale === "ar" ? "يوجد تعارض في المواعيد" : "Schedule Conflict Detected";
    default:
      return locale === "ar" ? "غير محدد" : status;
  }
}

export function getConflictReasonLabel(reason: string | null | undefined, locale: "ar" | "en" = "ar"): string {
  if (!reason) return locale === "ar" ? "تعارض غير محدد" : "Unspecified conflict";
  switch (reason.toUpperCase()) {
    case "TIME_OVERLAP":
      return locale === "ar" ? "تعارض في أوقات المحاضرات" : "Time overlap";
    case "LOCATION_TRAVEL":
      return locale === "ar" ? "تعارض في موقع الحرم / القاعة" : "Location/travel conflict";
    default:
      return locale === "ar" ? "تعارض في الجدول" : reason;
  }
}
