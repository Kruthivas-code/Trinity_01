# Trinity - Enterprise Ticket Management Platform

## Original Problem Statement
Build and maintain a full-stack ticket management system (React, FastAPI, MongoDB) with Atlas as the single source of truth for new tickets. Key goals:
- Standardize ticket statuses between Trinity and Atlas
- Implement Atlas Shadow Mode for real-time data synchronization
- Migrate attachments from Atlas to Emergent Object Storage
- Clean up AI-assigned (Zeus) tickets
- Maintain data parity with Atlas

## Architecture
- **Frontend**: React (port 3000)
- **Backend**: FastAPI (port 8001)
- **Database**: MongoDB
- **Data Flow**: Atlas API → Atlas Sync → Trinity DB ← IMAP (replies only)

## Key Design Decisions
- **Atlas is the single source of truth** for all new tickets
- **IMAP poller only processes replies** to existing tickets — does NOT create new tickets
- **Atlas sync runs every 60 seconds** polling for new/updated conversations
- **Trinity takes precedence** for field conflicts (if ticket modified in Trinity after last sync)

## Completed Work
- [x] Atlas Shadow Sync engine (real-time, 60s interval)
- [x] Race condition resolution: IMAP no longer creates new tickets (fixed 2026-03-06)
- [x] NoneType bug fix in Atlas sync for null customer emails (fixed 2026-03-06)
- [x] Data parity migration (ticket numbers, escalation levels, tags)
- [x] Assignment sync: unassignment + conflict path propagation (fixed 2026-03-07)
- [x] Escalation level sync from custom_fields.support_level (fixed 2026-03-06)
- [x] Recheck phase now syncs field updates, not just messages (fixed 2026-03-06)
- [x] Closed tickets recheck for reopened tickets (fixed 2026-03-06)
- [x] Assignment backfill: 1,287 tickets mapped from Atlas agent emails (fixed 2026-03-06)
- [x] Escalation backfill: 27 mismatches corrected (fixed 2026-03-06)
- [x] Attachment migration circuit breaker + retry limits (fixed 2026-03-06)
- [x] New user onboarding bug fixes (5 critical bugs)
- [x] User role backfill migration
- [x] Cross-browser CSS fixes
- [x] Wider ticket drawer layout
- [x] Redesigned reply toolbar
- [x] Background job stability (auto-resume attachment migration)
- [x] Bounce email detection and handling
- [x] Sent folder polling for agent Gmail replies

## In Progress
- [ ] Attachment migration: 25.9% done (13,432/51,816), high failure rate from object storage 500 errors
- [ ] Zeus ticket cleanup: recurring job active, cleaning stale AI-assigned tickets

## Recently Completed (2026-03-07)
- [x] Fixed missing ticket TKT-068210 for rohit@emergent.sh — root cause: conversation created during downtime gap outside 24h catchup window
- [x] Bulk-synced 231 additional missing non-closed conversations from Atlas (range 67714-69112)
- [x] Achieved 100% data parity: all 1,356 non-closed Atlas conversations now exist in Trinity
- [x] Added periodic gap audit phase to sync daemon (runs every 10 cycles) to auto-detect and sync any conversations missed by the 15-minute lookback window

## Upcoming Tasks (P2)
- [ ] Create Data Validation Script — admin endpoint to audit DB integrity
- [ ] Investigate attachment migration failures (object storage 500 errors)

## Future Tasks
- [ ] Real-time Notifications for agents
- [ ] Generic auto-close job for stale tickets

## 3rd Party Integrations
- Atlas API (primary data source)
- Emergent Object Storage (attachments)
- Gmail IMAP (reply processing only)
- Gemini (ticket summarization)
- Amazon SES (outbound email)
- Emergent-managed Google Auth

## Key DB Schema
- `tickets`: ticket_id (TKT-XXXXXX), atlas_conversation_id (unique sparse), source (atlas/email)
- `messages`: ticket_id, atlas_message_id (unique sparse)
- `users`: role field guaranteed (default "agent")
- `atlas_backfill_state`: _type="shadow" for sync state

## Critical Files
- `/app/backend/services/atlas_sync.py` — Atlas sync engine
- `/app/backend/services/email_poller.py` — IMAP poller (replies only)
- `/app/backend/server.py` — Startup hooks, background jobs
- `/app/backend/routes/tickets.py` — Ticket CRUD
