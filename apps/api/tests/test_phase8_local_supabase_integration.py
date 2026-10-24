"""Destructive, opt-in checks against the disposable local Supabase stack.

Run only after ``supabase db reset --local`` with::

    MORSHIDI_RUN_LOCAL_SUPABASE=1 pytest -q tests/test_phase8_local_supabase_integration.py

The suite creates synthetic Auth users, temporarily moves the eight seeded files to
private Storage, restarts only the local Storage container, and restores metadata.
It never reads hosted-project configuration.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import socket
import subprocess
import time
from uuid import uuid4

import httpx
import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("MORSHIDI_RUN_LOCAL_SUPABASE") != "1",
    reason="requires the disposable local Supabase stack",
)

ROOT = Path(__file__).resolve().parents[3]
PRIVATE_ROOT = ROOT / "apps" / "api" / "private" / "learning-materials"
DB_CONTAINER = "supabase_db_Morshidi"
STORAGE_CONTAINER = "supabase_storage_Morshidi"
AI_PLAN_ID = "10000000-0000-0000-0000-000000000005"
NURSING_PLAN_ID = "2a78bbbb-0dc0-5c46-8630-7a46e4179830"


def _run(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        input=input_text,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )


def _local_env() -> dict[str, str]:
    output = _run(
        "powershell.exe", "-NoProfile", "-Command", "supabase status --output env"
    ).stdout
    values: dict[str, str] = {}
    for line in output.splitlines():
        match = re.fullmatch(r'([A-Z0-9_]+)="(.*)"', line.strip())
        if match:
            values[match.group(1)] = match.group(2)
    required = {"API_URL", "ANON_KEY", "SERVICE_ROLE_KEY"}
    if not required <= values.keys():
        raise AssertionError("local Supabase status omitted required values")
    if values["API_URL"] != "http://127.0.0.1:54321":
        raise AssertionError("integration test refuses a non-local Supabase URL")
    return values


def _psql(sql: str) -> str:
    try:
        result = _run(
            "docker", "exec", "-i", DB_CONTAINER,
            "psql", "-X", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "postgres",
            input_text=sql,
        )
    except subprocess.CalledProcessError as error:
        raise AssertionError(error.stderr.strip() or "local PostgreSQL command failed") from error
    return result.stdout


def _headers(key: str, token: str | None = None) -> dict[str, str]:
    return {"apikey": key, "Authorization": f"Bearer {token or key}"}


def _signed_url(api_url: str, signed_path: str) -> str:
    if signed_path.startswith("/object/"):
        return f"{api_url}/storage/v1{signed_path}"
    if signed_path.startswith("/storage/v1/object/"):
        return f"{api_url}{signed_path}"
    raise AssertionError("Storage returned an unexpected signed path")


def _create_user(client: httpx.Client, api_url: str, service_key: str) -> tuple[str, str]:
    marker = uuid4().hex
    email = f"phase8-{marker}@example.invalid"
    password = f"Local-only-{marker}!Aa1"
    response = client.post(
        f"{api_url}/auth/v1/admin/users",
        headers=_headers(service_key),
        json={"email": email, "password": password, "email_confirm": True},
    )
    assert response.status_code == 200, response.text
    user_id = response.json()["id"]
    token_response = client.post(
        f"{api_url}/auth/v1/token?grant_type=password",
        headers={"apikey": service_key},
        json={"email": email, "password": password},
    )
    assert token_response.status_code == 200, token_response.text
    return user_id, token_response.json()["access_token"]


def _wait_http(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=1).status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise AssertionError(f"timed out waiting for {url}")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_catalog_grants_rls_constraints_and_policy_lifecycle() -> None:
    output = _psql(r"""
begin;
do $test$
declare
  package_id uuid := gen_random_uuid();
  first_version uuid := gen_random_uuid();
  second_version uuid := gen_random_uuid();
  source_id uuid;
  caught boolean;
