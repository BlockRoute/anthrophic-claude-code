-- Verdant — Supabase schema
-- Run this in the Supabase SQL editor (or `supabase db push`) for cloud mode.
-- The app works fully without it (local mode); this enables accounts + sync.

-- Snapshot table: one JSON document per user holding their full app state.
-- Simple, robust, and conflict-free for a single-user-per-account app.
create table if not exists public.app_state (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  snapshot   jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.app_state enable row level security;

create policy "owner can read"   on public.app_state
  for select using (auth.uid() = user_id);
create policy "owner can insert" on public.app_state
  for insert with check (auth.uid() = user_id);
create policy "owner can update" on public.app_state
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Keep updated_at fresh.
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end; $$;

drop trigger if exists app_state_touch on public.app_state;
create trigger app_state_touch
  before update on public.app_state
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------------------
-- Optional normalized tables (left here for teams that outgrow the snapshot
-- model — the client currently uses app_state above). Uncomment to adopt.
-- ---------------------------------------------------------------------------
-- create table public.food_entries (
--   id uuid primary key default gen_random_uuid(),
--   user_id uuid not null references auth.users(id) on delete cascade,
--   date date not null,
--   name text not null,
--   calories int, protein int, carbs int, fat int,
--   source text, barcode text, created_at timestamptz default now()
-- );
