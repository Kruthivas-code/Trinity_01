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
- **Email Inbound**: Gmail IMAP (`imaplib`) polling `support@emergent.sh` (alias of `hey@emergent.sh`)
- **Auth**: Emergent Google OAuth (dashboard), JWT-like sessions (portal)
- **Brand Color**: `#00A1B2`

## Credentials
- **Dashboard**: Google OAuth (Emergent Auth). For testing: session cookie via MongoDB
- **Portal**: Self-registration. Test account: `kruthivas@emergent.sh` / `Password123`

---

## Ticket Channels (3 Sources)

| Channel | Source Value | How It Works |
|---------|-------------|--------------|
| **Portal** | `portal` | Customer submits via `/portal/submit` → ticket created → confirmation email sent |
| **Dashboard** | `manual` | Agent creates via "+ New Ticket" in dashboard |
| **Email** | `email` | Customer emails `support@emergent.sh` → IMAP poller reads it → creates ticket |

---

## Email System Architecture

### Outbound (SES SMTP)
- **Endpoint**: `email-smtp.us-east-1.amazonaws.com:587` (auto-detected from 6 regions)
- **From**: `Emergent Support <support@emergent.sh>`
- **Threading**: `Message-ID`, `In-Reply-To`, `References` headers on every email
- **Triggers**:
  - Ticket confirmation → when customer submits via portal
  - Agent reply notification → when agent sends a reply (type='reply') in dashboard
  - Status update → when ticket status changes to resolved/closed/in_progress
- **Rate limiting**: 10 emails/sec (sliding window, thread-safe)
- **Retry queue**: Failed emails stored with exponential backoff (2^n seconds, max 1hr, max 5 attempts). Processed every ~2.5 min
- **All Message-IDs stored** in `email_threads` collection for threading

### Inbound (IMAP Polling)
- **Server**: `imap.gmail.com:993` SSL
- **Account**: `hey@emergent.sh` (app password auth). `support@emergent.sh` is an alias to this mailbox
- **Poll interval**: 30 seconds for UNSEEN emails
- **Processing logic**:
  - If email matches existing ticket via `In-Reply-To`/`References` headers → add as `customer_reply` to that ticket
  - If no match → create new ticket with `source: "email"`, tagged `["email"]`
  - Own emails (from `support@emergent.sh` or `hey@emergent.sh`) are skipped
  - Duplicate emails are skipped (Message-ID dedup)
  - **Bounce detection**: mailer-daemon/postmaster emails identified, original outbound marked as bounced
- **Body processing**: Strips quoted text (`On ... wrote:`, `>` lines, `---`, `Original Message`), sanitizes HTML (XSS prevention, script/style removal, null byte removal)
- **Resilience**: Auto-reconnect with exponential backoff on IMAP errors

### Dashboard Integration
- Messages show **"via email"** (teal badge) or **"via portal"** (gray badge) based on `source` field
- Email-sourced tickets show `Source: Email` in ticket attributes
- **Email delivery status** widget in ticket detail sidebar: shows sent/bounced/failed/received counts
- `GET /api/tickets/{id}/email-stats` endpoint for delivery stats

### Email Templates
- Branded HTML with `#00A1B2` accent, responsive design
- Plain text fallback included
- Templates: ticket confirmation, agent reply, status update

---

## Backend Architecture

