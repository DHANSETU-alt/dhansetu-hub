begin;

-- The checkout checks this row before creating an order; the entitlement RPC
-- increments seats_sold atomically after payment verification.
insert into public.tier_seats (tier, seat_limit) values ('founder_pass', 100)
on conflict (tier) do nothing;

commit;
