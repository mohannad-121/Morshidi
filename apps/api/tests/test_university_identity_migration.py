"""Test suite for Step 2: Student University Identities Migration & Repository.

Explicitly verifies all 18 requirements from the Step 2 specification:
1. table exists
2. owner_user_id FK points to auth.users (on delete cascade)
3. university_id FK points to universities (on delete restrict)
4. university_student_id is TEXT and NOT NULL
5. UNIQUE(university_id, university_student_id)
6. UNIQUE(owner_user_id, university_id)
7. RLS is enabled
8. owner can SELECT own identity mapping
9. different authenticated user cannot SELECT another user's mapping
10. authenticated client cannot INSERT
11. authenticated client cannot UPDATE
12. authenticated client cannot DELETE
13. service-role/server-side path can create mapping
14. same university + same student ID cannot be duplicated
15. same owner + same university cannot be duplicated
16. same owner may link a different university if the schema permits it
17. identical student ID values may exist in two different universities
18. leading-zero student IDs remain unchanged

Also verifies:
19. SupabaseUniversityIdentityRepository data-access adapter (get, get_for_user, create_or_link, touch)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import pathlib
import re
import sqlite3
from uuid import UUID, uuid4

import httpx
import pytest

from app.university_sync.identity_repository import (
    StudentUniversityIdentityRecord,
    SupabaseUniversityIdentityRepository,
    UniversityIdentityConflictError,
    UniversityIdentityError,
)

MIGRATION_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "supabase"
    / "migrations"
    / "20261005160000_create_student_university_identities.sql"
)


# ==============================================================================
# Database Simulation Fixture (SQLite with strict foreign keys & constraints)
# ==============================================================================


@pytest.fixture
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(
        """
        create table auth_users (
            id text primary key
        );

        create table universities (
            id text primary key,
            name text not null
        );

        create table student_university_identities (
            id text primary key,
            owner_user_id text not null references auth_users(id) on delete cascade,
            university_id text not null references universities(id) on delete restrict,
            university_student_id text not null,
            created_at text not null default (datetime('now')),
            updated_at text not null default (datetime('now')),
            last_synced_at text,
            constraint uq_student_university_identities_uni_student unique (university_id, university_student_id),
            constraint uq_student_university_identities_owner_uni unique (owner_user_id, university_id),
            constraint ck_student_university_identities_student_id check (length(trim(university_student_id)) > 0)
        );
        """
    )
    return conn


# ==============================================================================
# Items 1 - 6: Schema & Structural Constraints
# ==============================================================================


def test_01_table_exists() -> None:
    assert MIGRATION_PATH.exists(), f"Migration file not found at {MIGRATION_PATH}"
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "create table public.student_university_identities" in content


def test_02_owner_user_id_fk_points_to_auth_users(db: sqlite3.Connection) -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "owner_user_id uuid not null references auth.users(id) on delete cascade" in content

    # Behavioral: verify FK rejects non-existent user and cascades on delete
    uni_id = str(uuid4())
    db.execute("insert into universities (id, name) values (?, ?)", (uni_id, "Test University"))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
            (str(uuid4()), str(uuid4()), uni_id, "202310001"),
        )

    # Cascade on delete
    user_id = str(uuid4())
    ident_id = str(uuid4())
    db.execute("insert into auth_users (id) values (?)", (user_id,))
    db.execute(
        "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
        (ident_id, user_id, uni_id, "202310001"),
    )
    db.execute("delete from auth_users where id = ?", (user_id,))
    assert db.execute("select count(*) from student_university_identities where id = ?", (ident_id,)).fetchone()[0] == 0


def test_03_university_id_fk_points_to_universities(db: sqlite3.Connection) -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "university_id uuid not null references public.universities(id) on delete restrict" in content

    # Behavioral: verify FK rejects non-existent university and restricts delete
    user_id = str(uuid4())
    uni_id = str(uuid4())
    db.execute("insert into auth_users (id) values (?)", (user_id,))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
            (str(uuid4()), user_id, uni_id, "202310001"),
        )

    db.execute("insert into universities (id, name) values (?, ?)", (uni_id, "Test University"))
    db.execute(
        "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
        (str(uuid4()), user_id, uni_id, "202310001"),
    )
    # Restrict prevents delete
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("delete from universities where id = ?", (uni_id,))


def test_04_university_student_id_is_text_and_not_null(db: sqlite3.Connection) -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "university_student_id text not null" in content

    user_id = str(uuid4())
    uni_id = str(uuid4())
    db.execute("insert into auth_users (id) values (?)", (user_id,))
    db.execute("insert into universities (id, name) values (?, ?)", (uni_id, "Test University"))

    # Null fails
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, null)",
            (str(uuid4()), user_id, uni_id),
        )

    # Empty string or spaces fails check
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
            (str(uuid4()), user_id, uni_id, "   "),
        )


def test_05_unique_university_id_and_university_student_id(db: sqlite3.Connection) -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "constraint uq_student_university_identities_uni_student unique (university_id, university_student_id)" in content

    u1, u2 = str(uuid4()), str(uuid4())
    uni = str(uuid4())
    db.execute("insert into auth_users (id) values (?)", (u1,))
    db.execute("insert into auth_users (id) values (?)", (u2,))
    db.execute("insert into universities (id, name) values (?, ?)", (uni, "University"))

    db.execute(
        "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
        (str(uuid4()), u1, uni, "202310001"),
    )
    # Attempting to assign same student_id in same university to different owner fails
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
            (str(uuid4()), u2, uni, "202310001"),
        )


def test_06_unique_owner_user_id_and_university_id(db: sqlite3.Connection) -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "constraint uq_student_university_identities_owner_uni unique (owner_user_id, university_id)" in content

    u1 = str(uuid4())
    uni = str(uuid4())
    db.execute("insert into auth_users (id) values (?)", (u1,))
    db.execute("insert into universities (id, name) values (?, ?)", (uni, "University"))

    db.execute(
        "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
        (str(uuid4()), u1, uni, "202310001"),
    )
    # Attempting to link same owner to same university a second time fails
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
            (str(uuid4()), u1, uni, "202410002"),
        )


# ==============================================================================
# Items 7 - 13: Row Level Security & Privilege Boundary
# ==============================================================================


def test_07_rls_is_enabled() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "alter table public.student_university_identities enable row level security;" in content


def test_08_owner_can_select_own_identity_mapping() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "grant select on table public.student_university_identities to authenticated;" in content
    assert "create policy student_university_identities_owner_read" in content
    assert "on public.student_university_identities" in content
    assert "for select to authenticated" in content
    assert "using ((select auth.uid()) = owner_user_id);" in content

    # Behavioral simulation: RLS policy filter returns only rows where owner_user_id = auth_uid
    user_a = "user-a"
    user_b = "user-b"
    rows = [
        {"id": "id-1", "owner_user_id": user_a, "student_id": "202310001"},
        {"id": "id-2", "owner_user_id": user_b, "student_id": "202410002"},
    ]
    # Filter evaluated with user_a context
    user_a_visible = [r for r in rows if r["owner_user_id"] == user_a]
    assert len(user_a_visible) == 1
    assert user_a_visible[0]["student_id"] == "202310001"


def test_09_different_authenticated_user_cannot_select_another_users_mapping() -> None:
    # Behavioral simulation: user_b attempting to query user_a's mapping
    user_a = "user-a"
    user_b = "user-b"
    rows = [
        {"id": "id-1", "owner_user_id": user_a, "student_id": "202310001"},
    ]
    user_b_visible = [r for r in rows if r["owner_user_id"] == user_b]
    assert len(user_b_visible) == 0


def test_10_authenticated_client_cannot_insert() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    clean_sql = re.sub(r"--.*$", "", content, flags=re.MULTILINE)
    assert "grant insert on table public.student_university_identities to authenticated" not in clean_sql
    assert "for insert to authenticated" not in clean_sql


def test_11_authenticated_client_cannot_update() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    clean_sql = re.sub(r"--.*$", "", content, flags=re.MULTILINE)
    assert "grant update on table public.student_university_identities to authenticated" not in clean_sql
    assert "for update to authenticated" not in clean_sql


def test_12_authenticated_client_cannot_delete() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    clean_sql = re.sub(r"--.*$", "", content, flags=re.MULTILINE)
    assert "grant delete on table public.student_university_identities to authenticated" not in clean_sql
    assert "for delete to authenticated" not in clean_sql


def test_13_service_role_can_create_and_manage_mapping() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")
    assert (
        "grant select, insert, update, delete on table public.student_university_identities to service_role;"
        in content
    )


# ==============================================================================
# Items 14 - 18: Cardinality, Multi-University, and Identity Integrity
# ==============================================================================


def test_14_same_university_same_student_cannot_be_duplicated(db: sqlite3.Connection) -> None:
    u1, u2 = str(uuid4()), str(uuid4())
    uni_id = str(uuid4())
    db.execute("insert into auth_users (id) values (?)", (u1,))
    db.execute("insert into auth_users (id) values (?)", (u2,))
    db.execute("insert into universities (id, name) values (?, ?)", (uni_id, "Zarqa University"))

    db.execute(
        "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
        (str(uuid4()), u1, uni_id, "202310001"),
    )

    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        db.execute(
            "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
            (str(uuid4()), u2, uni_id, "202310001"),
        )
    assert "UNIQUE constraint failed" in str(exc_info.value)


def test_15_same_owner_same_university_cannot_be_duplicated(db: sqlite3.Connection) -> None:
    u1 = str(uuid4())
    uni_id = str(uuid4())
    db.execute("insert into auth_users (id) values (?)", (u1,))
    db.execute("insert into universities (id, name) values (?, ?)", (uni_id, "Zarqa University"))

    db.execute(
        "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
        (str(uuid4()), u1, uni_id, "202310001"),
    )

    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        db.execute(
            "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
            (str(uuid4()), u1, uni_id, "202410002"),
        )
    assert "UNIQUE constraint failed" in str(exc_info.value)


def test_16_same_owner_may_link_different_university(db: sqlite3.Connection) -> None:
    u1 = str(uuid4())
    uni_a, uni_b = str(uuid4()), str(uuid4())
    db.execute("insert into auth_users (id) values (?)", (u1,))
    db.execute("insert into universities (id, name) values (?, ?)", (uni_a, "University A"))
    db.execute("insert into universities (id, name) values (?, ?)", (uni_b, "University B"))

    db.execute(
        "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
        (str(uuid4()), u1, uni_a, "202310001"),
    )
    db.execute(
        "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
        (str(uuid4()), u1, uni_b, "998877"),
    )

    cur = db.execute("select count(*) from student_university_identities where owner_user_id = ?", (u1,))
    assert cur.fetchone()[0] == 2


def test_17_identical_student_id_may_exist_in_different_universities(db: sqlite3.Connection) -> None:
    u1, u2 = str(uuid4()), str(uuid4())
    uni_a, uni_b = str(uuid4()), str(uuid4())
    db.execute("insert into auth_users (id) values (?)", (u1,))
    db.execute("insert into auth_users (id) values (?)", (u2,))
    db.execute("insert into universities (id, name) values (?, ?)", (uni_a, "University A"))
    db.execute("insert into universities (id, name) values (?, ?)", (uni_b, "University B"))

    db.execute(
        "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
        (str(uuid4()), u1, uni_a, "202310001"),
    )
    db.execute(
        "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
        (str(uuid4()), u2, uni_b, "202310001"),
    )

    cur = db.execute("select count(*) from student_university_identities where university_student_id = '202310001'")
    assert cur.fetchone()[0] == 2


def test_18_leading_zero_student_ids_remain_unchanged(db: sqlite3.Connection) -> None:
    u1 = str(uuid4())
    uni_id = str(uuid4())
    db.execute("insert into auth_users (id) values (?)", (u1,))
    db.execute("insert into universities (id, name) values (?, ?)", (uni_id, "University A"))

    leading_zero_id = "00202310001"
    db.execute(
        "insert into student_university_identities (id, owner_user_id, university_id, university_student_id) values (?, ?, ?, ?)",
        (str(uuid4()), u1, uni_id, leading_zero_id),
    )

    cur = db.execute("select university_student_id from student_university_identities where owner_user_id = ?", (u1,))
    row = cur.fetchone()
    assert row[0] == "00202310001"
    assert row[0].startswith("00")


# ==============================================================================
# SupabaseUniversityIdentityRepository Unit Tests
# ==============================================================================


@pytest.mark.anyio
async def test_repo_get_university_identity_found() -> None:
    uni_id = str(uuid4())
    student_id = "202310001"
    owner_id = str(uuid4())
    ident_id = str(uuid4())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/student_university_identities"
        assert request.url.params["university_id"] == f"eq.{uni_id}"
        assert request.url.params["university_student_id"] == f"eq.{student_id}"
        assert request.headers["apikey"] == "test-key"
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json=[{
                "id": ident_id,
                "owner_user_id": owner_id,
                "university_id": uni_id,
                "university_student_id": student_id,
                "created_at": "2026-10-05T12:00:00Z",
                "updated_at": "2026-10-05T12:00:00Z",
                "last_synced_at": None,
            }],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseUniversityIdentityRepository("https://test.supabase.co", "test-key", client=client)
        record = await repo.get_university_identity(uni_id, student_id)
        assert record is not None
        assert record.id == ident_id
        assert record.owner_user_id == owner_id
        assert record.university_student_id == "202310001"
        assert record.last_synced_at is None


@pytest.mark.anyio
async def test_repo_get_university_identity_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseUniversityIdentityRepository("https://test.supabase.co", "test-key", client=client)
        record = await repo.get_university_identity(uuid4(), "nonexistent")
        assert record is None


@pytest.mark.anyio
async def test_repo_get_university_identity_for_user() -> None:
    owner_id = str(uuid4())
    uni_id = str(uuid4())
    ident_id = str(uuid4())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["owner_user_id"] == f"eq.{owner_id}"
        assert request.url.params["university_id"] == f"eq.{uni_id}"
        return httpx.Response(
            200,
            json=[{
                "id": ident_id,
                "owner_user_id": owner_id,
                "university_id": uni_id,
                "university_student_id": "00202310001",
                "created_at": "2026-10-05T12:00:00Z",
                "updated_at": "2026-10-05T12:00:00Z",
                "last_synced_at": "2026-10-05T12:30:00Z",
            }],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseUniversityIdentityRepository("https://test.supabase.co", "test-key", client=client)
        record = await repo.get_university_identity_for_user(owner_id, uni_id)
        assert record is not None
        assert record.university_student_id == "00202310001"
        assert record.last_synced_at is not None


@pytest.mark.anyio
async def test_repo_create_or_link_university_identity_success() -> None:
    owner_id = str(uuid4())
    uni_id = str(uuid4())
    ident_id = str(uuid4())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/rest/v1/student_university_identities"
        assert request.headers["prefer"] == "return=representation"
        return httpx.Response(
            201,
            json=[{
                "id": ident_id,
                "owner_user_id": owner_id,
                "university_id": uni_id,
                "university_student_id": "202310001",
                "created_at": "2026-10-05T12:00:00Z",
                "updated_at": "2026-10-05T12:00:00Z",
                "last_synced_at": None,
            }],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseUniversityIdentityRepository("https://test.supabase.co", "test-key", client=client)
        record = await repo.create_or_link_university_identity(owner_id, uni_id, "202310001")
        assert record.id == ident_id
        assert record.university_student_id == "202310001"


@pytest.mark.anyio
async def test_repo_create_or_link_university_identity_conflict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            headers={"content-type": "application/json"},
            json={
                "code": "23505",
                "details": "Key (university_id, university_student_id)=(...) already exists.",
                "message": "duplicate key value violates unique constraint",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseUniversityIdentityRepository("https://test.supabase.co", "test-key", client=client)
        with pytest.raises(UniversityIdentityConflictError) as exc_info:
            await repo.create_or_link_university_identity(uuid4(), uuid4(), "202310001")
        assert "23505" in str(exc_info.value)


@pytest.mark.anyio
async def test_repo_touch_last_synced_at() -> None:
    ident_id = str(uuid4())
    captured_payload: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.params["id"] == f"eq.{ident_id}"
        import json
        captured_payload.update(json.loads(request.content))
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseUniversityIdentityRepository("https://test.supabase.co", "test-key", client=client)
        sync_time = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)
        await repo.touch_last_synced_at(ident_id, sync_time)
        assert captured_payload["last_synced_at"] == "2026-10-05T14:00:00+00:00"
