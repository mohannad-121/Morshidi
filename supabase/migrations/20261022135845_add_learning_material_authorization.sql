-- University-, curriculum-version-, course-, and material-scoped learning content.
-- AI EXPLAINS — DETERMINISTIC RELATIONSHIPS AUTHORIZE.
-- Files remain outside public web roots and are delivered only after an owner-scoped check.

begin;

create table public.learning_materials (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete restrict,
  course_id uuid not null,
  material_key text not null check (material_key ~ '^[a-z0-9][a-z0-9._/-]{0,199}$'),
  title_ar text not null check (btrim(title_ar) <> ''),
  title_en text check (title_en is null or btrim(title_en) <> ''),
  description_ar text,
  description_en text,
  material_type text not null check (material_type in ('chapter', 'lecture', 'worksheet', 'reference')),
  chapter_number numeric(6, 2) check (chapter_number is null or chapter_number > 0),
  display_order integer not null default 0 check (display_order >= 0),
  file_name text not null check (
    btrim(file_name) <> ''
    and file_name = pg_catalog.regexp_replace(file_name, '^.*[\\/]', '')
    and file_name not like '%..%'
  ),
  mime_type text not null check (mime_type in (
    'application/pdf',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  )),
  byte_size bigint not null check (byte_size > 0 and byte_size <= 52428800),
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  storage_provider text not null check (storage_provider in ('local_private', 'supabase_private')),
  storage_bucket text,
  object_key text not null check (
    char_length(object_key) <= 400
    and object_key ~ '^[a-z0-9][a-z0-9._/-]*$'
    and object_key not like '%..%'
    and object_key not like '/%'
  ),
  version_label text not null check (btrim(version_label) <> ''),
  publication_status text not null default 'draft'
    check (publication_status in ('draft', 'review_required', 'published', 'retired')),
  published_at timestamptz,
  source_reference text not null check (btrim(source_reference) <> ''),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (university_id, material_key, version_label),
  unique (id, university_id, course_id),
  foreign key (course_id, university_id)
    references public.courses(id, university_id) on delete restrict,
  check ((storage_provider = 'supabase_private') = (storage_bucket is not null)),
  check (publication_status <> 'published' or published_at is not null)
);

create table public.learning_material_authorizations (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete restrict,
  study_plan_id uuid not null,
  course_id uuid not null,
  material_id uuid not null,
  authorization_status text not null default 'draft'
    check (authorization_status in ('draft', 'published', 'revoked')),
  valid_from date,
  valid_to date,
  source_reference text not null check (btrim(source_reference) <> ''),
  approved_by text,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (study_plan_id, material_id),
  foreign key (study_plan_id, course_id)
    references public.study_plan_courses(study_plan_id, course_id) on delete restrict,
  foreign key (material_id, university_id, course_id)
    references public.learning_materials(id, university_id, course_id) on delete restrict,
  check (valid_to is null or valid_from is null or valid_to >= valid_from),
  check (
    (authorization_status = 'published' and approved_by is not null and approved_at is not null)
    or authorization_status <> 'published'
  )
);

create table public.learning_material_import_reviews (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete cascade,
  import_reference text not null check (btrim(import_reference) <> ''),
  supplied_course_reference text not null check (btrim(supplied_course_reference) <> ''),
  proposed_course_id uuid,
  review_status text not null default 'ambiguous'
    check (review_status in ('ambiguous', 'confirmed', 'rejected')),
  diagnostic_codes text[] not null default '{}',
  reviewed_by text,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (university_id, import_reference),
  foreign key (proposed_course_id, university_id)
    references public.courses(id, university_id) on delete restrict,
  check ((review_status = 'ambiguous') or (reviewed_by is not null and reviewed_at is not null)),
  check (review_status <> 'confirmed' or proposed_course_id is not null)
);

create index learning_materials_course_status_order_idx
  on public.learning_materials (university_id, course_id, publication_status, display_order, id);
create unique index learning_materials_storage_object_uidx
  on public.learning_materials (storage_provider, coalesce(storage_bucket, ''), object_key);
create index learning_material_authorizations_plan_status_idx
  on public.learning_material_authorizations
  (university_id, study_plan_id, authorization_status, course_id, material_id);
create index learning_material_import_reviews_queue_idx
  on public.learning_material_import_reviews (university_id, review_status, created_at, id);

create or replace function public.validate_learning_material_authorization_scope()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if not exists (
    select 1
    from public.study_plans sp
    join public.majors m on m.id = sp.major_id
    join public.faculties f on f.id = m.faculty_id
    where sp.id = new.study_plan_id
      and f.university_id = new.university_id
  ) then
    raise exception 'Learning-material authorization study plan belongs to another university';
  end if;
  return new;
end;
$$;

create trigger validate_learning_material_authorization_scope_on_write
before insert or update of university_id, study_plan_id, course_id, material_id
on public.learning_material_authorizations
for each row execute function public.validate_learning_material_authorization_scope();

create trigger set_learning_materials_updated_at
before update on public.learning_materials
for each row execute function public.set_updated_at();
create trigger set_learning_material_authorizations_updated_at
before update on public.learning_material_authorizations
for each row execute function public.set_updated_at();

