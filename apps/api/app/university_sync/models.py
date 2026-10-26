"""Typed response models for the Fake University integration contract."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)

from app.university_sync.grading_policy import (
    FAKE_UNIVERSITY_COURSE_GRADE_MAX,
    FAKE_UNIVERSITY_COURSE_GRADE_MIN,
    FAKE_UNIVERSITY_GPA_MAX,
    FAKE_UNIVERSITY_GPA_MIN,
    FAKE_UNIVERSITY_GPA_SCALE,
    FAKE_UNIVERSITY_GRADING_POLICY_V1,
    SUPPORTED_POLICY_VERSIONS,
    strict_decimal,
)


StrictNumber = StrictInt | StrictFloat


class UniversityLoginResponse(BaseModel):
    """Authoritative response returned by POST /api/integrations/morshidi/v1/auth/login."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    token: str
    token_type: str = Field(default="Bearer", alias="tokenType")
    expires_in: int | None = Field(default=None, alias="expiresIn")
    student_id: str | None = Field(default=None, alias="studentId")

    @model_validator(mode="before")
    @classmethod
    def extract_token_payload(cls, data: Any) -> Any:
        if isinstance(data, dict):
            inner = data.get("data") if isinstance(data.get("data"), dict) else data
            token = inner.get("token") or inner.get("accessToken") or inner.get("access_token")
            if token and "token" not in inner:
                inner = dict(inner)
                inner["token"] = str(token)
            elif "token" in inner and inner["token"] is not None:
                inner = dict(inner)
                inner["token"] = str(inner["token"])
            student = inner.get("student") if isinstance(inner.get("student"), dict) else {}
            sid = (
                inner.get("studentId")
                or inner.get("student_id")
                or student.get("studentId")
                or student.get("student_id")
            )
            if sid is not None:
                inner = dict(inner)
                inner["student_id"] = str(sid)
            return inner
        return data


class UniversityStudentProfile(BaseModel):
    """Authoritative student profile returned by GET /api/integrations/morshidi/v1/student/me."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    student_id: str = Field(alias="studentId")
    name: str | None = Field(default=None, alias="fullName")
    email: str | None = None
    faculty: str | None = None
    major: str | None = None
    degree: str | None = None
    study_plan: str | None = Field(default=None, alias="studyPlan")
    plan_key: str | None = Field(default=None, alias="planKey")
    plan_number: str | None = Field(default=None, alias="planNumber")
    faculty_code: str | None = Field(default=None, alias="facultyCode")
    major_code: str | None = Field(default=None, alias="majorCode")
    admission_year: int | str | None = Field(default=None, alias="admissionYear")
    academic_status: str | None = Field(default=None, alias="academicStatus")
    academic_advisor: str | None = Field(default=None, alias="academicAdvisor")
    cumulative_gpa: float | str | None = Field(default=None, alias="cumulativeGpa")
    gpa_scale: float | str | None = Field(default=None, alias="gpaScale")
    earned_credits: float | str | None = Field(default=None, alias="earnedCredits")
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    extension_attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_profile(cls, data: Any) -> Any:
        if isinstance(data, dict):
            inner = data.get("data") if isinstance(data.get("data"), dict) else (
                data.get("student") if isinstance(data.get("student"), dict) else data
            )
            inner = dict(inner)
            sid = inner.get("student_id") or inner.get("studentId") or inner.get("id") or inner.get("university_id")
            if sid is not None:
                inner["student_id"] = str(sid)
                inner["studentId"] = str(sid)
            if "gpa" in inner and "cumulative_gpa" not in inner and "cumulativeGpa" not in inner:
                inner["cumulative_gpa"] = inner["gpa"]
            core_keys = {
                "student_id", "studentId", "id", "university_id", "name", "fullName", "email",
                "faculty", "major", "degree", "study_plan", "studyPlan", "plan_key", "planKey",
                "plan_number", "planNumber", "faculty_code", "facultyCode", "major_code", "majorCode",
                "admission_year", "admissionYear", "academic_status", "academicStatus",
                "academic_advisor", "academicAdvisor", "cumulative_gpa", "cumulativeGpa", "gpa",
                "gpa_scale", "gpaScale", "earned_credits", "earnedCredits", "raw_metadata",
                "extension_attributes", "data", "student", "success"
            }
            unmapped = {k: v for k, v in inner.items() if k not in core_keys}
            if unmapped and not inner.get("extension_attributes"):
                inner["extension_attributes"] = unmapped
            return inner
        return data


class UniversityStudentPayload(BaseModel):
    """Strict student object in the real student/me response."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    student_id: StrictStr = Field(alias="studentId")
    name: StrictStr
    email: StrictStr
    faculty: StrictStr
    major: StrictStr
    degree: StrictStr
    study_type: StrictStr = Field(alias="studyType")
    admission_year: StrictInt = Field(alias="admissionYear")
    academic_advisor: StrictStr = Field(alias="academicAdvisor")
    academic_status: StrictStr = Field(alias="academicStatus")
    gpa: StrictNumber | None
    gpa_scale: StrictNumber = Field(alias="gpaScale")
    earned_credits: StrictNumber = Field(alias="earnedCredits")
    plan_key: StrictStr | None = Field(default=None, alias="planKey")
    plan_number: StrictStr | None = Field(default=None, alias="planNumber")
    faculty_code: StrictStr | None = Field(default=None, alias="facultyCode")
    major_code: StrictStr | None = Field(default=None, alias="majorCode")

    @model_validator(mode="after")
    def validate_gpa_numbers(self) -> "UniversityStudentPayload":
        scale = strict_decimal(self.gpa_scale, "student GPA scale")
        if scale <= 0:
            raise ValueError("student GPA scale must be positive")
        if self.gpa is not None:
            strict_decimal(self.gpa, "student GPA")
        return self


