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

### Session: Mar 24, 2026 (Docs & Editor Content Rendering Fixes)
- **Standalone callout tag parsing**: `<Tip>`, `<Info>`, `<Warning>`, `<Note>`, `<Caution>`, `<Error>`, `<Danger>`, `<Success>` opening/closing pairs now render as proper callout components in both docs and KB editor.
- **NOTE callout color**: Changed from blue/purple to grey (bg-slate-500/10, text-slate-400) in both docs CALLOUT_CONFIG and editor CALLOUT_STYLES.
- **Steps width**: Article container widened from max-w-[800px] to max-w-4xl so Steps components have more room.
- **System theme default**: Both docs and KB editor now detect `prefers-color-scheme: dark` when no stored preference exists.
- **Mobile sidebar fix**: Removed stale `transform` class from docs sidebar that was overriding `-translate-x-full` on mobile viewports.
- **Responsive CSS**: Added mobile-specific styles for headings, code blocks, and tables.

## Architecture
- **Backend**: FastAPI (Python), MongoDB
- **Frontend**: React with Craco + Shadcn/UI + TipTap editor
- **Sync Engine**: 5-layer Atlas sync
- **Auth**: Emergent-managed Google Auth
- **Email**: Amazon SES (outbound), Gmail IMAP (disabled)
- **AI**: Gemini for ticket summarization

### Session: Mar 24, 2026 (Docs Visual Polish — Callouts, Tables, Steps, Images)
- **Callout blockquote fix**: Updated preprocessor regex in DocContent.jsx to handle escaped brackets `\[!TYPE\]` and same-line body text. All callouts on all pages now render as styled components (Tip, Info, Warning, Note, Success, etc.) instead of blockquotes.
- **Image shadow removal**: Removed shadow-lg/border container from Figure component and img renderer. Images now render cleanly without outer wrapper.
- **Table spacing reduced**: Changed table wrapper from `my-6` to `my-4` for tighter spacing.
- **Empty code block fix**: Added robust text extraction in CodeBlockRenderer to properly detect and skip empty/whitespace-only code blocks. Overrode `pre` component to remove default wrapper.
- **Steps accent fix**: Added CSS rules for `.step-body` to normalize inline code color (inherit instead of teal accent) and simplify code block appearance within steps.
- **Steps width fix**: Removed `overflow-hidden` from prose container, added `min-width: 0` to step flex children, ensured steps container uses full width.
- **No-language code blocks**: Now render as simple pre blocks without the header bar (language name + copy button).
- **Responsive verified**: Mobile layout (375px) confirmed working — sidebar hidden, breadcrumb bar with hamburger menu, content fills screen.

### Session: Mar 24, 2026 (Category/Subcategory Settings + CopyButton Fix)
- **CategorySettingsSlider** (new component): Slide-in settings panel for categories and subcategories with title input (rename), public/hidden toggle, delete button with confirmation modal. Auto-saves on close.
- **Sidebar updated**: Settings gear icon appears next to "+" icon on hover for both categories (groups) and subcategories (sections). "Hidden" tag shown on sidebar for unpublished categories/subcategories.
- **Backend visibility filtering**: `GET /api/kb/public-data` now skips categories with `published: false` and subcategories with `published: false`.
- **CopyButton fix**: Removed ChevronDown dropdown icon. Added `w-fit` to constrain width on mobile (no longer stretches full width).
- **Testing**: 18/18 tests pass (9 frontend UI, 2 backend API, 7 docs visual).

### Session: Mar 24, 2026 (Code Color + Table Gap + SEO + Accessibility)
- **Inline code color**: Changed from `text-pink-600` (purple) to `text-[#00A1B2]` (primary teal). Background also updated to `bg-[#00A1B2]/10`.
- **Table gap fix**: Reduced cell padding from `py-3` to `py-2.5`. Added `[&_tr:last-child_td]:border-b-0` to remove bottom border gap on last row.
- **SEO**: Dynamic `document.title`, `meta description`, Open Graph tags (`og:title`, `og:description`, `og:url`), Twitter Card tags, canonical URL, JSON-LD structured data (`TechArticle` schema), `html lang="en"`.
- **Accessibility**: Skip-to-content link, `role="navigation"` on sidebar, `role="main"` on main content, `role="complementary"` on TOC, `aria-expanded` on collapsible groups, `aria-current="page"` on active nav item, `aria-label` on close/copy/nav buttons, `tabIndex={-1}` on heading anchors, `focus-visible` outline styles (primary color), `prefers-reduced-motion` support.
- **Testing**: 16/16 tests pass (6 SEO, 7 accessibility, 3 visual).

## Pending Tasks

### P0 — Data Integrity
- Restore lost accordion content on 6 pages (faqs, deployment-information, mobile-app-development, rollback-feature, stripe-integration, using-apis-on-emergent) — blocked on user input

### P2 — Content Quality
- Raw HTML (`<div data-type="column-card">`) on `context-limits` page needs parser handling

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
- Unify markdown parsing logic between RichTextEditor.jsx and lib/mdx/parser.js into shared utility
