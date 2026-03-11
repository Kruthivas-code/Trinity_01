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
- [x] **Fix: Users list truncation (limit=100 -> limit=500)** (2026-03-11)
- [x] **Fix: "Unassigned" button now persists to backend** (2026-03-11)
- [x] **Fix: Toast notifications for assignment success/failure** (2026-03-11)
- [x] **Fix: Error propagation in handleUpdateTicket** (2026-03-11)
- [x] **Fix: trinity_assigned_at only set on actual assignee change** (2026-03-11)
- [x] **Fix: System messages use 'content' field consistently** (2026-03-11)
- [x] **Fix: Merged duplicate closed_at/resolved_at logic** (2026-03-11)
- [x] **Feature: Information density — tags & customer email in list view** (2026-03-11)
- [x] **Feature: Relative time (age) display in Kanban cards and list view** (2026-03-11)

### Session 2026-03-11 (Ghost User Fix)
- [x] **ROOT CAUSE FIX: @imported.local ghost user records** (2026-03-11)
  - Identified that 25 users were imported with placeholder `@imported.local` emails
  - When these users log in via Google OAuth, the auth upsert creates a GHOST duplicate record
  - The ghost has a different user_id from the imported record, breaking assignment mapping
- [x] **Migration script: fix_imported_local_emails.py** — Fixes existing @imported.local records by:
  - Looking up real emails via Atlas API using atlas_user_id
  - Merging ghost records (updates all references, deletes ghost)
  - Updating placeholder emails to real emails
- [x] **Auth flow fix: _resolve_imported_user()** — Prevents future ghost records by:
  - Before upsert, checks if login email has no direct match
  - Queries Atlas API for atlas_user_id, finds imported user with placeholder email
  - Updates imported record's email to real email BEFORE the upsert
  - Subsequent upsert merges into the existing (now-corrected) record
- [x] **Defensive validation: assignee_id existence check** — in both:
  - `PUT /api/tickets/{id}` (update_ticket)
  - `POST /api/tickets/{id}/assign` (assign_ticket)
  - Returns 400 with clear error for nonexistent user_ids
  - Null (unassign) is explicitly allowed

## Root Cause Analysis: "Assign to me" Button Failure

### The Problem
25 Atlas agents were bulk-imported on 2026-01-27 with placeholder emails like `animesh@imported.local`. When these users log in via Google OAuth with their real email (`animesh@emergent.sh`), the auth flow's `update_one({"email": email}, ..., upsert=True)` finds NO match (placeholder ≠ real email), creating a ghost duplicate user record.

**Result**: Two records for the same person:
- Imported record: `user_animesh_xxx` / `animesh@imported.local` — tickets reference this
- Ghost record: `user_yyy_zzz` / `animesh@emergent.sh` — session uses this

When the user clicks "Assign to me", the ghost user_id is written as assignee_id. The `agent_email_map` (email-based sync mapping) may also resolve inconsistently between the two records.

### Why it worked for rohit@emergent.sh
Rohit had BOTH an imported record AND an organic record (with real email, password, Google OAuth). The auth upsert matched on his real email, linking the session to his organic record. Other users only had the @imported.local record.

### The Fix (3 layers)
1. **Migration script** — fixes existing data (deployed, runs on next startup)
2. **Auth flow enhancement** — prevents future ghosts via Atlas API lookup
3. **Defensive validation** — prevents writing nonexistent user_ids

## Upcoming Tasks
- [ ] P0: Deploy and run migration script (fix_imported_local_emails.py --apply)
- [ ] P1: Create one-time script to deduplicate historical IMAP messages
- [ ] P1: Deprecate polling sync once webhooks proven stable
- [ ] P1: User must re-deploy to trigger ticket ID migration and message backfill
- [ ] P2: Align Trinity user_ids with Atlas UUIDs (eliminate email-based mapping entirely)
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
- `tickets`: ticket_id, atlas_conversation_id, status, assignee_id, trinity_assigned_at
- `messages`: ticket_id, atlas_message_id, attachments array, content (not text)
- `users`: user_id, email, role, atlas_user_id, source
- `file_attachments`: file_id, original_name, stored_name, content_type, size, uploaded_by
- `backfill_state`: Tracks one-time migration status
