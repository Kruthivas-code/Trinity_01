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
- **Email Outbound**: Amazon SES SMTP
- **Email Inbound**: Gmail IMAP polling
- **Auth**: Emergent Google OAuth (dashboard), JWT sessions (portal)

## Credentials
- **Dashboard**: Google OAuth (Emergent Auth)
- **Portal**: Self-registration
- **Atlas API Key**: In `backend/.env` as `ATLAS_API_KEY`

---

## Architecture

### Backend Services (`/app/backend/services/`)
| File | Purpose |
|------|---------|
| `atlas_backfill.py` | Resumable Atlas historical import + enrichment + agent import |
| `atlas_sync.py` | Atlas ongoing real-time sync (to be enhanced) |
| `email_poller.py` | IMAP polling, ticket matching/creation |
| `email_service.py` | SES SMTP sending, threading |

### Key API Endpoints (`/app/backend/routes/atlas.py`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/admin/atlas/backfill/status` | GET | Backfill progress |
| `/api/admin/atlas/backfill/start` | POST | Start/resume backfill |
| `/api/admin/atlas/backfill/stop` | POST | Pause backfill |
| `/api/admin/atlas/backfill/reset` | POST | Reset to start fresh |
| `/api/admin/atlas/backfill/test` | POST | Test batch (sync) |
| `/api/admin/atlas/backfill/enrich` | POST | Start enrichment pass |
| `/api/admin/atlas/backfill/enrich/status` | GET | Enrichment progress |
| `/api/admin/atlas/backfill/enrich/stop` | POST | Stop enrichment |
| `/api/admin/atlas/agents/import` | POST | Import Atlas agents |

### Key MongoDB Collections
| Collection | Purpose |
|-----------|---------|
| `tickets` | All tickets (portal, email, manual, atlas) |
| `messages` | Ticket messages + attachments |
| `atlas_backfill_state` | Backfill + enrichment progress (resumable) |
| `customers` | CRM customer records (enriched with Atlas custom fields) |
| `users` | Agents (163 from Atlas + existing, merge-safe by email) |

---

## Completed Work

### Atlas Full Metadata Import (Mar 2026)
**Conversation metadata (all fields):**
- Core: status, priority, subject, tags, custom_fields
- Channel: started_channel, started_sub_channel
- Timestamps: created_at, started_at, closed_at, assigned_at, escalated_at, snoozed_until
- Actors: closed_by, assigned_by, updated_by
- CSAT: atlas_csat_score, atlas_csat_comment
- Stats: first_response_time, avg_response_time, total_resolution_time
- Environment: browser, operating_system
- Atlas AI: atlas_assigned_to_zeus

**Message attachments:** name, url (files.atlas.so), size

**Customer enrichment:** atlas_custom_fields, phone, atlas_external_user_id, atlas_company_id

**Agent import:** 163 Atlas agents → Trinity users. Merge-safe via email upsert.

**Resumable infrastructure:**
- Backfill state persisted in MongoDB after every batch
- Auto-resume on server startup (handles pod sleep/kill)
- Enrichment runs in parallel as background thread

### Previous Work
- KB Editor (Visual Columns, Cards, Accordion, Steps, Icon Picker)
- Backend-driven Portal Categories
- Full Gmail Thread Capture with correct timestamps
- Email System (SES outbound, IMAP inbound, threading)

---

## In Progress
- **Backfill**: ~71.5% complete (~47,900/67,000). Auto-resumes across sessions.
- **Enrichment**: Patching ~45K previously-imported tickets with new metadata fields.

## Pending / Backlog

### P0: Atlas Real-Time Sync (Shadow Mode)
- Enhance `atlas_sync.py` for full conversation sync
- Background worker polling every 60s
- Admin controls and monitoring

### P1: Data Validation (Post-Backfill)
- Count verification, message integrity, timestamp sanity

### P2: Future
- Blob storage for attachment migration (full Atlas cutover)
- Real-time notifications for agents
- Auto-closing stale tickets
- Tag definitions & SLA rule import
- Email analytics dashboard
