import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.morshidi.test';

import ProfilePage from '@/app/(student)/student/profile/page';
import ProgressPage from '@/app/(student)/student/progress/page';
import CoursesPage from '@/app/(student)/student/courses/page';
import EligibilityPage from '@/app/(student)/student/eligibility/page';
import RecommendationsPage from '@/app/(student)/student/recommendations/page';
import PlannerPage from '@/app/(student)/student/planner/page';
import DegreePathPage from '@/app/(student)/student/degree-path/page';
import MockRegistrationPage from '@/app/(student)/student/mock-registration/page';
import AdvisorPage from '@/app/(student)/student/advisor/page';
import PoliciesPage from '@/app/(student)/student/policies/page';
import DecisionHistoryPage from '@/app/(student)/student/decision-history/page';

import { AuthProvider } from '@/auth/auth-provider';
import { FakeAuthClient, fakeSession } from '@/test/fake-auth-client';
import type {
  AcademicProfileResponse,
  AcademicProgressResponse,
  AdvisorResponse,
  CanTakeDecisionResponse,
  CourseAttemptResponse,
  DegreePathResponse,
  RecommendationResponse,
  SemesterPlannerResponse,
  StudentIntentResponse,
} from '@/lib/api/student-types';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/student',
}));

const mockProfile: AcademicProfileResponse = {
  id: 'test-profile-uuid',
  study_plan_id: 'test-plan-uuid',
  reported_cumulative_gpa: 3.75,
  reported_gpa_scale: 4.0,
  reported_earned_credit_hours: 60,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
};

const mockProgress: AcademicProgressResponse = {
  study_plan_id: 'test-plan-uuid',
  plan_total_required_credits: 132,
  completed_plan_credits: 60,
  in_progress_plan_credits: 15,
  remaining_plan_credits: 57,
  satisfied_requirement_group_count: 2,
  total_requirement_group_count: 4,
  all_modeled_plan_requirements_satisfied: false,
  requirement_groups: [
    {
      group_id: 'grp-1',
      group_code: 'REQ-COMP',
      name_ar: 'متطلبات كلية الحاسوب الإجبارية',
      name_en: 'IT College Mandatory',
      scope: 'COLLEGE',
      requirement_type: 'MANDATORY',
      required_credits: 24,
      listed_credits: 24,
      completed_listed_credits: 24,
      credited_toward_requirement: 24,
      in_progress_listed_credits: 0,
      remaining_required_credits: 0,
      completed_course_count: 8,
      in_progress_course_count: 0,
      attempted_not_completed_count: 0,
      not_attempted_count: 0,
      total_listed_course_count: 8,
      is_satisfied: true,
    },
  ],
  courses: [
    {
      course_code: '1501110',
      credit_hours: 3,
      requirement_group_id: 'grp-1',
      requirement_group_code: 'REQ-COMP',
      state: 'COMPLETED',
    },
  ],
  reported_cumulative_gpa: 3.75,
  reported_gpa_scale: 4.0,
  reported_earned_credit_hours: 60,
};

const mockAttempts: CourseAttemptResponse[] = [
  {
    id: 'attempt-1',
    course_code: '1501110',
    status: 'PASSED',
    attempt_sequence: 1,
    term_label: '2023-1',
    attempted_on: '2023-09-01',
    raw_grade_text: 'A',
    record_source: 'manual_entry',
    created_at: '2023-09-01T00:00:00Z',
    updated_at: '2023-09-01T00:00:00Z',
  },
];

const mockEligibility: CanTakeDecisionResponse = {
  kind: 'decision',
  decision: 'ELIGIBLE',
  study_plan_id: 'test-plan-uuid',
  target_course_code: '1501211',
  prerequisite_logic_status: 'verified',
  target_attempt_state: {
    has_passed_target: false,
    has_in_progress_target: false,
  },
  satisfied_dependency_groups: [
    {
      group_number: 1,
      dependency_type: 'prerequisite',
      option_course_codes: ['1501110'],
      passed_option_course_codes: ['1501110'],
      non_passed_option_course_codes: [],
    },
  ],
  missing_dependency_groups: [],
  reasons: ['PREREQUISITES_SATISFIED'],
  review_reasons: [],
  raw_prerequisite_text: '1501110',
  target_name_ar: 'برمجة كينونية',
};

