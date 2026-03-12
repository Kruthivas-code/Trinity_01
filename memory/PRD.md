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
- **Data Flow**: Atlas API -> Atlas Webhooks + Polling -> Trinity DB <- IMAP (replies only)

## Key Design Decisions
- **Atlas is the single source of truth** for all new tickets
- **IMAP poller only processes replies** to existing tickets — does NOT create new tickets
- **Bidirectional assignment sync**: Trinity pushes assignment changes TO Atlas + 5-minute protection window
- **2-Phase Sync Architecture** (new):
  - Phase 1 (Realtime): Syncs conversations updated in last 15 minutes, every cycle
  - Phase 2 (Full): Walks ALL conversations (including CLOSED) from last 45 days, 100/cycle

## Shadow Mode: 2-Phase Sync Architecture

### Phase 1: Realtime Sync (every 60s)
- Queries Atlas for conversations updated in the last `lookback_minutes` (default: 15)
- Creates new tickets, syncs messages/sidebars/field changes for existing ones
- IMAP dedup: links existing IMAP tickets to Atlas conversations instead of duplicating

### Phase 2: Full Comprehensive Sync (every 60s, batched)
- Walks through ALL Atlas conversations created in the last 45 days (configurable via `FULL_SYNC_WINDOW_DAYS`)
- Includes CLOSED conversations (fixes the old gap audit's blind spot)
- Processes 100 conversations per cycle (`FULL_SYNC_BATCH_SIZE`)
- Tracks cursor position in `backfill_state` collection for resumability
- When cursor reaches the end, resets and starts a new pass
- At 100/cycle, a full pass through ~30K conversations takes ~5 hours
- Catches: tickets opened+closed during downtime, missed messages, field drift

### Why 45 days?
- User confirmed: 99% of tickets close within 15 days, almost 0 remain open after 1 month
- 45 days = 15-day close rate + 30-day safety margin

## Completed Work
- [x] Atlas Shadow Sync engine (real-time, 60s interval)
- [x] Race condition resolution: IMAP no longer creates new tickets
- [x] Data parity: 72,943+ tickets synced from Atlas
- [x] 100% data parity achieved
- [x] All core UI features (Kanban, list views, ticket drawer, etc.)
- [x] Atlas webhook receiver
- [x] **Fix: "Assign to me" button — root cause: @imported.local placeholder emails** (2026-03-11)
- [x] **Fix: trinity_assigned_at only set on actual assignee change** (2026-03-11)
- [x] **Fix: System messages use 'content' field consistently** (2026-03-11)
- [x] **Feature: Information density — tags, customer email, relative time in views** (2026-03-11)
- [x] **Feature: File attachment support for outbound emails** (2026-03-10)
- [x] **Migration: fix_imported_local_emails.py — auto-runs on startup** (2026-03-11)
- [x] **Auth flow fix: _resolve_imported_user() prevents ghost duplicates** (2026-03-11)
- [x] **Defensive validation: assignee_id existence check** (2026-03-11)
- [x] **Refactor: 2-phase sync architecture replacing 3-phase** (2026-03-11)
- [x] **Feature: Atlas Admin Control Panel** (2026-03-11)
  - Sync Dashboard: Phase 1 + Phase 2 stats, full sync progress bar with ETA
  - API Health: 1-click Atlas API connectivity test (key validity, response time, conversation count)
  - Data Parity: Trinity vs Atlas totals, linked/missing counts, ticket ID alignment, parity score %
  - Configuration: Poll interval, lookback window, save config
  - New endpoints: `GET /api/admin/atlas/test`, `GET /api/admin/atlas/parity`
- [x] **Migration: Ticket ID alignment** (2026-03-11)
  - Aligned all 2,989 mismatched ticket IDs to match Atlas numbers (TKT-{atlas_number})
  - Relocated 1,561 IMAP-only blocking tickets to new sequential numbers
  - Updated 32,921 cross-collection references
  - 0 mismatched, 0 temp-prefixed tickets remaining
- [x] **Migration: Message deduplication** (2026-03-11)
  - Scanned for atlas_message_id + content-hash duplicates
  - Found 0 duplicates (data was already clean)

## Upcoming Tasks
- [ ] P0: Deploy and verify @imported.local migration + assign button fix on production
- [ ] P1: Trigger ticket ID migration and message backfill (auto-runs on deploy)
- [ ] P2: Align Trinity user_ids with Atlas UUIDs (eliminate email-based mapping)
- [ ] P2: Create data validation admin tool
- [ ] P2: Real-time notifications for agents
- [ ] P2: Auto-close stale tickets job
- [ ] P3: Cleanup one-time migration scripts after production run
- [ ] P3: Deprecate old polling references in code

## 3rd Party Integrations
- Atlas API + Webhooks (primary data source)
- Emergent Object Storage (attachments — outage)
- Gmail IMAP (reply processing only)
- Gemini (ticket summarization)
- Amazon SES (outbound email with file attachments)
- Emergent-managed Google Auth
