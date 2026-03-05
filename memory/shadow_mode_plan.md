# Shadow Mode: Atlas ↔ Trinity Merge & Sync Plan

## Context

Atlas and Trinity both watch the same inbox (`support@emergent.sh`). This creates duplicate tickets — the same email conversation exists as:
- A Trinity ticket (`source: "email"`, with `gmail_thread_id`)
- An Atlas ticket (`source: "atlas"`, with `atlas_conversation_id`)

There is no shared identifier between the two systems. Atlas does not expose Gmail Thread IDs.

**Goal:** Merge these duplicates, remap `source` to mean "channel" (not "import origin"), and establish a clean shadow mode where both systems can operate simultaneously without conflicts.

---

## Phase 1: Schema Changes

### 1.1 New field: `imported_from`
Add `imported_from: "atlas"` to all Atlas-originating tickets. This replaces the current overloading of `source`.

### 1.2 Remap `source` to reflect actual channel
| Current `source` | Current `started_channel` | New `source` |
|---|---|---|
| `atlas` | `EMAIL` | `email` |
| `atlas` | `DISCORD_CONNECT` | `discord` |
| `atlas` | (null/other) | `atlas` (keep as-is, rare) |
| `email` | — | `email` (unchanged) |
| `portal` | — | `portal` (unchanged) |
| `manual` | — | `manual` (unchanged) |

### 1.3 Update code references
- Backfill mapper: set `source` from `started_channel`, add `imported_from: "atlas"`
- Enrichment: same remapping
- Real-time sync: same
- Any queries filtering by `source: "atlas"` → use `imported_from: "atlas"` instead
- UI: no changes needed (it already shows "email", "discord" etc. based on source)

---

## Phase 2: Dedup & Merge (One-Time)

### 2.1 Matching Strategy

Match Atlas email tickets to Trinity email tickets by:
- **`customer_email`** (exact, case-insensitive)
- **`title` / subject** (exact or near-exact after normalization: strip "Re:", "Fwd:", whitespace)
- **`created_at`** (within ±5 minute window)

All three must match. This is 100% reliable for email conversations from the same inbox.

### 2.2 Merge Rules (Atlas wins, Trinity preserves email threading)

When a match is found (Atlas ticket A, Trinity ticket T):

| Field | Winner | Rationale |
|---|---|---|
| `ticket_id` | **Trinity** | Preserves all internal references, notes, changelog |
| `status` | **Atlas** | Atlas is source of truth |
| `priority` | **Atlas** | Atlas is source of truth |
| `assignee_id` | **Atlas** | Atlas is source of truth |
| `tags` | **Atlas** | Atlas is source of truth |
| `custom_fields` | **Atlas** | Atlas is source of truth |
| `customer_email` | Either (same) | — |
| `customer_name` | **Atlas** | May be richer |
| `customer_id` | **Trinity** | Preserves CRM linkage |
| `created_at` | **Atlas** | Original timestamp |
| `closed_at` | **Atlas** | — |
| `assigned_at` | **Atlas** | — |
| `escalated_at` | **Atlas** | — |
| `title` | **Atlas** | May have been edited |
| `description` | Keep both | Trinity may have richer first message |
| `gmail_thread_id` | **Trinity** | Critical for email threading |
| `email_message_id` | **Trinity** | Critical for email threading |
| `in_reply_to` | **Trinity** | Email threading |
| `atlas_conversation_id` | **Atlas** | Link to Atlas |
| `atlas_*` (all metadata) | **Atlas** | CSAT, stats, actor tracking, etc. |
| `started_channel` | **Atlas** | — |
| `started_sub_channel` | **Atlas** | — |
| `browser` / `operating_system` | **Atlas** | — |
| `imported_from` | Set to `"atlas"` | Mark as merged |
| `source` | `"email"` | Channel, not origin |

### 2.3 Message Merge

For matched tickets, messages from both sides need to coexist:
- **Trinity messages** (agent replies sent from Trinity): Keep as-is. These have email threading headers.
- **Atlas messages**: Import any messages NOT already present in Trinity (by matching `atlas_message_id` or by content+timestamp dedup).
- **Duplicate messages** (same email captured by both systems): Keep the Trinity version (has email headers), skip the Atlas version.

Message dedup strategy:
- Match by `author_email` + `created_at` (within ±60s window)
- If matched: skip Atlas message (Trinity version is richer with email headers)
- If not matched: import Atlas message (it's a message Trinity didn't capture, e.g. from Discord sidebar or Atlas-only reply)

