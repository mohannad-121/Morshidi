import { BookOpenCheck, GitCompareArrows, GraduationCap, Route, Scale } from "lucide-react";

import type { AdvisorResponse } from "@/lib/api/student-types";
import { label } from "@/lib/labels";

type UnknownRecord = Record<string, unknown>;

function record(value: unknown): UnknownRecord | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as UnknownRecord
    : null;
}

function rows(value: unknown): UnknownRecord[] {
  return Array.isArray(value) ? value.map(record).filter((item): item is UnknownRecord => item !== null) : [];
}

function text(value: unknown): string | null {
  return typeof value === "string" || typeof value === "number" ? String(value) : null;
}

function courseName(course: UnknownRecord): string {
  return text(course.course_name_ar) ?? text(course.canonical_arabic_name) ??
    text(course.course_name_en) ?? text(course.course_code) ?? "مساق";
}

function Metric({ value, title }: { value: string | null; title: string }) {
  if (value === null) return null;
  return <div className="advisor-result-metric"><strong>{value}</strong><span>{title}</span></div>;
}

export function AdvisorResultCard({ response }: { response: AdvisorResponse }) {
  const result = record(response.result);
  if (!result) return null;
  const kind = text(result.kind);

  if (kind === "progress") {
    return <section className="advisor-result-card" aria-label="ملخص التقدم الأكاديمي">
      <header><GraduationCap aria-hidden="true" size={18}/><h3>ملخص التقدم الموثق</h3></header>
      <div className="advisor-result-metrics">
        <Metric value={text(result.completed_plan_credits)} title="ساعة مكتملة"/>
        <Metric value={text(result.in_progress_plan_credits)} title="قيد الدراسة"/>
        <Metric value={text(result.remaining_plan_credits)} title="ساعة متبقية"/>
      </div>
    </section>;
  }

  if (kind === "eligibility") {
    return <section className="advisor-result-card" aria-label="نتيجة أهلية المساق">
      <header><Scale aria-hidden="true" size={18}/><h3>قرار محرك الأهلية</h3></header>
      <div className="advisor-result-line">
        <strong>{label(text(result.decision) ?? "") || text(result.decision)}</strong>
        {text(result.target_course_code) && <span dir="ltr">{text(result.target_course_code)}</span>}
      </div>
    </section>;
  }

  if (kind === "recommendations") {
    const courses = rows(result.ranked_courses).slice(0, 4);
    if (!courses.length) return null;
    return <section className="advisor-result-card" aria-label="المساقات الموصى بها">
      <header><BookOpenCheck aria-hidden="true" size={18}/><h3>أعلى الترشيحات المؤهلة</h3></header>
      <ol className="advisor-result-courses">
        {courses.map((course, index) => <li key={text(course.course_code) ?? index}>
          <span>{courseName(course)}</span><b dir="ltr">{text(course.course_code)}</b>
        </li>)}
      </ol>
    </section>;
  }

  if (kind === "semester_plans") {
    const first = rows(result.options)[0];
    if (!first) return null;
    const courses = rows(first.courses);
    return <section className="advisor-result-card" aria-label="أفضل خيار للفصل">
      <header><Route aria-hidden="true" size={18}/><h3>الخيار الأول للفصل</h3></header>
      <div className="advisor-result-line"><span>{courses.length} مساقات</span><strong>{text(first.total_credit_hours)} ساعة</strong></div>
      <p>{courses.map(courseName).join(" · ")}</p>
    </section>;
  }

  if (kind === "degree_paths") {
    const first = rows(result.paths)[0];
    if (!first) return null;
    return <section className="advisor-result-card" aria-label="أفضل مسار تخرج نمذجي">
      <header><Route aria-hidden="true" size={18}/><h3>المسار النمذجي الأول</h3></header>
      <div className="advisor-result-line"><span>{rows(first.semesters).length} فصول</span><strong>{label(text(first.status) ?? "") || text(first.status)}</strong></div>
    </section>;
  }

  if (kind === "course_information") {
    return <section className="advisor-result-card" aria-label="بطاقة معلومات المساق">
      <header><BookOpenCheck aria-hidden="true" size={18}/><h3>{courseName(result)}</h3></header>
      <div className="advisor-result-line"><span dir="ltr">{text(result.course_code)}</span>{text(result.credit_hours) && <strong>{text(result.credit_hours)} ساعات</strong>}</div>
    </section>;
  }

  if (kind === "course_comparison") {
    const courses = rows(result.courses).slice(0, 2);
    if (!courses.length) return null;
    return <section className="advisor-result-card" aria-label="مقارنة المساقات">
      <header><GitCompareArrows aria-hidden="true" size={18}/><h3>مقارنة موثقة</h3></header>
      <div className="advisor-comparison-grid">{courses.map((course, index) => <div key={text(course.course_code) ?? index}>
        <strong>{courseName(course)}</strong><span dir="ltr">{text(course.course_code)}</span>
      </div>)}</div>
    </section>;
  }

  return null;
}
