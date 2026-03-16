# Trinity — Product Requirements Document

## Original Problem Statement
Trinity is an enterprise ticket management platform that synchronizes data with Atlas (external helpdesk). The core challenge is maintaining data consistency between the two systems through a unified sync engine.

## Architecture
- **Frontend:** React (port 3000)
- **Backend:** FastAPI (port 8001)
- **Database:** MongoDB
- **External:** Atlas API, Amazon SES, Gmail IMAP, Gemini (summarization), Google OAuth

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

### 20 Flaws Fixed (March 16, 2026)
1. Poller docstring corrected (creation-date-only filtering)
2. Message sync poisoning — uses `last_message_synced_at` not `last_synced_at`
3. Tag removal — handles empty tags from Atlas
4. >90d invisibility — cold crawl covers ALL conversations (no date window)
5. CSAT/closed_at one-shot — allows re-updates
6. Unstable hot crawl pagination — documented, mitigated by multi-layer architecture
7. Per-conversation error boundary with consecutive failure abort
8. Empty tag cache poisoning protection
9. False-positive ticket matching — time+source constraints
10. Webhook projection optimization
11. Hot crawl status transition — documented, covered by cold crawl + poller
12. Redundant poller sync — skips recently message-synced tickets
13. Webhook IMAP linking — uses `_create_or_link_ticket`
14. Per-conversation error boundary in batch processor
15. Webhook async processing — background thread, immediate 200 response
16. Reverse priority map — "medium" → "NORMAL" (not "MEDIUM")
17. Team ID sync from Atlas
18. Messages with attachments but no text are now preserved
19. Conflict counter tracks actual conflicts
20. Tags webhook uses unified `_sync_fields` (no double update)

## Prioritized Backlog

### P1 — Upcoming
- Configure full webhooks in production (status_changed, conversation_created, agent_changed)

### P2 — Future
- Real-time agent notifications

### P3 — Low Priority
- Cleanup legacy DB collections (atlas_backfill_state, backfill_state)
- Recurring job for auto-closing stale tickets

## Key Files
- `/app/backend/services/atlas_sync.py` — Unified sync engine
- `/app/backend/routes/atlas_webhooks.py` — Webhook HTTP handler
- `/app/backend/services/ticket_sweep.py` — Ticket sweep daemon
- `/app/backend/routes/atlas.py` — Admin sync controls

## Test Reports
- `/app/test_reports/iteration_79.json` — 20-fix verification (23/23 passed)
