# Next steps

Live gate failed: {"checkedAt":"2026-10-19T08:10:13.578Z","origin":"200","public":"403"}

1. Render Dashboard -> dhansetu-hub -> Settings -> Custom Domains -> add and verify dhansetuhub.in and www.dhansetuhub.in.
2. Cloudflare DNS -> CNAME @ and www to dhansetu-hub.onrender.com, Proxied ON.
3. Purge Cloudflare cache.
4. Run: `VERIFY_SECONDS=300 ./scripts/plan-b-fallback.sh`
