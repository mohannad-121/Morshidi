import { describe, expect, test } from "vitest";
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

describe("offerings-formatting", () => {
  describe("formatWeekday", () => {
    test("formats ISO weekdays 1-7 in Arabic correctly", () => {
      expect(formatWeekday(1, "ar")).toBe("الاثنين");
      expect(formatWeekday(2, "ar")).toBe("الثلاثاء");
      expect(formatWeekday(3, "ar")).toBe("الأربعاء");
      expect(formatWeekday(4, "ar")).toBe("الخميس");
      expect(formatWeekday(5, "ar")).toBe("الجمعة");
      expect(formatWeekday(6, "ar")).toBe("السبت");
      expect(formatWeekday(7, "ar")).toBe("الأحد");
    });

    test("formats ISO weekdays 1-7 in English correctly", () => {
      expect(formatWeekday(1, "en")).toBe("Monday");
      expect(formatWeekday(7, "en")).toBe("Sunday");
    });

    test("gracefully falls back for invalid/null day", () => {
      expect(formatWeekday(null, "ar")).toBe("يوم غير محدد");
      expect(formatWeekday(null, "en")).toBe("Unspecified day");
      expect(formatWeekday(9, "ar")).toBe("يوم 9");
      expect(formatWeekday(9, "en")).toBe("Day 9");
    });
  });

  describe("formatTime12h", () => {
    test("converts morning hours and strips seconds", () => {
      expect(formatTime12h("09:00:00", "ar")).toBe("09:00 ص");
      expect(formatTime12h("09:00", "ar")).toBe("09:00 ص");
      expect(formatTime12h("11:00:00", "ar")).toBe("11:00 ص");
      expect(formatTime12h("11:00:00", "en")).toBe("11:00 AM");
    });

    test("converts noon and afternoon hours", () => {
      expect(formatTime12h("12:00:00", "ar")).toBe("12:00 م");
      expect(formatTime12h("12:30:00", "ar")).toBe("12:30 م");
      expect(formatTime12h("13:15:00", "ar")).toBe("01:15 م");
      expect(formatTime12h("17:45:00", "ar")).toBe("05:45 م");
      expect(formatTime12h("12:00:00", "en")).toBe("12:00 PM");
      expect(formatTime12h("14:30:00", "en")).toBe("02:30 PM");
    });

    test("converts midnight correctly", () => {
      expect(formatTime12h("00:00:00", "ar")).toBe("12:00 ص");
      expect(formatTime12h("00:30:00", "ar")).toBe("12:30 ص");
      expect(formatTime12h("00:00:00", "en")).toBe("12:00 AM");
    });

    test("handles null or invalid times", () => {
      expect(formatTime12h(null, "ar")).toBe("غير محدد");
      expect(formatTime12h("", "ar")).toBe("غير محدد");
      expect(formatTime12h(null, "en")).toBe("Unspecified");
    });
  });

  describe("formatTimeRange", () => {
    test("formats time range with en-dash and 12-hour times", () => {
      expect(formatTimeRange("11:00:00", "12:00:00", "ar")).toBe("11:00 ص – 12:00 م");
      expect(formatTimeRange("11:00:00", "12:30:00", "ar")).toBe("11:00 ص – 12:30 م");
      expect(formatTimeRange("11:00:00", "12:00:00", "en")).toBe("11:00 AM – 12:00 PM");
    });

    test("handles missing start or end", () => {
      expect(formatTimeRange(null, null, "ar")).toBe("الوقت غير محدد");
      expect(formatTimeRange(null, null, "en")).toBe("Time unspecified");
    });
  });

  describe("formatMeetingSchedule", () => {
    test("formats complete meeting string in Arabic", () => {
      expect(formatMeetingSchedule({ day: 7, starts_at: "11:00:00", ends_at: "12:00:00" }, "ar"))
        .toBe("الأحد · 11:00 ص – 12:00 م");
      expect(formatMeetingSchedule({ day: 2, starts_at: "11:00:00", ends_at: "12:30:00" }, "ar"))
        .toBe("الثلاثاء · 11:00 ص – 12:30 م");
    });

    test("formats complete meeting string in English", () => {
      expect(formatMeetingSchedule({ day: 1, starts_at: "09:00:00", ends_at: "10:30:00" }, "en"))
        .toBe("Monday · 09:00 AM – 10:30 AM");
    });
  });

  describe("status mappings", () => {
    test("academic decision labels", () => {
      expect(getAcademicDecisionLabel("ELIGIBLE", "ar")).toBe("مؤهل أكاديمياً");
      expect(getAcademicDecisionLabel("NOT_ELIGIBLE", "ar")).toBe("غير مؤهل أكاديمياً");
      expect(getAcademicDecisionLabel("UNKNOWN", "ar")).toBe("غير محدد");
      expect(getAcademicDecisionLabel("ELIGIBLE", "en")).toBe("Academically Eligible");
      expect(getAcademicDecisionLabel("NOT_ELIGIBLE", "en")).toBe("Not Academically Eligible");
    });

    test("capacity state labels", () => {
      expect(getCapacityStateLabel("KNOWN_OPEN", "ar")).toBe("مقاعد متاحة");
      expect(getCapacityStateLabel("SECTION_OPEN", "ar")).toBe("مقاعد متاحة");
      expect(getCapacityStateLabel("KNOWN_FULL", "ar")).toBe("الشعبة ممتلئة");
      expect(getCapacityStateLabel("UNKNOWN_CAPACITY", "ar")).toBe("غير محدد");
      expect(getCapacityStateLabel("UNKNOWN", "ar")).toBe("غير محدد");
      expect(getCapacityStateLabel("KNOWN_OPEN", "en")).toBe("Seats Available");
      expect(getCapacityStateLabel("KNOWN_FULL", "en")).toBe("Section Full");
    });

    test("operational state labels", () => {
      expect(getOperationalStateLabel("AVAILABLE", "ar")).toBe("متاحة للتسجيل");
      expect(getOperationalStateLabel("SECTION_OPEN", "ar")).toBe("الشعبة مفتوحة");
      expect(getOperationalStateLabel("PROVIDER_UNAVAILABLE", "ar")).toBe("بيانات الجامعة غير متاحة حالياً");
      expect(getOperationalStateLabel("SNAPSHOT_STALE", "ar")).toBe("البيانات بحاجة لتحديث");
      expect(getOperationalStateLabel("OFFERING_COVERAGE_INCOMPLETE", "ar")).toBe("بيانات الفصل غير مكتملة");
      expect(getOperationalStateLabel("AVAILABLE", "en")).toBe("Available for Registration");
      expect(getOperationalStateLabel("PROVIDER_UNAVAILABLE", "en")).toBe("University data unavailable");
    });

    test("modality labels", () => {
      expect(getModalityLabel("IN_PERSON", "ar")).toBe("وجاهي");
      expect(getModalityLabel("ONLINE", "ar")).toBe("عن بُعد");
      expect(getModalityLabel("HYBRID", "ar")).toBe("مدمج");
      expect(getModalityLabel("IN_PERSON", "en")).toBe("In-Person");
      expect(getModalityLabel("ONLINE", "en")).toBe("Online");
      expect(getModalityLabel("HYBRID", "en")).toBe("Hybrid");
    });

    test("planner status and conflict reason labels", () => {
      expect(getPlannerStatusLabel("CONFIRMED_KNOWN_OPEN_NONCONFLICTING_SET", "ar")).toBe("جدول مؤكد بدون تعارض");
      expect(getPlannerStatusLabel("NO_CONFIRMED_SET_OR_INCOMPLETE_DATA", "ar")).toBe("تعذّر تأكيد الجدول أو البيانات غير مكتملة");
      expect(getConflictReasonLabel("TIME_OVERLAP", "ar")).toBe("تعارض في أوقات المحاضرات");
      expect(getConflictReasonLabel("LOCATION_TRAVEL", "ar")).toBe("تعارض في موقع الحرم / القاعة");
    });
  });
});
