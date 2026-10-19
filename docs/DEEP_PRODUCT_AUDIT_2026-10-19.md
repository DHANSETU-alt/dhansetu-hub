# DhanSetu Hub deep product audit — 2026-10-19

## Authoritative application

- Production: `https://dhansetuhub.in` and `https://dhansetu-hub.onrender.com`.
- Hosting: Render service `srv-danctvrbc2fs73dvv80g`, repository `DHANSETU-alt/dhansetu-hub`, branch `codex-launch-20261019`.
- Verified deployed revision: `0b8c5ee` (homepage redesign). Both origin and public homepage returned HTTP 200 during this audit.
- Entrypoint: Next.js App Router in `app/`, started by `npm start` using `.next/standalone/server.js`.
- `/home/blackboxops/Projects/dhansetu-hub-redesign` is a separate Git worktree (`redesign/mitra-1.1-preview`, revision `7956192`), not the Render source. It was not modified or deleted.

## Baseline route probe

| Route | Result | Evidence |
|---|---:|---|
| `/`, `/tools`, `/smartbudget`, `/contact`, `/login`, `/checkout` | 200 | `curl -L` production probe |
| `/tools/image-to-pdf`, `/tools/invoice`, `/pdf-studio`, `/pricing` | 200 | production probe after fix |
| `/api/health`, `/api/payment/verify-live` | 200 | production probe |
| POST payment APIs without a body | 405 | correct method guard; no mutation performed |

## Findings and fixes

| Priority | Journey/control | Before | Fix |
|---|---|---|---|
| P1 | Homepage feature CTA | “Advanced Plant Sculpting” linked to unrelated `/tools/image-to-pdf` and made an unsupported claim. | Renamed to “Image to PDF” with an accurate local-processing description and retained the working route. `app/page.tsx` |
| P1 | Pricing discovery | `/pricing` was absent (404), despite checkout and paid tiers existing. | Added `/pricing` using `PUBLIC_PLANS`; paid CTAs route to existing authenticated checkout. `app/pricing/page.tsx` |
| P2 | Homepage feature cards | “Processing” and “Growth Archive” were non-interactive. | Linked them to `/tools` and `/smartbudget` with truthful descriptions. `app/page.tsx` |
| P2 | Homepage tags/social controls | Decorative tags and generic Twitter/LinkedIn/Instagram home links did not represent Dhansetu journeys. | Replaced with working internal links: idea validation, document tools, SmartBudget, tools, budget, and support. `app/page.tsx` |

## Verification coverage

- Source inventory: App Router pages, API routes, payment/auth components, middleware, Render branch and worktrees inspected.
- Browser smoke: production homepage rendered the new hero; controls were enumerated and the primary Explore CTA was exercised.
- Route probes: all listed customer-facing routes and health/payment readiness routes checked with `curl`.
- Automated checks: `npm run typecheck` PASS; `npm run lint` PASS with 3 pre-existing warnings; `npm test -- --run` PASS (25 tests); `npm run build` PASS.
- Not executed against production: login/signup, Google OAuth callback, Razorpay checkout/charge, webhook delivery, account mutation, upload/export mutation, delete, or real email. These require seeded credentials, sandbox payment authorization, or explicit non-production test data.

## Remaining risks

1. Production payment completion and entitlement persistence remain unverified in this audit because no test account/payment authorization was used.
2. External video and Google Fonts are third-party runtime dependencies; browser network/console monitoring should be repeated on a controlled preview.
3. Existing lint warnings are non-blocking but should be cleaned separately: custom font placement, `<img>` usage, and an unused ESLint disable.

## Release state

The patch is locally buildable and tested. Production deployment of this patch is not claimed until the changed files are committed/pushed and Render reports the resulting revision live.
