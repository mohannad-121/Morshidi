"use client";

import { useEffect, useMemo, useState } from "react";
import {
  BookOpenCheck,
  Brain,
  Code2,
  Download,
  FileEdit,
  FileText,
  FolderOpen,
  GraduationCap,
  Presentation,
  Search,
  X,
} from "lucide-react";
import type { ChapterFile, DiscoveredCourse } from "@/lib/chapters/discovery";
import { PageHeader } from "@/components/ui/DesignSystem";

function getCourseIcon(slug: string, name: string) {
  const text = (slug + " " + name).toLowerCase();
  if (text.includes("machine") || text.includes("ذكاء") || text.includes("آلة") || text.includes("learning")) {
    return <Brain className="h-6 w-6 text-[var(--gold-primary)]" />;
  }
  if (text.includes("programming") || text.includes("برمجة") || text.includes("code") || text.includes("حاسوب")) {
    return <Code2 className="h-6 w-6 text-[var(--gold-primary)]" />;
  }
  return <GraduationCap className="h-6 w-6 text-[var(--gold-primary)]" />;
}

function getFileIcon(fileType: ChapterFile["fileType"]) {
  switch (fileType) {
    case "PowerPoint":
      return <Presentation className="h-5 w-5 text-amber-400 shrink-0" />;
    case "PDF":
      return <FileText className="h-5 w-5 text-rose-400 shrink-0" />;
    case "Word":
      return <FileEdit className="h-5 w-5 text-blue-400 shrink-0" />;
    default:
      return <FileText className="h-5 w-5 text-[var(--gold-primary)] shrink-0" />;
  }
}

function formatFileCount(count: number): string {
  if (count === 0) return "لا توجد ملفات";
  if (count === 1) return "ملف واحد";
  if (count === 2) return "ملفان";
  if (count >= 3 && count <= 10) return `${count} ملفات`;
  return `${count} ملفاً`;
}

interface ChaptersClientProps {
  initialCourses: DiscoveredCourse[];
}

