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
- **Data Flow**: Atlas API → Atlas Webhooks + Polling → Trinity DB ← IMAP (replies only)

## Key Design Decisions
- **Atlas is the single source of truth** for all new tickets
- **IMAP poller only processes replies** to existing tickets — does NOT create new tickets
- **Atlas webhooks** provide real-time sync for: conversation created, agent changed, new message, tags changed
- **Atlas polling sync (60s)** still active as fallback — to be deprecated once webhooks proven stable
- **Trinity takes precedence** for field conflicts (if ticket modified in Trinity after last sync)
- **Priority updates** are synced via _sync_fields whenever any webhook event fires (no separate priority webhook)

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
- [x] 100% data parity achieved (68,578+ Atlas conversations)
- [x] Periodic gap audit phase in sync daemon
- [x] UI ticket count fixes (dashboard, sidebar, escalation)
- [x] L1/L2/L3 converted to editable custom inboxes
- [x] Zeus AI ticket filtering across all views
- [x] Light/dark mode contrast fixes
- [x] Clean RTF outbound emails
- [x] Status consolidation (Open/Waiting/Closed/Merged)
- [x] Atlas webhook receiver endpoint (2026-03-09)
- [x] Atlas webhook processing logic for all 4 registered events (2026-03-09)

## Webhook Implementation (2026-03-09)
- **Endpoint**: `/api/webhooks/atlas` (POST)
- **Registered events** (deployed env only):
  - conversation_created (secret: 5f1baf20faae445aa5a3705485d88161)
  - agent_changed (secret: 6d2f7f2c1e4044fb99e0f9269bd248ef)
  - new_message_received (secret: 903b0385e2554aaeb3df7957245d91c7)
  - tags_changed (secret: f07dc9880eb64b499d7220651ca07615)
- **Priority**: NOT a separate webhook — synced via _sync_fields on every event
- **Handler file**: `/app/backend/routes/atlas_webhooks.py`
- **Status**: Code complete, awaiting production verification

## In Progress
- [ ] Attachment migration: paused due to object storage 500 errors (auto-resume enabled)
- [ ] Zeus ticket cleanup: recurring job active

## Upcoming Tasks
- [ ] P1: Deprecate polling sync once webhooks proven stable
- [ ] P2: Create data validation admin tool
- [ ] P2: Real-time notifications for agents
- [ ] P2: Auto-close stale tickets job
- [ ] P3: Cleanup one-time migration scripts

## 3rd Party Integrations
- Atlas API (primary data source) + Atlas Webhooks (real-time events)
- Emergent Object Storage (attachments — currently experiencing outage)
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
- `/app/backend/routes/atlas_webhooks.py` — Atlas webhook handler (real-time sync)
- `/app/backend/services/atlas_sync.py` — Atlas polling sync engine (fallback)
- `/app/backend/services/email_poller.py` — IMAP poller (replies only)
- `/app/backend/server.py` — Startup hooks, background jobs
- `/app/backend/routes/tickets.py` — Ticket CRUD
