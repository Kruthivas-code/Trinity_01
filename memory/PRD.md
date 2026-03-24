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

### Session: Mar 2026 (Current)
- **KB Reimport Script Fixed** (`backend/scripts/reimport_kb.py`):
  - Now includes `created_at` and `updated_at` from source API
  - Auto-generates `description` from article content
- **KB Auto-Seed on Startup** (`routes/kb.py` → `seed_kb_articles()`):
  - Runs on server boot if `kb_articles` collection is empty
  - Idempotent — skips if articles already exist
- **Deployment Fix — Frontend Build**:
  - Cleaned up corrupted root `.gitignore`
  - Added `frontend/yarn.lock` to git tracking
- **KB Editor Visual Callout Blocks** (New Feature):
  - Created `CalloutBlock.jsx` TipTap extension with 6 types:
    - Info (gray), Check (green), Note (blue), Tip (teal), Warning (amber), Danger (red)
  - Each type has distinct bg color, border, icon (from lucide-react)
  - Callouts render as visual editable blocks in the editor (not raw MDX code)
  - Insert menu and Slash command menu updated with all 6 types
  - MDX `<Callout type="..." title="...">` syntax parsed into visual blocks
  - Visual blocks serialize back to MDX on save
  - Testing: 8/8 features passed (tested via testing_agent_v3_fork)

## Architecture
- **Backend**: FastAPI (Python), MongoDB
- **Frontend**: React with Craco + Shadcn/UI + TipTap editor
- **Sync Engine**: 5-layer Atlas sync
- **Auth**: Emergent-managed Google Auth
- **Email**: Amazon SES (outbound), Gmail IMAP (disabled)
- **AI**: Gemini for ticket summarization

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
