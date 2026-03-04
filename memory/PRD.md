# Trinity — Product Requirements Document

## Overview
Trinity is a comprehensive customer help suite with three public surfaces and one internal tool:

1. **Knowledge Base** (`/`, `/docs/:slug`) — Public documentation site with search, light/dark theme
2. **Help Portal** (`/portal`) — Customer-facing ticket submission and tracking
3. **Agent Dashboard** (`/dashboard`, `/all-tickets`) — Internal tool for agents to manage tickets, KB content, teams, analytics
4. **CSAT** (`/csat/:token`) — Customer satisfaction survey page

## Tech Stack
- **Frontend**: React 18 + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI (Python) + Socket.IO (real-time)
- **Database**: MongoDB (pymongo)
- **AI**: Gemini via `emergentintegrations` for ticket summarization
- **Email Outbound**: Amazon SES SMTP (`smtplib`)
- **Email Inbound**: Gmail IMAP (`imaplib`) polling `support@emergent.sh`
- **Auth**: Emergent Google OAuth (dashboard), JWT-like sessions (portal)
- **Brand Color**: `#00A1B2`

## Credentials
- **Dashboard**: Google OAuth (Emergent Auth)
- **Portal**: Self-registration. Test account: `kruthivas@emergent.sh` / `Password123`
- **Atlas API Key**: Configured in backend `.env` as `ATLAS_API_KEY`

---

## Architecture

### Backend Route Modules (`/app/backend/routes/`)
| Module | Prefix | Purpose |
|--------|--------|---------|
| `atlas.py` | `/api/admin/atlas` | Atlas backfill control & status |
| `auth.py` | `/api/auth` | Google OAuth, sessions, API keys |
| `tickets.py` | `/api/tickets` | CRUD, notes, assignment |
| `portal.py` | `/api/portal` | Customer auth, categories |
| `kb.py` | `/api/kb` | Knowledge Base articles |
| `admin.py` | `/api/admin` | Custom fields, routing, SLA |
| `filters.py` | `/api/filter` | Advanced filtering |

### Backend Services (`/app/backend/services/`)
| File | Purpose |
|------|---------|
| `atlas_backfill.py` | **NEW** — Resumable Atlas historical data import |
| `atlas_sync.py` | Atlas ongoing sync (to be enhanced for Phase 3) |
| `email_poller.py` | IMAP polling, ticket matching/creation |
| `email_service.py` | SES SMTP sending, threading |

### Key MongoDB Collections
| Collection | Purpose |
|-----------|---------|
| `tickets` | All tickets (portal, email, manual, atlas) |
| `messages` | Ticket conversation messages |
| `atlas_backfill_state` | **NEW** — Backfill progress tracking |
| `atlas_sync_state` | Sync cursor tracking |
| `customers` | CRM customer records |

---

## Completed Work

### Atlas Backfill System (Feb 2026)
- **Resumable backfill engine** — Persists state in MongoDB after every batch of 100 conversations
- **Auto-resume on startup** — Detects incomplete backfill and resumes from last cursor
- **API endpoints**: status, start, stop, reset, test
- **Test batch passed**: 100 conversations, 657 messages, 0 errors
- **Full backfill started**: ~66,650 conversations at ~100/min rate
- **Files**: `services/atlas_backfill.py`, `routes/atlas.py`

### Previous Work (see CHANGELOG.md for full history)
- KB Editor (Visual Columns, Cards, Accordion, Steps, Icon Picker, Markdown/Visual toggle, Preview)
- Backend-driven Portal Categories
- Full Gmail Thread Capture with correct timestamps
- Email System (SES outbound, IMAP inbound, threading, rate limiting)
- UI/UX improvements (IST timezone, density, avatars, search)
- Ticket merge, search fixes
- Docs page header, social links, breadcrumbs

---

## In Progress

### P0: Atlas Historical Data Backfill
- Status: RUNNING (~1% complete, auto-resumes across pod sessions)
- ~66,650 conversations to import with all messages
- Data mapping: status, priority, tags, customer, agent, timestamps

---

## Pending / Backlog

### P0: Atlas Real-Time Sync (Shadow Mode)
- Enhance `atlas_sync.py` for full conversation sync (not just agent messages)
- Background worker polling every 60s
- Sync status/priority/assignment changes
- Admin controls and monitoring

### P1: Data Validation (Post-Backfill)
- Count verification (Atlas total vs Trinity imported)
- Message integrity checks
- Timestamp sanity
- Customer linking audit

### P2: Future Features
- Real-time notifications for agents
- Recurring job for auto-closing stale tickets
- Email analytics dashboard
- Admin UI for Atlas sync monitoring

### Refactoring
- `RichTextEditor.jsx` — Extract markdown preprocessing into dedicated hooks
