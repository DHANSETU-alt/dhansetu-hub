# CTA audit report

| CTA | Current link | Expected link | Status | Fix needed |
|---|---|---|---|---|
| Explore workspace | `#tools` | `#tools` | pass | no |
| Open SmartBudget | `/smartbudget` | `/smartbudget` | pass | no |
| Start free | `/tools` | `/tools` | pass | no |
| Lifetime access (SmartBudget) | `/checkout?tier=smartbudget_pro` | authenticated checkout | pass | auth redirect expected |
| Lifetime access (All Access) | `/checkout?tier=all_access` | authenticated checkout | pass | auth redirect expected |
| Tool CTAs | `/tools/image-to-pdf`, `/tools/invoice`, `/pdf-studio` | same | pass | no |
| Billing | `/billing` | authenticated billing | pass | auth redirect expected |
| Contact/support | `/contact`, mailto | contact/support | pass | no |

Payment CTAs correctly enter the authenticated checkout path; direct browser testing cannot complete Razorpay without a logged-in test user and configured secrets.
