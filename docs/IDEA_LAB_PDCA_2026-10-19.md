# Idea Lab PDCA — 2026-10-19

## Plan

The live query `https://dhansetuhub.in/tools?idea=ai+to+passive+income+idea` was treated as a customer-facing journey, not just a page render. The goal was to stop the homepage from promoting an output that looked more authoritative than its implementation.

## Do

Removed Idea Lab from the homepage cards and removed idea-validation language from the homepage masthead. The `/tools` route remains available and unchanged in this pass, so the existing last tool and catalog are preserved.

## Check

The reproduced query currently returns a keyword-derived score and generic interview recommendation. It does not fetch Google Trends, Product Hunt, competitor data, source links, timestamps, or user evidence. It is therefore not suitable as a homepage promise of evidence-guided validation.

## Act

The homepage now exposes only the two directly understandable working journeys: SmartBudget and local document processing. Idea Lab should return to the homepage only after it has source-backed evidence, an explanation of scoring, and a meaningful empty/error state.

## Follow-up acceptance criteria

- Each result shows sources and timestamps.
- Missing evidence produces “not enough evidence”, not a fabricated confidence score.
- Score components are visible and reproducible.
- A user can clear/retry the query without stale query-string state.
- Add regression coverage for empty, short, and evidence-backed inputs before re-promoting it.
