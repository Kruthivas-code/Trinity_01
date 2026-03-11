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
- **Bidirectional assignment sync**: Trinity pushes assignment changes TO Atlas + 5-minute protection window prevents Atlas sync from overwriting recent Trinity assignments
- **Assignment protection**: `trinity_assigned_at` timestamp prevents `_sync_fields` from overwriting assignments within 5 minutes of a Trinity-originated change

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
- [x] Fix: Dead zone for closed tickets with null last_synced_at (2026-03-10)
- [x] Fix: Email search using regex for @ queries instead of $text (2026-03-10)
- [x] Fix: Attachment rendering in message threads (frontend) (2026-03-10)
- [x] Fix: IMAP duplicate prevention via _has_atlas_duplicate (2026-03-10)
- [x] **Fix: "Assign to me" button — bidirectional Atlas sync + 5min protection** (2026-03-11)
- [x] **Feature: File attachment support for outbound emails** (2026-03-10)
- [x] **Fix: Users list truncation (limit=100 → limit=500)** (2026-03-11)
- [x] **Fix: "Unassigned" button now persists to backend** (2026-03-11)
- [x] **Fix: Toast notifications for assignment success/failure** (2026-03-11)
- [x] **Fix: Error propagation in handleUpdateTicket** (2026-03-11)

## "Assign to me" Button Fix — Detailed RCA (2026-03-11)

### Root Cause
`_sync_fields()` had an unconditional rule: "Atlas owns assignments." In BOTH conflict and non-conflict branches, it overwrote Trinity's `assignee_id` with Atlas data. When a user assigned a ticket:

1. Trinity saved the assignment + pushed to Atlas via `sync_assignment_to_atlas()`
2. Before Atlas fully processed it (or on the next 60s polling cycle with cached list data), `_sync_fields` would run
3. It would either overwrite with the OLD Atlas agent or CLEAR the assignment entirely (if Atlas showed no agent)
4. This happened so fast it appeared as "the button simply did not work"

### Why it worked for Rohit
Rohit likely tested on tickets where he was already the assigned agent in Atlas. `_sync_fields` saw Atlas agent = Rohit = same as Trinity → no overwrite.

### Multi-layered Fix
1. **`trinity_assigned_at` timestamp** — Set on every Trinity-originated assignment change
2. **5-minute protection window** — `_sync_fields` skips assignment overwrite if `trinity_assigned_at` is within 5 minutes
3. **Bidirectional sync** — `sync_assignment_to_atlas()` pushes to Atlas via POST API
4. **Toast notifications** — Success/failure toasts on every assignment attempt
5. **Error propagation** — `handleUpdateTicket` now throws instead of silently catching
6. **Users list fix** — All users loaded (limit=500)

### Files Modified
- `/app/backend/services/atlas_sync.py` — `_sync_fields` respects `trinity_assigned_at`, `sync_assignment_to_atlas()` function
- `/app/backend/routes/tickets.py` — Sets `trinity_assigned_at` on assignment, import sync function, logging
- `/app/frontend/src/hooks/useTicketDrawer.js` — Toast notifications, error handling, revert on failure
- `/app/frontend/src/components/pages/DashboardContainer.js` — Error propagation, users limit=500
- `/app/frontend/src/components/tickets/TicketDetailsPanel.js` — "Unassigned" persists via handleAssign(null)
- `/app/frontend/src/App.js` — Toaster component added

## Upcoming Tasks
- [ ] P1: Create one-time script to deduplicate historical IMAP messages
- [ ] P1: Deprecate polling sync once webhooks proven stable
- [ ] P1: User must re-deploy to trigger ticket ID migration and message backfill
- [ ] P2: Match Atlas informational density (customer name, message preview, tags per ticket row)
- [ ] P2: Create data validation admin tool
- [ ] P2: Real-time notifications for agents
- [ ] P2: Auto-close stale tickets job
- [ ] P3: Cleanup one-time migration scripts after production run

## 3rd Party Integrations
- Atlas API + Webhooks (primary data source)
- Emergent Object Storage (attachments — outage)
- Gmail IMAP (reply processing only)
- Gemini (ticket summarization)
- Amazon SES (outbound email with file attachments)
- Emergent-managed Google Auth

## Key DB Schema
- `tickets`: ticket_id, atlas_conversation_id, status, assignee_id, **trinity_assigned_at** (new)
- `messages`: ticket_id, atlas_message_id, attachments array
- `users`: role, email (mapped to Atlas agent IDs)
- `file_attachments`: file_id, original_name, stored_name, content_type, size, uploaded_by
- `backfill_state`: Tracks one-time migration status
