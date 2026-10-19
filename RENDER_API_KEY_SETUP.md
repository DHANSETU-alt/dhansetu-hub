# Render API key setup

Create an API key in Render Dashboard → Account Settings → API Keys, then run:

```bash
export RENDER_API_KEY='your-key'
export RENDER_SERVICE_ID='srv-danctvrbc2fs73dvv80g'
./scripts/fix-cloudflare-custom-domain.sh
```

Never commit the key.