const mockRecommendations: RecommendationResponse = {
  study_plan_id: 'test-plan-uuid',
  recommendation_policy_version: '2026-p7',
  ranked_recommendations: [
    {
      course_code: '1501211',
      course_name_ar: 'برمجة كينونية',
      credit_hours: 3,
      requirement_group_code: 'REQ-COMP',
      requirement_type: 'MANDATORY',
      course_state: 'NOT_ATTEMPTED',
      eligibility_decision: 'ELIGIBLE',
      effective_credit_contribution: 3,
      group_remaining_credits_before: 12,
      group_remaining_credits_after: 9,
      completes_requirement_group: false,
      newly_eligible_count: 2,
      newly_eligible_course_codes: ['1501221', '1501332'],
      rank: 1,
      reason_codes: ['PRIORITY_CORE'],
      previously_attempted: false,
    },
  ],
  review_required_courses: [],
  excluded_in_progress: [],
  methodology_note: 'ترتيب يعتمد أولوية متطلبات التخصص وفتح المواد اللاحقة.',
  limitations: ['يخضع للشعب المطروحة'],
};

const mockSemesterPlanner: SemesterPlannerResponse = {
  study_plan_id: 'test-plan-uuid',
  semester_planner_policy_version: '2026-p7',
  planning_scope: 'UPCOMING_SEMESTER',
  constraints: {
    max_credit_hours: 15,
    max_courses: 5,
    max_options: 3,
  },
  candidate_window_size: 10,
  eligible_ranked_candidate_count: 5,
  evaluated_candidate_count: 5,
  valid_combination_count: 1,
  plan_options: [
    {
      rank: 1,
      courses: [
        {
          course_code: '1501211',
          course_name_ar: 'برمجة كينونية',
          course_name_en: 'Object-Oriented Programming',
          credit_hours: 3,
          requirement_group_code: 'REQ-COMP',
          requirement_type: 'MANDATORY',
          phase7_rank: 1,
          previously_attempted: false,
        },
      ],
      total_credit_hours: 3,
      total_courses: 1,
      mandatory_course_count: 1,
      zero_credit_required_count: 0,
      completed_plan_credit_delta: 3,
      newly_satisfied_requirement_group_codes: [],
      newly_satisfied_requirement_group_count: 0,
      newly_eligible_course_codes: ['1501221'],
      newly_eligible_count: 1,
      recommendation_rank_sum: 1,
      reason_codes: [],
    },
  ],
  review_required_courses: [],
  excluded_in_progress: [],
  methodology_note: 'توليد خيارات مثلى',
  limitations: [],
};

const mockDegreePath: DegreePathResponse = {
  study_plan_id: 'test-plan-uuid',
  degree_path_policy_version: '2026-p7',
  planning_scope: 'GRADUATION_SIMULATION',
  constraints: {
    max_credit_hours_per_semester: 15,
    max_courses_per_semester: 5,
    max_semesters_ahead: 8,
    max_paths: 1,
  },
  paths: [
    {
      rank: 1,
      status: 'COMPLETE',
      semesters: [
        {
          semester_index: 1,
          plan_option: mockSemesterPlanner.plan_options[0],
          completed_plan_credits_after: 63,
          remaining_plan_credits_after: 54,
          newly_satisfied_requirement_group_codes: [],
        },
      ],
      semester_count: 1,
      total_planned_courses: 1,
      total_planned_credits: 3,
      completed_plan_credit_delta: 3,
      final_completed_plan_credits: 132,
      final_remaining_plan_credits: 0,
      newly_satisfied_requirement_group_count: 1,
      newly_satisfied_requirement_group_codes: ['REQ-COMP'],
      remaining_required_course_codes: [],
      unresolved_blocker_codes: [],
      aggregate_semester_rank_sum: 1,
      reason_codes: [],
    },
  ],
  initial_completed_credits: 60,
  initial_remaining_credits: 72,
  initial_satisfied_group_count: 2,
  total_requirement_group_count: 4,
  unresolved_review_required_courses: [],
  persisted_in_progress_courses: [],
  total_parent_states_expanded: 5,
  methodology_note: 'محاكاة التخرج',
  limitations: [],
};

