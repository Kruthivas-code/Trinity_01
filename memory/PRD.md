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
- AI Ticket Summarization (auto-summarizes tickets with 5+ customer messages, past issue history)
- **Customer Portal** -- public help center at `/`, customer auth, ticket submission/tracking/replies, 10 admin-editable categories
- **Admin Category Management** -- Trinity admins can CRUD portal categories from /settings, including linking help.emergent.sh articles
- **Customer Ticket History** -- Logged-in portal customers can view all submitted tickets at /portal/my-tickets with detail view
- Data import/export
- API key management
- Custom inboxes and filters
- Analytics dashboard

## Current Status (Feb 2026)
- **Email System:** All legacy email configurations removed. Ready for fresh Mailgun integration.
- **Customer Portal:** Fully implemented and tested (V2 complete with admin category mgmt + ticket history)
- **Admin Category Management:** Complete -- edit/delete/add categories with help.emergent.sh article links from Settings page
- **Knowledge Base:** Fully implemented and tested
- **AI Summarization:** Fully implemented and tested

## Routing Structure
- `/` -- Customer portal home (public)
- `/portal/*` -- Portal routes (category, submit, login, my-tickets, ticket detail)
- `/dashboard`, `/login`, `/settings`, etc. -- Trinity admin routes (protected)

## Key Collections
- tickets, users, teams, messages, email_replies, knowledge_snippets
- portal_categories (now with help_articles field), portal_customers, portal_sessions
- csat_responses, csat_tokens, custom_inboxes, webhooks, etc.

## P0 - Completed
- Admin category management UI in Trinity settings
- Customer ticket history page

## P1 - Next Priority
- New Email System: Mailgun outbound from `support@emergent.sh` + webhook inbound
- Customer replies in portal (ability to reply to tickets from portal)

## P2 - Backlog
- Real-time notification center (non-intrusive, badge-based)
- Advanced reporting/analytics

## 3rd Party Integrations
- Gemini 3 Flash (via emergentintegrations + EMERGENT_LLM_KEY)
- Mailgun (planned, not yet integrated)

## Important Notes
- No toast notifications (user explicitly dislikes them)
- Portal uses separate auth from Trinity admin (portal_customers vs users collection)
- 10 default categories seeded on startup if none exist
- Categories support help_articles field [{title, url}] linking to help.emergent.sh
