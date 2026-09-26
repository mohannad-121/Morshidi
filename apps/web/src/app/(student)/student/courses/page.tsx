"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/auth/auth-provider";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type {
  AttemptCreateRequest,
  AttemptOutcome,
  AttemptUpdateRequest,
  CourseAttemptResponse,
  DashboardError,
  RecordSource,
} from "@/lib/api/student-types";
import { Badge, type BadgeVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert, isRetryableError } from "@/components/ui/ErrorAlert";
import { LoadingSkeletonCard } from "@/components/ui/LoadingSkeleton";
import { StatCard } from "@/components/ui/StatCard";
import {
  CheckCircleIcon,
  CloseIcon,
  CoursesIcon,
  EditIcon,
  PlusIcon,
  SearchIcon,
  TrashIcon,
} from "@/components/ui/Icons";

function getStatusDetails(status: AttemptOutcome): { label: string; variant: BadgeVariant } {
  switch (status) {
    case "PASSED":
      return { label: "ناجح / مستوفى", variant: "success" };
    case "IN_PROGRESS":
      return { label: "قيد الدراسة", variant: "gold" };
    case "FAILED":
      return { label: "غير مجتاز", variant: "error" };
    case "WITHDRAWN":
      return { label: "منسحب رسمياً", variant: "warning" };
    default:
      return { label: status, variant: "neutral" };
  }
}

function getSourceLabel(source: RecordSource): string {
  switch (source) {
    case "university_integration":
      return "ربط جامعي رسمي";
    case "transcript_import":
      return "استيراد كشف علامات";
    case "admin_correction":
      return "تدقيق وتصحيح إداري";
    case "manual_entry":
    default:
      return "إدخال يدوي";
  }
}

