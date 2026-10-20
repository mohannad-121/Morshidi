"use client";

import Link from "next/link";
import { useEffect, useState, useMemo } from "react";
import {
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  Building2,
  CheckCircle2,
  Clock,
  Download,
  ExternalLink,
  FileSpreadsheet,
  FileText,
  Filter,
  Layers,
  Lock,
  Network,
  Plus,
  RefreshCw,
  Rocket,
  Search,
  ShieldAlert,
  ShieldCheck,
  Users,
  X,
  XCircle,
} from "lucide-react";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { listTenants, type UniversityTenant } from "@/lib/api/institutional-integrations";
import {
  createPilot,
  listPilots,
  type PilotMode,
  type PilotStatus,
  type UniversityPilot,
} from "@/lib/api/institutional-pilots";

const STATUS_LABELS: Record<PilotStatus, { label: string; bg: string; text: string; border: string }> = {
  DRAFT: { label: "مسودة أولية", bg: "bg-slate-500/10", text: "text-slate-300", border: "border-slate-500/20" },
  DISCOVERY: { label: "استكشاف أولي", bg: "bg-blue-500/10", text: "text-blue-300", border: "border-blue-500/20" },
  WAITING_FOR_UNIVERSITY_IT: { label: "بانتظار فريق الـ IT", bg: "bg-amber-500/10", text: "text-amber-300", border: "border-amber-500/20" },
  TECHNICAL_REQUIREMENTS_RECEIVED: { label: "استلام المتطلبات الفنية", bg: "bg-sky-500/10", text: "text-sky-300", border: "border-sky-500/20" },
  SANDBOX_PREPARATION: { label: "تجهيز بيئة الاختبار", bg: "bg-indigo-500/10", text: "text-indigo-300", border: "border-indigo-500/20" },
  IDENTITY_CONFIGURATION: { label: "تهيئة الهوية و SSO", bg: "bg-purple-500/10", text: "text-purple-300", border: "border-purple-500/20" },
  ACADEMIC_MAPPING: { label: "مطابقة الخطط والمواد", bg: "bg-cyan-500/10", text: "text-cyan-300", border: "border-cyan-500/20" },
  SECURITY_REVIEW: { label: "المراجعة الأمنية", bg: "bg-violet-500/10", text: "text-violet-300", border: "border-violet-500/20" },
  TECHNICAL_VALIDATION: { label: "التحقق الفني الشامل", bg: "bg-teal-500/10", text: "text-teal-300", border: "border-teal-500/20" },
  READ_ONLY_PILOT_READY: { label: "جاهز للإطلاق التجريبي (قراءة)", bg: "bg-emerald-500/10", text: "text-emerald-300", border: "border-emerald-500/20" },
  READ_ONLY_PILOT_ACTIVE: { label: "إطلاق تجريبي نشط (قراءة)", bg: "bg-emerald-500/20", text: "text-emerald-200", border: "border-emerald-500/40" },
  READ_ONLY_PILOT_ACCEPTANCE: { label: "تقييم قبول الإطلاق (قراءة)", bg: "bg-amber-500/10", text: "text-amber-300", border: "border-amber-500/20" },
  WRITE_PILOT_REVIEW: { label: "مراجعة تفعيل الكتابة", bg: "bg-amber-500/10", text: "text-amber-300", border: "border-amber-500/20" },
  WRITE_ENABLED_PILOT_READY: { label: "جاهز للكتابة المباشرة", bg: "bg-emerald-500/15", text: "text-emerald-300", border: "border-emerald-500/30" },
  GO_LIVE_REVIEW: { label: "مراجعة الإطلاق الشامل", bg: "bg-blue-500/10", text: "text-blue-300", border: "border-blue-500/20" },
  ACCEPTED: { label: "مقبول رسميًا ومعتمد", bg: "bg-emerald-500/25", text: "text-emerald-200", border: "border-emerald-500/50" },
  BLOCKED: { label: "معطل بسبب عائق حرج", bg: "bg-rose-500/20", text: "text-rose-300", border: "border-rose-500/40" },
  SUSPENDED: { label: "معلق مؤقتًا", bg: "bg-orange-500/15", text: "text-orange-300", border: "border-orange-500/30" },
  CANCELLED: { label: "ملغى", bg: "bg-zinc-500/15", text: "text-zinc-400", border: "border-zinc-500/30" },
};

