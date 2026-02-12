# Trinity / TickFlow - Product Requirements Document

## Original Problem Statement
Build a full-stack email-first support ticket management platform (Trinity/TickFlow) with team management, customer tracking, SLA enforcement, analytics, and knowledge base capabilities.

## Core Architecture
- **Frontend:** React + Shadcn/UI + Tailwind CSS
- **Backend:** FastAPI + MongoDB
- **Auth:** Emergent-managed Google OAuth
- **AI:** Gemini 3 Flash (via emergentintegrations) for KB article refinement
- **Email:** IMAP sync + Gmail OAuth integration

## Current Status: Stable & Feature-Complete (as of Feb 2026)

### Implemented Features
- **Ticket Management:** Full CRUD, multi-level escalation (L1/L2/L3), status tracking, starring, merging, assignment
- **Email Integration:** IMAP sync, Gmail OAuth, email-to-ticket conversion, IDLE watcher
- **Team Management:** Create/manage teams, assign members, team-based ticket routing
- **Customer Management:** Customer profiles, contact info, ticket history
- **Canned Responses:** Pre-built reply templates with variable placeholders
- **Knowledge Base:** Snippet CRUD, AI-powered refinement (Gemini), search/filter/export, KB picker in ticket replies, save agent replies as KB snippets
- **Analytics Dashboard:** Ticket stats, team performance, SLA metrics
- **SLA Policies:** Configurable SLA rules with escalation
- **User Management:** Profiles, roles, leave management
- **Feature Requests:** Internal feature tracking with voting
- **Settings:** App configuration, admin panel
- **Real-time:** WebSocket for typing indicators, live updates
- **Search:** Global ticket/user search

### Knowledge Base (NEW - Feb 12, 2026)
- **KB Page** (`/knowledge-base`): Browse, search, filter, create, edit, delete snippets
- **Snippet Types:** Internal (content in DB) and External (links to help articles)
- **AI Refine:** One-click Gemini-powered polish of raw agent replies into clean KB articles
- **KB Picker:** Modal in ticket reply composer to search and insert KB articles (as link or inline content)
- **Save to KB:** Button on agent messages in conversation to save reply as draft snippet
- **Export:** JSON and CSV export of all snippets
- **Tags & Status:** Organize snippets with tags, track draft/refined/published status

### Toast Removal (Feb 12, 2026)
- All `sonner` toast notifications removed from the application
- `<Toaster>` component removed from App.js

## Key Files
- Backend KB: `/app/backend/routes/knowledge_base.py`
- Frontend KB Page: `/app/frontend/src/components/pages/KnowledgeBasePage.js`
- Frontend KB Picker: `/app/frontend/src/components/common/KnowledgeBasePicker.js`
- Ticket Drawer (KB integration): `/app/frontend/src/components/tickets/TicketDrawer.js`
- Database: `/app/backend/database.py` (knowledge_snippets_collection)

## API Endpoints (Knowledge Base)
- `GET /api/knowledge-base` — List snippets with search/filter/pagination
- `GET /api/knowledge-base/{id}` — Get single snippet
- `POST /api/knowledge-base` — Create snippet
- `PUT /api/knowledge-base/{id}` — Update snippet
- `DELETE /api/knowledge-base/{id}` — Delete snippet
- `POST /api/knowledge-base/{id}/refine` — AI refine with Gemini
- `GET /api/knowledge-base-search` — Quick search (published/refined only)
- `GET /api/knowledge-base-export?format=json|csv` — Export all snippets

## Test Reports
- `/app/test_reports/iteration_21.json` — KB feature testing (100% pass)
- `/app/test_reports/iteration_3.json`, `iteration_4.json` — Previous testing rounds

## Upcoming Tasks (P0)
- Real-time Notifications (WebSocket-based, non-intrusive inbox model)
- Advanced Reporting (enhanced analytics)

## Future Tasks (P1)
- Customer-Facing Portal
- AI-Powered Ticket Categorization & Routing
- Third-Party Integrations (Slack, Jira)

## Important Notes
- Backend APIs return lists in `{items: [...]}` wrapper format
- All MongoDB queries must exclude `_id` from projections
- Session-based auth via `session_token` cookie
- EMERGENT_LLM_KEY configured in `/app/backend/.env` for Gemini integration
