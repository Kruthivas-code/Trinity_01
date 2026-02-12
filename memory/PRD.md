# Trinity - Customer Support Ticketing System

## Original Problem Statement
Build a web-based customer support ticketing system ("Trinity") with ticket management, canned responses, and data import capabilities from external tools.

## Tech Stack
- **Frontend**: React 19, React Router v7, Shadcn UI
- **Backend**: Python, FastAPI
- **Database**: MongoDB (sync pymongo driver)
- **Email**: IMAP (Gmail App Password), UID-based tracking, IMAP IDLE push
- **Real-time**: Socket.IO (WebSocket + polling fallback)

## Architecture (Post-Refactoring)
```
backend/
  server.py           ~9,600 lines  (routes + startup/shutdown + background tasks)
  database.py         ~130 lines    (DB connection, all collections, constants)
  models/schemas.py   ~540 lines    (all Pydantic request/response models)
  dependencies.py     ~140 lines    (auth: get_current_user, verify_api_key, require_role)
  utils.py            ~36 lines     (serialize_doc utility)
  routes/
    filters.py        ~400 lines    (filter engine + inbox CRUD/sharing)
  realtime.py                       (Socket.IO + presence)
  search.py                         (search engine)
  imap_sync.py                      (IMAP IDLE + UID sync)
  adapters/                         (MongoDB adapters for distributed lock, pubsub)
```

## What's Been Implemented
- Ticket dashboard with priority/escalation badges
- Ticket CRUD, Kanban board, canned responses, data import (Zendesk, Atlas)
- Email ingestion via IMAP (Gmail App Password, UID-based, IMAP IDLE push)
- Team management, routing rules, SLA escalation
- Server-side pagination with infinite scroll
- Analytics via MongoDB aggregation pipelines
- Real-time ticket updates via Socket.IO
- Advanced filtering with AND/OR logic, nested groups (set theory)
- Custom inboxes (saved filter configs) with sharing (decoupled copies)
- ShareInboxModal (user picker) and EditInboxModal (rename/color)
- 10 MongoDB indexes for scalable filtering (100K+ tickets)
- **Backend refactoring** (Feb 2026): Extracted database.py, models/, dependencies.py, utils.py, routes/filters.py
- **WebSocket transport optimization** (Feb 2026): Changed to ['websocket', 'polling'] for faster initial connection

## Pending Items
- P2: End-to-end Atlas import test with real credentials
- P2: Continue backend route extraction (tickets, email, admin routes still in server.py)
- P2: Frontend component organization (51 files flat in components/)
- P3: Redis caching for analytics at higher scale