const mockIntent: StudentIntentResponse = {
  kind: 'mock_registration_intent',
  intent_id: 'intent-123',
  target_period_id: '2024-1',
  target_period_class: 'REGULAR',
  revision: 1,
  lifecycle_status: 'SUBMITTED',
  course_codes: ['1501211'],
  submission_validation_status: 'VALID',
  submission_reason_codes: ['VALID_SELECTION'],
  current_validity: 'VALID',
  revalidation_status: 'VALID',
  current_reason_codes: [],
  idempotent_replay: false,
  created_at: '2026-01-01T00:00:00Z',
  non_binding: true,
  limitations: ['غير ملزم'],
};

const mockAdvisor: AdvisorResponse = {
  policy_version: '2026-p7',
  intent: 'COURSE_ELIGIBILITY_INQUIRY',
  answer_authority: 'DETERMINISTIC_RULES_ENGINE',
  clarification: null,
  out_of_scope_reason: null,
  evidence: [
    {
      source: 'STUDY_PLAN_RULES',
      course_codes: ['1501211'],
      policy_version: '2026-p7',
    },
  ],
  trace: {
    authoritative_sources: ['STUDY_PLAN_12'],
    course_codes: ['1501211'],
    policy_versions: [{ source: 'RULES', version: '2026-p7' }],
    option_references: [],
  },
  result: {},
  explanation: 'أنت مؤهل لتسجيل مادة برمجة كينونية (1501211) بعد اجتيازك لمادتها السابقة بنجاح.',
  explanation_status: 'SUCCESS',
  explanation_language: 'ar',
};