class UniversityStudentResponse(BaseModel):
    """Strict real student/me response envelope."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    success: Literal[True]
    student: UniversityStudentPayload


class UniversityCourse(BaseModel):
    """Authoritative course catalog entry returned by GET /api/integrations/morshidi/v1/student/courses."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    course_code: str = Field(alias="courseCode")
    name_ar: str | None = Field(default=None, alias="nameAr")
    name_en: str | None = Field(default=None, alias="nameEn")
    title: str | None = Field(default=None, alias="name")
    credit_hours: int | float | None = Field(default=None, alias="creditHours")
    department: str | None = None
    faculty: str | None = None
    prerequisites: list[str] = Field(default_factory=list)
    status: str | None = None
    extension_attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_course(cls, data: Any) -> Any:
        if isinstance(data, dict):
            inner = dict(data)
            code = inner.get("course_code") or inner.get("courseCode") or inner.get("code") or inner.get("id")
            if code is not None:
                inner["course_code"] = str(code)
                inner["courseCode"] = str(code)
            if "credits" in inner and "credit_hours" not in inner and "creditHours" not in inner:
                inner["credit_hours"] = inner["credits"]
            return inner
        return data


class UniversityGroupedCourse(BaseModel):
    """Strict course item in one real grouped courses collection."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    course_code: StrictStr = Field(alias="courseCode")
    name: StrictStr
    credits: StrictNumber
    status: Literal["completed", "enrolled", "remaining"]


class UniversityCoursesPayload(BaseModel):
    """Strict grouped object returned under the real courses key."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    completed: list[UniversityGroupedCourse]
    current: list[UniversityGroupedCourse]
    remaining: list[UniversityGroupedCourse]


