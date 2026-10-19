begin;

alter table public.profiles add column if not exists plan text not null default 'free';
alter table public.profiles add column if not exists lifetime_since timestamptz;

create table if not exists public.tier_seats (
  tier text primary key,
  seat_limit integer not null check (seat_limit > 0),
  seats_sold integer not null default 0 check (seats_sold >= 0 and seats_sold <= seat_limit),
  updated_at timestamptz not null default now()
);

insert into public.tier_seats (tier, seat_limit) values
  ('founding_lifetime', 100), ('pro_lifetime', 250), ('team_lifetime', 50)
on conflict (tier) do nothing;

create table if not exists public.purchases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete restrict,
  tier text not null references public.tier_seats(tier),
  razorpay_order_id text not null unique,
  razorpay_payment_id text unique,
  amount_paise integer not null check (amount_paise > 0),
  currency text not null default 'INR' check (currency = 'INR'),
  status text not null default 'created' check (status in ('created', 'paid', 'failed')),
  consented_at timestamptz not null,
  consent_ip text not null,
  terms_version text not null,
  created_at timestamptz not null default now(),
  paid_at timestamptz
);
create index if not exists purchases_user_created_idx on public.purchases(user_id, created_at desc);

create table if not exists public.checkout_rate_limits (
  rate_key text not null,
  attempted_at timestamptz not null default now()
);
create index if not exists checkout_rate_limits_key_time_idx on public.checkout_rate_limits(rate_key, attempted_at desc);

alter table public.purchases enable row level security;
alter table public.tier_seats enable row level security;
alter table public.checkout_rate_limits enable row level security;

drop policy if exists "users read own purchases" on public.purchases;
create policy "users read own purchases" on public.purchases for select to authenticated using (auth.uid() = user_id);
drop policy if exists "public reads seat availability" on public.tier_seats;
create policy "public reads seat availability" on public.tier_seats for select using (true);

revoke insert, update, delete on public.purchases from anon, authenticated;
revoke all on public.checkout_rate_limits from anon, authenticated;

create or replace function public.protect_profile_entitlement_columns()
returns trigger language plpgsql as $$
begin
  if coalesce(auth.jwt() ->> 'role', '') <> 'service_role' and (new.plan is distinct from old.plan or new.lifetime_since is distinct from old.lifetime_since) then
    raise exception 'entitlement fields are server-managed';
  end if;
  return new;
end; $$;
drop trigger if exists protect_profile_entitlement_columns on public.profiles;
create trigger protect_profile_entitlement_columns before update on public.profiles for each row execute function public.protect_profile_entitlement_columns();

create or replace function public.check_checkout_rate_limit(p_key text, p_limit integer default 8, p_window_seconds integer default 60)
returns boolean language plpgsql security definer set search_path = public as $$
declare v_count integer;
begin
  delete from public.checkout_rate_limits where attempted_at < now() - interval '1 day';
  perform pg_advisory_xact_lock(hashtext(p_key));
  select count(*) into v_count from public.checkout_rate_limits where rate_key = p_key and attempted_at >= now() - make_interval(secs => p_window_seconds);
  if v_count >= p_limit then return false; end if;
  insert into public.checkout_rate_limits(rate_key) values (p_key);
  return true;
end; $$;

create or replace function public.grant_lifetime_entitlement(p_order_id text, p_payment_id text, p_user_id uuid, p_tier text)
returns table(granted boolean, idempotent boolean) language plpgsql security definer set search_path = public as $$
declare v_purchase public.purchases%rowtype; v_updated integer;
begin
  select * into v_purchase from public.purchases where razorpay_order_id = p_order_id for update;
  if not found then raise exception 'purchase not found'; end if;
  if v_purchase.user_id <> p_user_id or v_purchase.tier <> p_tier then raise exception 'purchase identity mismatch'; end if;
  if v_purchase.status = 'paid' then
    if v_purchase.razorpay_payment_id <> p_payment_id then raise exception 'order already paid with another payment'; end if;
    return query select false, true; return;
  end if;
  if exists(select 1 from public.purchases where razorpay_payment_id = p_payment_id) then return query select false, true; return; end if;
  update public.tier_seats set seats_sold = seats_sold + 1, updated_at = now() where tier = p_tier and seats_sold < seat_limit;
  get diagnostics v_updated = row_count;
  if v_updated <> 1 then raise exception 'tier is sold out'; end if;
  update public.purchases set status = 'paid', razorpay_payment_id = p_payment_id, paid_at = now() where id = v_purchase.id;
  insert into public.profiles(id, plan, lifetime_since) values (p_user_id, 'founding_lifetime', now())
    on conflict (id) do update set plan = excluded.plan, lifetime_since = coalesce(public.profiles.lifetime_since, excluded.lifetime_since);
  return query select true, false;
end; $$;

revoke all on function public.check_checkout_rate_limit(text, integer, integer) from public, anon, authenticated;
revoke all on function public.grant_lifetime_entitlement(text, text, uuid, text) from public, anon, authenticated;
grant execute on function public.check_checkout_rate_limit(text, integer, integer) to service_role;
grant execute on function public.grant_lifetime_entitlement(text, text, uuid, text) to service_role;

commit;
