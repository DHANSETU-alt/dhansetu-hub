# Task 1 Delivery SOP — DhanSetu SmartBudget + LeakShield™

For anyone onboarding a customer manually today, no technical background needed.
Real product: dhansetuhub.in → SmartBudget. Free tier: 300 entries/month. Paid
(one-time, no subscription, updated 2026-09-13): SmartBudget Pro ₹149
(unlimited entries + full LeakShield), or Dhansetu All Access ₹399
(SmartBudget Pro + Resume AI) — both via Razorpay.

**Before you start**: confirm the customer can actually sign in (see
`TASK_1_WATCHDOG_STATUS.md` — Google sign-in has had a real production bug;
do one test sign-in yourself first if you haven't recently).

## 1. Collect user info

- Full name and the email they'll sign in with (Google sign-in — must match a real Google account they can access).
- Ask if they want the free plan (300 entries/month), SmartBudget Pro (₹149 one-time), or All Access (₹399 one-time, adds Resume AI) — don't push a paid tier if they're just trying it out.
- Note down their primary income type (salary / freelance / business) — helps you set up categories sensibly in step 2.

## 2. Set up income/categories

- Have them sign in at dhansetuhub.in → "Start free" → SmartBudget.
- Categories are fixed in the app (Housing, Food, Transport, Bills, Shopping, Health, Education, Entertainment, Salary, Other) — walk them through which ones apply to their life.
- Go to the Budgets tab together and set a monthly ₹ limit for 3-5 categories they actually spend in. Skip categories they don't use — an empty budget just means LeakShield won't flag overspending there yet.

## 3. Add first transactions

- Add at least 5-10 real transactions from the last week or two (income and expenses both) — LeakShield needs at least 5 entries before it can say anything meaningful.
- Encourage them to backfill a month if they have the numbers handy (bank SMS, memory, a notebook) — more history makes LeakShield's subscription-detection and cash-flow signals more useful, since those need 2-3 months of data to fire.

## 4. Run LeakShield

- Open the LeakShield tab in SmartBudget.
- If it shows "Not enough history yet" — that's expected with a fresh account; tell them plainly it'll start finding patterns after a few more weeks of entries, don't oversell it.
- If it shows real alerts (overspending, a likely subscription, a low savings rate, rising spending), read through them together.

## 5. Prepare summary

- Write down (or screenshot) what LeakShield actually flagged, in plain words — e.g. "You went ₹500 over your Food budget this month" or "There's a ₹499 charge repeating every month in Entertainment."
- Do not add anything LeakShield didn't actually say. No estimated savings beyond what the app itself computed.

## 6. Explain leaks and next actions

- Walk through each flag one at a time: what it means, why it might be happening, and one concrete thing they could do about it (cancel a forgotten subscription, adjust a budget limit, review a category).
- Be explicit: "This isn't financial advice, it's just showing you your own numbers clearly."

## 7. Follow-up after 7 days

- Message or call 7 days later: ask if they've kept adding entries, whether anything from the LeakShield review actually changed their spending, and whether they have questions.
- If they're on the free plan and hitting the 300-entry limit, that's the natural moment to mention SmartBudget Pro (₹149 one-time) — not before.
- Log the outcome in `TASK_1_CUSTOMER_TRACKER.md`.
