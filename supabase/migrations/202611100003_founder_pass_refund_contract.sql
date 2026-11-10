-- Server-side catalog support for the existing ₹499 Founder Pass offer.
-- This migration does not change live prices or issue access on its own.
begin;

insert into public.tier_seats (tier, seat_limit)
values ('founder_pass', 100)
on conflict (tier) do nothing;

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
  if v_purchase.status <> 'created' then raise exception 'purchase is not eligible for activation'; end if;
  if exists(select 1 from public.purchases where razorpay_payment_id = p_payment_id) then return query select false, true; return; end if;
  update public.tier_seats set seats_sold = seats_sold + 1, updated_at = now() where tier = p_tier and seats_sold < seat_limit;
  get diagnostics v_updated = row_count;
  if v_updated <> 1 then raise exception 'tier is sold out'; end if;
  update public.purchases set status = 'paid', razorpay_payment_id = p_payment_id, paid_at = now() where id = v_purchase.id;
  insert into public.profiles(id, plan, lifetime_since) values (p_user_id, p_tier, now())
    on conflict (id) do update set plan = case
      when excluded.plan in ('all_access', 'founder_pass') or public.profiles.plan = 'free' then excluded.plan
      else public.profiles.plan end,
      lifetime_since = coalesce(public.profiles.lifetime_since, excluded.lifetime_since);
  return query select true, false;
end; $$;

create or replace function public.revoke_lifetime_entitlement(
  p_payment_id text, p_refund_id text, p_refund_amount_paise integer
) returns table(revoked boolean, idempotent boolean, partial boolean)
language plpgsql security definer set search_path = public as $$
declare
  v_purchase public.purchases%rowtype;
  v_refund_inserted integer;
  v_total_refunded integer;
  v_remaining_plan text;
begin
  if p_payment_id is null or p_payment_id = '' or p_refund_id is null or p_refund_id = '' or p_refund_amount_paise <= 0 then raise exception 'invalid refund identity'; end if;
  select * into v_purchase from public.purchases where razorpay_payment_id = p_payment_id for update;
  if not found then raise exception 'payment purchase not found'; end if;
  if v_purchase.status not in ('paid', 'partially_refunded', 'refunded') then raise exception 'payment is not eligible for refund reconciliation'; end if;
  insert into public.payment_refunds(razorpay_refund_id, razorpay_payment_id, amount_paise) values (p_refund_id, p_payment_id, p_refund_amount_paise) on conflict (razorpay_refund_id) do nothing;
  get diagnostics v_refund_inserted = row_count;
  if v_refund_inserted = 0 then return query select false, true, v_purchase.status = 'partially_refunded'; return; end if;
  select coalesce(sum(amount_paise), 0) into v_total_refunded from public.payment_refunds where razorpay_payment_id = p_payment_id;
  if v_total_refunded > v_purchase.amount_paise then raise exception 'refund total exceeds payment amount'; end if;
  if v_total_refunded < v_purchase.amount_paise then
    update public.purchases set status = 'partially_refunded', refunded_amount_paise = v_total_refunded where id = v_purchase.id;
    return query select false, false, true;
  end if;
  update public.purchases set status = 'refunded', refunded_amount_paise = v_total_refunded, refunded_at = now() where id = v_purchase.id;
  update public.tier_seats set seats_sold = greatest(0, seats_sold - 1), updated_at = now() where tier = v_purchase.tier;
  select tier into v_remaining_plan from public.purchases
  where user_id = v_purchase.user_id and status in ('paid', 'partially_refunded')
  order by case tier when 'founder_pass' then 6 when 'all_access' then 5 when 'smartbudget_pro' then 4 when 'team_lifetime' then 3 when 'pro_lifetime' then 2 when 'founding_lifetime' then 1 else 0 end desc
  limit 1;
  update public.profiles set plan = coalesce(v_remaining_plan, 'free') where id = v_purchase.user_id;
  return query select true, false, false;
end; $$;

revoke all on function public.grant_lifetime_entitlement(text, text, uuid, text) from public, anon, authenticated;
grant execute on function public.grant_lifetime_entitlement(text, text, uuid, text) to service_role;
revoke all on function public.revoke_lifetime_entitlement(text, text, integer) from public, anon, authenticated;
grant execute on function public.revoke_lifetime_entitlement(text, text, integer) to service_role;
commit;
