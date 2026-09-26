export type AttemptOutcome = "PASSED" | "FAILED" | "IN_PROGRESS" | "WITHDRAWN";

export type RecordSource =
  | "manual_entry"
  | "transcript_import"
  | "university_integration"
  | "admin_correction";

export type CourseProgressState =
  | "COMPLETED"
  | "IN_PROGRESS"
  | "ATTEMPTED_NOT_COMPLETED"
  | "NOT_ATTEMPTED";

export type RequirementType = "required" | "elective" | "MANDATORY" | "ELECTIVE";

export type Decision = "ELIGIBLE" | "NOT_ELIGIBLE" | "REVIEW_REQUIRED";

export type PrerequisiteLogicStatus =
  | "not_applicable"
  | "verified"
  | "unresolved"
  | "source_conflict";

export type DependencyType = "prerequisite" | "corequisite";

export type DecisionReason =
  | "NO_PREREQUISITES"
  | "PREREQUISITES_SATISFIED"
  | "MISSING_PREREQUISITE_GROUP"
  | "PREREQUISITE_LOGIC_UNRESOLVED"
  | "PREREQUISITE_SOURCE_CONFLICT"
  | "VERIFIED_PREREQUISITE_MODEL_INCOMPLETE"
  | "TARGET_ALREADY_COMPLETED"
  | "TARGET_CURRENTLY_ENROLLED"
  | string;

