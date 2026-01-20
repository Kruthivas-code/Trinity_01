# TickFlow Plan (Production-Ready Email-First Support System)

Problem Statement: Build a production-ready, email-first ticket management system with beautiful glassmorphic UI, 5-column kanban board (Backlog → To Do → In Progress → Review → Done), Gmail integration for real-time email ingestion and replies, multi-user collaboration, CRUD operations, analytics, export/import. Future: Customer data enrichment, AI agents, advanced routing, shift management.

Tech Stack: FastAPI + React + MongoDB + shadcn/ui + Gmail API + Google Cloud Pub/Sub

Vision: Rival Pylon/Zendesk with email as the primary support channel, intelligent threading, and unified inbox experience.

---------------------------------------------
Phase 1: Core Functionality POC (Skipped)
Status: ✅ COMPLETED
Objectives
- Skipped (Level 2 CRUD app). Proceeded directly to Phase 2.

---------------------------------------------
Phase 2: Main App Development (MVP)
Status: ✅ COMPLETED
Objectives
- Deliver a working, beautiful kanban app with drag-and-drop and persistence, multi-user auth with assignments, CRUD, analytics, export/import, and a sleek glassmorphism UI.

Implementation Completed
Backend (FastAPI + MongoDB)
- ✅ JWT auth with email/password (POST /api/auth/register, /api/auth/login)
- ✅ User management (GET /api/users, GET /api/users/me)
- ✅ Ticket CRUD (GET/POST/PUT/DELETE /api/tickets) with status/assignee filters
- ✅ Ticket reordering (POST /api/tickets/reorder) for drag-and-drop persistence
- ✅ Analytics endpoint (GET /api/analytics/summary) with counts by status and assignee
- ✅ Export functionality (GET /api/export?format=csv|json) with streaming
- ✅ Import functionality (POST /api/import) supporting CSV/JSON bulk upload
- ✅ serialize_doc helper for ObjectId/datetime conversion
- ✅ JWT protection on all ticket endpoints

Frontend (React + shadcn/ui)
- ✅ 5-column glassmorphism kanban board with responsive layout
- ✅ Drag-and-drop with dnd-kit (optimistic UI + backend persistence)
- ✅ Ticket cards with glassmorphic styling
- ✅ Side drawer for ticket details with edit/delete capabilities
- ✅ Create ticket modal with form validation
- ✅ Auth pages (login/register) with token storage
- ✅ Toast notifications (sonner) for user feedback
- ✅ Empty states and loading skeletons
- ✅ Analytics badges in header (total tickets, my tickets)
- ✅ Export/Import UI with file handling
- ✅ Dark theme with glassmorphism design system
- ✅ All interactive elements have data-testid attributes

Testing Results
- Backend: 100% (16/16 API tests passed)
- Frontend: 97% (33/34 tests passed)
- All Phase 2 user stories verified and working

Success Criteria: ✅ ALL MET
- ✅ Board loads with 5 columns; tickets persist across sessions
- ✅ Users can register/login; create/edit/delete/assign tickets
- ✅ Delete confirmation flow working (Delete → Cancel/Confirm → Deleted)
- ✅ Analytics shows live counts by status and assignee
- ✅ Export (JSON/CSV) and import work correctly
- ✅ Smooth, modern dark glass UI with no red-screen errors
- ✅ All interactive elements have data-testid for testing

User Stories: ✅ ALL COMPLETED
1) ✅ As a user, I can drag a ticket from Backlog to In Progress and see it persist on refresh.
2) ✅ As a user, I can open a ticket in a side drawer to edit title/description and save changes.
3) ✅ As a manager, I can assign a ticket to a teammate from the drawer.
4) ✅ As a user, I can export all tickets to CSV and re-import them after edits.
5) ✅ As a user, I can view counts per column and by assignee to understand workload.
6) ✅ As a user, I can register/login and only then access my workspace.
7) ✅ As a user, I get clear loading and error states when actions fail.

---------------------------------------------
Phase 3: Email Integration (Gmail API + Push Notifications)
Status: 🔄 IN PROGRESS - PRODUCTION-READY IMPLEMENTATION
Objectives
- Implement email as PRIMARY ticket creation channel using Gmail API
- Real-time email ingestion via Google Cloud Pub/Sub push notifications
- Native Gmail threading support for intelligent ticket grouping
- Reply capability directly from TickFlow using Gmail API
- Handle long email content with optimized UI
- Production-ready, scalable architecture (NOT MVP)

