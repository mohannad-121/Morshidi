import re
from pathlib import Path

from app.student_intelligence.diagnostic import DIAGNOSTIC_REASON_CODES


MIGRATION = (Path(__file__).parents[3] / "supabase" / "migrations" /
             "20261011190000_add_student_diagnostic_v1.sql")


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_diagnostic_migration_is_atomic_and_browser_closed() -> None:
    sql = _sql()
    assert sql.lstrip().startswith("-- student intelligence v2")
    assert "begin;" in sql and sql.rstrip().endswith("commit;")
    assert sql.count("enable row level security") == 3
    assert sql.count("owner to postgres") == 3
    assert sql.count("revoke all on public.student_diagnostic_") == 3
    assert "grant execute on function public.record_student_diagnostic_answer" in sql
    assert "to service_role" in sql


def test_diagnostic_migration_hardens_definers_and_closed_sessions() -> None:
    sql = _sql()
    assert sql.count("security definer") == 3
    assert sql.count("set search_path = ''") == 4
    assert sql.count("from public, anon, authenticated, service_role") == 4
    assert sql.count("from anon, authenticated, service_role") == 3
    assert "for update" in sql
    assert "unique(session_id, question_id)" in sql
    assert "unique(session_id, response_order)" in sql
    assert "diagnostic evidence is immutable" in sql
    assert "old.status in ('completed', 'abandoned')" in sql
    assert "jsonb_array_length(p_results) <> 5" in sql
    assert "grant select on public.student_diagnostic_responses to service_role" in sql
    assert "grant select, insert on public.student_diagnostic_responses" not in sql
    assert "grant update(status, current_question_id, updated_at)" in sql


def test_completion_minimum_and_exact_question_ten_static_contract() -> None:
    sql = _sql()
    assert "if next_order < 10 or next_order > 16 then" in sql
    assert "diagnostic completion requires 10 to 16 answers" in sql
    assert "next_order <= 10" not in sql


def test_question_sixteen_forces_completion_and_question_seventeen_is_impossible() -> None:
    sql = _sql()
    assert "actual_response_count <> s.question_count" in sql
    assert "diagnostic session response count mismatch" in sql
    assert "if next_order >= 16 then" in sql
    assert "diagnostic question 16 must complete the assessment" in sql
    assert "if next_order > 16 then" in sql
    assert "diagnostic maximum question count exceeded" in sql


def test_next_question_cannot_repeat_current_or_previous_question() -> None:
    sql = _sql()
    assert "if p_next_question_id = p_question_id then" in sql
    assert "r.session_id = s.id and r.question_id = p_next_question_id" in sql
    assert "diagnostic next question was already answered" in sql


def test_results_are_forbidden_while_continuing_and_required_on_completion() -> None:
    sql = _sql()
    assert "if p_results is not null then" in sql
    assert "diagnostic continuation must not include results" in sql
    assert "if p_results is null or pg_catalog.jsonb_typeof(p_results) <> 'array'" in sql
    assert "completed assessment requires results" in sql


def test_completion_requires_five_unique_domains_and_database_response_counts() -> None:
    sql = _sql()
    assert "jsonb_array_length(p_results) <> 5" in sql
    assert "count(distinct result->>'domain')" in sql
    assert "completed assessment requires five unique domains" in sql
    assert "r.session_id = s.id and r.domain = item->>'domain'" in sql
    assert "actual_response_count <> (item->>'response_count')::integer" in sql
    assert "diagnostic result response count mismatch" in sql
    assert "result_response_total <> next_order" in sql
    assert "diagnostic result response counts must equal answer count" in sql


def test_reason_codes_are_bounded_arrays_with_closed_vocabulary() -> None:
    sql = _sql()
    assert "jsonb_typeof(item->'reason_codes') is distinct from 'array'" in sql
    assert "jsonb_array_length(item->'reason_codes') not between 2 and 4" in sql
    allowlist = re.search(r"where reason not in \((.*?)\)\s*\)", sql, re.DOTALL)
    assert allowlist is not None
    assert set(re.findall(r"'([^']+)'", allowlist.group(1))) == {
        reason.lower() for reason in DIAGNOSTIC_REASON_CODES
    }
    assert "invalid diagnostic reason codes" in sql


def test_invalid_completion_rolls_back_current_answer_atomically() -> None:
    sql = _sql()
    answer_insert = sql.index("insert into public.student_diagnostic_responses")
    result_validation = sql.index("completed assessment requires results", answer_insert)
    completion_update = sql.index("set status='completed'", result_validation)
    assert answer_insert < result_validation < completion_update
    assert sql.lstrip().startswith("-- student intelligence v2")
    assert sql.rstrip().endswith("commit;")
