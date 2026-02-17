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
- **KB Docs Site (v2 - Ported from help.emergent.sh source)** at `/` (homepage) and `/docs/:slug` — 21 articles, dark theme (#0a0a0a), 5 top nav tabs with icons, hierarchical left sidebar, right TOC, FlexSearch-powered search (Cmd+K), prev/next navigation, copy page button, breadcrumbs, rich markdown rendering (react-markdown + remark-gfm + react-syntax-highlighter), custom MDX components (Steps, Cards, Tabs, Accordion, Callouts, YouTube/Loom embeds)
- **Full-Page KB Editor** at `/dashboard/kb-editor/:slug` — Split markdown/preview with live DocContent rendering, formatting toolbar (H1-H3, Bold, Italic, Code, Lists, Links, Images), MDX component insertion menu (Callouts, Steps, Cards, Tabs, Accordion, YouTube, Columns), document config panel (slug, nav group, section, order, published), sidebar document tree, Cmd+S auto-save, Cmd+B/I formatting shortcuts, device preview toggles (desktop/tablet/mobile), back-to-dashboard navigation
- **Admin KB Article Manager** at `/settings` — full CRUD: tree view (nav group > section > articles), markdown editor, publish/unpublish toggle, create/delete, slug rename, nav/section assignment, preview link. Navigation structure preserved from original help.emergent.sh
- Data import/export, API key management, custom inboxes/filters

## Routing
- `/`, `/docs/:slug` — KB documentation site (public homepage)
- `/portal`, `/portal/*` — Customer portal (categories, submit, login, tickets)
- `/dashboard`, `/login`, `/settings`, etc. — Trinity admin (protected)
- `/dashboard/kb-editor`, `/dashboard/kb-editor/:slug` — Full-page KB article editor (protected)

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
- KB Image Handling (download/store images from scraped articles)
- Advanced analytics

## Key Files (KB v2)
- `frontend/src/pages/kb/PublicDocs.jsx` — Main KB page (ported from help.emergent.sh)
- `frontend/src/components/docs/DocContent.jsx` — Rich markdown renderer
- `frontend/src/components/docs/{Steps,Cards,Tabs,Accordion,IconPicker}.jsx` — Custom MDX components
- `frontend/src/lib/mdx/parser.js` — MDX component extraction
- `frontend/src/lib/search/index.js` — FlexSearch client-side search
- `frontend/src/pages/KBEditor.jsx` — Full-page KB article editor (split markdown/preview)

## 3rd Party Integrations
- Gemini 3 Flash (via emergentintegrations + EMERGENT_LLM_KEY)
