-- SarkariJobAlert Admin CRUD repair (non-destructive; does not delete data)
-- Run in Supabase Dashboard > SQL Editor as project owner.
-- Admin access is restricted to authenticated Supabase users. Keep public signup disabled.

alter table public.jobs enable row level security;
grant select on table public.jobs to anon;
grant select, insert, update, delete on table public.jobs to authenticated;

drop policy if exists "Public can read published jobs" on public.jobs;
create policy "Public can read published jobs" on public.jobs
  for select to anon using (status = 'published');

drop policy if exists "Authenticated users manage jobs" on public.jobs;
create policy "Authenticated users manage jobs" on public.jobs
  for all to authenticated
  using ((select auth.uid()) is not null)
  with check ((select auth.uid()) is not null);
