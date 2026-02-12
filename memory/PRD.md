# Trinity / TickFlow - Product Requirements Document

## Original Problem Statement
Enterprise ticket management platform with real-time collaboration. Features include ticket CRUD, team management, shift scheduling, SLA policies, email integration (IMAP + Gmail), analytics, and custom inbox filtering.

## Architecture

### Backend (FastAPI + MongoDB)
```
/app/backend/
├── server.py              # 473 lines - App init, middleware, startup/shutdown, router includes
├── database.py            # DB connection + collection references
├── dependencies.py        # Auth dependencies (get_current_user, require_admin, etc.)
├── utils.py               # Shared utilities (serialize_doc, log_ticket_change, etc.)
├── ticket_helpers.py      # Routing rules, assignment, escalation helpers
├── rate_limiter.py        # Shared rate limiter instance
├── models/
│   └── schemas.py         # All Pydantic models
├── routes/
│   ├── auth.py            # Auth (session, me, logout, API keys)
│   ├── users.py           # User profile, preferences, listing, role update
│   ├── teams.py           # Team CRUD + members
│   ├── shifts.py          # Shift CRUD + user-shift assignment + on-shift queries
│   ├── tickets.py         # Core ticket CRUD + notes + activity + tags + metadata
│   ├── ticket_ops.py      # Bulk ops + merge/unmerge/link/unlink/split
│   ├── email.py           # IMAP sync + Gmail integration + file upload
│   ├── admin.py           # Custom fields + settings + routing rules + SLA admin
│   ├── sla.py             # SLA policies + per-ticket SLA status
│   ├── analytics.py       # Summary + overview + agent metrics + export
│   ├── search_presence.py # Search + suggestions + presence + notifications
│   ├── leaves.py          # Leave management CRUD
│   ├── feature_requests.py # Feature requests CRUD + ticket linking
│   ├── exports.py         # Data export system (tickets, users, teams)
│   ├── filters.py         # Advanced ticket filtering + custom inboxes
│   ├── webhooks.py        # Webhook management
│   ├── customers.py       # Customer CRUD + B2B prospects
│   ├── canned_responses.py # Canned response templates
│   └── csat.py            # CSAT surveys + analytics
├── realtime.py            # Socket.IO events + broadcast functions
├── search.py              # Search engine
├── leave_management.py    # Leave business logic
├── email_utils.py         # Email parsing utilities
├── imap_sync.py           # IMAP IDLE watcher
└── adapters/              # Distributed adapters (presence, lock, pubsub)
```

### Frontend (React + Material-UI)
```
/app/frontend/src/
├── components/            # 50+ components (flat structure - needs refactoring)
│   ├── Sidebar.js
│   ├── FilterBuilder.js
│   ├── modals/
│   │   ├── EditInboxModal.js
│   │   └── ShareInboxModal.js
│   └── ...
├── context/
│   └── SocketContext.js
├── pages/
│   └── TicketsListView.js
└── App.js
```

## Completed Work

### P0 - Bug Fixes & Scalability
- [x] Fixed user dropdown in filters not populating correctly
- [x] Added MongoDB indexes for filterable fields

### P1 - Custom Inbox Management
- [x] Inbox sharing with specific users (ShareInboxModal)
- [x] Inbox renaming (EditInboxModal)
- [x] Sidebar integration for inbox actions

### P2 - Code Refactoring
- [x] **Backend Refactoring COMPLETE** - server.py: 10,708 → 473 lines
  - 19 route modules extracted to backend/routes/
  - Supporting modules: database.py, dependencies.py, utils.py, ticket_helpers.py, rate_limiter.py
  - 137 total API routes verified working
  - 100% test pass rate (50/50 tests)
- [x] WebSocket transport optimization (prioritize websocket over polling)

## Remaining Tasks

### P1 - Frontend Component Refactoring
- [ ] Organize frontend/src/components/ into logical subdirectories (layout/, tickets/, inbox/, modals/, common/)
- [ ] Update all import paths across the frontend

### P2 - Deferred
- [ ] Atlas Search Import

## Key Technical Details
- **Auth**: Google OAuth via Emergent Auth, Cookie-based session tokens
- **Real-time**: Socket.IO for WebSocket communication
- **Database**: MongoDB (via pymongo sync + motor async)
- **Entry point**: `uvicorn server:app` (unchanged)
