# BlackBoxOps / Shakthi OS Cloudflare Zero Trust Runbook

**Status:** Ready for Cloudflare account execution  
**Scope:** Protect internal control surfaces without blocking the public site

## Public routes that must remain open

- `https://blackboxops.co.in/`
- `/try`
- `/blog` and published blog articles
- `/security-score`
- `/services`
- `/security-audit`
- `/build-automate`
- `/partners`
- `/privacy`, `/terms`, `/refunds`

These routes must remain reachable by customers, crawlers, and unauthenticated prospects.

## Private routes to protect

Protect these hostnames or paths with Cloudflare Access:

- `os.blackboxops.co.in`
- Shakthi dashboard
- Shakthi API
- staging environments
- deployment/admin panels
- SSH/private network services through Tunnel

Do not expose the Shakthi API directly to the public Internet.

## Identity provider

Recommended first provider: Google Workspace/Google login.

Create an owner group or allowlist containing the founder/admin email. Require
MFA at the identity provider. Add a separate recovery admin account before
removing one-time PIN as a fallback.

Suggested policy:

```text
Application: Shakthi OS Admin
Decision: Allow
Include: founder/admin Google identity or admin group
Require: device posture = Shakthi Managed Device
Require: MFA
Session duration: 8 hours
```

## Device enrollment

Enroll only managed founder/admin devices. Do not allow arbitrary email-domain
enrollment until the organization has a real team directory.

Initial enrollment allowlist:

```text
Include: exact founder/admin email addresses
Login method: Google
Device enrollment: enabled
Allow device to leave organization: disabled after recovery device is tested
```

## Device posture checks

Create a reusable posture group named `Shakthi Managed Device` containing:

- Cloudflare One Client/WARP enrolled and connected
- Supported operating system
- Disk encryption enabled where available
- Device certificate or managed-device signal
- OS security baseline current

Apply the posture group to the Shakthi admin application and private network
applications. Posture should not be used to gate the public marketing site.

## Cloudflare Tunnel

Create a tunnel named `shakthi-control-plane` from the machine or private host
that runs the dashboard/API. Route only private services:

```text
os.blackboxops.co.in       -> local dashboard service
api.os.blackboxops.co.in   -> local API service
staging.os.blackboxops.co.in -> staging service, if required
```

Use Access policies on each application. Do not route the public marketing
site through this private tunnel unless the deployment architecture requires it.

## Firewall/WAF baseline

Create rules in this order:

1. Allow Cloudflare-managed traffic to public web routes.
2. Allow verified payment and analytics dependencies required by the site.
3. Challenge obvious automated abuse on public forms and checkout endpoints.
4. Rate-limit authentication, lead, security-score, and payment endpoints.
5. Block direct origin access except Cloudflare-origin traffic.
6. Block administrative/API hostnames unless Access has already authenticated.
7. Log blocked and challenged events for seven days before tightening rules.

Never block all non-India traffic without reviewing analytics and customer
requirements first.

## SaaS integrations to add later

Add only after identity and Access work correctly:

- Google Workspace/Gmail/Calendar
- GitHub
- Hosting/deployment provider
- Monitoring provider
- Payment operations, if supported by the account plan

Each integration must have a named owner, least-privilege permissions, and a
documented offboarding/revocation path.

## Acceptance tests

- Public homepage returns HTTP 200 without login.
- Public `/try` returns HTTP 200 without login.
- Founder on enrolled device can open Shakthi dashboard.
- Unknown Google account is denied.
- Unenrolled device is denied for the admin app.
- API cannot be reached directly from the public Internet.
- Tunnel reconnects after local service restart.
- Payment checkout still loads and completes its normal redirect flow.
- Cloudflare Access logs show both allowed and denied attempts.
- Origin IP is not reachable around Cloudflare controls.

## Cutover order

1. Add recovery admin identity.
2. Connect Google identity provider.
3. Enroll founder device.
4. Create posture checks.
5. Deploy tunnel.
6. Create Access application in report-only/test mode where available.
7. Validate founder access and denied-user behavior.
8. Enforce Access policy.
9. Add firewall/WAF rules incrementally.
10. Review logs after 24 hours and tighten rules.
