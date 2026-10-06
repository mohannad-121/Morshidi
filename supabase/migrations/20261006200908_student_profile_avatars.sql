-- Private, owner-scoped profile images for authenticated students.
insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
values (
  'student-avatars',
  'student-avatars',
  false,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif']
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create policy "Students can read their own avatar"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'student-avatars'
  and owner_id = (select auth.uid()::text)
  and (storage.foldername(name))[1] = (select auth.uid()::text)
  and storage.filename(name) = 'avatar'
);

create policy "Students can upload their own avatar"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'student-avatars'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
  and storage.filename(name) = 'avatar'
);

create policy "Students can replace their own avatar"
on storage.objects
for update
to authenticated
using (
  bucket_id = 'student-avatars'
  and owner_id = (select auth.uid()::text)
  and (storage.foldername(name))[1] = (select auth.uid()::text)
  and storage.filename(name) = 'avatar'
)
with check (
  bucket_id = 'student-avatars'
  and owner_id = (select auth.uid()::text)
  and (storage.foldername(name))[1] = (select auth.uid()::text)
  and storage.filename(name) = 'avatar'
);