revoke all on function public.validate_learning_material_authorization_scope()
from public, anon, authenticated;

-- Create metadata for durable private object storage without exposing any object policy.
-- Objects are uploaded and verified by the release migration command before rows are
-- switched from the backward-compatible local_private provider.
insert into storage.buckets (
  id, name, public, file_size_limit, allowed_mime_types
) values (
  'learning-materials',
  'learning-materials',
  false,
  52428800,
  array[
    'application/pdf',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ]::text[]
)
on conflict (id) do nothing;

do $$
begin
  if not exists (
    select 1 from storage.buckets b
    where b.id = 'learning-materials'
      and b.name = 'learning-materials'
      and b.public is false
      and b.file_size_limit = 52428800
      and b.allowed_mime_types @> array[
        'application/pdf',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      ]::text[]
  ) then
    raise exception 'learning-materials bucket exists with unsafe or incompatible settings';
  end if;
end;
$$;

alter table public.learning_materials enable row level security;
alter table public.learning_material_authorizations enable row level security;
alter table public.learning_material_import_reviews enable row level security;

revoke all on public.learning_materials,
  public.learning_material_authorizations,
  public.learning_material_import_reviews
from public, anon, authenticated, service_role;

grant select on public.learning_materials, public.learning_material_authorizations to authenticated;
grant select, insert, update, delete on public.learning_materials,
  public.learning_material_authorizations,
  public.learning_material_import_reviews to service_role;

create policy learning_materials_owner_scoped_read
on public.learning_materials for select to authenticated
using (
  publication_status = 'published'
  and exists (
    select 1
    from public.student_academic_profiles profile
    join public.learning_material_authorizations material_auth
      on material_auth.study_plan_id = profile.study_plan_id
     and material_auth.material_id = learning_materials.id
     and material_auth.university_id = learning_materials.university_id
     and material_auth.course_id = learning_materials.course_id
    where profile.owner_user_id = (select auth.uid())
      and material_auth.authorization_status = 'published'
      and (material_auth.valid_from is null or material_auth.valid_from <= current_date)
      and (material_auth.valid_to is null or material_auth.valid_to >= current_date)
  )
);

create policy learning_material_authorizations_owner_scoped_read
on public.learning_material_authorizations for select to authenticated
using (
  authorization_status = 'published'
  and (valid_from is null or valid_from <= current_date)
  and (valid_to is null or valid_to >= current_date)
  and exists (
    select 1
    from public.student_academic_profiles profile
    where profile.owner_user_id = (select auth.uid())
      and profile.study_plan_id = learning_material_authorizations.study_plan_id
  )
);

-- The user explicitly identified both preserved collections as AI Plan 12 uploads.
-- Course identity is resolved by authoritative university + canonical course code, never folder name.
insert into public.learning_materials (
  id, university_id, course_id, material_key, title_ar, title_en, material_type,
  chapter_number, display_order, file_name, mime_type, byte_size, sha256,
  storage_provider, object_key, version_label, publication_status, published_at,
  source_reference
)
select seed.id, '10000000-0000-0000-0000-000000000001'::uuid, course.id,
  seed.material_key, seed.title_ar, seed.title_en, seed.material_type,
  seed.chapter_number, seed.display_order, seed.file_name, seed.mime_type,
  seed.byte_size, seed.sha256, 'local_private', seed.object_key, 'legacy-v1',
  'published', now(), 'USER_CONFIRMED_AI_PLAN_12_LEGACY_UPLOAD_2026-10-22'
