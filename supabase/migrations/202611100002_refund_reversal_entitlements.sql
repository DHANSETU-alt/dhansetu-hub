-- Signed Razorpay refund webhook reconciliation. This migration never issues refunds.
begin;

alter table public.purchases
  drop constraint if exists purchases_status_check;
alter table public.purchases
  add constraint purchases_status_check check (status in ('created', 'paid', 'failed', 'partially_refunded', 'refunded'));
alter table public.purchases
  add column if not exists refunded_amount_paise integer not null default 0 check (refunded_amount_paise >= 0 and refunded_amount_paise <= amount_paise),
  add column if not exists refunded_at timestamptz;

create table if not exists public.payment_refunds (
  razorpay_refund_id text primary key,
  razorpay_payment_id text not null references public.purchases(razorpay_payment_id) on delete restrict,
  amount_paise integer not null check (amount_paise > 0),
  processed_at timestamptz not null default now()
);
alter table public.payment_refunds enable row level security;
revoke all on public.payment_refunds from public, anon, authenticated;

create or replace function public.revoke_lifetime_entitlement(
  p_payment_id text,
  p_refund_id text,
  p_refund_amount_paise integer
) returns table(revoked boolean, idempotent boolean, partial boolean)
language plpgsql security definer set search_path = public as $$
declare
  v_purchase public.purchases%rowtype;
  v_refund_inserted integer;
  v_total_refunded integer;
  v_remaining_plan text;
begin
  if p_payment_id is null or p_payment_id = '' or p_refund_id is null or p_refund_id = '' or p_refund_amount_paise <= 0 then
    raise exception 'invalid refund identity';
  end if;

  select * into v_purchase from public.purchases where razorpay_payment_id = p_payment_id for update;
  if not found then raise exception 'payment purchase not found'; end if;
  if v_purchase.status not in ('paid', 'partially_refunded', 'refunded') then
    raise exception 'payment is not eligible for refund reconciliation';
  end if;

  insert into public.payment_refunds(razorpay_refund_id, razorpay_payment_id, amount_paise)
  values (p_refund_id, p_payment_id, p_refund_amount_paise)
  on conflict (razorpay_refund_id) do nothing;
  get diagnostics v_refund_inserted = row_count;
  if v_refund_inserted = 0 then return query select false, true, v_purchase.status = 'partially_refunded'; return; end if;

  select coalesce(sum(amount_paise), 0) into v_total_refunded from public.payment_refunds where razorpay_payment_id = p_payment_id;
  if v_total_refunded > v_purchase.amount_paise then raise exception 'refund total exceeds payment amount'; end if;

  if v_total_refunded < v_purchase.amount_paise then
    update public.purchases set status = 'partially_refunded', refunded_amount_paise = v_total_refunded where id = v_purchase.id;
    return query select false, false, true; return;
  end if;

  update public.purchases set status = 'refunded', refunded_amount_paise = v_total_refunded, refunded_at = now() where id = v_purchase.id;
  update public.tier_seats set seats_sold = greatest(0, seats_sold - 1), updated_at = now() where tier = v_purchase.tier;

  select tier into v_remaining_plan
  from public.purchases
  where user_id = v_purchase.user_id and status in ('paid', 'partially_refunded')
  order by case tier
    when 'all_access' then 5 when 'smartbudget_pro' then 4 when 'team_lifetime' then 3
    when 'pro_lifetime' then 2 when 'founding_lifetime' then 1 else 0 end desc
  limit 1;
  update public.profiles set plan = coalesce(v_remaining_plan, 'free') where id = v_purchase.user_id;

  return query select true, false, false;
end; $$;

revoke all on function public.revoke_lifetime_entitlement(text, text, integer) from public, anon, authenticated;
grant execute on function public.revoke_lifetime_entitlement(text, text, integer) to service_role;

commit;
