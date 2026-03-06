# Trinity - Support Ticket Management System

## Original Problem Statement
Migrate historical data from Atlas support platform into Trinity and establish real-time two-way sync. Extended to include comprehensive metadata import, agent account import, and new features (bounce details, CC on replies, agent-initiated tickets).

## Core Architecture
- **Frontend:** React (CRA) + Shadcn UI + TailwindCSS
- **Backend:** FastAPI (Python) on port 8001
- **Database:** MongoDB (`test_database`)
- **Auth:** Emergent-managed Google OAuth
- **Integrations:** Gemini (summarization), Amazon SES (outbound email), Gmail IMAP (inbound email), Atlas API (historical + real-time sync)

## Ticket Status Values (Standardized)
| Status | Description |
|--------|-------------|
| `todo` | New/unassigned ticket |
| `in_progress` | Agent actively working |
| `waiting` | Waiting on customer (unified from: snoozed, pending, waiting_on_customer) |
| `review` | Under review |
| `closed` | Ticket completed (unified from: resolved, closed) |
| `queued` | In queue for assignment |
| `assigned` | Assigned but not started |

## Completed Work
- **Atlas Historical Backfill:** ~67,000 conversations, ~348,000 messages imported (resumable engine)
- **Atlas Metadata Enrichment:** CSAT scores, custom fields, attachments (URLs), actor/timestamp info
- **Atlas Agent Import:** 163 agents with upsert-by-email dedup
- **Bounce Detail Tooltip:** UI tooltip on bounced messages with recipient + reason
- **CC on Replies:** CC field in reply composer, backend SES support
- **Agent-Initiated Outbound Tickets:** Create tickets + send initial email to customer
- **Status Standardization (2026-03-06):** Unified `resolved` → `closed`, all waiting variants → `waiting`
- **Atlas Shadow Sync (2026-03-06):** Real-time sync engine polling Atlas every 60s, syncing new conversations, messages, sidebars (internal notes), and field changes. Auto-starts on boot. Admin UI with start/stop/config/stats. Trinity takes precedence in conflicts.

## Shadow Sync Architecture
- **Engine:** `backend/services/atlas_sync.py` — daemon thread with MongoDB state persistence
- **Polling:** Every 60s, fetches Atlas conversations active in last 15 minutes
- **New conversations:** Creates Trinity tickets with full field mapping
- **Existing tickets:** Syncs new messages, sidebars, and field changes (status/priority/assignee)
- **Conflict resolution:** Trinity takes precedence — if ticket was modified in Trinity since last sync, Atlas field changes are skipped (logged as conflict)
- **Active ticket re-check:** Each cycle re-checks a batch of active (non-closed) Atlas tickets for new messages
- **Admin controls:** Start/Stop/Config via `/api/admin/atlas/sync/*` endpoints
- **Admin UI:** "Atlas Sync" tab in admin page with status indicator, live stats, config, error log

## Upcoming Tasks (Priority Order)
1. **P1: Data Validation Script** — Admin endpoint to audit DB for duplicate tickets/messages
2. **P2: Real-time Agent Notifications**
3. **P2: Auto-Close Stale Tickets** (recurring job)
4. **P3: Migrate Atlas Attachments to Blob Storage**

## Key Files
- `/app/backend/services/atlas_sync.py` — Shadow sync engine (real-time)
- `/app/backend/services/atlas_backfill.py` — Backfill engine (historical)
- `/app/backend/routes/atlas.py` — Backfill + sync API endpoints
- `/app/backend/server.py` — App startup + auto-resume + auto-start sync
- `/app/frontend/src/components/admin/AdminPage.js` — Admin page with Atlas Sync tab
- `/app/memory/atlas_sync_plan.md` — Migration strategy doc

## Key API Endpoints — Atlas Sync
- `GET /api/admin/atlas/sync/status` — Sync state, last run, counters, errors
- `POST /api/admin/atlas/sync/start` — Start the sync worker
- `POST /api/admin/atlas/sync/stop` — Stop the sync worker
- `PATCH /api/admin/atlas/sync/config` — Update poll interval / lookback window

## Credentials
- **Atlas API Key:** `NY7YY8Y3092NKWXSQGR8BT3NIXNFOGFWBGFJ36WD8KCBQ9UIQ8VM8CX2K1I2LY75`
- **Auth:** Emergent Google OAuth
