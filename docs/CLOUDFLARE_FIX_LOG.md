# Cloudflare fix log

- Browser verified apex and `www` CNAME → `dhansetu-hub.onrender.com`.
- No conflicting A records were present.
- DNS-only is the safe final state; orange-cloud proxying reproduced Error 1000 through the Render Cloudflare edge.
- Evidence: `docs/CLOUDFLARE_FIXED.png`.