class UniversityCoursesResponse(BaseModel):
    """Strict real student/courses response envelope."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    success: Literal[True]
    courses: UniversityCoursesPayload


class UniversityGradeRecord(BaseModel):
    """Authoritative student grade record returned by GET /api/integrations/morshidi/v1/student/grades."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    course_code: str = Field(alias="courseCode")
    course_name: str | None = Field(default=None, alias="courseName")
    term: str | None = Field(default=None, alias="semester")
    academic_year: str | None = Field(default=None, alias="academicYear")
    letter_grade: str | None = Field(default=None, alias="letterGrade")
    numeric_grade: float | int | str | None = Field(default=None, alias="numericGrade")
    grade_points: float | None = Field(default=None, alias="gradePoints")
    credit_hours: int | float | None = Field(default=None, alias="creditHours")
    status: str = Field(default="PASSED", alias="outcome")
    extension_attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_grade(cls, data: Any) -> Any:
        if isinstance(data, dict):
            inner = dict(data)
            code = inner.get("course_code") or inner.get("courseCode") or inner.get("code")
            if code is not None:
                inner["course_code"] = str(code)
                inner["courseCode"] = str(code)
            if "grade" in inner and "letter_grade" not in inner and "letterGrade" not in inner:
                inner["letter_grade"] = str(inner["grade"])
            if "credits" in inner and "credit_hours" not in inner and "creditHours" not in inner:
                inner["credit_hours"] = inner["credits"]
            return inner
        return data


class UniversitySemesterGradeCourse(BaseModel):
    """Strict course result nested inside the real grades response."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    course_code: str = Field(alias="courseCode")
    name: str
    credits: StrictInt | StrictFloat
    grade: StrictInt | StrictFloat
    letter_grade: str = Field(alias="letterGrade")
    status: Literal["passed", "failed", "withdrawn"]


class UniversityNumericRange(BaseModel):
    """Strict numeric bounds supplied by the university contract."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    numeric_min: StrictNumber = Field(alias="numericMin")
    numeric_max: StrictNumber = Field(alias="numericMax")


class UniversityGpaPolicy(UniversityNumericRange):
    scale: StrictNumber


class UniversityCourseGradePolicy(UniversityNumericRange):
    pass


class UniversityGradingPolicy(BaseModel):
    """Authoritative upstream grading policy contract."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    version: str
    gpa: UniversityGpaPolicy
    course_grade: UniversityCourseGradePolicy = Field(alias="courseGrade")

    @model_validator(mode="after")
    def validate_exact_v1_semantics(self) -> "UniversityGradingPolicy":
        if self.version not in SUPPORTED_POLICY_VERSIONS:
            raise ValueError("grading policy does not match the exact supported V1 contract")
        gpa_min = strict_decimal(self.gpa.numeric_min, "gradingPolicy.gpa.numericMin")
        gpa_max = strict_decimal(self.gpa.numeric_max, "gradingPolicy.gpa.numericMax")
        gpa_scale = strict_decimal(self.gpa.scale, "gradingPolicy.gpa.scale")
        course_min = strict_decimal(self.course_grade.numeric_min, "gradingPolicy.courseGrade.numericMin")
        course_max = strict_decimal(self.course_grade.numeric_max, "gradingPolicy.courseGrade.numericMax")

        if self.version == FAKE_UNIVERSITY_GRADING_POLICY_V1:
            actual = (gpa_min, gpa_max, gpa_scale, course_min, course_max)
            expected = (
                FAKE_UNIVERSITY_GPA_MIN,
                FAKE_UNIVERSITY_GPA_MAX,
                FAKE_UNIVERSITY_GPA_SCALE,
                FAKE_UNIVERSITY_COURSE_GRADE_MIN,
                FAKE_UNIVERSITY_COURSE_GRADE_MAX,
            )
            if actual != expected:
                raise ValueError("grading policy does not match the exact supported V1 contract")
        else:
            if gpa_min >= gpa_max or gpa_scale <= Decimal("0"):
                raise ValueError("grading policy GPA bounds are invalid")
            if course_min >= course_max:
                raise ValueError("grading policy course grade bounds are invalid")
        return self


class UniversitySemesterGrades(BaseModel):
    """Strict semester object nested inside the real grades response."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    term: str
    term_label: str = Field(alias="termLabel")
    registered_hours: StrictInt | StrictFloat = Field(alias="registeredHours")
    passed_hours: StrictInt | StrictFloat = Field(alias="passedHours")
    semester_gpa: StrictInt | StrictFloat = Field(alias="semesterGpa")
    cumulative_gpa: StrictInt | StrictFloat = Field(alias="cumulativeGpa")
    courses: list[UniversitySemesterGradeCourse]


