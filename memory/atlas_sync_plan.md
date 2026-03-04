# Atlas Data Sync & Backfill Strategy

## Overview

This document outlines the strategy for migrating historical data from **Atlas** (https://atlas.so) into **Trinity** and establishing a real-time two-way sync ("shadow mode") so Trinity can operate as the primary support tool while Atlas continues to receive data.

**Atlas API Base:** `https://api.atlas.so/v1`
**Atlas API Docs:** https://developers.atlas.so/reference

---

## Current State

| Metric | Value |
|--------|-------|
| Atlas total conversations | ~66,635 |
| Atlas tags | 20 |
| Channels in Atlas | EMAIL (~60%), DISCORD_CONNECT (~40%) |
| Trinity tickets (non-Atlas) | ~44,233 |
| Trinity messages (non-Atlas) | ~108,985 |
| Atlas tickets already imported | 0 |

### Existing Code

| File | Purpose | Status |
|------|---------|--------|
| `backend/atlas_import.py` | Full historical import orchestrator (async, paginated, dedup) | Ready, untested at scale |
| `backend/services/atlas_sync.py` | Ongoing sync — polls Atlas for agent replies, inserts into Trinity | Ready, untested at scale |
| `backend/routes/email.py` | `POST /api/email/import/atlas` endpoint to trigger import | Wired up |
| DB indexes | `atlas_conversation_id` (unique, sparse), `atlas_message_id` (unique, sparse) | Created |

### Atlas API Data Model

**Conversation fields:** `id`, `customerId`, `customer`, `startedAt`, `createdAt`, `closedAt`, `assignedAgent`, `assignedAgentId`, `assignedTeamId`, `number`, `subject`, `status` (OPEN/CLOSED/SNOOZED/PENDING), `priority` (NO_PRIORITY/LOW/NORMAL/HIGH/URGENT), `tags` (UUID array), `customFields`, `startedChannel` (EMAIL/DISCORD_CONNECT), `csat`, `statistics`, `lastMessage`

**Message fields:** `id` (integer), `side` (customer/agent/bot), `type`, `createdAt` (epoch), `sentAt` (epoch), `agent` (object), `customer` (object), `text` (HTML), `channel`, `attachments`

**Tag fields:** `id` (UUID), `label`, `groupId`, `archived`, `used`

---

## Phase 1: Historical Backfill (One-Time)

### Goal
Import all ~66,635 Atlas conversations and their messages into Trinity as historical records.

### Strategy

**Batch processing** — Process conversations in pages of 100, with rate limiting to respect Atlas API limits.

**Steps:**
1. **Fetch all tags** — Build UUID-to-label lookup for tag resolution
2. **Paginate conversations** — Fetch 100 at a time using cursor-based pagination (`cursor=0, limit=100`, increment by page size)
3. **For each conversation:**
   a. **Dedup check** — Skip if `atlas_conversation_id` already exists in `tickets` collection
   b. **Map conversation to ticket** — Using `map_conversation_to_ticket()` in `atlas_import.py`
   c. **Fetch all messages** — Paginate messages for the conversation
   d. **Map messages to notes** — Using `map_message_to_note()` in `atlas_import.py`
   e. **Link customer** — Match or create customer record by email
   f. **Map agent** — Match Atlas agent email to Trinity user_id
   g. **Insert ticket + messages** — Atomic per-conversation

### Field Mapping

| Atlas Field | Trinity Field | Notes |
|-------------|--------------|-------|
| `id` | `atlas_conversation_id` | UUID, stored for dedup |
| `subject` | `title` | Falls back to "Conversation #N" |
| `status` (OPEN/CLOSED/SNOOZED/PENDING) | `status` (todo/resolved/waiting/in_progress) | Via `STATUS_MAP` |
| `priority` (NO_PRIORITY/LOW/NORMAL/HIGH/URGENT) | `priority` (medium/low/medium/high/urgent) | Via `PRIORITY_MAP` |
| `tags` (UUID[]) | `tags` (string[]) | Resolved via tag lookup |
| `customer.email` | `customer_email` | Used for customer linking |
| `assignedAgent.email` | `assignee_id` | Matched to Trinity user by email |
| `createdAt` | `created_at` | Epoch -> UTC datetime |
| `closedAt` | `closed_at` | Epoch -> UTC datetime |
| `startedChannel` | `source` = "atlas" | Always "atlas" for imported tickets |
| `startedChannel` | `started_channel` | Preserved as-is (EMAIL, DISCORD_CONNECT) |
| Message `side` (AGENT/CUSTOMER/BOT) | `type` (reply/customer_reply/reply/system) | Via `MESSAGE_TYPE_MAP` |
| Message `text` | `content` | HTML stripped for plain text |
| Message `sentAt` | `created_at` | Epoch -> UTC datetime |

### Rate Limiting & Error Handling

- **Rate limit**: 500ms sleep between conversation batches (2 API calls per conversation: list + messages)
- **Timeout**: 60s per HTTP request
- **Retries**: On HTTP timeout or 429, wait 5s and retry. On persistent failure, skip conversation and log error
- **Progress tracking**: Store cursor position in `atlas_sync_state` collection for resumability
- **Dedup**: Unique sparse index on `atlas_conversation_id` and `atlas_message_id` prevents duplicates on re-run

### Execution Plan

```
1. Verify Atlas API key is valid (test fetch with limit=1)
2. Run backfill in background process (not blocking main app)
3. Log progress every 10 batches (1,000 conversations)
4. Expected duration: ~66,635 conversations / 100 per batch = 667 batches
   At 500ms between batches + ~1s per conversation for messages = ~18-20 hours
5. Backfill is idempotent — safe to restart from last cursor on failure
```

### Estimated Data Volume

| Metric | Estimate |
|--------|----------|
| New tickets | ~66,635 |
| New messages | ~200,000-400,000 (avg 3-6 per conversation) |
| New customer records | ~10,000-20,000 (deduped by email) |
| DB size increase | ~200-400 MB |

---

## Phase 2: Data Validation & Cleanup

### Goal
Verify the imported data is correct and clean up any issues.

### Checks

1. **Count verification**: Compare Atlas total vs Trinity imported count
2. **Message integrity**: Verify each imported ticket has at least 1 message
3. **Timestamp sanity**: Ensure `created_at` values are reasonable (not in the future, not before 2020)
4. **Customer linking**: Verify customer records were created/linked correctly
5. **Agent mapping**: Report on how many tickets had agents mapped vs unmapped
6. **Tag resolution**: Report on any unresolved tag UUIDs
7. **Duplicate check**: Ensure no duplicate `atlas_conversation_id` values

### Cleanup Script

```python
# Validation queries to run post-backfill:
# 1. Tickets without messages
# 2. Messages without matching tickets  
# 3. Tickets with future timestamps
# 4. Summary statistics by status, channel, priority
```

---

## Phase 3: Real-Time Sync ("Shadow Mode")

### Goal
Keep Trinity in sync with Atlas in real-time so agents can gradually transition from Atlas to Trinity.

### Architecture

```
Atlas (source of truth during transition)
  |
  |  [Periodic Poll — every 60s]
  v
Trinity Sync Worker
  |
  ├── New conversations  →  Create ticket + messages
  ├── New messages       →  Append to existing ticket
  ├── Status changes     →  Update ticket status
  └── Assignment changes →  Update ticket assignee
```

### Sync Strategy

**Direction: Atlas → Trinity (one-way read)**

The sync worker will:
1. **Poll for recent conversations** — Fetch conversations updated in the last 2 minutes (`startDate` param)
2. **For each conversation:**
   a. If `atlas_conversation_id` exists in Trinity → check for new messages and status/assignment changes
   b. If not → create new ticket with all messages (same flow as backfill)
3. **Message sync**: Compare Atlas message count vs Trinity message count for the ticket. Fetch and insert any new messages.
4. **Status sync**: If Atlas status changed, update Trinity ticket status (using `STATUS_MAP`)
5. **Assignment sync**: If Atlas agent changed, update Trinity assignee

### Conflict Resolution

During shadow mode, Atlas is the **source of truth**:
- Atlas changes always overwrite Trinity for synced fields (status, priority, assignee)
- Trinity-only fields (custom notes, internal tags) are preserved
- Messages are append-only — never deleted or modified during sync

### Polling Interval

| Phase | Interval | Rationale |
|-------|----------|-----------|
| Initial (first week) | 60 seconds | Aggressive sync for testing |
| Stable (after validation) | 120 seconds | Reduce API load |
| Transition complete | Disabled | Atlas no longer authoritative |

### Implementation: Existing `services/atlas_sync.py`

The current `atlas_sync.py` needs to be enhanced:

1. **Current**: Only syncs agent messages for EMAIL conversations matched by customer email
2. **Needed**: 
   - Sync ALL channels (not just EMAIL)
   - Sync ALL message types (customer + agent + bot)
   - Sync status/priority/assignment changes
   - Create new tickets for conversations not yet in Trinity
   - Use `atlas_conversation_id` for matching (not customer email)

### Background Worker

The sync worker will run as a background thread (same pattern as `email_poller.py`):

```python
def start_atlas_sync():
    """Start the Atlas sync daemon thread."""
    thread = threading.Thread(target=_sync_loop, daemon=True)
    thread.start()

def _sync_loop():
    while not _stop_event.is_set():
        try:
            sync_recent_conversations()
        except Exception as e:
            logger.error(f"[ATLAS SYNC] Error: {e}")
        _stop_event.wait(60)  # Poll every 60s
```

### Admin Controls

Expose sync status and controls via API:

- `GET /api/admin/atlas-sync/status` — Current sync state (last cursor, last run, counts)
- `POST /api/admin/atlas-sync/start` — Start the sync worker
- `POST /api/admin/atlas-sync/stop` — Stop the sync worker
- `POST /api/admin/atlas-sync/backfill` — Trigger historical backfill

### Dashboard UI

Add an "Atlas Sync" section to the admin dashboard:

- Sync status indicator (running/stopped)
- Last sync timestamp
- Conversations synced count
- Messages synced count
- Error count and recent errors
- Start/Stop/Backfill buttons

---

## Implementation Order

| Step | Task | Effort | Dependencies |
|------|------|--------|-------------|
| 1 | Update `.env` with correct Atlas API key | 5 min | None |
| 2 | Enhance `atlas_import.py` — fix tag label lookup, test with small batch | 1 hr | Step 1 |
| 3 | Run historical backfill (background) | 18-20 hrs | Step 2 |
| 4 | Run validation queries | 30 min | Step 3 |
| 5 | Enhance `atlas_sync.py` — full conversation sync, status/assignment sync | 3-4 hrs | Step 2 |
| 6 | Add sync background worker with start/stop | 1 hr | Step 5 |
| 7 | Add admin API endpoints | 1 hr | Step 6 |
| 8 | Add admin dashboard UI | 2-3 hrs | Step 7 |

**Total estimated effort: 2-3 days** (excluding backfill runtime)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Atlas API rate limiting | 500ms delay between batches, exponential backoff on 429 |
| Large data volume (~66K conversations) | Cursor-based pagination, resumable from last position |
| Network failures during backfill | Idempotent import (dedup by `atlas_conversation_id`) |
| Data mapping errors | Preserve all Atlas fields in `atlas_*` prefixed fields for debugging |
| Conflicting edits in shadow mode | Atlas is source of truth; Trinity fields not overwritten |
| API key expiry | Monitor for 401 responses, alert admin |

---

## Success Criteria

1. All ~66,635 Atlas conversations imported into Trinity with correct field mapping
2. Real-time sync running with < 2 minute lag
3. No duplicate tickets or messages
4. Agent can view full conversation history for any customer across both Atlas and Trinity-native tickets
5. Admin can monitor sync health and control the worker
