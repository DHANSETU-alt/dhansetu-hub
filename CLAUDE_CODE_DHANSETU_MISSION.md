# Claude Code Mission — DhansetuHub.in

You are the Principal Product Engineer for DhansetuHub.in.

Work directly in the repository and deployment that actually serves:
https://dhansetuhub.in/

Do not guess the source repository or deployment. First verify:

1. GitHub repositories, branches, and latest commits
2. Cloudflare Workers & Pages projects
3. DNS records and custom-domain bindings
4. Build configuration
5. Deployment configuration
6. Environment variables and secrets references
7. Current live runtime

The live homepage is a Next.js/Vinext application served through Cloudflare. The old repository `DHANSETU-alt/dhansetu-web` may not be the canonical source. Do not modify or deploy from it unless you prove it serves the live site.

## Mission

Transform DhansetuHub into a focused production-ready platform for practical productivity and business software.

Public website must expose only these current products:

- SmartBudget
- PDF Studio
- PeopleDesk

Future products may appear only as “Coming Soon”.

## Remove completely from the public site

- Jarvis
- SHAKTHI_OS
- Executive Dashboard
- Mission Control
- Agent Network
- AI Operating System
- Autonomous Company
- Neural Network
- Founder Command Center
- Internal engineering visuals
- Fake live activity
- Demo dashboards
- Experimental pages
- Hidden navigation
- Unused pricing cards
- Unused buttons

## Homepage

Build these sections:

1. Clear hero explaining what DhansetuHub is
2. Real product cards
3. Benefits
4. Pricing
5. Customer FAQ
6. Genuine testimonials only; otherwise omit testimonials
7. Contact/support
8. Footer

## `/tools`

Create an All Tools directory with:

- Categories: Finance, Documents, HR, Business, Career
- Search
- Filters
- Status filters: Live, Coming Soon, Beta
- Real product data only

## SmartBudget

Implement or improve:

- Monthly income onboarding
- Category setup
- First transaction
- Budget suggestion
- Starter dashboard
- CSV import
- CSV export
- Google Sign-In
- Secure user profile

## User dashboard

Users can manage:

- Profile
- Purchases
- Subscriptions
- Saved data
- Exports
- Delete-account flow

## Checkout

- Verify the existing Razorpay integration
- Repair payment verification
- Unlock paid access only after verified payment
- Receipt/confirmation handling
- Confirmation email if the configured provider exists
- Refund policy
- Terms
- No fake payment success states
- Never expose or print secrets

## Support

Add or verify:

- Support form
- Privacy Policy
- Data Deletion Request
- FAQ
- Product Status page
- Release Notes/changelog

## Mobile and analytics

- Responsive layout
- Compact mobile navigation or bottom navigation where appropriate
- Fast loading
- Accessible controls
- Keyboard-friendly forms

Use privacy-first event tracking only:

- `tool_opened`
- `signup_completed`
- `pricing_viewed`
- `checkout_started`
- `checkout_completed`

Do not add invasive tracking or unconfigured third-party analytics.

## Engineering rules

- Inspect before editing.
- Preserve unrelated user changes.
- Do not overwrite or delete production data.
- Do not change DNS or domain routing blindly.
- Do not create fake integrations.
- Do not expose internal Shakthi/OpenClaw/agent terminology publicly.
- Keep internal engineering tools separate from the public website.
- Use real product status labels.
- Add tests for important behavior.
- Use existing design language where possible.
- Make the smallest safe production change for each task.

## Priority

### Phase 1

1. Remove all public Jarvis/internal references.
2. Fix homepage product positioning.
3. Keep only SmartBudget, PDF Studio, and PeopleDesk as current products.
4. Repair navigation and pricing consistency.
5. Add/repair support, privacy, terms, refund, and changelog links.

### Phase 2

6. Build `/tools` directory.
7. Improve SmartBudget onboarding.
8. Add CSV import/export.
9. Add user dashboard basics.
10. Verify Razorpay payment and access-unlock flow.

### Phase 3

11. Mobile optimization.
12. Privacy-first analytics.
13. Product status and release notes.
14. Accessibility and performance improvements.

## Mandatory verification

After every phase:

- Run lint/typecheck
- Run unit/integration tests
- Run production build
- Run the app locally
- Check all public routes
- Check mobile layout
- Check accessibility basics
- Run broken-link checks
- Verify security headers
- Verify live deployment
- Visually inspect the live homepage
- Search the deployed site for forbidden terms:
  `Jarvis`, `SHAKTHI_OS`, `Mission Control`, `Agent Network`,
  `Executive Dashboard`, `AI Operating System`, `Autonomous Company`,
  `Neural Network`, `Founder Command Center`

Do not report success unless the live deployment has been verified.

## Final report

Report only:

- Canonical source repository verified
- Deployment verified
- Completed improvements
- Tests/build/runtime evidence
- Live visual verification
- Remaining blockers
- Next highest-impact task

If credentials, OAuth consent, payment confirmation, production secrets, or domain ownership approval is required, pause and ask for that specific approval. Continue all safe work automatically.
