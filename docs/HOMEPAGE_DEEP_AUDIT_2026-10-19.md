# Homepage deep audit — 2026-10-19

## Baseline

`https://dhansetuhub.in/` and the linked public routes returned HTTP 200 during the audit. The authoritative homepage is `app/page.tsx`, with its visual system in `app/home.css`. The `/tools` catalog was deliberately left unchanged in this pass.

## Mismatch found

The previous masthead promised generic “AI performance”, while the actual working product is a browser-first workspace for SmartBudget, local document processing, and Idea Lab. That made the primary message and CTA less trustworthy than the implementation.

## Competitor patterns used

| Reference | Observable pattern | Dhansetu application |
| --- | --- | --- |
| [YNAB](https://www.ynab.com/) / [Monarch](https://www.monarch.com/) | Start from a clear money-management job and make the method legible. | Homepage names SmartBudget as a money workspace and preserves its local-first boundary. |
| [Rocket Money](https://www.rocketmoney.com/) | Lead with a concrete household-money outcome rather than infrastructure language. | Masthead now speaks to everyday decisions, not abstract AI performance. |
| [iLovePDF](https://www.ilovepdf.com/) / [Smallpdf](https://smallpdf.com/) | Send users directly to a named document task. | Document card now links with an explicit “Open document tools” CTA. |
| [PDF24](https://tools.pdf24.org/en/all-tools) | Make the tool inventory discoverable and grouped by task. | Homepage adds a direct Tools navigation link; detailed catalog remains at `/tools`. |
| [Google Trends](https://trends.google.com/) / [Product Hunt](https://www.producthunt.com/) | Validation starts with a question/evidence workflow, not an unsupported certainty claim. | Idea card says “Test an idea” and routes into the existing evidence-guided Idea Lab. |

These are workflow comparisons, not a claim that Dhansetu has their traffic or feature depth. No Google Analytics export is connected in this session, so first-party demand rankings remain unverified.

## Implemented

- Replaced the generic AI masthead with product-accurate workspace positioning.
- Added direct Tools navigation.
- Replaced identical “Open service” labels with intent-specific CTAs.
- Preserved the existing three-card visual system and all existing tool routes.
- Left `/tools` and its last tool unchanged.

## Verification plan

1. Typecheck, lint, and automated tests.
2. Deploy through the existing Render service.
3. Browser-check homepage text, nav, and all three card CTAs.
4. HTTP-check `/`, `/tools`, `/smartbudget`, `/tools/image-to-pdf`, and `/pricing`.

## Follow-up product work

- Add a visible “local / cloud / account required” trust legend to the homepage cards.
- Add real source links and timestamps to Idea Lab before calling it evidence-backed research.
- Connect GA4/Search Console to rank homepage → tool open → completed result, rather than guessing from public competitor traffic.