const TEMPLATE_FILES = [
  { name: "استبيان استكشاف نظم الجامعة (IT Discovery)", file: "university_it_discovery.csv", category: "استبيانات" },
  { name: "قالب مطابقة الكليات (Faculty Mapping)", file: "faculty_mapping.csv", category: "مطابقة أكاديمية" },
  { name: "قالب مطابقة التخصصات (Major Mapping)", file: "major_mapping.csv", category: "مطابقة أكاديمية" },
  { name: "قالب مطابقة الخطط الدراسية (Plan Mapping)", file: "plan_mapping.csv", category: "مطابقة أكاديمية" },
  { name: "قالب مطابقة المواد والشُعب (Course Mapping)", file: "course_mapping.csv", category: "مطابقة أكاديمية" },
  { name: "قالب مطابقة الفصول والسنوات (Term Mapping)", file: "term_mapping.csv", category: "مطابقة أكاديمية" },
  { name: "قالب عينة الطلاب الوهمية للاختبار (Test Students)", file: "test_students.csv", category: "بيئة تجريبية" },
  { name: "قائمة مراجعة قبول الإطلاق (Acceptance Checklist)", file: "pilot_acceptance_checklist.csv", category: "إجراءات قبول" },
  { name: "استبيان الأمن وحماية البيانات (Security Questionnaire)", file: "security_questionnaire.csv", category: "أمن ومعلومات" },
];