begin
  if (select count(*) from public.learning_materials) <> 8
     or (select count(*) from public.learning_material_authorizations) <> 8 then
    raise exception 'seeded learning-material count mismatch';
  end if;
  if exists (
    select 1 from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and (c.relname like 'learning_material%' or c.relname like 'graduation_policy%')
      and c.relkind = 'r' and not c.relrowsecurity
  ) then
    raise exception 'required RLS is disabled';
  end if;
  if has_table_privilege('anon', 'public.learning_materials', 'select')
     or has_table_privilege('authenticated', 'public.graduation_policy_versions', 'select')
     or has_table_privilege('service_role', 'public.graduation_policy_audit_events', 'delete')
     or has_table_privilege('service_role', 'public.graduation_policy_audit_events', 'update')
     or has_table_privilege('service_role', 'public.graduation_policy_versions', 'truncate') then
    raise exception 'table grants are broader than intended';
  end if;
  if not has_table_privilege('authenticated', 'public.learning_materials', 'select')
     or not has_table_privilege('service_role', 'public.graduation_policy_versions', 'select,insert,update,delete')
     or not has_table_privilege('service_role', 'public.graduation_policy_audit_events', 'select,insert') then
    raise exception 'required table grants are missing';
  end if;
  if has_function_privilege('authenticated', 'public.validate_learning_material_authorization_scope()', 'execute')
     or has_function_privilege('anon', 'public.enforce_graduation_policy_version_lifecycle()', 'execute') then
    raise exception 'trigger functions remain client executable';
  end if;
  if not exists (
    select 1 from storage.buckets
    where id = 'learning-materials' and public is false and file_size_limit = 52428800
  ) then
    raise exception 'private learning-material bucket is missing or unsafe';
  end if;

  select sp.source_id into source_id from public.study_plans sp where sp.id =
    '10000000-0000-0000-0000-000000000005'::uuid;
  insert into public.graduation_policy_packages(id, university_id, policy_code, name_ar)
  values (package_id, '10000000-0000-0000-0000-000000000001', 'phase8-test', 'اختبار');
  insert into public.graduation_policy_versions(
    id, policy_package_id, version, effective_from, source_id, content_hash
  ) values (first_version, package_id, '1', date '2026-01-01', source_id, 'hash-1');
  insert into public.graduation_policy_applicability(
    policy_version_id, university_id, scope_level, study_plan_id
  ) values (
    first_version, '10000000-0000-0000-0000-000000000001', 'study_plan',
    '10000000-0000-0000-0000-000000000005'
  );
  insert into public.graduation_policy_rules(
    policy_version_id, rule_code, rule_kind, provenance, minimum_credits
  ) values (first_version, 'earned', 'min_earned_credits_for_course', 'synthetic-test', 90);

  update public.graduation_policy_versions set
    lifecycle_status = 'validated', validated_at = now(), validated_by = gen_random_uuid()
  where id = first_version;
  update public.graduation_policy_versions set
    lifecycle_status = 'approved', approved_at = now(), approved_by = gen_random_uuid()
  where id = first_version;

  caught := false;
  begin
    update public.graduation_policy_rules set minimum_credits = 91
    where policy_version_id = first_version;
  exception when others then caught := true;
  end;
  if not caught then raise exception 'approved policy rule remained mutable'; end if;

  insert into public.graduation_policy_versions(
    id, policy_package_id, version, effective_from, source_id, content_hash
  ) values (second_version, package_id, '2', date '2026-06-01', source_id, 'hash-2');
  insert into public.graduation_policy_applicability(
    policy_version_id, university_id, scope_level, study_plan_id
  ) values (
    second_version, '10000000-0000-0000-0000-000000000001', 'study_plan',
    '10000000-0000-0000-0000-000000000005'
  );
  insert into public.graduation_policy_rules(
    policy_version_id, rule_code, rule_kind, provenance, minimum_credits
  ) values (second_version, 'earned', 'min_earned_credits_for_course', 'synthetic-test', 90);
  update public.graduation_policy_versions set
    lifecycle_status = 'validated', validated_at = now(), validated_by = gen_random_uuid()
  where id = second_version;

  caught := false;
  begin
    update public.graduation_policy_versions set
      lifecycle_status = 'approved', approved_at = now(), approved_by = gen_random_uuid()
    where id = second_version;
  exception when others then caught := true;
  end;
  if not caught then raise exception 'overlapping approved policy version was accepted'; end if;

  update public.graduation_policy_versions set lifecycle_status = 'retired', effective_to = date '2026-12-31'
  where id = first_version;
  caught := false;
  begin
    update public.graduation_policy_versions set content_hash = 'changed' where id = first_version;
  exception when others then caught := true;
  end;
  if not caught then raise exception 'retired policy version remained mutable'; end if;
end
$test$;
rollback;
select 'PHASE8_DB_CONTRACTS_OK';
""")
    assert "PHASE8_DB_CONTRACTS_OK" in output


def test_two_university_overlapping_code_policy_content_and_revision_isolation() -> None:
    local = _local_env()
    os.environ.setdefault("MORSHIDI_LOCAL_SUPABASE_URL", local["API_URL"])
    os.environ.setdefault("MORSHIDI_LOCAL_SUPABASE_SERVER_KEY", local["SERVICE_ROLE_KEY"])
    os.environ.setdefault("MORSHIDI_LOCAL_SUPABASE_ANON_KEY", local["ANON_KEY"])
    from tests.p10_synthetic_fixture import seed_catalog

    with httpx.Client(timeout=30) as client:
        seed_catalog(client)
    output = _psql(r"""