class UniversityGradesResponse(BaseModel):
    """Strict real response returned by the student grades endpoint."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    success: Literal[True]
    cumulative_gpa: StrictInt | StrictFloat | None = Field(alias="cumulativeGpa")
    gpa_scale: StrictInt | StrictFloat = Field(alias="gpaScale")
    grading_policy: UniversityGradingPolicy = Field(alias="gradingPolicy")
    semesters: list[UniversitySemesterGrades]

    @model_validator(mode="after")
    def validate_values_against_policy(self) -> "UniversityGradesResponse":
        policy = self.grading_policy
        gpa_min = strict_decimal(policy.gpa.numeric_min, "GPA minimum")
        gpa_max = strict_decimal(policy.gpa.numeric_max, "GPA maximum")
        grade_min = strict_decimal(policy.course_grade.numeric_min, "course-grade minimum")
        grade_max = strict_decimal(policy.course_grade.numeric_max, "course-grade maximum")
        scale = strict_decimal(self.gpa_scale, "grades GPA scale")
        if scale != strict_decimal(policy.gpa.scale, "policy GPA scale"):
            raise ValueError("grades GPA scale contradicts grading policy")
        # A student with no completed grade history has no cumulative GPA yet.
        # Preserve that absence; semester GPA fields remain strictly numeric.
        gpas = []
        if self.cumulative_gpa is not None:
            gpas.append(("cumulative GPA", self.cumulative_gpa))
        for semester in self.semesters:
            gpas.extend((("semester GPA", semester.semester_gpa),
                         ("semester cumulative GPA", semester.cumulative_gpa)))
            for course in semester.courses:
                grade = strict_decimal(course.grade, "course numeric grade")
                if not grade_min <= grade <= grade_max:
                    raise ValueError("course numeric grade is outside grading-policy bounds")
        for field, raw in gpas:
            value = strict_decimal(raw, field)
            if not gpa_min <= value <= gpa_max:
                raise ValueError(f"{field} is outside grading-policy bounds")
        return self


class UniversityGradesSnapshot(BaseModel):
    """Validated academic-grade snapshot retained after wire-contract parsing."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    cumulative_gpa: Decimal | None
    gpa_scale: Decimal
    grading_policy: UniversityGradingPolicy
    records: list[UniversityGradeRecord]

    def __iter__(self):
        return iter(self.records)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> UniversityGradeRecord:
        return self.records[index]


class UniversityEnrollmentRecord(BaseModel):
    """Authoritative enrollment returned by GET /api/integrations/morshidi/v1/student/enrollments."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    course_code: str = Field(alias="courseCode")
    course_name: str | None = Field(default=None, alias="courseName")
    section_id: str | None = Field(default=None, alias="sectionId")
    term: str | None = Field(default=None, alias="semester")
    status: str = "ENROLLED"
    credit_hours: int | float | None = Field(default=None, alias="creditHours")
    instructor: str | None = None
    schedule: list[dict[str, Any]] | str | None = None
    extension_attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_enrollment(cls, data: Any) -> Any:
        if isinstance(data, dict):
            inner = dict(data)
            code = inner.get("course_code") or inner.get("courseCode") or inner.get("code")
            if code is not None:
                inner["course_code"] = str(code)
                inner["courseCode"] = str(code)
            return inner
        return data


class UniversityEnrollmentPayload(BaseModel):
    """Strict enrollment item in the real enrollments response."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    course_code: StrictStr = Field(alias="courseCode")
    course_name: StrictStr = Field(alias="courseName")
    section_id: StrictStr = Field(alias="sectionId")
    section_number: StrictInt = Field(alias="sectionNumber")
    credits: StrictNumber
    days: StrictStr
    days_array: list[StrictStr] = Field(alias="daysArray")
    start_time: StrictStr = Field(alias="startTime")
    end_time: StrictStr = Field(alias="endTime")
    room: StrictStr
    instructor: StrictStr