export default function PilotsDashboardPage() {
  const api = useAuthenticatedApi();
  const [pilots, setPilots] = useState<UniversityPilot[]>([]);
  const [tenants, setTenants] = useState<UniversityTenant[]>([]);
  const [selectedUniversityId, setSelectedUniversityId] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // New Pilot Modal state
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [creating, setCreating] = useState<boolean>(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [formName, setFormName] = useState("");
  const [formUniversityId, setFormUniversityId] = useState("");
  const [formMode, setFormMode] = useState<PilotMode>("READ_ONLY_PILOT");
  const [formStartDate, setFormStartDate] = useState("");
  const [formEndDate, setFormEndDate] = useState("");
  const [formFaculties, setFormFaculties] = useState("");
  const [formMajors, setFormMajors] = useState("");
  const [formStudentCount, setFormStudentCount] = useState<number>(50);
  const [formScopeNotes, setFormScopeNotes] = useState("");
  const [formSisVendor, setFormSisVendor] = useState("Custom / Other");
  const [formAuthProtocol, setFormAuthProtocol] = useState("OIDC");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [tenantsData, pilotsData] = await Promise.all([
        listTenants(api).catch(() => []),
        listPilots(api).catch(() => []),
      ]);
      setTenants(tenantsData);
      setPilots(pilotsData);
      if (tenantsData.length > 0 && !formUniversityId) {
        setFormUniversityId(tenantsData[0].id);
      }
    } catch (err: unknown) {
      console.error("Failed to load pilots:", err);
      setError("تعذر تحميل قائمة مشاريع الإطلاق. يرجى إعادة المحاولة.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  const filteredPilots = useMemo(() => {
    return pilots.filter((p) => {
      if (selectedUniversityId !== "ALL" && p.university_id !== selectedUniversityId) {
        return false;
      }
      if (selectedStatus !== "ALL" && p.status !== selectedStatus) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = p.pilot_name.toLowerCase().includes(q);
        const tenant = tenants.find((t) => t.id === p.university_id);
        const matchesTenant = tenant?.name_ar.toLowerCase().includes(q) || tenant?.tenant_key.toLowerCase().includes(q);
        if (!matchesName && !matchesTenant) return false;
      }
      return true;
    });
  }, [pilots, selectedUniversityId, selectedStatus, searchQuery, tenants]);

  // Metrics
  const metrics = useMemo(() => {
    const total = pilots.length;
    const active = pilots.filter((p) =>
      p.status === "READ_ONLY_PILOT_ACTIVE" || p.status === "WRITE_ENABLED_PILOT_READY"
    ).length;
    const inPrep = pilots.filter((p) =>
      [
        "DRAFT",
        "DISCOVERY",
        "WAITING_FOR_UNIVERSITY_IT",
        "TECHNICAL_REQUIREMENTS_RECEIVED",
        "SANDBOX_PREPARATION",
        "IDENTITY_CONFIGURATION",
        "ACADEMIC_MAPPING",
        "SECURITY_REVIEW",
        "TECHNICAL_VALIDATION",
        "READ_ONLY_PILOT_READY",
      ].includes(p.status)
    ).length;
    const accepted = pilots.filter((p) => p.status === "ACCEPTED").length;
    const blocked = pilots.filter((p) => p.status === "BLOCKED").length;

    return { total, active, inPrep, accepted, blocked };
  }, [pilots]);

  const handleCreatePilot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim() || !formUniversityId) {
      setModalError("يرجى إدخال اسم المشروع واختيار الجامعة");
      return;
    }

    setCreating(true);
    setModalError(null);
    try {
      const payload: Partial<UniversityPilot> = {
        university_id: formUniversityId,
        pilot_name: formName.trim(),
        mode: formMode,
        target_start_date: formStartDate || null,
        target_end_date: formEndDate || null,
        cohort_scope: {
          faculties: formFaculties ? formFaculties.split(",").map((s) => s.trim()) : [],
          majors: formMajors ? formMajors.split(",").map((s) => s.trim()) : [],
          academic_plans: [],
          target_terms: [],
          estimated_student_count: formStudentCount,
          scope_notes: formScopeNotes,
        },
        discovery_intake: {
          university_name_official: tenants.find((t) => t.id === formUniversityId)?.name_ar || "",
          country: "Jordan",
          timezone: "Asia/Amman",
          preferred_locale: "ar",
          sis_vendor: formSisVendor,
          hosting_model: "CLOUD",
          api_available: true,
          api_version: "v1",
          sandbox_available: true,
          documentation_available: true,
          identity_protocol: formAuthProtocol,
          academic_structure_summary: "",
          network_restrictions: "IP Whitelisting required",
          notes: "أنشئ المشروع عبر لوحة تحكم الإطلاق المؤسسي",
        },
        notes: "مشروع إطلاق جامعي جديد",
      };

      const created = await createPilot(api, payload);
      setPilots((prev) => [created, ...prev]);
      setIsModalOpen(false);
      // Reset form
      setFormName("");
      setFormFaculties("");
      setFormMajors("");
      setFormScopeNotes("");
    } catch (err: unknown) {
      console.error("Failed to create pilot:", err);
      setModalError("حدث خطأ أثناء إنشاء المشروع. تأكد من صحة البيانات وصلاحيات الحساب.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="p-4 lg:p-8 space-y-6" dir="rtl">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-amber-500/25 bg-amber-500/10 p-2 text-amber-300">
              <Rocket className="size-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">
                نظام إطلاق الجامعات التجريبي (Pilot Onboarding)
              </h1>
              <p className="mt-1 text-sm text-muted">
                إدارة دورة حياة الإطلاق التجريبي، توثيق المتطلبات، التدقيق الفني والأكاديمي، وبوابات القبول الصارمة للجامعات الشريكة.
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/institutional/integrations"
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-3.5 py-2 text-xs font-semibold text-foreground hover:bg-white/5 transition-colors"
          >
            <Network className="size-4" />
            <span>بوابة ربط SIS</span>
          </Link>

          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors shadow-sm"
          >
            <Plus className="size-4" />
            <span>مشروع إطلاق جديد</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/25 bg-rose-500/10 p-4 text-sm text-rose-300">
          {error}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="flex items-center justify-between text-muted text-xs">
            <span>إجمالي المشاريع</span>
            <Layers className="size-4 text-muted" />
          </div>
          <div className="mt-2 text-2xl font-bold text-foreground">{metrics.total}</div>
          <p className="mt-1 text-[11px] text-muted">كافة الجامعات المسجلة</p>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="flex items-center justify-between text-muted text-xs">
            <span>قيد الإعداد والتهيئة</span>
            <Clock className="size-4 text-sky-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-sky-300">{metrics.inPrep}</div>
          <p className="mt-1 text-[11px] text-muted">متطلبات / مطابقة / أمان</p>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="flex items-center justify-between text-muted text-xs">
            <span>مشاريع نشطة</span>
            <Rocket className="size-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-300">{metrics.active}</div>
          <p className="mt-1 text-[11px] text-muted">قراءة فقط أو كتابة تجريبية</p>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="flex items-center justify-between text-muted text-xs">
            <span>معتمدة ومقبولة</span>
            <ShieldCheck className="size-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-300">{metrics.accepted}</div>
          <p className="mt-1 text-[11px] text-muted">اجتازت كافة بوابات القبول</p>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="flex items-center justify-between text-muted text-xs">
            <span>عوائق حرجة (SEV1)</span>
            <ShieldAlert className="size-4 text-rose-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-rose-300">{metrics.blocked}</div>
          <p className="mt-1 text-[11px] text-muted">تتطلب تدخل فني عاجل</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-surface p-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus-within:border-amber-500">
          <Search className="size-4 text-muted shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="البحث باسم المشروع أو الجامعة..."
            className="w-full bg-transparent placeholder-muted focus:outline-none text-sm"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* University Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted">الجامعة:</span>
            <select
              value={selectedUniversityId}
              onChange={(e) => setSelectedUniversityId(e.target.value)}
              className="rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-amber-500 focus:outline-none"
            >
              <option value="ALL">كافة الجامعات</option>
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name_ar} ({t.tenant_key})
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted">الحالة:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-amber-500 focus:outline-none"
            >
              <option value="ALL">كافة الحالات</option>
              {Object.entries(STATUS_LABELS).map(([k, meta]) => (
                <option key={k} value={k}>
                  {meta.label}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="rounded-xl border border-border bg-background p-2 text-muted hover:text-foreground transition-colors disabled:opacity-50"
            title="تحديث البيانات"
          >
            <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Pilots List */}
      {loading ? (
        <div className="rounded-2xl border border-border bg-surface p-12 text-center text-muted">
          <RefreshCw className="mx-auto size-8 animate-spin text-amber-400 mb-3" />
          <p>جارٍ تحميل بيانات مشاريع الإطلاق...</p>
        </div>
      ) : filteredPilots.length === 0 ? (
        <div className="rounded-2xl border border-border bg-surface p-12 text-center">
          <Rocket className="mx-auto size-12 text-muted/50 mb-3" />
          <h3 className="text-lg font-semibold text-foreground">لا توجد مشاريع إطلاق مطابقة</h3>
          <p className="mt-1 text-sm text-muted max-w-md mx-auto">
            لم يتم العثور على أي مشاريع إطلاق تطابق معايير البحث المحددة. يمكنك إنشاء مشروع جديد للبدء في تأهيل أول جامعة حقيقية.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="mt-4 inline-flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors"
          >
            <Plus className="size-4" />
            <span>إنشاء أول مشروع إطلاق</span>
          </button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredPilots.map((pilot) => {
            const tenant = tenants.find((t) => t.id === pilot.university_id);
            const statusMeta = STATUS_LABELS[pilot.status] || {
              label: pilot.status,
              bg: "bg-slate-500/10",
              text: "text-slate-300",
              border: "border-slate-500/20",
            };
            const isReadOnly = pilot.mode === "READ_ONLY_PILOT";

            return (
              <div
                key={pilot.id}
                className="flex flex-col justify-between rounded-2xl border border-border bg-surface p-5 hover:border-amber-500/30 transition-colors"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-[11px] font-medium text-muted flex items-center gap-1">
                        <Building2 className="size-3" />
                        {tenant?.name_ar || "جامعة غير محددة"} ({tenant?.tenant_key || "unknown"})
                      </span>
                      <h3 className="mt-1 font-bold text-foreground text-base">{pilot.pilot_name}</h3>
                    </div>
                    <span
                      className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusMeta.bg} ${statusMeta.text} ${statusMeta.border}`}
                    >
                      {statusMeta.label}
                    </span>
                  </div>

                  {/* Mode and Cohort info */}
                  <div className="mt-4 space-y-2 text-xs text-muted">
                    <div className="flex items-center justify-between border-t border-border/50 pt-2">
                      <span>نمط التشغيل:</span>
                      <span
                        className={`inline-flex items-center gap-1 font-medium ${
                          isReadOnly ? "text-sky-300" : "text-amber-300"
                        }`}
                      >
                        {isReadOnly ? <Lock className="size-3" /> : <CheckCircle2 className="size-3" />}
                        {isReadOnly ? "قراءة فقط (آمن)" : "كتابة مباشرة (SIS Mutation)"}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span>الطلبة المستهدفون:</span>
                      <span className="font-semibold text-foreground">
                        {pilot.cohort_scope?.estimated_student_count || 0} طالب
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span>الكليات المشمولة:</span>
                      <span className="truncate max-w-[150px] text-foreground" title={pilot.cohort_scope?.faculties?.join(", ")}>
                        {pilot.cohort_scope?.faculties?.length > 0
                          ? pilot.cohort_scope.faculties.join(", ")
                          : "كافة الكليات"}
                      </span>
                    </div>

                    {(pilot.target_start_date || pilot.target_end_date) && (
                      <div className="flex items-center justify-between text-[11px]">
                        <span>الجدول الزمني:</span>
                        <span className="text-muted">
                          {pilot.target_start_date || "—"} إلى {pilot.target_end_date || "—"}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Card Action Link */}
                <div className="mt-5 border-t border-border/50 pt-4">
                  <Link
                    href={`/institutional/pilots/${pilot.id}`}
                    className="flex w-full items-center justify-center gap-2 rounded-xl border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-200 hover:bg-amber-500/20 transition-colors"
                  >
                    <span>فتح لوحة القيادة والفحوصات</span>
                    <ArrowUpRight className="size-4" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Downloadable Package & Templates Section */}
      <div className="rounded-2xl border border-border bg-surface p-6">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b border-border pb-4">
          <div>
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="size-5 text-amber-400" />
              <h2 className="text-base font-bold text-foreground">
                حزمة الإطلاق وقوالب التهيئة الرسمية (Pilot Toolkit & Templates)
              </h2>
            </div>
            <p className="mt-1 text-xs text-muted">
              قوالب CSV رسمية جاهزة للتسليم إلى فريق الـ IT والمسجل العام في الجامعة لتعبئة بيانات المطابقة والاستبيانات الفنية.
            </p>
          </div>
          <span className="text-xs text-muted bg-background px-3 py-1.5 rounded-xl border border-border">
            مبدأ الحوكمة: الذكاء يشرح، والقواعد تقرر
          </span>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {TEMPLATE_FILES.map((tpl) => (
            <div
              key={tpl.file}
              className="flex items-center justify-between rounded-xl border border-border/80 bg-background/50 p-3 hover:border-amber-500/30 transition-colors"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <FileText className="size-4 text-muted shrink-0" />
                <div className="truncate">
                  <p className="text-xs font-medium text-foreground truncate">{tpl.name}</p>
                  <p className="text-[10px] text-muted">{tpl.category}</p>
                </div>
              </div>
              <a
                href={`/pilot-templates/${tpl.file}`}
                download={tpl.file}
                className="shrink-0 p-1.5 text-muted hover:text-amber-300 transition-colors rounded-lg hover:bg-white/5"
                title={`تحميل ملف ${tpl.file}`}
              >
                <Download className="size-4" />
              </a>
            </div>
          ))}
        </div>
      </div>

      {/* Create Pilot Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-xl rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-4 my-8" dir="rtl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Rocket className="size-5 text-amber-400" />
                <h3 className="font-bold text-foreground text-lg">إنشاء مشروع إطلاق تجريبي جديد</h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg p-1 text-muted hover:text-foreground hover:bg-white/5"
              >
                <X className="size-5" />
              </button>
            </div>

            {modalError && (
              <div className="rounded-xl border border-rose-500/25 bg-rose-500/10 p-3 text-xs text-rose-300">
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreatePilot} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">اسم المشروع التجريبي *</label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="مثال: الإطلاق التجريبي لكليات الهندسة وتكنولوجيا المعلومات - ربيع 2026"
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">الجامعة الشريكة *</label>
                  <select
                    value={formUniversityId}
                    onChange={(e) => setFormUniversityId(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                  >
                    {tenants.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name_ar} ({t.tenant_key})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted mb-1">نمط الإطلاق الأولي *</label>
                  <select
                    value={formMode}
                    onChange={(e) => setFormMode(e.target.value as PilotMode)}
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                  >
                    <option value="READ_ONLY_PILOT">قراءة فقط - آمن وبدون تعديل SIS (موصى به)</option>
                    <option value="WRITE_ENABLED_PILOT">كتابة مفعلة - يتطلب اجتياز بوابة الـ 12 معياراً</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">تاريخ البدء المتوقع</label>
                  <input
                    type="date"
                    value={formStartDate}
                    onChange={(e) => setFormStartDate(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">تاريخ الانتهاء المتوقع</label>
                  <input
                    type="date"
                    value={formEndDate}
                    onChange={(e) => setFormEndDate(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Cohort Scope */}
              <div className="rounded-xl border border-border/80 bg-background/50 p-3 space-y-3">
                <span className="text-xs font-semibold text-amber-300 block">نطاق العينة التجريبية (Cohort Scope):</span>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-[11px] text-muted mb-1">الكليات (مفصولة بفواصل)</label>
                    <input
                      type="text"
                      value={formFaculties}
                      onChange={(e) => setFormFaculties(e.target.value)}
                      placeholder="كلية تكنولوجيا المعلومات, كلية الهندسة"
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-muted mb-1">التخصصات (مفصولة بفواصل)</label>
                    <input
                      type="text"
                      value={formMajors}
                      onChange={(e) => setFormMajors(e.target.value)}
                      placeholder="علم الحاسوب, هندسة البرمجيات"
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-[11px] text-muted mb-1">العدد التقديري للطلبة</label>
                    <input
                      type="number"
                      min={1}
                      max={10000}
                      value={formStudentCount}
                      onChange={(e) => setFormStudentCount(parseInt(e.target.value) || 0)}
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-muted mb-1">نوع نظام الـ SIS</label>
                    <select
                      value={formSisVendor}
                      onChange={(e) => setFormSisVendor(e.target.value)}
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                    >
                      <option value="FakeUniversity / Sandbox">FakeUniversity / Sandbox (بيئة الاختبار)</option>
                      <option value="Ellucian Banner">Ellucian Banner</option>
                      <option value="Oracle Peoplesoft">Oracle PeopleSoft</option>
                      <option value="Workday Student">Workday Student</option>
                      <option value="Custom REST API">نظام محلي عبر REST API</option>
                      <option value="Custom / Other">نظام محلي آخر</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] text-muted mb-1">ملاحظات النطاق</label>
                  <textarea
                    rows={2}
                    value={formScopeNotes}
                    onChange={(e) => setFormScopeNotes(e.target.value)}
                    placeholder="أي قيود أو شروط خاصة بالعينة التجريبية..."
                    className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-muted hover:text-foreground transition-colors"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors disabled:opacity-50"
                >
                  {creating ? <RefreshCw className="size-3.5 animate-spin" /> : <Plus className="size-3.5" />}
                  <span>{creating ? "جارٍ الإنشاء..." : "إنشاء المشروع"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
