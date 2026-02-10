# Trinity - Customer Support Ticketing System

## Original Problem Statement
Build a web-based customer support ticketing system ("Trinity") with ticket management, canned responses, and data import capabilities from external tools.

## Core Features
- Ticket dashboard with priority/escalation badges
- Detailed ticket view in drawer with metadata
- Canned response system with in-app creation
- Data import from external tools (Zendesk, Atlas)
- Gmail integration for email-based tickets
- Team management, routing rules, SLA escalation

## Tech Stack
- **Frontend**: React 19, React Router v7, Shadcn UI
- **Backend**: Python, FastAPI
- **Database**: MongoDB (Motor async driver)

## What's Been Implemented
- Ticket Drawer UI Enhancement (priority + escalation badges in left panel)
- In-App Canned Response Creation (create directly from picker modal)
- Atlas Import backend logic (`POST /api/import/atlas`)
- Database indexes for Atlas deduplication (tickets, messages, customers)
- Deployment blocker fixes (hardcoded DB name → env variable)
- Production navigation bug fix (React.lazy + window.history.pushState desync)
- Post-login auth cache fix (module-level user cache in ProtectedRoute)

## Architecture
```
/app
├── backend/
│   ├── atlas_import.py          # Atlas API data fetching & transformation
│   ├── server.py                # FastAPI main server
│   ├── realtime.py              # Socket.IO realtime module
│   └── .env                     # MONGO_URL, DB_NAME, etc.
├── frontend/
│   └── src/
│       ├── App.js               # Router + AppWithRealtime wrapper
│       ├── components/
│       │   ├── ProtectedRoute.js  # Auth guard with module-level cache
│       │   ├── AuthCallback.js    # Google OAuth callback handler
│       │   ├── MainLayout.js      # Main layout with view switching
│       │   ├── DashboardContainer.js
│       │   ├── Sidebar.js
│       │   ├── CannedResponsePicker.js
│       │   ├── SettingsPage.js
│       │   └── TicketDrawer.js
│       └── contexts/
│           └── RealtimeContext.js  # Socket.IO context
```

## Key Bug Fixes
- 2026-02-10: Fixed post-login auth (module-level cache replaces location.state)
- 2026-02-10: Fixed production navigation (React.lazy + pushState desync)
- 2026-02-10: Fixed 3 deployment blockers (hardcoded DB name)
- 2026-02-10: Added missing deduplication indexes

## Pending Items
- P1: End-to-end Atlas import test with real credentials
- P2: N+1 query optimization in agent assignment logic
- Verify production navigation after redeployment
