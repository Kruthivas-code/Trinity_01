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
- **Data Flow**: Atlas API -> Webhooks (L1) + Polling (L2) + Crawl (L3) -> Trinity DB <- IMAP (replies only) -> Push-back (L4) -> Atlas API

## Key Design Decisions
- **Atlas is the single source of truth** for all new tickets
- **IMAP poller only processes replies** to existing tickets — does NOT create new tickets
- **Bidirectional assignment sync**: Trinity pushes assignment changes TO Atlas + 5-minute protection window
- **Unified 5-Layer Sync Architecture** (2026-03-14):
  - Layer 1 (Webhooks): Real-time event processing from Atlas webhooks
  - Layer 2 (Poller): Safety-net polling every 60s, lookback 60 minutes
  - Layer 3 (Full Crawl): Historical reconciliation walk, 90-day window, 200/batch
  - Layer 4 (Push-back): Trinity → Atlas field sync (status, priority, tags, assignment)
  - Layer 5 (Sweep): Unassigned ticket auto-assignment (separate module: ticket_sweep.py)

## Unified 5-Layer Sync Engine

### Layer 1: Webhooks (Real-time)
- HTTP endpoint: POST /api/webhooks/atlas (no auth — Atlas calls directly)
- Handles: conversation.created, status_changed, agent_changed, priority_changed, tags_changed, message.received, sidebar events
- Thin HTTP handler in routes/atlas_webhooks.py delegates to handle_webhook_event() in atlas_sync.py
- Tracks webhook_events_processed counter in state

### Layer 2: Poller (Safety Net, every 60s)
- Queries Atlas for conversations updated in last 60 minutes (configurable)
- Creates new tickets, syncs messages/sidebars/field changes for existing ones
- IMAP dedup: links existing IMAP tickets to Atlas conversations instead of duplicating

### Layer 3: Full Crawl (Reconciliation)
- Walks through ALL Atlas conversations from last 90 days (configurable via FULL_SYNC_WINDOW_DAYS)
- Includes CLOSED conversations
- Processes 200 conversations per cycle (FULL_SYNC_BATCH_SIZE)
- Tracks cursor position for resumability
- At ~45K conversations, a full pass takes several hours
- Catches: tickets opened+closed during downtime, missed messages, field drift

### Layer 4: Push-back (Trinity → Atlas)
- sync_ticket_to_atlas(): Pushes status, priority, tags, custom_fields changes
- sync_assignment_to_atlas(): Pushes assignment changes with agent ID resolution
- sync_tags_to_atlas(): Convenience wrapper for tag-only sync
- Hooked into: PUT /api/tickets/{id}, POST /api/tickets/bulk-update, tag add/remove, Kanban drag

### Layer 5: Sweep (Auto-assignment)
- Separate module: services/ticket_sweep.py (unchanged)
- Runs every 5 minutes, assigns stale unassigned tickets
- Tries routing rules first, fallback to default team + assignment method
- Supports round_robin and least_tickets strategies
- Skips Zeus-handled tickets

## Completed Work
- [x] Atlas Shadow Sync engine (real-time, 60s interval)
- [x] Race condition resolution: IMAP no longer creates new tickets
- [x] Data parity: 72,943+ tickets synced from Atlas
- [x] 100% data parity achieved
- [x] All core UI features (Kanban, list views, ticket drawer, etc.)
- [x] Atlas webhook receiver
- [x] Fix: "Assign to me" button — root cause: @imported.local placeholder emails (2026-03-11)
- [x] Fix: trinity_assigned_at only set on actual assignee change (2026-03-11)
- [x] Fix: System messages use 'content' field consistently (2026-03-11)
- [x] Feature: Information density — tags, customer email, relative time in views (2026-03-11)
- [x] Feature: File attachment support for outbound emails (2026-03-10)
- [x] Migration: fix_imported_local_emails.py — auto-runs on startup (2026-03-11)
- [x] Auth flow fix: _resolve_imported_user() prevents ghost duplicates (2026-03-11)
- [x] Defensive validation: assignee_id existence check (2026-03-11)
- [x] Feature: Atlas Admin Control Panel (2026-03-11)
- [x] Migration: Ticket ID alignment (2026-03-11)
- [x] Migration: Message deduplication (2026-03-11)
- [x] Fix: Tag UUID→Name resolution for existing ticket updates (2026-03-13)
- [x] Fix: Data sync drift — removed false conflict detection (2026-03-13)
- [x] Fix: Ghost ticket cleanup (2026-03-13)
- [x] Bidirectional sync: Trinity → Atlas push (2026-03-13)
- [x] Routing & Auto-Assignment Enhancements (2026-03-13)
- [x] Sync Health Dashboard (2026-03-13)
- [x] **Unified 5-Layer Sync Engine** (2026-03-14)
  - Consolidated atlas_sync.py + atlas_webhooks.py logic into single service
  - Deleted obsolete atlas_backfill.py (1,084 lines of dead code)
  - Slimmed atlas_webhooks.py to thin HTTP handler (~55 lines)
  - Added priority_changed and sidebar webhook event handlers
  - Unified lookup caching (agent map, tag map) shared between webhooks and poller
  - Stubbed all legacy backfill endpoints with helpful deprecation messages
  - Kept import_atlas_agents inline in routes/atlas.py (still useful admin function)
  - Removed backfill auto-resume from server.py startup
  - Testing: 39/41 passed (95%), 0 critical issues

## Upcoming Tasks
- [ ] P1: Configure production webhook URL in Atlas settings (user action)
- [ ] P1: Subscribe to conversation.priority and sidebar.* events in Atlas (user action)
- [ ] P2: Real-time agent notifications
- [ ] P2: Auto-close stale tickets job
- [ ] P3: Cleanup one-time migration scripts after production run
- [ ] P3: Align Trinity user_ids with Atlas UUIDs

## 3rd Party Integrations
- Atlas API + Webhooks (primary data source)
- Emergent Object Storage (attachments — outage)
- Gmail IMAP (reply processing only)
- Gemini (ticket summarization)
- Amazon SES (outbound email with file attachments)
- Emergent-managed Google Auth

## Code Architecture
```
/app
├── backend/
│   ├── routes/
│   │   ├── atlas_webhooks.py    # Thin HTTP handler → delegates to atlas_sync.py
│   │   ├── atlas.py             # Atlas admin routes (sync control, health, parity)
│   │   ├── tickets.py           # Ticket CRUD with push-back hooks
│   │   └── ticket_ops.py        # Bulk ops with push-back hooks
│   ├── services/
│   │   ├── atlas_sync.py        # UNIFIED 5-Layer Sync Engine (~800 lines)
│   │   ├── ticket_sweep.py      # Layer 5: Auto-assignment (separate concern)
│   │   ├── email_poller.py      # IMAP reply processing
│   │   └── email_service.py     # SES outbound email
│   └── server.py                # Starts unified engine on boot
└── frontend/
    └── src/pages/AdminPage/
        └── AtlasSyncTab.js      # Sync Health dashboard UI
```
