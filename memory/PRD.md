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
- Advanced filtering with AND/OR logic, nested groups
- Custom inboxes (saved filter configurations)

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
- **IMAP Email Sync (UID-based + IDLE push)** — Feb 2026
- **Real-time ticket push** — Feb 2026
- **Advanced Filters + Custom Inboxes** — Feb 2026:
  - Server-side filter engine: `filter_tree_to_mongo()` translates recursive AND/OR filter trees to MongoDB `$and`/`$or` queries
  - 15+ operators: is, is_not, contains, is_one_of, is_none, before, after, between, etc.
  - Supports nested groups (brackets) for full set theory (unions/intersections)
  - Filters on ALL ticket metadata: status, priority, source, assignee, dates, custom fields
  - Custom Inboxes: save filter configs, share with team (decoupled copies), 3-dot menu (edit/share/delete)
  - Sidebar integration: custom inboxes appear under Tickets section with colored dots
  - New endpoints: `POST /api/filter/tickets`, `GET /api/filter/fields`, CRUD `/api/inboxes`
- **Bug Fix: Filter UI crash** — Feb 2026:
  - Fixed `users.map is not a function` in FilterBuilder.js and TicketsListView.js
  - Root cause: `/api/users` returns paginated `{items: [], total, ...}` but frontend set users state to full response
  - Fix: Extract `.items` array from response before setting state
  - Added guard for empty field conditions in `filter_tree_to_mongo()`
- **Scalable Filtering Indexes** — Feb 2026:
  - Added 7 new ticket indexes: source, tags, priority+date, source+date, status+priority+date, assignee+status+date, email_sender_name
  - Added 3 custom_inboxes indexes: inbox_id (unique), owner_id, shared_with
  - Isolated index creation in separate try blocks to prevent cascading failures

## Key API Endpoints
- `GET /api/tickets?page=1&limit=50&status=todo&status=in_progress` — Paginated, multi-status
- `GET /api/analytics/summary` — Single $facet aggregation
- `GET /api/analytics/overview?days=30` — Full analytics via aggregation pipeline
- `GET /api/tickets/{id}/notes?page=1&limit=100` — Paginated notes
- `GET /api/export?format=json|csv` — Streaming export
- `POST /api/email/sync?fetch_all=false` — Manual IMAP sync (UID-based)
- `GET /api/email/status` — IMAP connection + sync state status
- `GET /api/filter/fields` — Available filter fields
- `POST /api/filter/tickets` — Apply filter tree to get matching tickets
- `GET /api/inboxes` — List custom inboxes
- `POST /api/inboxes` — Create custom inbox
- `PUT /api/inboxes/{inbox_id}` — Update custom inbox
- `DELETE /api/inboxes/{inbox_id}` — Delete custom inbox
- `POST /api/inboxes/{inbox_id}/share` — Share inbox (decoupled copy)
- `GET /api/inboxes/{inbox_id}/tickets` — Get tickets for a saved inbox

## Key DB Collections
- `tickets` — Ticket data with email metadata
- `email_replies` — Incoming/outgoing email replies
- `imap_sync_state` — IMAP UID tracking
- `users`, `user_sessions`, `customers`, `notes`, `messages`
- `custom_inboxes` — Saved filter configurations

## Pending Items
- P1: Custom Inbox Sharing UI (share modal with user picker)
- P1: Custom Inbox Edit/Delete (wiring 3-dot menu actions fully)
- P2: End-to-end Atlas import test with real credentials
- P2: Refactor large components (TicketsListView, MainLayout, server.py)
- P2: WebSocket upgrade investigation (polling fallback)
- P3: Redis caching for analytics at higher scale
