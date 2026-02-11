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
- Custom inboxes (saved filter configurations) with sharing

## Tech Stack
- **Frontend**: React 19, React Router v7, Shadcn UI
- **Backend**: Python, FastAPI
- **Database**: MongoDB (sync pymongo driver)
- **Email**: IMAP (Gmail App Password), UID-based tracking, IMAP IDLE push
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
- 8 Scalability Fixes: analytics aggregation, auto-close batch ops, streaming export, notes pagination, N+1 fix, compound indexes
- IMAP Email Sync (UID-based + IDLE push) - Feb 2026
- Real-time ticket push - Feb 2026
- Advanced Filters + Custom Inboxes - Feb 2026
- Bug Fix: Filter UI crash (users.map not a function) - Feb 2026
- Scalable Filtering Indexes (7 ticket + 3 inbox indexes) - Feb 2026
- Custom Inbox Sharing UI (ShareInboxModal with user picker) - Feb 2026
- Custom Inbox Management (EditInboxModal for rename/color, 3-dot menu) - Feb 2026

## Key API Endpoints
- `GET /api/tickets?page=1&limit=50&status=todo` - Paginated tickets
- `GET /api/filter/fields` - Available filter fields
- `POST /api/filter/tickets` - Apply filter tree
- `GET /api/inboxes` - List custom inboxes
- `POST /api/inboxes` - Create custom inbox
- `PUT /api/inboxes/{inbox_id}` - Update custom inbox
- `DELETE /api/inboxes/{inbox_id}` - Delete custom inbox
- `POST /api/inboxes/{inbox_id}/share` - Share inbox (decoupled copy)
- `GET /api/inboxes/{inbox_id}/tickets` - Inbox filtered tickets

## Key DB Collections
- `tickets` - Ticket data with email metadata
- `email_replies` - Incoming/outgoing email replies
- `imap_sync_state` - IMAP UID tracking
- `users`, `user_sessions`, `customers`, `notes`, `messages`
- `custom_inboxes` - Saved filter configurations (indexed: inbox_id, owner_id, shared_with)

## Pending Items
- P2: End-to-end Atlas import test with real credentials
- P2: Refactor large components (TicketsListView, MainLayout, server.py)
- P2: WebSocket upgrade investigation (polling fallback)
- P3: Redis caching for analytics at higher scale
- P3: Break down server.py into route modules
