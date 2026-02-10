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
- **Frontend**: React, Shadcn UI
- **Backend**: Python, FastAPI
- **Database**: MongoDB (Motor async driver)

## What's Been Implemented
- Ticket Drawer UI Enhancement (priority + escalation badges in left panel)
- In-App Canned Response Creation (create directly from picker modal)
- Atlas Import backend logic (`POST /api/import/atlas`)
- Database indexes for Atlas deduplication (tickets, messages, customers)
- Deployment blocker fixes (hardcoded DB name -> env variable)

## Architecture
```
/app
├── backend/
│   ├── atlas_import.py          # Atlas API data fetching & transformation
│   ├── server.py                # FastAPI main server
│   └── .env                     # MONGO_URL, DB_NAME, etc.
├── frontend/
│   └── src/components/
│       ├── CannedResponsePicker.js
│       └── TicketDrawer.js
```

## Key API Endpoints
- `POST /api/import/atlas` - Import data from Atlas (requires api_key + domain)
- `GET /api/health` - Health check

## Pending Items
- P1: End-to-end Atlas import test with real credentials
- P2: N+1 query optimization in agent assignment logic

## Changelog
- 2026-02-10: Fixed 3 deployment blockers (hardcoded DB name in 3 locations)
- 2026-02-10: Added missing deduplication indexes for messages and customers collections