### Route Modules (`/app/backend/routes/`)
| Module | Prefix | Purpose |
|--------|--------|---------|
| `auth.py` | `/api/auth` | Google OAuth session exchange, API keys |
| `tickets.py` | `/api/tickets` | CRUD, notes, assignment, status changes |
| `ticket_ops.py` | `/api/ticket-ops` | Bulk operations, merge, split |
| `portal.py` | `/api/portal` | Customer auth, categories, ticket submission |
| `kb.py` | `/api/kb` | Knowledge Base articles, navigation, images |
| `knowledge_base.py` | `/api/knowledge-base` | Internal KB snippets for agents |
| `admin.py` | `/api/admin` | Custom fields, routing rules, SLA policies |
| `analytics.py` | `/api/analytics` | Dashboard analytics, exports |
| `teams.py` | `/api/teams` | Team management |
| `users.py` | `/api/users` | User management, profiles |
| `customers.py` | `/api/customers` | Customer CRM, merge, link emails |
| `filters.py` | `/api/filter` | Advanced ticket filtering, custom inboxes |
| `canned_responses.py` | `/api/canned-responses` | Saved reply templates |
| `csat.py` | `/api/csat` | Customer satisfaction surveys |
| `feature_requests.py` | `/api/feature-requests` | Feature request tracking |
| `webhooks.py` | `/api/webhooks` | Webhook subscriptions and delivery |
| `email.py` | `/api/email` | Legacy email/import routes, image uploads |
| `summaries.py` | `/api/summaries` | AI-powered ticket summaries |
| `shifts.py` | `/api/shifts` | Agent shift management |
| `sla.py` | `/api/sla` | SLA policy enforcement |
| `leaves.py` | `/api/leaves` | Leave management |
| `exports.py` | `/api/admin/export` | Data exports (tickets, customers, analytics) |
| `search_presence.py` | `/api/search` | Search, presence tracking, notifications |

### Services (`/app/backend/services/`)
| File | Purpose |
|------|---------|
| `email_service.py` | SES SMTP sending, threading, rate limiting, retry queue |
| `email_poller.py` | IMAP polling, ticket matching/creation, body parsing |
| `email_templates.py` | Branded HTML/text email templates |

### Key MongoDB Collections
| Collection | Docs | Purpose |
|-----------|------|---------|
| `tickets` | 1,632 | All tickets (portal, email, manual) |
| `messages` | 1,393 | Ticket conversation messages |
| `email_threads` | 8,172 | Email Message-ID tracking for threading and dedup |
| `email_replies` | 552 | Legacy email replies |
| `users` | 13 | Dashboard agents/admins |
| `portal_customers` | 39 | Portal customer accounts |
| `kb_articles` | 46 | Knowledge base articles |
| `customers` | 29 | CRM customer records |
| `custom_inboxes` | 16 | Saved filter views |
| `portal_categories` | 10 | Help portal category structure |

---

## Frontend Architecture

### Pages
| Route | Component | Auth |
|-------|-----------|------|
| `/` | `PublicDocs.jsx` | Public |
| `/docs/:slug` | `PublicDocs.jsx` | Public |
| `/portal` | `PortalHome.js` | Public |
| `/portal/login` | `PortalLogin.js` | Public |
| `/portal/submit` | `PortalSubmit.js` | Portal auth |
| `/portal/my-tickets` | `PortalTickets.js` | Portal auth |
| `/portal/my-tickets/:id` | `PortalTicketDetail.js` | Portal auth |
| `/portal/category/:slug` | `PortalCategory.js` | Portal auth |
| `/login` | `LoginPage.js` | Public |
| `/dashboard` | `MainLayout` | Google OAuth |
| `/all-tickets` | `MainLayout` | Google OAuth |
| `/dashboard/kb-editor` | `KBEditor.jsx` | Google OAuth |
| `/csat/:token` | `CSATPage.js` | Public |

### Key Frontend Components
- **Knowledge Base**: `PublicDocs.jsx` (layout, theme, search, sidebar), `DocContent.jsx`, `Cards.jsx`, `Accordion.jsx`, `Steps.jsx`, `Tabs.jsx`
- **Portal**: `PortalLayout.js` (header with dark mode sync), `PortalHome.js` (hero, cards, categories, search)
- **Dashboard**: `MainLayout.js`, `TicketConversation.js`, `EmailMessage.js` (with source badges), `useTicketDrawer.js`
- **Auth**: `ProtectedRoute.js` (cookie-based), `PortalAuthContext.js` (JWT-like token)

