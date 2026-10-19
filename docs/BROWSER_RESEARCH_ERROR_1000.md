# Browser research: Error 1000

1. Render docs: https://render.com/docs/custom-domains
2. Add the custom domain to the exact Render web service first.
3. Configure DNS to the service `onrender.com` hostname, then verify in Render.
4. Render recommends removing AAAA records because it uses IPv4.
5. Cloudflare Error 1000 means DNS points to prohibited Cloudflare infrastructure.
6. A SaaS provider using Cloudflare also needs its custom hostname configured.
7. Render may need time to update routing after verification.
8. Cloudflare docs: https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1000/
9. Current origin is 200; public domain remains 403, proving an edge/custom-host issue.
