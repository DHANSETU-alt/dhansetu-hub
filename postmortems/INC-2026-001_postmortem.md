# Postmortem — INC-2026-001

**Title:** Payment Failure
**Date:** 2026-08-23 16:45:48
**Severity:** P2
**Owner:** finance_lead
**Support Team:** security, bug_fixer
**Detected by:** manual

## Timeline

- 2026-08-23 16:45:48 — **created**: type=payment_failure severity=P2 owner=finance_lead (primary owner available)
- 2026-08-23 16:45:59 — **state_change**: NEW -> ACKNOWLEDGED. Finance Lead acknowledged
- 2026-08-23 16:45:59 — **state_change**: ACKNOWLEDGED -> INVESTIGATING. checking Razorpay dashboard
- 2026-08-23 16:46:00 — **state_change**: INVESTIGATING -> FIXING. retrying with backoff
- 2026-08-23 16:46:00 — **state_change**: FIXING -> VERIFYING. confirming payment link now succeeds
- 2026-08-23 16:46:01 — **state_change**: VERIFYING -> READY_TO_DEPLOY. fix confirmed
- 2026-08-23 16:46:01 — **state_change**: READY_TO_DEPLOY -> RESOLVED. root_cause=Razorpay API had a transient 30s latency spike
- 2026-08-23 16:46:10 — **state_change**: RESOLVED -> CLOSED

## Timing

- Detection: 2026-08-23 16:45:48
- Response time: 0m 11s
- Resolution time: 0m 13s

## Root Cause

Razorpay API had a transient 30s latency spike

## Systems Affected

payment_failure

## Actions Taken / Fix Applied

Added retry with exponential backoff to create_payment_link



## Mistakes Made

The initial system design was overly brittle, relying on a single, synchronous call to the external payment gateway. This dependency failed catastrophically when the external API experienced high, transient latency. We were unprepared to handle predictable degradation in external service reliability.

## Lessons Learned

Transient failures from third-party APIs are an inevitable operational risk that must be proactively mitigated. The successful implementation of exponential backoff proved that systematic retry logic is essential for maintaining payment flow availability. Furthermore, the incident confirmed that our process for rapid verification and deployment of fixes is highly effective.

## Preventive Actions / Future Recommendations

We must roll out robust retry mechanisms with exponential backoff across all payment-related microservices to prevent similar timeouts. Implementing a circuit breaker pattern is strongly recommended to immediately fail services when an external dependency shows sustained instability. Finally, enhance our monitoring to track API latency metrics, setting alerts for deviations rather than just outright failures.
