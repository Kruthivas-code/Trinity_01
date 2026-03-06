# Trinity - Support Ticket Management System

## Original Problem Statement
Migrate historical data from Atlas support platform into Trinity and establish real-time two-way sync. Extended to include comprehensive metadata import, agent account import, and new features (bounce details, CC on replies, agent-initiated tickets).

## Core Architecture
- **Frontend:** React (CRA) + Shadcn UI + TailwindCSS
- **Backend:** FastAPI (Python) on port 8001
- **Database:** MongoDB (`test_database`)
- **Auth:** Emergent-managed Google OAuth
- **Integrations:** Gemini (summarization), Amazon SES (outbound email), Gmail IMAP (inbound email), Atlas API (historical data)

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

## Upcoming Tasks (Priority Order)
1. **P1: Data Validation Script** — Admin endpoint to audit DB for duplicate tickets/messages
2. **P2: Real-Time Atlas Sync ("Shadow Mode")** — Two-way live sync per atlas_sync_plan.md
3. **P2: Real-time Agent Notifications**
4. **P2: Auto-Close Stale Tickets** (recurring job)
5. **P3: Migrate Atlas Attachments to Blob Storage**

## Key Files
- `/app/backend/services/atlas_backfill.py` — Backfill engine
- `/app/backend/routes/atlas.py` — Backfill API
- `/app/backend/server.py` — App startup + auto-resume
- `/app/memory/atlas_sync_plan.md` — Migration strategy doc

## Credentials
- **Atlas API Key:** `NY7YY8Y3092NKWXSQGR8BT3NIXNFOGFWBGFJ36WD8KCBQ9UIQ8VM8CX2K1I2LY75`
- **Auth:** Emergent Google OAuth
