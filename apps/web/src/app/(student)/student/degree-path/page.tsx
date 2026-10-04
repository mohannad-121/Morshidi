"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/auth/auth-provider";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import { useCourseIdentities } from "@/lib/api/use-course-identities";
import { CourseDifficulty } from "@/components/academic/CourseDifficulty";
import { CourseIdentity } from "@/components/academic/CourseIdentity";
import { AcademicGraphExplanation } from "@/components/academic/AcademicGraphExplanation";
import type { AcademicExplanationGraph, AdaptiveCourseResponse, CreditTimelineResponse, CreditComparisonResponse,
  CreditTimelineRequest } from "@/lib/api/student-types";
import type {
  DegreePathOptionResponse,
  DegreePathRequest,
  DegreePathResponse,
  ModeledSemesterResponse,
  PlannedCourseEntryResponse,
} from "@/lib/api/student-types";
import {PathMap} from '@/components/ui/PathMap';
import {Button,Dial,FriendlyState,SegmentedControl} from '@/components/ui/DesignSystem';
import {label} from '@/lib/labels';
import {Compass,Printer} from 'lucide-react';
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { LoadingSkeletonCard } from "@/components/ui/LoadingSkeleton";
import { StatCard } from "@/components/ui/StatCard";
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  CoursesIcon,
  DegreePathIcon,
  InfoIcon,
  SparklesIcon,
} from "@/components/ui/Icons";

const PATH_STAGES = [
  "قراءة الخطة الدراسية والسجل الأكاديمي",
  "فحص المتطلبات السابقة والمواد المتبقية",
  "محاكاة المسارات الفصلية وترتيبها",
  "تجهيز نتيجة مسار التخرج",
] as const;