export interface AcademicProfileResponse {
  id: string;
  study_plan_id: string;
  reported_cumulative_gpa: number | null;
  reported_gpa_scale: number | null;
  reported_earned_credit_hours: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProfileCreateRequest {
  study_plan_id: string;
  reported_cumulative_gpa?: number | null;
  reported_gpa_scale?: number | null;
  reported_earned_credit_hours?: number | null;
}

export interface ProfileUpdateRequest {
  reported_cumulative_gpa?: number | null;
  reported_gpa_scale?: number | null;
  reported_earned_credit_hours?: number | null;
}

export interface CourseAttemptResponse {
  id: string;
  course_code: string;
  status: AttemptOutcome;
  attempt_sequence: number | null;
  term_label: string | null;
  attempted_on: string | null;
  raw_grade_text: string | null;
  record_source: RecordSource;
  created_at: string;
  updated_at: string;
}

export interface AttemptCreateRequest {
  course_code: string;
  status: AttemptOutcome;
  attempt_sequence?: number | null;
  term_label?: string | null;
  attempted_on?: string | null;
  raw_grade_text?: string | null;
  record_source?: RecordSource;
}

export interface AttemptUpdateRequest {
  status?: AttemptOutcome;
  attempt_sequence?: number | null;
  term_label?: string | null;
  attempted_on?: string | null;
  raw_grade_text?: string | null;
  record_source?: RecordSource;
}

export interface RequirementGroupProgressResponse {
  group_id: string;
  group_code: string;
  name_ar: string;
  name_en: string | null;
  scope: string;
  requirement_type: string;
  required_credits: number;
  listed_credits: number;
  completed_listed_credits: number;
  credited_toward_requirement: number;
  in_progress_listed_credits: number;
  remaining_required_credits: number;
  completed_course_count: number;
  in_progress_course_count: number;
  attempted_not_completed_count: number;
  not_attempted_count: number;
  total_listed_course_count: number;
  is_satisfied: boolean;
}

export interface CourseProgressResponse {
  course_code: string;
  credit_hours: number;
  requirement_group_id: string | null;
  requirement_group_code: string | null;
  state: CourseProgressState | string;
}

export interface AcademicProgressResponse {
  study_plan_id: string;
  plan_total_required_credits: number;
  completed_plan_credits: number;
  in_progress_plan_credits: number;
  remaining_plan_credits: number;
  satisfied_requirement_group_count: number;
  total_requirement_group_count: number;
  all_modeled_plan_requirements_satisfied: boolean;
  requirement_groups: RequirementGroupProgressResponse[];
  courses: CourseProgressResponse[];
  reported_cumulative_gpa: number | null;
  reported_gpa_scale: number | null;
  reported_earned_credit_hours: number | null;
}

export interface TargetAttemptStateResponse {
  has_passed_target: boolean;
  has_in_progress_target: boolean;
}

export interface DependencyGroupEvidenceResponse {
  group_number: number;
  dependency_type: DependencyType;
  option_course_codes: string[];
  passed_option_course_codes: string[];
  non_passed_option_course_codes: string[];
}

export interface CanTakeDecisionResponse {
  kind: "decision";
  decision: Decision;
  study_plan_id: string;
  target_course_code: string;
  prerequisite_logic_status: PrerequisiteLogicStatus;
  target_attempt_state: TargetAttemptStateResponse;
  satisfied_dependency_groups: DependencyGroupEvidenceResponse[];
  missing_dependency_groups: DependencyGroupEvidenceResponse[];
  reasons: DecisionReason[];
  review_reasons: DecisionReason[];
  raw_prerequisite_text: string | null;
  target_name_ar: string | null;
}

export interface RecommendationCandidateResponse {
  course_code: string;
  course_name_ar: string | null;
  credit_hours: number;
  requirement_group_code: string;
  requirement_type: string;
  course_state: string;
  eligibility_decision: string;
  effective_credit_contribution: number;
  group_remaining_credits_before: number;
  group_remaining_credits_after: number;
  completes_requirement_group: boolean;
  newly_eligible_count: number;
  newly_eligible_course_codes: string[];
  rank: number;
  reason_codes: string[];
  previously_attempted: boolean;
}

export interface ReviewRequiredCourseResponse {
  course_code: string;
  course_name_ar: string | null;
  credit_hours: number;
  requirement_group_code: string;
  requirement_type: string;
  review_reason: string;
  previously_attempted: boolean;
}

export interface RecommendationResponse {
  study_plan_id: string;
  recommendation_policy_version: string;
  ranked_recommendations: RecommendationCandidateResponse[];
  review_required_courses: ReviewRequiredCourseResponse[];
  excluded_in_progress: string[];
  methodology_note: string;
  limitations: string[];
}

export interface SemesterPlanRequest {
  max_credit_hours: number;
  max_courses?: number | null;
  max_options?: number;
}

export interface PlannedCourseEntryResponse {
  course_code: string;
  course_name_ar: string | null;
  course_name_en: string | null;
  credit_hours: number;
  requirement_group_code: string;
  requirement_type: string;
  phase7_rank: number;
  previously_attempted: boolean;
}

export interface SemesterPlanOptionResponse {
  rank: number;
  courses: PlannedCourseEntryResponse[];
  total_credit_hours: number;
  total_courses: number;
  mandatory_course_count: number;
  zero_credit_required_count: number;
  completed_plan_credit_delta: number;
  newly_satisfied_requirement_group_codes: string[];
  newly_satisfied_requirement_group_count: number;
  newly_eligible_course_codes: string[];
  newly_eligible_count: number;
  recommendation_rank_sum: number;
  reason_codes: string[];
}

export interface PlannerConstraintsResponse {
  max_credit_hours: number;
  max_courses: number | null;
  max_options: number;
}

export interface SemesterPlannerResponse {
  study_plan_id: string;
  semester_planner_policy_version: string;
  planning_scope: string;
  constraints: PlannerConstraintsResponse;
  candidate_window_size: number;
  eligible_ranked_candidate_count: number;
  evaluated_candidate_count: number;
  valid_combination_count: number;
  plan_options: SemesterPlanOptionResponse[];
  review_required_courses: string[];
  excluded_in_progress: string[];
  methodology_note: string;
  limitations: string[];
}

export interface DegreePathRequest {
  max_credit_hours_per_semester: number;
  max_courses_per_semester?: number | null;
  max_semesters_ahead?: number;
  max_paths?: number;
}

export interface ModeledSemesterResponse {
  semester_index: number;
  plan_option: SemesterPlanOptionResponse;
  completed_plan_credits_after: number;
  remaining_plan_credits_after: number;
  newly_satisfied_requirement_group_codes: string[];
}

export interface DegreePathOptionResponse {
  rank: number;
  status: "COMPLETE" | "INCOMPLETE_MAX_SEMESTERS" | "INCOMPLETE_BLOCKED" | string;
  semesters: ModeledSemesterResponse[];
  semester_count: number;
  total_planned_courses: number;
  total_planned_credits: number;
  completed_plan_credit_delta: number;
  final_completed_plan_credits: number;
  final_remaining_plan_credits: number;
  newly_satisfied_requirement_group_count: number;
  newly_satisfied_requirement_group_codes: string[];
  remaining_required_course_codes: string[];
  unresolved_blocker_codes: string[];
  aggregate_semester_rank_sum: number;
  reason_codes: string[];
}

export interface DegreePathConstraintsResponse {
  max_credit_hours_per_semester: number;
  max_courses_per_semester: number | null;
  max_semesters_ahead: number;
  max_paths: number;
}

export interface DegreePathResponse {
  study_plan_id: string;
  degree_path_policy_version: string;
  planning_scope: string;
  constraints: DegreePathConstraintsResponse;
  paths: DegreePathOptionResponse[];
  initial_completed_credits: number;
  initial_remaining_credits: number;
  initial_satisfied_group_count: number;
  total_requirement_group_count: number;
  unresolved_review_required_courses: string[];
  persisted_in_progress_courses: string[];
  total_parent_states_expanded: number;
  methodology_note: string;
  limitations: string[];
}

export interface StudentIntentResponse {
  kind: "mock_registration_intent";
  intent_id: string;
  target_period_id: string;
  target_period_class: string;
  revision: number;
  lifecycle_status: string;
  course_codes: string[];
  submission_validation_status: "VALID" | "REVIEW_REQUIRED" | "INVALID" | string;
  submission_reason_codes: string[];
  current_validity: string | null;
  revalidation_status: string;
  current_reason_codes: string[];
  idempotent_replay: boolean;
  created_at: string;
  non_binding: true;
  limitations: string[];
}

export interface SubmitIntentRequest {
  target_period_id: string;
  course_codes: string[];
  expected_current_revision?: number | null;
  transparency_notice_version: string;
}

export interface WithdrawIntentRequest {
  target_period_id: string;
  expected_current_revision: number;
  transparency_notice_version: string;
}

export interface AdvisorRequest {
  message: string;
}

export interface AdvisorEvidenceResponse {
  source: string;
  course_codes: string[];
  policy_version: string | null;
}

export interface PolicyVersionResponse {
  source: string;
  version: string;
}

export interface AdvisorTraceResponse {
  authoritative_sources: string[];
  course_codes: string[];
  policy_versions: PolicyVersionResponse[];
  option_references: number[];
}

export interface AdvisorResponse {
  policy_version: string;
  intent: string;
  answer_authority: string;
  clarification: { reason: string; message_key: string; candidate_course_codes: string[] } | null;
  out_of_scope_reason: string | null;
  evidence: AdvisorEvidenceResponse[];
  trace: AdvisorTraceResponse;
  result: Record<string, unknown> | null;
  explanation: string | null;
  explanation_status: string;
  explanation_language: string | null;
}

export type DashboardError =
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "VALIDATION_ERROR"
  | "SERVICE_UNAVAILABLE"
  | "SERVER_ERROR"
  | "NETWORK_ERROR"
  | "CONFIGURATION_ERROR"
  | "UNKNOWN";
