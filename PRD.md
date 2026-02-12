# TickFlow - Product Requirements Document (PRD)

## Executive Summary

TickFlow is an enterprise-grade, API-first ticket management platform designed for customer support operations. It provides intelligent ticket routing, multi-team collaboration, shift management, and comprehensive analytics capabilities.

---

## Table of Contents

1. [Current State](#current-state)
2. [Product Vision](#product-vision)
3. [Core Modules](#core-modules)
4. [Implementation Phases](#implementation-phases)
5. [Technical Architecture](#technical-architecture)
6. [API Specification](#api-specification)
7. [Data Models](#data-models)

---

## Current State (v0.1 - MVP)

### Completed Features

#### Authentication & Authorization
- [x] Google OAuth via Emergent Auth
- [x] Session management with JWT cookies
- [x] Domain-based access control (configurable)
- [x] User profile management

#### Ticket Management
- [x] Basic ticket CRUD operations
- [x] Kanban board with drag-and-drop (Todo, In Progress, Waiting, Review, Resolved)
- [x] List views (All, Open, Waiting, Closed)
- [x] Infinite scroll pagination
- [x] Ticket status transitions
- [x] Priority levels (low, medium, high, urgent)

#### Email Integration
- [x] Gmail OAuth connection
- [x] Email-to-ticket conversion
- [x] Query-based email sync filter
- [x] Mock email reply mode (for testing)
- [x] Email simulator for testing

#### User Interface
- [x] Dark/Light theme with persistence
- [x] Collapsible sidebar navigation
- [x] Responsive design (desktop/mobile)
- [x] Glassmorphism design language

#### Data Management
- [x] JSON/CSV export
- [x] JSON/CSV import
- [x] MongoDB persistence

---

## Product Vision

### Target Users
1. **Support Agents (L1)** - Front-line customer support
2. **Technical Support (L2)** - Escalation team for complex issues
3. **Team Leads** - Manage shifts, assignments, performance
4. **Administrators** - System configuration, user management
5. **External Systems** - API consumers for integrations

### Key Principles
1. **API-First** - Every feature accessible via REST API
2. **Extensible** - Custom fields, webhooks, integrations
3. **Intelligent** - AI-powered routing, suggestions, summaries
4. **Collaborative** - Real-time updates, mentions, internal notes
5. **Measurable** - Comprehensive analytics and reporting

---

## Core Modules

### Module 1: Advanced Ticket Management

#### 1.1 Ticket Attributes
| Attribute | Type | Description |
|-----------|------|-------------|
| `ticket_id` | string | Unique identifier (e.g., `TKT-001234`) |
| `title` | string | AI-generated or manual title |
| `description` | text | Full ticket content |
| `status` | enum | todo, in_progress, waiting, review, resolved, closed |
| `priority` | enum | low, medium, high, urgent |
| `source` | enum | email, manual, api, chat, phone |
| `domain` | string | Customer domain (extracted from email) |
| `job_id` | string | Related job/project ID (for integrations) |
| `tags` | array | Custom tags for categorization |
| `custom_fields` | object | Dynamic custom attributes |

#### 1.2 Conversation Threading
- Parent/child ticket relationships
- Email thread tracking
- Message-level operations (merge point, split point)
- Conversation timeline view

#### 1.3 Ticket Operations
| Operation | Description |
|-----------|-------------|
| **Merge** | Combine multiple tickets into one (at any message) |
| **Split** | Create new ticket from a message onwards |
| **Link** | Associate related tickets (blocks, blocked_by, related_to, duplicate_of) |
| **Clone** | Duplicate ticket for similar issues |
| **Snooze** | Temporarily hide until specified time |

#### 1.4 Assignment & Ownership
- Single assignee per ticket
- Team-based ownership (team inbox)
- Watchers/followers
- Assignment history

---

### Module 2: Routing & Automation

#### 2.1 Routing Methods
| Method | Description |
|--------|-------------|
| **Round Robin** | Distribute evenly across available agents |
| **Load-Based** | Assign to agent with lowest open ticket count |
| **Skill-Based** | Match ticket tags/domain to agent skills |
| **Sticky** | Same customer always goes to same agent |
| **Manual** | Team inbox, agents self-assign |

#### 2.2 Routing Rules Engine
```yaml
# Example Rule
name: "VIP Customer Routing"
conditions:
  - field: "customer.revenue_tier"
    operator: "equals"
    value: "enterprise"
  - field: "ticket.priority"
    operator: "in"
    value: ["high", "urgent"]
actions:
  - type: "assign_team"
    value: "l2_technical"
  - type: "set_priority"
    value: "urgent"
  - type: "add_tag"
    value: "vip"
  - type: "notify"
    value: "slack_channel_vip"
```

#### 2.3 Escalation Rules
- Time-based escalation (SLA breach warning)
- Manual escalation with reason
- Auto-escalation based on customer tier
- Escalation notifications

#### 2.4 Workflow Automation
| Trigger | Example Actions |
|---------|----------------|
| Ticket Created | Auto-assign, send acknowledgment, add tags |
| Status Changed | Notify customer, update SLA timer |
| SLA Breach | Escalate, notify manager, increase priority |
| Customer Reply | Reopen if closed, reset SLA, notify assignee |
| Agent Reply | Set to "waiting", start response timer |
| Ticket Resolved | Send survey, schedule follow-up |
| No Response 3 days | Auto-close with notification |

---

### Module 3: Team & Shift Management

#### 3.1 Organization Structure
```
Organization
├── Teams
│   ├── L1 Support (Non-Technical)
│   │   ├── Shift A (9am-5pm)
│   │   ├── Shift B (5pm-1am)
│   │   └── Shift C (1am-9am)
│   └── L2 Technical
│       ├── Backend Team
│       ├── Frontend Team
│       └── Infrastructure Team
└── User Groups
    ├── Managers
    ├── QA Reviewers
    └── Admins
```

#### 3.2 Shift Management
| Feature | Description |
|---------|-------------|
| Shift Definition | Name, start time, end time, timezone, days |
| Shift Assignment | Assign users to shifts |
| Shift Handoff | Auto-reassign tickets at shift end |
| Coverage View | Visual calendar of shift coverage |
| Overtime Tracking | Hours beyond scheduled shift |

#### 3.3 Leave Management
| Leave Type | Description |
|------------|-------------|
| Planned | Vacation, PTO (advance booking) |
| Sick | Unplanned sick leave |
| Half-day | Morning or afternoon off |
| Custom | Company-specific leave types |

Leave impacts:
- Excluded from round-robin
- Tickets reassigned (optional)
- Coverage alerts if understaffed

#### 3.4 Capacity Planning
- Tickets per agent per shift
- Real-time workload dashboard
- Understaffing alerts
- Historical capacity trends

---

### Module 4: Collaboration

#### 4.1 Internal Notes
- Private notes (not visible to customer)
- Rich text formatting
- File attachments
- @mentions with notifications

#### 4.2 Mentions & Notifications
| Mention Type | Notification |
|--------------|--------------|
| @user | Direct notification to user |
| @team | Notification to all team members |
| @here | Notification to online agents |
| @on-call | Notification to current shift agents |

#### 4.3 Activity Feed
- All ticket activities logged
- Filter by activity type
- User attribution
- Timestamp with timezone

---

### Module 5: Customer Management

#### 5.1 Customer Profile
| Attribute | Description |
|-----------|-------------|
| `customer_id` | Unique identifier |
| `email` | Primary email |
| `name` | Display name |
| `domain` | Company domain |
| `company` | Company name |
| `revenue_tier` | free, starter, pro, enterprise |
| `status` | active, churned, trial |
| `custom_fields` | Integration data (job_id, plan, etc.) |

#### 5.2 Customer Context
- All tickets from customer
- Interaction history
- Custom attributes from external DB
- Revenue/account status
- Health score

#### 5.3 External Database Integration
Connect your own database to enrich customer data:
```json
{
  "integration": "postgres",
  "connection": "postgresql://...",
  "sync": {
    "table": "customers",
    "key_field": "email",
    "fields": ["revenue", "plan", "job_count", "last_active"]
  }
}
```

---

### Module 6: Quality & Feedback

#### 6.1 Post-Resolution Survey
| Field | Description |
|-------|-------------|
| `cx_score` | 1-5 rating (CSAT) |
| `cx_reason` | Optional text feedback |
| `resolution_quality` | Was issue fully resolved? |
| `response_speed` | Satisfaction with speed |

#### 6.2 Quality Assurance
- Manager review queue
- QA scoring rubric
- Agent performance metrics
- Coaching notes

#### 6.3 SLA Management
| SLA Metric | Description |
|------------|-------------|
| First Response Time | Time to first agent reply |
| Resolution Time | Time to ticket closure |
| Response Time | Time between customer message and reply |
| Business Hours | SLA calculated in business hours only |

SLA Policies:
- Per-priority SLA targets
- Per-customer-tier overrides
- Pause on "waiting" status
- Breach notifications

---

### Module 7: Analytics & Reporting

#### 7.1 Real-time Dashboard
- Open tickets by status
- Tickets by priority
- Agent workload
- SLA health
- Incoming volume trend

#### 7.2 Historical Reports
| Report | Metrics |
|--------|---------|
| Volume | Tickets created, resolved, backlog |
| Performance | CSAT, SLA compliance, resolution rate |
| Agent | Tickets handled, avg resolution time, CSAT |
| Team | Comparison across teams/shifts |
| Customer | Top requesters, repeat issues |

#### 7.3 API Analytics
- Endpoint usage statistics
- Rate limit monitoring
- Integration health
- Webhook delivery stats

---

### Module 8: API & Integrations

#### 8.1 REST API Principles
- RESTful design
- JSON request/response
- API key authentication
- Rate limiting (1000 req/min default)
- Pagination (cursor-based)
- Filtering, sorting, field selection

#### 8.2 Webhook Events
| Event | Payload |
|-------|---------|
| `ticket.created` | Full ticket object |
| `ticket.updated` | Changed fields + ticket |
| `ticket.assigned` | Assignment details |
| `ticket.resolved` | Resolution details |
| `ticket.sla_breach` | SLA details |
| `message.created` | New message on ticket |
| `customer.created` | New customer |

#### 8.3 Integration Connectors
| Integration | Type | Description |
|-------------|------|-------------|
| Slack | Notification | Alerts, ticket cards |
| Email (SMTP) | Outbound | Send replies |
| Email (Webhook) | Inbound | Receive emails |
| PostgreSQL | Data | Customer enrichment |
| MongoDB | Data | Customer enrichment |
| REST API | Generic | Custom integrations |
| Zapier | Automation | No-code workflows |

---

## Implementation Phases

### Phase 1: Foundation (Current + Stabilization)
**Duration: 1 week**
**Goal: Stable base for building**

#### 1.1 Bug Fixes & Cleanup
- [ ] Fix sidebar submenu click behavior
- [ ] Verify email sync functionality
- [ ] Clean up test data
- [ ] Remove unused code

#### 1.2 Core Ticket Enhancements
- [ ] Ticket ID format (TKT-XXXXX)
- [ ] Domain extraction from email
- [ ] Source tracking (email, manual, api)
- [ ] Tags system (add, remove, filter)

#### 1.3 API Foundation
- [ ] API key authentication system
- [ ] Rate limiting middleware
- [ ] Standardized error responses
- [ ] API documentation (OpenAPI/Swagger)

**Deliverables:**
- Stable ticket management
- Working email-to-ticket flow
- Basic API authentication

---

### Phase 2: Team Structure & Assignment
**Duration: 1-2 weeks**
**Goal: Multi-team support with basic routing**

#### 2.1 User & Team Management
- [ ] Team CRUD (create L1, L2 teams)
- [ ] User-to-team assignment
- [ ] Team inbox view
- [ ] User roles (agent, lead, admin)

#### 2.2 Basic Routing
- [ ] Manual assignment
- [ ] Round-robin within team
- [ ] Team-based ticket queue
- [ ] Assignment history

#### 2.3 Collaboration Basics
- [ ] Internal notes on tickets
- [ ] @mention users
- [ ] Activity log

**Deliverables:**
- Team management UI
- Round-robin routing
- Internal notes

---

### Phase 3: Shift & Availability
**Duration: 1-2 weeks**
**Goal: Shift-aware operations**

#### 3.1 Shift Management
- [ ] Shift definition (time, days, timezone)
- [ ] User-to-shift assignment
- [ ] Shift calendar view
- [ ] Current shift indicator

#### 3.2 Leave Management
- [ ] Leave request/entry
- [ ] Leave calendar
- [ ] Auto-exclude from routing
- [ ] Coverage alerts

#### 3.3 Shift-Aware Routing
- [ ] Route only to on-shift agents
- [ ] Shift handoff automation
- [ ] Out-of-hours handling

**Deliverables:**
- Shift management UI
- Leave tracking
- Shift-aware routing

---

### Phase 4: Advanced Ticket Operations
**Duration: 1-2 weeks**
**Goal: Power user ticket features**

#### 4.1 Ticket Operations
- [ ] Merge tickets (with conversation combining)
- [ ] Split ticket (from message point)
- [ ] Link tickets (related, blocks, duplicate)
- [ ] Snooze tickets

#### 4.2 Conversation Enhancements
- [ ] Threaded conversation view
- [ ] Message-level actions
- [ ] Reply templates / canned responses
- [ ] Rich text editor

#### 4.3 Bulk Operations
- [ ] Bulk assign
- [ ] Bulk status change
- [ ] Bulk tag
- [ ] Bulk close

**Deliverables:**
- Merge/split/link functionality
- Improved conversation UI
- Bulk operations

---

### Phase 5: Customer & Context
**Duration: 1-2 weeks**
**Goal: Customer-centric view**

#### 5.1 Customer Management
- [ ] Customer profile page
- [ ] Customer ticket history
- [ ] Customer attributes (revenue_tier, status)
- [ ] Customer search

#### 5.2 External Data Integration
- [ ] Database connector framework
- [ ] PostgreSQL connector
- [ ] Field mapping configuration
- [ ] Sync scheduling

#### 5.3 Conversation Attributes
- [ ] Custom fields on tickets
- [ ] AI-generated title
- [ ] Auto-extracted metadata (domain, job_id)
- [ ] Customer context panel

**Deliverables:**
- Customer profiles
- External DB integration
- Custom ticket fields

---

### Phase 6: Automation & Rules
**Duration: 2 weeks**
**Goal: Intelligent automation**

#### 6.1 Rules Engine
- [ ] Rule builder UI
- [ ] Condition types (field, time, customer)
- [ ] Action types (assign, tag, notify, escalate)
- [ ] Rule testing/preview

#### 6.2 SLA Management
- [ ] SLA policy definition
- [ ] SLA timer tracking
- [ ] Breach warnings
- [ ] SLA reports

#### 6.3 Workflow Automation
- [ ] Trigger-based workflows
- [ ] Auto-assignment rules
- [ ] Escalation rules
- [ ] Auto-close rules

**Deliverables:**
- Visual rule builder
- SLA tracking
- Automated workflows

---

### Phase 7: Quality & Feedback
**Duration: 1 week**
**Goal: Quality measurement**

#### 7.1 Customer Feedback
- [ ] Post-resolution survey
- [ ] CSAT collection
- [ ] Feedback reason capture
- [ ] Survey customization

#### 7.2 Quality Assurance
- [ ] QA review queue
- [ ] Scoring rubric
- [ ] Manager review workflow
- [ ] Performance notes

**Deliverables:**
- CSAT surveys
- QA workflow

---

### Phase 8: Analytics & Reporting
**Duration: 1-2 weeks**
**Goal: Data-driven insights**

#### 8.1 Dashboards
- [ ] Real-time operations dashboard
- [ ] Team performance dashboard
- [ ] Agent performance dashboard
- [ ] Customer insights dashboard

#### 8.2 Reports
- [ ] Volume trends
- [ ] SLA compliance
- [ ] Agent leaderboard
- [ ] Customer analysis

#### 8.3 API Analytics
- [ ] Usage tracking
- [ ] Rate limit dashboard
- [ ] Webhook delivery stats

**Deliverables:**
- Analytics dashboards
- Exportable reports

---

### Phase 9: Advanced Integrations
**Duration: 1-2 weeks**
**Goal: External connectivity**

#### 9.1 Outbound Integrations
- [ ] Slack notifications
- [ ] Email (SMTP) sending
- [ ] Webhook delivery system

#### 9.2 Inbound Integrations
- [ ] Generic email webhook
- [ ] Mailgun integration
- [ ] API for external ticket creation

#### 9.3 Connector Framework
- [ ] Connector configuration UI
- [ ] Health monitoring
- [ ] Error handling/retry

**Deliverables:**
- Slack integration
- Email sending (real mode)
- Webhook system

---

### Phase 10: AI & Intelligence
**Duration: 2 weeks**
**Goal: AI-powered assistance**

#### 10.1 AI Features
- [ ] Auto-title generation
- [ ] Suggested responses
- [ ] Sentiment analysis
- [ ] Auto-categorization

#### 10.2 Smart Routing
- [ ] Intent detection
- [ ] Skill matching
- [ ] Priority prediction

**Deliverables:**
- AI-powered features
- Smart routing

---

## Technical Architecture

### Stack
| Layer | Technology |
|-------|------------|
| Frontend | React, TailwindCSS, Shadcn UI |
| Backend | FastAPI (Python) |
| Database | MongoDB |
| Cache | Redis (future) |
| Queue | Redis/Celery (future) |
| Search | MongoDB Atlas Search / Elasticsearch (future) |

### API Authentication
```
# API Key in header
Authorization: Bearer tk_live_xxxxxxxxxxxx

# Types
tk_live_* - Production keys
tk_test_* - Test/sandbox keys
```

### Database Collections
```
- users
- teams
- shifts
- leaves
- tickets
- messages
- customers
- rules
- sla_policies
- api_keys
- webhooks
- audit_logs
```

---

## API Specification (Preview)

### Tickets
```
GET    /api/v1/tickets              # List tickets
POST   /api/v1/tickets              # Create ticket
GET    /api/v1/tickets/:id          # Get ticket
PUT    /api/v1/tickets/:id          # Update ticket
DELETE /api/v1/tickets/:id          # Delete ticket
POST   /api/v1/tickets/:id/assign   # Assign ticket
POST   /api/v1/tickets/:id/merge    # Merge tickets
POST   /api/v1/tickets/:id/split    # Split ticket
POST   /api/v1/tickets/:id/link     # Link tickets
POST   /api/v1/tickets/:id/reply    # Add reply
POST   /api/v1/tickets/:id/note     # Add internal note
```

### Teams & Users
```
GET    /api/v1/teams                # List teams
POST   /api/v1/teams                # Create team
GET    /api/v1/users                # List users
PUT    /api/v1/users/:id/team       # Assign to team
```

### Shifts & Leaves
```
GET    /api/v1/shifts               # List shifts
POST   /api/v1/shifts               # Create shift
GET    /api/v1/leaves               # List leaves
POST   /api/v1/leaves               # Request leave
```

### Routing & Rules
```
GET    /api/v1/routing/rules        # List rules
POST   /api/v1/routing/rules        # Create rule
POST   /api/v1/routing/assign       # Trigger assignment
```

### Analytics
```
GET    /api/v1/analytics/summary    # Overview stats
GET    /api/v1/analytics/volume     # Volume trends
GET    /api/v1/analytics/sla        # SLA metrics
GET    /api/v1/analytics/agents     # Agent performance
```

---

## Data Models

### Ticket (Enhanced)
```javascript
{
  ticket_id: "TKT-001234",
  title: "Cannot deploy application",
  description: "Full ticket content...",
  status: "in_progress",
  priority: "high",
  source: "email",
  
  // Assignment
  assignee_id: "user_xxx",
  team_id: "team_l2_tech",
  watchers: ["user_yyy", "user_zzz"],
  
  // Customer
  customer_id: "cust_xxx",
  customer_email: "user@company.com",
  domain: "company.com",
  
  // Metadata
  tags: ["deployment", "urgent"],
  job_id: "job_abc123",
  custom_fields: {
    "product": "web-app",
    "version": "2.1.0"
  },
  
  // Email
  email_thread_id: "thread_xxx",
  email_message_ids: ["msg_1", "msg_2"],
  
  // Links
  linked_tickets: [
    { ticket_id: "TKT-001230", type: "related_to" },
    { ticket_id: "TKT-001235", type: "duplicate_of" }
  ],
  parent_ticket_id: null,  // If merged into another
  child_ticket_ids: [],    // If split from this
  
  // SLA
  sla_policy_id: "sla_enterprise",
  first_response_at: "2026-01-20T10:30:00Z",
  first_response_sla: "met",
  resolution_sla: "at_risk",
  
  // Quality
  cx_score: 5,
  cx_reason: "Fast and helpful!",
  qa_score: 4.5,
  
  // Timestamps
  created_at: "2026-01-20T10:00:00Z",
  updated_at: "2026-01-20T14:30:00Z",
  resolved_at: null,
  closed_at: null,
  snoozed_until: null
}
```

### User (Enhanced)
```javascript
{
  user_id: "user_xxx",
  email: "agent@company.com",
  name: "John Doe",
  role: "agent",  // agent, lead, admin
  
  // Team & Shift
  team_id: "team_l1",
  shift_id: "shift_morning",
  skills: ["billing", "technical"],
  
  // Status
  status: "online",  // online, away, offline
  on_leave: false,
  current_ticket_count: 5,
  max_tickets: 10,
  
  // Performance
  avg_resolution_time: 3600,
  avg_csat: 4.5,
  tickets_resolved_today: 12
}
```

### Customer
```javascript
{
  customer_id: "cust_xxx",
  email: "user@company.com",
  name: "Jane Smith",
  domain: "company.com",
  company: "Company Inc",
  
  // Attributes
  revenue_tier: "enterprise",  // free, starter, pro, enterprise
  status: "active",            // trial, active, churned
  mrr: 5000,
  
  // External data
  external_id: "ext_123",
  job_ids: ["job_1", "job_2"],
  custom_fields: {},
  
  // Stats
  total_tickets: 15,
  open_tickets: 2,
  avg_csat_given: 4.2,
  
  created_at: "2025-06-01T00:00:00Z",
  last_contact_at: "2026-01-20T10:00:00Z"
}
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| First Response Time | < 1 hour (business hours) |
| Resolution Time | < 24 hours |
| CSAT Score | > 4.5/5 |
| SLA Compliance | > 95% |
| Agent Utilization | 70-80% |
| API Uptime | 99.9% |

---

## Appendix

### A. Suggested Additional Features
1. **Knowledge Base Integration** - Link tickets to help articles
2. **Customer Portal** - Self-service ticket submission/tracking
3. **Mobile App** - Native iOS/Android for agents
4. **Real-time Collaboration** - Live typing indicators, presence
5. **Audit Logs** - Complete activity trail for compliance
6. **Multi-language Support** - i18n for global teams
7. **Sandbox Environment** - Test integrations safely

### B. Glossary
| Term | Definition |
|------|------------|
| SLA | Service Level Agreement |
| CSAT | Customer Satisfaction Score |
| L1/L2 | Support tiers (Level 1 = frontline, Level 2 = escalation) |
| Round Robin | Even distribution of work |
| Escalation | Moving ticket to higher support tier |

---

*Document Version: 2.1*
*Last Updated: February 12, 2026*
*Author: TickFlow Team*

---

## Quality Assurance Report (Feb 12, 2026)

### Test Execution Summary
A comprehensive 10-phase testing program was executed covering all 175 API endpoints and 20 frontend pages.

| Phase | Scope | Result |
|-------|-------|--------|
| Phase 1 | Navigation & Dashboard | ✅ Pass |
| Phase 2 | Ticket CRUD & Views | ✅ Pass |
| Phase 3 | Ticket Operations | ✅ Pass |
| Phase 4 | Team Management | ✅ Pass |
| Phase 5 | Customer Management | ✅ Pass |
| Phase 6 | Canned Responses & Feature Requests | ✅ Pass |
| Phase 7 | Leave Management & Analytics | ✅ Pass |
| Phase 8 | Admin, Settings & SLA | ✅ Pass |
| Phase 9 | Search, Custom Inboxes & CSAT | ✅ Pass |
| Phase 10 | End-to-End Workflows | ✅ Pass |

**Result:** 37/37 backend tests passed, 20/20 frontend pages verified, 15 bugs found and fixed.

### Bugs Fixed
- 9 frontend files: API response `{items:[...]}` handling
- Leave creation route: wrong arguments
- Feature requests: status/type field mismatches
- Search endpoint: missing db argument
- Feature requests MongoDB index: legacy conflict
- Settings export: response format handling

### Test Artifacts
| Artifact | Location |
|----------|----------|
| Test Plan | `/app/TEST_PLAN_PHASES.md` |
| Phase 1-6 Report | `/app/test_reports/iteration_19.json` |
| Phase 7-10 Report | `/app/test_reports/iteration_20.json` |
| Backend Tests | `/app/backend/tests/test_phase7_10_trinity.py` |
| Feature Index | `/app/FEATURES.md` |
| API Docs | `/api/docs` (Swagger), `/api/redoc` (ReDoc) |
