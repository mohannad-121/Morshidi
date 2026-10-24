-- The unscoped RPC has been revoked since university-scoped notifications
-- shipped. The application uses ingest_university_event_scoped exclusively.
-- Removing the dead function eliminates an invalid/stale privileged surface
-- while retaining all scoped event, notification, webhook, and SSE contracts.

begin;

do $$
begin
  if to_regprocedure('public.ingest_university_event_scoped(uuid,jsonb)') is null then
    raise exception 'scoped university event RPC must exist before removing legacy RPC';
  end if;
end;
$$;

drop function public.ingest_university_event(jsonb);

commit;
