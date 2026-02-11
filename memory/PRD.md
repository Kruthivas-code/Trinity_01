# Trinity - Customer Support Ticketing System

## Original Problem Statement
Build a web-based customer support ticketing system ("Trinity") with ticket management, canned responses, and data import capabilities from external tools.

## Core Features
- Ticket dashboard with priority/escalation badges
- Detailed ticket view in drawer with metadata
- Canned response system with in-app creation
- Data import from external tools (Zendesk, Atlas)
- Email ingestion via IMAP (forwarded from support@emergent.sh)
- Team management, routing rules, SLA escalation
- Server-side pagination with infinite scroll
- Scalable analytics via MongoDB aggregation pipelines
- Real-time ticket updates via Socket.IO (no page refresh needed)

## Tech Stack
- **Frontend**: React 19, React Router v7, Shadcn UI
- **Backend**: Python, FastAPI
- **Database**: MongoDB (sync pymongo driver)
- **Email**: IMAP (Gmail App Password), UID-based tracking, **IMAP IDLE push**
- **Real-time**: Socket.IO (WebSocket + polling fallback)

## What's Been Implemented
- Ticket Drawer UI Enhancement (priority + escalation badges in left panel)
- In-App Canned Response Creation (create directly from picker modal)
- Atlas Import backend logic (`POST /api/import/atlas`)
- Database indexes for Atlas deduplication + compound indexes for pagination
- Deployment blocker fixes (hardcoded DB name -> env variable)
- Production navigation bug fix (React.lazy + window.history.pushState desync)
- Post-login auth cache fix (module-level user cache in ProtectedRoute)
- Server-side pagination on GET /api/tickets with infinite scroll
- **8 Scalability Fixes**: analytics aggregation, auto-close batch ops, streaming export, notes pagination, N+1 fix, compound indexes
- **IMAP Email Sync (UID-based + IDLE push)** — Feb 2026:
  - Replaced unreliable time-based IMAP fetching with UID-tracking mechanism
  - **IMAP IDLE** for near-realtime push notifications (~1-5s latency vs 60s polling)
  - `IMAPIdleWatcher` class maintains persistent IMAP connection using `imapclient`
  - Auto-reconnects with exponential backoff (5s→60s) on failures
  - Renews IDLE every 25 min (Gmail drops after ~29 min)
  - Thread-safe callback via `asyncio.run_coroutine_threadsafe`
  - `imap_sync_state` MongoDB collection stores last_uid persistently
  - First-run seeding: sets last_uid to current max UID (no backfill)
  - Fixed Gmail IMAP connection hang on close/logout (force-close socket)
  - Unique sparse index on `email_replies.email_rfc_message_id`
- **Real-time ticket push** — Feb 2026:
  - Fixed ObjectId serialization in Socket.IO broadcasts (serialize_doc before emit)
  - Fixed wrong function name/signature (broadcast_ticket_updated → broadcast_ticket_update)
  - Fixed Socket.IO routing for Kubernetes ingress (/api/socket.io/ path)
  - Fixed RequestIdFilter applied to all logger handlers (not just module logger)
  - Added error-level logging for broadcast failures in email sync task
  - New email-created tickets now appear in UI without page refresh (verified E2E)

## Key API Endpoints
- `GET /api/tickets?page=1&limit=50&status=todo&status=in_progress` — Paginated, multi-status
- `GET /api/analytics/summary` — Single $facet aggregation
- `GET /api/analytics/overview?days=30` — Full analytics via aggregation pipeline
- `GET /api/tickets/{id}/notes?page=1&limit=100` — Paginated notes
- `GET /api/export?format=json|csv` — Streaming export
- `POST /api/email/sync?fetch_all=false` — Manual IMAP sync (UID-based)
- `GET /api/email/status` — IMAP connection + sync state status

## Key DB Collections
- `tickets` — Ticket data with email metadata
- `email_replies` — Incoming/outgoing email replies (unique index on email_rfc_message_id)
- `imap_sync_state` — Stores `{_id: "imap_last_uid", last_uid: <int>, seeded: <bool>, updated_at: <datetime>}`
- `users`, `user_sessions`, `customers`, `notes`, `messages`

## Pending Items
- P2: IMAP IDLE (push-based) for near-realtime email sync (~1-5s latency instead of 60s polling). No Google config changes needed — purely app-side.
- P2: End-to-end Atlas import test with real credentials
- P3: Remaining N+1 query patterns (non-critical)
- P3: Redis caching for analytics at higher scale
- P3: Break down server.py (10K+ lines) into route modules
