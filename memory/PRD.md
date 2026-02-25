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

### Ticket Drawer UI Fixes (Feb 25, 2026)
- **Issue 1 — Stable ticket order**: Rewrote `CustomerHistoryPanel.js` to render all tickets (current + related) in a single flat list sorted by `created_at` desc. Only the highlight moves when switching tickets — order never changes.
- **Issue 2 — WhatsApp-style delivery ticks**: Removed `EmailDeliveryStatus` from Attributes section. Added delivery indicators to agent reply messages in conversation: ✓✓ (sent via email), ✓ (sent), ⚠ (failed/bounced). Shows tooltip on hover.
- **Issue 3 — Tags without #**: Removed hardcoded `#` prefix from tag display.
- **Issue 4 — Stray brackets**: Deleted orphaned `)}` text on line 915 of `TicketDetailsPanel.js`.
- **Issue 5 — Removed Channel field**: Removed redundant "Channel" row from Attributes (Source already shows the same info).
- Files modified: `CustomerHistoryPanel.js`, `TicketDetailsPanel.js`, `EmailMessage.js`, `TicketConversation.js`

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
