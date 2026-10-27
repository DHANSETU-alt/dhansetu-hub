# DhanSetu audit corrections — 2026-10-28

Scoped repair, not a full penetration test. Existing source/deployment matched
9cdd4f302e7704d91a124258fa316b5ee44a121e on codex-launch-20261019, service
dhansetu-hub in the founder-confirmed Gauravkumar workspace.

## App changes

Added Content-Security-Policy through next.config.mjs. The policy preserves static
Next hydration (inline scripts), Razorpay, Supabase, existing PostHog/Meta analytics,
Google fonts and the homepage's CloudFront media. Production disallows eval,
plugins, foreign form actions and framing. This is a compatibility CSP, not a
nonce-based strict XSS policy. Nonces would require dynamic rendering changes;
those are outside this small correction. Existing middleware remains unchanged.

Published /.well-known/security.txt with the site's existing support/contact URI,
canonical HTTPS URL, preferred languages and an expiry less than one year away.
It is copied by the existing standalone postbuild step. Refresh before expiry.

Six focused tests passed in offline bwrap: read-only app/toolchain, no external
network, empty allowlisted environment, bounded scratch disk, process/memory/CPU,
wall-clock and file-size limits. Full local Next build was not run because this
recovered source has no installed Next dependencies. Render's existing build
pipeline must pass before any deployed claim; verify live headers, sign-in modal
hydration and security.txt afterward. No production payment test is part of this.

## DNS findings and prepared changes

Observed public DNS: Titan MX/SPF and titan1 DKIM present; DMARC TXT absent; CAA
absent; no DS or DNSKEY. RDAP identifies EIG India as registrar and delegationSigned
false. These are point-in-time observations, not full email delivery validation.

DMARC: enumerate all senders (the app includes Resend receipts) and confirm the
report mailbox before policy enforcement. Start monitored p=none; only promote
quarantine/reject after alignment evidence. A DKIM DNS key alone does not prove
that every legitimate sender signs aligned messages. Do not invent a report inbox.

CAA: allow the configured Cloudflare/Render issuers. Their current documentation
lists letsencrypt.org, pki.goog, ssl.com and sectigo.com for Cloudflare, with
letsencrypt.org and pki.goog required by Render. Prepare issue/issuewild pairs;
confirm active certificate configuration before publication. Do not add a CA
restriction that prevents renewal.

DNSSEC: enable signing in Cloudflare, then publish its exact generated DS at the
actual registrar. Verify the parent DS matches the child DNSKEY and validating
resolvers return authenticated answers. Enabling signing alone is not completion.

The current Wrangler OAuth identity cannot read/edit this zone's DNS/DNSSEC or
certificate packs. BrowserSkill's persistent daemon is running but no browser
extension is connected. DNS changes remain pending authorized dashboard access.

## Rollback

Revert this bounded app commit on codex-launch-20261019 and redeploy the known
previous Render commit if required. Keep the last live version serving on build
failure. No database, mail delivery, payment setting, DNS record, registrar or
secret was changed by the app patch. DNS changes, when authorized and performed,
need their own before/after record IDs and rollback evidence.

Primary references:
https://nextjs.org/docs/app/guides/content-security-policy
https://nextjs.org/docs/app/api-reference/config/next-config-js/headers
https://support.titan.email/hc/en-us/articles/900006395783-Add-DMARC-record
https://developers.cloudflare.com/ssl/edge-certificates/caa-records/
https://render.com/docs/custom-domains
https://developers.cloudflare.com/dns/dnssec/
