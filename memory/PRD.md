# Trinity — Product Requirements Document

## Original Problem Statement
Trinity is an enterprise ticket management platform that synchronizes data with Atlas (external helpdesk). The core challenge is maintaining data consistency between the two systems through a unified sync engine.

## Architecture
- **Frontend:** React (port 3000)
- **Backend:** FastAPI (port 8001)
- **Database:** MongoDB
- **External:** Atlas API, Amazon SES, Gmail IMAP, Gemini (summarization via Emergent LLM Key), Google OAuth

## Sync Engine — 5-Layer Architecture
1. **Webhooks** — Real-time event processing from Atlas
2. **Poller** — Safety net for recently created conversations (every 30s)
3. **Two-Tier Crawl** — Hot (active statuses) + Cold (full reconciliation)
4. **Push-back** — Trinity to Atlas field sync
5. **Sweep** — Unassigned ticket management

## What's Been Implemented

### Completed (March 2026)
- Unified sync engine refactoring from legacy scripts
- Two-tier hot/cold crawl optimization
- Deployment failure resolution
- Ticket sweep bug fix
- Deep sync logic audit (found 20 flaws, all fixed)

### Backend Audit — 15 Issues Reviewed (March 2026)
**Fixed (4 real issues, verified 24/24 tests):**
- Issue 4: Robustified get_current_user in dependencies.py
- Issue 7: Teams authorization — mutation endpoints require lead/admin role
- Issue 8: TeamCreate/TeamUpdate validation — name/escalation_level constraints
- Issue 15: Removed ~200 lines of dead one-time migration code from server.py

**Already Fixed (by previous agents):** Issues 1-3, 14
**Not Applicable (code verified correct):** Issues 5-6, 9-13

### Frontend Audit — 5 Issues Fixed (March 2026, verified 8/8 backend + all frontend Playwright tests)
1. **P0 — Missing `/api/auth/shift-start` route:** Added POST route in auth.py, wired to existing `trigger_shift_start_assignment` helper
2. **P1 — 12 console.log statements in production:** All removed from AuthCallback.js, RealtimeContext.js, LeavePage.js
3. **P1 — Dead `window.__CURRENT_USER_ID__`:** Removed from App.js (only used by orphaned component)
4. **P2 — Orphaned dead components:** Deleted `_orphaned/AuthPage.js` and `_orphaned/PresenceIndicator.js`
5. **P2 — Logout clearing theme preference:** Sidebar logout now only clears sidebarWidth, theme persists

## Prioritized Backlog

### P1 — Upcoming
- Configure full webhooks in production (status_changed, conversation_created, agent_changed)

### P2 — Future
- Real-time agent notifications

### P3 — Low Priority
- Cleanup legacy DB collections (atlas_backfill_state, backfill_state)
- Recurring job for auto-closing stale tickets

## Key Files
- `/app/backend/services/atlas_sync.py` — Unified sync engine (stable, do not modify)
- `/app/backend/routes/atlas_webhooks.py` — Webhook HTTP handler
- `/app/backend/services/ticket_sweep.py` — Ticket sweep daemon
- `/app/backend/routes/auth.py` — Auth routes including shift-start
- `/app/backend/dependencies.py` — Auth dependencies
- `/app/backend/routes/teams.py` — Team management (lead/admin protected)
- `/app/backend/models/schemas.py` — All Pydantic schemas with validation

## Test Reports
- `/app/test_reports/iteration_79.json` — 20-fix sync verification (23/23 passed)
- `/app/test_reports/iteration_80.json` — Backend audit fixes (24/24 passed)
- `/app/test_reports/iteration_81.json` — Frontend audit fixes (8/8 backend + all frontend passed)