class UniversityEnrollmentsResponse(BaseModel):
    """Strict real student/enrollments response with shared term context."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    success: Literal[True]
    term: StrictStr
    term_label: StrictStr = Field(alias="termLabel")
    enrollments: list[UniversityEnrollmentPayload]


class UniversityAcademicPlan(BaseModel):
    """Authoritative plan structure returned by GET /api/integrations/morshidi/v1/student/academic-plan."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    plan_id: str | None = Field(default=None, alias="planId")
    plan_key: str | None = Field(default=None, alias="planKey")
    plan_number: str | None = Field(default=None, alias="planNumber")
    faculty: str | None = None
    faculty_code: str | None = Field(default=None, alias="facultyCode")
    major_code: str | None = Field(default=None, alias="majorCode")
    title: str | None = None
    major: str | None = None
    degree: str | None = None
    total_credit_hours: int | float | None = Field(default=None, alias="totalCreditHours")
    requirement_groups: list[dict[str, Any]] = Field(default_factory=list, alias="requirementGroups")
    courses: list[dict[str, Any]] = Field(default_factory=list)
    semesters: list[dict[str, Any]] = Field(default_factory=list)
    extension_attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_plan(cls, data: Any) -> Any:
        if isinstance(data, dict):
            inner = data.get("data") if isinstance(data.get("data"), dict) else (
                data.get("plan") if isinstance(data.get("plan"), dict) else data
            )
            inner = dict(inner)
            pid = inner.get("plan_id") or inner.get("planId") or inner.get("plan_number") or inner.get("id")
            if pid is not None:
                inner["plan_id"] = str(pid)
            plan_number = inner.get("plan_number") or inner.get("planNumber")
            if plan_number is not None:
                inner["plan_number"] = str(plan_number)
            if "total_credits" in inner and "total_credit_hours" not in inner:
                inner["total_credit_hours"] = inner["total_credits"]
            elif "totalCredits" in inner and "total_credit_hours" not in inner:
                inner["total_credit_hours"] = inner["totalCredits"]
            return inner
        return data


class UniversityAcademicPlanCourse(BaseModel):
    """Strict course item in the real academic-plan response."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    course_code: StrictStr = Field(alias="courseCode")
    name: StrictStr
    credits: StrictNumber
    group: StrictStr
    type: StrictStr
    prerequisites: list[StrictStr]
    status: Literal["completed", "current", "remaining"]


class UniversityAcademicPlanPayload(BaseModel):
    """Strict plan object returned under the real plan key."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    plan_id: StrictStr = Field(alias="planId")
    plan_key: StrictStr | None = Field(default=None, alias="planKey")
    plan_number: StrictStr | None = Field(default=None, alias="planNumber")
    faculty: StrictStr | None = None
    faculty_code: StrictStr | None = Field(default=None, alias="facultyCode")
    major: StrictStr
    major_code: StrictStr | None = Field(default=None, alias="majorCode")
    total_required_credits: StrictNumber = Field(alias="totalRequiredCredits")
    earned_credits: StrictNumber = Field(alias="earnedCredits")
    remaining_credits: StrictNumber = Field(alias="remainingCredits")
    courses: list[UniversityAcademicPlanCourse]


class UniversityAcademicPlanResponse(BaseModel):
    """Strict real student/academic-plan response envelope."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    success: Literal[True]
    plan: UniversityAcademicPlanPayload
