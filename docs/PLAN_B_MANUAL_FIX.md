# Plan B: manual custom-domain repair

## Render

1. Open Render Dashboard and select `dhansetu-hub`.
2. Open Settings → Custom Domains.
3. Click Add Custom Domain and enter `dhansetuhub.in`.
4. Add `www.dhansetuhub.in` as a second custom domain.
5. Click Verify for each domain and wait for Certificate Issued.

## Cloudflare

1. Open DNS → Records for `dhansetuhub.in`.
2. Remove only conflicting A/AAAA records, especially any `104.x` or `172.x` Cloudflare edge IP records.
3. Add CNAME `@` → `dhansetu-hub.onrender.com`, DNS only (gray cloud).
4. Add CNAME `www` → `dhansetu-hub.onrender.com`, DNS only (gray cloud).
5. Purge cache, then recheck the Render Verify button.

Research links:

- Render: https://render.com/docs/custom-domains
- Cloudflare Error 1000: https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1000/
- Cloudflare 1xxx guide: https://developers.cloudflare.com/support/troubleshooting/cloudflare-errors/troubleshooting-cloudflare-1xxx-errors/