from (values
  ('f2a021cc-0038-5d10-8c4c-aff26e42eecc'::uuid, '1501112', 'computer-programming-2/chapter-01', 'الفصل 1', 'Chapter 1', 'chapter', 1.0, 1, 'chapter-01.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 7646010::bigint, '871aa2792a60c1b251c09496a92ff9266d0d4c2215bcdf6dc64718d48eef9ea2', 'zu/ai-p12/1501112/chapter-01.pptx'),
  ('241b584e-04e1-5d1c-83f8-e5f54b0d1b76'::uuid, '1501112', 'computer-programming-2/chapter-02', 'الفصل 2', 'Chapter 2', 'chapter', 2.0, 2, 'chapter-02.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 8052403::bigint, 'aaf506defc9e4a61c6eedabfa1c7156f0043904d2b3366b1a51758ed95de4e62', 'zu/ai-p12/1501112/chapter-02.pptx'),
  ('deae4a30-13ce-57cf-859c-42d73f630adc'::uuid, '1501112', 'computer-programming-2/chapter-03', 'الفصل 3', 'Chapter 3', 'chapter', 3.0, 3, 'chapter-03.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 8036710::bigint, '2c51a4ea1786c6895357fcb6f60b4768afff16ad01a4d523a7f4f0a53070c01b', 'zu/ai-p12/1501112/chapter-03.pptx'),
  ('72d338e1-9eca-5462-87ff-c1985ad10043'::uuid, '1505311', 'machine-learning/lecture-01', 'المحاضرة 1', 'Lecture 1', 'lecture', 1.0, 1, 'machine-learning-lecture-01.pdf', 'application/pdf', 2046516::bigint, 'b36c76903909b345f04a0be6fbe69b405d8380a0f41190e67c4a008e50e1ad57', 'zu/ai-p12/1505311/lecture-01.pdf'),
  ('46328848-445d-5729-9dae-beb01199173f'::uuid, '1505311', 'machine-learning/lecture-02-03', 'المحاضرتان 2–3', 'Lectures 2–3', 'lecture', 2.0, 2, 'machine-learning-lecture-02-03.pdf', 'application/pdf', 1038939::bigint, '754dc82e356b025ef0734d6179f3c85f6d34c66ee1202c8b8f264a1ad8347c47', 'zu/ai-p12/1505311/lecture-02-03.pdf'),
  ('291e0e64-e33b-5622-b62c-e1e616c90ad1'::uuid, '1505311', 'machine-learning/lecture-04', 'المحاضرة 4', 'Lecture 4', 'lecture', 4.0, 4, 'machine-learning-lecture-04.pdf', 'application/pdf', 820499::bigint, '86b62b0d65f0ef3135630d6bf322b15fa8f4cd4ae366d6de0e756b12e6e0969b', 'zu/ai-p12/1505311/lecture-04.pdf'),
  ('f815022a-64fc-54fc-9583-f8c36e69323c'::uuid, '1505311', 'machine-learning/lecture-05', 'المحاضرة 5', 'Lecture 5', 'lecture', 5.0, 5, 'machine-learning-lecture-05.pdf', 'application/pdf', 1749703::bigint, 'f8920de4c5abe6a5eec8b9b0bd5f0f390297a4d1a558319ee1789e40a87b3a16', 'zu/ai-p12/1505311/lecture-05.pdf'),
  ('aaf7f46d-7798-52b3-a168-ede426c3e450'::uuid, '1505311', 'machine-learning/lecture-06', 'المحاضرة 6', 'Lecture 6', 'lecture', 6.0, 6, 'machine-learning-lecture-06.pdf', 'application/pdf', 2274725::bigint, '1333b43014cc2924141d16d7842efa175c3ab317417544ca649c1e171c15db63', 'zu/ai-p12/1505311/lecture-06.pdf')
) as seed(id, course_code, material_key, title_ar, title_en, material_type,
          chapter_number, display_order, file_name, mime_type, byte_size, sha256, object_key)
join public.courses course
  on course.university_id = '10000000-0000-0000-0000-000000000001'::uuid
 and course.course_code = seed.course_code;

do $$
begin
  if (select count(*) from public.learning_materials
      where source_reference = 'USER_CONFIRMED_AI_PLAN_12_LEGACY_UPLOAD_2026-10-22') <> 8 then
    raise exception 'Expected all eight user-confirmed legacy learning materials to map canonically';
  end if;
end;
$$;

insert into public.learning_material_authorizations (
  id, university_id, study_plan_id, course_id, material_id,
  authorization_status, source_reference, approved_by, approved_at
)
select auth.id, material.university_id,
  '10000000-0000-0000-0000-000000000005'::uuid,
  material.course_id, material.id, 'published',
  'USER_CONFIRMED_AI_PLAN_12_LEGACY_UPLOAD_2026-10-22',
  'repository-migration', now()
from (values
  ('8d69a51d-c9fa-5e3a-bcd9-be7a8ae597e9'::uuid, 'f2a021cc-0038-5d10-8c4c-aff26e42eecc'::uuid),
  ('909ffbca-a6da-522e-b878-62a6dc33e19c'::uuid, '241b584e-04e1-5d1c-83f8-e5f54b0d1b76'::uuid),
  ('6f2ad1a8-e777-595d-b19b-896243fd93aa'::uuid, 'deae4a30-13ce-57cf-859c-42d73f630adc'::uuid),
  ('0401bba9-8782-5976-aaa9-5678b599dce8'::uuid, '72d338e1-9eca-5462-87ff-c1985ad10043'::uuid),
  ('a1ff9d61-6c20-5fa4-a66a-b67a3d395bbc'::uuid, '46328848-445d-5729-9dae-beb01199173f'::uuid),
  ('c7fffece-6b2f-51be-8480-c8ef1910da9a'::uuid, '291e0e64-e33b-5622-b62c-e1e616c90ad1'::uuid),
  ('95f57b97-1081-591f-8aa8-871e8357f84c'::uuid, 'f815022a-64fc-54fc-9583-f8c36e69323c'::uuid),
  ('440b39cd-b423-5289-96d9-a715a0fa1ec7'::uuid, 'aaf7f46d-7798-52b3-a168-ede426c3e450'::uuid)
) as auth(id, material_id)
join public.learning_materials material on material.id = auth.material_id;

do $$
begin
  if (select count(*) from public.learning_material_authorizations
      where source_reference = 'USER_CONFIRMED_AI_PLAN_12_LEGACY_UPLOAD_2026-10-22') <> 8 then
    raise exception 'Expected all eight AI Plan 12 material authorizations';
  end if;
end;
$$;

commit;