begin;
do $test$
declare
  university_a constant uuid := 'f1000000-0000-0000-0000-000000000010';
  university_b constant uuid := 'f1000000-0000-0000-0000-000000000050';
  plan_a constant uuid := 'f1000000-0000-0000-0000-000000000023';
  plan_b constant uuid := 'f1000000-0000-0000-0000-000000000053';
  course_a uuid;
  course_b uuid;
  source_a uuid := gen_random_uuid();
  source_b uuid := gen_random_uuid();
  package_a uuid := gen_random_uuid();
  package_b uuid := gen_random_uuid();
  version_a uuid := gen_random_uuid();
  version_b uuid := gen_random_uuid();
  material_a uuid := gen_random_uuid();
  material_b uuid := gen_random_uuid();
  revision_a uuid := gen_random_uuid();
  major_a uuid;
  caught boolean := false;
begin
  select id into strict course_a from public.courses
  where university_id = university_a and course_code = 'CS101';
  select id into strict course_b from public.courses
  where university_id = university_b and course_code = 'CS101';
  if course_a = course_b then raise exception 'overlapping code collapsed across tenants'; end if;
  if (select total_credit_hours from public.study_plans where id = plan_a) <> 12
     or (select total_credit_hours from public.study_plans where id = plan_b) <> 3 then
    raise exception 'synthetic curricula are not distinct';
  end if;

  insert into public.academic_sources(id, university_id, source_type, title, source_status)
  values (source_a, university_a, 'manual_verification', 'Phase 8 synthetic A', 'active'),
         (source_b, university_b, 'manual_verification', 'Phase 8 synthetic B', 'active');
  insert into public.graduation_policy_packages(id, university_id, policy_code, name_ar)
  values (package_a, university_a, 'graduation-project', 'سياسة تجريبية أ'),
         (package_b, university_b, 'graduation-project', 'سياسة تجريبية ب');
  insert into public.graduation_policy_versions(
    id, policy_package_id, version, effective_from, source_id, content_hash
  ) values (version_a, package_a, '1', date '2026-01-01', source_a, 'synthetic-a'),
           (version_b, package_b, '1', date '2027-01-01', source_b, 'synthetic-b');
  insert into public.graduation_policy_applicability(
    policy_version_id, university_id, scope_level, study_plan_id
  ) values (version_a, university_a, 'study_plan', plan_a),
           (version_b, university_b, 'study_plan', plan_b);
  insert into public.graduation_policy_rules(
    policy_version_id, rule_code, rule_kind, provenance, minimum_credits
  ) values (version_a, 'project-credit-gate', 'min_earned_credits_for_course', 'synthetic-phase8', 9),
           (version_b, 'project-credit-gate', 'min_earned_credits_for_course', 'synthetic-phase8', 3);
  update public.graduation_policy_versions set lifecycle_status = 'validated',
    validated_at = now(), validated_by = gen_random_uuid() where id in (version_a, version_b);
  update public.graduation_policy_versions set lifecycle_status = 'approved',
    approved_at = now(), approved_by = gen_random_uuid() where id in (version_a, version_b);

  insert into public.learning_materials(
    id, university_id, course_id, material_key, title_ar, material_type, file_name,
    mime_type, byte_size, sha256, storage_provider, object_key, version_label,
    publication_status, published_at, source_reference
  ) values
    (material_a, university_a, course_a, 'phase8/cs101-a', 'فصل تجريبي أ', 'chapter',
     'a.pdf', 'application/pdf', 1, repeat('a', 64), 'local_private',
     'phase8/a/cs101.pdf', '1', 'published', now(), 'synthetic-phase8'),
    (material_b, university_b, course_b, 'phase8/cs101-b', 'فصل تجريبي ب', 'chapter',
     'b.pdf', 'application/pdf', 1, repeat('b', 64), 'local_private',
     'phase8/b/cs101.pdf', '1', 'published', now(), 'synthetic-phase8');
  insert into public.learning_material_authorizations(
    university_id, study_plan_id, course_id, material_id, authorization_status,
    source_reference, approved_by, approved_at
  ) values (university_a, plan_a, course_a, material_a, 'published', 'synthetic-phase8', 'phase8', now()),
           (university_b, plan_b, course_b, material_b, 'published', 'synthetic-phase8', 'phase8', now());

  begin
    insert into public.learning_material_authorizations(
      university_id, study_plan_id, course_id, material_id, authorization_status,
      source_reference, approved_by, approved_at
    ) values (university_b, plan_b, course_a, material_a, 'published', 'forgery', 'phase8', now());
  exception when others then caught := true;
  end;
  if not caught then raise exception 'cross-university material authorization succeeded'; end if;

  select major_id into strict major_a from public.study_plans where id = plan_a;
  insert into public.study_plans(id, major_id, plan_number, total_credit_hours, effective_year, status)
  values (revision_a, major_a, 'P10-SYNTHETIC-R2', 15, 2027, 'draft');
  if exists (select 1 from public.learning_material_authorizations where study_plan_id = revision_a)
     or exists (select 1 from public.graduation_policy_applicability where study_plan_id = revision_a) then
    raise exception 'new curriculum revision inherited governed content or policy';
  end if;
  if (select minimum_credits from public.graduation_policy_rules where policy_version_id = version_a) <> 9
     or (select minimum_credits from public.graduation_policy_rules where policy_version_id = version_b) <> 3 then
    raise exception 'tenant policy values were merged';
  end if;
  if (select count(*) from public.learning_material_authorizations
      where (university_id, study_plan_id, course_id, material_id) in (
        (university_a, plan_a, course_a, material_a),
        (university_b, plan_b, course_b, material_b))) <> 2 then
    raise exception 'tenant chapter libraries were not isolated';
  end if;