### 2.4 Handle Unmatched Tickets

**Atlas tickets with no Trinity match:**
- These are either older (pre-Trinity) or Discord-channel tickets
- Remap `source` based on `started_channel`, add `imported_from: "atlas"`
- No merge needed

**Trinity tickets with no Atlas match:**
- Should not exist per user (Atlas is source of truth)
- Flag for manual review if found
- Likely edge cases: portal tickets, manual tickets, or very recent emails not yet in Atlas

### 2.5 Cleanup After Merge

For each matched pair (Atlas A, Trinity T):
1. Patch Trinity ticket T with Atlas metadata (per merge rules above)
2. Import any missing Atlas messages into T
3. **Delete the Atlas-only ticket A** (its data now lives on T)
4. The `atlas_conversation_id` on T links back to Atlas for ongoing sync

---

## Phase 3: Ongoing Shadow Mode Sync

After the one-time merge, both systems run simultaneously:

### 3.1 Inbound (Atlas → Trinity)

The sync worker polls Atlas every 60s for new/updated conversations:

**New conversation in Atlas (no matching Trinity ticket):**
- Create Trinity ticket with `source` based on channel, `imported_from: "atlas"`
- Import all messages

**Existing conversation updated in Atlas:**
- Find Trinity ticket by `atlas_conversation_id`
- Sync: status, priority, assignee, tags (Atlas wins)
- Import new messages not yet in Trinity

### 3.2 Inbound (Email → Trinity)

Trinity's IMAP poller continues to process emails independently:
- Creates tickets with `source: "email"` as before
- If a new email ticket is created, it won't have `atlas_conversation_id` yet
- The next Atlas sync cycle will find the matching Atlas conversation and link them (set `atlas_conversation_id` on the Trinity ticket)

### 3.3 Outbound (Trinity → Atlas)

Not needed for shadow mode. Agents work in Trinity, emails go out via SES. Atlas sees the same emails arrive via its own email integration.

### 3.4 Conflict Resolution During Shadow Mode

| Scenario | Resolution |
|---|---|
| Status changed in Atlas | Atlas wins → update Trinity |
| Status changed in Trinity | Trinity change persists until next Atlas sync overwrites it |
| New reply sent from Trinity | Email goes via SES, Atlas captures it independently |
| New reply sent from Atlas | Email goes via Atlas, Trinity IMAP poller captures it |
| Assignment changed in Atlas | Atlas wins → update Trinity |
| CSAT submitted in Atlas | Synced to Trinity via `atlas_csat_score` |

---

## Phase 4: Full Cutover (Future)

When ready to fully switch from Atlas to Trinity:
1. Stop Atlas sync worker
2. Trinity becomes sole source of truth
3. Status/assignment changes in Trinity are authoritative
4. Atlas can be decommissioned

---

## Implementation Order

| Step | Task | Effort |
|---|---|---|
| 1 | Schema: add `imported_from` field, remap `source` in DB | 30 min |
| 2 | Update backfill/enrichment mapper to use new schema | 30 min |
| 3 | Update code: replace `source: "atlas"` queries with `imported_from: "atlas"` | 1 hr |
| 4 | Build dedup/merge script (match + merge + cleanup) | 2-3 hrs |
| 5 | Run merge (one-time, resumable) | Runtime depends on data |
| 6 | Verify: no duplicates, correct threading, correct statuses | 1 hr |
| 7 | Update real-time sync to use new schema + matching logic | 2 hrs |
| 8 | Test shadow mode end-to-end | 1 hr |

**Total: ~8-10 hours of dev work**

---

## Data Volumes

| Metric | Count |
|---|---|
| Atlas email tickets to match | ~40,000 (EMAIL channel) |
| Atlas Discord tickets (no match needed) | ~27,000 |
| Trinity email tickets | ~44,700 |
| Expected matches | ~35,000-40,000 |
| Expected Atlas-only (older/Discord) | ~27,000-32,000 |
| Expected Trinity-only (very recent, edge cases) | <100 |

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| False positive match (wrong dedup) | Require all 3 criteria (email + subject + timestamp). Log all matches for review. |
| Missing messages after merge | Import ALL Atlas messages, dedup by content+timestamp |
| Email threading broken | Trinity ticket preserved with `gmail_thread_id` — threading continues to work |
| Enrichment running concurrently | Stop enrichment before running merge, restart after |
