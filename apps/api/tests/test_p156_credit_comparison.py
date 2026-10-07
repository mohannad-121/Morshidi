"""Bounded, deterministic, credit-only strategy comparison."""

from decimal import Decimal

import pytest

from app.degree_path.credit_timeline import (AcademicTerm, ComparisonMode,
                                             compare_credit_timelines)


def compare(**changes):
    params = dict(required=Decimal(132), earned=Decimal(60), start_year=2026,
                  start_term=AcademicTerm.FIRST_SEMESTER)
    params.update(changes)
    return compare_credit_timelines(**params)


def test_three_distinct_named_views_are_deterministic_and_bounded():
    result = compare()
    assert result == compare()
    assert result.evaluated_scenarios == 12
    assert tuple(row.mode for row in result.scenarios) == tuple(ComparisonMode)
    assert all(row.timeline.initial_remaining_credits == 72 for row in result.scenarios)
    assert all(row.provenance == "MODELED_ACADEMIC_CALENDAR" for row in result.scenarios)
    assert all(row.difficulty_evidence == "NO_FUTURE_COURSE_ALLOCATION" for row in result.scenarios)
    assert any("Prerequisites" in note for note in result.limitations)


def test_fastest_and_lower_load_priorities_are_explicit_not_universal_best():
    fastest, balanced, lower = compare().scenarios
    assert fastest.total_modeled_terms <= balanced.total_modeled_terms
    assert fastest.total_modeled_terms <= lower.total_modeled_terms
    assert lower.timeline.regular_load == 12
    assert lower.timeline.summer_load == 0
    assert balanced.mode is ComparisonMode.BALANCED
    assert balanced.timeline.regular_load in (12, 15, 18)


def test_preference_match_and_summer_arithmetic():
    result = compare(preferred_regular_load=Decimal(15), preferred_summer_enabled=True,
                     preferred_summer_load=Decimal(6))
    assert result.scenarios[1].preference_match
    for row in result.scenarios:
        assert row.preference_match == (row.timeline.regular_load == 15
                                        and row.timeline.summer_load == 6)
        assert row.timeline.summer_load == 0 or 3 <= row.timeline.summer_load <= 9


def test_absent_preferences_never_claim_a_match_and_current_difficulty_only_informs_balance():
    assert not any(row.preference_match for row in compare().scenarios)
    cautious = compare(current_workload_risk=95, difficulty_evidence="CURRENT_ELIGIBLE_COURSES_ONLY")
    assert cautious.scenarios[1].timeline.regular_load <= compare().scenarios[1].timeline.regular_load
    assert cautious.scenarios[0].timeline == compare().scenarios[0].timeline
    assert cautious == compare(current_workload_risk=95, difficulty_evidence="CURRENT_ELIGIBLE_COURSES_ONLY")


def test_custom_summer_preference_remains_bounded_and_pace_match_is_not_universal_best():
    result = compare(preferred_regular_load=Decimal(15), preferred_summer_enabled=True,
                     preferred_summer_load=Decimal(4), graduation_pace=ComparisonMode.BALANCED)
    assert result.evaluated_scenarios == 15
    assert result.scenarios[1].timeline.summer_load == 4
    assert result.scenarios[1].preference_match
    assert not result.scenarios[0].preference_match


@pytest.mark.parametrize("invalid", [Decimal(2), Decimal(10)])
def test_invalid_summer_preference_is_rejected(invalid):
    with pytest.raises(ValueError):
        compare(preferred_summer_load=invalid)


@pytest.mark.parametrize("regular", [12, 15, 18])
@pytest.mark.parametrize("summer", [0, 3, 9])
def test_presets_are_valid_credit_timelines(regular, summer):
    from app.degree_path.credit_timeline import simulate_credit_timeline
    timeline = simulate_credit_timeline(
        required=Decimal(132), earned=Decimal(60), regular_load=Decimal(regular),
        summer_enabled=summer > 0, summer_load=Decimal(summer),
        start_year=2026, start_term=AcademicTerm.FIRST_SEMESTER)
    assert sum(term.planned_credits for term in timeline.terms) == 72


def test_scheduled_term_count_and_calendar_slots_reconciled():
    from app.degree_path.credit_timeline import simulate_credit_timeline

    # Case 1: required=132, earned=96, load=12, summer=false -> 3 study terms, credits [12, 12, 12]
    # First 2026, Second 2026, [skip Summer 2026], First 2027 -> 4 calendar slots
    tl_12 = simulate_credit_timeline(
        required=Decimal(132), earned=Decimal(96), regular_load=Decimal(12),
        summer_enabled=False, summer_load=Decimal(0),
        start_year=2026, start_term=AcademicTerm.FIRST_SEMESTER,
    )
    assert tl_12.initial_remaining_credits == Decimal(36)
    assert len(tl_12.terms) == 3
    assert [t.planned_credits for t in tl_12.terms] == [Decimal(12), Decimal(12), Decimal(12)]
    assert sum(t.planned_credits for t in tl_12.terms) == Decimal(36)

    # Case 2: required=132, earned=96, load=18, summer=false -> 2 study terms, credits [18, 18]
    tl_18 = simulate_credit_timeline(
        required=Decimal(132), earned=Decimal(96), regular_load=Decimal(18),
        summer_enabled=False, summer_load=Decimal(0),
        start_year=2026, start_term=AcademicTerm.FIRST_SEMESTER,
    )
    assert len(tl_18.terms) == 2
    assert [t.planned_credits for t in tl_18.terms] == [Decimal(18), Decimal(18)]
    assert sum(t.planned_credits for t in tl_18.terms) == Decimal(36)

    # Case 3: required=132, earned=96, load=15, summer=true (6cr) -> credits [15, 15, 6], 3 terms
    tl_15 = simulate_credit_timeline(
        required=Decimal(132), earned=Decimal(96), regular_load=Decimal(15),
        summer_enabled=True, summer_load=Decimal(6),
        start_year=2026, start_term=AcademicTerm.FIRST_SEMESTER,
    )
    assert len(tl_15.terms) == 3
    assert [t.planned_credits for t in tl_15.terms] == [Decimal(15), Decimal(15), Decimal(6)]
    assert sum(t.planned_credits for t in tl_15.terms) == Decimal(36)

    # Case 4: compare_credit_timelines with 132 required and 96 earned
    res = compare_credit_timelines(
        required=Decimal(132), earned=Decimal(96),
        start_year=2026, start_term=AcademicTerm.FIRST_SEMESTER,
    )
    for scenario in res.scenarios:
        assert scenario.scheduled_term_count == len(scenario.timeline.terms)
        assert scenario.total_modeled_terms == len(scenario.timeline.terms)
        assert sum(t.planned_credits for t in scenario.timeline.terms) == Decimal(36)
        # Skipped summer does not increment scheduled_term_count
        if not scenario.timeline.summer_enabled:
            assert scenario.scheduled_term_count == scenario.timeline.regular_semester_count

    fastest = next(s for s in res.scenarios if s.mode == ComparisonMode.FASTEST)
    assert fastest.scheduled_term_count == 2
    assert fastest.calendar_slots_elapsed == 2

    lower = next(s for s in res.scenarios if s.mode == ComparisonMode.LOWER_LOAD)
    assert lower.scheduled_term_count == 3
    assert lower.calendar_slots_elapsed == 4
