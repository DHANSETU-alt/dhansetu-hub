# Ready to add in Render

Render Dashboard → `dhansetu-hub` → Settings → Custom Domains → Add Custom Domain.
Add `dhansetuhub.in`, then `www.dhansetuhub.in`, and click Verify.

API payload:

```json
{"name":"dhansetuhub.in"}
```

POST `https://api.render.com/v1/services/srv-danctvrbc2fs73dvv80g/custom-domains` with `Authorization: Bearer $RENDER_API_KEY`.
