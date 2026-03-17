# Trinity Support Platform — PRD

## Original Problem Statement
A full-stack application (React, FastAPI, MongoDB) for customer support ticket management, integrated with Atlas as the primary data source. The platform includes a knowledge base, customer portal, team management, and real-time sync with Atlas.

## Core Requirements
- Robust sync engine ensuring 100% data consistency with Atlas (Completed — 5-layer architecture)
- Changes in the app pushed back to Atlas (Completed)
- Self-service health dashboard in admin panel (Completed)
- Cleanup of legacy/dead code (In Progress)
- Production-ready, stable, and secure application (In Progress)

## What's Been Implemented

### Session: Feb 2026 (Previous)
- Critical "Match 1" logic flaw fixed in atlas_sync.py
- Deployment blockers resolved (sparse index, IMAP backoff, .gitignore)
- Full-stack audit fixes (4 backend, 5 frontend)
- IMAP poller disabled — Atlas-only ingestion mode
- Data reset features removed (production deploys to fresh DB)
- Authenticated UI testing via session cookie injection

### Session: Feb 2026 (Current)
- **KB Reimport Script Fixed** (`backend/scripts/reimport_kb.py`):
  - Now includes `created_at` and `updated_at` from source API
  - Auto-generates `description` from article content
  - Preserves `icon` from both navigation and document sources
- **KB Auto-Seed on Startup** (`routes/kb.py` → `seed_kb_articles()`):
  - Runs on server boot if `kb_articles` collection is empty
  - Fetches from `help.emergent.sh/api/public/default-project`
  - Idempotent — skips if articles already exist
  - Hooked into `server.py` startup alongside `seed_default_categories()`

## Architecture
- **Backend**: FastAPI (Python), MongoDB
- **Frontend**: React with Shadcn/UI
- **Sync Engine**: 5-layer Atlas sync (Webhooks → Poller → Hot/Cold Crawl → Push-back → Sweep)
- **Auth**: Emergent-managed Google Auth
- **Email**: Amazon SES (outbound), Gmail IMAP (disabled)
- **AI**: Gemini for ticket summarization

## Key Collections
- `kb_articles` — Help docs (seeded from help.emergent.sh)
- `kb_navigation` — Navigation structure
- `portal_categories` — Support portal categories (seeded on startup)
- `tickets` — Support tickets (synced from Atlas)
- `messages` — Ticket messages/conversations

## Pending Tasks

### P0 — Backend Audit Remaining Issues
- Inefficient `search_tickets` in tickets.py (add text indexes)
- Hardcoded Slack webhook in ticket_sweep.py (move to env var)
- Missing auth on some admin endpoints in admin.py
- Review tickets.py and users.py for other unaddressed items

### P1 — Production Readiness
- Configure Atlas webhooks in production
- Cleanup `atlas_backfill_state` collection

### P2 — Future
- Re-enable IMAP polling (optional)
- Real-time agent notifications
- Auto-close stale tickets job
