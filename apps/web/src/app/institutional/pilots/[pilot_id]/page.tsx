"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState, useMemo, useCallback } from "react";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Building2,
  Calendar,
  CheckCircle2,
  ChevronDown,
  Clock,
  Database,
  ExternalLink,
  FileCheck,
  FileSpreadsheet,
  FileText,
  Key,
  Layers,
  Lock,
  Network,
  Plus,
  RefreshCw,
  Rocket,
  Scale,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  Users,
  X,
  XCircle,
  Zap,
} from "lucide-react";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import {
  addPilotStakeholder,
  createPilotBlocker,
  deletePilotStakeholder,
  getPilot,
  getPilotReport,
  getPilotSummary,
  getPilotWriteEnablement,
  listPilotAcceptanceChecks,
  listPilotActivity,
  listPilotBlockers,
  listPilotRequirements,
  listPilotSignoffs,
  listPilotStakeholders,
  recordPilotSignoff,
  runAutomatedAcceptance,
  transitionPilot,
  updatePilot,
  updatePilotAcceptanceCheck,
  updatePilotBlocker,
  updatePilotRequirement,
  type PilotAcceptanceCheck,
  type PilotActivity,
  type PilotBlocker,
  type PilotMode,
  type PilotReport,
  type PilotRequirement,
  type PilotSignoff,
  type PilotStakeholder,
  type PilotStatus,
  type PilotSummary,
  type UniversityPilot,
  type WriteEnablementResult,
} from "@/lib/api/institutional-pilots";

type TabId =
  | "overview"
  | "scope"
  | "requirements"
  | "questionnaires"
  | "blockers"
  | "acceptance"
  | "write_enablement"
  | "signoffs"
  | "stakeholders"
  | "activity";

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

const LIFECYCLE_STAGES: { stage: string; statuses: PilotStatus[] }[] = [
  {
    stage: "الإعداد والاستكشاف",
    statuses: ["DRAFT", "DISCOVERY", "WAITING_FOR_UNIVERSITY_IT"],
  },
  {
    stage: "التهيئة الفنية والأمنية",
    statuses: [
      "TECHNICAL_REQUIREMENTS_RECEIVED",
      "SANDBOX_PREPARATION",
      "IDENTITY_CONFIGURATION",
      "ACADEMIC_MAPPING",
      "SECURITY_REVIEW",
      "TECHNICAL_VALIDATION",
    ],
  },
  {
    stage: "الإطلاق التجريبي (قراءة)",
    statuses: ["READ_ONLY_PILOT_READY", "READ_ONLY_PILOT_ACTIVE", "READ_ONLY_PILOT_ACCEPTANCE"],
  },
  {
    stage: "الكتابة والاعتماد",
    statuses: ["WRITE_PILOT_REVIEW", "WRITE_ENABLED_PILOT_READY", "GO_LIVE_REVIEW", "ACCEPTED"],
  },
];

