# Trinity - Support Ticket Management System

## Original Problem Statement
Migrate historical data from Atlas support platform into Trinity and establish real-time two-way sync. Extended to include comprehensive metadata import, agent account import, new features, and full attachment migration.

## Core Architecture
- **Frontend:** React (CRA) + Shadcn UI + TailwindCSS
- **Backend:** FastAPI (Python) on port 8001
- **Database:** MongoDB (`test_database`)
- **Auth:** Emergent-managed Google OAuth
- **File Storage:** Emergent Object Storage (S3-compatible)
- **Integrations:** Gemini (summarization), Amazon SES (outbound email), Gmail IMAP (inbound email), Atlas API (historical + real-time sync)

## Ticket Status Values (Standardized)
| Status | Description |
|--------|-------------|
| `todo` | New/unassigned ticket |
| `in_progress` | Agent actively working |
| `waiting` | Waiting on customer (unified from: snoozed, pending, waiting_on_customer) |
| `review` | Under review |
| `closed` | Ticket completed (unified from: resolved, closed) |

## Completed Work
- **Atlas Historical Backfill:** ~67,000 conversations, ~348,000 messages imported (resumable engine)
- **Atlas Metadata Enrichment:** CSAT scores, custom fields, attachments (URLs), actor/timestamp info
- **Atlas Agent Import:** 163 agents with upsert-by-email dedup
- **Bounce Detail Tooltip:** UI tooltip on bounced messages with recipient + reason
- **CC on Replies:** CC field in reply composer, backend SES support
- **Agent-Initiated Outbound Tickets:** Create tickets + send initial email to customer
- **Status Standardization (2026-03-06):** Unified `resolved` → `closed`, all waiting variants → `waiting`
- **Atlas Shadow Sync (2026-03-06):** Real-time sync engine polling every 60s
- **Collapsible Quoted Text (2026-03-06):** Email reply chains collapse behind tiny `···` toggle
- **Email Capitalization Fix (2026-03-06):** from_addr lowercased in email_poller
- **Data Validation (2026-03-06):** One-time audit — 0 duplicates confirmed
- **Attachment Migration (2026-03-06):** Background job downloading ~65K files from Atlas CDN to Emergent Object Storage. Proxy endpoint at `/api/files/{path}`. Admin UI with progress bar. Resumable.

## Attachment Migration Architecture
- **Engine:** `backend/services/attachment_migration.py`
- **CDN domains migrated:** `files.atlas.so`, `cdn.discordapp.com`, `media.discordapp.net`
- **Storage:** Emergent Object Storage at `trinity/attachments/{uuid}.{ext}`
- **Proxy:** `GET /api/files/{path}` — serves files from storage (public, cached 24h)
- **DB update:** `attachments[].url` → `/api/files/...`, `attachments[].original_url` → original CDN URL
- **Admin API:** Start/Stop/Status at `/api/admin/atlas/attachments/*`
- **Admin UI:** Progress bar, stats, start/stop in Atlas Sync tab

## Upcoming Tasks
1. **P2: Real-time Agent Notifications**
2. **P2: Auto-Close Stale Tickets** (recurring job)
3. **P3: Atlas Webhook Registration** for real-time sync supplement

## Key Files
- `/app/backend/services/attachment_migration.py` — Attachment migration engine
- `/app/backend/services/atlas_sync.py` — Shadow sync engine
- `/app/backend/services/atlas_backfill.py` — Historical backfill engine
- `/app/backend/services/email_poller.py` — Email ingestion
- `/app/backend/routes/atlas.py` — All Atlas admin API endpoints
- `/app/backend/server.py` — App startup + file proxy
- `/app/frontend/src/components/admin/AdminPage.js` — Admin page with sync + migration UI
- `/app/frontend/src/components/tickets/EmailMessage.js` — Message rendering + collapsible quotes

## Credentials
- **Atlas API Key:** `NY7YY8Y3092NKWXSQGR8BT3NIXNFOGFWBGFJ36WD8KCBQ9UIQ8VM8CX2K1I2LY75`
- **Admin API Key:** `tk_live_C47oqvueOkUiCEBs-8EBNkJmu3-VyYdSfOB8RgeFZXI`
- **Auth:** Emergent Google OAuth
