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

- **Backend Audit Review** (P1):
  - All 3 reported issues verified as already resolved

### Session: Mar 24, 2026 (KB Editor Redesign)
- **Sidebar Redesign**:
  - Removed likes/dislikes metrics and page icons from sidebar
  - Settings gear icon appears on hover over any page (CSS group-hover)
  - "+" icon appears on hover over categories and subcategories to create pages underneath
  - Chevron click only toggles expand/collapse (not entire row)
  - Main "+" in Navigation header opens settings for creating new categories
  - Header label changed from "Articles" to "Navigation"

- **PageSettingsSlider** (new component):
  - Slide-in panel from right with backdrop
  - Fields: Title, Slug, Description, Sidebar title, Keywords (add/remove), Tags (add/remove), Publishing toggle
  - Delete button with confirmation overlay modal
  - Close button and Escape key to dismiss

- **Editor Area Simplified**:
  - Removed Document section (meta fields) and Publishing section from main editor
  - Only inline title input and content editor remain
  - "Draft" tag shown in navbar when page is unpublished

- **Backend Model Extension**:
  - Added `sidebar_title`, `keywords`, `tags` fields to ArticleCreate and ArticleUpdate models
  - All new fields persist correctly via API

- **Testing**: 100% pass (17/17 frontend, 11/11 backend)

### Session: Mar 24, 2026 (KB Editor Fixes)
- **Slider repositioned**: Now appears next to left sidebar (left:256px) with left-side slide-in animation, matching reference design
- **Draft tag moved**: From navbar to sidebar page item (right-aligned). Hides on hover, replaced by settings gear (CSS group-hover)
- **Draft persistence fixed**: Slider auto-saves on close. Fixed useEffect dependency that was overwriting unsaved form changes on article list refresh
- **Draft filtering confirmed**: Backend already filters `published:True` on all public endpoints — drafts never go live
- **Testing**: 100% pass (10/10 frontend, 7/7 backend)

### Session: Mar 24, 2026 (KB Editor Bug Fixes & Slider Refinement)
- **Save new page fix**: useEffect was overwriting pre-filled form state (nav_group_key/section_key) on /new route. Fixed via `pendingNewForm` ref that handlers set before navigation.
- **Sidebar reflection fix**: New pages now appear under correct category/section after save.
- **Slider positioning**: Moved to appear behind sidebar (z-20 < sidebar z-30), starts below header (top:56px), min-width 400px, smooth CSS transition-transform.
- **Overlay fix**: Backdrop only covers main content area (left:256px, top:56px), sidebar remains unaffected.
- **Draft tag restyled**: Grey fill (bg-slate-500/20 text-slate-400) with proper right padding (mr-1.5).
- **Testing**: 100% pass (16/16 frontend features)

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

### Feature Ideas
- Keyboard shortcuts for editor (Alt+Up/Down for row reorder)
- Live preview split-pane while editing
- Consolidate KBArticleManager (admin) to use shared TipTap RichTextEditor
