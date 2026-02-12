# Trinity / TickFlow - Comprehensive Test & Code Review Plan

## Architecture Overview
- **Backend**: FastAPI (Python) on port 8001, single uvicorn worker
- **Frontend**: React (CRA + craco) on port 3000, shadcn/ui components
- **Database**: MongoDB (pymongo sync + motor async)
- **Realtime**: Socket.IO (python-socketio)
- **Auth**: Emergent Auth (Google OAuth) + API keys
- **Rate Limiting**: SlowAPI with MongoDB storage
- **Production Target**: 2 load-balanced K8s pods, single cloud MongoDB

---

## PHASE 1: API Health & Backend Smoke Tests
**Goal**: Verify all API endpoints respond correctly and backend is stable.

### 1.1 Health Check & Basic Connectivity
- [x] Verify `/api/health` returns healthy
- [ ] Verify MongoDB connection is alive
- [ ] Verify all required collections exist

### 1.2 Authentication Flow
- [ ] Test `/api/auth/session` with valid/invalid session_id
- [ ] Test `/api/auth/me` with valid session cookie
- [ ] Test `/api/auth/me` without auth (expect 401)
- [ ] Test API key creation, listing, revocation
- [ ] Test API key authentication header flow

### 1.3 Ticket CRUD via API
- [ ] Create ticket via API
- [ ] Read ticket by ID
- [ ] Update ticket (status, priority, assignee)
- [ ] Delete ticket
- [ ] List tickets with pagination
- [ ] Verify ticket_id sequential generation (TKT-XXXXXX)

### 1.4 Team Management API
- [ ] Create team
- [ ] List teams
- [ ] Add/remove members
- [ ] Update team
- [ ] Delete team

### 1.5 Customer Management API
- [ ] Create customer
- [ ] List customers with pagination
- [ ] Update customer
- [ ] Merge customers
- [ ] Link emails to customer

### 1.6 All Other Endpoints (Smoke)
- [ ] Shifts CRUD
- [ ] Canned Responses CRUD
- [ ] Feature Requests CRUD
- [ ] Leave Management CRUD
- [ ] Webhooks CRUD
- [ ] Custom Inboxes/Filters
- [ ] SLA Policies
- [ ] Admin Settings
- [ ] Routing Rules
- [ ] CSAT
- [ ] Exports
- [ ] Search & Presence

---

## PHASE 2: UI Functional Testing (Playwright)
**Goal**: Test all UI flows as a real user would.

### 2.1 Login & Authentication UI
- [ ] Login page renders correctly
- [ ] Google OAuth button is present
- [ ] Auth callback flow works
- [ ] Session persistence after page refresh
- [ ] Logout flow

### 2.2 Dashboard & Navigation
- [ ] Dashboard loads with ticket stats
- [ ] Sidebar navigation works (all links)
- [ ] Theme toggle (dark/light) works
- [ ] Command palette (Cmd+K) opens/closes
- [ ] Keyboard shortcuts help (?) dialog

### 2.3 Ticket Management UI
- [ ] Create new ticket (modal form)
- [ ] Ticket list view loads
- [ ] Kanban board renders with correct columns
- [ ] Ticket card shows correct info
- [ ] Click ticket opens drawer
- [ ] Ticket detail drawer shows all fields
- [ ] Edit ticket in drawer (status, priority, assignee)
- [ ] Add internal note with @mention
- [ ] Activity timeline shows changes
- [ ] Tags add/remove
- [ ] Star/unstar tickets
- [ ] Drag-and-drop on Kanban board

### 2.4 Filtering & Custom Inboxes UI
- [ ] Filter builder opens
- [ ] Add/remove filter conditions
- [ ] AND/OR group logic
- [ ] Save filter as custom inbox
- [ ] Custom inbox appears in sidebar
- [ ] Share inbox with other users

### 2.5 Team Management UI
- [ ] Teams page renders
- [ ] Create team form
- [ ] Add members to team
- [ ] Edit team details
- [ ] Shift scheduling view

### 2.6 Admin Panel UI
- [ ] Admin page loads (settings, custom fields, routing rules, SLA)
- [ ] Custom fields CRUD
- [ ] Routing rules CRUD
- [ ] SLA policies configuration
- [ ] SLA escalation rules

### 2.7 Other Pages UI
- [ ] Customers page renders with list
- [ ] Feature requests page
- [ ] Canned responses page
- [ ] Leave management page
- [ ] Analytics page (charts render)
- [ ] Search results page
- [ ] Profile page
- [ ] CSAT public survey page

---

## PHASE 3: Production Readiness Code Review
**Goal**: Evaluate code for scalability, stability, and best practices.

### 3.1 Database Layer
- [ ] Sync pymongo vs async motor usage consistency
- [ ] Connection pooling configuration
- [ ] Index coverage for all query patterns
- [ ] Missing indexes for common queries
- [ ] Race conditions in counter operations (generate_ticket_id)
- [ ] Transaction usage for multi-document operations
- [ ] Query performance (N+1 queries, unbounded results)

### 3.2 Authentication & Security
- [ ] Session management vulnerabilities
- [ ] API key verification (bcrypt scan of ALL keys per request!)
- [ ] CORS configuration
- [ ] Input validation/sanitization
- [ ] Rate limiting adequacy
- [ ] WebSocket authentication security
- [ ] XSS prevention (bleach usage)
- [ ] SQL/NoSQL injection prevention

### 3.3 Scalability (2 K8s Pods)
- [ ] Distributed locking for background tasks
- [ ] Pub/sub for cross-instance WebSocket
- [ ] Session stickiness requirements
- [ ] Rate limiter shared state across pods
- [ ] File upload storage (local vs cloud)
- [ ] Background task coordination
- [ ] IMAP sync singleton concerns

### 3.4 Error Handling & Resilience
- [ ] Global exception handler adequacy
- [ ] Graceful shutdown implementation
- [ ] Database reconnection logic
- [ ] Webhook delivery retry logic
- [ ] Background task failure recovery

### 3.5 Code Quality
- [ ] Python linting (ruff)
- [ ] JavaScript linting (ESLint)
- [ ] Dead code identification
- [ ] Duplicate logic across routes
- [ ] Magic numbers and hardcoded values
- [ ] Logging quality and consistency
- [ ] Type annotations coverage
- [ ] Deprecated API usage (FastAPI on_event)

---

## PHASE 4: Edge Cases & Stress Testing
**Goal**: Find bugs through edge cases and boundary conditions.

### 4.1 Concurrent Operations
- [ ] Multiple ticket creates simultaneously
- [ ] Concurrent ticket updates (last-write-wins?)
- [ ] Bulk operations with large sets
- [ ] Race in round-robin assignment

### 4.2 Data Validation Edge Cases
- [ ] Very long titles/descriptions
- [ ] Special characters in all text fields
- [ ] Empty/null required fields
- [ ] Invalid enum values (status, priority)
- [ ] Duplicate ticket creation
- [ ] Large file uploads

### 4.3 Error Scenarios
- [ ] Invalid ticket IDs in operations
- [ ] Unauthorized access to protected routes
- [ ] Database connection failure handling
- [ ] Webhook delivery to unreachable URLs

---

## PHASE 5: Findings Report & Recommendations
**Goal**: Compile all findings into actionable report.

### Deliverables
- [ ] Bug list with severity ratings
- [ ] Code quality issues
- [ ] Security vulnerabilities
- [ ] Performance bottlenecks
- [ ] Production deployment recommendations
- [ ] Prioritized fix list
