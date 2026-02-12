# Trinity - Customer Support Ticketing System

## Original Problem Statement
Build a web-based customer support ticketing system ("Trinity") with ticket management, canned responses, data import, email ingestion, and advanced filtering.

## Tech Stack
- **Frontend**: React 19, React Router v7, Shadcn UI, Socket.IO client
- **Backend**: Python, FastAPI, pymongo
- **Database**: MongoDB
- **Email**: IMAP (Gmail App Password), UID-based tracking, IMAP IDLE push
- **Real-time**: Socket.IO (WebSocket + polling fallback)

## Architecture (Post-Refactoring)
```
backend/
  server.py            ~6,774 lines  (remaining routes + startup/shutdown + background tasks)
  database.py          ~136 lines    (DB connection, all collections, constants)
  models/schemas.py    ~544 lines    (all Pydantic request/response models)
  dependencies.py      ~144 lines    (auth: get_current_user, verify_api_key, require_role)
  utils.py             ~361 lines    (serialize_doc, log_ticket_change, deliver_webhook, etc.)
  routes/
    filters.py         ~398 lines    (filter engine + inbox CRUD/sharing)
    webhooks.py        ~325 lines    (webhooks API + trigger-auto-close)
    customers.py       ~426 lines    (customer CRUD)
    csat.py            ~545 lines    (CSAT system)
    canned_responses.py ~202 lines   (canned responses CRUD)
  realtime.py                        (Socket.IO + presence)
  search.py                          (search engine)
  imap_sync.py                       (IMAP IDLE + UID sync)
  adapters/                          (MongoDB adapters for distributed lock, pubsub)
```

## What's Been Implemented
- Full ticket CRUD, Kanban board, canned responses, data import
- Email ingestion via IMAP (UID-based, IMAP IDLE push)
- Team management, routing rules, SLA escalation
- Analytics via MongoDB aggregation pipelines
- Real-time ticket updates via Socket.IO
- Advanced filtering with AND/OR logic, nested groups
- Custom inboxes with sharing (decoupled copies)
- ShareInboxModal (user picker) and EditInboxModal (rename/color)
- 10+ MongoDB indexes for scalable filtering (100K+ tickets)
- Backend refactoring: 10,708 → 6,774 lines (-37%)
  - Extracted: database.py, models/, dependencies.py, utils.py
  - Extracted routes: filters, webhooks, customers, csat, canned_responses
- WebSocket transport order optimized (['websocket', 'polling'])

## Pending Items
- P2: Continue extracting remaining routes from server.py (tickets, email, admin, teams ~4K lines)
- P2: Frontend component organization (51 files flat in components/)
- P2: End-to-end Atlas import test with real credentials
- P3: Redis caching for analytics at higher scale