export default function CoursesPage() {
  const auth = useAuth();
  const client = useAuthenticatedApi();
  const [attempts, setAttempts] = useState<CourseAttemptResponse[]>([]);
  const [error, setError] = useState<DashboardError | null>(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>("ALL");

  // Modal states
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingAttempt, setEditingAttempt] = useState<CourseAttemptResponse | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Form states for Add / Edit
  const [formCourseCode, setFormCourseCode] = useState("");
  const [formTermLabel, setFormTermLabel] = useState("");
  const [formStatus, setFormStatus] = useState<AttemptOutcome>("PASSED");
  const [formGrade, setFormGrade] = useState("");
  const [formSource, setFormSource] = useState<RecordSource>("manual_entry");

  const fetchAttempts = async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new StudentApiService(client);
      const data = await api.listAttempts();
      setAttempts(data);
    } catch {
      setError("SERVER_ERROR");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (auth.isAuthenticated) {
      void fetchAttempts();
    }
  }, [auth.isAuthenticated]);

  const openAddModal = () => {
    setFormCourseCode("");
    setFormTermLabel("2024-1");
    setFormStatus("PASSED");
    setFormGrade("");
    setFormSource("manual_entry");
    setActionError(null);
    setIsAddModalOpen(true);
  };

  const openEditModal = (attempt: CourseAttemptResponse) => {
    setEditingAttempt(attempt);
    setFormStatus(attempt.status);
    setFormGrade(attempt.raw_grade_text ?? "");
    setFormTermLabel(attempt.term_label ?? "");
    setActionError(null);
  };

  const handleCreateAttempt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formCourseCode.trim()) {
      setActionError("يرجى إدخال رمز المادة.");
      return;
    }

    setActionLoading(true);
    setActionError(null);
    try {
      const api = new StudentApiService(client);
      const req: AttemptCreateRequest = {
        course_code: formCourseCode.trim().toUpperCase(),
        status: formStatus,
        term_label: formTermLabel.trim() || null,
        raw_grade_text: formGrade.trim() || null,
        record_source: formSource,
      };
      await api.createAttempt(req);
      setIsAddModalOpen(false);
      await fetchAttempts();
    } catch {
      setActionError("تعذر حفظ المحاولة. تأكد من صحة البيانات وعدم تكرار القيد.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdateAttempt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAttempt) return;

    setActionLoading(true);
    setActionError(null);
    try {
      const api = new StudentApiService(client);
      const req: AttemptUpdateRequest = {
        status: formStatus,
        term_label: formTermLabel.trim() || null,
        raw_grade_text: formGrade.trim() || null,
      };
      await api.updateAttempt(editingAttempt.id, req);
      setEditingAttempt(null);
      await fetchAttempts();
    } catch {
      setActionError("تعذر تحديث المحاولة. يرجى المحاولة لاحقاً.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteAttempt = async (id: string) => {
    if (!confirm("هل أنت متأكد من رغبتك في حذف هذا القيد؟")) return;
    setDeletingId(id);
    try {
      const api = new StudentApiService(client);
      await api.deleteAttempt(id);
      await fetchAttempts();
    } catch {
      alert("تعذر حذف المحاولة.");
    } finally {
      setDeletingId(null);
    }
  };

  // Stats calculation
  const stats = useMemo(() => {
    const total = attempts.length;
    const passed = attempts.filter((a) => a.status === "PASSED").length;
    const inProgress = attempts.filter((a) => a.status === "IN_PROGRESS").length;
    const notCompleted = attempts.filter((a) => a.status === "FAILED" || a.status === "WITHDRAWN").length;
    return { total, passed, inProgress, notCompleted };
  }, [attempts]);

  // Filtered list
  const filteredAttempts = useMemo(() => {
    return attempts.filter((attempt) => {
      const matchesStatus =
        selectedStatusFilter === "ALL" || attempt.status === selectedStatusFilter;
      const matchesSearch =
        searchQuery.trim() === "" ||
        attempt.course_code.toLowerCase().includes(searchQuery.trim().toLowerCase()) ||
        (attempt.term_label && attempt.term_label.toLowerCase().includes(searchQuery.trim().toLowerCase()));
      return matchesStatus && matchesSearch;
    });
  }, [attempts, selectedStatusFilter, searchQuery]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 border-b border-[#EDE2C5] pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-[#A66F00]/10 px-2.5 py-0.5 text-xs font-bold text-[#A66F00]">
              سجل المحاولات
            </span>
            <span className="text-xs text-[#726B5E]">السجل الأكاديمي</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#28241C]">
            المواد وسجل المحاولات
          </h1>
          <p className="text-xs text-[#726B5E]">
            استعراض وتوثيق كافة المحاولات الدراسية وحساب المتطلبات السابقة للمواد.
          </p>
        </div>

        <button
          type="button"
          onClick={openAddModal}
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#E2AD27] px-5 py-2.5 text-xs font-bold text-[#28241C] shadow-xs hover:bg-[#A66F00] hover:text-white transition-all focus:outline-hidden focus:ring-2 focus:ring-[#E2AD27]/50"
        >
          <PlusIcon className="h-4 w-4" />
          <span>إضافة محاولة دراسية</span>
        </button>
      </div>

      {/* Error State */}
      {error ? (
        <ErrorAlert
          error={error}
          onRetry={isRetryableError(error) ? fetchAttempts : undefined}
        />
      ) : null}

      {/* Loading Skeleton */}
      {loading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <LoadingSkeletonCard />
            <LoadingSkeletonCard />
            <LoadingSkeletonCard />
            <LoadingSkeletonCard />
          </div>
          <LoadingSkeletonCard />
        </div>
      ) : null}

      {/* Content */}
      {!loading && !error ? (
        <div className="space-y-6">
          {/* Summary Stat Cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard
              title="إجمالي المحاولات"
              value={stats.total}
              subtitle="سجل المحاولات التراكمي"
              icon={<CoursesIcon className="h-5 w-5" />}
            />
            <StatCard
              title="المواد المجتازة"
              value={stats.passed}
              subtitle="تم استيفاء متطلباتها بنجاح"
              icon={<CheckCircleIcon className="h-5 w-5" />}
            />
            <StatCard
              title="قيد الدراسة حالياً"
              value={stats.inProgress}
              subtitle="مسجلة في الفصل الجاري"
              icon={<CoursesIcon className="h-5 w-5" />}
            />
            <StatCard
              title="محاولات غير مكتملة"
              value={stats.notCompleted}
              subtitle="رسوب أو انسحاب رسمي"
              icon={<CoursesIcon className="h-5 w-5" />}
            />
          </div>

          {/* Search and Filters */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-1 rounded-2xl border border-[#EDE2C5] bg-[#FFF9E8] p-1 text-xs">
              {[
                { key: "ALL", label: "كافة المحاولات" },
                { key: "PASSED", label: "ناجح" },
                { key: "IN_PROGRESS", label: "قيد الدراسة" },
                { key: "FAILED", label: "راسب" },
                { key: "WITHDRAWN", label: "منسحب" },
              ].map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setSelectedStatusFilter(tab.key)}
                  className={`rounded-xl px-3 py-1.5 font-semibold transition-colors ${
                    selectedStatusFilter === tab.key
                      ? "bg-white text-[#805400] shadow-xs"
                      : "text-[#726B5E] hover:text-[#28241C]"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="relative min-w-[240px]">
              <SearchIcon className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#726B5E]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="بحث برمز المادة أو الفصل..."
                className="w-full rounded-2xl border border-[#EDE2C5] bg-white py-2 pr-11 pl-4 text-xs text-[#28241C] placeholder-[#726B5E]/60 focus:border-[#E2AD27] focus:outline-hidden focus:ring-2 focus:ring-[#E2AD27]/20"
              />
            </div>
          </div>

          {/* Attempts Table */}
          {filteredAttempts.length === 0 ? (
            <EmptyState
              title="لا توجد محاولات مسجلة"
              description="لم يتم العثور على أي محاولة دراسية مسجلة تطابق التصفية الحالية. يمكنك إضافة مادة جديدة من الزر أعلاه."
              action={
                <button
                  type="button"
                  onClick={openAddModal}
                  className="rounded-xl bg-[#E2AD27] px-4 py-2 text-xs font-bold text-[#28241C] hover:bg-[#A66F00] hover:text-white transition-colors"
                >
                  إضافة محاولة دراسية
                </button>
              }
            />
          ) : (
            <div className="overflow-hidden rounded-3xl border border-[#EDE2C5] bg-white shadow-xs">
              <div className="overflow-x-auto">
                <table className="w-full text-right text-xs">
                  <thead>
                    <tr className="border-b border-[#EDE2C5] bg-[#FFF9E8]/70 text-[#726B5E]">
                      <th className="px-6 py-4 font-bold">رمز المادة</th>
                      <th className="px-6 py-4 font-bold">الفصل الدراسي</th>
                      <th className="px-6 py-4 font-bold">العلامة</th>
                      <th className="px-6 py-4 font-bold">الحالة الأكاديمية</th>
                      <th className="px-6 py-4 font-bold">مصدر القيد</th>
                      <th className="px-6 py-4 font-bold text-center">الإجراءات</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EDE2C5]/50">
                    {filteredAttempts.map((attempt) => {
                      const statusDetails = getStatusDetails(attempt.status);
                      return (
                        <tr key={attempt.id} className="hover:bg-[#FFFDF7] transition-colors">
                          <td className="px-6 py-4 font-mono font-bold text-[#28241C]" dir="ltr">
                            {attempt.course_code}
                          </td>
                          <td className="px-6 py-4 font-mono text-[#726B5E]" dir="ltr">
                            {attempt.term_label ?? "—"}
                          </td>
                          <td className="px-6 py-4 font-mono font-bold text-[#28241C]">
                            {attempt.raw_grade_text ?? "—"}
                          </td>
                          <td className="px-6 py-4">
                            <Badge variant={statusDetails.variant}>
                              {statusDetails.label}
                            </Badge>
                          </td>
                          <td className="px-6 py-4 text-[#726B5E]">
                            <span className="rounded-md bg-[#FFF9E8] px-2 py-0.5 text-[10px] border border-[#EDE2C5]">
                              {getSourceLabel(attempt.record_source)}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-center">
                            <div className="flex items-center justify-center gap-2">
                              <button
                                type="button"
                                onClick={() => openEditModal(attempt)}
                                className="rounded-lg p-1.5 text-[#726B5E] hover:bg-[#FFF4C7] hover:text-[#805400] transition-colors"
                                title="تعديل المحاولة"
                              >
                                <EditIcon className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                onClick={() => void handleDeleteAttempt(attempt.id)}
                                disabled={deletingId === attempt.id}
                                className="rounded-lg p-1.5 text-stone-400 hover:bg-red-50 hover:text-red-700 transition-colors disabled:opacity-50"
                                title="حذف المحاولة"
                              >
                                <TrashIcon className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : null}

      {/* Add Modal */}
      {isAddModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-3xl border border-[#EDE2C5] bg-white p-7 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#EDE2C5] pb-4">
              <h2 className="text-base font-bold text-[#28241C]">إضافة محاولة دراسية جديدة</h2>
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="rounded-lg p-1 text-[#726B5E] hover:bg-[#FFF9E8]"
              >
                <CloseIcon className="h-5 w-5" />
              </button>
            </div>

            {actionError ? (
              <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800">
                {actionError}
              </div>
            ) : null}

            <form onSubmit={handleCreateAttempt} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block font-bold text-[#28241C] mb-1">
                  رمز المادة (Course Code) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="مثال: CS101 أو MATH101"
                  value={formCourseCode}
                  onChange={(e) => setFormCourseCode(e.target.value.toUpperCase())}
                  className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 font-mono uppercase text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
                  dir="ltr"
                />
              </div>

              <div>
                <label className="block font-bold text-[#28241C] mb-1">
                  الفصل الدراسي (Term Label)
                </label>
                <input
                  type="text"
                  placeholder="مثال: 2024-1 أو 2023-2"
                  value={formTermLabel}
                  onChange={(e) => setFormTermLabel(e.target.value)}
                  className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 font-mono text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
                  dir="ltr"
                />
              </div>

              <div>
                <label className="block font-bold text-[#28241C] mb-1">
                  الحالة الأكاديمية *
                </label>
                <select
                  value={formStatus}
                  onChange={(e) => setFormStatus(e.target.value as AttemptOutcome)}
                  className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
                >
                  <option value="PASSED">ناجح / مستوفى (PASSED)</option>
                  <option value="IN_PROGRESS">قيد الدراسة (IN_PROGRESS)</option>
                  <option value="FAILED">راسب (FAILED)</option>
                  <option value="WITHDRAWN">منسحب (WITHDRAWN)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#28241C] mb-1">
                  العلامة المسجلة (اختياري)
                </label>
                <input
                  type="text"
                  placeholder="مثال: A أو 85 أو Pass"
                  value={formGrade}
                  onChange={(e) => setFormGrade(e.target.value)}
                  className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 font-mono text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block font-bold text-[#28241C] mb-1">
                  مصدر القيد
                </label>
                <select
                  value={formSource}
                  onChange={(e) => setFormSource(e.target.value as RecordSource)}
                  className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
                >
                  <option value="manual_entry">إدخال يدوي للطالب</option>
                  <option value="transcript_import">استيراد كشف علامات</option>
                  <option value="university_integration">ربط جامعي</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-[#EDE2C5]">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="rounded-xl border border-[#EDE2C5] px-4 py-2 font-bold text-[#726B5E] hover:bg-[#FFF9E8]"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="rounded-xl bg-[#E2AD27] px-5 py-2 font-bold text-[#28241C] hover:bg-[#A66F00] hover:text-white transition-all disabled:opacity-50"
                >
                  {actionLoading ? "جاري الحفظ..." : "حفظ المحاولة"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {/* Edit Modal */}
      {editingAttempt ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-3xl border border-[#EDE2C5] bg-white p-7 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#EDE2C5] pb-4">
              <div>
                <h2 className="text-base font-bold text-[#28241C]">تعديل المحاولة الدراسية</h2>
                <p className="font-mono text-xs text-[#A66F00] font-bold" dir="ltr">
                  {editingAttempt.course_code} {editingAttempt.term_label ? `(${editingAttempt.term_label})` : ""}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setEditingAttempt(null)}
                className="rounded-lg p-1 text-[#726B5E] hover:bg-[#FFF9E8]"
              >
                <CloseIcon className="h-5 w-5" />
              </button>
            </div>

            {actionError ? (
              <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800">
                {actionError}
              </div>
            ) : null}

            <form onSubmit={handleUpdateAttempt} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block font-bold text-[#28241C] mb-1">
                  الفصل الدراسي (Term Label)
                </label>
                <input
                  type="text"
                  value={formTermLabel}
                  onChange={(e) => setFormTermLabel(e.target.value)}
                  className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 font-mono text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
                  dir="ltr"
                />
              </div>

              <div>
                <label className="block font-bold text-[#28241C] mb-1">
                  الحالة الأكاديمية *
                </label>
                <select
                  value={formStatus}
                  onChange={(e) => setFormStatus(e.target.value as AttemptOutcome)}
                  className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
                >
                  <option value="PASSED">ناجح / مستوفى (PASSED)</option>
                  <option value="IN_PROGRESS">قيد الدراسة (IN_PROGRESS)</option>
                  <option value="FAILED">راسب (FAILED)</option>
                  <option value="WITHDRAWN">منسحب (WITHDRAWN)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#28241C] mb-1">
                  العلامة المسجلة
                </label>
                <input
                  type="text"
                  placeholder="مثال: A أو 85 أو Pass"
                  value={formGrade}
                  onChange={(e) => setFormGrade(e.target.value)}
                  className="w-full rounded-xl border border-[#EDE2C5] bg-white p-2.5 font-mono text-[#28241C] focus:border-[#E2AD27] focus:outline-hidden"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-[#EDE2C5]">
                <button
                  type="button"
                  onClick={() => setEditingAttempt(null)}
                  className="rounded-xl border border-[#EDE2C5] px-4 py-2 font-bold text-[#726B5E] hover:bg-[#FFF9E8]"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="rounded-xl bg-[#E2AD27] px-5 py-2 font-bold text-[#28241C] hover:bg-[#A66F00] hover:text-white transition-all disabled:opacity-50"
                >
                  {actionLoading ? "جاري الحفظ..." : "تحديث المحاولة"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