export default function PilotDetailsPage() {
  const params = useParams();
  const pilotId = params?.pilot_id as string;
  const api = useAuthenticatedApi();

  const [pilot, setPilot] = useState<UniversityPilot | null>(null);
  const [summary, setSummary] = useState<PilotSummary | null>(null);
  const [requirements, setRequirements] = useState<PilotRequirement[]>([]);
  const [blockers, setBlockers] = useState<PilotBlocker[]>([]);
  const [stakeholders, setStakeholders] = useState<PilotStakeholder[]>([]);
  const [acceptanceChecks, setAcceptanceChecks] = useState<PilotAcceptanceCheck[]>([]);
  const [signoffs, setSignoffs] = useState<PilotSignoff[]>([]);
  const [writeEnablement, setWriteEnablement] = useState<WriteEnablementResult | null>(null);
  const [activity, setActivity] = useState<PilotActivity[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Transition Modal State
  const [isTransitionModalOpen, setIsTransitionModalOpen] = useState(false);
  const [targetStatus, setTargetStatus] = useState<PilotStatus>("DISCOVERY");
  const [transitionNotes, setTransitionNotes] = useState("");
  const [transitioning, setTransitioning] = useState(false);
  const [transitionError, setTransitionError] = useState<string | null>(null);

  // Blocker Modal State
  const [isBlockerModalOpen, setIsBlockerModalOpen] = useState(false);
  const [blockerCode, setBlockerCode] = useState("");
  const [blockerTitle, setBlockerTitle] = useState("");
  const [blockerSeverity, setBlockerSeverity] = useState<string>("SEV1");
  const [blockerOwner, setBlockerOwner] = useState("UNIVERSITY_IT");
  const [blockerNotes, setBlockerNotes] = useState("");
  const [savingBlocker, setSavingBlocker] = useState(false);

  // Resolve Blocker Modal State
  const [resolveBlockerTarget, setResolveBlockerTarget] = useState<PilotBlocker | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [resolvingBlocker, setResolvingBlocker] = useState(false);

  // Requirement Update Modal State
  const [editingRequirement, setEditingRequirement] = useState<PilotRequirement | null>(null);
  const [reqStatus, setReqStatus] = useState<string>("VALIDATED");
  const [reqSecretRef, setReqSecretRef] = useState<string>("");
  const [reqNotes, setReqNotes] = useState<string>("");
  const [updatingReq, setUpdatingReq] = useState(false);

  // Signoff Modal State
  const [isSignoffModalOpen, setIsSignoffModalOpen] = useState(false);
  const [signoffRole, setSignoffRole] = useState("TECHNICAL_SIGN_OFF");
  const [signeeName, setSigneeName] = useState("");
  const [signeeTitle, setSigneeTitle] = useState("");
  const [signoffDecision, setSignoffDecision] = useState("APPROVED");
  const [signoffNotes, setSignoffNotes] = useState("");
  const [savingSignoff, setSavingSignoff] = useState(false);

  // Acceptance Check Modal State
  const [editingCheck, setEditingCheck] = useState<PilotAcceptanceCheck | null>(null);
  const [checkStatus, setCheckStatus] = useState<string>("PASS");
  const [checkEvidence, setCheckEvidence] = useState("");
  const [checkNotes, setCheckNotes] = useState("");
  const [updatingCheck, setUpdatingCheck] = useState(false);
  const [runningAutomated, setRunningAutomated] = useState(false);

  // Report Modal State
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [pilotReport, setPilotReport] = useState<PilotReport | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);

  // Stakeholder Modal State
  const [isStakeholderModalOpen, setIsStakeholderModalOpen] = useState(false);
  const [stakeholderRole, setStakeholderRole] = useState("PROJECT_LEAD");
  const [stakeholderName, setStakeholderName] = useState("");
  const [stakeholderEmail, setStakeholderEmail] = useState("");
  const [stakeholderTitle, setStakeholderTitle] = useState("");
  const [stakeholderPhone, setStakeholderPhone] = useState("");
  const [savingStakeholder, setSavingStakeholder] = useState(false);

  // Scope form state
  const [scopeFaculties, setScopeFaculties] = useState("");
  const [scopeMajors, setScopeMajors] = useState("");
  const [scopeStudents, setScopeStudents] = useState<number>(50);
  const [scopeNotes, setScopeNotes] = useState("");
  const [savingScope, setSavingScope] = useState(false);

  // Load all pilot data
  const loadPilotDetails = useCallback(async () => {
    if (!pilotId) return;
    setLoading(true);
    setError(null);
    try {
      const [
        pData,
        sumData,
        reqData,
        blkData,
        stkData,
        chkData,
        srfData,
        wreData,
        actData,
      ] = await Promise.all([
        getPilot(api, pilotId),
        getPilotSummary(api, pilotId).catch(() => null),
        listPilotRequirements(api, pilotId).catch(() => []),
        listPilotBlockers(api, pilotId).catch(() => []),
        listPilotStakeholders(api, pilotId).catch(() => []),
        listPilotAcceptanceChecks(api, pilotId).catch(() => []),
        listPilotSignoffs(api, pilotId).catch(() => []),
        getPilotWriteEnablement(api, pilotId).catch(() => null),
        listPilotActivity(api, pilotId).catch(() => []),
      ]);

      setPilot(pData);
      setSummary(sumData);
      setRequirements(reqData);
      setBlockers(blkData);
      setStakeholders(stkData);
      setAcceptanceChecks(chkData);
      setSignoffs(srfData);
      setWriteEnablement(wreData);
      setActivity(actData);

      if (pData) {
        setScopeFaculties(pData.cohort_scope?.faculties?.join(", ") || "");
        setScopeMajors(pData.cohort_scope?.majors?.join(", ") || "");
        setScopeStudents(pData.cohort_scope?.estimated_student_count || 50);
        setScopeNotes(pData.cohort_scope?.scope_notes || "");
      }
    } catch (err: unknown) {
      console.error("Failed to load pilot details:", err);
      setError("تعذر تحميل بيانات المشروع. يرجى التأكد من المعرّف وصلاحيات الدخول.");
    } finally {
      setLoading(false);
    }
  }, [api, pilotId]);

  useEffect(() => {
    loadPilotDetails();
  }, [loadPilotDetails]);

  // Handle Transition
  const handleTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pilot) return;
    setTransitioning(true);
    setTransitionError(null);
    try {
      const updated = await transitionPilot(api, pilot.id, targetStatus, transitionNotes);
      setPilot(updated);
      setIsTransitionModalOpen(false);
      setTransitionNotes("");
      await loadPilotDetails();
    } catch (err: unknown) {
      console.error("Transition failed:", err);
      setTransitionError("فشل الانتقال إلى الحالة المطلوبة. تأكد من استيفاء المتطلبات وعدم وجود عوائق حرجة مفتوحة.");
    } finally {
      setTransitioning(false);
    }
  };

  // Handle Add Blocker
  const handleAddBlocker = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pilot || !blockerTitle.trim()) return;
    setSavingBlocker(true);
    try {
      await createPilotBlocker(api, pilot.id, {
        blocker_code: blockerCode.trim() || `BLK_${Date.now()}`,
        title_ar: blockerTitle.trim(),
        severity: blockerSeverity,
        owner_role: blockerOwner,
        resolution_notes: blockerNotes,
      });
      setIsBlockerModalOpen(false);
      setBlockerCode("");
      setBlockerTitle("");
      setBlockerNotes("");
      await loadPilotDetails();
    } catch (err) {
      console.error("Failed to create blocker:", err);
    } finally {
      setSavingBlocker(false);
    }
  };

  // Handle Resolve Blocker
  const handleResolveBlocker = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pilot || !resolveBlockerTarget) return;
    setResolvingBlocker(true);
    try {
      await updatePilotBlocker(api, pilot.id, resolveBlockerTarget.id, {
        status: "RESOLVED",
        resolution_notes: resolutionNotes.trim(),
      });
      setResolveBlockerTarget(null);
      setResolutionNotes("");
      await loadPilotDetails();
    } catch (err) {
      console.error("Failed to resolve blocker:", err);
    } finally {
      setResolvingBlocker(false);
    }
  };

  // Handle Update Requirement
  const handleUpdateRequirement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pilot || !editingRequirement) return;
    setUpdatingReq(true);
    try {
      await updatePilotRequirement(api, pilot.id, editingRequirement.requirement_key, {
        status: reqStatus,
        secret_ref_name: reqSecretRef.trim() || null,
        notes: reqNotes.trim(),
        validated_by: "فريق منصة مرشدي",
      });
      setEditingRequirement(null);
      await loadPilotDetails();
    } catch (err) {
      console.error("Failed to update requirement:", err);
    } finally {
      setUpdatingReq(false);
    }
  };

  // Handle Update Check
  const handleUpdateCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pilot || !editingCheck) return;
    setUpdatingCheck(true);
    try {
      await updatePilotAcceptanceCheck(api, pilot.id, editingCheck.check_key, {
        status: checkStatus,
        evidence_ref: checkEvidence.trim(),
        notes: checkNotes.trim(),
      });
      setEditingCheck(null);
      await loadPilotDetails();
    } catch (err) {
      console.error("Failed to update check:", err);
    } finally {
      setUpdatingCheck(false);
    }
  };

  // Run Automated Checks
  const handleRunAutomatedChecks = async () => {
    if (!pilot) return;
    setRunningAutomated(true);
    try {
      await runAutomatedAcceptance(api, pilot.id);
      await loadPilotDetails();
    } catch (err) {
      console.error("Failed to run automated checks:", err);
    } finally {
      setRunningAutomated(false);
    }
  };

  // Handle Record Signoff
  const handleRecordSignoff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pilot || !signeeName.trim()) return;
    setSavingSignoff(true);
    try {
      await recordPilotSignoff(api, pilot.id, {
        signoff_role: signoffRole,
        signee_name: signeeName.trim(),
        signee_role: signeeTitle.trim(),
        status: signoffDecision,
        decision_notes: signoffNotes.trim(),
      });
      setIsSignoffModalOpen(false);
      setSigneeName("");
      setSigneeTitle("");
      setSignoffNotes("");
      await loadPilotDetails();
    } catch (err) {
      console.error("Failed to record signoff:", err);
    } finally {
      setSavingSignoff(false);
    }
  };

  // Handle Add Stakeholder
  const handleAddStakeholder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pilot || !stakeholderName.trim() || !stakeholderEmail.trim()) return;
    setSavingStakeholder(true);
    try {
      await addPilotStakeholder(api, pilot.id, {
        role: stakeholderRole,
        name: stakeholderName.trim(),
        email: stakeholderEmail.trim(),
        title: stakeholderTitle.trim(),
        phone: stakeholderPhone.trim(),
      });
      setIsStakeholderModalOpen(false);
      setStakeholderName("");
      setStakeholderEmail("");
      setStakeholderTitle("");
      setStakeholderPhone("");
      await loadPilotDetails();
    } catch (err) {
      console.error("Failed to add stakeholder:", err);
    } finally {
      setSavingStakeholder(false);
    }
  };

  // Handle Delete Stakeholder
  const handleDeleteStakeholder = async (stkId: string) => {
    if (!pilot) return;
    try {
      await deletePilotStakeholder(api, pilot.id, stkId);
      await loadPilotDetails();
    } catch (err) {
      console.error("Failed to delete stakeholder:", err);
    }
  };

  // Handle Update Scope
  const handleSaveScope = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pilot) return;
    setSavingScope(true);
    try {
      await updatePilot(api, pilot.id, {
        cohort_scope: {
          faculties: scopeFaculties ? scopeFaculties.split(",").map((s) => s.trim()) : [],
          majors: scopeMajors ? scopeMajors.split(",").map((s) => s.trim()) : [],
          academic_plans: pilot.cohort_scope?.academic_plans || [],
          target_terms: pilot.cohort_scope?.target_terms || [],
          estimated_student_count: scopeStudents,
          scope_notes: scopeNotes.trim(),
        },
      });
      await loadPilotDetails();
    } catch (err) {
      console.error("Failed to update scope:", err);
    } finally {
      setSavingScope(false);
    }
  };

  // Load and show report
  const handleViewReport = async () => {
    if (!pilot) return;
    setLoadingReport(true);
    setIsReportModalOpen(true);
    try {
      const rep = await getPilotReport(api, pilot.id);
      setPilotReport(rep);
    } catch (err) {
      console.error("Failed to load report:", err);
    } finally {
      setLoadingReport(false);
    }
  };

  // Metrics
  const openBlockers = useMemo(() => blockers.filter((b) => b.status === "OPEN" || b.status === "IN_PROGRESS"), [blockers]);
  const sev1Blockers = useMemo(() => openBlockers.filter((b) => b.severity === "SEV1"), [openBlockers]);
  const validatedReqs = useMemo(() => requirements.filter((r) => r.status === "VALIDATED"), [requirements]);
  const passedChecks = useMemo(() => acceptanceChecks.filter((c) => c.status === "PASS"), [acceptanceChecks]);

  if (loading) {
    return (
      <div className="p-8 space-y-6" dir="rtl">
        <div className="rounded-2xl border border-border bg-surface p-12 text-center text-muted">
          <RefreshCw className="mx-auto size-8 animate-spin text-amber-400 mb-3" />
          <p>جارٍ تحميل بيانات مسار الإطلاق التجريبي...</p>
        </div>
      </div>
    );
  }

  if (error || !pilot) {
    return (
      <div className="p-8 space-y-6" dir="rtl">
        <div className="rounded-2xl border border-rose-500/25 bg-rose-500/10 p-6 text-center text-rose-300">
          <AlertOctagon className="mx-auto size-10 mb-2" />
          <p className="text-base font-bold">{error || "المشروع غير موجود"}</p>
          <Link
            href="/institutional/pilots"
            className="mt-4 inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-foreground hover:bg-white/5"
          >
            <ArrowRight className="size-4" />
            <span>العودة لقائمة مشاريع الإطلاق</span>
          </Link>
        </div>
      </div>
    );
  }

  const statusMeta = STATUS_LABELS[pilot.status] || {
    label: pilot.status,
    bg: "bg-slate-500/10",
    text: "text-slate-300",
    border: "border-slate-500/20",
  };
  const isReadOnly = pilot.mode === "READ_ONLY_PILOT";

  return (
    <div className="p-4 lg:p-8 space-y-6" dir="rtl">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted mb-2">
            <Link href="/institutional/pilots" className="hover:text-foreground transition-colors">
              مشاريع الإطلاق
            </Link>
            <span>/</span>
            <span className="text-foreground font-medium">{pilot.pilot_name}</span>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold text-foreground">{pilot.pilot_name}</h1>
            <span
              className={`inline-flex items-center rounded-full border px-3 py-0.5 text-xs font-semibold ${statusMeta.bg} ${statusMeta.text} ${statusMeta.border}`}
            >
              {statusMeta.label}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-3 py-0.5 text-xs font-medium ${
                isReadOnly
                  ? "border-sky-500/25 bg-sky-500/10 text-sky-300"
                  : "border-amber-500/25 bg-amber-500/10 text-amber-300"
              }`}
            >
              {isReadOnly ? <Lock className="size-3" /> : <Zap className="size-3" />}
              {isReadOnly ? "قراءة فقط (آمن)" : "كتابة مفعلة"}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setIsTransitionModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500 px-3.5 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors shadow-sm"
          >
            <Rocket className="size-4" />
            <span>تحديث مسار الحالة</span>
          </button>

          <button
            onClick={handleViewReport}
            className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3.5 py-2 text-xs font-semibold text-foreground hover:bg-white/5 transition-colors"
          >
            <FileCheck className="size-4 text-emerald-400" />
            <span>تقرير القبول المؤسسي</span>
          </button>

          <button
            onClick={loadPilotDetails}
            className="rounded-xl border border-border bg-surface p-2 text-muted hover:text-foreground transition-colors"
            title="تحديث البيانات"
          >
            <RefreshCw className="size-4" />
          </button>
        </div>
      </div>

      {/* KPI Highlights Ribbon */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="flex items-center justify-between text-muted text-xs">
            <span>درجة الجاهزية الفنية</span>
            <Activity className="size-4 text-amber-400" />
          </div>
          <div className="mt-2 text-xl font-bold text-foreground">
            {summary?.technical_readiness_score || "N/A"}
          </div>
          <p className="mt-1 text-[10px] text-muted">استيفاء المتطلبات الأساسية</p>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="flex items-center justify-between text-muted text-xs">
            <span>المتطلبات المكتملة</span>
            <CheckCircle2 className="size-4 text-sky-400" />
          </div>
          <div className="mt-2 text-xl font-bold text-sky-300">
            {validatedReqs.length} / {requirements.length}
          </div>
          <p className="mt-1 text-[10px] text-muted">
            {requirements.length > 0
              ? `${Math.round((validatedReqs.length / requirements.length) * 100)}% تم التحقق`
              : "لا توجد متطلبات"}
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="flex items-center justify-between text-muted text-xs">
            <span>فحوصات القبول المجتازة</span>
            <ShieldCheck className="size-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-xl font-bold text-emerald-300">
            {passedChecks.length} / {acceptanceChecks.length}
          </div>
          <p className="mt-1 text-[10px] text-muted">
            {acceptanceChecks.length > 0
              ? `${Math.round((passedChecks.length / acceptanceChecks.length) * 100)}% اجتياز`
              : "لا توجد فحوصات"}
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="flex items-center justify-between text-muted text-xs">
            <span>العوائق المفتوحة</span>
            <AlertTriangle className="size-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-foreground">{openBlockers.length}</span>
            {sev1Blockers.length > 0 && (
              <span className="text-xs font-semibold text-rose-400">({sev1Blockers.length} حرج)</span>
            )}
          </div>
          <p className="mt-1 text-[10px] text-muted">
            {sev1Blockers.length > 0 ? "يمنع الانتقال للمراحل المتقدمة" : "لا توجد عوائق حرجة"}
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="flex items-center justify-between text-muted text-xs">
            <span>بوابة تفعيل الكتابة</span>
            <Lock className="size-4 text-muted" />
          </div>
          <div className="mt-2 text-xl font-bold">
            {writeEnablement?.can_enable_write ? (
              <span className="text-emerald-400">مسموح</span>
            ) : (
              <span className="text-rose-400">مغلق (12 معياراً)</span>
            )}
          </div>
          <p className="mt-1 text-[10px] text-muted">
            {writeEnablement?.overall_status === "PASS" ? "اجتاز كافة الشروط" : "شروط أمنية غير مستوفاة"}
          </p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex gap-2 overflow-x-auto border-b border-border pb-1">
        {[
          { id: "overview", label: "مسار الحالة والنظرة العامة", icon: Rocket },
          { id: "scope", label: "نطاق العينة (Scope)", icon: Users },
          { id: "requirements", label: `المتطلبات التقنية (${requirements.length})`, icon: Layers },
          { id: "questionnaires", label: "الاستبيانات الفنية والأمنية", icon: FileText },
          {
            id: "blockers",
            label: `العوائق (${openBlockers.length})`,
            icon: AlertTriangle,
            badge: sev1Blockers.length > 0 ? "SEV1" : undefined,
          },
          { id: "acceptance", label: `فحوصات القبول (${passedChecks.length}/${acceptanceChecks.length})`, icon: ShieldCheck },
          { id: "write_enablement", label: "بوابة الكتابة (12 معياراً)", icon: Lock },
          { id: "signoffs", label: `التوقيعات الرسمية (${signoffs.length})`, icon: UserCheck },
          { id: "stakeholders", label: `المعنيون (${stakeholders.length})`, icon: Users },
          { id: "activity", label: "سجل التدقيق", icon: Activity },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabId)}
              className={`flex shrink-0 items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold transition-colors ${
                active
                  ? "border border-amber-500/30 bg-amber-500/10 text-amber-200"
                  : "text-muted hover:bg-white/5 hover:text-foreground"
              }`}
            >
              <Icon className="size-4" />
              <span>{tab.label}</span>
              {tab.badge && (
                <span className="rounded-full bg-rose-500/20 px-1.5 py-0.2 text-[10px] font-bold text-rose-300">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB CONTENT */}

      {/* TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Lifecycle Stages Visual Stepper */}
          <div className="rounded-2xl border border-border bg-surface p-6">
            <h3 className="text-sm font-bold text-foreground mb-4">
              مسار دورة حياة الإطلاق التجريبي (19 مرحلة معيارية)
            </h3>
            <div className="grid gap-4 md:grid-cols-4">
              {LIFECYCLE_STAGES.map((stg, idx) => (
                <div key={idx} className="rounded-xl border border-border/80 bg-background/50 p-3 space-y-2">
                  <span className="text-xs font-semibold text-amber-300 block">{stg.stage}</span>
                  <div className="space-y-1.5">
                    {stg.statuses.map((st) => {
                      const isCurrent = pilot.status === st;
                      const meta = STATUS_LABELS[st];
                      return (
                        <div
                          key={st}
                          className={`flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs transition-colors ${
                            isCurrent
                              ? "border border-amber-500/50 bg-amber-500/20 font-bold text-amber-200"
                              : "text-muted bg-surface/50"
                          }`}
                        >
                          <span className="truncate">{meta.label}</span>
                          {isCurrent && <Rocket className="size-3.5 text-amber-400 shrink-0" />}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Summary Cards */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-border bg-surface p-5 space-y-3">
              <h3 className="font-bold text-foreground text-sm flex items-center gap-2">
                <Building2 className="size-4 text-amber-400" />
                <span>بيانات الجامعة وبيئة الربط</span>
              </h3>
              <div className="space-y-2 text-xs text-muted">
                <div className="flex justify-between border-b border-border/40 pb-2">
                  <span>اسم الجامعة الرسمي:</span>
                  <span className="font-medium text-foreground">
                    {pilot.discovery_intake?.university_name_official || "غير محدد"}
                  </span>
                </div>
                <div className="flex justify-between border-b border-border/40 pb-2">
                  <span>مزود نظام الـ SIS:</span>
                  <span className="font-medium text-foreground">
                    {pilot.discovery_intake?.sis_vendor || "غير محدد"}
                  </span>
                </div>
                <div className="flex justify-between border-b border-border/40 pb-2">
                  <span>بروتوكول الهوية (SSO):</span>
                  <span className="font-medium text-foreground">
                    {pilot.discovery_intake?.identity_protocol || "OIDC / SAML"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>الجدول الزمني للإطلاق:</span>
                  <span className="font-medium text-foreground">
                    {pilot.target_start_date || "—"} إلى {pilot.target_end_date || "—"}
                  </span>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-surface p-5 space-y-3">
              <h3 className="font-bold text-foreground text-sm flex items-center gap-2">
                <Users className="size-4 text-amber-400" />
                <span>نطاق العينة التجريبية (Cohort Scope)</span>
              </h3>
              <div className="space-y-2 text-xs text-muted">
                <div className="flex justify-between border-b border-border/40 pb-2">
                  <span>عدد الطلبة المستهدفين:</span>
                  <span className="font-medium text-foreground">
                    {pilot.cohort_scope?.estimated_student_count || 0} طالب
                  </span>
                </div>
                <div className="flex justify-between border-b border-border/40 pb-2">
                  <span>الكليات المشمولة:</span>
                  <span className="font-medium text-foreground">
                    {pilot.cohort_scope?.faculties?.length > 0
                      ? pilot.cohort_scope.faculties.join("، ")
                      : "كافة الكليات"}
                  </span>
                </div>
                <div className="flex justify-between border-b border-border/40 pb-2">
                  <span>التخصصات المشمولة:</span>
                  <span className="font-medium text-foreground">
                    {pilot.cohort_scope?.majors?.length > 0
                      ? pilot.cohort_scope.majors.join("، ")
                      : "كافة التخصصات"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>ملاحظات النطاق:</span>
                  <span className="font-medium text-foreground">
                    {pilot.cohort_scope?.scope_notes || "لا توجد ملاحظات خاصة"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: COHORT SCOPE */}
      {activeTab === "scope" && (
        <div className="rounded-2xl border border-border bg-surface p-6 max-w-2xl">
          <h3 className="text-base font-bold text-foreground mb-1">تحديد نطاق الدفعة التجريبية (Cohort Scope)</h3>
          <p className="text-xs text-muted mb-4">
            وفق مبدأ &quot;البدء بعينة منضبطة&quot;، يحدد نطاق الإطلاق كليات وتخصصات معينة لضمان التحقق الدقيق قبل التوسع.
          </p>

          <form onSubmit={handleSaveScope} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-muted mb-1">الكليات المشمولة (مفصولة بفواصل)</label>
              <input
                type="text"
                value={scopeFaculties}
                onChange={(e) => setScopeFaculties(e.target.value)}
                placeholder="كلية تكنولوجيا المعلومات، كلية الهندسة"
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-muted mb-1">التخصصات المشمولة (مفصولة بفواصل)</label>
              <input
                type="text"
                value={scopeMajors}
                onChange={(e) => setScopeMajors(e.target.value)}
                placeholder="علم الحاسوب، هندسة البرمجيات، الأمن السيبراني"
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-muted mb-1">العدد التقديري للطلبة</label>
              <input
                type="number"
                min={1}
                max={50000}
                value={scopeStudents}
                onChange={(e) => setScopeStudents(parseInt(e.target.value) || 0)}
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-muted mb-1">ملاحظات وقيود النطاق</label>
              <textarea
                rows={3}
                value={scopeNotes}
                onChange={(e) => setScopeNotes(e.target.value)}
                placeholder="أي شروط خاصة بالعينة التجريبية..."
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
              />
            </div>

            <div className="flex justify-end pt-3">
              <button
                type="submit"
                disabled={savingScope}
                className="inline-flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors disabled:opacity-50"
              >
                {savingScope ? <RefreshCw className="size-3.5 animate-spin" /> : <CheckCircle2 className="size-3.5" />}
                <span>{savingScope ? "جارٍ الحفظ..." : "حفظ التعديلات"}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 3: REQUIREMENTS (21 ITEMS) */}
      {activeTab === "requirements" && (
        <div className="space-y-4">
          {/* Secret Ref Security Banner */}
          <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2">
            <ShieldCheck className="size-4 shrink-0 text-emerald-400" />
            <span>
              <strong>قاعدة أمان صارمة:</strong> لا يتم تخزين أي كلمات سر أو مفاتيح API في جدول المتطلبات. يتم فقط تسجيل اسم المتغير البيئي المرجعي (مثل `SIS_API_KEY_ENV`) الذي يُحفظ بأمان في الخادم المشفر.
            </span>
          </div>

          <div className="rounded-2xl border border-border bg-surface overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="font-bold text-foreground text-sm">
                  المتطلبات الفنية والتشغيلية المعتمدة ({requirements.length} متطلب)
                </h3>
                <p className="text-xs text-muted">
                  مقسمة عبر 7 فئات رئيسية تغطي الـ API، الهوية، الأمان، والبيئة التجريبية.
                </p>
              </div>
              <span className="text-xs text-sky-400 font-semibold">
                {validatedReqs.length} مكتمل من {requirements.length}
              </span>
            </div>

            <div className="divide-y divide-border/60">
              {requirements.map((req) => (
                <div key={req.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-white/[0.02]">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-foreground">{req.title_ar}</span>
                      <span className="text-[11px] text-muted font-mono">{req.requirement_key}</span>
                      <span
                        className={`rounded-full px-2 py-0.2 text-[10px] font-bold ${
                          req.importance === "REQUIRED"
                            ? "bg-rose-500/10 text-rose-300 border border-rose-500/20"
                            : "bg-slate-500/10 text-slate-300"
                        }`}
                      >
                        {req.importance === "REQUIRED" ? "إلزامي" : "اختياري"}
                      </span>
                      <span className="rounded bg-background px-1.5 py-0.5 text-[10px] text-muted border border-border">
                        {req.category}
                      </span>
                    </div>
                    <p className="text-xs text-muted">{req.notes || "لا توجد ملاحظات مسجلة"}</p>
                    {req.secret_ref_name && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-amber-300 font-mono">
                        <Key className="size-3" /> مرجع المتغير: {req.secret_ref_name}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`rounded-xl px-2.5 py-1 text-xs font-semibold ${
                        req.status === "VALIDATED"
                          ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                          : req.status === "RECEIVED"
                          ? "bg-sky-500/15 text-sky-300 border border-sky-500/30"
                          : req.status === "REQUESTED"
                          ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                          : req.status === "REJECTED"
                          ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                          : "bg-slate-500/10 text-slate-300 border border-slate-500/20"
                      }`}
                    >
                      {req.status}
                    </span>

                    <button
                      onClick={() => {
                        setEditingRequirement(req);
                        setReqStatus(req.status);
                        setReqSecretRef(req.secret_ref_name || "");
                        setReqNotes(req.notes || "");
                      }}
                      className="rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-muted hover:text-foreground hover:bg-white/5 transition-colors"
                    >
                      تعديل
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: QUESTIONNAIRES */}
      {activeTab === "questionnaires" && (
        <div className="space-y-6">
          {/* Data Minimization Notice */}
          <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-200 space-y-2">
            <div className="flex items-center gap-2 font-bold text-sm">
              <Scale className="size-4" />
              <span>مبدأ الحد الأدنى من البيانات (Data Minimization):</span>
            </div>
            <p>
              يقتصر مرشدي حصريًا على البيانات الأكاديمية الضرورية لتوجيه الطالب وتسجيل المواد. يُحظر جمع أو تخزين البيانات المالية والرسوم، السجلات الطبية والصحية، السجلات المسلكية والتأديبية، أو أرقام الهوية الوطنية وجوازات السفر.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            {/* Technical Questionnaire View */}
            <div className="rounded-2xl border border-border bg-surface p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <h3 className="font-bold text-foreground text-sm flex items-center gap-2">
                  <FileText className="size-4 text-amber-400" />
                  <span>الاستبيان الفني (13 قسمًا تقنيًا)</span>
                </h3>
                <span className="text-xs text-muted font-mono">13 Sections (A-M)</span>
              </div>

              <div className="space-y-2.5 text-xs">
                {Object.entries(pilot.technical_questionnaire || {}).map(([key, val]) => (
                  <div key={key} className="rounded-xl border border-border/60 bg-background/50 p-2.5">
                    <span className="text-muted block text-[11px] font-mono">{key}</span>
                    <span className="font-medium text-foreground block mt-0.5">
                      {typeof val === "object" ? JSON.stringify(val) : String(val)}
                    </span>
                  </div>
                ))}
                {Object.keys(pilot.technical_questionnaire || {}).length === 0 && (
                  <p className="text-muted text-xs">تمت تهيئة الاستبيان بالقيم المعيارية التلقائية.</p>
                )}
              </div>
            </div>

            {/* Security Questionnaire View */}
            <div className="rounded-2xl border border-border bg-surface p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <h3 className="font-bold text-foreground text-sm flex items-center gap-2">
                  <ShieldCheck className="size-4 text-emerald-400" />
                  <span>الاستبيان الأمني (11 موضوعًا أمنيًا)</span>
                </h3>
                <span className="text-xs text-muted font-mono">11 Topics</span>
              </div>

              <div className="space-y-2.5 text-xs">
                {Object.entries(pilot.security_questionnaire || {}).map(([key, val]) => (
                  <div key={key} className="rounded-xl border border-border/60 bg-background/50 p-2.5">
                    <span className="text-muted block text-[11px] font-mono">{key}</span>
                    <span className="font-medium text-foreground block mt-0.5">
                      {typeof val === "object" ? JSON.stringify(val) : String(val)}
                    </span>
                  </div>
                ))}
                {Object.keys(pilot.security_questionnaire || {}).length === 0 && (
                  <p className="text-muted text-xs">تمت تهيئة الاستبيان الأمني بالضوابط القياسية.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: BLOCKERS */}
      {activeTab === "blockers" && (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-bold text-foreground text-sm">إدارة العوائق والمشاكل (Blockers & Escalations)</h3>
              <p className="text-xs text-muted">
                أي عائق بمستوى SEV1 يعطل التقدم تلقائيًا ويمنع الانتقال للمراحل المتقدمة حتى يتم حله وتوثيقه.
              </p>
            </div>
            <button
              onClick={() => setIsBlockerModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500 px-3.5 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors"
            >
              <Plus className="size-4" />
              <span>تسجيل عائق جديد</span>
            </button>
          </div>

          <div className="rounded-2xl border border-border bg-surface overflow-hidden">
            {blockers.length === 0 ? (
              <div className="p-8 text-center text-muted">
                <CheckCircle2 className="mx-auto size-8 text-emerald-400 mb-2" />
                <p className="text-sm font-semibold text-foreground">لا توجد أي عوائق مسجلة</p>
                <p className="text-xs text-muted mt-1">مسار الإطلاق يسير بسلاسة بدون معوقات.</p>
              </div>
            ) : (
              <div className="divide-y divide-border/60">
                {blockers.map((b) => (
                  <div key={b.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-full px-2 py-0.2 text-[10px] font-bold ${
                            b.severity === "SEV1"
                              ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                              : b.severity === "SEV2"
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              : "bg-slate-500/20 text-slate-300 border border-slate-500/30"
                          }`}
                        >
                          {b.severity}
                        </span>
                        <span className="text-xs font-bold text-foreground">{b.title_ar}</span>
                        <span className="text-[11px] text-muted font-mono">{b.blocker_code}</span>
                        <span className="text-[10px] text-muted">المسؤول: {b.owner_role}</span>
                      </div>
                      {b.resolution_notes && (
                        <p className="text-xs text-emerald-300 mt-1">
                          <strong>ملاحظات الحل:</strong> {b.resolution_notes}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`rounded-xl px-2.5 py-1 text-xs font-semibold ${
                          b.status === "RESOLVED"
                            ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                            : b.status === "OPEN"
                            ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                            : "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                        }`}
                      >
                        {b.status}
                      </span>

                      {b.status !== "RESOLVED" && b.status !== "WONT_FIX" && (
                        <button
                          onClick={() => {
                            setResolveBlockerTarget(b);
                            setResolutionNotes("");
                          }}
                          className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20 transition-colors"
                        >
                          إغلاق العائق
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 6: ACCEPTANCE CHECKS (21 ITEMS) */}
      {activeTab === "acceptance" && (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-bold text-foreground text-sm">
                فحوصات القبول الصارمة ({acceptanceChecks.length} فحصاً معيارياً)
              </h3>
              <p className="text-xs text-muted">
                وفق مبدأ Fail-Closed، أي فحص إلزامي غير مختبر أو راسب يعطل القبول النهائي للمشروع.
              </p>
            </div>
            <button
              onClick={handleRunAutomatedChecks}
              disabled={runningAutomated}
              className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500 px-3.5 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`size-3.5 ${runningAutomated ? "animate-spin" : ""}`} />
              <span>{runningAutomated ? "جارٍ الفحص الآلي..." : "تشغيل الفحوصات الآلية"}</span>
            </button>
          </div>

          <div className="rounded-2xl border border-border bg-surface overflow-hidden">
            <div className="divide-y divide-border/60">
              {acceptanceChecks.map((chk) => (
                <div key={chk.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-white/[0.02]">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-foreground">{chk.title_ar}</span>
                      <span className="text-[11px] text-muted font-mono">{chk.check_key}</span>
                      <span
                        className={`rounded-full px-2 py-0.2 text-[10px] font-bold ${
                          chk.importance === "REQUIRED"
                            ? "bg-rose-500/10 text-rose-300 border border-rose-500/20"
                            : "bg-slate-500/10 text-slate-300"
                        }`}
                      >
                        {chk.importance === "REQUIRED" ? "إلزامي" : "اختياري"}
                      </span>
                      <span className="rounded bg-background px-1.5 py-0.5 text-[10px] text-muted border border-border">
                        {chk.category}
                      </span>
                      {chk.is_automated && (
                        <span className="rounded bg-sky-500/10 text-sky-300 border border-sky-500/20 px-1.5 py-0.5 text-[10px]">
                          آلي
                        </span>
                      )}
                    </div>
                    {chk.evidence_ref && (
                      <p className="text-xs text-sky-300 font-mono">
                        <strong>الدليل المرجعي:</strong> {chk.evidence_ref}
                      </p>
                    )}
                    {chk.notes && <p className="text-xs text-muted">{chk.notes}</p>}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`rounded-xl px-2.5 py-1 text-xs font-semibold ${
                        chk.status === "PASS"
                          ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                          : chk.status === "FAIL"
                          ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                          : chk.status === "WARNING"
                          ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                          : "bg-slate-500/10 text-slate-300 border border-slate-500/20"
                      }`}
                    >
                      {chk.status}
                    </span>

                    <button
                      onClick={() => {
                        setEditingCheck(chk);
                        setCheckStatus(chk.status);
                        setCheckEvidence(chk.evidence_ref || "");
                        setCheckNotes(chk.notes || "");
                      }}
                      className="rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-muted hover:text-foreground hover:bg-white/5 transition-colors"
                    >
                      تسجيل النتيجة
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 7: WRITE ENABLEMENT GATE (12 CRITERIA) */}
      {activeTab === "write_enablement" && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-border bg-surface p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
              <div>
                <h3 className="font-bold text-foreground text-base">
                  بوابة تفعيل وضع الكتابة المباشرة (12 معياراً إلزامياً)
                </h3>
                <p className="text-xs text-muted mt-1">
                  تسمح الكتابة المباشرة لمرشدي بتسجيل أو تعديل مواد الطالب في نظام الجامعة SIS. تتطلب موافقة واجتياز 100% من المعايير.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-3 py-1 text-xs font-bold border ${
                    writeEnablement?.can_enable_write
                      ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-300"
                      : "border-rose-500/30 bg-rose-500/15 text-rose-300"
                  }`}
                >
                  {writeEnablement?.can_enable_write ? "مسموح بالانتقال لوضع الكتابة" : "غير مسموح - شروط غير مستوفاة"}
                </span>
              </div>
            </div>

            <p className="text-xs text-muted mt-3">{writeEnablement?.summary_ar}</p>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {writeEnablement?.checks.map((chk) => (
                <div
                  key={chk.check_key}
                  className="rounded-xl border border-border/80 bg-background/50 p-3.5 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-foreground">{chk.title_ar}</span>
                    <span
                      className={`rounded-full px-2 py-0.2 text-[10px] font-bold ${
                        chk.status === "PASS"
                          ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                          : "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                      }`}
                    >
                      {chk.status}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted">{chk.details}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 8: SIGNOFFS */}
      {activeTab === "signoffs" && (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-bold text-foreground text-sm">التوقيعات والاعتمادات الرسمية (Formal Sign-Offs)</h3>
              <p className="text-xs text-muted">
                تتطلب المرحلة النهائية اعتماد مسؤولي الجامعة الفنيين والأكاديميين بالإضافة لفريق منصة مرشدي.
              </p>
            </div>
            <button
              onClick={() => setIsSignoffModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500 px-3.5 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors"
            >
              <UserCheck className="size-4" />
              <span>تسجيل اعتماد جديد</span>
            </button>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {[
              { role: "TECHNICAL_SIGN_OFF", title: "الاعتماد الفني لمدير الـ IT" },
              { role: "ACADEMIC_VALIDATION_SIGN_OFF", title: "الاعتماد الأكاديمي للعمادة والمسجل" },
              { role: "PILOT_SPONSOR_FINAL_SIGN_OFF", title: "اعتماد راعي المشروع في الجامعة" },
              { role: "MORSHIDI_PLATFORM_SIGN_OFF", title: "اعتماد فريق منصة مرشدي" },
            ].map((slot) => {
              const sign = signoffs.find((s) => s.signoff_role === slot.role);
              return (
                <div key={slot.role} className="rounded-2xl border border-border bg-surface p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-foreground text-xs">{slot.title}</h4>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                        sign?.status === "APPROVED"
                          ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                          : sign?.status === "REJECTED"
                          ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                          : "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                      }`}
                    >
                      {sign?.status || "PENDING (معلق)"}
                    </span>
                  </div>

                  {sign ? (
                    <div className="space-y-1.5 text-xs text-muted border-t border-border/50 pt-2">
                      <p>
                        <strong>الموقّع:</strong> {sign.signee_name} ({sign.signee_role})
                      </p>
                      <p>
                        <strong>التاريخ:</strong> {new Date(sign.created_at).toLocaleDateString("ar-EG")}
                      </p>
                      {sign.decision_notes && (
                        <p>
                          <strong>ملاحظات القرار:</strong> {sign.decision_notes}
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-muted border-t border-border/50 pt-2">
                      بانتظار اكتمال المتطلبات وفحوصات القبول لتسجيل الاعتماد الرسمي.
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 9: STAKEHOLDERS */}
      {activeTab === "stakeholders" && (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-bold text-foreground text-sm">فريق العمل والمعنيون (Project Stakeholders)</h3>
              <p className="text-xs text-muted">قائمة جهات الاتصال وفرق العمل المشتركة في الجامعة ومنصة مرشدي.</p>
            </div>
            <button
              onClick={() => setIsStakeholderModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500 px-3.5 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors"
            >
              <Plus className="size-4" />
              <span>إضافة عضو جديد</span>
            </button>
          </div>

          <div className="rounded-2xl border border-border bg-surface overflow-hidden">
            {stakeholders.length === 0 ? (
              <div className="p-8 text-center text-muted">
                <Users className="mx-auto size-8 text-muted/50 mb-2" />
                <p className="text-sm font-semibold text-foreground">لا يوجد معنيون مسجلون حالياً</p>
                <p className="text-xs text-muted mt-1">أضف أعضاء فريق الـ IT والمسجل لتسهيل التواصل.</p>
              </div>
            ) : (
              <div className="divide-y divide-border/60">
                {stakeholders.map((s) => (
                  <div key={s.id} className="p-4 flex items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-foreground text-xs">{s.name}</span>
                        <span className="rounded bg-background px-2 py-0.5 text-[10px] text-muted border border-border">
                          {s.role}
                        </span>
                        {s.title && <span className="text-[11px] text-muted">({s.title})</span>}
                      </div>
                      <p className="text-xs text-muted font-mono">{s.email} {s.phone ? `| ${s.phone}` : ""}</p>
                    </div>

                    <button
                      onClick={() => handleDeleteStakeholder(s.id)}
                      className="p-1.5 text-muted hover:text-rose-400 transition-colors rounded-lg hover:bg-white/5"
                      title="حذف"
                    >
                      <X className="size-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 10: ACTIVITY AUDIT */}
      {activeTab === "activity" && (
        <div className="rounded-2xl border border-border bg-surface p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <h3 className="font-bold text-foreground text-sm flex items-center gap-2">
              <Activity className="size-4 text-amber-400" />
              <span>سجل التدقيق المؤسسي والعمليات (Audit Trail)</span>
            </h3>
            <span className="text-xs text-muted">{activity.length} عملية مسجلة</span>
          </div>

          <div className="divide-y divide-border/50">
            {activity.map((act) => (
              <div key={act.id} className="py-3 flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs">
                <div>
                  <span className="font-semibold text-foreground">{act.action}</span>
                  <span className="text-muted block mt-0.5">بواسطة: {act.actor_email}</span>
                </div>
                <span className="text-muted text-[11px] font-mono">
                  {new Date(act.created_at).toLocaleString("ar-EG")}
                </span>
              </div>
            ))}
            {activity.length === 0 && (
              <p className="py-4 text-center text-muted text-xs">لا توجد عمليات تدقيق مسجلة حتى الآن.</p>
            )}
          </div>
        </div>
      )}

      {/* MODAL 1: STATUS TRANSITION */}
      {isTransitionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-4 my-8" dir="rtl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Rocket className="size-5 text-amber-400" />
                <h3 className="font-bold text-foreground text-base">تحديث مسار حالة المشروع</h3>
              </div>
              <button onClick={() => setIsTransitionModalOpen(false)} className="rounded-lg p-1 text-muted hover:text-foreground">
                <X className="size-5" />
              </button>
            </div>

            {transitionError && (
              <div className="rounded-xl border border-rose-500/25 bg-rose-500/10 p-3 text-xs text-rose-300">
                {transitionError}
              </div>
            )}

            <form onSubmit={handleTransition} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">الحالة الحالية:</label>
                <div className="rounded-xl border border-border bg-background px-3 py-2 text-xs font-bold text-foreground">
                  {STATUS_LABELS[pilot.status]?.label} ({pilot.status})
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">الحالة المستهدفة *</label>
                <select
                  value={targetStatus}
                  onChange={(e) => setTargetStatus(e.target.value as PilotStatus)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                >
                  {Object.entries(STATUS_LABELS).map(([k, meta]) => (
                    <option key={k} value={k}>
                      {meta.label} ({k})
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-[11px] text-muted">
                  ملاحظة: محرك الحالة يرفض القفزات غير المنطقية ويلزم بحل العوائق الحرجة (SEV1).
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">ملاحظات وسبب الانتقال</label>
                <textarea
                  rows={3}
                  value={transitionNotes}
                  onChange={(e) => setTransitionNotes(e.target.value)}
                  placeholder="توثيق مبررات الانتقال والتحقق الميداني..."
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setIsTransitionModalOpen(false)}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-muted hover:text-foreground"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  disabled={transitioning}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors disabled:opacity-50"
                >
                  {transitioning ? <RefreshCw className="size-3.5 animate-spin" /> : <Rocket className="size-3.5" />}
                  <span>{transitioning ? "جارٍ التحديث..." : "تأكيد الانتقال"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: ADD BLOCKER */}
      {isBlockerModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-4 my-8" dir="rtl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="size-5 text-amber-400" />
                <h3 className="font-bold text-foreground text-base">تسجيل عائق فني أو تشغيلي (Blocker)</h3>
              </div>
              <button onClick={() => setIsBlockerModalOpen(false)} className="rounded-lg p-1 text-muted hover:text-foreground">
                <X className="size-5" />
              </button>
            </div>

            <form onSubmit={handleAddBlocker} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">عنوان العائق بالعربية *</label>
                <input
                  type="text"
                  required
                  value={blockerTitle}
                  onChange={(e) => setBlockerTitle(e.target.value)}
                  placeholder="مثال: تعذر الوصول إلى بيئة الـ Sandbox الخاصة بالجامعة"
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">مستوى الأهمية (Severity) *</label>
                  <select
                    value={blockerSeverity}
                    onChange={(e) => setBlockerSeverity(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                  >
                    <option value="SEV1">SEV1 (حرج يعطل الإطلاق فوراً)</option>
                    <option value="SEV2">SEV2 (عالٍ يتطلب حل عاجل)</option>
                    <option value="SEV3">SEV3 (متوسط)</option>
                    <option value="SEV4">SEV4 (منخفض / تحسين)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">الجهة المسؤولة *</label>
                  <select
                    value={blockerOwner}
                    onChange={(e) => setBlockerOwner(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                  >
                    <option value="UNIVERSITY_IT">فريق تقنية المعلومات بالجامعة (IT)</option>
                    <option value="UNIVERSITY_REGISTRAR">المسجل العام والعمادة الأكاديمية</option>
                    <option value="MORSHIDI_PLATFORM">فريق منصة مرشدي</option>
                    <option value="SIS_VENDOR">الشركة المزودة لنظام الـ SIS</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">تفاصيل وملاحظات العائق</label>
                <textarea
                  rows={3}
                  value={blockerNotes}
                  onChange={(e) => setBlockerNotes(e.target.value)}
                  placeholder="توضيح الخطوات المطلوب اتخاذها لحل المشكلة..."
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setIsBlockerModalOpen(false)}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-muted hover:text-foreground"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  disabled={savingBlocker}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors disabled:opacity-50"
                >
                  {savingBlocker ? <RefreshCw className="size-3.5 animate-spin" /> : <Plus className="size-3.5" />}
                  <span>{savingBlocker ? "جارٍ الحفظ..." : "تسجيل العائق"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: RESOLVE BLOCKER */}
      {resolveBlockerTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-4 my-8" dir="rtl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="size-5 text-emerald-400" />
                <h3 className="font-bold text-foreground text-base">إغلاق وحل العائق</h3>
              </div>
              <button onClick={() => setResolveBlockerTarget(null)} className="rounded-lg p-1 text-muted hover:text-foreground">
                <X className="size-5" />
              </button>
            </div>

            <form onSubmit={handleResolveBlocker} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">العائق المستهدف:</label>
                <div className="rounded-xl border border-border bg-background px-3 py-2 text-xs font-bold text-foreground">
                  {resolveBlockerTarget.title_ar} ({resolveBlockerTarget.severity})
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">ملاحظات وإثبات الحل *</label>
                <textarea
                  rows={3}
                  required
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="كيف تم حل العائق؟ وما هو الإجراء المتخذ للتأكد من عدم تكراره؟"
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setResolveBlockerTarget(null)}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-muted hover:text-foreground"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  disabled={resolvingBlocker}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500 px-4 py-2 text-xs font-semibold text-stone-950 hover:bg-emerald-400 transition-colors disabled:opacity-50"
                >
                  {resolvingBlocker ? <RefreshCw className="size-3.5 animate-spin" /> : <CheckCircle2 className="size-3.5" />}
                  <span>{resolvingBlocker ? "جارٍ الإغلاق..." : "تأكيد الحل والإغلاق"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: EDIT REQUIREMENT */}
      {editingRequirement && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-4 my-8" dir="rtl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Layers className="size-5 text-amber-400" />
                <h3 className="font-bold text-foreground text-base">تحديث حالة المتطلب التقني</h3>
              </div>
              <button onClick={() => setEditingRequirement(null)} className="rounded-lg p-1 text-muted hover:text-foreground">
                <X className="size-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateRequirement} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">المتطلب:</label>
                <div className="rounded-xl border border-border bg-background px-3 py-2 text-xs font-bold text-foreground">
                  {editingRequirement.title_ar} ({editingRequirement.requirement_key})
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">الحالة *</label>
                <select
                  value={reqStatus}
                  onChange={(e) => setReqStatus(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                >
                  <option value="NOT_REQUESTED">NOT_REQUESTED (لم يُطلب بعد)</option>
                  <option value="REQUESTED">REQUESTED (طُلب من الجامعة)</option>
                  <option value="RECEIVED">RECEIVED (تم استلامه)</option>
                  <option value="VALIDATED">VALIDATED (تم التحقق واعتماده)</option>
                  <option value="REJECTED">REJECTED (مرفوض / غير صالح)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">
                  اسم المتغير البيئي المرجعي (Secret Reference Name)
                </label>
                <input
                  type="text"
                  value={reqSecretRef}
                  onChange={(e) => setReqSecretRef(e.target.value)}
                  placeholder="مثال: SIS_API_PROD_KEY"
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground font-mono focus:border-amber-500 focus:outline-none"
                />
                <p className="mt-1 text-[10px] text-amber-400">
                  تحذير: لا تدخل القيمة السرية إطلاقاً هنا! أدخل اسم المفتاح فقط.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">ملاحظات التحقق</label>
                <textarea
                  rows={3}
                  value={reqNotes}
                  onChange={(e) => setReqNotes(e.target.value)}
                  placeholder="ملاحظات حول طريقة التحقق أو المتطلبات المتبقية..."
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setEditingRequirement(null)}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-muted hover:text-foreground"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  disabled={updatingReq}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors disabled:opacity-50"
                >
                  {updatingReq ? <RefreshCw className="size-3.5 animate-spin" /> : <CheckCircle2 className="size-3.5" />}
                  <span>{updatingReq ? "جارٍ الحفظ..." : "حفظ التعديلات"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 5: EDIT ACCEPTANCE CHECK */}
      {editingCheck && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-4 my-8" dir="rtl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-5 text-emerald-400" />
                <h3 className="font-bold text-foreground text-base">تسجيل نتيجة فحص القبول</h3>
              </div>
              <button onClick={() => setEditingCheck(null)} className="rounded-lg p-1 text-muted hover:text-foreground">
                <X className="size-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateCheck} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">الفحص:</label>
                <div className="rounded-xl border border-border bg-background px-3 py-2 text-xs font-bold text-foreground">
                  {editingCheck.title_ar} ({editingCheck.check_key})
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">النتيجة *</label>
                <select
                  value={checkStatus}
                  onChange={(e) => setCheckStatus(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                >
                  <option value="PASS">PASS (ناجح ومعتمد)</option>
                  <option value="FAIL">FAIL (راسب / غير مستوفٍ)</option>
                  <option value="WARNING">WARNING (ناجح مع تنبيهات)</option>
                  <option value="NOT_TESTED">NOT_TESTED (لم يُختبر)</option>
                  <option value="NOT_APPLICABLE">NOT_APPLICABLE (غير منطبق)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">مرجع الدليل (Evidence Ref)</label>
                <input
                  type="text"
                  value={checkEvidence}
                  onChange={(e) => setCheckEvidence(e.target.value)}
                  placeholder="مثال: report_test_run_2026_04.pdf أو sync_job_id"
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground font-mono focus:border-amber-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">ملاحظات الفاحص</label>
                <textarea
                  rows={3}
                  value={checkNotes}
                  onChange={(e) => setCheckNotes(e.target.value)}
                  placeholder="شرح النتيجة والأدلة الداعمة..."
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setEditingCheck(null)}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-muted hover:text-foreground"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  disabled={updatingCheck}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors disabled:opacity-50"
                >
                  {updatingCheck ? <RefreshCw className="size-3.5 animate-spin" /> : <CheckCircle2 className="size-3.5" />}
                  <span>{updatingCheck ? "جارٍ الحفظ..." : "تسجيل النتيجة"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 6: RECORD SIGNOFF */}
      {isSignoffModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-4 my-8" dir="rtl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <UserCheck className="size-5 text-emerald-400" />
                <h3 className="font-bold text-foreground text-base">تسجيل اعتماد وتوقيع رسمي</h3>
              </div>
              <button onClick={() => setIsSignoffModalOpen(false)} className="rounded-lg p-1 text-muted hover:text-foreground">
                <X className="size-5" />
              </button>
            </div>

            <form onSubmit={handleRecordSignoff} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">صفة الاعتماد *</label>
                <select
                  value={signoffRole}
                  onChange={(e) => setSignoffRole(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                >
                  <option value="TECHNICAL_SIGN_OFF">الاعتماد الفني (مدير تكنولوجيا المعلومات)</option>
                  <option value="ACADEMIC_VALIDATION_SIGN_OFF">الاعتماد الأكاديمي (العميد / المسجل العام)</option>
                  <option value="PILOT_SPONSOR_FINAL_SIGN_OFF">اعتماد راعي المشروع بالجامعة</option>
                  <option value="MORSHIDI_PLATFORM_SIGN_OFF">اعتماد فريق منصة مرشدي</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">اسم الموقّع *</label>
                  <input
                    type="text"
                    required
                    value={signeeName}
                    onChange={(e) => setSigneeName(e.target.value)}
                    placeholder="د. أحمد الخالد"
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">المسمى الوظيفي</label>
                  <input
                    type="text"
                    value={signeeTitle}
                    onChange={(e) => setSigneeTitle(e.target.value)}
                    placeholder="مدير مركز الحاسوب"
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">القرار *</label>
                <select
                  value={signoffDecision}
                  onChange={(e) => setSignoffDecision(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                >
                  <option value="APPROVED">APPROVED (موافقة واعتماد رسمي)</option>
                  <option value="REJECTED">REJECTED (رفض الاعتماد)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">ملاحظات وتوصيات الاعتماد</label>
                <textarea
                  rows={3}
                  value={signoffNotes}
                  onChange={(e) => setSignoffNotes(e.target.value)}
                  placeholder="أي شروط أو توصيات خاصة بهذا الاعتماد..."
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setIsSignoffModalOpen(false)}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-muted hover:text-foreground"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  disabled={savingSignoff}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500 px-4 py-2 text-xs font-semibold text-stone-950 hover:bg-emerald-400 transition-colors disabled:opacity-50"
                >
                  {savingSignoff ? <RefreshCw className="size-3.5 animate-spin" /> : <CheckCircle2 className="size-3.5" />}
                  <span>{savingSignoff ? "جارٍ الحفظ..." : "تأكيد الاعتماد"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 7: ADD STAKEHOLDER */}
      {isStakeholderModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-4 my-8" dir="rtl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Users className="size-5 text-amber-400" />
                <h3 className="font-bold text-foreground text-base">إضافة عضو لفريق العمل المشترك</h3>
              </div>
              <button onClick={() => setIsStakeholderModalOpen(false)} className="rounded-lg p-1 text-muted hover:text-foreground">
                <X className="size-5" />
              </button>
            </div>

            <form onSubmit={handleAddStakeholder} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">الدور في المشروع *</label>
                <select
                  value={stakeholderRole}
                  onChange={(e) => setStakeholderRole(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-amber-500 focus:outline-none"
                >
                  <option value="PROJECT_LEAD">قائد المشروع المشترك (Project Lead)</option>
                  <option value="IT_DIRECTOR">مدير تكنولوجيا المعلومات (IT Director)</option>
                  <option value="SIS_ADMIN">مسؤول نظام الـ SIS (SIS Admin)</option>
                  <option value="REGISTRAR">المسجل العام (Registrar)</option>
                  <option value="SECURITY_OFFICER">مسؤول أمن المعلومات (CISO/Security)</option>
                  <option value="ACADEMIC_DEAN">عميد الكلية المعنية (Academic Dean)</option>
                  <option value="MORSHIDI_ENGINEER">مهندس منصة مرشدي</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">الاسم الكامل *</label>
                  <input
                    type="text"
                    required
                    value={stakeholderName}
                    onChange={(e) => setStakeholderName(e.target.value)}
                    placeholder="م. عمر يوسف"
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">المسمى الوظيفي</label>
                  <input
                    type="text"
                    value={stakeholderTitle}
                    onChange={(e) => setStakeholderTitle(e.target.value)}
                    placeholder="مهندس نظم قواعد البيانات"
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">البريد الإلكتروني الرسمي *</label>
                  <input
                    type="email"
                    required
                    value={stakeholderEmail}
                    onChange={(e) => setStakeholderEmail(e.target.value)}
                    placeholder="user@university.edu"
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">رقم الهاتف</label>
                  <input
                    type="tel"
                    value={stakeholderPhone}
                    onChange={(e) => setStakeholderPhone(e.target.value)}
                    placeholder="+962 79 000 0000"
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-amber-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setIsStakeholderModalOpen(false)}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-muted hover:text-foreground"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  disabled={savingStakeholder}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500 px-4 py-2 text-xs font-semibold text-stone-950 hover:bg-amber-400 transition-colors disabled:opacity-50"
                >
                  {savingStakeholder ? <RefreshCw className="size-3.5 animate-spin" /> : <Plus className="size-3.5" />}
                  <span>{savingStakeholder ? "جارٍ الإضافة..." : "إضافة العضو"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 8: PILOT FULL REPORT */}
      {isReportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-3xl rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-4 my-8 max-h-[90vh] overflow-y-auto" dir="rtl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <FileCheck className="size-5 text-emerald-400" />
                <h3 className="font-bold text-foreground text-lg">تقرير القبول المؤسسي المعتمد (Pilot Acceptance Report)</h3>
              </div>
              <button onClick={() => setIsReportModalOpen(false)} className="rounded-lg p-1 text-muted hover:text-foreground">
                <X className="size-5" />
              </button>
            </div>

            {loadingReport ? (
              <div className="p-8 text-center text-muted">
                <RefreshCw className="mx-auto size-8 animate-spin text-amber-400 mb-2" />
                <p className="text-xs">جارٍ توليد التقرير والتحقق من المعايير...</p>
              </div>
            ) : pilotReport ? (
              <div className="space-y-4 text-xs">
                {/* Recommendation Banner */}
                <div
                  className={`rounded-xl border p-4 flex items-center justify-between ${
                    pilotReport.final_recommendation === "ACCEPTED"
                      ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-200"
                      : pilotReport.final_recommendation === "ACCEPTED_WITH_WARNINGS"
                      ? "border-amber-500/30 bg-amber-500/15 text-amber-200"
                      : "border-rose-500/30 bg-rose-500/15 text-rose-200"
                  }`}
                >
                  <div>
                    <span className="font-bold text-sm block">التوصية النهائية:</span>
                    <span className="text-xs mt-0.5 block font-mono">{pilotReport.final_recommendation}</span>
                  </div>
                  <span className="text-[11px] font-mono">
                    تاريخ التوليد: {new Date(pilotReport.generated_at).toLocaleString("ar-EG")}
                  </span>
                </div>

                {/* Report Sections */}
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-border/80 bg-background/50 p-3 space-y-1.5">
                    <span className="font-bold text-foreground block">الجاهزية الفنية:</span>
                    <pre className="text-[11px] font-mono text-muted overflow-x-auto">
                      {JSON.stringify(pilotReport.technical_readiness, null, 2)}
                    </pre>
                  </div>

                  <div className="rounded-xl border border-border/80 bg-background/50 p-3 space-y-1.5">
                    <span className="font-bold text-foreground block">تغطية المطابقة الأكاديمية:</span>
                    <pre className="text-[11px] font-mono text-muted overflow-x-auto">
                      {JSON.stringify(pilotReport.mapping_coverage, null, 2)}
                    </pre>
                  </div>
                </div>

                <div className="rounded-xl border border-border/80 bg-background/50 p-3 space-y-1.5">
                  <span className="font-bold text-foreground block">نتائج فحوصات القبول:</span>
                  <pre className="text-[11px] font-mono text-muted overflow-x-auto">
                    {JSON.stringify(pilotReport.acceptance_results, null, 2)}
                  </pre>
                </div>

                <div className="rounded-xl border border-border/80 bg-background/50 p-3 space-y-1.5">
                  <span className="font-bold text-foreground block">
                    العوائق المفتوحة ({pilotReport.open_blockers?.length || 0}):
                  </span>
                  {pilotReport.open_blockers?.length === 0 ? (
                    <p className="text-emerald-300">لا توجد أي عوائق مفتوحة.</p>
                  ) : (
                    <div className="space-y-1">
                      {pilotReport.open_blockers?.map((b) => (
                        <p key={b.id} className="text-rose-300">
                          [{b.severity}] {b.title_ar} ({b.status})
                        </p>
                      ))}
                    </div>
                  )}
                </div>

                <div className="rounded-xl border border-border/80 bg-background/50 p-3 space-y-1.5">
                  <span className="font-bold text-foreground block">التوقيعات الرسمية المسجلة:</span>
                  {pilotReport.signoffs?.length === 0 ? (
                    <p className="text-muted">لم يتم تسجيل أي اعتماد بعد.</p>
                  ) : (
                    <div className="space-y-1">
                      {pilotReport.signoffs?.map((s) => (
                        <p key={s.id} className="text-foreground">
                          {s.signoff_role}: {s.signee_name} ({s.status})
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : null}

            <div className="flex justify-end border-t border-border pt-3">
              <button
                type="button"
                onClick={() => setIsReportModalOpen(false)}
                className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-foreground hover:bg-white/5"
              >
                إغلاق
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
