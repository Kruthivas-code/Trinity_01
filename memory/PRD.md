# Trinity Support Platform — PRD

## Original Problem Statement
A full-stack application (React, FastAPI, MongoDB) for customer support ticket management, integrated with Atlas as the primary data source. The platform includes a knowledge base, customer portal, team management, and real-time sync with Atlas.

## Core Requirements
- Robust sync engine ensuring 100% data consistency with Atlas (Completed)
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

### Session: Mar 2026 (Early)
- KB Reimport Script Fixed & Auto-Seed on Startup
- Deployment Fix: Cleaned corrupted `.gitignore`, added `yarn.lock` to git
- KB Editor Visual Callout Blocks (6 types matching docs page design)
- KB Editor Table Support (insertion, context menu, custom CSS)
- Docs Page Table Fix (responsive with overflow-x-auto wrapper)

### Session: Mar 24, 2026
- **Table Drag-and-Drop Row Reordering** (P0):
  - Grip handles on ALL data rows, click vs drag distinction
  - Visual drop indicators and source highlight
  - ProseMirror transaction-based reorder
  - 100% test pass (13/13 features)

- **Theme Adaptation & Cross-Page Consistency**:
  - Editor table CSS: Added `.dark` selector variants for light/dark mode
  - TableMenu: Theme-aware context menu, grip handles, drop indicators
  - Added CHECK callout type to DocContent CALLOUT_CONFIG
  - Fixed slash command hint styling for both themes
  - Made context menu position responsive for narrow screens
  - Verified: Public docs callouts (16 found), tables (7 found), theme toggle, mobile responsive

- **Backend Audit Review** (P1):
  - All 3 reported issues verified as already resolved

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
- Real-time agent notifications
- Auto-close stale tickets job
