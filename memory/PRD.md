# Trinity - Enterprise Ticket Management Platform

## Original Problem Statement
Build an enterprise ticket management platform with email-first support management. Features include ticket CRUD, team management, real-time collaboration, SLA tracking, CSAT surveys, knowledge base, customer portal, and email integration.

## Core Requirements
- Ticket management with full CRUD, assignment, escalation, notes, activity
- Team and shift management
- Real-time collaboration via Socket.IO
- SLA policies and tracking
- CSAT surveys
- Knowledge base with AI-powered article refinement (Gemini)
- Customer-facing support portal with auth, ticket submission, tracking, and replies
- Public KB docs site mirroring help.emergent.sh
- Email integration for inbound/outbound (being rebuilt)
- Data import/export (JSON, CSV, Atlas)
- API key management
- Custom inboxes and filters
- Analytics dashboard

## Architecture
- **Frontend:** React + Tailwind CSS + Shadcn/UI
- **Backend:** FastAPI + MongoDB (pymongo)
- **Real-time:** Socket.IO
- **AI:** Gemini via emergentintegrations
- **Auth:** Emergent Google Auth (admin) + Email/Password (portal customers)

## What's Been Implemented
- Full ticket management system (CRUD, assignment, escalation, merge, split, link)
- Team and shift management
- Real-time collaboration (Socket.IO)
- SLA policies and tracking
- CSAT surveys (email delivery pending)
- Knowledge Base with AI refinement
- AI Ticket Summarization (auto-summarizes tickets with 5+ customer messages)
- **Customer Portal** at `/` and `/portal/*` — customer auth, ticket submission/tracking/replies, 10 admin-editable categories
- **Admin Category Management** — CRUD portal categories from /settings, including help.emergent.sh article links
- **Customer Ticket History** at `/portal/my-tickets` with detail view
- **KB Docs Site** at `/docs` and `/docs/:slug` — 21 articles scraped from help.emergent.sh, sidebar nav, top nav tabs, search, dark/light mode, markdown rendering with callouts, prev/next navigation, TOC
- Data import/export
- API key management
- Custom inboxes and filters
- Analytics dashboard

## Current Status (Feb 2026)
- **Email System:** Legacy removed. Ready for Mailgun integration.
- **Customer Portal:** V2 complete (admin category mgmt + ticket history)
- **KB Docs:** V1 complete — 21 articles imported, mirroring help.emergent.sh design
- **Knowledge Base (Admin):** Fully implemented
- **AI Summarization:** Fully implemented

## Routing Structure
- `/docs`, `/docs/:slug` — KB documentation site (public, new homepage)
- `/` — Customer portal support center (category grid)
- `/portal/*` — Portal routes (category, submit, login, my-tickets, ticket detail)
- `/dashboard`, `/login`, `/settings`, etc. — Trinity admin routes (protected)

## Key Collections
- tickets, users, teams, messages, email_replies, knowledge_snippets
- portal_categories (with help_articles), portal_customers, portal_sessions
- **kb_articles** (21 articles: slug, title, section/nav keys, content_markdown, order, published)
- **kb_navigation** (sidebar nav structure: 5 groups with sections)
- csat_responses, csat_tokens, custom_inboxes, webhooks, etc.

## P1 - Next Priority
- New Email System: Mailgun outbound from `support@emergent.sh` + webhook inbound
- Customer replies in portal (ability to reply to tickets from portal)
- KB article editing from Trinity admin (CRUD UI for kb_articles)

## P2 - Backlog
- Real-time notification center (non-intrusive, badge-based)
- Advanced reporting/analytics
- KB full-text search improvement (MongoDB text index or embedding-based)

## 3rd Party Integrations
- Gemini 3 Flash (via emergentintegrations + EMERGENT_LLM_KEY)
- Mailgun (planned, not yet integrated)

## Important Notes
- No toast notifications (user explicitly dislikes them)
- Portal uses separate auth from Trinity admin
- 10 default categories seeded on startup if none exist
- KB articles imported from help.emergent.sh via Playwright scraping (text only, images skipped)
- KB article content is Mintlify-compatible markdown
