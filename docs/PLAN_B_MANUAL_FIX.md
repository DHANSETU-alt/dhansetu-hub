# Plan B manual fix

1. Render Dashboard → `dhansetu-hub` → Settings → Custom Domains → Add `dhansetuhub.in`.
2. Add `www.dhansetuhub.in` and verify both until Certificate Issued.
3. Cloudflare DNS: CNAME `@` → `dhansetu-hub.onrender.com` Proxied ON; CNAME `www` → same target Proxied ON.
4. Purge Cloudflare cache, wait for DNS/TLS propagation, then run `scripts/plan-b-fallback.sh`.
