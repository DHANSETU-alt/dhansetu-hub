# Dhansetu `/tools` competitive audit

## Evidence boundary

No Google Analytics property or first-party traffic export is connected in this session, so this audit does not invent Dhansetu traffic numbers. Public traffic figures are directional only; the product decisions below are based on observed workflows in the current source and public product documentation/roundups.

## Working patterns worth copying

| Category | Busy/established references | Pattern to adopt |
| --- | --- | --- |
| PDF utilities | [iLovePDF](https://www.ilovepdf.com/), [Smallpdf](https://smallpdf.com/), [PDF24](https://tools.pdf24.org/), [Xodo](https://xodo.com/) | Lead with a task picker, state privacy/processing mode, and send the user directly into one action. |
| Invoicing | [Zoho Invoice](https://www.zoho.com/invoice/), [FreshBooks](https://www.freshbooks.com/), [Wave](https://www.waveapps.com/) | Use structured inputs, a clear preview/export result, and name the exact artifact the user receives. |
| Idea validation | [Google Trends](https://trends.google.com/), [Product Hunt Trend Seeker](https://www.producthunt.com/products/trend-seeker), [Preuve](https://preuve.ai/idea-validation/) | Separate a heuristic signal from evidence-backed research; expose the next validation action instead of presenting a magic score. |
| Tax/GST | [Income Tax e-filing](https://www.incometax.gov.in/), [GST portal](https://www.gst.gov.in/) | State assessment year, assumptions, privacy boundary, and “estimate/review only” limitations. |
| Budgeting | [YNAB](https://www.ynab.com/), [Money Manager](https://www.realbyteapps.com/) | Make the primary action obvious and preserve user data through local persistence/import/export. |

Public demand signals also support prioritising PDF workflows: [Brandwave’s PDF-tools demand page](https://gobrandwave.com/demand/global-en/categories/pdf-tools) reports iLovePDF as the leading searched brand in its comparison set, while [Ahrefs’ Smallpdf profile](https://ahrefs.com/websites/smallpdf.com) shows the category’s strong search/backlink orientation. These are not Dhansetu Analytics measurements.

## Dhansetu findings

- `/tools` previously advertised only Image to PDF, Invoice Generator, and a `/pdf-studio` route that is explicitly “coming soon”.
- Working Tax Estimator, GST LeakShield, and SmartBudget journeys were not discoverable from the tools index.
- “AI idea validator” overstated the current implementation: the code is a deterministic heuristic from one text field, not live market research.
- The previous cards did not tell users whether processing was local, an estimate, or a review-only workflow.

## Implemented decision

`app/tools/page.tsx` now indexes the five working tool journeys, labels their processing mode, names the exact CTA, and reframes Idea Lab as an evidence-guided heuristic with an explicit next step. `/pdf-studio` is no longer advertised until it has a working user journey.

## Next product batch

1. Add source-backed Idea Lab evidence adapters (Google Trends/Product Hunt or user-provided links) behind server-side rate limits and explicit source timestamps.
2. Add tool-level regression tests for invoice PDF export, tax assumptions, GST CSV matching, and SmartBudget reload persistence.
3. Connect GA4/Search Console and publish a weekly funnel report: tools landing → tool open → result/export → return visit.
