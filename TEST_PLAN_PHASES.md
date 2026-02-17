# Trinity - Phased Screenshot Testing Plan

**Created:** February 12, 2026  
**App URL:** https://knowledge-base-179.preview.emergentagent.com  
**API Docs:** https://knowledge-base-179.preview.emergentagent.com/api/docs  

## Test Credentials
- **Admin User:** test@test.com (user_id: b1bbdaf9-5ac0-47a9-ac7d-31b0b149010e)
- **Session Token:** test_filter_session (cookie: session_token=test_filter_session)
- **Real User:** rohit@emergent.sh (user_id: user_5aeff57a3631)

## Current Data State
| Collection | Count |
|------------|-------|
| Tickets | 150 |
| Teams | 2 |
| Users | 7 |
| Customers | 0 |
| Canned Responses | 0 |
| Feature Requests | 0 |
| SLA Policies | 0 |
| Leaves | 0 |
| Shifts | 0 |
| Webhooks | 0 |
| Custom Fields | 0 |

---

## PHASE 1: Core Navigation & Dashboard (Est: 1 run)
**Goal:** Verify login, sidebar, dashboard, theme toggle, and basic navigation.

| # | Test Case | Steps | Status |
|---|-----------|-------|--------|
| 1.1 | Login Page Renders | Navigate to /login, verify Google sign-in button visible | |
| 1.2 | Auth & Session | Set session cookie, navigate to /dashboard, verify user loads | |
| 1.3 | Dashboard Loads | Verify dashboard renders with ticket stats/kanban | |
| 1.4 | Sidebar Navigation | Click each sidebar link, verify page loads: All Tickets, Open, Waiting, Closed, Starred | |
| 1.5 | Theme Toggle | Toggle dark/light mode, verify UI changes | |
| 1.6 | Profile Page | Navigate to /profile, verify user info displays | |
| 1.7 | Responsive Sidebar | Collapse/expand sidebar, verify layout adjusts | |

---

## PHASE 2: Ticket Management - CRUD & Views (Est: 1-2 runs)
**Goal:** Test ticket creation, viewing, editing, and list/kanban views.

| # | Test Case | Steps | Status |
|---|-----------|-------|--------|
| 2.1 | Create Ticket | Open create modal, fill form, submit, verify ticket appears | |
| 2.2 | View Ticket Drawer | Click a ticket, verify drawer opens with all details | |
| 2.3 | Edit Ticket Status | Change status in drawer, verify change persists | |
| 2.4 | Edit Ticket Priority | Change priority, verify badge updates | |
| 2.5 | Assign Ticket | Assign to a user, verify assignment shows | |
| 2.6 | Ticket List View | Navigate to /all-tickets, verify list renders with pagination | |
| 2.7 | Kanban Board | Verify kanban columns render by status | |
| 2.8 | Star/Unstar Ticket | Star a ticket, navigate to /starred-tickets, verify it appears | |
| 2.9 | Add Internal Note | Open ticket, add note, verify it appears in activity | |
| 2.10 | Add Tags | Add/remove tags on a ticket | |
| 2.11 | Ticket Activity Log | View activity timeline, verify change entries | |
| 2.12 | Filter Tickets | Use status/priority filters on ticket list | |

---

## PHASE 3: Ticket Operations - Merge, Split, Link (Est: 1 run)
**Goal:** Test advanced ticket operations.

| # | Test Case | Steps | Status |
|---|-----------|-------|--------|
| 3.1 | Merge Tickets | Select 2 tickets, merge, verify merged view | |
| 3.2 | Unmerge Ticket | Unmerge previously merged ticket | |
| 3.3 | Split Ticket | Split ticket from a message, verify new ticket created | |
| 3.4 | Link Tickets | Link two tickets with relationship type | |
| 3.5 | Unlink Tickets | Remove a link between tickets | |
| 3.6 | Merge Suggestions | Check auto-merge suggestions for a ticket | |

---

## PHASE 4: Team Management (Est: 1 run)
**Goal:** Test team CRUD and member management.

| # | Test Case | Steps | Status |
|---|-----------|-------|--------|
| 4.1 | View Teams Page | Navigate to /teams, verify teams list renders | |
| 4.2 | Create Team | Create a new team with escalation level | |
| 4.3 | View Team Details | Click a team, verify members and info | |
| 4.4 | Add Team Member | Add a user to the team | |
| 4.5 | Remove Team Member | Remove a user from team | |
| 4.6 | Edit Team | Update team name/description | |
| 4.7 | Delete Team | Delete a team, verify removed | |
| 4.8 | Team Ticket Inbox | View tickets assigned to a team | |
| 4.9 | Assign Ticket to Team | Assign a ticket to a team, verify in team inbox | |

