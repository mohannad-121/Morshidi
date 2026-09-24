export interface AcademicProfileResponse {
  id: string;
  study_plan_id: string;
  reported_cumulative_gpa: number | null;
  reported_gpa_scale: number | null;
  reported_earned_credit_hours: number | null;
  created_at: string | null;
  updated_at: string | null;
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
  state: string;
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
