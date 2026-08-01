-- AEON cloud mirror. Local hash-chained runtime remains authoritative in Alpha.
create table if not exists public.aeon_events (
  event_id text primary key,
  cycle_id text not null,
  timestamp timestamptz not null,
  actor text not null,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  previous_event_hash text not null,
  event_hash text not null unique,
  signature text not null,
  created_at timestamptz not null default now()
);
create index if not exists aeon_events_cycle_idx on public.aeon_events(cycle_id, timestamp);

create table if not exists public.aeon_snapshots (
  snapshot_id uuid primary key default gen_random_uuid(),
  continuity_id text not null,
  snapshot jsonb not null,
  event_head_hash text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.aeon_experiments (
  experiment_id text primary key,
  record jsonb not null,
  integrity_hash text not null,
  created_at timestamptz not null default now()
);

alter table public.aeon_events enable row level security;
alter table public.aeon_snapshots enable row level security;
alter table public.aeon_experiments enable row level security;
-- No public policies: service-role backend only. Never expose service-role key to frontend.

