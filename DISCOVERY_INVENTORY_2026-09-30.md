# DhanSetu Repository Discovery & Inventory
**Date:** 2026-09-30  
**Status:** Discovery Complete (Task #1)  
**Discovery Agent:** Codex (via Shakthi OS 1.2)

---

## Executive Summary

**Canonical DhanSetu Workspace:** `/Users/apple/shakthi-os`  
**Remote:** https://github.com/DHANSETU-alt/dhansetu-web.git  
**Branch:** main (clean history, ~120 uncommitted changes)  
**Database:** SQLite `/Users/apple/shakthi-os/shakthi.db` (38.5MB)  
**Status:** Infrastructure 40% built, payment integration in progress, Google Sign-In pending

---

## Canonical DhanSetu Workspace

### Path & Structure
```
/Users/apple/shakthi-os/
├── orchestrator/          # Python FastAPI backend (API on :8787)
├── dashboard/             # Next.js frontend (dev server on :3000)
├── dhansetu-web/          # Static web app (HTML landing + planner)
├── shakthi.db             # SQLite database (38.5MB)
├── start_dashboard.sh     # Startup script
├── requirements.txt       # Python dependencies
└── [many docs & backups]
```

### Git Status
```
Last commit:  a59e669 "docs: add Cloudflare Zero Trust runbook"
Branch:       main (tracked to origin/main)
Uncommitted:  ~120 modified files + 50 untracked files
Status:       Clean at HEAD, significant work staged for commit
```

### Current Services
- **API Server:** `orchestrator/api.py` (Python FastAPI, port 8787)
- **Dashboard:** `dashboard/` (Next.js, port 3000)
- **Web App:** `dhansetu-web/` (static HTML landing + planner app)

---

## Database Inventory

### SQLite Schema: 61 Tables

**Key Business Tables:**
| Table | Purpose | Status |
|-------|---------|--------|
| `payment_transactions` | Payment gateway records (Razorpay/Stripe/UPI/PayU) | Empty (0 records) |
| `product_subscriptions` | Customer entitlements (email → product access) | Empty (0 records) |
| `businesses` | Business entities | Setup (1 founder tenant) |
| `agents` | Agent configurations (55+ agents defined) | Active |
| `tasks` | Work queue | Active |
| `leads` | Lead capture | Active |
| `finance_entries` | Financial tracking | Active |

**Status:** Payment infrastructure exists in code, database tables prepared, no live transactions yet.

### Database Backups
```
backups/shakthi_before_overnight_v6_backup_2026-09-08.db       (5.4M)
backups/shakthi_before_v6_baseline_2026-09-08.db               (4.9M)
backups/shakthi_before_linux_dashboard_alignment_2026-09-06.db (3.5M)
backups/shakthi_before_revenue_status_correction_2026-09-05.db (3.5M)
```

---

## Pricing Tiers (Already Configured)

- **SmartBudget Pro:** ₹149 (one-time)
- **DhanSetu All Access:** ₹399 (one-time)  
- **PDF Studio:** ₹99 (annual, 10 free uses)
- **PeopleDesk:** ₹99 (monthly)
- **BlackBoxOps OS Starter:** ₹2,999 (one-time, first 300 customers)
- **BlackBoxOps OS Growth:** ₹7,999 (one-time, first 300 customers)

---

## Uncommitted Work (120 Changes)

### Critical New Routes
```
✓ /api/blackboxops/razorpay-order/route.ts    (Razorpay order creation)
✓ /api/blackboxops/razorpay-verify/route.ts   (Razorpay webhook verification)
✓ /api/blackboxops/subscribe/route.ts         (Subscription flow)
✓ /api/jarvis/                                (Jarvis API infrastructure)
✓ /app/readiness/page.tsx                     (Readiness scorecard dashboard)
```

### New Dashboard Pages
- `/app/jarvis/` - Jarvis integration UI
- `/app/readiness/` - DhanSetu Revenue Readiness scorecard

### New Components
- `JarvisMissionGraph.tsx` - Jarvis system visualization
- `SystemCircuitDiagram.tsx` - Mac ↔ Linux ↔ Agents architecture

---

## Legacy Repositories (26GB Total)

**Classification for Cleanup:**
| Repo | Size | Type | Action |
|------|------|------|--------|
| `shakthi-services/` | 8.6G | AUDIT-NEEDED | Review usage |
| `colibri/` | 9.0G | DUPLICATE | Archive & remove |
| `OmniRoute/` | 6.0G | DUPLICATE | Archive & remove |
| `deepseek-harness/` | 648M | LEGACY-OS | Archive & remove |
| `youtube-automation-agent/` | 456M | LEGACY-OS | Archive & remove |
| `ai-setup/` | 314M | LEGACY-OS | Archive & remove |
| `MonkeyCode/` | 312M | LEGACY-OS | Archive & remove |
| `free-claude-code/` | 77M | LEGACY-OS | Archive & remove |
| `claude-code/` | 45M | LEGACY-OS | Archive & remove |
| `stockyield_bot/` | 228K | LEGACY-OS | Archive & remove |

---

## Feature Status

### ✓ Complete/In-Progress
- Database schema (comprehensive, 61 tables)
- Pricing configuration (all tiers defined)
- Agent system (55+ agents, tested)
- Task queue (operational)
- Payment infrastructure (code exists)
- Razorpay integration (code written, not live-tested)
- Readiness dashboard (exists)

### ⚠ Partial/Incomplete  
- Google Sign-In (routes exist, not verified live)
- Razorpay webhook verification (code written, untested)
- Founder dashboard (readiness exists, 12-workspace version not built)

### ✗ Not Started
- SmartBudget income-first dashboard
- Indian tax estimator
- GST LeakShield
- Daily research automation
- Content publishing pipeline
- Partner network / commissions
- MacBook hosting migration

---

## Next Phase: Task #2

Create legacy cleanup archive and quarantine 26GB of old repos:
1. Encrypted archive on external SSD
2. Manifest with sample restore proof
3. Move to dated quarantine in Trash
4. Hold 7 days for validation

**Owner Action:** Confirm external SSD availability + cleanup approval.

---

**Discovery Tool:** Codex  
**Verified:** Canonical repo at `/Users/apple/shakthi-os`, no duplicates, single database  
**Date:** 2026-09-30