Architecture Overview
- Gmail OAuth: Authenticate support@emergent.sh with gmail.readonly, gmail.send, gmail.modify scopes
- Push Notifications: Google Cloud Pub/Sub → Webhook → TickFlow API (near-instant delivery)
- Email Processing: Parse headers, extract threading metadata, create/update tickets
- Threading Logic: Use Gmail's native threadId for intelligent grouping
- Reply System: Send via Gmail API with proper In-Reply-To and References headers
- UI Updates: Enhanced drawer for long email content, email-specific metadata on cards

Implementation Steps

Backend (FastAPI + MongoDB + Gmail API)
1. Gmail OAuth Integration
   - OAuth2 flow for support@emergent.sh authentication
   - Store refresh tokens securely in MongoDB (encrypted)
   - Token refresh mechanism for long-lived access
   - Endpoints: POST /api/gmail/auth/start, GET /api/gmail/auth/callback
   
2. Google Cloud Pub/Sub Setup
   - Configure Gmail push notifications to Pub/Sub topic
   - Create subscription pointing to TickFlow webhook
   - Endpoint: POST /api/gmail/webhook (receives push notifications)
   - Verify webhook authenticity (signature validation)
   
3. Email to Ticket Conversion
   - Parse email: sender, subject, body (plain text + HTML), headers
   - Extract threading metadata: Message-ID, In-Reply-To, References, threadId
   - Enhance Ticket model with email fields:
     * email_from (sender email address)
     * email_to (recipient list)
     * email_cc (CC list)
     * email_message_id (unique email identifier)
     * email_thread_id (Gmail's threadId for grouping)
     * email_in_reply_to (parent message ID)
     * email_references (thread chain)
     * email_body_plain (plain text content)
     * email_body_html (HTML content)
     * is_email_ticket (boolean flag)
     * channel (enum: 'email', 'manual')
   - Create ticket with status='backlog' by default
   - Endpoint: Internal function called by webhook handler
   
4. Threading Intelligence (Basic Rules)
   - Rule 1: Use Gmail's threadId to link related emails
   - Rule 2: If threadId matches existing ticket → Update ticket (add to thread)
   - Rule 3: If threadId has gap > 24 hours + subject change → Create new ticket
   - Rule 4: Store thread history in ticket document (array of messages)
   - Manual split option: PUT /api/tickets/{id}/split-thread
   
5. Reply Functionality via Gmail API
   - Endpoint: POST /api/tickets/{id}/reply
   - Compose reply with proper threading headers (In-Reply-To, References)
   - Send via Gmail API using support@emergent.sh credentials
   - Store sent reply in ticket history with timestamp
   - Mark email as replied in Gmail
   - Return success/failure with sent message metadata
   
6. Email Polling Fallback (Backup)
   - Background job polls Gmail History API every 60s as backup
   - Only processes changes since last historyId (efficient)
   - Ensures no emails are missed if push fails
   - Endpoint: Background worker, not exposed via API

Frontend (React + Enhanced UI for Email)
1. Gmail OAuth Flow
   - "Connect Gmail" button in settings
   - OAuth popup window for Google authentication
   - Success/error states with toast notifications
   - Display connected email address in settings
   
2. Enhanced Ticket Card (Email-Aware)
   - Show email icon badge if ticket is from email
   - Display sender email address prominently
   - Show "3 messages" badge for threaded tickets
   - Timestamp of latest email in thread
   - Visual indicator for unread vs replied status
   
3. Enhanced Drawer for Long Emails
   - Tabbed interface: "Details" | "Email Thread" | "History"
   - Email Thread tab:
     * Scrollable container for long content
     * Message list showing sender, timestamp, preview
     * Expand individual messages to see full content
     * HTML email rendering with sanitization
     * Preserve formatting (bold, links, lists)
     * "Show more" for very long emails (>1000 words)
   - Reply composer:
     * Rich text editor (simple formatting: bold, italic, links)
     * "Reply" and "Reply All" buttons
     * CC/BCC fields (collapsible)
     * Send button with loading state
     * Draft autosave (optional)
   
4. Email-Specific Metadata Display
   - Show sender email, recipients, CC in drawer header
   - Display email received timestamp
   - Show Gmail labels/tags if any
   - Link to view in Gmail (external link icon)
   
5. Settings Page for Gmail
   - Connect/Disconnect Gmail account
   - View connected email address
   - Test connection button
   - Configure default ticket status for email tickets
   - Configure auto-reply templates (future)

Data Model Updates
Ticket Schema Enhancement:
```javascript
{
  _id: ObjectId,
  title: String,  // Email subject for email tickets
  description: String,  // Email body (plain text fallback)
  status: String,  // backlog, todo, in_progress, review, done
  assignee_id: String (nullable),
  priority: String,  // low, medium, high, urgent
  order: Number,
  created_at: DateTime,
  updated_at: DateTime,
  created_by: String,
  
  // Email-specific fields (NEW)
  channel: String,  // 'email' or 'manual'
  is_email_ticket: Boolean,
  email_from: String,  // sender@example.com
  email_to: [String],  // [support@emergent.sh]
  email_cc: [String],
  email_message_id: String,  // <unique-id@gmail.com>
  email_thread_id: String,  // Gmail threadId
  email_in_reply_to: String,
  email_references: [String],
  email_body_plain: String,  // Full plain text
  email_body_html: String,  // Full HTML
  email_thread: [{  // Thread history
    message_id: String,
    from: String,
    to: [String],
    subject: String,
    body_plain: String,
    body_html: String,
    timestamp: DateTime,
    direction: String  // 'inbound' or 'outbound'
  }]
}
```

GmailAuth Collection (NEW):
```javascript
{
  _id: ObjectId,
  email: String,  // support@emergent.sh
  access_token: String (encrypted),
  refresh_token: String (encrypted),
  token_expiry: DateTime,
  scopes: [String],
  created_at: DateTime,
  updated_at: DateTime,
  last_history_id: String  // For History API polling
}
```

Integration Requirements
1. Google Cloud Project Setup (User will do):
   - Create project at console.cloud.google.com
   - Enable Gmail API
   - Enable Cloud Pub/Sub API
   - Create OAuth 2.0 credentials (Web application)
   - Add authorized redirect URI: https://tickflow-6.preview.emergentagent.com/api/gmail/auth/callback
   - Create Pub/Sub topic and subscription
   - Configure Gmail push notifications to topic
   
2. Environment Variables (NEW):
   - GOOGLE_CLIENT_ID (from OAuth credentials)
   - GOOGLE_CLIENT_SECRET (from OAuth credentials)
   - GOOGLE_REDIRECT_URI (callback URL)
   - PUBSUB_TOPIC (Pub/Sub topic name)
   - PUBSUB_SUBSCRIPTION (subscription name)
   - ENCRYPTION_KEY (for token encryption)

Dependencies to Install
Backend:
- google-auth (OAuth flow)
- google-auth-oauthlib (OAuth helpers)
- google-auth-httplib2 (HTTP transport)
- google-api-python-client (Gmail API client)
- google-cloud-pubsub (Pub/Sub client)
- cryptography (token encryption)
- beautifulsoup4 (HTML email parsing)
- html2text (HTML to plain text conversion)

Frontend:
- react-quill or @tiptap/react (rich text editor for replies)
- dompurify (HTML sanitization for email display)
- react-markdown (optional, for plain text formatting)

Testing Strategy
Backend:
- Unit tests for email parsing logic
- Mock Gmail API responses
- Test threading rules with various scenarios
- Test reply formatting with proper headers
- Verify webhook signature validation
- Test token refresh mechanism

Frontend:
- Test email thread display with long content
- Test reply composer with validation
- Test OAuth flow (manual)
- Test email-specific card rendering
- Verify HTML sanitization prevents XSS

Success Criteria
- ✅ OAuth flow completes successfully, tokens stored securely
- ✅ Push notifications received within 1 second of email arrival
- ✅ Emails automatically create tickets with all metadata
- ✅ Threading works: related emails grouped correctly
- ✅ Long email content (5000+ words) displays smoothly in drawer
- ✅ Replies sent from TickFlow appear in Gmail sent folder
- ✅ Recipients receive replies from support@emergent.sh
- ✅ Email threads display chronologically with expand/collapse
- ✅ No performance degradation with email processing
- ✅ Fallback polling works if push notifications fail

User Stories
1) As a support agent, I receive an email at support@emergent.sh and see it as a ticket in TickFlow within 1 second
2) As an agent, I can read the full email content in the drawer, even if it's 10 pages long
3) As an agent, I can reply to a ticket and the customer receives it from support@emergent.sh
4) As an agent, I see all emails in the same Gmail thread grouped under one ticket
5) As a customer, when I reply to a support email, my reply appears in the existing ticket (not a new one)
6) As an agent, I can see sender email, timestamp, and thread history for context
7) As an agent, I can manually split a thread if Gmail grouped unrelated issues together
8) As an admin, I can connect/disconnect the Gmail account from settings