export default function DegreePathPage() {
  const auth = useAuth();
  const client = useAuthenticatedApi();
  const identities = useCourseIdentities(auth.isAuthenticated);

  // Constraints
  const [maxCreditsPerSemester, setMaxCreditsPerSemester] = useState<number>(15);
  const [maxSemestersAhead, setMaxSemestersAhead] = useState<number>(8);
  const [maxPaths, setMaxPaths] = useState<number>(2);
  const [regularLoad, setRegularLoad] = useState(15);
  const [summerEnabled, setSummerEnabled] = useState(false);
  const [summerLoad, setSummerLoad] = useState(6);
  const [graduationPace, setGraduationPace] = useState<"FASTEST" | "BALANCED" | "LOWER_LOAD">("BALANCED");
  const preferencesEdited = useRef(false);
  const comparisonRequestId = useRef(0);
  const [startYear, setStartYear] = useState(new Date().getFullYear());
  const [startTerm, setStartTerm] = useState<CreditTimelineRequest["start_term"]>("FIRST_SEMESTER");
  const [creditTimeline, setCreditTimeline] = useState<CreditTimelineResponse | null>(null);
  const [creditComparison, setCreditComparison] = useState<CreditComparisonResponse | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState(false);
  const [creditLoading, setCreditLoading] = useState(false);
  const [creditError, setCreditError] = useState<string | null>(null);

  // States
  const [result, setResult] = useState<DegreePathResponse | null>(null);
  const [adaptive, setAdaptive] = useState<AdaptiveCourseResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedPathIndex, setSelectedPathIndex] = useState<number>(0);
  const [graph, setGraph] = useState<AcademicExplanationGraph | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState(false);
  const lastGraphRequest = useRef<DegreePathRequest | null>(null);
  const graphRequestId = useRef(0);
  const requestId = useRef(0);

  useEffect(() => {
    if (!auth.isAuthenticated) return;
    let active = true;
    void new StudentApiService(client).getConversationPreferences().then((prefs) => {
      if (!active || preferencesEdited.current) return;
      if (!prefs || typeof prefs !== "object" || Array.isArray(prefs)) return;
      const regular = Number(prefs.regular_load);
      const summer = Number(prefs.summer_load);
      if (Number.isInteger(regular) && regular >= 3 && regular <= 30) setRegularLoad(regular);
      if (prefs.summer_enabled === "true" || prefs.summer_enabled === "false")
        setSummerEnabled(prefs.summer_enabled === "true");
      if (Number.isInteger(summer) && summer >= 3 && summer <= 9) setSummerLoad(summer);
      if (prefs.graduation_pace === "FASTEST" || prefs.graduation_pace === "BALANCED" || prefs.graduation_pace === "LOWER_LOAD")
        setGraduationPace(prefs.graduation_pace);
    }).catch(() => { /* Preferences are optional; no academic assumption is inferred. */ });
    return () => { active = false; };
  }, [auth.isAuthenticated, client]);

  const handleCreditTimeline = async (e: React.FormEvent) => {
    e.preventDefault(); setCreditLoading(true); setCreditError(null); setCreditTimeline(null);
    try {
      setCreditTimeline(await new StudentApiService(client).simulateCreditTimeline({
        regular_load: regularLoad, summer_enabled: summerEnabled,
        summer_load: summerEnabled ? summerLoad : 0,
        start_year: startYear, start_term: startTerm,
      }));
    } catch { setCreditError("تعذّر حساب المسار الائتماني. تأكد من الحمل والفصل المختارين."); }
    finally { setCreditLoading(false); }
  };

  const handleComparison = async () => {
    const currentId = ++comparisonRequestId.current;
    setComparisonLoading(true); setComparisonError(false); setCreditComparison(null);
    try {
      const comparison = await new StudentApiService(client).compareCreditTimelines({
        start_year: startYear, start_term: startTerm,
        preferred_regular_load: regularLoad,
        preferred_summer_enabled: summerEnabled,
        preferred_summer_load: summerEnabled ? summerLoad : undefined,
        graduation_pace: graduationPace,
      });
      if (currentId === comparisonRequestId.current) setCreditComparison(comparison);
    } catch { if (currentId === comparisonRequestId.current) setComparisonError(true); }
    finally { if (currentId === comparisonRequestId.current) setComparisonLoading(false); }
  };

  const loadGraph = async (request: DegreePathRequest) => {
    const currentId = ++graphRequestId.current;
    setGraphLoading(true);
    setGraphError(false);
    try {
      const nextGraph = await new StudentApiService(client).createDegreePathGraph(request);
      if (currentId === graphRequestId.current) setGraph(nextGraph);
    } catch {
      if (currentId === graphRequestId.current) setGraphError(true);
    } finally {
      if (currentId === graphRequestId.current) setGraphLoading(false);
    }
  };

  const handleGeneratePath = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    setErrorMessage(null);
    setResult(null);
    graphRequestId.current += 1;
    setGraph(null);
    setGraphError(false);
    const currentRequest = ++requestId.current;
    let timeoutSignal: AbortSignal | null = null;

    try {
      timeoutSignal = AbortSignal.timeout(60_000);
      const api = new StudentApiService(client);
      void api.getAdaptiveCourseIntelligence().then((intelligence) => {
        if (currentRequest === requestId.current) setAdaptive(intelligence);
      }).catch(() => { if (currentRequest === requestId.current) setAdaptive(null); });
      const req: DegreePathRequest = {
        max_credit_hours_per_semester: maxCreditsPerSemester,
        max_semesters_ahead: maxSemestersAhead,
        max_paths: maxPaths,
      };
      const data = await api.createDegreePaths(req, timeoutSignal);
      if (currentRequest !== requestId.current) return;
      setResult(data);
      setSelectedPathIndex(0);
      lastGraphRequest.current = req;
      void loadGraph(req);
    } catch {
      if (currentRequest !== requestId.current) return;
      setErrorMessage(timeoutSignal?.aborted
        ? "استغرق إنشاء مسار التخرج وقتًا أطول من المتوقع. حاول مرة أخرى."
        : "تعذر إنشاء مسار التخرج الآن. حاول مرة أخرى.");
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  };

  const selectedPath: DegreePathOptionResponse | null =
    result?.paths && result.paths.length > selectedPathIndex
      ? result.paths[selectedPathIndex]
      : null;


  return <div className="space-y-8 degree-page"><div className="page-heading"><span className="eyebrow">خطوة تلو خطوة</span><h1>مسار التخرج</h1></div>
    <form className="control-rail engraved" onSubmit={handleGeneratePath}>
      <label>ساعات الفصل <div className="range-value"><strong>{maxCreditsPerSemester}</strong><input aria-label="ساعات الفصل" type="range" min={6} max={21} value={maxCreditsPerSemester} onChange={e=>setMaxCreditsPerSemester(Number(e.target.value))}/></div></label>
      <label>عدد الفصول<select aria-label="عدد الفصول" value={maxSemestersAhead} onChange={e=>setMaxSemestersAhead(Number(e.target.value))}>{[4,6,8,10].map(n=><option key={n} value={n}>{n} فصول</option>)}</select></label>
      <label>المسارات<select aria-label="المسارات" value={maxPaths} onChange={e=>setMaxPaths(Number(e.target.value))}>{[1,2,3].map(n=><option key={n} value={n}>{n}</option>)}</select></label>
      <Button type="submit" disabled={loading}><Compass size={18}/>{loading?'جارٍ الرسم…':'ارسم المسار'}</Button>
    </form>
    {errorMessage&&<FriendlyState error onRetry={()=>void handleGeneratePath()}/>}
    {loading&&<LoadingSkeletonCard className="min-h-80"/>}
    {!loading&&selectedPath&&result?<><div className="flex items-center justify-between flex-wrap gap-4"><SegmentedControl value={String(selectedPathIndex)} onChange={v=>setSelectedPathIndex(Number(v))} options={result.paths.map((p,i)=>({value:String(i),label:`المسار ${p.rank} · ${p.semester_count} فصول`}))}/><button className="button-secondary" onClick={()=>window.print()}><Printer size={16}/>تصدير PDF</button></div>
      <div className="journey-kpis"><div className="engraved"><strong>{selectedPath.semester_count}</strong><span>فصول مخططة</span></div><div className="engraved"><strong>{selectedPath.total_planned_credits}</strong><span>ساعات مخططة</span></div><div className="engraved"><strong>{selectedPath.final_remaining_plan_credits}</strong><span>متبقية بعد المسار</span></div><div className="engraved"><Dial value={selectedPath.final_completed_plan_credits} max={selectedPath.final_completed_plan_credits+selectedPath.final_remaining_plan_credits} size={100} label="إنجاز متوقع"/></div></div>
      <PathMap key={selectedPath.rank} stations={selectedPath.semesters.map(sem=>({id:String(sem.semester_index),title:`الفصل ${sem.semester_index}`,hours:sem.plan_option.total_credit_hours,courses:sem.plan_option.courses.map(c=>({code:c.course_code,name:c.course_name_ar,hours:c.credit_hours}))}))}/>
      {selectedPath.status!=='COMPLETE'&&<p className="text-xs text-copper">المسار جزئي ضمن المعايير المختارة.</p>}
      <details className="engraved p-5"><summary>تفاصيل الاختيار</summary><AcademicGraphExplanation graph={graph} focusId={`degree-path:${selectedPath.rank}`} identities={identities} loading={graphLoading} error={graphError} onRetry={()=>{if(lastGraphRequest.current)void loadGraph(lastGraphRequest.current);}}/></details>
    </>:!loading&&!errorMessage&&<FriendlyState title="ارسم رحلتك"/>}
    <details className="engraved p-6"><summary className="flex items-center gap-3"><Compass size={18}/><h2 className="text-base">التقدير الزمني والمقارنة</h2></summary>
      <form className="control-rail mt-6" onChange={()=>{preferencesEdited.current=true;comparisonRequestId.current+=1;setComparisonLoading(false);setComparisonError(false);setCreditComparison(null);}} onSubmit={e=>void handleCreditTimeline(e)}>
        <label>ساعات الفصل<select aria-label="ساعات التقدير الزمني" value={regularLoad} onChange={e=>setRegularLoad(Number(e.target.value))}>{Array.from(new Set([12,15,18,regularLoad])).map(n=><option key={n} value={n}>{n}</option>)}</select></label>
        <label>سنة البداية<input aria-label="سنة البداية" type="number" min={2000} max={2200} value={startYear} onChange={e=>setStartYear(Number(e.target.value))}/></label>
        <label>فصل البداية<select aria-label="فصل البداية" value={startTerm} onChange={e=>setStartTerm(e.target.value as CreditTimelineRequest['start_term'])}><option value="FIRST_SEMESTER">الأول</option><option value="SECOND_SEMESTER">الثاني</option><option value="SUMMER">الصيفي</option></select></label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={summerEnabled} onChange={e=>setSummerEnabled(e.target.checked)}/>الصيفي</label>
        {summerEnabled&&<label>ساعات الصيفي<input aria-label="ساعات الصيفي" type="number" min={3} max={9} value={summerLoad} onChange={e=>setSummerLoad(Number(e.target.value))}/></label>}
        <label>وتيرة التخرج<select value={graduationPace} onChange={e=>setGraduationPace(e.target.value as typeof graduationPace)}><option value="FASTEST">الأسرع</option><option value="BALANCED">المتوازن</option><option value="LOWER_LOAD">الأخف</option></select></label>
        <Button type="submit" disabled={creditLoading}>{creditLoading?'جارٍ الحساب…':'احسب المدة'}</Button><button className="button-secondary" type="button" disabled={comparisonLoading} onClick={()=>void handleComparison()}>قارن المسارات</button>
      </form>
      {(creditLoading||comparisonLoading)&&<LoadingSkeletonCard/>}{(creditError||comparisonError)&&<FriendlyState error/>}
      {creditTimeline&&<div className="mt-6"><div className="journey-kpis"><div className="engraved"><strong>{creditTimeline.initial_remaining_credits}</strong><span>ساعة متبقية</span></div><div className="engraved"><strong>{creditTimeline.regular_semester_count+creditTimeline.summer_count}</strong><span>فصل متوقع</span></div>{creditTimeline.completion_year&&<div className="engraved"><strong>{creditTimeline.completion_year}</strong><span>{label(creditTimeline.completion_term)}</span></div>}</div><PathMap stations={creditTimeline.terms.map((t,i)=>({id:String(i),title:`${label(t.term)} ${t.academic_year}`,hours:t.planned_credits}))}/></div>}
      {creditComparison&&<div className="scenario-roads">{creditComparison.scenarios.map(s=><article className="engraved p-5" key={s.scenario_id}><h3>{label(s.mode)}</h3><div className="scenario-line"/><strong className="text-2xl">{s.total_modeled_terms}</strong><span> فصول · {label(s.timeline.completion_term)} {s.timeline.completion_year}</span>{s.preference_match&&<small className="block text-copper">يناسب تفضيلك</small>}</article>)}</div>}
      <p className="text-xs text-muted mt-4">تقدير تخطيطي، وليس موعد تخرج معتمدًا.</p>
    </details>
  </div>;
}

