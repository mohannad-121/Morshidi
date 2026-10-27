import type { CourseDisplayIdentity } from "@/lib/api/use-course-identities";

/**
 * Strict Arabic normalization preserving ة vs ه distinction.
 * Strips tashkeel diacritics, tatweel/kashida, unifies alef forms and alif maqsura,
 * and collapses whitespace.
 */
export function normalizeCourseSearch(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/[\u064B-\u065F\u0670\u06D6-\u06ED]/g, "") // Diacritics
    .replace(/[\u0640ـ]/g, "") // Tatweel / Kashida
    .replace(/[أإآٱ]/g, "ا") // Alef forms
    .replace(/ى/g, "ي") // Alif Maqsura
    .toLocaleLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Relaxed Arabic normalization mapping ة to ه,
 * supporting dialect and colloquial typing.
 */
export function normalizeRelaxedSearch(value: string): string {
  return normalizeCourseSearch(value).replace(/ة/g, "ه");
}

/**
 * Strip leading Arabic definite article 'ال' if the remaining stem has at least 2 characters.
 */
export function stripArabicArticle(word: string): string {
  if (word.startsWith("ال") && word.length > 3) {
    return word.slice(2);
  }
  return word;
}

export interface CourseMatch {
  identity: CourseDisplayIdentity;
  score: number;
  priorityTier: 1 | 2 | 3 | 4 | 5;
  isOffered: boolean;
}

interface FieldMatch {
  score: number;
  tier: 1 | 2 | 3 | 4 | 0;
}

function scoreTextField(
  text: string | null | undefined,
  normQuery: string,
  relaxedQuery: string,
  qStem: string,
  relaxedQStem: string,
): FieldMatch {
  if (!text) return { score: 0, tier: 0 };

  const normText = normalizeCourseSearch(text);
  const relaxedText = normalizeRelaxedSearch(text);
  if (!normText) return { score: 0, tier: 0 };

  // Priority 1: Exact normalized match
  if (normText === normQuery || relaxedText === relaxedQuery) {
    return { score: 10000, tier: 1 };
  }
  const normTextStem = stripArabicArticle(normText);
  const relaxedTextStem = stripArabicArticle(relaxedText);
  if (normTextStem === qStem || relaxedTextStem === relaxedQStem) {
    return { score: 9500, tier: 1 };
  }

  // Priority 2: Course name starts with query
  if (normText.startsWith(normQuery) || relaxedText.startsWith(relaxedQuery)) {
    return { score: 8000 + (100 / (normText.length + 1)), tier: 2 };
  }
  if (normTextStem.startsWith(qStem) || relaxedTextStem.startsWith(relaxedQStem)) {
    return { score: 7800 + (100 / (normText.length + 1)), tier: 2 };
  }

  // Priority 3: A word in the course name starts with query
  const words = normText.split(" ");
  const relWords = relaxedText.split(" ");
  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    const rw = relWords[i] ?? w;
    const wStem = stripArabicArticle(w);
    const rwStem = stripArabicArticle(rw);

    if (
      w.startsWith(normQuery) ||
      rw.startsWith(relaxedQuery) ||
      wStem.startsWith(qStem) ||
      rwStem.startsWith(relaxedQStem)
    ) {
      const wordPenalty = Math.min(i * 50, 200);
      return { score: 6000 - wordPenalty + (10 / (w.length + 1)), tier: 3 };
    }
  }

  // Priority 4: Other partial substring matches in the course name
  if (normText.includes(normQuery) || relaxedText.includes(relaxedQuery)) {
    return { score: 4000 + (100 / (normText.length + 1)), tier: 4 };
  }
  if (relaxedText.includes(relaxedQStem) || normText.includes(qStem)) {
    return { score: 3800 + (100 / (normText.length + 1)), tier: 4 };
  }

  return { score: 0, tier: 0 };
}

function scoreCourseCode(
  courseCode: string,
  normQuery: string,
): { score: number; tier: 5 | 0 } {
  const normCode = normalizeCourseSearch(courseCode);
  if (!normCode) return { score: 0, tier: 0 };

  if (normCode === normQuery) {
    return { score: 3500, tier: 5 };
  }
  if (normCode.startsWith(normQuery)) {
    return { score: 3000 + (50 / (normCode.length + 1)), tier: 5 };
  }
  if (normCode.includes(normQuery)) {
    return { score: 2000, tier: 5 };
  }

  return { score: 0, tier: 0 };
}

export function scoreCourseMatch(
  row: CourseDisplayIdentity,
  query: string,
  locale: "ar" | "en" = "ar",
  isOffered = false,
): CourseMatch | null {
  const normQ = normalizeCourseSearch(query);
  if (!normQ) return null;

  const relaxedQ = normalizeRelaxedSearch(query);
  const qStem = stripArabicArticle(normQ);
  const relaxedQStem = stripArabicArticle(relaxedQ);

  const primaryName = locale === "ar" ? row.name_ar : row.name_en;
  const secondaryName = locale === "ar" ? row.name_en : row.name_ar;

  const primaryResult = scoreTextField(primaryName, normQ, relaxedQ, qStem, relaxedQStem);
  const secondaryResult = scoreTextField(secondaryName, normQ, relaxedQ, qStem, relaxedQStem);
  const codeResult = scoreCourseCode(row.course_code, normQ);

  let bestScore = 0;
  let bestTier: 1 | 2 | 3 | 4 | 5 = 5;

  if (primaryResult.score > 0) {
    bestScore = primaryResult.score;
    bestTier = primaryResult.tier as 1 | 2 | 3 | 4;
  }

  if (secondaryResult.score > 0) {
    const adjustedSecondary = secondaryResult.score * 0.95;
    if (adjustedSecondary > bestScore) {
      bestScore = adjustedSecondary;
      bestTier = secondaryResult.tier as 1 | 2 | 3 | 4;
    }
  }

  if (codeResult.score > 0 && codeResult.score > bestScore) {
    bestScore = codeResult.score;
    bestTier = 5;
  }

  if (row.aliases && row.aliases.length > 0) {
    for (const alias of row.aliases) {
      const aliasResult = scoreTextField(alias, normQ, relaxedQ, qStem, relaxedQStem);
      if (aliasResult.score > 0) {
        const adjustedAlias = aliasResult.score * 0.96;
        if (adjustedAlias > bestScore) {
          bestScore = adjustedAlias;
          bestTier = aliasResult.tier as 1 | 2 | 3 | 4;
        }
      }
    }
  }

  if (bestScore <= 0) return null;

  // Boost courses currently offered in this semester
  if (isOffered) {
    bestScore += 25;
  }

  return {
    identity: row,
    score: bestScore,
    priorityTier: bestTier,
    isOffered,
  };
}

export function rankCourseSuggestions(
  rows: CourseDisplayIdentity[],
  query: string,
  locale: "ar" | "en" = "ar",
  offeredCourseCodes?: Set<string>,
  limit = 12,
): CourseDisplayIdentity[] {
  const trimmed = query.trim();
  if (!trimmed) return [];

  const matches: CourseMatch[] = [];
  const seenCodes = new Set<string>();

  for (const row of rows) {
    if (!row.course_code || seenCodes.has(row.course_code)) continue;
    seenCodes.add(row.course_code);

    const isOffered = offeredCourseCodes ? offeredCourseCodes.has(row.course_code) : false;
    const match = scoreCourseMatch(row, trimmed, locale, isOffered);
    if (match) {
      matches.push(match);
    }
  }

  matches.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return a.identity.course_code.localeCompare(b.identity.course_code);
  });

  return matches.slice(0, limit).map(m => m.identity);
}