Non-Goals in Phase 3
- Customer database enrichment (postponed to Phase 3B)
- AI-powered email summarization (Phase 5)
- Sentiment analysis (Phase 5)
- Auto-assignment based on email content (Phase 4)
- Attachment handling (future - requires external storage)
- Email templates/canned responses (future)

Next Actions
1. Call integration_playbook_expert_v2 for Gmail API integration playbook
2. Update backend: Add Gmail OAuth endpoints, webhook handler, email parsing
3. Update frontend: Add OAuth flow, enhanced drawer, reply composer
4. Install required dependencies (google-api-python-client, etc.)
5. Test with real emails to support@emergent.sh
6. Verify threading logic with multiple scenarios
7. Test reply functionality end-to-end
8. Run comprehensive testing via testing_agent_v3

---------------------------------------------
Phase 3B: Customer Data Enrichment (Postponed)
Status: ⏸️ POSTPONED
Objectives
- Enrich tickets with customer metadata from external database
- Display LTV, refund history, ticket history for prioritization
- Auto-tagging based on customer segment

Notes
- Postponed per user request - database integration complex
- Will implement after email integration is stable
- Requires API endpoint or direct DB connection to customer database

---------------------------------------------
Phase 4: Advanced Collaboration & Realtime
Status: 📋 PLANNED
Objectives
- Enhance collaboration and visibility; enable realtime updates
- Advanced filtering, bulk actions, comments/mentions

