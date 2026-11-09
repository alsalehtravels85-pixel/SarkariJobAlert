-- SarkariJobAlert Admit Card / Result fields
-- Safe, additive and re-runnable. Existing jobs and records are not deleted or modified.
alter table public.jobs add column if not exists exam_date date;
alter table public.jobs add column if not exists admit_card_release_date date;
alter table public.jobs add column if not exists admit_card_url text;
alter table public.jobs add column if not exists result_date date;
alter table public.jobs add column if not exists result_status text;
alter table public.jobs add column if not exists result_url text;
alter table public.jobs add column if not exists cutoff_details text;
alter table public.jobs add column if not exists merit_list_url text;
