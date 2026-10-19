-- Add the current public catalog without removing legacy product identifiers.
begin;

insert into public.tier_seats (tier, seat_limit) values
  ('smartbudget_pro', 10000), ('all_access', 10000)
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
  if exists(select 1 from public.purchases where razorpay_payment_id = p_payment_id) then return query select false, true; return; end if;
  update public.tier_seats set seats_sold = seats_sold + 1, updated_at = now() where tier = p_tier and seats_sold < seat_limit;
  get diagnostics v_updated = row_count;
  if v_updated <> 1 then raise exception 'tier is sold out'; end if;
  update public.purchases set status = 'paid', razorpay_payment_id = p_payment_id, paid_at = now() where id = v_purchase.id;
  insert into public.profiles(id, plan, lifetime_since) values (p_user_id, p_tier, now())
    on conflict (id) do update set plan = case when excluded.plan = 'all_access' or public.profiles.plan = 'free' then excluded.plan else public.profiles.plan end, lifetime_since = coalesce(public.profiles.lifetime_since, excluded.lifetime_since);
  return query select true, false;
end; $$;

revoke all on function public.grant_lifetime_entitlement(text, text, uuid, text) from public, anon, authenticated;
grant execute on function public.grant_lifetime_entitlement(text, text, uuid, text) to service_role;
commit;
