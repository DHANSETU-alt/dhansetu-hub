# Browser research: Render + Cloudflare Error 1000

Reviewed 2026-10-19:

- Render custom domains: https://render.com/docs/custom-domains
- Cloudflare Error 1000: https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1000/
- Cloudflare 1xxx overview: https://developers.cloudflare.com/support/troubleshooting/cloudflare-errors/troubleshooting-cloudflare-1xxx-errors/

Findings:

1. Render requires the domain to be added to the specific web service, then DNS must point to the service's `onrender.com` hostname, and the domain must be verified in Render. Render says to remove AAAA records because Render uses IPv4.
2. Cloudflare Error 1000 is caused by a DNS record pointing to Cloudflare infrastructure, a reverse-proxy loop, an SNI mismatch, or a SaaS provider using Cloudflare without a configured custom hostname.
3. For a Render service using Render's Cloudflare-backed edge, the decisive provider-side fix is that the custom hostname must be configured on the Render service. A CNAME alone cannot create that provider-side mapping.
4. DNS-only CNAME records to `dhansetu-hub.onrender.com` are the safe configuration for this zone; orange-cloud proxying can create a second Cloudflare hop.

Conclusion: verify the Render custom-domain attachment and remove conflicting A/AAAA/proxy records. If Render's custom hostname is already verified and Error 1000 persists, the remaining action is Render support/provider-side routing refresh, not an application change.
