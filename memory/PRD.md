# Trinity Support Platform — PRD

## Original Problem Statement
A full-stack application (React, FastAPI, MongoDB) for customer support ticket management, integrated with Atlas as the primary data source. The platform includes a knowledge base, customer portal, team management, and real-time sync with Atlas.

## Core Requirements
- Robust sync engine ensuring 100% data consistency with Atlas (Completed — 5-layer architecture)
- Changes in the app pushed back to Atlas (Completed)
- Self-service health dashboard in admin panel (Completed)
- Cleanup of legacy/dead code (Completed)
- Production-ready, stable, and secure application (Completed)
- KB editor provides a rich, visual editing experience (Completed)

## What's Been Implemented

### Session: Feb 2026
- Critical "Match 1" logic flaw fixed in atlas_sync.py
- Deployment blockers resolved (sparse index, IMAP backoff, .gitignore)
- Full-stack audit fixes (4 backend, 5 frontend)
- IMAP poller disabled — Atlas-only ingestion mode
- Data reset features removed (production deploys to fresh DB)

### Session: Mar 2026 (Early)
- KB Reimport Script Fixed: `created_at`, `updated_at`, `description` metadata
- KB Auto-Seed on Startup: `seed_kb_articles()` — idempotent, fetches from help.emergent.sh
- Deployment Fix: Cleaned corrupted `.gitignore`, added `yarn.lock` to git
- KB Editor Visual Callout Blocks: 6 types matching docs page design
- Callout Design Fix: Translucent overlays, full border, title text, fixed 20px margin
- KB Editor Table Support: TipTap table extensions, insertion via Insert menu and Slash commands
- Row context menu with green grip handle (Insert before/after, Move up/down, Copy row, Delete row)
- Custom table CSS (dark theme, green selection highlight, proper borders)
- Docs Page Table Fix: `display: table`, responsive with `overflow-x-auto` wrapper

### Session: Mar 24, 2026 (Current)
- **KB Editor Table Drag-and-Drop Row Reordering** (P0 — Completed):
  - Refactored `TableMenu.jsx` to show grip handles on ALL data rows (not just active)
  - Implemented mouse-based drag with 5px threshold (click vs. drag distinction)
  - Visual feedback: drag-source-highlight overlay + emerald drop indicator line with circle endpoints
  - ProseMirror transaction-based row reordering using `arrayMove` semantic
  - Auto-focus moved row after reorder completes
  - Context menu preserved: click grip → menu, drag grip → reorder
  - 100% test pass rate (13/13 features verified by testing agent)
- **Backend Audit Review** (P1 — Completed):
  - Verified search_tickets already has proper text indexes in search.py
  - Verified no hardcoded Slack webhook in ticket_sweep.py
  - Verified all /admin/* endpoints use require_admin dependency

## Architecture
- **Backend**: FastAPI (Python), MongoDB
- **Frontend**: React with Craco + Shadcn/UI + TipTap editor
- **Sync Engine**: 5-layer Atlas sync
- **Auth**: Emergent-managed Google Auth
- **Email**: Amazon SES (outbound), Gmail IMAP (disabled)
- **AI**: Gemini for ticket summarization

## Pending Tasks

### P2 — Production Readiness
- Configure full Atlas webhooks in production
- Cleanup `atlas_backfill_state` collection

### P2 — Future
- Re-enable IMAP polling (optional)
- Real-time agent notifications
- Auto-close stale tickets job
