"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRightLeft,
  CheckCircle2,
  Clock,
  Database,
  ExternalLink,
  Layers,
  Lock,
  Network,
  RefreshCw,
  Rocket,
  Server,
  ShieldAlert,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import {
  getConfig,
  getHealth,
  getReadiness,
  listMappings,
  listReconciliation,
  listSyncJobs,
  listTenants,
  triggerSync,
  type HealthResult,
  type PilotReadinessScorecard,
  type ReconciliationItem,
  type SyncJob,
  type UniversityIntegrationConfig,
  type UniversityMapping,
  type UniversityTenant,
} from "@/lib/api/institutional-integrations";

type TabId = "overview" | "readiness" | "connection" | "capabilities" | "mappings" | "sync" | "webhooks" | "reconciliation";

export default function IntegrationsDashboardPage() {
  const api = useAuthenticatedApi();
  const [tenants, setTenants] = useState<UniversityTenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const [config, setConfig] = useState<UniversityIntegrationConfig | null>(null);
  const [health, setHealth] = useState<HealthResult | null>(null);
  const [readiness, setReadiness] = useState<PilotReadinessScorecard | null>(null);
  const [mappings, setMappings] = useState<UniversityMapping[]>([]);
  const [syncJobs, setSyncJobs] = useState<SyncJob[]>([]);
  const [reconciliation, setReconciliation] = useState<ReconciliationItem[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load tenants on mount
  useEffect(() => {
    listTenants(api)
      .then((t) => {
        setTenants(t);
        if (t.length > 0) {
          setSelectedTenantId(t[0].id);
        }
      })
      .catch((err) => {
        console.error("Failed to load university tenants:", err);
        setError("تعذر تحميل بيانات الجامعات المتصلة");
      })
      .finally(() => setLoading(false));
  }, [api]);

  // Load tenant-scoped details
  useEffect(() => {
    if (!selectedTenantId) return;
    setLoading(true);
    setError(null);

    Promise.allSettled([
      getConfig(api, selectedTenantId),
      getHealth(api, selectedTenantId),
      getReadiness(api, selectedTenantId),
      listMappings(api, selectedTenantId),
      listSyncJobs(api, selectedTenantId),
      listReconciliation(api, selectedTenantId),
    ]).then(([cfgRes, hlthRes, readRes, mapRes, jobsRes, reconRes]) => {
      if (cfgRes.status === "fulfilled") setConfig(cfgRes.value);
      if (hlthRes.status === "fulfilled") setHealth(hlthRes.value);
      if (readRes.status === "fulfilled") setReadiness(readRes.value);
      if (mapRes.status === "fulfilled") setMappings(mapRes.value);
      if (jobsRes.status === "fulfilled") setSyncJobs(jobsRes.value);
      if (reconRes.status === "fulfilled") setReconciliation(reconRes.value);
      setLoading(false);
    });
  }, [api, selectedTenantId]);

  const handleTriggerSync = async (mode: "FULL_SYNC" | "INCREMENTAL_SYNC") => {
    if (!selectedTenantId) return;
    setSyncing(true);
    try {
      const job = await triggerSync(api, selectedTenantId, mode);
      setSyncJobs((prev) => [job, ...prev]);
      // Refresh health
      const h = await getHealth(api, selectedTenantId);
      setHealth(h);
    } catch (err) {
      console.error("Sync failed:", err);
    } finally {
      setSyncing(false);
    }
  };

  const currentTenant = tenants.find((t) => t.id === selectedTenantId);

  return (
    <div className="p-4 lg:p-8 space-y-6" dir="rtl">
      {/* Header & University Selector */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-foreground">بوابة ربط الجامعات وأنظمة SIS</h1>
            {readiness?.overall_status === "PASS" && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                <ShieldCheck className="size-3.5" /> جاهز للإطلاق
              </span>
            )}
            {readiness?.overall_status === "WARNING" && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/25 bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-400">
                <AlertTriangle className="size-3.5" /> تنبيهات جاهزية
              </span>
            )}
            {readiness?.overall_status === "FAIL" && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/25 bg-rose-500/10 px-2.5 py-0.5 text-xs font-semibold text-rose-400">
                <ShieldAlert className="size-3.5" /> غير مكتمل
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted">
            إدارة التكامل الفني، مطابقة الخطط والمواد، المزامنة الدورية، واختبار الجاهزية التشغيلية للجامعات الشريكة.
          </p>
        </div>

        {/* Tenant Selector & Pilot Link */}
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/institutional/pilots"
            className="inline-flex items-center gap-2 rounded-xl border border-amber-500/25 bg-amber-500/10 px-3.5 py-2 text-xs font-semibold text-amber-200 hover:bg-amber-500/20 transition-colors"
          >
            <Rocket className="size-4" />
            <span>إدارة مشاريع الإطلاق (Pilots)</span>
          </Link>

          {tenants.length > 0 && (
            <div className="flex items-center gap-2">
              <label htmlFor="tenant-select" className="text-xs font-medium text-muted whitespace-nowrap">
                الجامعة:
              </label>
              <select
                id="tenant-select"
                value={selectedTenantId}
                onChange={(e) => setSelectedTenantId(e.target.value)}
                className="rounded-xl border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
              >
                {tenants.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name_ar} ({t.tenant_key})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/25 bg-rose-500/10 p-4 text-sm text-rose-300">
          {error}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex gap-2 overflow-x-auto border-b border-border pb-2 text-sm">
        {(
          [
            ["overview", "نظرة عامة", Activity],
            ["readiness", "بطاقة الجاهزية (16 معياراً)", ShieldCheck],
            ["connection", "إعدادات الاتصال", Server],
            ["capabilities", "القدرات المصرحة", Lock],
            ["mappings", "مطابقة الخطط والمواد", ArrowRightLeft],
            ["sync", "المزامنة والتشغيل", RefreshCw],
            ["webhooks", "أحداث الويب (Webhooks)", Zap],
            ["reconciliation", "تقرير الفروقات (Reconciliation)", Layers],
          ] as const
        ).map(([id, label, Icon]) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex shrink-0 items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                active
                  ? "border border-amber-500/30 bg-amber-500/10 text-amber-200"
                  : "text-muted hover:bg-surface hover:text-foreground"
              }`}
            >
              <Icon className="size-4" />
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Overview */}
      {activeTab === "overview" && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-border bg-surface p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted">حالة النظام</span>
              <span
                className={`size-2.5 rounded-full ${
                  health?.status === "HEALTHY"
                    ? "bg-emerald-400"
                    : health?.status === "DEGRADED"
                    ? "bg-amber-400"
                    : "bg-rose-400"
                }`}
              />
            </div>
            <p className="mt-3 text-2xl font-bold text-foreground">
              {health?.status === "HEALTHY"
                ? "متصل وسليم"
                : health?.status === "DEGRADED"
                ? "استجابة بطيئة"
                : "غير متصل"}
            </p>
            <p className="mt-1 text-xs text-muted">
              زمن الاستجابة: {health?.latency_ms ?? 0} مللي ثانية
            </p>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-5">
            <span className="text-xs text-muted">نمط الإطلاق التجريبي</span>
            <p className="mt-3 text-xl font-bold text-foreground">
              {config?.pilot_mode === "WRITE_ENABLED_PILOT"
                ? "تسجيل وسحب مصرح (Write-Enabled)"
                : "قراءة ومحاكاة فقط (Read-Only)"}
            </p>
            <p className="mt-1 text-xs text-muted">
              المبدأ: نظام الجامعة يبقى المرجع المعتمد دائماً
            </p>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-5">
            <span className="text-xs text-muted">تغطية مطابقة المواد</span>
            <p className="mt-3 text-2xl font-bold text-foreground">
              {readiness?.mapping_coverage?.course ?? 100}%
            </p>
            <p className="mt-1 text-xs text-muted">
              إجمالي الكيانات المطابقة: {mappings.length}
            </p>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-5">
            <span className="text-xs text-muted">آخر مزامنة ناجحة</span>
            <p className="mt-3 text-lg font-bold text-foreground">
              {syncJobs[0]?.status ?? "لا يوجد"}
            </p>
            <p className="mt-1 text-xs text-muted">
              {syncJobs[0] ? `${syncJobs[0].records_processed} سجل عولج` : "لم تجر مزامنة بعد"}
            </p>
          </div>

          {/* Detailed summary card */}
          <div className="col-span-full rounded-2xl border border-border bg-surface p-6 space-y-4">
            <h3 className="text-base font-semibold text-foreground">بيانات المستأجر (Tenant Invariants)</h3>
            <div className="grid gap-4 sm:grid-cols-3 text-sm">
              <div>
                <span className="text-xs text-muted block">معرف المستأجر (Tenant Key)</span>
                <span className="font-mono text-foreground">{currentTenant?.tenant_key}</span>
              </div>
              <div>
                <span className="text-xs text-muted block">المنطقة الزمنية</span>
                <span className="text-foreground">{currentTenant?.timezone}</span>
              </div>
              <div>
                <span className="text-xs text-muted block">اللغة الافتراضية</span>
                <span className="text-foreground">{currentTenant?.default_locale === "ar" ? "العربية" : "الإنجليزية"}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Readiness Scorecard */}
      {activeTab === "readiness" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-border bg-surface p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-lg font-bold text-foreground">قائمة التدقيق الفني للإطلاق التجريبي (16 معياراً)</h3>
                <p className="mt-1 text-sm text-muted">{readiness?.summary_ar}</p>
              </div>
              <div className="text-left">
                <span className="text-xs text-muted block">تقييم الجاهزية الإجمالي</span>
                <span
                  className={`inline-block mt-1 px-3 py-1 rounded-full text-sm font-bold ${
                    readiness?.overall_status === "PASS"
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                      : readiness?.overall_status === "WARNING"
                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                      : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                  }`}
                >
                  {readiness?.overall_status === "PASS"
                    ? "جاهز للاعتماد"
                    : readiness?.overall_status === "WARNING"
                    ? "شبه جاهز مع ملاحظات"
                    : "غير جاهز"}
                </span>
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {readiness?.checklist &&
                Object.entries(readiness.checklist).map(([criterion, status]) => (
                  <div
                    key={criterion}
                    className="flex items-center justify-between rounded-xl border border-border/60 bg-background/50 p-3.5"
                  >
                    <span className="text-xs font-mono text-muted">{criterion}</span>
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded ${
                        status === "PASS"
                          ? "text-emerald-400 bg-emerald-500/10"
                          : status === "WARNING"
                          ? "text-amber-400 bg-amber-500/10"
                          : status === "NOT_APPLICABLE"
                          ? "text-muted bg-white/5"
                          : "text-rose-400 bg-rose-500/10"
                      }`}
                    >
                      {status}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Connection */}
      {activeTab === "connection" && (
        <div className="rounded-2xl border border-border bg-surface p-6 space-y-6">
          <h3 className="text-lg font-bold text-foreground">إعدادات الاتصال والمزود (SIS Connection)</h3>
          <div className="grid gap-6 md:grid-cols-2 text-sm">
            <div>
              <label className="block text-xs text-muted mb-1">نوع المزود (Provider Type)</label>
              <div className="rounded-xl border border-border bg-background p-3 font-mono text-foreground">
                {config?.provider_type ?? "غير محدد"}
              </div>
            </div>
            <div>
              <label className="block text-xs text-muted mb-1">الرابط الأساسي (Base URL)</label>
              <div className="rounded-xl border border-border bg-background p-3 font-mono text-foreground">
                {config?.base_url ?? "غير محدد"}
              </div>
            </div>
            <div>
              <label className="block text-xs text-muted mb-1">طريقة المصادقة (Auth Method)</label>
              <div className="rounded-xl border border-border bg-background p-3 text-foreground">
                {config?.auth_method ?? "token"}
              </div>
            </div>
            <div>
              <label className="block text-xs text-muted mb-1">متغير السر بالخادم (Secret Env Reference)</label>
              <div className="rounded-xl border border-border bg-background p-3 font-mono text-amber-300">
                {config?.secret_env_ref ?? "لم يحدد متغير بيئة"}
              </div>
            </div>
            <div>
              <label className="block text-xs text-muted mb-1">المهلة الزمنية (Timeouts)</label>
              <div className="rounded-xl border border-border bg-background p-3 text-foreground">
                اتصال: {config?.timeouts_ms?.connect ?? 5000}ms | قراءة: {config?.timeouts_ms?.read ?? 10000}ms
              </div>
            </div>
            <div>
              <label className="block text-xs text-muted mb-1">حد الطلبات (Rate Limit RPM)</label>
              <div className="rounded-xl border border-border bg-background p-3 text-foreground">
                {config?.rate_limit_rpm ?? 600} طلب بالدقيقة
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Capabilities */}
      {activeTab === "capabilities" && (
        <div className="rounded-2xl border border-border bg-surface p-6 space-y-6">
          <div>
            <h3 className="text-lg font-bold text-foreground">مصفوفة القدرات المصرحة (Capability Negotiation)</h3>
            <p className="mt-1 text-sm text-muted">
              كل صلاحية تتطلب ترخيصاً مستقلاً من الجامعة قبل تفعيلها. العمليات غير المصرحة ترفض برمجياً بشكل قاطع.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[
              ["IDENTITY_AUTH", "مصادقة هوية الطالب", true],
              ["STUDENT_PROFILE_READ", "قراءة الملف الأكاديمي", true],
              ["GRADES_READ", "قراءة سجل العلامات والمحاولات", true],
              ["ENROLLMENTS_READ", "قراءة التسجيل الفصلي الحالي", true],
              ["CURRICULUM_READ", "قراءة هيكل الخطة الدراسية", true],
              ["OFFERINGS_READ", "قراءة الشعب والمواعيد المطروحة", true],
              ["SECTION_CAPACITY", "قراءة طاقة الشعب والمقاعد المتاحة", true],
              ["REGISTRATION_PREVIEW", "معاينة التسجيل غير المعدلة", true],
              ["REGISTRATION_WRITE", "اعتماد التسجيل رسمياً في الـ SIS", config?.pilot_mode === "WRITE_ENABLED_PILOT"],
              ["DROP_WRITE", "سحب الشعب في الـ SIS", config?.pilot_mode === "WRITE_ENABLED_PILOT"],
              ["INCREMENTAL_SYNC", "المزامنة التدريجية عبر المؤشرات", true],
              ["WEBHOOKS", "استقبال إشعارات التحديث الفورية", true],
              ["SSO", "الربط مع موفر الهوية الموحد (OIDC/SAML)", false],
            ].map(([capId, label, permitted]) => {
              const hasCap = config?.supported_capabilities?.includes(capId as string);
              return (
                <div
                  key={capId as string}
                  className={`rounded-xl border p-4 flex items-center justify-between ${
                    hasCap && permitted
                      ? "border-emerald-500/25 bg-emerald-500/5"
                      : "border-border bg-background/50 opacity-60"
                  }`}
                >
                  <div>
                    <span className="text-sm font-semibold text-foreground block">{label}</span>
                    <span className="text-xs font-mono text-muted">{capId as string}</span>
                  </div>
                  {hasCap && permitted ? (
                    <CheckCircle2 className="size-5 text-emerald-400" />
                  ) : (
                    <Lock className="size-4 text-muted" />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 5: Mappings */}
      {activeTab === "mappings" && (
        <div className="rounded-2xl border border-border bg-surface p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-foreground">جدول المطابقة الأكاديمية (Curriculum Mappings)</h3>
              <p className="mt-1 text-sm text-muted">
                ربط رموز الكليات، التخصصات، الخطط، والمواد الخاصة بنظام الجامعة بالكيانات المعيارية في مرشدي.
              </p>
            </div>
            <span className="text-xs text-muted font-mono">{mappings.length} سجلات مطابقة</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-right text-sm">
              <thead className="border-b border-border text-xs text-muted">
                <tr>
                  <th className="pb-3 pr-2">نوع الكيان</th>
                  <th className="pb-3">الرمز الخارجي لدى الجامعة</th>
                  <th className="pb-3">المعرف المعياري في مرشدي</th>
                  <th className="pb-3">الرمز المعياري</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {mappings.map((m) => (
                  <tr key={m.id} className="hover:bg-white/5">
                    <td className="py-3 pr-2 font-semibold text-amber-300">{m.entity_type}</td>
                    <td className="py-3 font-mono text-foreground">{m.external_code}</td>
                    <td className="py-3 font-mono text-muted">{m.canonical_id}</td>
                    <td className="py-3 font-mono text-emerald-400">{m.canonical_code ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 6: Synchronization */}
      {activeTab === "sync" && (
        <div className="rounded-2xl border border-border bg-surface p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-foreground">مركز مزامنة البيانات (Sync Orchestration)</h3>
              <p className="mt-1 text-sm text-muted">
                مزامنة الكتالوج، الشعب، وسجلات الطلاب المحدثة تدريجياً مع نظام الجامعة المعتمد.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                disabled={syncing}
                onClick={() => handleTriggerSync("FULL_SYNC")}
                className="flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50"
              >
                <RefreshCw className={`size-4 ${syncing ? "animate-spin" : ""}`} />
                <span>مزامنة شاملة (Full)</span>
              </button>
              <button
                disabled={syncing}
                onClick={() => handleTriggerSync("INCREMENTAL_SYNC")}
                className="flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-2 text-sm font-semibold text-foreground hover:bg-white/5 disabled:opacity-50"
              >
                <RefreshCw className={`size-4 ${syncing ? "animate-spin" : ""}`} />
                <span>مزامنة تدريجية (Incremental)</span>
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-right text-sm">
              <thead className="border-b border-border text-xs text-muted">
                <tr>
                  <th className="pb-3 pr-2">النمط</th>
                  <th className="pb-3">الحالة</th>
                  <th className="pb-3">السجلات المعالجة</th>
                  <th className="pb-3">الناجحة</th>
                  <th className="pb-3">المتعثرة</th>
                  <th className="pb-3">المدة</th>
                  <th className="pb-3">تاريخ البدء</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {syncJobs.map((job) => (
                  <tr key={job.id} className="hover:bg-white/5">
                    <td className="py-3 pr-2 font-mono text-xs">{job.sync_mode}</td>
                    <td className="py-3">
                      <span
                        className={`text-xs font-bold px-2 py-0.5 rounded ${
                          job.status === "SUCCEEDED"
                            ? "text-emerald-400 bg-emerald-500/10"
                            : job.status === "PARTIAL"
                            ? "text-amber-400 bg-amber-500/10"
                            : "text-rose-400 bg-rose-500/10"
                        }`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="py-3 font-mono">{job.records_processed}</td>
                    <td className="py-3 font-mono text-emerald-400">{job.records_created + job.records_updated}</td>
                    <td className="py-3 font-mono text-rose-400">{job.records_failed}</td>
                    <td className="py-3 text-muted">{job.duration_ms}ms</td>
                    <td className="py-3 text-muted text-xs">{new Date(job.started_at).toLocaleString("ar")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 7: Webhooks */}
      {activeTab === "webhooks" && (
        <div className="rounded-2xl border border-border bg-surface p-6 space-y-6">
          <h3 className="text-lg font-bold text-foreground">تكامل إشعارات الويب (Inbound Webhooks)</h3>
          <p className="text-sm text-muted">
            يمكن لنظام الجامعة إرسال تحديثات فورية (تسجيل طالب، رصد علامة، تعديل شعبة) إلى رابط الاستقبال الخاص بالجامعة:
          </p>

          <div className="space-y-4">
            <div>
              <span className="text-xs text-muted block mb-1">رابط الاستقبال للجامعة (Webhook Target URL)</span>
              <div className="rounded-xl border border-border bg-background p-3 font-mono text-sm text-emerald-400">
                https://morshidi.onrender.com/api/v1/integrations/{currentTenant?.tenant_key}/webhooks/generic
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3 text-xs">
              <div className="rounded-xl border border-border p-4 bg-background/50">
                <span className="font-bold text-foreground block mb-1">التحقق من التوقيع (HMAC-SHA256)</span>
                <p className="text-muted">ترويسة: <code className="text-amber-300">X-Morshidi-Signature</code></p>
                <p className="text-muted mt-1">تشفير كامل لمحتوى الطلب باستخدام المفتاح المشترك.</p>
              </div>

              <div className="rounded-xl border border-border p-4 bg-background/50">
                <span className="font-bold text-foreground block mb-1">نافذة منع التكرار (Replay Window)</span>
                <p className="text-muted">ترويسة: <code className="text-amber-300">X-Morshidi-Timestamp</code></p>
                <p className="text-muted mt-1">المهلة القصوى: 300 ثانية (5 دقائق). ترفض الطلبات الأقدم تلقائياً.</p>
              </div>

              <div className="rounded-xl border border-border p-4 bg-background/50">
                <span className="font-bold text-foreground block mb-1">معرف العملية الفريد (Idempotency)</span>
                <p className="text-muted">ترويسة: <code className="text-amber-300">X-Morshidi-Event-ID</code></p>
                <p className="text-muted mt-1">منع المعالجة المزدوجة للأحداث المتكررة.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 8: Reconciliation */}
      {activeTab === "reconciliation" && (
        <div className="rounded-2xl border border-border bg-surface p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-foreground">تقرير الفروقات والتسوية (Reconciliation Report)</h3>
              <p className="mt-1 text-sm text-muted">
                مقارنة مستمرة بين الحالة التخزينية في مرشدي ونظام الجامعة المعتمد لرصد أي انحراف (Drift).
              </p>
            </div>
            <span className="text-xs text-muted font-mono">{reconciliation.length} عناصر تسوية</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-right text-sm">
              <thead className="border-b border-border text-xs text-muted">
                <tr>
                  <th className="pb-3 pr-2">نوع الكيان</th>
                  <th className="pb-3">المعرف لدى الجامعة</th>
                  <th className="pb-3">حالة التسوية</th>
                  <th className="pb-3">تاريخ الاكتشاف</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {reconciliation.map((item) => (
                  <tr key={item.id} className="hover:bg-white/5">
                    <td className="py-3 pr-2 font-semibold text-foreground">{item.entity_type}</td>
                    <td className="py-3 font-mono text-muted">{item.external_identifier}</td>
                    <td className="py-3">
                      <span
                        className={`text-xs font-bold px-2 py-0.5 rounded ${
                          item.status === "IN_SYNC"
                            ? "text-emerald-400 bg-emerald-500/10"
                            : item.status === "STALE_LOCALLY"
                            ? "text-amber-400 bg-amber-500/10"
                            : "text-rose-400 bg-rose-500/10"
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3 text-xs text-muted">{new Date(item.detected_at).toLocaleString("ar")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
