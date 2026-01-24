# TickFlow Implementation Plan

## Overview

This document breaks down the PRD into actionable implementation phases. Each phase has:
- Clear scope and deliverables
- Testing checkpoints
- Bug fix windows

---

## Phase 1: Foundation & Stabilization
**Timeline: Week 1**
**Status: IN PROGRESS**

### 1.1 Bug Fixes (Day 1-2)
- [ ] Fix sidebar click-based submenu (completed partially)
- [ ] Verify email sync with correct query
- [ ] Test email simulator endpoint
- [ ] Clean up rohit@emergent.sh Gmail connection (disconnect)

### 1.2 Ticket ID & Source Tracking (Day 2-3)
- [ ] Generate sequential ticket IDs (TKT-000001 format)
- [ ] Add `source` field (email, manual, api, simulator)
- [ ] Extract `domain` from customer email
- [ ] Add `tags` array field

**Backend Changes:**
```python
# New ticket ID generator
def generate_ticket_id():
    counter = db.counters.find_one_and_update(
        {"_id": "ticket_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return f"TKT-{counter['seq']:06d}"
```

### 1.3 API Foundation (Day 3-5)
- [ ] Create API key model and generation
- [ ] API key authentication middleware
- [ ] Rate limiting (1000 req/min)
- [ ] Standardized error responses
- [ ] Basic OpenAPI documentation

**New Endpoints:**
```
POST /api/v1/auth/api-keys      # Generate API key
GET  /api/v1/auth/api-keys      # List API keys
DELETE /api/v1/auth/api-keys/:id # Revoke API key
```

### 1.4 Testing Checkpoint
- [ ] All existing features working
- [ ] API key auth working
- [ ] Email simulator creates tickets
- [ ] Ticket IDs sequential

---

## Phase 2: Team Structure & Basic Routing
**Timeline: Week 2**
**Status: NOT STARTED**

### 2.1 Team Management (Day 1-2)
- [ ] Create `teams` collection
- [ ] Team CRUD endpoints
- [ ] Team types (L1, L2, etc.)
- [ ] Team UI in settings

**Data Model:**
```javascript
{
  team_id: "team_xxx",
  name: "L1 Support",
  type: "l1",  // l1, l2, specialist
  description: "Front-line support team",
  members: ["user_1", "user_2"],
  lead_id: "user_1",
  created_at: Date
}
```

**Endpoints:**
```
GET    /api/v1/teams
POST   /api/v1/teams
GET    /api/v1/teams/:id
PUT    /api/v1/teams/:id
DELETE /api/v1/teams/:id
POST   /api/v1/teams/:id/members     # Add member
DELETE /api/v1/teams/:id/members/:uid # Remove member
```

### 2.2 User Roles & Team Assignment (Day 2-3)
- [ ] Add `role` to user (agent, lead, admin)
- [ ] Add `team_id` to user
- [ ] Add `skills` array to user
- [ ] User management UI

### 2.3 Team Inbox (Day 3-4)
- [ ] Add `team_id` to tickets
- [ ] Team inbox view (unassigned tickets for team)
- [ ] Filter tickets by team
- [ ] Team assignment on ticket

### 2.4 Basic Round Robin (Day 4-5)
- [ ] Round robin assignment within team
- [ ] Track last assigned user per team
- [ ] Skip users with max tickets
- [ ] Manual override option

**Assignment Logic:**
```python
def round_robin_assign(team_id, ticket_id):
    team = teams_collection.find_one({"team_id": team_id})
    members = team["members"]
    
    # Get last assigned index
    last_idx = team.get("last_assigned_idx", -1)
    
    # Find next available agent
    for i in range(len(members)):
        idx = (last_idx + 1 + i) % len(members)
        user = users_collection.find_one({"user_id": members[idx]})
        
        if user.get("status") == "online" and not user.get("on_leave"):
            if user.get("current_ticket_count", 0) < user.get("max_tickets", 10):
                # Assign
                assign_ticket(ticket_id, members[idx])
                teams_collection.update_one(
                    {"team_id": team_id},
                    {"$set": {"last_assigned_idx": idx}}
                )
                return members[idx]
    
    return None  # No available agent
```

### 2.5 Internal Notes (Day 5)
- [ ] Create `messages` collection (for notes & replies)
- [ ] Internal note endpoint
- [ ] Notes visible in ticket drawer
- [ ] Differentiate internal vs customer-visible

**Data Model:**
```javascript
{
  message_id: "msg_xxx",
  ticket_id: "TKT-000001",
  type: "internal_note",  // internal_note, reply, customer_message
  content: "Internal discussion...",
  author_id: "user_xxx",
  author_name: "John Doe",
  mentions: ["user_yyy"],
  created_at: Date
}
```

### 2.6 Testing Checkpoint
- [ ] Create teams and assign users
- [ ] Round robin distributes tickets
- [ ] Team inbox shows unassigned
- [ ] Internal notes work

---

## Phase 3: Shift & Leave Management
**Timeline: Week 3**
**Status: NOT STARTED**

