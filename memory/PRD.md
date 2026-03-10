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
- **Bidirectional assignment sync**: Trinity pushes assignment changes TO Atlas via `POST /v1/conversations/{id}` so assignments aren't overwritten by next sync cycle
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
- [x] Fix: Dead zone for closed tickets with null last_synced_at (2026-03-10)
- [x] Fix: Email search using regex for @ queries instead of $text (2026-03-10)
- [x] Fix: Attachment rendering in message threads (frontend) (2026-03-10)
- [x] Fix: IMAP duplicate prevention via _has_atlas_duplicate (2026-03-10)
- [x] Fix: "Assign to me" button — bidirectional Atlas sync (2026-03-10)
- [x] **Feature: File attachment support for outbound emails** (2026-03-10)

## Recent: File Attachment Feature (2026-03-10)

### What's New
Agents can now attach files (PDFs, Word, Excel, images, text, CSV, ZIP, etc.) when replying to customers. Files are:
1. Uploaded and stored server-side
2. Attached as MIME parts in outbound emails via SES
3. Displayed in the conversation thread for audit

### Implementation
- **Backend**: `POST /api/attachments/upload`, `GET /api/attachments/{file_id}`, `DELETE /api/attachments/{file_id}`
- **Backend**: `send_email()` enhanced with MIME multipart/mixed for file attachments
- **Backend**: `POST /api/tickets/{id}/notes` accepts `attachment_ids`, stores metadata in message record
- **Frontend**: "File" button in composer toolbar, file preview with name/size/remove, outbound attachment display in messages
- **Limits**: 7MB per file, 10MB total (SES limit). Allowed types: PDF, Word, Excel, PowerPoint, text, CSV, ZIP, images
- **Storage**: Files in `/app/backend/uploads/`, metadata in MongoDB `file_attachments` collection

### Files Modified
- `/app/backend/routes/email.py` — Upload/download/delete endpoints
- `/app/backend/services/email_service.py` — MIME attachment support
- `/app/backend/routes/tickets.py` — Notes endpoint accepts attachment_ids
- `/app/backend/models/schemas.py` — InternalNoteCreate schema
- `/app/backend/database.py` — file_attachments_collection
- `/app/frontend/src/hooks/useTicketDrawer.js` — File state, upload/remove handlers
- `/app/frontend/src/components/tickets/TicketConversation.js` — File button + preview UI
- `/app/frontend/src/components/tickets/TicketDrawer.js` — Props passthrough
- `/app/frontend/src/components/tickets/EmailMessage.js` — Outbound attachment rendering

## In Progress
- [ ] Attachment migration: paused due to object storage 500 errors (auto-resume enabled)

## Upcoming Tasks
- [ ] P1: Create one-time script to deduplicate historical IMAP messages
- [ ] P1: Deprecate polling sync once webhooks proven stable
- [ ] P1: User must re-deploy to trigger ticket ID migration and message backfill
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
- `tickets`: ticket_id, atlas_conversation_id (unique sparse), status (todo/waiting/closed/merged)
- `messages`: ticket_id, atlas_message_id (unique sparse), attachments array (for outbound: file_id, original_name, content_type, size, download_url)
- `users`: role field (default "agent"), email (mapped to Atlas agent IDs)
- `inboxes`: system + user-created inboxes
- `backfill_state`: Tracks one-time migration status
- `file_attachments`: file_id, original_name, stored_name, content_type, size, uploaded_by, created_at

## Critical Files
- `/app/backend/routes/atlas_webhooks.py` — Atlas webhook handler
- `/app/backend/services/atlas_sync.py` — Atlas polling sync + bidirectional assignment sync
- `/app/backend/services/email_service.py` — SES email with MIME attachments
- `/app/backend/services/email_poller.py` — IMAP poller (with dedup)
- `/app/backend/routes/email.py` — File upload/download/delete + data import
- `/app/backend/search.py` — Search engine (with email regex fix)
- `/app/backend/server.py` — Startup hooks, /health endpoint
- `/app/backend/routes/tickets.py` — Ticket CRUD + Atlas assignment sync + notes with attachments
- `/app/frontend/src/hooks/useTicketDrawer.js` — Thread builder (images + file attachments)
- `/app/frontend/src/components/tickets/TicketConversation.js` — Composer with file attachment UI
- `/app/frontend/src/components/tickets/EmailMessage.js` — Message display (inbound + outbound attachments)
