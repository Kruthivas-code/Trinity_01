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

## Recent Fixes (2026-03-10)

### Fix 1: Dead Zone for Closed Tickets
- **Problem**: 59,359 closed tickets with null `last_synced_at` were never rechecked for missing messages
- **Root cause**: MongoDB `$lt` doesn't match null values, so these tickets fell through both recheck paths
- **Fix**: Added `$or: [null, {$exists: false}]` to closed_batch query in atlas_sync.py
- **File**: `/app/backend/services/atlas_sync.py` line ~795

### Fix 2: Email Search
- **Problem**: Searching `formlyhq@gmail.com` returned 0 relevant results (20 wrong matches)
- **Root cause**: MongoDB `$text` tokenizes emails on `.` and `@`, drowning actual matches in common tokens
- **Fix**: Detect email-like queries (contains `@`) → use regex on customer_email instead of $text
- **File**: `/app/backend/search.py` line ~410

### Fix 3: Attachment Display
- **Problem**: Attachments synced from Atlas stored in DB but never rendered in UI
- **Root cause**: `useTicketDrawer.js` dropped attachments field; `EmailMessage.js` had no attachment renderer
- **Fix**: Pass attachments through thread builder, render image thumbnails + file download links
- **Files**: `useTicketDrawer.js`, `TicketConversation.js`, `EmailMessage.js`

### Fix 4: IMAP Duplicate Prevention
- **Problem**: IMAP poller created duplicate messages that Atlas already synced (~186 dupes for one customer)
- **Fix**: `_has_atlas_duplicate()` checks for Atlas messages with similar content before inserting
- **File**: `/app/backend/services/email_poller.py` line ~33

## In Progress
- [ ] Attachment migration: paused due to object storage 500 errors (auto-resume enabled)
- [ ] 59,359 closed tickets gradually being rechecked (5 per cycle)

## Upcoming Tasks
- [ ] P1: Deprecate polling sync once webhooks proven stable
- [ ] P1: One-time backfill script to resync messages for all null last_synced_at tickets (faster than 5/cycle)
- [ ] P2: Create data validation admin tool
- [ ] P2: Real-time notifications for agents
- [ ] P2: Auto-close stale tickets job
- [ ] P2: Deduplicate existing IMAP duplicate messages (historical cleanup)
- [ ] P3: Cleanup one-time migration scripts

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
- `users`: role field (default "agent")
- `inboxes`: system + user-created inboxes

## Critical Files
- `/app/backend/routes/atlas_webhooks.py` — Atlas webhook handler
- `/app/backend/services/atlas_sync.py` — Atlas polling sync (with dead zone fix)
- `/app/backend/services/email_poller.py` — IMAP poller (with dedup)
- `/app/backend/search.py` — Search engine (with email regex fix)
- `/app/backend/server.py` — Startup hooks, /health endpoint
- `/app/backend/routes/tickets.py` — Ticket CRUD
- `/app/frontend/src/components/tickets/EmailMessage.js` — Message display (with attachments)
- `/app/frontend/src/hooks/useTicketDrawer.js` — Thread builder (passes attachments)
