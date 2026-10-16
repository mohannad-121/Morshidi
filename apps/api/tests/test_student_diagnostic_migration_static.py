from pathlib import Path


ROOT = Path(__file__).parents[3] / "supabase" / "migrations"
V1 = ROOT / "20261011190000_add_student_diagnostic_v1.sql"
V2 = ROOT / "20261016090000_upgrade_student_diagnostic_v2.sql"


def _sql(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_diagnostic_migrations_remain_atomic_and_browser_closed() -> None:
    v1, v2 = _sql(V1), _sql(V2)
    assert v1.lstrip().startswith("-- student intelligence v2")
    assert v1.rstrip().endswith("commit;") and v2.lstrip().startswith("begin;")
    assert v2.rstrip().endswith("commit;")
    assert v1.count("enable row level security") == 3
    assert v1.count("revoke all on public.student_diagnostic_") == 3
    assert "grant execute on function public.record_student_diagnostic_answer" in v2
    assert "to service_role" in v2
    assert "to authenticated" not in v2 and "to anon" not in v2


def test_expand_migration_preserves_v1_rpc_and_adds_v2_overload() -> None:
    sql = _sql(V2)
    v1_signature = "uuid,uuid,text,text,text,text,boolean,text,jsonb"
    v2_signature = "uuid,uuid,text,text,text,text,boolean,integer,text,text,jsonb"
    assert "drop function" not in sql
    assert "create or replace function public.record_student_diagnostic_answer(" in sql
    assert "create function public.record_student_diagnostic_answer(" in sql
    assert sql.count("grant execute on function public.record_student_diagnostic_answer") == 2
    assert sql.count("revoke all on function public.record_student_diagnostic_answer") == 2
    compact = "".join(sql.split())
    assert v1_signature in compact and v2_signature in compact
    assert "s.assessment_version <> 'quick_diagnostic_v1'" in sql
    assert "s.assessment_version <> 'quick_diagnostic_v2'" in sql


def test_v2_captures_bounded_timing_and_self_confidence() -> None:
    sql = _sql(V2)
    assert "add column response_time_ms integer not null" in sql
    assert "response_time_ms between 0 and 1800000" in sql
    assert "add column self_confidence text not null" in sql
    assert "self_confidence in ('low', 'medium', 'high')" in sql
    assert "p_response_time_ms integer, p_self_confidence text" in sql
    assert "p_response_time_ms not between 0 and 1800000" in sql


def test_v2_requires_exactly_thirty_and_six_per_domain() -> None:
    sql = _sql(V2)
    assert "question_count between 0 and 30" in sql
    assert "response_order between 1 and 30" in sql
    assert "next_order <> 30" in sql
    assert "diagnostic completion requires exactly 30 answers" in sql
    assert "next_order >= 30" in sql and "question 30 must complete" in sql
    assert "actual_response_count <> 6" in sql
    assert "each diagnostic domain requires six responses" in sql
    assert "<> 2" in sql and "each domain requires two responses per difficulty" in sql
    assert "result_response_total <> 30" in sql


def test_v2_completion_and_replay_guards_are_inside_atomic_rpc() -> None:
    sql = _sql(V2)
    assert "for update" in sql
    assert "actual_response_count <> s.question_count" in sql
    assert "p_next_question_id = p_question_id or exists" in sql
    assert "diagnostic next question must be unanswered" in sql
    assert "diagnostic continuation must not include results" in sql
    answer_insert = sql.index("insert into public.student_diagnostic_responses")
    validation = sql.index("completed assessment requires five results", answer_insert)
    completion = sql.index("set status='completed'", validation)
    assert answer_insert < validation < completion


def test_v2_result_codes_and_reasoning_patterns_are_closed_vocabularies() -> None:
    sql = _sql(V2)
    assert "jsonb_typeof(item->'reason_codes') is distinct from 'array'" in sql
    assert "jsonb_typeof(item->'reasoning_patterns') is distinct from 'array'" in sql
    for code in (
        "modeled_diagnostic_baseline", "unrealistically_fast", "repetitive_option_pattern",
        "random_looking_pattern", "strong_systematic_reasoning", "careful_but_slower",
        "self_confidence_above_evidence", "difficulty_with_multi_step_problems",
    ):
        assert f"'{code}'" in sql
    assert "invalid diagnostic bounded evidence codes" in sql


def test_v2_preserves_closed_session_and_child_immutability_from_v1() -> None:
    v1 = _sql(V1)
    assert "diagnostic evidence is immutable" in v1
    assert "old.status in ('completed', 'abandoned')" in v1
    assert "unique(session_id, question_id)" in v1
    assert "unique(session_id, response_order)" in v1
    assert "grant select, insert on public.student_diagnostic_sessions to service_role" in v1
    assert "grant select, insert on public.student_diagnostic_responses" not in v1
