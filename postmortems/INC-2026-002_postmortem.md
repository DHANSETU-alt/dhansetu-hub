# Postmortem — INC-2026-002

**Title:** Ollama Offline
**Date:** 2026-08-23 16:50:41
**Severity:** P1
**Owner:** ai_operations_lead
**Support Team:** sentinel
**Detected by:** incident_scheduler

## Timeline

- 2026-08-23 16:50:41 — **created**: type=ollama_offline severity=P1 owner=ai_operations_lead (primary owner available)
- 2026-08-23 16:52:41 — **state_change**: NEW -> RESOLVED. root_cause=False positive: incident_scheduler.py checked sentinel.service_status()['ollama'], which doesn't exist (that function returns docker/claude/telegram/sheets status, not Ollama). Ollama was never actually down.
- 2026-08-23 16:52:42 — **state_change**: RESOLVED -> CLOSED

## Timing

- Detection: 2026-08-23 16:50:41
- Response time: unknown
- Resolution time: 2m 0s

## Root Cause

False positive: incident_scheduler.py checked sentinel.service_status()['ollama'], which doesn't exist (that function returns docker/claude/telegram/sheets status, not Ollama). Ollama was never actually down.

## Systems Affected

ollama_offline

## Actions Taken / Fix Applied

Changed the check to snap.get('ollama_ok') from sentinel.collect_health(), the real signal.



## Mistakes Made

The primary mistake was the monitoring script's reliance on an outdated or incorrectly structured health check function. Specifically, `incident_scheduler.py` incorrectly called `sentinel.service_status()['ollama']` when the appropriate, reliable signal should have been retrieved via `snap.get('ollama_ok')`. This design flaw allowed a non-existent API check to trigger a high-severity false positive incident.

## Lessons Learned

We learned that monitoring systems must be version-controlled and kept synchronized with the underlying service implementation details. Any new service addition or API change requires immediate updates to all dependent health check logic to prevent false positives. It is critical to audit how service status signals are consumed across the board.

## Preventive Actions / Future Recommendations

Implement a centralized service discovery mechanism that provides a single, documented source of truth for all service health endpoints. All monitoring code must undergo mandatory unit and integration testing when external dependencies or service APIs change. This will prevent future false positives stemming from incorrect API calls.
