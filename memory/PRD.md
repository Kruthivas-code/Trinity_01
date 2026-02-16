# Trinity - Enterprise Ticket Management Platform

## Original Problem Statement
Build an enterprise ticket management platform with email-first support management. Features include ticket CRUD, team management, real-time collaboration, SLA tracking, CSAT surveys, knowledge base, customer portal, and email integration.

## Architecture
- **Frontend:** React + Tailwind CSS + Shadcn/UI
- **Backend:** FastAPI + MongoDB (pymongo)
- **Real-time:** Socket.IO
- **AI:** Gemini via emergentintegrations
- **Auth:** Emergent Google Auth (admin) + Email/Password (portal customers)

## What's Been Implemented
- Full ticket management system (CRUD, assignment, escalation, merge, split, link)
- Team and shift management, real-time collaboration (Socket.IO)
- SLA policies, CSAT surveys, analytics dashboard
- Knowledge Base with AI refinement (Gemini)
- AI Ticket Summarization
- **Customer Portal** at `/` and `/portal/*` — auth, ticket submission/tracking, 10 admin-editable categories with help.emergent.sh links
- **KB Docs Site** at `/docs/:slug` — 21 articles from help.emergent.sh, sidebar nav, top nav, search, dark/light mode, markdown rendering, TOC, prev/next
- **Admin KB Article Manager** at `/settings` — full CRUD: tree view (nav group > section > articles), markdown editor, publish/unpublish toggle, create/delete, slug rename, nav/section assignment, preview link. Navigation structure preserved from original help.emergent.sh
- Data import/export, API key management, custom inboxes/filters

## Routing
- `/docs`, `/docs/:slug` — KB documentation site (public)
- `/` — Customer portal support center (category grid)
- `/portal/*` — Portal routes (category, submit, login, my-tickets, ticket detail)
- `/dashboard`, `/login`, `/settings`, etc. — Trinity admin (protected)

## Key Collections
- tickets, users, teams, messages, knowledge_snippets
- portal_categories, portal_customers, portal_sessions
- **kb_articles** (slug, title, section/nav keys, content_markdown, order, published)
- **kb_navigation** (sidebar nav structure: 5 groups with sections)

## P1 - Next Priority
- New Email System (Mailgun outbound/inbound)
- Customer replies in portal

## P2 - Backlog
- Real-time notification center
- KB full-text search improvement
- Advanced analytics

## 3rd Party Integrations
- Gemini 3 Flash (via emergentintegrations + EMERGENT_LLM_KEY)
