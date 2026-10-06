import type { Metadata } from "next";
import { getDiscoveredCourses } from "@/lib/chapters/discovery";
import { ChaptersClient } from "./ChaptersClient";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "شباتر المواد | مرشدي",
  description: "استعراض وتحميل شباتر ومحاضرات المواد الدراسية المتاحة.",
};

export default async function ChaptersPage() {
  const courses = await getDiscoveredCourses();
  return <ChaptersClient initialCourses={courses} />;
}
