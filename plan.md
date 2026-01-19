# TickFlow Plan (Pylon‑rival Ticket Management System)

Problem Statement: Build a beautiful, dark-themed, glassmorphic ticket management app with a 5-column kanban board (Backlog → To Do → In Progress → Review → Done), basic ticket fields (Title, Description, Status), drag-and-drop, multi-user assignments/collaboration, CRUD + analytics/reporting + export/import. Future: AI agents, routing, shift management.
Tech: FastAPI + React + MongoDB + shadcn/ui.

Level Decision: This is Level 2 (CRUD + simple auth). POC is NOT required. We will build the app directly and test comprehensively.

Architecture (High-level)
- Backend (FastAPI): JWT auth; Models: User, Ticket; Endpoints: auth, tickets (CRUD, reorder), analytics, export/import. MongoDB via MONGO_URL. All routes under /api.
- Frontend (React + shadcn/ui + dnd-kit): 5-column board, glassmorphism dark UI, drawer details, create/edit forms, drag-and-drop with persistence, virtualization for large lists.
- Data model (initial)
  - User: { _id, email (unique), name, role, created_at }
  - Ticket: { _id, title, description, status ∈ [backlog,todo,in_progress,review,done], assignee_id (nullable), order (int), created_at, updated_at }

---------------------------------------------
Phase 1: Core Functionality POC (Skipped)
Objectives
- Skipped (Level 2). Proceed to Phase 2 directly.
Implementation Steps
- N/A
Next Actions
- Move to Phase 2 (Main App Development).
Success Criteria
- N/A
User Stories (reference only)
1) As a dev, I can connect to MongoDB using MONGO_URL.
2) As a dev, I can create/read a sample ticket document.
3) As a dev, I can serialize ObjectId and datetime safely from APIs.
4) As a dev, I can hit a health endpoint and receive 200.
5) As a dev, I can lint backend and frontend with no syntax errors.

---------------------------------------------
Phase 2: Main App Development (MVP)
Objectives
- Deliver a working, beautiful kanban app with drag-and-drop and persistence, multi-user auth with assignments, CRUD, analytics, export/import, and a sleek glassmorphism UI.
Implementation Steps
Backend (FastAPI + MongoDB)
- Auth: JWT email/password; endpoints: POST /api/auth/register, /api/auth/login; password hashing.
- Users: GET /api/users (list), GET /api/users/me.
- Tickets: CRUD: GET/POST/PUT/DELETE /api/tickets; list query supports status/assignee filters (basic for analytics/export).
- Reorder/Move: POST /api/tickets/reorder to persist column and order changes from DnD.
- Analytics: GET /api/analytics/summary (counts by status, by assignee).
- Export: GET /api/export?format=csv|json (streamed download).
- Import: POST /api/import (CSV/JSON upload) → bulk create; returns summary.
- Utilities: serialize_doc helper for ObjectId/datetime; error handling; seed script/endpoint (optional).
- Security: Protect ticket endpoints with JWT; basic role field in User (future-ready).
Frontend (React + shadcn/ui)
- Layout: 5 glass panels left→right (Backlog, To Do, In Progress, Review, Done); responsive.
- Drag & Drop: dnd-kit for smooth column and index changes; optimistic UI + rollback on error.
- Ticket Card: compact glass card; click → right-side Drawer with details & actions (edit, reassign, delete).
- Create/Edit: modal or drawer form (title, description, status, assignee).
- Auth: login/register views; store token; attach to API calls.
- Lists at scale: virtualization for each column when item count is large; skeleton loading.
- UX polish: toasts, empty states, loading and error states; data-testid on interactive elements.
- Theming: dark + glassmorphism; subtle blur, elevation, gradients; accessible color contrast.
- Export/Import: buttons in header; export format choose CSV/JSON; import via file upload.
- Analytics: header badges/chips with counts by column + small panel by assignee.
Non-Goals in Phase 2
- Real-time collaboration (websockets), complex routing/queues, AI features, SSO/OAuth.
Next Actions
- Call design_agent for UI guidelines (dark glassmorphism, drawer patterns, high-density lists).
- Implement backend + frontend in parallel; wire APIs; ensure /api prefix and env vars used.
- Run testing_agent_v3 for end-to-end tests (skip drag-and-drop automation if unsupported).
Success Criteria
- Board loads with 5 columns; tickets draggable across columns and persist.
- Users can register/login; create/edit/delete/assign tickets.
- Analytics shows counts by status and assignee; export and import work with valid files.
- Smooth, modern dark glass UI; no red-screen errors; all interactive elements have data-testid.
User Stories
1) As a user, I can drag a ticket from Backlog to In Progress and see it persist on refresh.
2) As a user, I can open a ticket in a side drawer to edit title/description and save changes.
3) As a manager, I can assign a ticket to a teammate from the drawer.
4) As a user, I can export all tickets to CSV and re-import them after edits.
5) As a user, I can view counts per column and by assignee to understand workload.
6) As a user, I can register/login and only then access my workspace.
7) As a user, I get clear loading and error states when actions fail.

