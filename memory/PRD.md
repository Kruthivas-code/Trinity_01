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
- **Bidirectional assignment sync**: Trinity pushes assignment changes TO Atlas via `POST /v1/conversations/{id}` so assignments aren't overwritten by next sync cycle
- **Priority updates** are synced via _sync_fields whenever any webhook event fires (no separate priority webhook)
- **IMAP dedup** prevents duplicate messages when Atlas already synced the same content

## Completed Work
- [x] Atlas Shadow Sync engine (real-time, 60s interval)
- [x] Race condition resolution: IMAP no longer creates new tickets
- [x] Data parity: 72,943+ tickets synced from Atlas
- [x] 100% data parity achieved
- [x] Gap audit phase in sync daemon
- [x] UI ticket count fixes (dashboard, sidebar, escalation)
- [x] L1/L2/L3 converted to editable custom inboxes
- [x] Zeus AI ticket filtering across all views
- [x] Light/dark mode contrast fixes
- [x] Clean RTF outbound emails
- [x] Status consolidation (Open/Waiting/Closed/Merged)
- [x] Atlas webhook receiver endpoint with processing logic (2026-03-09)
- [x] Dashboard UI: full-width kanban, message preview, compact cards (2026-03-10)
- [x] Health endpoint fix: /health + /api/health for K8s probes (2026-03-10)
- [x] MongoDB index creation: per-index error handling, removed duplicate index (2026-03-10)
- [x] **Fix: Dead zone for closed tickets with null last_synced_at** (2026-03-10)
- [x] **Fix: Email search using regex for @ queries instead of $text** (2026-03-10)
- [x] **Fix: Attachment rendering in message threads (frontend)** (2026-03-10)
- [x] **Fix: IMAP duplicate prevention via _has_atlas_duplicate** (2026-03-10)
- [x] **Fix: "Assign to me" button — bidirectional Atlas sync** (2026-03-10)

## Recent Fix: "Assign to me" Button (2026-03-10)

### Root Cause
When a user clicked "Assign to me" in Trinity, the assignment was only saved to Trinity's local DB. The Atlas polling sync (every 60s) would then overwrite the local assignment with Atlas's old value because `_sync_fields()` explicitly treated Atlas as the owner of assignments. This made the assignment appear to "disappear" after ~60 seconds.

### Fix
- Added `sync_assignment_to_atlas()` function in `atlas_sync.py` that pushes assignment changes to Atlas via `POST /v1/conversations/{id}` with `{assignedAgentId: atlas_uuid}`
- Added helper functions `_fetch_atlas_users()` and `_get_atlas_agent_id_by_email()` with 5-minute caching
- Called from both `PUT /api/tickets/{id}` and `POST /api/tickets/{id}/assign` endpoints
- Graceful degradation: Atlas API errors are logged but don't break the main update flow
- Handles unassignment (null) correctly

### Files Modified
- `/app/backend/services/atlas_sync.py` — New functions: `sync_assignment_to_atlas`, `_fetch_atlas_users`, `_get_atlas_agent_id_by_email`
- `/app/backend/routes/tickets.py` — Import + calls to `sync_assignment_to_atlas` in both update and assign endpoints

## In Progress
- [ ] Attachment migration: paused due to object storage 500 errors (auto-resume enabled)

## Upcoming Tasks
- [ ] P1: Create one-time script to deduplicate historical IMAP messages
- [ ] P1: Deprecate polling sync once webhooks proven stable
- [ ] P1: User must re-deploy to trigger ticket ID migration and message backfill
- [ ] P2: Create data validation admin tool
- [ ] P2: Real-time notifications for agents
- [ ] P2: Auto-close stale tickets job
- [ ] P3: Cleanup one-time migration scripts after production run

## 3rd Party Integrations
- Atlas API + Webhooks (primary data source)
- Emergent Object Storage (attachments — outage)
- Gmail IMAP (reply processing only)
- Gemini (ticket summarization)
- Amazon SES (outbound email)
- Emergent-managed Google Auth

## Key DB Schema
- `tickets`: ticket_id, atlas_conversation_id (unique sparse), status (todo/waiting/closed/merged)
- `messages`: ticket_id, atlas_message_id (unique sparse), attachments array
- `users`: role field (default "agent"), email (mapped to Atlas agent IDs)
- `inboxes`: system + user-created inboxes
- `backfill_state`: Tracks one-time migration status

## Critical Files
- `/app/backend/routes/atlas_webhooks.py` — Atlas webhook handler
- `/app/backend/services/atlas_sync.py` — Atlas polling sync + bidirectional assignment sync
- `/app/backend/services/email_poller.py` — IMAP poller (with dedup)
- `/app/backend/search.py` — Search engine (with email regex fix)
- `/app/backend/server.py` — Startup hooks, /health endpoint
- `/app/backend/routes/tickets.py` — Ticket CRUD + Atlas assignment sync
- `/app/frontend/src/components/tickets/EmailMessage.js` — Message display (with attachments)
- `/app/frontend/src/hooks/useTicketDrawer.js` — Thread builder (passes attachments)
