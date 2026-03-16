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
4. **Push-back** — Trinity → Atlas field sync
5. **Sweep** — Unassigned ticket management

## What's Been Implemented

### Completed (March 2026)
- Unified sync engine refactoring from legacy scripts
- Two-tier hot/cold crawl optimization
- Deployment failure resolution
- Ticket sweep bug fix
- Deep sync logic audit (found 20 flaws)
- **All 20 sync engine flaws fixed and verified (100% test pass rate)**

### Backend Audit — 15 Issues (March 2026)
**Already Fixed (before this session):**
- Issue 1 (P0): Hardcoded Gemini key → summaries.py uses EMERGENT_LLM_KEY from env
- Issue 2 (P0): Auth bypass → No /auth/google endpoint; uses Emergent session flow
- Issue 3 (P0): Route conflict → atlas_webhooks.py has clean routes
- Issue 14 (P3): Admin auth → All admin routes use require_admin

**Fixed This Session (verified 24/24 tests):**
- Issue 4 (P1): Robustified get_current_user in dependencies.py with proper error handling for edge cases
- Issue 7 (P1): Teams authorization — create_team, update_team, add/remove members now require lead/admin role
- Issue 8 (P1): TeamCreate/TeamUpdate validation — name length constraints, escalation_level validation
- Issue 15 (P3): Removed ~200 lines of dead one-time migration code from server.py startup

**Not Applicable (verified correct in current code):**
- Issue 5: No mutable default arguments found
- Issue 6: No soft deletion logic exists
- Issue 9: Search uses proper MongoDB text indexes
- Issue 10: Routes use string ticket_id, not ObjectId
- Issue 11: Single-tenant architecture, no cross-tenant risk
- Issue 12: Sweep is properly batched (50 tickets max)
- Issue 13: No hardcoded Slack webhook URL in codebase

## Prioritized Backlog

### P0 — Next
- Frontend Codebase QA Audit (same thorough review as backend)

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
- `/app/backend/routes/atlas.py` — Admin sync controls
- `/app/backend/dependencies.py` — Auth dependencies
- `/app/backend/routes/teams.py` — Team management
- `/app/backend/models/schemas.py` — All Pydantic schemas

## Test Reports
- `/app/test_reports/iteration_79.json` — 20-fix sync verification (23/23 passed)
- `/app/test_reports/iteration_80.json` — Backend audit fixes (24/24 passed)