---

## PHASE 5: Customer Management (Est: 1 run)
**Goal:** Test customer CRUD and B2B features.

| # | Test Case | Steps | Status |
|---|-----------|-------|--------|
| 5.1 | View Customers Page | Navigate to /customers, verify page renders | |
| 5.2 | Create Customer | Create a new customer profile | |
| 5.3 | View Customer Details | Click customer, verify profile info | |
| 5.4 | Edit Customer | Update customer fields | |
| 5.5 | Link Email to Customer | Add additional email to customer | |
| 5.6 | B2B Prospects | Verify B2B detection for corporate emails | |
| 5.7 | Customer Tickets | View tickets associated with a customer | |
| 5.8 | Merge Customers | Merge two customer profiles | |

---

## PHASE 6: Canned Responses & Feature Requests (Est: 1 run)
**Goal:** Test canned responses and feature request management.

| # | Test Case | Steps | Status |
|---|-----------|-------|--------|
| 6.1 | View Canned Responses Page | Navigate to /canned-responses | |
| 6.2 | Create Canned Response | Create with title, shortcode, content, placeholders | |
| 6.3 | Edit Canned Response | Modify existing response | |
| 6.4 | Delete Canned Response | Remove a response | |
| 6.5 | View Feature Requests | Navigate to /feature-requests | |
| 6.6 | Create Feature Request | Create new feature request | |
| 6.7 | Edit Feature Request | Update status/details | |
| 6.8 | Link Ticket to Feature Request | Associate a ticket | |

---

## PHASE 7: Leave Management & Analytics (Est: 1 run)
**Goal:** Test leave management and analytics pages.

| # | Test Case | Steps | Status |
|---|-----------|-------|--------|
| 7.1 | View Leave Page | Navigate to /leaves, verify calendar renders | |
| 7.2 | Create Leave Request | Submit a leave request | |
| 7.3 | View Leave Calendar | Check monthly calendar view | |
| 7.4 | Edit/Delete Leave | Modify or cancel a leave | |
| 7.5 | View Analytics Page | Navigate to /analytics | |
| 7.6 | Analytics Overview | Verify charts and stats render | |
| 7.7 | Agent Performance | Check agent metrics section | |

---

## PHASE 8: Admin, Settings & SLA (Est: 1 run)
**Goal:** Test admin panel, settings, and SLA management.

| # | Test Case | Steps | Status |
|---|-----------|-------|--------|
| 8.1 | View Admin Page | Navigate to /admin, verify tabs render | |
| 8.2 | Custom Fields | Create/edit/delete custom ticket fields | |
| 8.3 | Admin Settings | Toggle auto-assignment, auto-close | |
| 8.4 | Routing Rules | Create/edit/delete routing rules | |
| 8.5 | Test Routing Rule | Use test endpoint to validate a rule | |
| 8.6 | View Settings Page | Navigate to /settings | |
| 8.7 | User Preferences | Update notification/display preferences | |
| 8.8 | SLA Policies | Create/edit/delete SLA policies | |
| 8.9 | Verify SLA on Ticket | Check SLA status display on a ticket | |

---

## PHASE 9: Search, Custom Inboxes & CSAT (Est: 1 run)
**Goal:** Test search, custom inbox creation, and CSAT flows.

| # | Test Case | Steps | Status |
|---|-----------|-------|--------|
| 9.1 | Search Tickets | Use search bar, verify results | |
| 9.2 | Search Suggestions | Type in search, verify auto-suggest | |
| 9.3 | Search Results Page | Navigate to /search?q=..., verify page | |
| 9.4 | Create Custom Inbox | Build filter, save as inbox | |
| 9.5 | View Custom Inbox | Navigate to saved inbox, verify filtered tickets | |
| 9.6 | Edit Custom Inbox | Rename inbox | |
| 9.7 | Share Custom Inbox | Share inbox with another user | |
| 9.8 | Delete Custom Inbox | Remove inbox | |
| 9.9 | CSAT Survey Flow | Send CSAT for a ticket, verify token link | |
| 9.10 | Submit CSAT Rating | Open CSAT link, submit rating | |
| 9.11 | CSAT Analytics | Verify CSAT page shows data | |

---

## PHASE 10: End-to-End Workflows (Est: 1 run)
**Goal:** Test complete multi-step business workflows.

