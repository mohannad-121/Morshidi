import type { User } from "@supabase/supabase-js";

export const GENERIC_STUDENT_NAME = "طالب مرشدي";

export function getStudentDisplayName(user: User | null | undefined): string {
  const value = user?.user_metadata?.full_name;
  if (typeof value !== "string") return GENERIC_STUDENT_NAME;

  const normalized = value.replace(/\s+/g, " ").trim();
  if (!normalized || normalized.includes("@")) return GENERIC_STUDENT_NAME;
  return normalized;
}

export function getStudentInitial(user: User | null | undefined): string {
  return Array.from(getStudentDisplayName(user))[0] ?? "م";
}

export function getArabicGreeting(date = new Date()): "صباح الخير" | "مساء الخير" {
  const hour = date.getHours();
  return hour >= 5 && hour < 12 ? "صباح الخير" : "مساء الخير";
}