### 3.1 Shift Definition (Day 1-2)
- [ ] Create `shifts` collection
- [ ] Shift CRUD endpoints
- [ ] Shift assignment to users
- [ ] Shift calendar UI

**Data Model:**
```javascript
{
  shift_id: "shift_xxx",
  name: "Morning Shift",
  team_id: "team_l1",
  start_time: "09:00",
  end_time: "17:00",
  timezone: "Asia/Kolkata",
  days: ["mon", "tue", "wed", "thu", "fri"],
  members: ["user_1", "user_2"]
}
```

### 3.2 Leave Management (Day 2-3)
- [ ] Create `leaves` collection
- [ ] Leave request/entry endpoints
- [ ] Leave calendar view
- [ ] Leave approval workflow (optional)

**Data Model:**
```javascript
{
  leave_id: "leave_xxx",
  user_id: "user_xxx",
  type: "vacation",  // vacation, sick, half_day, custom
  start_date: "2026-01-25",
  end_date: "2026-01-27",
  half_day_type: null,  // morning, afternoon
  reason: "Family vacation",
  status: "approved",
  approved_by: "user_lead"
}
```

### 3.3 Shift-Aware Routing (Day 3-4)
- [ ] Check if user is on-shift before assignment
- [ ] Current shift indicator in UI
- [ ] Shift handoff logic
- [ ] Out-of-hours ticket handling

### 3.4 Coverage Dashboard (Day 4-5)
- [ ] Visual shift calendar
- [ ] Coverage gaps indicator
- [ ] Team availability view
- [ ] Real-time on-shift agents

### 3.5 Testing Checkpoint
- [ ] Shifts created and assigned
- [ ] Leave blocks assignment
- [ ] Routing respects shifts
- [ ] Coverage view accurate

---

## Phase 4: Advanced Ticket Operations
**Timeline: Week 4**
**Status: NOT STARTED**

### 4.1 Ticket Linking (Day 1)
- [ ] Add `linked_tickets` array
- [ ] Link types: related_to, blocks, blocked_by, duplicate_of
- [ ] Link creation endpoint
- [ ] Linked tickets in UI

### 4.2 Ticket Merge (Day 2-3)
- [ ] Merge endpoint
- [ ] Combine conversations
- [ ] Update references
- [ ] Merge history tracking

**Merge Logic:**
```python
def merge_tickets(target_id, source_ids):
    target = tickets_collection.find_one({"ticket_id": target_id})
    
    for source_id in source_ids:
        source = tickets_collection.find_one({"ticket_id": source_id})
        
        # Move messages to target
        messages_collection.update_many(
            {"ticket_id": source_id},
            {"$set": {"ticket_id": target_id, "merged_from": source_id}}
        )
        
        # Mark source as merged
        tickets_collection.update_one(
            {"ticket_id": source_id},
            {"$set": {
                "status": "merged",
                "merged_into": target_id,
                "merged_at": datetime.now()
            }}
        )
    
    # Add merge note to target
    add_internal_note(target_id, f"Merged tickets: {source_ids}")
```

### 4.3 Ticket Split (Day 3-4)
- [ ] Split from message point
- [ ] Create new ticket with subset of messages
- [ ] Link original and split tickets
- [ ] Split UI in conversation view

### 4.4 Bulk Operations (Day 4-5)
- [ ] Bulk selection UI
- [ ] Bulk assign
- [ ] Bulk status change
- [ ] Bulk tag

### 4.5 Snooze & Follow-up (Day 5)
- [ ] Snooze ticket until datetime
- [ ] Snoozed tickets view
- [ ] Auto-unsnooze job

### 4.6 Testing Checkpoint
- [ ] Merge combines tickets correctly
- [ ] Split creates new ticket
- [ ] Links visible and navigable
- [ ] Bulk operations work

---

## Phase 5: Customer Context & External Data
**Timeline: Week 5**
**Status: NOT STARTED**

### 5.1 Customer Management (Day 1-2)
- [ ] Create `customers` collection
- [ ] Auto-create customer from ticket email
- [ ] Customer profile page
- [ ] Customer ticket history

### 5.2 Customer Attributes (Day 2-3)
- [ ] Revenue tier field
- [ ] Status field (active, trial, churned)
- [ ] Custom fields support
- [ ] Customer context in ticket drawer

### 5.3 External Database Connector (Day 3-5)
- [ ] Connector configuration model
- [ ] PostgreSQL connector
- [ ] Field mapping
- [ ] Manual & scheduled sync
- [ ] Webhook for real-time sync

**Configuration:**
```javascript
{
  connector_id: "conn_xxx",
  type: "postgresql",
  connection_string: "postgresql://...",
  table: "customers",
  key_field: "email",
  field_mappings: {
    "mrr": "revenue",
    "plan_name": "plan",
    "job_count": "jobs"
  },
  sync_interval: "1h",
  last_sync: Date
}
```

### 5.4 Testing Checkpoint
- [ ] Customers auto-created
- [ ] Customer profile shows history
- [ ] External data syncs
- [ ] Context visible in tickets

---

## Phase 6: Automation & Rules Engine
**Timeline: Week 6-7**
**Status: NOT STARTED**