---------------------------------------------
Phase 3: Collaboration & Realtime (Post-MVP)
Objectives
- Enhance collaboration and visibility; enable realtime updates.
Implementation Steps
- WebSockets for live board updates; presence indicators; activity log per ticket.
- Mentions/comments in drawer; watchers; basic notifications (in-app).
- Advanced filters: priority, tags, due dates (adds fields + indexes).
- Bulk actions: multi-select, assign/move.
- Performance: indexing, pagination, aggressive virtualization.
Next Actions
- Add fields to Ticket; migrate existing data.
Success Criteria
- Changes on one client reflect in others within seconds; activity feed persists.
User Stories
1) As a user, I see ticket updates in realtime without refreshing.
2) As a user, I can @mention a teammate in a ticket comment.
3) As a lead, I can watch a ticket and receive in-app notifications.
4) As a user, I can filter tickets by tag/priority/due date.
5) As a manager, I can select multiple tickets and assign them together.

---------------------------------------------
Phase 4: Routing, Queues & Shift Management
Objectives
- Operational robustness similar to Pylon: routing rules, queues, shifts, SLAs.
Implementation Steps
- Queues: define queues per team; ticket intake endpoints.
- Routing rules: rule engine to auto-assign based on tags/load/shifts.
- Shift calendar: define shifts; capacity planning; time-zone support.
- SLA policy: timers, breach indicators, escalation rules.
Next Actions
- Design rule schema; add admin UI for rules/shifts.
Success Criteria
- New tickets auto-routed to correct queue/assignee honoring capacity and shifts.
User Stories
1) As an admin, I can define routing rules in the UI.
2) As a supervisor, I can configure team shifts and capacities.
3) As an agent, I see my queue and pickup suggestions.
4) As a manager, I see SLA timers and breach warnings on tickets.
5) As an admin, I can override routing manually when needed.

---------------------------------------------
Phase 5: AI Agents (LLM-Assisted)
Objectives
- Integrate AI to summarize, suggest replies, and route tickets.
Implementation Steps
- POC (required): test LLM call using Emergent LLM key; finalize prompts.
- Features: AI summary in drawer; suggested replies; auto-tagging and routing recommendations.
- Guardrails: human-in-the-loop approvals; cost tracking.
Next Actions
- Call integration_playbook_expert_v2 for LLM provider; build test_core.py; validate.
Success Criteria
- AI responses render quickly and accurately; users can accept/edit suggestions.
User Stories
1) As an agent, I can generate a summary of a ticket thread.
2) As an agent, I get suggested replies I can insert and edit.
3) As a lead, I see AI-proposed tags/priority with confidence.
4) As a supervisor, I can enable/disable AI features per team.
5) As an admin, I can view AI usage metrics and costs.

---------------------------------------------
Phase 6: Enterprise & Compliance
Objectives
- Hardening for scale and enterprise orgs.
Implementation Steps
- SSO/OAuth (Google/Microsoft), RBAC, audit logs, retention policies.
- Multi-tenant isolation, organization billing, rate limits.
- Backups, exports at org level; GDPR tooling.
Next Actions
- Plan data partitioning and org boundaries.
Success Criteria
- Secure SSO, clear audit trails, tenant isolation, predictable costs.
User Stories
1) As an admin, I can onboard users via SSO.
2) As a security officer, I can export audit logs for a time range.
3) As an org owner, I can see usage and manage billing.
4) As a privacy officer, I can configure data retention.
5) As a tenant, my data is isolated from other tenants.

---------------------------------------------
Global Success Criteria
- MVP (Phase 2) deployed with no red-screen errors; stable UX; all core flows pass testing_agent_v3.
- Clean separation of concerns; environment variables respected; all /api routes prefixed.
- Visual design meets dark glassmorphism standards; responsive and performant for large boards.

Immediate Next Actions
- Proceed to Phase 2 build: obtain design guidelines via design_agent, then implement backend + frontend, then run end-to-end tests.
- Expect 20–30 minutes for first working MVP build after design guidelines.