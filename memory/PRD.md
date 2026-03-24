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

### Session: Mar 2026 (Current)
- **KB Reimport Script Fixed**: `created_at`, `updated_at`, `description` metadata
- **KB Auto-Seed on Startup**: `seed_kb_articles()` — idempotent, fetches from help.emergent.sh
- **Deployment Fix**: Cleaned corrupted `.gitignore`, added `yarn.lock` to git
- **KB Editor Visual Callout Blocks**: 6 types matching docs page design (Info, Check, Note, Tip, Warning, Danger)
- **Callout Design Fix**: Translucent overlays, full border, title text, matching DocContent.jsx exactly, fixed 20px margin
- **KB Editor Table Support** (New):
  - TipTap table extensions (Table, TableRow, TableCell, TableHeader)
  - Table insertion via Insert menu and Slash commands
  - Row context menu with green grip handle (Insert before/after, Move up/down, Copy row, Delete row)
  - Custom table CSS (dark theme, green selection highlight, proper borders)
- **Docs Page Table Fix**:
  - Fixed `display: block` → `display: table` in PublicDocs.css
  - Responsive tables with `overflow-x-auto` wrapper and `min-w-[400px]`
  - Proper `border-collapse` and `break-words` for cell content

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

### P1 — Production Readiness
- Configure Atlas webhooks in production
- Cleanup `atlas_backfill_state` collection

### P2 — Future
- Re-enable IMAP polling (optional)
- Real-time agent notifications
- Auto-close stale tickets job
