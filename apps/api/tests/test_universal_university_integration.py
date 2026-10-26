"""Comprehensive automated tests for Morshidi Universal University Integration Engine.

Validates:
1. Universal institutional data models and hierarchies.
2. Extensible institutional grading & GPA policies (100-point, 4.0, 4.33, 5.0, letter grades).
3. Universal course identity and terminology/alias resolution.
4. Architectural invariant: AI EXPLAINS — DETERMINISTIC RULES DECIDE (search synonyms vs verified equivalencies).
5. Safe preservation of unknown provider attributes in extension_attributes.
6. University adapter capability discovery and graceful degradation.
7. Multi-university tenant isolation.
8. University onboarding configuration validation and live diagnostics engine.
9. Academic AI system prompt institutional grounding.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4
import pytest
from pydantic import ValidationError

from app.advisor.conversation_agent import (
    InstitutionalContext,
    build_conversation_system_instruction,
)
from app.catalog.course_identity import (
    CourseAliasResolver,
    CourseAliasType,
    CourseEquivalencyRecord,
    InstitutionalCourseAlias,
    UniversalCourseIdentity,
    normalize_arabic_terminology,
)
from app.sis_integration.capabilities import (
    CapabilityNegotiator,
    PilotMode,
    SISCapability,
    TenantStatus,
)
from app.sis_integration.models import (
    HealthResult,
    NormalizedCourse,
    NormalizedGradeAttempt,
    NormalizedOffering,
    NormalizedStudent,
    UniversityIntegrationConfig,
    UniversityTenant,
)
from app.sis_integration.onboarding import (
    CampusSpec,
    FacultySpec,
    GradingPolicyConfigSpec,
    InstitutionalHierarchySpec,
    MajorSpec,
    OnboardingDiagnosticsEngine,
    UniversityOnboardingSpec,
)
from app.university_sync.grading_policy import (
    FAKE_UNIVERSITY_GRADING_POLICY_V1,
    UNIVERSAL_GPA_4_V1,
    UNIVERSAL_GPA_433_V1,
    UNIVERSAL_GPA_5_V1,
    UNIVERSAL_PERCENTAGE_100_V1,
    GradingScaleType,
    InstitutionalGradingPolicy,
    create_standard_policy,
    grading_policy_source_reference,
    parse_grading_policy_source_reference,
)
from app.university_sync.models import (
    UniversityGradingPolicy,
    UniversityStudentProfile,
)


UNI_A_ID = "10000000-0000-0000-0000-000000000001"
UNI_B_ID = "20000000-0000-0000-0000-000000000002"


# --- 1. Institutional Grading & GPA Policy Extensibility ---

def test_standard_percentage_grading_policy() -> None:
    policy = create_standard_policy(UNIVERSAL_PERCENTAGE_100_V1, UNI_A_ID)
    assert policy.scale_type == GradingScaleType.PERCENTAGE_100
    assert policy.gpa_scale == Decimal("100")
    assert policy.is_grade_passing(Decimal("50")) is True
    assert policy.is_grade_passing(Decimal("49")) is False
    assert policy.is_grade_passing(Decimal("55"), is_major=True) is False
    assert policy.is_grade_passing(Decimal("60"), is_major=True) is True
    assert policy.is_gpa_on_warning(Decimal("59.9")) is True
    assert policy.is_gpa_on_warning(Decimal("60.0")) is False
    assert policy.is_gpa_honors(Decimal("84.5")) is True
    assert policy.normalize_to_percentage(Decimal("75")) == 75


def test_standard_gpa4_grading_policy() -> None:
    policy = create_standard_policy(UNIVERSAL_GPA_4_V1, UNI_B_ID)
    assert policy.scale_type == GradingScaleType.GPA_4_0
    assert policy.gpa_scale == Decimal("4.0")
    assert policy.is_grade_passing(Decimal("2.0")) is True
    assert policy.is_grade_passing(Decimal("1.99")) is False
    assert policy.is_gpa_on_warning(Decimal("1.85")) is True
    assert policy.is_gpa_honors(Decimal("3.6")) is True
    # 3.0 out of 4.0 should normalize to 75%
    assert policy.normalize_to_percentage(Decimal("3.0")) == 75


def test_standard_gpa5_grading_policy() -> None:
    policy = create_standard_policy(UNIVERSAL_GPA_5_V1, UNI_B_ID)
    assert policy.scale_type == GradingScaleType.GPA_5_0
    assert policy.gpa_scale == Decimal("5.0")
    assert policy.is_grade_passing(Decimal("2.75")) is True
    assert policy.is_grade_passing(Decimal("2.5")) is False
    # 4.0 out of 5.0 should normalize to 80%
    assert policy.normalize_to_percentage(Decimal("4.0")) == 80


def test_grading_policy_source_reference_lifecycle() -> None:
    ref = grading_policy_source_reference(UNI_A_ID, UNIVERSAL_GPA_4_V1)
    assert ref == f"university:{UNI_A_ID}:grading-policy:{UNIVERSAL_GPA_4_V1}"

    parsed = parse_grading_policy_source_reference(ref)
    assert parsed is not None
    assert parsed.university_id == UNI_A_ID
    assert parsed.version == UNIVERSAL_GPA_4_V1

    # Malformed reference fails closed
    assert parse_grading_policy_source_reference("forged:policy") is None
    assert parse_grading_policy_source_reference(f"university:not-a-uuid:grading-policy:{UNIVERSAL_GPA_4_V1}") is None


def test_university_grading_policy_model_accepts_supported_versions() -> None:
    # 4.0 GPA policy accepted
    policy_4 = UniversityGradingPolicy.model_validate({
        "version": UNIVERSAL_GPA_4_V1,
        "gpa": {"numericMin": 0.0, "numericMax": 4.0, "scale": 4.0},
        "courseGrade": {"numericMin": 0.0, "numericMax": 4.0},
    })
    assert policy_4.version == UNIVERSAL_GPA_4_V1
    assert policy_4.gpa.scale == 4.0

    # 100 percentage policy accepted
    policy_100 = UniversityGradingPolicy.model_validate({
        "version": FAKE_UNIVERSITY_GRADING_POLICY_V1,
        "gpa": {"numericMin": 0, "numericMax": 100, "scale": 100},
        "courseGrade": {"numericMin": 0, "numericMax": 100},
    })
    assert policy_100.version == FAKE_UNIVERSITY_GRADING_POLICY_V1


def test_unknown_grading_policy_version_fails_closed() -> None:
    with pytest.raises(ValidationError):
        UniversityGradingPolicy.model_validate({
            "version": "COMPLETELY_UNSUPPORTED_V99",
            "gpa": {"numericMin": 0, "numericMax": 100, "scale": 100},
            "courseGrade": {"numericMin": 0, "numericMax": 100},
        })


# --- 2. Universal Course Identity & Terminology/Alias Resolution ---

def test_arabic_terminology_normalization() -> None:
    # Normalizes diacritics, alefs, and ta marbuta
    assert normalize_arabic_terminology("التَّرْبِيَةُ الوَطَنِيَّةُ") == "التربيه الوطنيه"
    assert normalize_arabic_terminology("  أصول  البحث   العلمي  ") == "اصول البحث العلمي"
    assert normalize_arabic_terminology("كيمياء١٠١") == "كيمياء101"


def test_course_alias_resolution_and_discovery() -> None:
    c1 = UniversalCourseIdentity(
        canonical_id="c1",
        canonical_code="0100101",
        name_ar="التربية الوطنية",
        name_en="National Education",
        credit_hours=Decimal("3.0"),
    )
    c2 = UniversalCourseIdentity(
        canonical_id="c2",
        canonical_code="1501110",
        name_ar="أساسيات البرمجة",
        name_en="Programming Fundamentals",
        credit_hours=Decimal("3.0"),
    )

    alias1 = InstitutionalCourseAlias(
        university_id=UNI_A_ID,
        canonical_course_code="0100101",
        alias_name_ar="المواطنة الصالحة",
        alias_type=CourseAliasType.SEARCH_SYNONYM,
    )
    alias2 = InstitutionalCourseAlias(
        university_id=UNI_A_ID,
        canonical_course_code="1501110",
        alias_name_ar="مقدمة في البرمجة",
        alias_type=CourseAliasType.REGIONAL_VARIANT,
    )

    resolver = CourseAliasResolver(
        university_id=UNI_A_ID,
        courses=[c1, c2],
        aliases=[alias1, alias2],
    )

    # 1. Search by canonical title
    results_canon = resolver.search_courses("التربية")
    assert len(results_canon) > 0
    assert results_canon[0][0].canonical_code == "0100101"

    # 2. Search by alias/synonym
    results_alias = resolver.search_courses("المواطنة")
    assert len(results_alias) > 0
    assert results_alias[0][0].canonical_code == "0100101"

    results_intro = resolver.search_courses("مقدمة")
    assert len(results_intro) > 0
    assert results_intro[0][0].canonical_code == "1501110"


def test_ai_explains_deterministic_rules_decide_invariant() -> None:
    """CRITICAL: Search synonyms must NEVER create academic equivalencies."""
    c1 = UniversalCourseIdentity(
        canonical_id="c1",
        canonical_code="0100101",
        name_ar="التربية الوطنية",
    )
    c2 = UniversalCourseIdentity(
        canonical_id="c2",
        canonical_code="0100102",
        name_ar="المواطنة الصالحة",
    )

    # Alias says "المواطنة الصالحة" is a synonym for finding "0100101"
    alias = InstitutionalCourseAlias(
        university_id=UNI_A_ID,
        canonical_course_code="0100101",
        alias_name_ar="المواطنة الصالحة",
        alias_type=CourseAliasType.SEARCH_SYNONYM,
    )

    # NO academic equivalency declared in public.course_equivalencies
    resolver = CourseAliasResolver(
        university_id=UNI_A_ID,
        courses=[c1, c2],
        aliases=[alias],
        equivalencies=[],
    )

    # Deterministic academic check: Are 0100101 and 0100102 equivalent?
    # MUST BE FALSE! A search synonym does not grant course credit transfer.
    assert resolver.is_academically_equivalent("0100101", "0100102") is False

    # Now add an official, verified institutional equivalency record
    official_eq = CourseEquivalencyRecord(
        source_course_code="0100101",
        target_course_code="0100102",
        relationship_type="equivalent",
        is_bidirectional=True,
        verification_status="verified",
    )
    resolver_verified = CourseAliasResolver(
        university_id=UNI_A_ID,
        courses=[c1, c2],
        aliases=[alias],
        equivalencies=[official_eq],
    )
    # NOW it is equivalent because of verified institutional policy
    assert resolver_verified.is_academically_equivalent("0100101", "0100102") is True
    assert resolver_verified.is_academically_equivalent("0100102", "0100101") is True


# --- 3. Extensible Unknown-Data Handling ---

def test_unmapped_provider_attributes_preserved_safely() -> None:
    """Verify that unexpected SIS attributes are preserved in extension_attributes without breaking core validation."""
    raw_student_data = {
        "studentId": "202310042",
        "fullName": "Zaid Al-Tal",
        "faculty": "IT",
        "major": "AI",
        "gpa": 88.5,
        "gpaScale": 100,
        "earnedCredits": 45,
        # Unexpected provider fields:
        "financial_hold": False,
        "dormitory_building": "Hall C",
        "bus_subscription_route": "Amman-Zarqa Express",
        "high_school_percentile": 94.2,
    }

    profile = UniversityStudentProfile.model_validate(raw_student_data)
    assert profile.student_id == "202310042"
    assert profile.cumulative_gpa == 88.5
    # Verify extension attributes captured unexpected fields
    assert profile.extension_attributes.get("dormitory_building") == "Hall C"
    assert profile.extension_attributes.get("bus_subscription_route") == "Amman-Zarqa Express"
    assert profile.extension_attributes.get("high_school_percentile") == 94.2

    # Verify NormalizedCourse preserves extension attributes
    course = NormalizedCourse(
        course_code="CS101",
        name_ar="برمجة 1",
        credit_hours=Decimal("3"),
        extension_attributes={"lab_hours": 2, "special_accreditation": "ABET"},
    )
    assert course.extension_attributes["lab_hours"] == 2
    assert course.extension_attributes["special_accreditation"] == "ABET"


# --- 4. Adapter Capability Discovery and Graceful Degradation ---

def test_capability_negotiator_enforces_read_only_pilot() -> None:
    caps = {
        SISCapability.IDENTITY_AUTH,
        SISCapability.STUDENT_PROFILE_READ,
        SISCapability.CURRICULUM_READ,
        SISCapability.OFFERINGS_READ,
    }

    # In READ_ONLY_PILOT mode, write actions must be blocked
    permitted, reason = CapabilityNegotiator.is_action_permitted(
        "register",
        capabilities=caps,
        pilot_mode=PilotMode.READ_ONLY_PILOT,
        tenant_status=TenantStatus.PILOT_READY,
    )
    assert permitted is False
    assert reason == "WRITE_ACTION_BLOCKED_BY_PILOT_MODE"

    # Even in WRITE_ENABLED_PILOT, missing capability blocks action
    permitted, reason = CapabilityNegotiator.is_action_permitted(
        "register",
        capabilities=caps,
        pilot_mode=PilotMode.WRITE_ENABLED_PILOT,
        tenant_status=TenantStatus.ACTIVE,
    )
    assert permitted is False
    assert reason == "CAPABILITY_REGISTRATION_WRITE_REQUIRED"


def test_capability_degradation_evaluation() -> None:
    read_only_caps = {
        SISCapability.IDENTITY_AUTH,
        SISCapability.STUDENT_PROFILE_READ,
        SISCapability.CURRICULUM_READ,
        SISCapability.OFFERINGS_READ,
        SISCapability.REGISTRATION_PREVIEW,
    }

    degradation = CapabilityNegotiator.evaluate_feature_degradation(read_only_caps)
    assert degradation["registration"]["available"] is True
    assert degradation["registration"]["can_write"] is False
    assert degradation["registration"]["can_preview"] is True
    assert degradation["registration"]["degradation_mode"] == "PREVIEW_ONLY"
    assert degradation["offerings_discovery"]["available"] is True


# --- 5. University Onboarding Configuration & Diagnostics ---

def test_onboarding_spec_validation_success() -> None:
    spec = UniversityOnboardingSpec(
        name_ar="الجامعة الأردنية",
        name_en="University of Jordan",
        tenant_key="uj-amman",
        country="JO",
        timezone="Asia/Amman",
        adapter_provider_type="generic_rest",
        base_url="https://api.uj.edu.jo/sis/v1",
        auth_method="client_credentials",
        client_id="uj-morshidi-gateway",
        secret_env_ref="UJ_SIS_API_SECRET",
        supported_capabilities=[
            SISCapability.IDENTITY_AUTH,
            SISCapability.STUDENT_PROFILE_READ,
            SISCapability.CURRICULUM_READ,
            SISCapability.OFFERINGS_READ,
            SISCapability.GRADES_READ,
        ],
        hierarchy=InstitutionalHierarchySpec(
            faculties=[FacultySpec(code="IT", name_ar="كلية الملك عبد الله الثاني لتكنولوجيا المعلومات")],
            majors=[MajorSpec(code="CS", faculty_code="IT", name_ar="علم الحاسوب")],
            campuses=[CampusSpec(code="MAIN", name_ar="الحرم الجامعي الرئيسي - الجبيهة", is_main=True)],
        ),
        grading_policy=GradingPolicyConfigSpec(
            policy_version=UNIVERSAL_GPA_4_V1,
            scale_type=GradingScaleType.GPA_4_0,
            gpa_scale=Decimal("4.0"),
            gpa_min=Decimal("0.0"),
            gpa_max=Decimal("4.0"),
            course_grade_min=Decimal("0.0"),
            course_grade_max=Decimal("4.0"),
            passing_grade=Decimal("2.0"),
            major_passing_grade=Decimal("2.0"),
            warning_threshold=Decimal("2.0"),
            honors_threshold=Decimal("3.5"),
        ),
    )

    result = OnboardingDiagnosticsEngine.validate_spec(spec)
    assert result.valid is True
    assert len(result.errors) == 0
    assert result.tenant_key == "uj-amman"
    assert result.readiness_stage == "PILOT_READY"


def test_onboarding_spec_validation_catches_invalid_config() -> None:
    # Missing IDENTITY_AUTH and invalid tenant_key
    invalid_spec = UniversityOnboardingSpec(
        name_ar="جامعة تجريبية",
        tenant_key="INVALID TENANT KEY WITH SPACES!",
        base_url="https://sis.example.edu",
        supported_capabilities=[SISCapability.OFFERINGS_READ],  # Missing IDENTITY_AUTH & STUDENT_PROFILE_READ
    )

    result = OnboardingDiagnosticsEngine.validate_spec(invalid_spec)
    assert result.valid is False
    assert any("tenant_key" in e for e in result.errors)
    assert any("IDENTITY_AUTH" in e for e in result.errors)
    assert any("STUDENT_PROFILE_READ" in e for e in result.errors)


def test_onboarding_diagnostics_live_readiness() -> None:
    tenant = UniversityTenant(
        id=UUID(UNI_A_ID),
        tenant_key="zarqa",
        name_ar="جامعة الزرقاء",
        country="JO",
        status=TenantStatus.ACTIVE,
    )
    config = UniversityIntegrationConfig(
        university_id=UUID(UNI_A_ID),
        provider_type="generic_rest",
        base_url="https://fake-university-aqdn.onrender.com",
        supported_capabilities=[
            SISCapability.IDENTITY_AUTH,
            SISCapability.STUDENT_PROFILE_READ,
            SISCapability.OFFERINGS_READ,
            SISCapability.GRADES_READ,
        ],
        active=True,
    )
    health = HealthResult(
        status="HEALTHY",
        connectivity=True,
        latency_ms=45.2,
    )

    report = OnboardingDiagnosticsEngine.evaluate_live_readiness(
        tenant=tenant,
        config=config,
        health=health,
        declared_capabilities=set(config.supported_capabilities),
        mappings_by_type={"FACULTY": 7, "MAJOR": 17, "PLAN": 17, "COURSE": 120},
        has_grading_policy=True,
    )

    assert report.overall_readiness == "READY"
    assert report.tenant_key == "zarqa"
    assert all(c.status == "PASS" for c in report.checks)


# --- 6. Multi-University Tenant Isolation ---

def test_multi_university_alias_isolation() -> None:
    """Aliases for University A must never appear in search for University B."""
    course = UniversalCourseIdentity(
        canonical_id="c1",
        canonical_code="0100101",
        name_ar="التربية الوطنية",
    )

    alias_a = InstitutionalCourseAlias(
        university_id=UNI_A_ID,
        canonical_course_code="0100101",
        alias_name_ar="المواطنة الصالحة",
    )

    resolver_b = CourseAliasResolver(
        university_id=UNI_B_ID,
        courses=[course],
        aliases=[],
    )
    # Attempt to inject alias from University A into University B resolver
    resolver_b.add_alias(alias_a)

    # University B must NOT match on University A's alias
    results_b = resolver_b.search_courses("المواطنة")
    assert len(results_b) == 0


# --- 7. Academic AI System Instruction Grounding ---

def test_ai_system_instruction_incorporates_institutional_context() -> None:
    context = InstitutionalContext(
        university_id=UNI_A_ID,
        university_name_ar="جامعة الزرقاء",
        university_name_en="Zarqa University",
        grading_scale_description="نظام العلامات المئوي (0-100) والحد الأدنى للنجاح 50",
        tenant_key="zarqa",
    )

    instruction = build_conversation_system_instruction(context)
    assert "جامعة الزرقاء" in instruction
    assert "نظام العلامات المئوي (0-100)" in instruction
    assert "AI explains; deterministic rules decide." in instruction
    assert "Never cite or cross-pollinate policies from another university." in instruction
