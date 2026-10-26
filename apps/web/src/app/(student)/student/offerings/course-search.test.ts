import { describe, expect, it } from "vitest";
import {
  normalizeCourseSearch,
  normalizeRelaxedSearch,
  rankCourseSuggestions,
  scoreCourseMatch,
  stripArabicArticle,
} from "./course-search";
import type { CourseDisplayIdentity } from "@/lib/api/use-course-identities";

const sampleCourses: CourseDisplayIdentity[] = [
  { course_id: "c1", course_code: "1501110", name_ar: "التربية الوطنية", name_en: "National Education" },
  { course_id: "c2", course_code: "1501111", name_ar: "التربية الإسلامية", name_en: "Islamic Education" },
  { course_id: "c3", course_code: "1501211", name_ar: "مُقَدِّمة البرمجة", name_en: "Introduction to Programming" },
  { course_id: "c4", course_code: "1501330", name_ar: "الذكاء الاصطناعي", name_en: "Artificial Intelligence" },
  { course_id: "c5", course_code: "1501331", name_ar: "تعلم الآلة", name_en: "Machine Learning" },
  { course_id: "c6", course_code: "1501340", name_ar: "مناهج التربية وطرق التدريس", name_en: "Education Curricula" },
  { course_id: "c7", course_code: "MATH101", name_ar: "تفاضل وتكامل 1", name_en: "Calculus I" },
  { course_id: "c8", course_code: "CS101", name_ar: "أساسيات الحاسوب", name_en: "Computer Fundamentals" },
];

