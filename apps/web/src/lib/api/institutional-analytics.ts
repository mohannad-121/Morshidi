import type { AuthenticatedApiClient } from "./authenticated-client";

export type Metric = {
  value: number | null;
  status: "AVAILABLE" | "INSUFFICIENT_DATA" | "SUPPRESSED" | "UNAVAILABLE";
  unit: string;
  inputs: Record<string, number | string | boolean | null>;
  reason_codes: string[];
};

export type ProgramMetric = {
  plan_id: string; plan_key: string; plan_number: string;
  faculty_code: string; faculty_name_ar: string; major_code: string; major_name_ar: string;
  student_count: number; data_status: Metric["status"];
  average_progress_percent: number | null; average_earned_credits: number | null;
  median_earned_credits: number | null; current_registered_credits: number;
  blocked_student_count: number | null; review_required_count: number | null;
  progress_distribution: { band: string; student_count: number | null; status: Metric["status"] }[];
  high_demand_courses: string[]; bottleneck_courses: string[];
};

export type CourseMetric = {
  course_code: string; name_ar: string | null; name_en: string | null;
  programs: string[]; requirement_categories: string[];
  prerequisite_status: "VERIFIED" | "REVIEW_REQUIRED" | "NOT_APPLICABLE";
  current_registered: Metric; eligible_not_registered: Metric; planned_need: Metric;
  degree_path_need: Metric; projected_demand: Metric;
  projection_confidence: "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT_DATA";
  projection_components: { currently_eligible: number; planner_selected: number;
    degree_path_upcoming: number; excluded_completed_or_registered: number };
  offered_seats: Metric; available_seats: Metric; utilization_percent: Metric;
  demand_capacity_gap: Metric;
  capacity_state: "UNDER_CAPACITY" | "HEALTHY" | "NEAR_CAPACITY" | "OVER_DEMAND" | "UNAVAILABLE";
  bottleneck_score: number; bottleneck_level: "NONE" | "WATCH" | "HIGH" | "CRITICAL";
  bottleneck_reasons: string[]; affected_student_count: number;
  downstream_course_count: number; programs_affected: string[];
  action_recommendation: string | null; estimated_students_helped: number;
  demand_by_program: { plan_key: string; faculty_code: string; major_code: string;
    student_count: number; demand_count: number }[];
};

export type Dashboard = {
  kind: "INSTITUTIONAL_INTELLIGENCE_DASHBOARD"; contract_version: "2.0";
  university_id: string; term_key: string; role_scope: "INSTITUTION_ADMIN" | "ADVISOR_ASSIGNED";
  filters: Record<string, string | null>; minimum_cohort_size: number;
  overview: {
    total_active_students: Metric; current_registrations: Metric; average_registered_credit_load: Metric;
    eligible_course_opportunities: Metric; blocked_by_prerequisite: Metric; review_required: Metric;
    high_demand_courses: Metric; capacity_pressure_courses: Metric; academic_bottlenecks: Metric;
    approaching_graduation: Metric; blocked_degree_paths: Metric;
    students_by_faculty: Record<string, number>; students_by_major: Record<string, number>;
  };
  programs: ProgramMetric[]; courses: CourseMetric[];
  review_queue: { course_code: string; unresolved_prerequisite_codes: string[];
    affected_plans: string[]; affected_student_count: number | null;
    downstream_course_count: number; system_behavior: "FAIL_CLOSED" }[];
  advisor_caseload: { scope: string; assigned_student_count: number | null;
    prerequisite_review: number; blocked_degree_paths: number; near_graduation: number;
    registration_conflicts: Metric; approaching_credit_limit: Metric;
    without_viable_semester_plan: number; impacted_by_high_pressure_courses: number; reason_codes: string[] };
  methodology: Record<string, string>; source_versions: Record<string, string>; generated_at: string;
};

export type Simulation = {
  simulation_only: true; course_code: string; kind: string;
  capacity_before: number | null; capacity_after: number | null;
  demand_gap_before: number | null; demand_gap_after: number | null;
  estimated_students_helped: number; bottleneck_score_before: number; bottleneck_score_after: number;
  affected_programs: string[]; affected_eligible_students: number; affected_degree_paths: number;
  downstream_courses_impacted: number; assumptions: string[];
};

export type CopilotAnswer = {
  status: "ANSWERED" | "ABSTAINED"; tool: string | null; answer_text: string;
  result: Record<string, unknown> | unknown[] | null; course_code: string | null;
  limitations: string[];
};

export class InstitutionalAnalyticsApi {
  constructor(private readonly client: AuthenticatedApiClient) {}

  async access(): Promise<{ university_id: string; role_scope: string }[]> {
    const response = await this.client.request("/api/v1/institutional/analytics/access");
    if (!response.ok) throw new Error("INSTITUTIONAL_ACCESS_UNAVAILABLE");
    const body = await response.json() as { scopes: { university_id: string; role_scope: string }[] };
    return body.scopes;
  }

  async dashboard(input: { universityId: string; termKey: string; faculty?: string; major?: string }): Promise<Dashboard> {
    const query = new URLSearchParams({ university_id: input.universityId, term_key: input.termKey });
    if (input.faculty) query.set("faculty", input.faculty);
    if (input.major) query.set("major", input.major);
    const response = await this.client.request(`/api/v1/institutional/analytics/dashboard?${query}`);
    if (!response.ok) throw new Error("INSTITUTIONAL_DASHBOARD_UNAVAILABLE");
    return response.json() as Promise<Dashboard>;
  }

  async simulate(input: { university_id: string; term_key: string; course_code: string;
    kind: "ADD_SECTION" | "REMOVE_OFFERING" | "CHANGE_SECTION_CAPACITY";
    seats?: number; section_id?: string }): Promise<Simulation> {
    const response = await this.client.request("/api/v1/institutional/analytics/simulate", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
    });
    if (!response.ok) throw new Error("INSTITUTIONAL_SIMULATION_UNAVAILABLE");
    return response.json() as Promise<Simulation>;
  }

  async ask(input: { question: string; university_id: string; term_key: string;
    previous_tool?: string; previous_course_code?: string }): Promise<CopilotAnswer> {
    const response = await this.client.request("/api/v1/institutional/analytics/copilot", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
    });
    if (!response.ok) throw new Error("INSTITUTIONAL_COPILOT_UNAVAILABLE");
    return response.json() as Promise<CopilotAnswer>;
  }
}