export function ChaptersClient({ initialCourses }: ChaptersClientProps) {
  const [courses] = useState<DiscoveredCourse[]>(initialCourses);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCourse, setSelectedCourse] = useState<DiscoveredCourse | null>(null);

  // Close modal on Escape key
  useEffect(() => {
    if (!selectedCourse) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedCourse(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedCourse]);

  const filteredCourses = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return courses;
    return courses.filter(
      (course) =>
        course.name.toLowerCase().includes(q) ||
        course.slug.toLowerCase().includes(q)
    );
  }, [courses, searchQuery]);

  return (
    <div className="space-y-8" dir="rtl">
      <PageHeader
        eyebrow="المصادر الأكاديمية"
        title="شباتر المواد"
        description="استعراض وتحميل شباتر ومحاضرات المواد الدراسية المتاحة."
      />

      {/* Search Bar */}
      {courses.length > 0 && (
        <div className="relative max-w-md">
          <Search
            size={18}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted pointer-events-none"
          />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="ابحث عن مادة..."
            aria-label="البحث عن مادة"
            className="w-full rounded-xl border border-border bg-surface py-2.5 pr-10 pl-4 text-sm text-foreground focus-visible:outline-2 focus-visible:outline-accent"
          />
        </div>
      )}

      {/* Empty State: No Courses at all */}
      {courses.length === 0 && (
        <div className="empty-state flex flex-col items-center justify-center rounded-2xl border border-dashed border-border-strong p-10 text-center sm:p-14">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-soft text-accent">
            <FolderOpen size={32} />
          </div>
          <h2 className="text-lg font-bold text-foreground sm:text-xl">
            لا توجد شباتر متاحة حالياً
          </h2>
          <p className="mt-2 max-w-md text-xs leading-relaxed text-muted sm:text-sm">
            لم تتم إضافة ملفات أو مقررات دراسية حتى الآن. يُرجى مراجعة المرشد الأكاديمي أو المحاضر.
          </p>
        </div>
      )}

      {/* Empty State: Search yielded no matches */}
      {courses.length > 0 && filteredCourses.length === 0 && (
        <div className="empty-state flex flex-col items-center justify-center rounded-2xl border border-dashed border-border p-8 text-center sm:p-12">
          <h3 className="text-base font-bold text-foreground sm:text-lg">
            لا توجد مواد مطابقة لبحثك
          </h3>
          <p className="mt-2 text-xs text-muted sm:text-sm">
            جرّب البحث باسم مادة مختلف أو مسح حقل البحث.
          </p>
          <button
            type="button"
            onClick={() => setSearchQuery("")}
            className="button-secondary mt-4 text-xs"
          >
            مسح البحث
          </button>
        </div>
      )}

      {/* Course Cards Grid */}
      {filteredCourses.length > 0 && (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {filteredCourses.map((course) => {
            const fileCount = course.files.length;
            return (
              <article
                key={course.slug}
                className="engraved surface-base flex flex-col justify-between rounded-2xl p-6 transition-all duration-200 hover:border-border-strong"
              >
                <div>
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-border bg-accent-soft">
                      {getCourseIcon(course.slug, course.name)}
                    </div>
                    <span className="badge badge-gold rounded-full px-3 py-1 font-mono text-xs">
                      {formatFileCount(fileCount)}
                    </span>
                  </div>

                  <h2 className="mt-4 text-lg font-bold leading-snug text-foreground">
                    {course.name}
                  </h2>
                </div>

                <div className="mt-6 pt-4 border-t border-border">
                  <button
                    type="button"
                    onClick={() => setSelectedCourse(course)}
                    className="button-primary w-full text-xs font-semibold"
                    aria-label={`عرض الشباتر لمادة ${course.name}`}
                  >
                    <BookOpenCheck size={16} />
                    <span>عرض الشباتر</span>
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* Selected Course Chapters Modal/Sheet */}
      {selectedCourse && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="course-chapters-title"
          onClick={() => setSelectedCourse(null)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 backdrop-blur-xs sm:p-4"
        >
          <div
            onClick={(event) => event.stopPropagation()}
            className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border-strong bg-surface shadow-2xl"
          >
            {/* Modal Header */}
            <header className="flex items-start justify-between gap-4 border-b border-border p-5">
              <div className="min-w-0">
                <span className="badge badge-gold rounded-full px-2.5 py-0.5 font-mono text-[11px]">
                  {formatFileCount(selectedCourse.files.length)}
                </span>
                <h2
                  id="course-chapters-title"
                  className="mt-2 break-words text-lg font-bold text-foreground sm:text-xl"
                >
                  {selectedCourse.name}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setSelectedCourse(null)}
                aria-label="إغلاق تفاصيل المادة"
                className="icon-button shrink-0"
              >
                <X size={18} />
              </button>
            </header>

            {/* Modal Content */}
            <div className="flex-1 space-y-3 overflow-y-auto p-4 sm:p-6">
              {selectedCourse.files.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border p-8 text-center">
                  <FolderOpen size={36} className="mx-auto text-muted" />
                  <p className="mt-3 text-sm text-muted">
                    لم تتم إضافة ملفات لهذه المادة بعد
                  </p>
                </div>
              ) : (
                selectedCourse.files.map((file) => (
                  <article
                    key={file.filename}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-border bg-surface-muted p-4 transition-colors hover:border-border-strong"
                  >
                    <div className="flex items-center gap-3.5 min-w-0">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-surface">
                        {getFileIcon(file.fileType)}
                      </div>
                      <div className="min-w-0">
                        <h3
                          className="text-sm font-bold text-foreground break-words"
                          dir="auto"
                        >
                          {file.displayName}
                        </h3>
                        <p className="mt-0.5 text-xs text-muted">
                          {file.fileType}
                        </p>
                      </div>
                    </div>

                    <a
                      href={file.downloadUrl}
                      download={file.filename}
                      className="button-primary min-h-[44px] shrink-0 text-xs px-4 py-2 font-semibold"
                      aria-label={`تحميل ${file.displayName}`}
                    >
                      <Download size={14} />
                      <span>تحميل</span>
                    </a>
                  </article>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
