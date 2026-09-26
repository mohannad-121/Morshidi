import {
  AuthenticatedApiClient,
  AuthenticatedApiError,
} from "@/lib/api/authenticated-client";
import type {
  AcademicProfileResponse,
  AcademicProgressResponse,
  AdvisorRequest,
  AdvisorResponse,
  AttemptCreateRequest,
  AttemptUpdateRequest,
  CanTakeDecisionResponse,
  CourseAttemptResponse,
  DegreePathRequest,
  DegreePathResponse,
  RecommendationResponse,
  SemesterPlanRequest,
  SemesterPlannerResponse,
  StudentIntentResponse,
  SubmitIntentRequest,
  WithdrawIntentRequest,
} from "@/lib/api/student-types";

async function parseJson<T>(response: Response): Promise<T> {
  if (response.status === 404) {
    throw new Error("NOT_FOUND");
  }
  if (!response.ok) {
    if (response.status === 403) throw new AuthenticatedApiError("FORBIDDEN", 403);
    if (response.status === 422) throw new AuthenticatedApiError("VALIDATION_ERROR", 422);
    if (response.status === 503) throw new AuthenticatedApiError("SERVICE_UNAVAILABLE", 503);
    if (response.status >= 500) throw new AuthenticatedApiError("SERVER_ERROR", response.status);
    throw new Error(`HTTP_${response.status}`);
  }
  return (await response.json()) as T;
}

export class StudentApiService {
  constructor(private readonly client: AuthenticatedApiClient) {}

  async getProfile(): Promise<AcademicProfileResponse> {
    const res = await this.client.request("/api/v1/me/academic-profile");
    return parseJson<AcademicProfileResponse>(res);
  }

  async getProgress(): Promise<AcademicProgressResponse> {
    const res = await this.client.request("/api/v1/me/academic-progress");
    return parseJson<AcademicProgressResponse>(res);
  }

  async listAttempts(): Promise<CourseAttemptResponse[]> {
    const res = await this.client.request("/api/v1/me/academic-profile/attempts");
    return parseJson<CourseAttemptResponse[]>(res);
  }

  async createAttempt(data: AttemptCreateRequest): Promise<CourseAttemptResponse> {
    const res = await this.client.request("/api/v1/me/academic-profile/attempts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return parseJson<CourseAttemptResponse>(res);
  }

  async updateAttempt(
    attemptId: string,
    data: AttemptUpdateRequest,
  ): Promise<CourseAttemptResponse> {
    const res = await this.client.request(
      `/api/v1/me/academic-profile/attempts/${encodeURIComponent(attemptId)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      },
    );
    return parseJson<CourseAttemptResponse>(res);
  }

  async deleteAttempt(attemptId: string): Promise<void> {
    const res = await this.client.request(
      `/api/v1/me/academic-profile/attempts/${encodeURIComponent(attemptId)}`,
      { method: "DELETE" },
    );
    if (res.status !== 204 && !res.ok) {
      if (res.status === 404) throw new Error("NOT_FOUND");
      throw new Error(`HTTP_${res.status}`);
    }
  }

  async checkEligibility(courseCode: string): Promise<CanTakeDecisionResponse> {
    const res = await this.client.request(
      `/api/v1/me/eligibility/${encodeURIComponent(courseCode.trim().toUpperCase())}`,
    );
    return parseJson<CanTakeDecisionResponse>(res);
  }

  async getRecommendations(limit?: number): Promise<RecommendationResponse> {
    const query = limit ? `?limit=${encodeURIComponent(limit)}` : "";
    const res = await this.client.request(
      `/api/v1/me/course-recommendations${query}`,
    );
    return parseJson<RecommendationResponse>(res);
  }

  async createSemesterPlans(
    request: SemesterPlanRequest,
  ): Promise<SemesterPlannerResponse> {
    const res = await this.client.request("/api/v1/me/semester-plans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    return parseJson<SemesterPlannerResponse>(res);
  }

  async createDegreePaths(
    request: DegreePathRequest,
  ): Promise<DegreePathResponse> {
    const res = await this.client.request("/api/v1/me/degree-paths", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    return parseJson<DegreePathResponse>(res);
  }

  async getCurrentMockRegistration(
    targetPeriodId: string,
  ): Promise<StudentIntentResponse> {
    const res = await this.client.request(
      `/api/v1/me/mock-registration/current?target_period_id=${encodeURIComponent(targetPeriodId)}`,
    );
    return parseJson<StudentIntentResponse>(res);
  }

  async submitMockRegistration(
    request: SubmitIntentRequest,
  ): Promise<StudentIntentResponse> {
    const res = await this.client.request("/api/v1/me/mock-registration/revisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    return parseJson<StudentIntentResponse>(res);
  }

  async withdrawMockRegistration(
    request: WithdrawIntentRequest,
  ): Promise<StudentIntentResponse> {
    const res = await this.client.request(
      "/api/v1/me/mock-registration/withdrawals",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      },
    );
    return parseJson<StudentIntentResponse>(res);
  }

  async askAdvisor(request: AdvisorRequest): Promise<AdvisorResponse> {
    const res = await this.client.request("/api/v1/me/advisor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    return parseJson<AdvisorResponse>(res);
  }
}