function setupMockFetch() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);

    if (url.includes('/api/v1/me/academic-profile/attempts')) {
      return new Response(JSON.stringify(mockAttempts), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (url.includes('/api/v1/me/academic-profile')) {
      return new Response(JSON.stringify(mockProfile), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (url.includes('/api/v1/me/academic-progress')) {
      return new Response(JSON.stringify(mockProgress), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (url.includes('/api/v1/me/eligibility')) {
      return new Response(JSON.stringify(mockEligibility), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (url.includes('/api/v1/me/course-recommendations')) {
      return new Response(JSON.stringify(mockRecommendations), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (url.includes('/api/v1/me/semester-plans')) {
      return new Response(JSON.stringify(mockSemesterPlanner), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (url.includes('/api/v1/me/degree-paths')) {
      return new Response(JSON.stringify(mockDegreePath), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (url.includes('/api/v1/me/mock-registration/current')) {
      return new Response(JSON.stringify(mockIntent), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (url.includes('/api/v1/me/advisor')) {
      return new Response(JSON.stringify(mockAdvisor), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({}), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  });
}

function renderWithAuth(ui: React.ReactElement) {
  const authClient = new FakeAuthClient(fakeSession());
  return render(
    <AuthProvider client={authClient}>
      {ui}
    </AuthProvider>,
  );
}

describe('Morshidi Student Portal Pages Suite', () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchSpy = setupMockFetch();
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it('renders ProfilePage with GPA and academic details', async () => {
    renderWithAuth(<ProfilePage />);
    expect(screen.getByText('ملفي الأكاديمي')).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText('3.75')).toBeDefined();
    });
    expect(screen.getByText('حساب معتمد')).toBeDefined();
  });

  it('renders ProgressPage with credit progress and requirement groups', async () => {
    renderWithAuth(<ProgressPage />);
    expect(screen.getByText('التقدم الأكاديمي')).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText('متطلبات كلية الحاسوب الإجبارية')).toBeDefined();
    });
    expect(screen.getByText('1501110')).toBeDefined();
  });

  it('renders CoursesPage with attempts list and stats', async () => {
    renderWithAuth(<CoursesPage />);
    expect(screen.getByText('المواد وسجل المحاولات')).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText('1501110')).toBeDefined();
    });
    expect(screen.getByText('ناجح / مستوفى')).toBeDefined();
  });

  it('renders EligibilityPage and checks course eligibility', async () => {
    const user = userEvent.setup();
    renderWithAuth(<EligibilityPage />);
    expect(screen.getByText('فحص أهلية تسجيل مادة')).toBeDefined();

    const input = screen.getByPlaceholderText('أدخل رمز المادة هنا...');
    await user.type(input, '1501211');
    const checkBtn = screen.getByRole('button', { name: 'فحص الأهلية' });
    await user.click(checkBtn);

    await waitFor(() => {
      expect(screen.getByText(/مؤهل لتسجيل المادة/)).toBeDefined();
    });
    expect(screen.getByText(/برمجة كينونية/)).toBeDefined();
  });

  it('renders RecommendationsPage with ranked courses and impact tags', async () => {
    renderWithAuth(<RecommendationsPage />);
    expect(screen.getByText('التوصيات الأكاديمية الذكية')).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText('#1')).toBeDefined();
    });
    expect(screen.getByText(/تفتح 2 مواد لاحقة/)).toBeDefined();
  });

  it('renders PlannerPage and generates plan options', async () => {
    const user = userEvent.setup();
    renderWithAuth(<PlannerPage />);
    expect(screen.getByText('مخطط الفصل الدراسي')).toBeDefined();

    const generateBtn = screen.getByRole('button', { name: /توليد خيارات الفصل/ });
    await user.click(generateBtn);

    await waitFor(() => {
      expect(screen.getByText('الخيار #1 (الأفضل تقييماً)')).toBeDefined();
    });
    expect(screen.getByText('برمجة كينونية')).toBeDefined();
  });

  it('renders DegreePathPage and simulates path until graduation', async () => {
    const user = userEvent.setup();
    renderWithAuth(<DegreePathPage />);
    expect(screen.getByText('المسار الدراسي حتى التخرج')).toBeDefined();

    const simulateBtn = screen.getByRole('button', { name: /توليد ومحاكاة مسار التخرج/ });
    await user.click(simulateBtn);

    await waitFor(() => {
      expect(screen.getByText('تخرج كامل')).toBeDefined();
    });
    expect(screen.getByText(/الفصل الدراسي القادم #1/)).toBeDefined();
  });

  it('renders MockRegistrationPage with active submitted intent and non-binding notice', async () => {
    renderWithAuth(<MockRegistrationPage />);
    expect(screen.getByText('التسجيل التجريبي والمحاكاة')).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText('مرسلة ومعتمدة')).toBeDefined();
    });
    expect(screen.getByText(/إشعار الشفافية والمسؤولية الأكاديمية/)).toBeDefined();
  });

  it('renders AdvisorPage with suggested questions and conversational message sending', async () => {
    const user = userEvent.setup();
    renderWithAuth(<AdvisorPage />);
    expect(screen.getByText('المرشد الأكاديمي الذكي')).toBeDefined();

    const quickBtn = screen.getByText('هل يمكنني تسجيل مادة الذكاء الاصطناعي؟');
    await user.click(quickBtn);

    await waitFor(() => {
      expect(screen.getByText(/أنت مؤهل لتسجيل مادة برمجة كينونية/)).toBeDefined();
    });
    expect(screen.getByText('المصدر: DETERMINISTIC_RULES_ENGINE')).toBeDefined();
  });

  it('renders PoliciesPage and DecisionHistoryPage with under development state', () => {
    const { unmount } = render(<PoliciesPage />);
    expect(screen.getByText('اللوائح والسياسات الجامعية')).toBeDefined();
    expect(screen.getByText('بوابة اللوائح والسياسات قيد التجهيز')).toBeDefined();
    unmount();

    render(<DecisionHistoryPage />);
    expect(screen.getByText('سجل القرارات والتدقيق الأكاديمي')).toBeDefined();
    expect(screen.getByText('سجل القرارات الأكاديمية قيد التجهيز')).toBeDefined();
  });
});