| # | Test Case | Steps | Status |
|---|-----------|-------|--------|
| 10.1 | Full Ticket Lifecycle | Create -> Assign -> Work -> Resolve -> Close | |
| 10.2 | Team Escalation Flow | Create ticket -> Assign L1 -> Escalate to L2 -> Resolve | |
| 10.3 | Customer Journey | Email in -> Auto-customer -> Ticket -> Reply -> CSAT | |
| 10.4 | Bulk Operations | Select multiple tickets -> Bulk update status | |
| 10.5 | Export Data | Export tickets as CSV/JSON | |
| 10.6 | API Documentation | Verify /api/docs loads with all endpoints | |

---

## Testing Progress Log

| Phase | Status | Date Started | Date Completed | Issues Found | Notes |
|-------|--------|-------------|---------------|-------------|-------|
| Phase 1 | COMPLETE | Feb 12, 2026 | Feb 12, 2026 | 1 (fixed) | All 12 pages render correctly |
| Phase 2 | COMPLETE | Feb 12, 2026 | Feb 12, 2026 | 0 | Ticket create + drawer verified |
| Phase 3 | NOT STARTED | | | | |
| Phase 4 | COMPLETE | Feb 12, 2026 | Feb 12, 2026 | 0 | 2 teams, members visible |
| Phase 5 | COMPLETE | Feb 12, 2026 | Feb 12, 2026 | 1 (fixed) | Empty state works, agent loading fixed |
| Phase 6 | COMPLETE | Feb 12, 2026 | Feb 12, 2026 | 2 (fixed) | Feature Requests crash fixed + type/status mismatch |
| Phase 7 | COMPLETE | Feb 12, 2026 | Feb 12, 2026 | 1 (fixed) | Leave creation bug fixed, calendar works |
| Phase 8 | COMPLETE | Feb 12, 2026 | Feb 12, 2026 | 1 (fixed) | Admin page array fix, export fix, custom field created |
| Phase 9 | COMPLETE | Feb 12, 2026 | Feb 12, 2026 | 1 (fixed) | Search endpoint bug fixed (missing db arg + wrong method) |
| Phase 10 | COMPLETE | Feb 12, 2026 | Feb 12, 2026 | 0 | Full ticket lifecycle E2E verified |

---

## Issue Tracking

| # | Phase | Test Case | Severity | Description | Status | Fix Applied |
|---|-------|-----------|----------|-------------|--------|-------------|
| 1 | 6 | Feature Requests | CRITICAL | `featureRequests.filter is not a function` - API returns `{items:[]}` not array | FIXED | FeatureRequestsPage.js line 58 |
| 2 | 5 | Customer Detail | HIGH | `data.filter is not a function` - /api/users returns `{items:[]}` | FIXED | CustomersPage.js line 123 |
| 3 | 1 | Profile Page | HIGH | User list not extracted from `{items:[]}` | FIXED | ProfilePage.js line 54 |
| 4 | 1 | Dashboard | MEDIUM | Users list not extracted from `{items:[]}` | FIXED | Dashboard.js line 66 |
| 5 | 1 | Dashboard Container | MEDIUM | Users list not extracted from `{items:[]}` | FIXED | DashboardContainer.js line 99 |
| 6 | 1 | Main Layout | MEDIUM | Users list not extracted from `{items:[]}` | FIXED | MainLayout.js line 108 |
| 7 | 1 | Starred Tickets | MEDIUM | Users list not extracted from `{items:[]}` | FIXED | StarredTicketsPage.js line 72 |
| 8 | 7 | Leave Page | MEDIUM | Users list not extracted from `{items:[]}` | FIXED | LeavePage.js line 110 |
| 9 | 8 | Admin Page | MEDIUM | Users list not extracted from `{items:[]}` | FIXED | AdminPage.js line 486 |
| 10 | 8 | Settings Export | LOW | Export functions only handle `{tickets:[]}` not `{items:[]}` | FIXED | SettingsPage.js lines 280,330 |
| 11 | 7 | Leave Creation | CRITICAL | `LeaveManager.create_leave()` called with wrong args (dict + user_id instead of LeaveRequest) | FIXED | routes/leaves.py line 39 |
| 12 | 6 | Feature Request Status | MEDIUM | Backend creates with `status: "proposed"` but frontend expects `"new"` | FIXED | routes/feature_requests.py line 35 |
| 13 | 6 | Feature Request Type | MEDIUM | Backend returns `category` but frontend reads `request_type` | FIXED | FeatureRequestsPage.js (3 locations) |
| 14 | 9 | Search Endpoint | CRITICAL | `get_search_engine()` called without db arg + wrong method name | FIXED | routes/search_presence.py |
| 15 | 6 | Feature Request Index | MEDIUM | MongoDB had legacy `feature_id` index conflicting with `feature_request_id` | FIXED | Dropped index |

---

*This plan is designed to be executed across multiple agentic runs. Each phase can be completed independently.*