### Design System
- **Light theme**: White backgrounds, `border-gray-200`, `text-gray-900`
- **Dark theme**: `bg-[#0a0a0a]`, `border-white/10`, text `#999999` (muted), `#787878` (secondary), white (headings)
- **Cards**: `rounded-2xl`, `bg-white dark:bg-[#0a0a0a]`, `border-gray-200 dark:border-white/10`, `hover:border-[#00A1B2]`
- **KB sidebar**: White bg (light), no icons on pages, collapsible groups with chevron, tabs as plain text headers

---

## Completed Work (This Session — Feb 2026)

### Email System (Phase 1 + Phase 2)
- SES SMTP outbound with auto-region detection
- IMAP inbound polling with ticket creation from new emails
- Email threading via Message-ID/In-Reply-To/References
- Rate limiting (10/sec), retry queue (exponential backoff)
- Body sanitization (XSS, quoted text stripping)
- "via email" / "via portal" source badges
- 13 unit tests passing

### UI/UX Overhaul
- KB sidebar redesign (collapsible groups, no icons, white bg)
- Dark mode neutral greys (#999999, #787878) across all content components
- Portal UI: consistent header, brand colors, 960px max-width, 3-col category grid, search
- Portal dark mode page-load fix (dark class sync)
- Portal auth body-stream bug fix
- Docs header: "Need Help" as primary CTA (removed "Try Emergent")

### Bug Fixes
- Portal registration "body stream already read" error → `res.text()` + `JSON.parse()`
- Sender fallback matching pollution → removed, cleaned 75 bogus messages
- IMAP poller missing ticket creation → added `_create_ticket_from_email()`

---

## Completed Work (Feb 23, 2026)

### IST Timezone & Atlas Cleanup
- All timestamps across the app now display in IST (Asia/Kolkata, UTC+5:30)
- Fixed root cause: backend sends naive UTC timestamps without Z suffix; added `ensureUTC()` helper that appends Z before JS Date parsing
- Updated 15+ frontend files with `timeZone: 'Asia/Kolkata'` and UTC-aware date parsing
- Created centralized `utils/dateFormat.js` utility with `ensureUTC`, `formatDateTime`, `formatDateShort`, `formatDateFull`, `formatDateWithWeekday`
- Converted 244 Manish (Atlas) messages from `reply` → `internal_note`
- Deleted 5,968 Atlas messages older than 1 week (keeping 1,196 from Feb 16–22)

### IMAP Poller Fix — Critical Email Processing Bug
- **Root cause**: 53,867 unseen emails in inbox. Poller searched UNSEEN oldest-first, timing out before reaching new emails at position ~53,849
- **Fix**: Changed to search by `SINCE <7 days ago>` (not UNSEEN), process **newest first** (reversed order)
- Result: 11,262 emails from last 7 days, processed newest first — r44ohit@gmail.com emails immediately picked up
- Files modified: `email_poller.py`

### Duplicate Reply Bug Fix
- **Root cause**: Frontend was calling BOTH `/api/tickets/{id}/reply` (stores plain text message) AND `/api/tickets/{id}/notes` (stores HTML message + sends email) — creating 2 messages per reply
- **Fix**: Removed the redundant `/reply` call; `/notes` endpoint already handles email sending
- Cleaned up affected ticket TKT-035560
- Files modified: `useTicketDrawer.js`

### UI Density Improvements (2x)
- **Ticket list**: Combined preview+metadata into one row, reduced padding from `py-4` to `py-1.5`, font sizes from 13-15px to 11-13px — ~17 tickets visible vs ~9 before
- **Conversation**: Reduced message spacing from `space-y-1.5` to `space-y-0.5`, container padding from `p-3` to `p-1.5`, message body font from 14px to 12px with `leading-snug`, tighter prose paragraph spacing
- **Email content**: Reduced empty line spacer from `h-1` to `h-px`, font from 13px to 12px
- Files modified: `TicketsListView.js`, `EmailMessage.js`, `TicketConversation.js`, `EmailViewer.js`
- Tested by testing_agent: 100% pass rate (iteration_45)

### Initial-Based Avatars in Ticket Conversation
- Replaced generic single-character avatars with full initials (e.g., "Nikita C" → "NC", "Atlas Agent" → "AA")
- Curated 8-color on-brand palette (Cyan, Blue, Indigo, Violet, Teal, Emerald, Amber, Rose) harmonizing with brand teal `#00A1B2`
- Deterministic color assignment via name hashing — same sender always gets same color
- Handles full names, single names, and email addresses as sender names
- Works across all message types: customer (left-aligned), agent replies (right-aligned), internal notes (center)
- Updated typing indicator to use same avatar system
- Files modified: `EmailMessage.js`, `TicketConversation.js`
- Tested by testing_agent: 100% pass rate (iteration_44)

### Search API Method Fix (Feb 23, 2026)
- **Root cause**: Frontend (GlobalHeader, CommandPalette, SearchResultsPage) all call `GET /api/search?q=...&limit=...` but backend only had `POST /api/search` handler — returned 405 Method Not Allowed
- **Fix**: Added `GET /api/search` endpoint in `search_presence.py` accepting query params `q`, `limit`, `type`
- Both GET and POST handlers now work, calling the same `SearchEngine.search_all()` method
- Files modified: `backend/routes/search_presence.py`
- Tested by testing_agent: 100% pass rate (iteration_46, 8/8 tests)

### Ticket Switching Bug Fix (Feb 23, 2026)
- **Root cause**: Clicking a related ticket in CustomerHistoryPanel used `navigate()` to change URL, but the `useEffect` in MainLayout depended on the `searchParams` object reference which didn't reliably trigger re-renders for same-route query param changes
- **Fix**: (1) Changed useEffect dependency from `searchParams` object to extracted `ticketIdFromUrl` string for reliable primitive comparison. (2) Added `onTicketSwitch` callback prop that bypasses URL-based navigation by directly calling `openTicketById()` to fetch and display the new ticket
- Files modified: `MainLayout.js`, `TicketDrawer.js`, `CustomerHistoryPanel.js`, `DashboardContainer.js`
- Tested by testing_agent: 100% pass rate (iteration_47, 5/5 tests)

### Compact Header + Backend-Driven Sorting (Feb 23, 2026)
- **UI Density**: Compacted tickets list header into single row — title+count on left, sort dropdown+filter button on right. Reduced padding from py-2 to py-1.5, removed subtitle row
- **Sorting**: Added sort dropdown with 8 fields (created_at, updated_at, last_message_at, last_customer_message_at, last_agent_message_at, priority, status, escalation_level). All sorting is backend-driven (MongoDB query level). Click same field to toggle asc/desc
- **Backend**: Added `last_message_at`, `last_customer_message_at`, `last_agent_message_at` field tracking to ticket note creation and IMAP poller. Whitelisted sort fields in both GET /api/tickets and POST /api/filter/tickets
- Files modified: `TicketsListView.js`, `tickets.py`, `filters.py`, `email_poller.py`
- Tested by testing_agent: 100% pass rate (iteration_48, 28/28 tests)

### KB Editor Theme - Content Color Fix (Feb 24, 2026)
- **Root cause**: DocContent, Cards, Tabs, Steps, Accordion all use Tailwind `dark:` variants (e.g. `dark:text-white`, `dark:bg-slate-800`). These respond to `.dark` class on `<html>`. The KB Editor was toggling its own theme state but never synced it to `document.documentElement.classList`
- **Fix**: Added `useEffect` to toggle `.dark` class on `<html>` based on editor theme, with cleanup on unmount. Now content colors and card styles match the Docs page exactly
- **Verified**: Dark heading=`rgb(255,255,255)`, Light heading=`rgb(17,24,39)`. Cards, borders, backgrounds all correct. PublicDocs page confirmed independent
- Tested: 100% pass (iteration_50, 9/9 features)

### KB Editor Independent Scrollbars (Feb 24, 2026)
- **Root cause**: Textarea's intrinsic `min-height: auto` as a flex item prevented flex containers from shrinking, pushing the page body taller than the viewport. Mouse wheel scrolling then moved the entire page, affecting both panels simultaneously.
- **Fix**: (1) Added `overflow: hidden` to `<html>` and `<body>` on mount via `useEffect` (cleaned up on unmount). (2) Added `min-h-0` to all flex containers in the sidebar→editor chain to allow proper flex shrinking. (3) Changed textarea from `flex-1` to absolute positioning within a `flex-1 min-h-0 relative` wrapper, fully containing it.
- **Sidebar scrollbar**: Only visible on hover via custom CSS `.scrollbar-on-hover` using `scrollbar-color: transparent` → visible on `:hover`.
- Files modified: `KBEditor.jsx`, `ArticleSidebar.jsx`, `index.css`
- Tested: Mouse wheel simulation — sidebar scrollTop=500 stays put when textarea scrolls to 500, page scroll always 0.

### Custom Inbox Delete Navigation Fix + Sidebar Density (Feb 25, 2026)
- **Bug fix**: Deleting a custom inbox while viewing it now navigates to `/all-tickets` instead of staying on the stale deleted inbox view.
- **Sidebar density**: Reduced nav item height from `h-9` (36px) to `h-7` (28px), tightened section spacing and divider margins for more text density.
- Files modified: `Sidebar.js`

### Conversation Thread Refactor — Single Source of Truth (Feb 25, 2026)
- **Duplicate message fix**: Conversation thread now built entirely from `messages` collection (single source of truth). Removed synthetic `ticket.description` injection from frontend. Notes API updated to include `type: "original"`. Cleaned up 368 original+customer_reply duplicates and 617 duplicate customer_reply records.
- **Email HTML preservation**: Refactored `_extract_reply_body` → `_extract_email_parts` returning `{content, email_html, email_text}`. Messages now store all three fields. `EmailViewer` renders rich HTML when available.
- **Backfill**: Created `original` messages for 6125 legacy tickets that only had `ticket.description`.
- **All ticket creation paths now create original messages**: email (already did), portal tickets (already did), portal inquiries (added), manual agent tickets (added).
- Files modified: `email_poller.py`, `tickets.py`, `portal.py`, `useTicketDrawer.js`, `EmailMessage.js`, `TicketConversation.js`
- Tested: 100% pass (8 backend + 16 frontend tests)

### Ticket Drawer UI Fixes (Feb 25, 2026)
- **Issue 1 — Stable ticket order**: Rewrote `CustomerHistoryPanel.js` to render all tickets in a single flat list sorted by `created_at` desc. Only the highlight moves when switching tickets — order never changes.
- **Issue 2 — WhatsApp-style delivery ticks**: Removed `EmailDeliveryStatus` from Attributes section. Added delivery indicators to agent reply messages: ✓✓ (sent via email), ✓ (sent), ⚠ (failed/bounced). Shows tooltip on hover.
- **Issue 3 — Tags without #**: Removed hardcoded `#` prefix from tag display.
- **Issue 4 — Stray brackets**: Deleted orphaned `)}` text.
- **Issue 5 — Removed Channel field**: Removed redundant "Channel" row from Attributes.
- Files modified: `CustomerHistoryPanel.js`, `TicketDetailsPanel.js`, `EmailMessage.js`, `TicketConversation.js`

---

### Docs Page Header Refactor + Breadcrumb Bar (Feb 25, 2026)
- Replaced full center search bar in header with a simple search icon button (opens search dialog on click, Cmd+K shortcut still works)
- Added a secondary breadcrumb bar below the main header showing "Section > Article Title" with subtle backdrop blur and semi-transparent fill
- Breadcrumb bar has a hamburger menu icon on mobile (lg:hidden) that toggles the sidebar
- Adjusted layout offsets: sidebar, right TOC, and main content all start below both headers (top-24 / pt-24)
- Theme-adaptive: light uses rgba(255,255,255,0.75), dark uses rgba(10,10,10,0.75) with 12px blur
- Tested: 100% pass (31/31 docs page tests, iteration_53)

### Social Links on Docs Pages (Feb 25, 2026)
- Added social links (Twitter/X, LinkedIn, Discord, YouTube, Reddit) below the Next/Previous CTAs on all public docs pages
- Backend: `GET /api/kb/social-links` (public) and `PUT /api/kb/admin/social-links` (admin) endpoints using `kb_settings` collection
- Frontend: `SocialLinks` component in `PublicDocs.jsx` renders SVG icons, theme-adaptive (muted gray → bright on hover), hidden when no links configured
- KB Editor: `SocialLinksPanel.jsx` modal accessible via Share2 icon button in editor header — manage all 5 platform URLs
- Tested: 100% pass (28/28 tests, iteration_52)

---

### P1 Improvements (Feb 26, 2026)
- **Strip Duplicate H1**: When loading an article into the editor, if the content starts with `# Title` matching the article title, it's stripped (since title is shown separately in Document Section)
- **"On This Page" TOC**: Added TOC section between Publishing and Content in the editor, showing H2/H3 headings extracted from the markdown content. Hidden when no headings exist.
- **Backend Search Refactor**: Replaced client-side FlexSearch with backend `GET /api/kb/search?q=query`. Returns results with contextual snippets (±60/100 chars around match) and category/section info. Frontend uses 200ms debounced API calls. Snippets show highlighted match text.
- Tested: 100% pass (29/29 backend + 46/46 frontend tests, iteration_55)

### Email Threading Fix — Production-Grade (Feb 26, 2026)
- **Root cause**: `get_thread_context()` only looked at outbound emails. First agent reply sent without In-Reply-To/References headers → customer reply created new ticket.
- **Primary pipeline** (99% coverage): Proper In-Reply-To + References chain on ALL outbound emails. DB indexes on message_id, gmail_thread_id, ticket_id for fast lookups.
- **Matching pipeline**: In-Reply-To → References → Gmail Thread ID → References overlap → X-Ticket-ID header → Body ticket ID extraction → Subject+email match (multi-layer Re:/Fwd: stripping)
- **Additional**: Bounce detection, retry queue with exponential backoff, rate limiting
- All 6 unit tests passing

### Ticket Merge & Search Bug Fixes (Feb 26, 2026)
- **Bug 1 — One-click "Accept Merge"**: Rewired the merge suggestion banner's "Merge" button (now "Accept Merge") to call `handleAcceptMergeSuggestion` which directly merges the suggested ticket INTO the current ticket via `POST /api/tickets/{suggestedId}/merge`. Previously opened the manual search modal.
- **Bug 2 — Merge modal search broken**: Fixed `MergeTicketModal.js` — changed API param from `types=tickets` (wrong) to `type=ticket` (correct) and response parsing from `data.tickets` to `data.by_category?.tickets`.
- **Bug 3 — Numeric ticket ID search**: Added direct `ticket_id` lookup in `search.py` `search_tickets()` for numeric-only queries. Searching "042237" now automatically finds "TKT-042237".
- **Bug 4 — 3+ duplicate detection**: Backend already returned all duplicates. Fixed frontend to display count ("2 possible duplicates detected") and each suggestion gets its own one-click merge button.
- Tested: 100% pass (7/7 backend + all frontend tests, iteration_56)

### KB Editor v2 — Visual Columns, Cards & Slash Commands (Feb 26, 2026)
- **Visual Columns & Cards**: Created custom TipTap extensions (`ColumnsBlockNode`, `ColumnCardNode`) that render `<Columns>` and `<Card>` markdown components as visual, editable cards in a grid layout (1/2/3 columns). Cards display icon, title, description with hover effects.
- **Card Edit Popup**: Click any card to open "Edit Card Attributes" popup with fields: Title, Description, Icon, URL, Image Path, Call To Action, and Horizontal layout toggle. Includes Save/Delete buttons.
- **Edit Columns Popup**: Hover over columns block reveals "Edit Columns" button. Popup lets user change column count (1/2/3) with a dropdown selector.
- **Slash Command Menu**: Typing "/" triggers a floating menu with 19 items in 3 groups (Basic: Paragraph/Headings/Lists/Code/Divider, Layout: 2/3 Columns, Components: CardGroup/Callouts/Steps/Tabs/Accordion/YouTube). Keyboard nav (arrow keys + Enter).
- **Meta Title & Description**: Renamed "Title" → "Meta Title", "Description" → "Meta Description" with updated placeholders. H1 is now part of content editor.
- **Markdown Pipeline**: Columns/Cards serialized to/from `<Columns cols={N}><Card ...>` markdown syntax. Non-visual components (Callouts, Steps, etc.) still render as code blocks in editor.
- **New files**: `extensions/SlashCommand.jsx`, `extensions/ColumnsBlock.jsx`. Rewrote `RichTextEditor.jsx`.
- **Packages added**: `@tiptap/suggestion`, `tippy.js`
- Tested: 100% pass (10/10 frontend tests, iteration_57)

### KB Editor — Theme Fix & Performance Optimization (Mar 1, 2026)
- **Theme-aware cards**: Cards, popups, and slash command menu now properly adapt to light/dark mode via `EditorThemeContext`. Light mode uses white/gray backgrounds with dark text; dark mode uses dark backgrounds with light text.
- **Lazy article loading**: Backend `GET /api/kb/admin/articles` now excludes `content_markdown` (response ~19KB vs hundreds KB). Added `GET /api/kb/admin/articles/{slug}` for on-demand full content fetch. Frontend lazy-loads content when selecting articles.
- Tested: 100% pass (8/8 tests, iteration_58)

### KB Editor — Visual/Markdown Toggle, Preview Page & Editing Fix (Mar 1, 2026)
- **Removed "On This Page" (TOC) section** from the editor sidebar, per user request.
- **Visual Edit / Markdown toggle**: Replaced the page heading in the editor header with a segmented control toggle. Defaults to "Visual Edit" (WYSIWYG). "Markdown" mode shows a raw textarea for direct markdown editing.
- **Fixed content editing bug**: Added `lastExternalContent.current = md` in the TipTap `onUpdate` handler to prevent the editor from resetting content on every keystroke (caused by the parent re-render cycle).
- **Preview button**: Added "Preview" button in the header that opens a full-page overlay (`ArticlePreview.jsx`) rendering content identically to PublicDocs using `DocContent`. Supports Desktop (100%), Tablet (768px), and Mobile (375px) viewport switching with visual device frames. Includes a "Back to Editor" button.
- **1 Column layout option**: Added "1 Column" to the slash command menu under Layout, alongside the existing 2/3 column options.
- **Responsive columns CSS**: Added `@media (max-width: 768px)` rule to stack multi-column layouts into single columns on smaller screens.
- **New file**: `kb-editor/ArticlePreview.jsx`
- **Modified files**: `KBEditor.jsx`, `RichTextEditor.jsx`, `SlashCommand.jsx`, `index.css`
- Tested: All features verified via code review and screenshots

---

## Pending / Backlog

### P1
- Portal category alignment with user's desired structure

### P2
- Real-time notifications for agents
- Refactor portal categories to backend-managed
- On-demand full thread fetch from Gmail
- Recurring job for auto-closing stale tickets
- Email analytics dashboard (send/receive volumes, match rates)
