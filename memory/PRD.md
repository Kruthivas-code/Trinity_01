# Trinity - Support Ticket Management System

## Original Problem Statement
Migrate historical data from Atlas support platform into Trinity and establish real-time two-way sync. Extended to include comprehensive metadata import, agent account import, new features, attachment migration, and AI ticket management.

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
| `waiting` | Waiting on customer |
| `closed` | Ticket completed |

## Completed Work
- **Atlas Historical Backfill:** ~67,000 conversations, ~348,000 messages imported
- **Atlas Metadata Enrichment:** CSAT, custom fields, attachments, timestamps
- **Atlas Agent Import:** 163 agents with upsert-by-email dedup
- **Status Standardization:** `resolved` → `closed`, waiting variants → `waiting`
- **Atlas Shadow Sync:** Real-time polling every 60s, auto-starts on boot
- **Collapsible Quoted Text:** Email reply chains collapse behind `···` toggle
- **Email Capitalization Fix:** from_addr lowercased in email_poller
- **Attachment Migration:** Background job downloading ~65K files from Atlas CDN to Emergent Object Storage
- **Zeus (AI) Ticket Cleanup (2026-03-06):** Recurring job (30 min) closes Zeus-assigned tickets stale > 48h. Closes on both Trinity and Atlas. Already processed 2,700+ tickets.
- **Assigned to AI View (2026-03-06):** New sidebar nav + page showing active Zeus-assigned tickets. Filters by `atlas_assigned_to_zeus=true` on tickets API.

## Zeus Cleanup Architecture
- **Engine:** `backend/services/zeus_cleanup.py`
- **Rule:** Close if `atlas_assigned_to_zeus=True` AND `last_message_at > 48h ago`
- **Batch:** 500 tickets per run, every 30 minutes
- **Atlas close:** Uses `POST /v1/conversations/{id}` with `{"status": "CLOSED"}`
- **System message:** Added to ticket when auto-closed
- **Admin API:** `GET /api/admin/atlas/zeus/status`, `POST /api/admin/atlas/zeus/run`

## Verified (2026-03-06)
- **Authenticated Screenshots:** Working with QA session cookie (`session_token=qa_test_admin_session_token_2026`)
- **Cross-Browser CSS Fix:** Sidebar text visibility confirmed on Chromium via screenshot
- **Data Integrity Validation:** 15 tickets sampled (10 Atlas + 5 regular) — zero duplicate messages
- **Collapsible Email Quotes:** Verified in UI — "..." toggle correctly hides quoted reply chains
- **Background Jobs Re-verified:**
  - Atlas Shadow Sync: Running (1347 conversations checked, 527 messages synced)
  - Attachment Migration: Restarted and running (737/65,093 migrated, 595MB transferred)
  - Zeus Cleanup: Auto-recurring every 30 min (500 closed so far, 6,679 remaining)

## Upcoming Tasks
1. **P2: Real-time Agent Notifications**
2. **P2: Auto-Close Stale Tickets** (non-Zeus, general recurring job)
3. **P3: Atlas Webhook Registration**

## Key Files
- `/app/backend/services/zeus_cleanup.py` — Zeus cleanup engine
- `/app/backend/services/attachment_migration.py` — Attachment migration
- `/app/backend/services/atlas_sync.py` — Shadow sync engine
- `/app/backend/services/atlas_backfill.py` — Historical backfill
- `/app/backend/routes/atlas.py` — All Atlas admin endpoints
- `/app/backend/server.py` — Startup + recurring jobs + file proxy
- `/app/frontend/src/components/tickets/AIAssignedTicketsPage.js` — AI view
- `/app/frontend/src/components/layout/Sidebar.js` — Navigation
- `/app/frontend/src/components/admin/AdminPage.js` — Admin with sync + migration UI

## Credentials
- **Atlas API Key:** `NY7YY8Y3092NKWXSQGR8BT3NIXNFOGFWBGFJ36WD8KCBQ9UIQ8VM8CX2K1I2LY75`
- **Admin API Key:** `tk_live_C47oqvueOkUiCEBs-8EBNkJmu3-VyYdSfOB8RgeFZXI`
- **Auth:** Emergent Google OAuth