describe("Course Search & Autocomplete Intelligence", () => {
  it("normalizes Arabic diacritics, tatweel, alef variants, and alif maqsura strictly", () => {
    expect(normalizeCourseSearch("إِدَارَةُ الـمُحتوى")).toBe("ادارة المحتوي");
  });

  it("relaxes Teh-Marbuta to Heh in relaxed search for casual typing", () => {
    expect(normalizeRelaxedSearch("التربية")).toBe("التربيه");
    expect(normalizeRelaxedSearch("تربيه")).toBe("تربيه");
  });

  it("strips Arabic definite article 'ال' when word has sufficient length", () => {
    expect(stripArabicArticle("الوطنية")).toBe("وطنية");
    expect(stripArabicArticle("الذكاء")).toBe("ذكاء");
    expect(stripArabicArticle("ال")).toBe("ال"); // Too short to strip
  });

  it("Priority 1: exact normalized match scores higher than prefix match", () => {
    const exact = scoreCourseMatch(sampleCourses[0], "التربية الوطنية", "ar");
    const prefix = scoreCourseMatch(sampleCourses[0], "التربية", "ar");
    expect(exact).not.toBeNull();
    expect(prefix).not.toBeNull();
    expect(exact!.priorityTier).toBe(1);
    expect(prefix!.priorityTier).toBe(2);
    expect(exact!.score).toBeGreaterThan(prefix!.score);
  });

  it("Priority 2: name starting with query ranks before name with query in middle", () => {
    // "التربية" should rank "التربية الوطنية" (starts with) before "مناهج التربية" (word 2)
    const results = rankCourseSuggestions(sampleCourses, "التربية", "ar");
    expect(results.length).toBeGreaterThan(1);
    expect(results[0].course_code).toBe("1501110"); // التربية الوطنية
    expect(results[1].course_code).toBe("1501111"); // التربية الإسلامية
    const curriculaIndex = results.findIndex(c => c.course_code === "1501340");
    expect(curriculaIndex).toBeGreaterThan(1);
  });

  it("Priority 3: matches words inside the course title with or without 'ال'", () => {
    // Typing "وطنية" should match "التربية الوطنية"
    const results = rankCourseSuggestions(sampleCourses, "وطنية", "ar");
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].name_ar).toBe("التربية الوطنية");
  });

  it("matches 'ذكاء' to 'الذكاء الاصطناعي'", () => {
    const results = rankCourseSuggestions(sampleCourses, "ذكاء", "ar");
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].name_ar).toBe("الذكاء الاصطناعي");
  });

  it("matches 'تعلم' and 'آلة' to 'تعلم الآلة'", () => {
    const res1 = rankCourseSuggestions(sampleCourses, "تعلم", "ar");
    expect(res1[0].name_ar).toBe("تعلم الآلة");

    const res2 = rankCourseSuggestions(sampleCourses, "آلة", "ar");
    expect(res2[0].name_ar).toBe("تعلم الآلة");

    // Also with alef without madda
    const res3 = rankCourseSuggestions(sampleCourses, "الة", "ar");
    expect(res3[0].name_ar).toBe("تعلم الآلة");
  });

  it("supports Teh-Marbuta / Heh dialect variation (تربيه matches التربية)", () => {
    const results = rankCourseSuggestions(sampleCourses, "تربيه", "ar");
    expect(results.length).toBeGreaterThan(0);
    expect(results.some(c => c.name_ar === "التربية الوطنية")).toBe(true);
    expect(results.some(c => c.name_ar === "التربية الإسلامية")).toBe(true);
  });

  it("Priority 5: matches course code as secondary convenience", () => {
    const results = rankCourseSuggestions(sampleCourses, "CS101", "ar");
    expect(results.length).toBe(1);
    expect(results[0].course_code).toBe("CS101");
    expect(results[0].name_ar).toBe("أساسيات الحاسوب");
  });

  it("supports English matching and case insensitivity", () => {
    const results = rankCourseSuggestions(sampleCourses, "machine", "en");
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].name_en).toBe("Machine Learning");
  });

  it("supports single-character search sensibly", () => {
    const arabicRes = rankCourseSuggestions(sampleCourses, "ت", "ar");
    expect(arabicRes.length).toBeGreaterThan(0);
    // "تعلم الآلة" or "تفاضل وتكامل 1" start with "ت"
    expect(arabicRes[0].name_ar).toMatch(/^ت/);

    const engRes = rankCourseSuggestions(sampleCourses, "C", "en");
    expect(engRes.length).toBeGreaterThan(0);
    expect(engRes[0].name_en).toMatch(/^C/i);
  });

  it("boosts courses offered this semester when relevance score is otherwise equal", () => {
    const offered = new Set(["1501111"]); // Islamic Education is offered
    const results = rankCourseSuggestions(sampleCourses, "التربية", "ar", offered);
    // Both start with "التربية" (Tier 2), but Islamic Education is offered
    expect(results[0].course_code).toBe("1501111");
  });

  it("deduplicates multiple entries with the same course code", () => {
    const duplicated: CourseDisplayIdentity[] = [
      ...sampleCourses,
      { course_id: "c1-dup", course_code: "1501110", name_ar: "التربية الوطنية", name_en: "National Education" },
    ];
    const results = rankCourseSuggestions(duplicated, "التربية", "ar");
    const count = results.filter(c => c.course_code === "1501110").length;
    expect(count).toBe(1);
  });

  it("matches course by institutional alias or search synonym", () => {
    const withAliases: CourseDisplayIdentity[] = [
      {
        course_id: "c1",
        course_code: "0100101",
        name_ar: "التربية الوطنية",
        name_en: "National Education",
        aliases: ["المواطنة", "التربية المدنية"],
      },
      {
        course_id: "c2",
        course_code: "1501110",
        name_ar: "أساسيات البرمجة",
        name_en: "Programming Fundamentals",
        aliases: ["مقدمة في البرمجة"],
      },
    ];
    // Student searches for "المواطنة" and matches "التربية الوطنية"
    const citizenResults = rankCourseSuggestions(withAliases, "المواطنة", "ar");
    expect(citizenResults.length).toBeGreaterThan(0);
    expect(citizenResults[0].course_code).toBe("0100101");
    expect(citizenResults[0].name_ar).toBe("التربية الوطنية");

    // Student searches for "مقدمة" and matches "أساسيات البرمجة"
    const introResults = rankCourseSuggestions(withAliases, "مقدمة", "ar");
    expect(introResults.length).toBeGreaterThan(0);
    expect(introResults[0].course_code).toBe("1501110");
  });

  it("returns empty list for blank or unmatched query", () => {
    expect(rankCourseSuggestions(sampleCourses, "")).toEqual([]);
    expect(rankCourseSuggestions(sampleCourses, "   ")).toEqual([]);
    expect(rankCourseSuggestions(sampleCourses, "فلك وكواكب غير موجود")).toEqual([]);
  });
});

