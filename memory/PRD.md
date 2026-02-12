# Trinity / TickFlow - Product Requirements Document

## Original Problem Statement
Enterprise ticket management platform with real-time collaboration. Features include ticket CRUD, team management, shift scheduling, SLA policies, email integration (IMAP + Gmail), analytics, and custom inbox filtering.

## Architecture

### Backend (FastAPI + MongoDB)
```
/app/backend/
├── server.py              # App init, middleware, startup/shutdown, router includes
├── database.py            # DB connection + collection references
├── dependencies.py        # Auth dependencies (get_current_user, require_admin, etc.)
├── utils.py               # Shared utilities (serialize_doc, log_ticket_change, etc.)
├── ticket_helpers.py      # Routing rules, assignment, escalation helpers
├── rate_limiter.py        # Shared rate limiter instance
├── models/
│   └── schemas.py         # All Pydantic models with example payloads
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

### Frontend (React + Tailwind + Shadcn/UI)
```
/app/frontend/src/
├── components/
│   ├── layout/            # MainLayout, Sidebar, GlobalHeader, Header, PageLayout
│   ├── auth/              # LoginPage, AuthCallback, ProtectedRoute
│   ├── tickets/           # TicketDrawer, TicketCard, KanbanBoard, FilterBuilder, etc.
│   ├── inbox/             # CustomInboxPage, SaveInboxModal, EditInboxModal, ShareInboxModal
│   ├── admin/             # AdminPage, SettingsPage, RoutingRulesTab, SLA tabs
│   ├── pages/             # Dashboard, Analytics, CSAT, Customers, Teams, etc.
│   ├── common/            # ActivityTimeline, CommandPalette, MentionInput, etc.
│   └── ui/                # Shadcn UI components
├── contexts/
│   ├── RealtimeContext.js
│   └── ThemeContext.js
├── hooks/
│   └── use-toast.js
├── App.js
└── index.js
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
  - 175 total API routes verified working
- [x] WebSocket transport optimization (prioritize websocket over polling)

### P2 - API Documentation (Feb 12, 2026)
- [x] **API Documentation COMPLETE**
  - Configured FastAPI docs at /api/docs (Swagger UI) and /api/redoc (ReDoc)
  - Added 20 tag groups with descriptions for organized navigation
  - Added docstrings to all 175 endpoints across 19 route files
  - Added pre-filled sample payloads to 34 Pydantic models

### P1 - Frontend Component Refactoring (Feb 12, 2026)
- [x] **Frontend Modularization COMPLETE**
  - Organized 50+ flat components into 7 logical subdirectories
  - Updated all import paths across App.js and 20+ component files

### P0 - Comprehensive Feature Testing (Feb 12, 2026)
- [x] **10-Phase Screenshot & API Testing COMPLETE**
  - 15 bugs found and fixed across frontend and backend
  - All 12 frontend pages verified rendering correctly
  - All CRUD operations verified: Tickets, Teams, Customers, Canned Responses, Feature Requests, Leaves, Custom Fields, Routing Rules
  - Full ticket lifecycle E2E tested: Create → Assign → Update → Resolve
  - 37/37 backend tests passed, 100% frontend success rate
  - Bug fixes:
    - 9 frontend files: API response `{items:[]}` handling (was crashing with `.filter()`)
    - Leave creation: wrong args passed to `LeaveManager.create_leave()`
    - Feature requests: status/type field mismatches between frontend/backend
    - Search endpoint: missing `db` argument + wrong method name
    - Feature requests MongoDB index: legacy `feature_id` conflicting with `feature_request_id`
    - Settings export: didn't handle `{items:[]}` response format

## Remaining Tasks

### P2 - Deferred
- [ ] Atlas Search Import
- [ ] CSAT survey send (requires Gmail integration)

## Key Technical Details
- **Auth**: Google OAuth via Emergent Auth, Cookie-based session tokens
- **Real-time**: Socket.IO for WebSocket communication
- **Database**: MongoDB (via pymongo sync + motor async)
- **Entry point**: `uvicorn server:app` (unchanged)
- **API Docs**: /api/docs (Swagger), /api/redoc (ReDoc), /api/openapi.json (schema)
- **Test Plan**: /app/TEST_PLAN_PHASES.md (10 phases, all complete)
- **Test Reports**: /app/test_reports/iteration_19.json (Phase 1-6), iteration_20.json (Phase 7-10)