end
$test$;
rollback;
select 'PHASE8_MULTI_UNIVERSITY_OK';
""")
    assert "PHASE8_MULTI_UNIVERSITY_OK" in output


def test_real_auth_rls_private_storage_api_and_restart_durability() -> None:
    local = _local_env()
    api_url = local["API_URL"]
    anon_key = local["ANON_KEY"]
    service_key = local["SERVICE_ROLE_KEY"]
    users: list[str] = []
    uploaded: list[str] = []
    api_process: subprocess.Popen[str] | None = None

    with httpx.Client(timeout=30, follow_redirects=False) as client:
        try:
            identities = {}
            for label, plan_id in (
                ("ai", AI_PLAN_ID), ("nursing", NURSING_PLAN_ID), ("unknown", None)
            ):
                user_id, token = _create_user(client, api_url, service_key)
                users.append(user_id)
                identities[label] = (user_id, token)
                if plan_id:
                    response = client.post(
                        f"{api_url}/rest/v1/student_academic_profiles",
                        headers={**_headers(service_key), "Prefer": "return=minimal"},
                        json={"owner_user_id": user_id, "study_plan_id": plan_id},
                    )
                    assert response.status_code == 201, response.text

            for label, expected in (("ai", 8), ("nursing", 0), ("unknown", 0)):
                token = identities[label][1]
                response = client.get(
                    f"{api_url}/rest/v1/learning_materials?select=id",
                    headers=_headers(anon_key, token),
                )
                assert response.status_code == 200, response.text
                assert len(response.json()) == expected

            anonymous = client.get(
                f"{api_url}/rest/v1/learning_materials?select=id",
                headers=_headers(anon_key),
            )
            assert anonymous.status_code in {401, 403}
            policy_read = client.get(
                f"{api_url}/rest/v1/graduation_policy_versions?select=id",
                headers=_headers(anon_key, identities["ai"][1]),
            )
            assert policy_read.status_code in {401, 403}

            rows = client.get(
                f"{api_url}/rest/v1/learning_materials"
                "?select=id,object_key,mime_type,byte_size,sha256&order=object_key",
                headers=_headers(service_key),
            )
            assert rows.status_code == 200, rows.text
            assert len(rows.json()) == 8
            for row in rows.json():
                path = PRIVATE_ROOT / row["object_key"]
                payload = path.read_bytes()
                assert len(payload) == row["byte_size"]
                assert hashlib.sha256(payload).hexdigest() == row["sha256"]
                upload = client.post(
                    f"{api_url}/storage/v1/object/learning-materials/{row['object_key']}",
                    headers={**_headers(service_key), "Content-Type": row["mime_type"], "x-upsert": "false"},
                    content=payload,
                )
                assert upload.status_code == 200, upload.text
                uploaded.append(row["object_key"])

            update = client.patch(
                f"{api_url}/rest/v1/learning_materials?id=not.is.null",
                headers={**_headers(service_key), "Prefer": "return=minimal"},
                json={"storage_provider": "supabase_private", "storage_bucket": "learning-materials"},
            )
            assert update.status_code == 204, update.text

            first = rows.json()[0]
            direct_anon = client.get(
                f"{api_url}/storage/v1/object/learning-materials/{first['object_key']}",
                headers=_headers(anon_key),
            )
            direct_student = client.get(
                f"{api_url}/storage/v1/object/learning-materials/{first['object_key']}",
                headers=_headers(anon_key, identities["ai"][1]),
            )
            assert direct_anon.status_code in {400, 401, 403, 404}
            assert direct_student.status_code in {400, 401, 403, 404}

            signed = client.post(
                f"{api_url}/storage/v1/object/sign/learning-materials/{first['object_key']}",
                headers=_headers(service_key), json={"expiresIn": 5},
            )
            assert signed.status_code == 200, signed.text
            signed_url = _signed_url(api_url, signed.json()["signedURL"])
            download = client.get(signed_url)
            assert download.status_code == 200
            assert hashlib.sha256(download.content).hexdigest() == first["sha256"]
            time.sleep(6.1)
            assert client.get(signed_url).status_code in {400, 401, 403}

            port = _free_port()
            process_env = os.environ.copy()
            process_env.update({
                "APP_ENV": "test",
                "SUPABASE_URL": api_url,
                "SUPABASE_SECRET_KEY": service_key,
                "UNI_BASE_URL": "http://127.0.0.1:9",
                "UNI_CLIENT_SECRET": "",
                "UNI_SERVICE_KEY": "",
                "UNI_WEBHOOK_SECRET": "",
                "UNI_INTERNAL_AUTH_SECRET": "",
                "UNI_UNIVERSITY_ID": "",
                "ADVISOR_LLM_API_KEY": "",
                "POLICY_EMBEDDING_API_KEY": "",
            })
            python = ROOT / "apps" / "api" / ".venv311" / "Scripts" / "python.exe"
            api_process = subprocess.Popen(
                [str(python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=ROOT / "apps" / "api",
                env=process_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            _wait_http(f"http://127.0.0.1:{port}/health")
            ai_list = client.get(
                f"http://127.0.0.1:{port}/api/v1/me/learning-materials",
                headers={"Authorization": f"Bearer {identities['ai'][1]}"},
            )
            nursing_list = client.get(
                f"http://127.0.0.1:{port}/api/v1/me/learning-materials",
                headers={"Authorization": f"Bearer {identities['nursing'][1]}"},
            )
            assert ai_list.status_code == 200, ai_list.text
            assert sum(len(course["materials"]) for course in ai_list.json()["courses"]) == 8
            assert nursing_list.status_code == 200 and nursing_list.json()["courses"] == []
            material_id = ai_list.json()["courses"][0]["materials"][0]["material_id"]
            authorized_download = client.get(
                f"http://127.0.0.1:{port}/api/v1/me/learning-materials/{material_id}/download",
                headers={"Authorization": f"Bearer {identities['ai'][1]}"},
            )
            denied_download = client.get(
                f"http://127.0.0.1:{port}/api/v1/me/learning-materials/{material_id}/download",
                headers={"Authorization": f"Bearer {identities['nursing'][1]}"},
            )
            assert authorized_download.status_code == 307
            assert authorized_download.headers["location"].startswith(api_url)
            assert denied_download.status_code == 404

            _run("docker", "restart", STORAGE_CONTAINER)
            _wait_http(f"{api_url}/storage/v1/status", timeout=45)
            durable = client.post(
                f"{api_url}/storage/v1/object/sign/learning-materials/{first['object_key']}",
                headers=_headers(service_key), json={"expiresIn": 30},
            )
            assert durable.status_code == 200, durable.text
            assert client.get(_signed_url(api_url, durable.json()["signedURL"])).status_code == 200
        finally:
            if api_process is not None:
                api_process.terminate()
                try:
                    api_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    api_process.kill()
            client.patch(
                f"{api_url}/rest/v1/learning_materials?id=not.is.null",
                headers={**_headers(service_key), "Prefer": "return=minimal"},
                json={"storage_provider": "local_private", "storage_bucket": None},
            )
            for object_key in uploaded:
                client.delete(
                    f"{api_url}/storage/v1/object/learning-materials/{object_key}",
                    headers=_headers(service_key),
                )
            for user_id in users:
                client.delete(
                    f"{api_url}/auth/v1/admin/users/{user_id}",
                    headers=_headers(service_key),
                )


def test_legacy_public_chapter_tree_is_absent() -> None:
    public_chapters = ROOT / "apps" / "web" / "public" / "chapters"
    assert not public_chapters.exists() or not any(public_chapters.rglob("*.*"))
    assert not (ROOT / "apps" / "web" / "src" / "lib" / "chapters" / "discovery.ts").exists()
