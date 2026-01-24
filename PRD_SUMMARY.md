# TickFlow PRD - Executive Summary

## What We're Building
An API-first ticket management platform with intelligent routing, team collaboration, and analytics.

---

## Core Features (10 Modules)

| Module | Key Features |
|--------|--------------|
| **1. Tickets** | Merge, split, link, tags, custom fields, AI title |
| **2. Routing** | Round-robin, rule-based, skill-based, escalation |
| **3. Teams** | L1/L2 structure, team inbox, user groups |
| **4. Shifts** | Shift schedules, leave tracking, coverage view |
| **5. Collaboration** | Internal notes, @mentions, activity log |
| **6. Customers** | Profiles, revenue tier, external DB sync |
| **7. Quality** | CSAT surveys, QA scoring, SLA tracking |
| **8. Analytics** | Dashboards, reports, API usage stats |
| **9. Integrations** | Webhooks, Slack, email, database connectors |
| **10. AI** | Auto-title, suggested responses, smart routing |

---

## Implementation Phases

| Phase | What | When |
|-------|------|------|
| **1** | Bug fixes, API keys, ticket IDs | Week 1 |
| **2** | Teams, round-robin routing | Week 2 |
| **3** | Shifts, leave management | Week 3 |
| **4** | Merge/split/link tickets | Week 4 |
| **5** | Customer profiles, external DB | Week 5 |
| **6** | Rules engine, SLA, automation | Week 6-7 |
| **7** | CSAT surveys, QA workflow | Week 8 |
| **8** | Analytics dashboards | Week 9 |
| **9** | Webhooks, Slack, real email | Week 10 |
| **10** | AI features | Week 11-12 |

---

## Key Data Models

**Ticket:** ID, title, status, priority, assignee, team, customer, tags, SLA, CSAT
**User:** Role (agent/lead/admin), team, shift, skills, capacity
**Customer:** Email, domain, revenue_tier, status, custom fields from external DB

---

## API Principles
- REST + JSON
- API key authentication
- Rate limiting (1000 req/min)
- Webhook events for all changes

---

*Full PRD: /app/PRD.md*