Implementation Steps
- WebSockets for live board updates; presence indicators
- Comments/mentions in drawer; watchers; notifications
- Advanced filters: priority, tags, due dates
- Bulk actions: multi-select, assign/move
- Performance: indexing, pagination, virtualization

User Stories
1) As a user, I see ticket updates in realtime without refreshing
2) As a user, I can @mention a teammate in a ticket comment
3) As a lead, I can watch a ticket and receive in-app notifications
4) As a user, I can filter tickets by tag/priority/due date
5) As a manager, I can select multiple tickets and assign them together

---------------------------------------------
Phase 5: Routing, Queues & Shift Management
Status: 📋 PLANNED
Objectives
- Operational robustness similar to Pylon: routing rules, queues, shifts, SLAs

Implementation Steps
- Queues: define queues per team; ticket intake endpoints
- Routing rules: rule engine to auto-assign based on tags/load/shifts
- Shift calendar: define shifts; capacity planning; time-zone support
- SLA policy: timers, breach indicators, escalation rules

User Stories
1) As an admin, I can define routing rules in the UI
2) As a supervisor, I can configure team shifts and capacities
3) As an agent, I see my queue and pickup suggestions
4) As a manager, I see SLA timers and breach warnings on tickets
5) As an admin, I can override routing manually when needed

---------------------------------------------
Phase 6: AI Agents (LLM-Assisted)
Status: 📋 PLANNED
Objectives
- Integrate AI to summarize emails, suggest replies, and route tickets

Implementation Steps
- POC: test LLM call using Emergent LLM key; finalize prompts
- Features: AI email summary in drawer; suggested replies; auto-tagging
- Guardrails: human-in-the-loop approvals; cost tracking

User Stories
1) As an agent, I can generate a summary of a long email thread
2) As an agent, I get suggested replies I can insert and edit
3) As a lead, I see AI-proposed tags/priority with confidence
4) As a supervisor, I can enable/disable AI features per team
5) As an admin, I can view AI usage metrics and costs

---------------------------------------------
Phase 7: Enterprise & Compliance
Status: 📋 PLANNED
Objectives
- Hardening for scale and enterprise orgs

Implementation Steps
- SSO/OAuth (Google/Microsoft), RBAC, audit logs
- Multi-tenant isolation, organization billing, rate limits
- Backups, exports at org level; GDPR tooling

User Stories
1) As an admin, I can onboard users via SSO
2) As a security officer, I can export audit logs for a time range
3) As an org owner, I can see usage and manage billing
4) As a privacy officer, I can configure data retention
5) As a tenant, my data is isolated from other tenants

---------------------------------------------
Global Success Criteria
- Phase 2 MVP: ✅ COMPLETED - Deployed with no red-screen errors; stable UX; all core flows tested
- Phase 3 Email Integration: 🔄 IN PROGRESS - Production-ready Gmail integration with push notifications
- Clean separation of concerns; environment variables respected; all /api routes prefixed
- Visual design meets dark glassmorphism standards; responsive and performant
- Production-ready code: error handling, logging, monitoring, security best practices

Current Status
- Phase 2: ✅ COMPLETED (100% backend, 97% frontend)
- Phase 3: 🔄 STARTING NOW - Email integration with Gmail API
- Application URL: https://tickflow-6.preview.emergentagent.com

Immediate Next Actions
1. Get Gmail API integration playbook from integration_playbook_expert_v2
2. Implement Gmail OAuth flow (backend + frontend)
3. Set up webhook endpoint for Pub/Sub push notifications
4. Implement email parsing and ticket creation logic
5. Add threading intelligence with Gmail threadId
6. Build reply functionality using Gmail API
7. Update UI: enhanced drawer, email thread display, reply composer
8. Test end-to-end with real emails to support@emergent.sh
9. Deploy and verify production readiness
