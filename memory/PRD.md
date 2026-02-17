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
- **Customer Portal** at `/` and `/portal/*` -- Vercel-style contact page with triage funnel: 4 contact cards (Product help, Partner Programs modal, Emergency Help, Talk to Sales modal), Dedicated Engineer upsell ($1000/10hrs admin-configurable), category-based issue triage with auto-tagged ticket submission. No KB links -- pure problem identification to ticket flow.
- **KB Docs Site (v2 - Ported from help.emergent.sh source)** at `/` (homepage) and `/docs/:slug` -- 21 articles, dark theme (#0a0a0a), 5 top nav tabs with icons, hierarchical left sidebar, right TOC, FlexSearch-powered search (Cmd+K), prev/next navigation, copy page button, breadcrumbs, rich markdown rendering (react-markdown + remark-gfm + react-syntax-highlighter), custom MDX components (Steps, Cards, Tabs, Accordion, Callouts, YouTube/Loom embeds)
- **Full-Page KB Editor** at `/dashboard/kb-editor/:slug` -- Split markdown/preview with live DocContent rendering, formatting toolbar (H1-H3, Bold, Italic, Code, Lists, Links, Images), MDX component insertion menu (Callouts, Steps, Cards, Tabs, Accordion, YouTube, Columns), document config panel (slug, nav group, section, order, published), sidebar document tree, Cmd+S auto-save, Cmd+B/I formatting shortcuts, device preview toggles (desktop/tablet/mobile), back-to-dashboard navigation
- **Admin KB Article Manager** at `/settings` -- full CRUD: tree view (nav group > section > articles), markdown editor, publish/unpublish toggle, create/delete, slug rename, nav/section assignment, preview link. Navigation structure preserved from original help.emergent.sh
- **Admin KB Suite** -- Navigation Manager (CRUD for tabs/sections), Icon Picker, auto-increment ordering, tab-scoped prev/next, bulk section move, image upload (drag-and-drop, paste)
- **KB Visual Parity** -- Pixel-perfect match with help.emergent.sh: blockquote styling, callout rendering, "Made with Emergent" badge, header nav refactor
- Data import/export, API key management, custom inboxes/filters

## Routing
- `/`, `/docs/:slug` -- KB documentation site (public homepage)
- `/portal`, `/portal/*` -- Customer portal (categories, submit, login, tickets)
- `/dashboard`, `/login`, `/settings`, etc. -- Trinity admin (protected)
- `/dashboard/kb-editor`, `/dashboard/kb-editor/:slug` -- Full-page KB article editor (protected)

## Key Collections
- tickets, users, teams, messages, knowledge_snippets
- portal_categories, portal_customers, portal_sessions
- **kb_articles** (slug, title, section/nav keys, content_markdown, order, published, icon)
- **kb_navigation** (sidebar nav structure: 5 groups with sections)
- **kb_image_files** (filename, original_name, content_type, data [binary], size, uploaded_at, uploaded_by)

## P0 - Completed
- Admin Image Upload in KB Editor (toolbar button, drag-and-drop, paste support, stored in MongoDB)
- KB Visual Consistency Fixes: decorative blockquote quotes, indigo border color, callout code block font normalization, "Made with Emergent" badge
- Header Navigation: "Get more help" CTA to portal, logo to app.emergent.sh
- KB Editor Enhancements: Navigation Manager (CRUD for tabs/sections), Icon Picker, auto-increment ordering, tab-scoped prev/next
- Bulk section move feature
- **KB Previous/Next Navigation Verification** -- All 5 tabs verified (12/12 tests passed Feb 2026)
- **Article Feedback Widget** -- "Was this article helpful?" thumbs up/down on every KB article, anonymous, confirmation messages, resets on navigation. Admin sidebar shows color-coded helpfulness % badges per article (green >=70%, amber >=40%, red <40%). Backend: kb_feedback collection, POST/GET endpoints. (Feb 2026, all tests passed)
- **Portal Triage Funnel** -- Removed all KB links from category pages. Subtopics are now clickable buttons that navigate to `/portal/submit` with category, subtopic, and tag auto-filled via URL params. Submit form shows context ribbon ("Auto-tagged: Category > Subtopic > Tag"), emergency banner for urgent tickets, contextual placeholders. Backend tickets store tags[], priority, job_id, and video_link from portal flow. Job ID field visible for ALL categories (mandatory for agent-ai, deployments, database, mobile-builds, features, custom-domain, credits-pricing/Credit Usage; optional for others). Video Recording Link field optional for all. Both stored as ticket metadata and displayed in agent dashboard Metadata tab (job_id, video_link, category, subtopic, tags). (Feb 2026, all tests passed)

## P1 - Next Priority
- New Email System (transactional emails for ticket notifications)

## P2 - Backlog
- Real-time notification center
- Advanced analytics
- KBEditor.js refactoring (break into smaller sub-components)

## Key Files (KB v2)
- `frontend/src/pages/kb/PublicDocs.jsx` -- Main KB page (ported from help.emergent.sh)
- `frontend/src/components/docs/DocContent.jsx` -- Rich markdown renderer
- `frontend/src/components/docs/{Steps,Cards,Tabs,Accordion,IconPicker}.jsx` -- Custom MDX components
- `frontend/src/lib/mdx/parser.js` -- MDX component extraction
- `frontend/src/lib/search/index.js` -- FlexSearch client-side search
- `frontend/src/pages/KBEditor.jsx` -- Full-page KB article editor with image upload support
- `backend/routes/kb.py` -- KB API routes including image upload/serve/list/delete

## 3rd Party Integrations
- Gemini 3 Flash (via emergentintegrations + EMERGENT_LLM_KEY)
