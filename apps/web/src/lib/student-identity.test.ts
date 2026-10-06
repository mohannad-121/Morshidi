import type { User } from "@supabase/supabase-js";
import { describe, expect, it } from "vitest";

import {
  GENERIC_STUDENT_NAME,
  getArabicGreeting,
  getStudentDisplayName,
  getStudentInitial,
} from "./student-identity";

function userWithMetadata(user_metadata: Record<string, unknown>, email = "202310001@shadow.morshidi.internal") {
  return { email, user_metadata } as User;
}

describe("student identity presentation", () => {
  it("uses the university-synchronized full name and derives its initial", () => {
    const user = userWithMetadata({ full_name: "  أحمد   محمد العلي  " });
    expect(getStudentDisplayName(user)).toBe("أحمد محمد العلي");
    expect(getStudentInitial(user)).toBe("أ");
  });

  it("never falls back to a shadow or public email", () => {
    expect(getStudentDisplayName(userWithMetadata({}))).toBe(GENERIC_STUDENT_NAME);
    expect(getStudentDisplayName(userWithMetadata({ full_name: "student@example.com" }))).toBe(
      GENERIC_STUDENT_NAME,
    );
  });

  it("uses the browser-local hour for simple morning and evening greetings", () => {
    expect(getArabicGreeting(new Date(2026, 9, 6, 5, 0))).toBe("صباح الخير");
    expect(getArabicGreeting(new Date(2026, 9, 6, 11, 59))).toBe("صباح الخير");
    expect(getArabicGreeting(new Date(2026, 9, 6, 12, 0))).toBe("مساء الخير");
    expect(getArabicGreeting(new Date(2026, 9, 6, 4, 59))).toBe("مساء الخير");
  });
});
