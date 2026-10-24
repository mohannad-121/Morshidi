"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { BookOpenCheck, Download, FileText, FolderOpen, Search, X } from "lucide-react";
import { PageHeader } from "@/components/ui/DesignSystem";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import {
  LearningMaterialsApi,
  type LearningMaterialCourseView,
  type LearningMaterialLibraryView,
  type LearningMaterialView,
} from "@/lib/api/learning-materials";

interface ChaptersClientProps {
  initialLibrary?: LearningMaterialLibraryView;
}

function courseName(course: LearningMaterialCourseView): string {
  return course.course_name_ar ?? course.course_name_en ?? course.course_code;
}

function normalizeArabic(value: string): string {
  return value.normalize("NFKD")
    .replace(/[\u064B-\u065F\u0670]/g, "")
    .replace(/[أإآ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .toLocaleLowerCase();
}

function formatCount(count: number): string {
  if (count === 1) return "ملف واحد";
  if (count === 2) return "ملفان";
  if (count >= 3 && count <= 10) return `${count} ملفات`;
  return `${count} ملفاً`;
}

function fileType(material: LearningMaterialView): string {
  if (material.mime_type === "application/pdf") return "PDF";
  if (material.mime_type.includes("presentation") || material.mime_type.includes("powerpoint")) return "PowerPoint";
  return "Word";
}

export function ChaptersClient({ initialLibrary }: ChaptersClientProps) {
  const client = useAuthenticatedApi();
  const api = useMemo(() => new LearningMaterialsApi(client), [client]);
  const [library, setLibrary] = useState<LearningMaterialLibraryView | null>(initialLibrary ?? null);
  const [loading, setLoading] = useState(!initialLibrary);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<LearningMaterialCourseView | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const closeButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (initialLibrary) return;
    let active = true;
    void api.list().then((value) => {
      if (active) setLibrary(value);
    }).catch(() => {
      if (active) setError(true);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [api, initialLibrary]);

  useEffect(() => {
    if (!selected) return;
    closeButton.current?.focus();
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelected(null);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [selected]);

  const courses = useMemo(() => library?.courses ?? [], [library]);
  const filtered = useMemo(() => {
    const needle = normalizeArabic(query.trim());
    if (!needle) return courses;
    return courses.filter((course) => normalizeArabic([
      course.course_name_ar, course.course_name_en, course.course_code,
    ].filter(Boolean).join(" ")).includes(needle));
  }, [courses, query]);

  async function download(material: LearningMaterialView) {
    setDownloading(material.material_id);
    setError(false);
    try {
      await api.download(material);
    } catch {
      setError(true);
    } finally {
      setDownloading(null);
    }
  }

  return <div className="space-y-8" dir="rtl">
    <PageHeader eyebrow="المصادر الأكاديمية المصرّح بها" title="شبّاتِر المواد"
      description="المواد المعتمدة لخطة دراستك الحالية فقط. قد تختلف الإصدارات بين الخطط والجامعات." />

    {loading && <div role="status" className="surface-base rounded-2xl p-6 text-muted">جارٍ تحميل المواد المصرّح بها…</div>}
    {error && <div role="alert" className="rounded-2xl border border-danger/40 bg-danger/10 p-4">
      تعذّر تحميل المواد الآن. لا يعني ذلك عدم توفرها لدى الجامعة.
    </div>}

    {!loading && courses.length > 0 && <label className="relative block max-w-md">
      <span className="sr-only">البحث عن مادة</span>
      <Search aria-hidden="true" className="pointer-events-none absolute right-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" />
      <input type="search" value={query} onChange={(event) => setQuery(event.target.value)}
        placeholder="ابحث باسم المادة أو رمزها…"
        className="min-h-11 w-full rounded-xl border border-border bg-surface py-2.5 pr-11 pl-4 text-sm focus-visible:outline-2 focus-visible:outline-accent" />
    </label>}

    {!loading && !error && courses.length === 0 && <section className="empty-state rounded-2xl border border-dashed border-border-strong p-10 text-center">
      <FolderOpen aria-hidden="true" className="mx-auto h-12 w-12 text-accent" />
      <h2 className="mt-4 text-lg font-bold">لا تتوفر شبّاتِر لهذه الخطة الدراسية حالياً</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm text-muted">ستظهر المواد هنا تلقائياً عندما تعتمدها الجامعة لخطة دراستك وإصدار المنهاج الحالي.</p>
    </section>}

    {courses.length > 0 && filtered.length === 0 && <section className="empty-state rounded-2xl border border-dashed border-border p-8 text-center">
      <h2 className="font-bold">لا توجد مواد مطابقة لبحثك</h2>
      <button type="button" className="button-secondary mt-4" onClick={() => setQuery("")}>مسح البحث</button>
    </section>}

    {filtered.length > 0 && <section className="grid gap-5 md:grid-cols-2 lg:grid-cols-3" aria-label="المواد المصرّح بها">
      {filtered.map((course) => <article key={course.course_id} className="engraved surface-base flex flex-col rounded-2xl p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-border bg-accent-soft">
            <BookOpenCheck aria-hidden="true" className="h-6 w-6 text-accent" />
          </div>
          <span className="badge badge-gold rounded-full px-3 py-1 text-xs">{formatCount(course.materials.length)}</span>
        </div>
        <h2 className="mt-4 text-lg font-bold">{courseName(course)}</h2>
        <p className="mt-1 font-mono text-xs text-muted" dir="ltr">{course.course_code}</p>
        <button type="button" onClick={() => setSelected(course)} className="button-primary mt-6 min-h-11 w-full">عرض المواد</button>
      </article>)}
    </section>}

    {selected && <div role="dialog" aria-modal="true" aria-labelledby="materials-dialog-title"
      onMouseDown={(event) => { if (event.target === event.currentTarget) setSelected(null); }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-3 backdrop-blur-sm">
      <section className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border-strong bg-surface shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-border p-5">
          <div><h2 id="materials-dialog-title" className="text-xl font-bold">{courseName(selected)}</h2>
            <p className="mt-1 font-mono text-xs text-muted" dir="ltr">{selected.course_code}</p></div>
          <button ref={closeButton} type="button" className="icon-button min-h-11 min-w-11" aria-label="إغلاق" onClick={() => setSelected(null)}>
            <X aria-hidden="true" />
          </button>
        </header>
        <div className="space-y-3 overflow-y-auto p-4 sm:p-6">
          {selected.materials.map((material) => <article key={material.material_id} className="flex flex-col gap-4 rounded-xl border border-border bg-surface-muted p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-center gap-3"><FileText aria-hidden="true" className="h-6 w-6 shrink-0 text-accent" />
              <div className="min-w-0"><h3 className="break-words font-bold">{material.title_ar}</h3>
                <p className="mt-1 text-xs text-muted">{fileType(material)} · {material.version_label}</p></div></div>
            <button type="button" disabled={downloading === material.material_id} onClick={() => void download(material)}
              className="button-secondary min-h-11 shrink-0 disabled:opacity-50" aria-label={`تحميل ${material.title_ar}`}>
              <Download aria-hidden="true" className="h-4 w-4" />
              {downloading === material.material_id ? "جارٍ التحميل…" : "تحميل"}
            </button>
          </article>)}
        </div>
      </section>
    </div>}
  </div>;
}
