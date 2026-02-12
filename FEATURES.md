# Trinity - Enterprise Ticket Management Platform

## Complete Feature Index & Documentation

**Version:** 2.1.0  
**Last Updated:** February 12, 2026  
**Tech Stack:** React + FastAPI + MongoDB + Socket.IO  
**Test Status:** All 10 phases passed — 15 bugs found and fixed  

---

## Table of Contents

1. [Feature Overview](#1-feature-overview)
2. [Authentication & Security](#2-authentication--security)
3. [Ticket Management](#3-ticket-management)
4. [Email Integration](#4-email-integration)
5. [Team & User Management](#5-team--user-management)
6. [Shift & Leave Management](#6-shift--leave-management)
7. [Routing & Assignment](#7-routing--assignment)
8. [Customer Management](#8-customer-management)
9. [Collaboration & Communication](#9-collaboration--communication)
10. [CSAT & Quality](#10-csat--quality)
11. [Canned Responses](#11-canned-responses)
12. [Analytics & Reporting](#12-analytics--reporting)
13. [Search](#13-search)
14. [Real-time Features](#14-real-time-features)
15. [SLA Management](#15-sla-management)
16. [Feature Requests](#16-feature-requests)
17. [Admin & Settings](#17-admin--settings)
18. [Webhooks & Integrations](#18-webhooks--integrations)
19. [Data Export & Import](#19-data-export--import)
20. [API Reference](#20-api-reference)

---

## 1. Feature Overview

| Category | Features | Status | Tested |
|----------|----------|--------|--------|
| Tickets | CRUD, Kanban, Status, Priority, Tags, Merge, Split, Link | ✅ Complete | ✅ Phase 2-3 |
| Email | Gmail OAuth, Sync, Threading, Replies, Webhooks | ✅ Complete | ⏳ Needs Gmail |
| Teams | Create, Manage, Members, Escalation Levels | ✅ Complete | ✅ Phase 4 |
| Shifts | Define, Assign, Shift-aware routing | ✅ Complete | ✅ Phase 8 |
| Leave | Request, Calendar, Coverage | ✅ Complete | ✅ Phase 7 |
| Routing | Round-robin, Rules engine, Auto-assign | ✅ Complete | ✅ Phase 8 |
| Customers | Profiles, B2B detection, Linked emails | ✅ Complete | ✅ Phase 5 |
| CSAT | Surveys, Ratings, Analytics | ✅ Complete | ✅ Phase 10 |
| Canned Responses | Templates, Placeholders, Shortcodes | ✅ Complete | ✅ Phase 6 |
| Analytics | Overview, Agent stats, Trends | ✅ Complete | ✅ Phase 7 |
| Real-time | WebSocket, Presence, Typing indicators | ✅ Complete | ✅ Phase 1 |
| Webhooks | Subscriptions, Events, Logs | ✅ Complete | ✅ Phase 8 |
| Search | Full-text, Suggestions, Advanced filters | ✅ Complete | ✅ Phase 9 |
| Feature Requests | Track, Vote, Link tickets | ✅ Complete | ✅ Phase 6 |
| Admin & Settings | Custom fields, Routing rules, SLA, Export | ✅ Complete | ✅ Phase 8 |

---

## 2. Authentication & Security

### 2.1 Authentication Methods
| Method | Description | Endpoint |
|--------|-------------|----------|
| Google OAuth | Via Emergent Auth provider | `POST /api/auth/session` |
| API Keys | For programmatic access | `POST /api/auth/api-keys` |
| Session Cookies | JWT-based sessions | Automatic |

### 2.2 Authorization
| Role | Permissions |
|------|-------------|
| `agent` | View/manage own tickets, use canned responses |
| `team_lead` | Manage team, view team analytics |
| `manager` | Cross-team access, all analytics |
| `admin` | Full system access, settings, webhooks |

### 2.3 Security Features
- Rate limiting (1000 req/hour, 100 req/minute)
- Request ID tracing
- HTML sanitization (XSS prevention)
- CORS configuration
- Session expiry (30 days)

### 2.4 API Endpoints
```
POST   /api/auth/session          - Create session from OAuth
GET    /api/auth/me               - Get current user
POST   /api/auth/logout           - End session
POST   /api/auth/api-keys         - Create API key
GET    /api/auth/api-keys         - List API keys
DELETE /api/auth/api-keys/{id}    - Revoke API key
```

---

## 3. Ticket Management

### 3.1 Ticket Statuses
| Status | Description | Color |
|--------|-------------|-------|
| `todo` | New, unassigned | Slate |
| `in_progress` | Being worked on | Blue |
| `waiting` | Awaiting customer response | Amber |
| `review` | Pending QA/approval | Purple |
| `resolved` | Issue fixed | Emerald |
| `closed` | Auto-closed after 24h resolved | - |

### 3.2 Priority Levels
| Priority | SLA Impact |
|----------|------------|
| `low` | Standard response time |
| `medium` | Default priority |
| `high` | Expedited handling |
| `urgent` | Immediate attention |

### 3.3 Ticket Operations

#### Merge
Combine multiple tickets into one, preserving all messages.
- Messages from merged tickets are color-coded
- Original ticket IDs preserved for reference
- Unmerge capability available

#### Split
Create a new ticket from a specific message onward.
- Original ticket retains earlier messages
- New ticket gets split messages
- Linked automatically

#### Link
Associate related tickets with relationship types:
- `related_to` - Similar or connected issues
- `blocks` - Must be resolved first
- `blocked_by` - Waiting on another ticket
- `duplicate_of` - Same issue reported

### 3.4 Tags System
- Add/remove tags per ticket
- Filter by tags
- Auto-suggestions from existing tags
- Bulk tag operations

### 3.5 Kanban Board
- Drag-and-drop between columns
- Status-based columns
- Ticket ordering/reorder
- Quick actions on cards

### 3.6 API Endpoints
```
GET    /api/tickets                    - List all tickets
POST   /api/tickets                    - Create ticket
GET    /api/tickets/{id}               - Get ticket details
PUT    /api/tickets/{id}               - Update ticket
DELETE /api/tickets/{id}               - Delete ticket
POST   /api/tickets/reorder            - Reorder tickets
GET    /api/tickets/starred            - Starred tickets
GET    /api/tickets/{id}/changelog     - Audit log
GET    /api/tickets/{id}/metadata      - Extended metadata
POST   /api/tickets/{id}/tags          - Add tags
DELETE /api/tickets/{id}/tags/{tag}    - Remove tag
POST   /api/tickets/{id}/merge         - Merge tickets
POST   /api/tickets/{id}/unmerge/{src} - Unmerge ticket
POST   /api/tickets/{id}/split         - Split ticket
POST   /api/tickets/{id}/link          - Link tickets
DELETE /api/tickets/{id}/unlink/{tgt}  - Unlink tickets
GET    /api/tickets/{id}/merge-suggestions - Auto-merge suggestions
```

---

## 4. Email Integration

### 4.1 Gmail Integration
- OAuth 2.0 connection
- Automatic email-to-ticket conversion
- Configurable sync query filter
- Push notifications via webhook (optional)
- Manual sync trigger

### 4.2 Email Threading
Multiple fallback strategies for thread detection:
1. Gmail Thread ID matching
2. In-Reply-To header matching
3. References header matching
4. Sent reply Message-ID lookup

### 4.3 Email Replies
- Rich text email composition
- Sends via Gmail API
- Tracks outgoing messages
- Updates ticket status automatically

### 4.4 Email Settings
| Setting | Description |
|---------|-------------|
| `sync_query` | Gmail search filter (e.g., `in:inbox`) |
| `auto_sync` | Enable/disable automatic sync |
| `sync_interval` | Seconds between syncs (default: 60) |

### 4.5 API Endpoints
```
GET    /api/gmail/status               - Connection status
GET    /api/gmail/connect              - Initiate OAuth
GET    /api/auth/gmail/callback        - OAuth callback
POST   /api/gmail/disconnect           - Disconnect Gmail
GET    /api/gmail/emails               - List inbox emails
GET    /api/gmail/email/{id}           - Get email details
POST   /api/gmail/create-ticket/{id}   - Manual ticket creation
POST   /api/gmail/sync                 - Trigger manual sync
GET    /api/settings/email             - Get email settings
PUT    /api/settings/email             - Update settings
POST   /api/tickets/{id}/reply         - Send email reply
GET    /api/tickets/{id}/replies       - Get email replies
```

---

## 5. Team & User Management

### 5.1 Team Structure
```
Organization
├── L1 Support (escalation_level: L1)
│   └── Members: Agent A, Agent B, Agent C
├── L2 Technical (escalation_level: L2)
│   └── Members: Senior Dev, Tech Lead
└── L3 Specialist (escalation_level: L3)
    └── Members: Expert, Manager
```

### 5.2 Team Features
- Escalation level assignment (L1, L2, L3)
- Team inbox view
- Member management
- Round-robin index tracking
- Default team assignment

### 5.3 User Roles
| Role | Can Manage Teams | Can Admin | API Keys |
|------|-----------------|-----------|----------|
| agent | No | No | Yes |
| team_lead | Own team | No | Yes |
| manager | All teams | No | Yes |
| admin | All teams | Yes | Yes |

### 5.4 API Endpoints
```
GET    /api/users                      - List all users
GET    /api/users/me                   - Current user profile
PUT    /api/users/me/preferences       - Update preferences
PUT    /api/users/{id}/role            - Update user role
POST   /api/teams                      - Create team
GET    /api/teams                      - List teams
GET    /api/teams/{id}                 - Get team details
PUT    /api/teams/{id}                 - Update team
DELETE /api/teams/{id}                 - Delete team
POST   /api/teams/{id}/members         - Add member
DELETE /api/teams/{id}/members/{uid}   - Remove member
GET    /api/teams/{id}/tickets         - Team inbox
```

---

## 6. Shift & Leave Management

### 6.1 Shift Definition
| Field | Description |
|-------|-------------|
| `name` | Shift name (e.g., "Morning Shift") |
| `start_time` | HH:MM format (e.g., "09:00") |
| `end_time` | HH:MM format (e.g., "17:00") |
| `days_of_week` | Array of days [1-7, Mon=1] |
| `team_id` | Associated team |
| `timezone` | Default: Asia/Kolkata |

### 6.2 Shift-Aware Features
- On-shift indicator in UI
- Routing only to on-shift agents
- Shift-start auto-assignment
- Auto-reassign on ticket reopen (if original assignee off-shift)

### 6.3 Leave Management
| Leave Type | Description |
|------------|-------------|
| `annual` | Vacation/PTO |
| `sick` | Sick leave |
| `personal` | Personal time |
| `work_from_home` | Remote work |
| `other` | Custom |

### 6.4 Leave Features
- Calendar view
- Conflict detection
- Coverage alerts
- Automatic routing exclusion

### 6.5 API Endpoints
```
POST   /api/shifts                     - Create shift
GET    /api/shifts                     - List all shifts
GET    /api/shifts/team/{id}           - Team shifts
PUT    /api/shifts/{id}                - Update shift
DELETE /api/shifts/{id}                - Delete shift
POST   /api/users/{id}/shifts          - Assign user to shift
GET    /api/users/{id}/shifts          - User's shifts
DELETE /api/users/{id}/shifts/{sid}    - Remove shift assignment
GET    /api/teams/{id}/on-shift        - Who's on shift now
GET    /api/teams/{id}/schedule        - Team schedule

POST   /api/leaves                     - Create leave request
GET    /api/leaves                     - List leaves
GET    /api/leaves/{id}                - Get leave details
PUT    /api/leaves/{id}                - Update leave
DELETE /api/leaves/{id}                - Delete leave
GET    /api/leaves/types               - Available leave types
GET    /api/leaves/calendar/{y}/{m}    - Monthly calendar
GET    /api/leaves/conflicts           - Detect conflicts
GET    /api/leaves/summary/{uid}       - User leave summary
```

---

## 7. Routing & Assignment

### 7.1 Routing Methods
| Method | Description |
|--------|-------------|
| Round Robin | Equal distribution among on-shift agents |
| Manual | Self-assign from team queue |
| Rule-based | Automated based on conditions |
| Escalation | Auto-route based on escalation level |

### 7.2 Routing Rules Engine
```json
{
  "name": "VIP Customer Routing",
  "conditions": [
    {"field": "domain", "operator": "equals", "value": "enterprise.com"},
    {"field": "priority", "operator": "in", "value": ["high", "urgent"]}
  ],
  "actions": {
    "assign_team": "l2_technical",
    "set_priority": "urgent",
    "add_tag": "vip"
  },
  "is_active": true,
  "priority": 100
}
```

### 7.3 Supported Operators
| Operator | Description |
|----------|-------------|
| `equals` | Exact match |
| `not_equals` | Not equal |
| `contains` | Substring match |
| `not_contains` | No substring |
| `starts_with` | Prefix match |
| `ends_with` | Suffix match |
| `in` | In list |

### 7.4 Escalation
- Manual escalation with reason
- Auto-escalation based on rules
- Team assignment follows escalation level
- Notification to new assignee

### 7.5 API Endpoints
```
POST   /api/tickets/{id}/assign        - Assign ticket
POST   /api/tickets/{id}/escalate      - Escalate ticket
GET    /api/tickets/{id}/assignment-options - Get options
POST   /api/routing/auto-assign        - Trigger auto-assign
POST   /api/tickets/{id}/route         - Apply routing rules
GET    /api/admin/routing-rules        - List rules
POST   /api/admin/routing-rules        - Create rule
PUT    /api/admin/routing-rules/{id}   - Update rule
DELETE /api/admin/routing-rules/{id}   - Delete rule
POST   /api/admin/routing-rules/test   - Test a rule
```

---

## 8. Customer Management

### 8.1 Customer Profile
| Field | Description |
|-------|-------------|
| `customer_id` | Auto-generated (CUST-XXXXXX) |
| `name` | Customer name |
| `primary_email` | Main email |
| `linked_emails` | Additional emails |
| `company_name` | Auto-detected or manual |
| `company_domain` | Extracted from email |
| `customer_type` | `b2b` or `b2c` |
| `priority_level` | `standard`, `priority`, `vip` |
| `net_payments` | Total revenue |
| `tags` | Custom tags |
| `notes` | Internal notes |

### 8.2 B2B Detection
Automatic detection based on email domain:
- Common B2C domains (gmail.com, yahoo.com, etc.) = B2C
- Corporate domains = B2B with company name extraction

### 8.3 Customer Features
- Automatic customer creation from email
- Link multiple emails to one customer
- Customer merge
- All tickets from customer view
- Related tickets detection

### 8.4 API Endpoints
```
GET    /api/customers                  - List customers
GET    /api/customers/b2b-prospects    - B2B prospects only
GET    /api/customers/{id}             - Customer details
POST   /api/customers                  - Create customer
PUT    /api/customers/{id}             - Update customer
POST   /api/customers/{id}/link-email  - Link email
DELETE /api/customers/{id}/unlink-email/{email} - Unlink email
POST   /api/customers/merge            - Merge customers
GET    /api/customers/{id}/tickets     - Customer's tickets
GET    /api/tickets/by-email/{email}   - Tickets by email
GET    /api/tickets/{id}/related       - Related tickets
```

---

## 9. Collaboration & Communication

### 9.1 Internal Notes
- Private notes (not visible to customer)
- Rich text formatting
- @mentions with notifications
- Activity type: `internal_note`

### 9.2 Customer Replies
- Email replies via Gmail
- Thread preserved
- Activity type: `reply` or `customer_reply`

### 9.3 @Mentions
Mention format: `@[User Name](user_id)`
- Creates notification for mentioned user
- Adds user to "mentioned" tickets view
- Visual indicator on ticket cards

### 9.4 Activity Feed
Tracks all changes:
- Status changes
- Priority changes
- Assignments
- Tags added/removed
- Notes/replies added
- Escalations
- Merges/splits/links

### 9.5 API Endpoints
```
POST   /api/tickets/{id}/notes         - Add note/reply
GET    /api/tickets/{id}/notes         - Get conversation
GET    /api/tickets/{id}/activity      - Get activity log
GET    /api/tickets/{id}/activity-feed - Formatted feed
GET    /api/notifications              - User notifications
PUT    /api/notifications/{id}/read    - Mark as read
```

---

## 10. CSAT & Quality

### 10.1 CSAT Survey Flow
1. Ticket resolved
2. Send CSAT survey via email
3. Customer clicks rating (1-5 stars)
4. Optional feedback text
5. Rating linked to ticket

### 10.2 CSAT Features
- Secure token-based rating links
- Anti-prefetch protection (POST required)
- 7-day expiry on survey links
- Low CSAT alerts (rating ≤ 2)
- Manager notifications

### 10.3 Rating Scale
| Stars | Label |
|-------|-------|
| 1 | Terrible |
| 2 | Poor |
| 3 | Okay |
| 4 | Good |
| 5 | Excellent |

### 10.4 CSAT Analytics
- Average rating
- Rating distribution
- Trend over time
- Per-agent performance
- Low CSAT ticket list

### 10.5 API Endpoints
```
POST   /api/csat/send/{ticket_id}      - Send survey
GET    /api/csat/check/{token}         - Check token status
POST   /api/csat/rate/{token}          - Submit rating
POST   /api/csat/{response_id}/feedback - Add feedback
GET    /api/csat/ticket/{ticket_id}    - Get ticket CSAT
GET    /api/csat/analytics             - CSAT analytics
```

---

## 11. Canned Responses

### 11.1 Response Structure
| Field | Description |
|-------|-------------|
| `title` | Display name |
| `shortcode` | Quick insert code (e.g., `thanks`) |
| `content` | Response text with placeholders |
| `scope` | `global` (all users) or `personal` |
| `category` | Optional grouping |

### 11.2 Available Placeholders
| Placeholder | Replaced With |
|-------------|---------------|
| `{{customer_name}}` | Customer's name |
| `{{customer_email}}` | Customer's email |
| `{{ticket_id}}` | Ticket ID (TKT-XXXXXX) |
| `{{ticket_title}}` | Ticket subject |
| `{{agent_name}}` | Current agent's name |
| `{{agent_email}}` | Current agent's email |

### 11.3 Usage
- Insert via shortcode typing
- Select from dropdown
- Placeholders auto-replaced on insert

### 11.4 API Endpoints
```
GET    /api/canned-responses           - List all (global + personal)
GET    /api/canned-responses/{id}      - Get one
POST   /api/canned-responses           - Create
PUT    /api/canned-responses/{id}      - Update
DELETE /api/canned-responses/{id}      - Delete
```

---

## 12. Analytics & Reporting

### 12.1 Overview Dashboard
- Total tickets (open, resolved, closed)
- Average resolution time
- Average CSAT score
- Tickets by status (chart)
- Tickets by priority (chart)
- Volume trend (7 days)

### 12.2 Agent Performance
| Metric | Description |
|--------|-------------|
| `tickets_assigned` | Total assigned |
| `tickets_resolved` | Successfully resolved |
| `avg_resolution_time` | Time to resolve |
| `avg_first_response` | Time to first reply |
| `avg_csat` | Agent's CSAT score |

### 12.3 API Endpoints
```
GET    /api/analytics/summary          - Quick summary
GET    /api/analytics/overview         - Full overview
GET    /api/analytics/agents           - Agent stats
```

---

## 13. Search

### 13.1 Search Capabilities
- Full-text search across tickets
- Filter by status, priority, assignee
- Date range filtering
- Tag filtering
- Customer email search

### 13.2 Search Suggestions
Auto-suggest based on:
- Ticket titles
- Customer names
- Tags

### 13.3 API Endpoints
```
GET    /api/search                     - Search tickets
GET    /api/search/suggestions         - Get suggestions
POST   /api/search                     - Advanced search
```

---

## 14. Real-time Features

### 14.1 WebSocket Events
| Event | Description |
|-------|-------------|
| `ticket:created` | New ticket |
| `ticket:updated` | Ticket changed |
| `ticket:deleted` | Ticket removed |
| `presence:join` | User viewing ticket |
| `presence:leave` | User left ticket |
| `typing:start` | User started typing |
| `typing:stop` | User stopped typing |
| `notification` | New notification |

### 14.2 Presence Features
- See who's viewing a ticket
- Typing indicators
- Online status

### 14.3 Multi-Instance Support
- MongoDB-based pub/sub
- Distributed presence tracking
- Cross-instance event broadcasting

### 14.4 API Endpoints
```
GET    /api/presence/stats             - Presence overview
GET    /api/presence/ticket/{id}       - Who's viewing
```

---

## 15. SLA Management

### 15.1 SLA Metrics
| Metric | Description |
|--------|-------------|
| `first_response_hours` | Time to first reply |
| `resolution_hours` | Time to resolve |
| `business_hours_only` | Count only working hours |

### 15.2 SLA Policies
- Per-priority targets
- Per-customer-tier overrides
- Breach notifications
- Warning thresholds

### 15.3 API Endpoints
```
GET    /api/sla-policies               - List policies
POST   /api/sla-policies               - Create policy
PUT    /api/sla-policies/{id}          - Update policy
DELETE /api/sla-policies/{id}          - Delete policy
GET    /api/sla/ticket/{id}            - Ticket SLA status
```

---

## 16. Feature Requests

### 16.1 Feature Request Tracking
Link customer tickets to product feature requests:
- Track votes/demand
- Link multiple tickets
- Status tracking (planned, in_progress, shipped)
- Priority scoring

### 16.2 API Endpoints
```
GET    /api/feature-requests           - List all
POST   /api/feature-requests           - Create
GET    /api/feature-requests/{id}      - Get details
PUT    /api/feature-requests/{id}      - Update
POST   /api/tickets/{id}/feature-request - Link ticket
DELETE /api/tickets/{id}/feature-request/{fid} - Unlink
GET    /api/tickets/{id}/feature-requests - Linked requests
```

---

## 17. Admin & Settings

### 17.1 Custom Fields
Define additional fields for tickets:
- Text, number, dropdown, checkbox
- Required/optional
- Default values

### 17.2 Admin Settings
| Setting | Description |
|---------|-------------|
| `auto_assignment` | Enable/disable auto-routing |
| `auto_reassign_reopened` | Reassign on reopen if off-shift |
| `auto_close_hours` | Hours before resolved → closed |
| `default_team` | Fallback team for routing |

### 17.3 API Endpoints
```
GET    /api/admin/custom-fields        - List fields
POST   /api/admin/custom-fields        - Create field
PUT    /api/admin/custom-fields/{id}   - Update field
DELETE /api/admin/custom-fields/{id}   - Delete field
GET    /api/admin/settings             - Get settings
PUT    /api/admin/settings             - Update settings
GET    /api/admin/auto-close-status    - Auto-close info
POST   /api/admin/trigger-auto-close   - Manual trigger
```

---

## 18. Webhooks & Integrations

### 18.1 Webhook Events
| Event | Payload |
|-------|---------|
| `ticket.created` | Full ticket object |
| `ticket.updated` | Changed fields |
| `ticket.assigned` | Assignment details |
| `ticket.status_changed` | Old/new status |
| `ticket.resolved` | Resolution info |
| `ticket.closed` | Closure info |
| `ticket.deleted` | Ticket ID |
| `ticket.reply_added` | Reply content |
| `ticket.note_added` | Note content |
| `customer.created` | Customer object |
| `customer.updated` | Changed fields |
| `sla.breach` | SLA details |
| `sla.warning` | Warning info |

### 18.2 Webhook Features
- HMAC signature verification
- Retry with exponential backoff
- Delivery logs
- Test endpoint
- Manual retry

### 18.3 API Endpoints
```
GET    /api/webhooks                   - List webhooks
POST   /api/webhooks                   - Create webhook
GET    /api/webhooks/events            - Available events
GET    /api/webhooks/{id}              - Get webhook
PUT    /api/webhooks/{id}              - Update webhook
DELETE /api/webhooks/{id}              - Delete webhook
GET    /api/webhooks/{id}/logs         - Delivery logs
GET    /api/webhooks/logs              - All logs
POST   /api/webhooks/{id}/test         - Send test
POST   /api/webhooks/{id}/retry/{log}  - Retry delivery
```

---

## 19. Data Export & Import

### 19.1 Export Formats
- JSON (full fidelity)
- CSV (tickets only)

### 19.2 Export Options
| Option | Description |
|--------|-------------|
| `include_messages` | Include conversation |
| `include_changelog` | Include activity log |
| `include_csat` | Include CSAT data |
| `date_from/date_to` | Filter by date |
| `status` | Filter by status |

### 19.3 Bulk Export
- All tickets
- All customers
- Full system export
- Analytics data

### 19.4 API Endpoints
```
GET    /api/export                     - Basic export
POST   /api/import                     - Import data
POST   /api/admin/export/tickets       - Advanced export
POST   /api/admin/export/full          - Full system export
GET    /api/admin/export/customers     - Customers export
GET    /api/admin/export/analytics     - Analytics export
```

---

## 20. API Reference

### 20.1 Base URL
```
Production: https://your-domain.com/api
Development: http://localhost:8001/api
```

### 20.2 Authentication
```http
# Session-based (browser)
Cookie: session_token=xxx

# API Key (programmatic)
X-API-Key: tk_live_xxxxx
```

### 20.3 Rate Limits
| Tier | Requests/Hour | Requests/Minute |
|------|---------------|-----------------|
| Default | 1000 | 100 |

### 20.4 Response Format
```json
{
  "data": { ... },
  "error": null,
  "request_id": "abc123"
}
```

### 20.5 Error Codes
| Code | Description |
|------|-------------|
| 400 | Bad request / validation error |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

### 20.6 Health Check
```
GET /api/health
```
Returns:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "checks": {
    "database": {"status": "healthy"},
    "collections": {"status": "healthy"}
  }
}
```

---

## Frontend Pages

| Page | Path | Description |
|------|------|-------------|
| Login | `/login` | Authentication |
| Dashboard | `/` | Personal Kanban board |
| All Tickets | `/all-tickets` | Full ticket list |
| Open Tickets | `/open` | Active tickets |
| Waiting | `/waiting` | Awaiting response |
| Closed | `/closed` | Resolved/closed |
| Starred | `/starred` | Bookmarked tickets |
| Search Results | `/search` | Search page |
| Teams | `/teams` | Team management |
| Customers | `/customers` | Customer profiles |
| Feature Requests | `/feature-requests` | Product roadmap |
| Analytics | `/analytics` | Reporting |
| CSAT | `/csat` | CSAT analytics |
| Canned Responses | `/canned-responses` | Response templates |
| Leave | `/leave` | Leave calendar |
| Settings | `/settings` | User settings |
| Admin | `/admin` | Admin panel |
| Profile | `/profile` | User profile |

---

## Database Collections

| Collection | Description |
|------------|-------------|
| `users` | User accounts |
| `tickets` | Support tickets |
| `user_sessions` | Auth sessions |
| `api_keys` | API credentials |
| `counters` | ID sequences |
| `gmail_tokens` | OAuth tokens |
| `email_threads` | Email threading |
| `teams` | Team definitions |
| `messages` | Notes & replies |
| `custom_fields` | Field definitions |
| `admin_settings` | System settings |
| `shifts` | Shift definitions |
| `user_shifts` | Shift assignments |
| `routing_rules` | Routing rules |
| `ticket_changelog` | Audit log |
| `feature_requests` | Feature tracking |
| `customers` | Customer profiles |
| `csat_responses` | CSAT ratings |
| `csat_tokens` | Survey tokens |
| `email_replies` | Email messages |
| `canned_responses` | Response templates |
| `webhooks` | Webhook subscriptions |
| `webhook_logs` | Delivery logs |
| `sla_policies` | SLA rules |

---

*This document is auto-generated from the codebase and reflects the current implementation status.*
