-- SarkariJobAlert Supabase schema
-- Run this whole file in Supabase Dashboard > SQL Editor.
create extension if not exists pgcrypto;

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(title) between 3 and 180),
  department text not null default '',
  category text not null check (category in ('Latest Jobs','Admit Card','Results','Answer Key','Admission','Syllabus')),
  vacancies text not null default '',
  last_date date,
  qualification text not null default '',
  fees text not null default '',
  age_limit text not null default '',
  selection_process text not null default '',
  notification_url text,
  apply_url text,
  description text not null default '',
  status text not null default 'draft' check (status in ('draft','published')),
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists jobs_public_list_idx on public.jobs(status, created_at desc);
alter table public.jobs enable row level security;

-- Anyone can read only published posts.
drop policy if exists "Public can read published jobs" on public.jobs;
create policy "Public can read published jobs" on public.jobs
for select to anon, authenticated using (status = 'published' or auth.uid() = created_by);

-- Only authenticated users can create posts as themselves.
drop policy if exists "Admin can insert own jobs" on public.jobs;
create policy "Admin can insert own jobs" on public.jobs
for insert to authenticated with check (auth.uid() = created_by);

-- Owner can edit own posts.
drop policy if exists "Admin can update own jobs" on public.jobs;
create policy "Admin can update own jobs" on public.jobs
for update to authenticated using (auth.uid() = created_by) with check (auth.uid() = created_by);

-- Owner can delete own posts.
drop policy if exists "Admin can delete own jobs" on public.jobs;
create policy "Admin can delete own jobs" on public.jobs
for delete to authenticated using (auth.uid() = created_by);

-- IMPORTANT:
-- Create your first admin user manually in Supabase Dashboard > Authentication > Users.
-- Do not enable public signups. If you later add more admins, adjust ownership/roles securely.