### 6.1 Rules Engine Core (Day 1-3)
- [ ] Rule data model
- [ ] Condition evaluator
- [ ] Action executor
- [ ] Rule priority ordering

### 6.2 Rule Builder UI (Day 3-5)
- [ ] Visual rule builder
- [ ] Condition builder
- [ ] Action configuration
- [ ] Rule testing/preview

### 6.3 SLA Management (Day 5-7)
- [ ] SLA policy model
- [ ] SLA timer tracking
- [ ] First response SLA
- [ ] Resolution SLA
- [ ] SLA breach warnings

### 6.4 Workflow Automation (Day 7-10)
- [ ] Trigger types (ticket.created, status.changed, etc.)
- [ ] Auto-assignment rules
- [ ] Escalation rules
- [ ] Auto-close after X days

### 6.5 Testing Checkpoint
- [ ] Rules trigger correctly
- [ ] SLA timers accurate
- [ ] Automations execute

---

## Phase 7: Quality & Feedback
**Timeline: Week 8**
**Status: NOT STARTED**

### 7.1 CSAT Survey (Day 1-2)
- [ ] Survey trigger on resolution
- [ ] Rating collection (1-5)
- [ ] Reason text field
- [ ] Survey in ticket model

### 7.2 Survey Delivery (Day 2-3)
- [ ] Email survey (if not mock mode)
- [ ] In-app survey link
- [ ] Survey response endpoint

### 7.3 QA Workflow (Day 3-5)
- [ ] QA queue view
- [ ] Scoring rubric
- [ ] Manager review assignment
- [ ] Performance notes

### 7.4 Testing Checkpoint
- [ ] Surveys sent on resolution
- [ ] Scores recorded
- [ ] QA queue works

---

## Phase 8: Analytics & Reporting
**Timeline: Week 9**
**Status: NOT STARTED**

### 8.1 Real-time Dashboard (Day 1-2)
- [ ] Open tickets by status
- [ ] Tickets by priority
- [ ] Agent workload
- [ ] SLA health indicators

### 8.2 Historical Reports (Day 2-4)
- [ ] Volume trends
- [ ] SLA compliance
- [ ] Agent performance
- [ ] CSAT trends

### 8.3 API Analytics (Day 4-5)
- [ ] API usage tracking
- [ ] Rate limit stats
- [ ] Webhook delivery stats

### 8.4 Testing Checkpoint
- [ ] Dashboard accurate
- [ ] Reports exportable
- [ ] API stats tracked

---

## Phase 9: Integrations & Webhooks
**Timeline: Week 10**
**Status: NOT STARTED**

### 9.1 Webhook System (Day 1-2)
- [ ] Webhook configuration
- [ ] Event subscription
- [ ] Delivery with retry
- [ ] Delivery logs

### 9.2 Slack Integration (Day 2-3)
- [ ] Slack app setup
- [ ] Ticket notifications
- [ ] Ticket cards
- [ ] Actions from Slack

### 9.3 Real Email Sending (Day 3-5)
- [ ] SMTP configuration
- [ ] Toggle mock mode off
- [ ] Email templates
- [ ] Delivery tracking

### 9.4 Testing Checkpoint
- [ ] Webhooks deliver
- [ ] Slack notifications work
- [ ] Emails send correctly

---

## Phase 10: AI Features
**Timeline: Week 11-12**
**Status: NOT STARTED**

### 10.1 AI Title Generation (Day 1-2)
- [ ] LLM integration
- [ ] Auto-generate on ticket creation
- [ ] Regenerate option

### 10.2 Suggested Responses (Day 2-4)
- [ ] Context-aware suggestions
- [ ] One-click insert
- [ ] Learn from used responses

### 10.3 Smart Routing (Day 4-7)
- [ ] Intent detection
- [ ] Category prediction
- [ ] Priority prediction
- [ ] Team suggestion

### 10.4 Testing Checkpoint
- [ ] AI titles generated
- [ ] Suggestions relevant
- [ ] Routing accurate

---

## Testing Strategy

### Per-Phase Testing
1. **Unit Tests** - API endpoints
2. **Integration Tests** - Full workflows
3. **UI Tests** - Key user flows
4. **Load Tests** - API performance

### Bug Fix Windows
- 1-2 days after each phase
- Priority: P0 → P1 → P2
- No new features during fix window

### Regression Testing
- Run full test suite before each phase
- Automated smoke tests on deploy

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Scope creep | Strict phase boundaries |
| Data migration | Backward-compatible schema |
| Performance | Index early, paginate everything |
| Downtime | Feature flags for gradual rollout |

---

## Success Criteria

### Phase 1
- [ ] 100% existing features working
- [ ] API auth functional
- [ ] <200ms average response time

### Phase 2
- [ ] Teams assignable
- [ ] Round robin distributes evenly

### Phase 3
- [ ] Shifts enforced in routing
- [ ] Leave blocks assignment

### Overall
- [ ] All API endpoints documented
- [ ] Test coverage >70%
- [ ] No P0 bugs

---

*Last Updated: January 2026*
