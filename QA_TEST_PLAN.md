# TickFlow (Trinity) — Comprehensive QA Test Plan

**Version:** 3.0  
**Date:** 2026-02-17  
**Scope:** Full-stack coverage of all 175+ API endpoints, 20+ frontend pages, real-time features, and edge cases.

---

## Table of Contents

1. [Authentication & Authorization](#1-authentication--authorization)
2. [Ticket CRUD](#2-ticket-crud)
3. [Ticket Assignment & Routing](#3-ticket-assignment--routing)
4. [Ticket Operations (Merge/Split/Link/Bulk)](#4-ticket-operations)
5. [Internal Notes & Activity](#5-internal-notes--activity)
6. [Tags & Starred Tickets](#6-tags--starred-tickets)
7. [Team Management](#7-team-management)
8. [Shift Management](#8-shift-management)
9. [Leave Management](#9-leave-management)
10. [Customer Management](#10-customer-management)
11. [Filters & Custom Inboxes](#11-filters--custom-inboxes)
12. [CSAT (Customer Satisfaction)](#12-csat)
13. [Canned Responses](#13-canned-responses)
14. [Feature Requests](#14-feature-requests)
15. [SLA Policies & Escalation Rules](#15-sla-policies--escalation-rules)
16. [Admin & Settings](#16-admin--settings)
17. [Analytics & Reporting](#17-analytics--reporting)
18. [Search & Presence](#18-search--presence)
19. [Webhooks](#19-webhooks)
20. [Exports](#20-exports)
21. [Email Integration](#21-email-integration)
22. [Knowledge Base](#22-knowledge-base)
23. [Customer Portal](#23-customer-portal)
24. [Real-time / WebSocket](#24-real-time--websocket)
25. [Frontend UI & Navigation](#25-frontend-ui--navigation)
26. [Security & Input Validation](#26-security--input-validation)
27. [Performance & Scalability](#27-performance--scalability)
28. [Error Handling & Edge Cases](#28-error-handling--edge-cases)
29. [Data Integrity & Consistency](#29-data-integrity--consistency)
30. [Atlas Import](#30-atlas-import)

---

## 1. Authentication & Authorization

### 1.1 Session Creation (`POST /api/auth/session`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 1.1.1 | Valid session_id from Emergent Auth | Returns user object, sets `session_token` cookie (httponly, secure, samesite=none, 7-day max-age) | P0 |
| 1.1.2 | Invalid session_id | 401 "Invalid session_id" | P0 |
| 1.1.3 | Expired session_id | 401 error | P0 |
| 1.1.4 | Empty session_id string | 422 validation error (min_length=10) | P1 |
| 1.1.5 | session_id shorter than 10 chars | 422 validation error | P1 |
| 1.1.6 | session_id longer than 500 chars | 422 validation error | P1 |
| 1.1.7 | Domain restriction: email not matching ALLOWED_DOMAIN | 403 "Access restricted" | P1 |
| 1.1.8 | New user (first login) — creates user doc with user_id, defaults `preferences.theme=dark` | User created in DB with generated user_id | P0 |
| 1.1.9 | Returning user — updates name/picture, does NOT overwrite user_id | Existing user_id preserved | P0 |
| 1.1.10 | Legacy user without user_id field | user_id field backfilled | P2 |
| 1.1.11 | Rate limit: >10 requests/minute | 429 Too Many Requests | P1 |
| 1.1.12 | Emergent Auth API timeout (>30s) | 500 error with detail | P2 |
| 1.1.13 | Concurrent sessions for same user | Both sessions valid, latest overwrites | P2 |

### 1.2 Get Current User (`GET /api/auth/me`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 1.2.1 | Valid session token (cookie) | Returns user object | P0 |
| 1.2.2 | Valid session token (Authorization: Bearer header) | Returns user object | P0 |
| 1.2.3 | No token provided | 401 "Not authenticated" | P0 |
| 1.2.4 | Invalid session token | 401 "Invalid session" | P0 |
| 1.2.5 | Expired session token | 401 "Session expired", session deleted from DB | P0 |
| 1.2.6 | Valid API key in X-API-Key header | Returns API key user info | P0 |
| 1.2.7 | Invalid API key | 401 "Invalid API key" | P0 |
| 1.2.8 | Revoked API key | 401 "Invalid API key" | P1 |

### 1.3 Logout (`POST /api/auth/logout`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 1.3.1 | Logout with valid session | Session deleted from DB, cookie cleared | P0 |
| 1.3.2 | Logout with no session token | Cookie cleared, no error | P1 |
| 1.3.3 | Logout with invalid session token | Cookie cleared, no error | P1 |

### 1.4 API Key Management

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 1.4.1 | Create API key (`POST /api/auth/api-keys`) | Returns key_id, full key (only shown once), created_at | P0 |
| 1.4.2 | Create API key rate limit: >10/hour | 429 | P1 |
| 1.4.3 | List API keys (`GET /api/auth/api-keys`) | Returns keys for current user only, key_hash excluded, key_prefix shown | P0 |
| 1.4.4 | Revoke API key (`DELETE /api/auth/api-keys/{key_id}`) | Key marked revoked, no longer usable | P0 |
| 1.4.5 | Revoke another user's API key | 404 "API key not found" | P1 |
| 1.4.6 | Use revoked API key for authenticated request | 401 | P0 |
| 1.4.7 | API key SHA-256 lookup + bcrypt verification | Successful auth with usage_count incremented | P1 |
| 1.4.8 | Legacy API key without key_sha256 (migration path) | Falls back to full scan, backfills sha256 | P2 |

### 1.5 Role-Based Authorization

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 1.5.1 | Agent accessing agent-level endpoint | Allowed | P0 |
| 1.5.2 | Agent accessing lead-only endpoint | 403 "Insufficient permissions" | P0 |
| 1.5.3 | Agent accessing admin-only endpoint | 403 "Admin privileges required" | P0 |
| 1.5.4 | Lead accessing lead-or-admin endpoint | Allowed | P0 |
| 1.5.5 | Admin accessing any endpoint | Allowed | P0 |
| 1.5.6 | User with no role field (defaults to "agent") | Treated as agent | P1 |

---

## 2. Ticket CRUD

### 2.1 List Tickets (`GET /api/tickets`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 2.1.1 | List all tickets (no filters) | Returns paginated list, excludes "merged" status by default | P0 |
| 2.1.2 | Filter by single status `?status=todo` | Only todo tickets | P0 |
| 2.1.3 | Filter by multiple statuses `?status=todo&status=in_progress` | Tickets with either status | P0 |
| 2.1.4 | Filter by assignee_id | Only tickets assigned to that user | P0 |
| 2.1.5 | Filter by mentioned_user_id | Tickets where user is @mentioned | P1 |
| 2.1.6 | Filter by is_starred=true | Only starred tickets | P1 |
| 2.1.7 | Filter by escalation_level=L2 | Only L2 tickets | P1 |
| 2.1.8 | include_merged=true | Merged tickets included | P1 |
| 2.1.9 | Pagination: page=1, limit=10 | First 10 results, total count, has_more correct | P0 |
| 2.1.10 | Pagination: page=2, limit=10 on 15 results | Next 5 results, has_more=false | P0 |
| 2.1.11 | Sort by created_at desc (default) | Most recent first | P0 |
| 2.1.12 | Sort by updated_at asc | Oldest updated first | P1 |
| 2.1.13 | Sort by priority | Sorted alphabetically by priority | P2 |
| 2.1.14 | Invalid page (page=0) | 422 validation error (ge=1) | P1 |
| 2.1.15 | Limit exceeds max (limit=201) | 422 validation error (le=200) | P1 |
| 2.1.16 | Empty result set | Returns `{"tickets": [], "total": 0}` | P1 |

### 2.2 Create Ticket (`POST /api/tickets`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 2.2.1 | Create with required fields only (title) | Ticket created with TKT-XXXXXX ID, uuid, defaults applied | P0 |
| 2.2.2 | Create with all fields | All fields persisted correctly | P0 |
| 2.2.3 | Title validation: empty string | 422 (min_length=1) | P0 |
| 2.2.4 | Title validation: >500 chars | 422 (max_length) | P1 |
| 2.2.5 | Description >50000 chars | 422 validation error | P1 |
| 2.2.6 | Invalid status value "invalid" | 422 validator error | P0 |
| 2.2.7 | Invalid priority value | 422 validator error | P0 |
| 2.2.8 | Invalid escalation_level "L4" | 422 validator error | P1 |
| 2.2.9 | Invalid source "unknown" | 422 validator error | P1 |
| 2.2.10 | Tags: >50 tags | 422 "Maximum 50 tags allowed" | P1 |
| 2.2.11 | Tags: single tag >100 chars | 422 "Tag length cannot exceed 100" | P1 |
| 2.2.12 | Customer email provided — auto-creates/links customer | customer_id set, domain extracted | P0 |
| 2.2.13 | No assignee_id — defaults to current_user | assignee_id = current_user.user_id | P0 |
| 2.2.14 | Routing rules evaluated on creation | routing_applied and routing_rule in response | P1 |
| 2.2.15 | Kanban order calculated (next order in status column) | order field set correctly | P1 |
| 2.2.16 | Changelog entry created (change_type="create") | Entry exists in ticket_changelog | P1 |
| 2.2.17 | Webhook triggered (ticket.created) | Webhook fired with ticket payload | P1 |
| 2.2.18 | Real-time broadcast (ticket:created) | Socket.IO event emitted | P1 |
| 2.2.19 | Sequential ticket ID generation | IDs are sequential (TKT-000001, TKT-000002, ...) | P0 |

### 2.3 Get Single Ticket (`GET /api/tickets/{ticket_id}`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 2.3.1 | Valid ticket_id | Full ticket object returned | P0 |
| 2.3.2 | Non-existent ticket_id | 404 "Ticket not found" | P0 |
| 2.3.3 | _id excluded from response | No MongoDB _id in response | P1 |

### 2.4 Update Ticket (`PUT /api/tickets/{ticket_id}`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 2.4.1 | Update single field (status) | Field updated, updated_at changed | P0 |
| 2.4.2 | Update multiple fields | All fields updated | P0 |
| 2.4.3 | Update to status=resolved | resolved_at timestamp set | P0 |
| 2.4.4 | Update to status=closed | closed_at timestamp set | P0 |
| 2.4.5 | Empty update body (all null) | 400 "No data to update" | P1 |
| 2.4.6 | Non-existent ticket | 404 | P0 |
| 2.4.7 | Status change creates system message in messages collection | System message logged | P0 |
| 2.4.8 | Assignee change creates system message | "Assigned to {name}" message logged | P0 |
| 2.4.9 | Priority change creates system message | "Priority set to {value}" message logged | P1 |
| 2.4.10 | Changelog batch logged for all changed fields | Entries in ticket_changelog with old/new values | P0 |
| 2.4.11 | Reopen ticket (resolved→todo) triggers reassignment logic | handle_ticket_reopen_reassignment called | P1 |
| 2.4.12 | Reopen with original assignee off-shift → queued | Status becomes "queued", assignee set to None | P2 |
| 2.4.13 | Webhook triggered (ticket.updated) | Webhook fired | P1 |
| 2.4.14 | Status change triggers ticket.status_changed webhook | Additional webhook event | P1 |
| 2.4.15 | Resolved triggers ticket.resolved webhook | Additional webhook event | P1 |
| 2.4.16 | Assignee change triggers ticket.assigned webhook | Additional webhook event | P1 |
| 2.4.17 | Real-time broadcast (ticket:update) | Socket.IO event emitted to all clients | P1 |
| 2.4.18 | Custom fields update with value >10000 chars | 422 validator error | P2 |
| 2.4.19 | Set is_starred=true | Field persisted | P1 |
| 2.4.20 | Set snoozed=true | Field persisted | P1 |

### 2.5 Delete Ticket (`DELETE /api/tickets/{ticket_id}`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 2.5.1 | Delete existing ticket | Ticket removed, 200 "Ticket deleted successfully" | P0 |
| 2.5.2 | Delete non-existent ticket | 404 | P0 |
| 2.5.3 | Changelog entry created (change_type="delete") | Entry exists | P1 |
| 2.5.4 | Real-time broadcast (ticket:deleted) | Socket.IO event emitted | P1 |
| 2.5.5 | Webhook triggered (ticket.deleted) | Webhook fired | P1 |

### 2.6 Reorder Tickets (`POST /api/tickets/reorder`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 2.6.1 | Move ticket to new status column with specific order | Status and order updated, other tickets reordered | P0 |
| 2.6.2 | Non-existent ticket_id | 404 | P1 |

---

## 3. Ticket Assignment & Routing

### 3.1 Manual Assignment (`POST /api/tickets/{ticket_id}/assign`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 3.1.1 | Assign to specific user | assignee_id set, current_ticket_count incremented | P0 |
| 3.1.2 | Assign to team only (no assignee_id) | Round-robin selects agent | P0 |
| 3.1.3 | Assign to team + specific user | Both team_id and assignee_id set | P1 |
| 3.1.4 | Non-existent ticket | 404 | P0 |
| 3.1.5 | System message created for assignment | Message logged | P1 |

### 3.2 Auto-Assign (`POST /api/routing/auto-assign`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 3.2.1 | Auto-assign with available agents | Agent selected via round-robin | P0 |
| 3.2.2 | No available agents in team | 400 "No available agents in team" | P0 |
| 3.2.3 | Non-existent ticket | 404 | P1 |

### 3.3 Escalation (`PUT /api/tickets/{ticket_id}/escalate`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 3.3.1 | Escalate L1→L2 | escalation_level updated, escalation_history appended, auto-assigned to L2 team | P0 |
| 3.3.2 | Escalate L2→L3 | Same as above for L3 | P0 |
| 3.3.3 | Invalid escalation level "L4" | 400 "Invalid escalation level" | P1 |
| 3.3.4 | Non-existent ticket | 404 | P0 |
| 3.3.5 | Escalation with reason text | Reason stored in escalation_history | P1 |
| 3.3.6 | Escalated_at timestamp set | Field updated | P1 |

### 3.4 Assignment Options (`GET /api/tickets/{ticket_id}/assignment-options`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 3.4.1 | Get options for ticket with team | Returns team_members with is_on_shift flag, other_teams with on_shift_count | P0 |
| 3.4.2 | Get options for ticket without team | team_members empty, all teams listed as other_teams | P1 |
| 3.4.3 | Non-existent ticket | 404 | P1 |

### 3.5 Routing Rules Engine

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 3.5.1 | Ticket matches routing rule conditions | Rule applied, actions executed | P0 |
| 3.5.2 | Multiple rules match — only first (highest priority) applied | Single rule applied | P1 |
| 3.5.3 | No rules match | No changes applied | P1 |
| 3.5.4 | Condition operator: equals (case-insensitive) | Matches correctly | P1 |
| 3.5.5 | Condition operator: not_equals | Matches correctly | P1 |
| 3.5.6 | Condition operator: contains | Substring match | P1 |
| 3.5.7 | Condition operator: in (list values) | Value in list | P1 |
| 3.5.8 | Condition operator: exists | Field non-null and non-empty | P1 |
| 3.5.9 | Condition operator: not_exists | Field null or empty | P1 |
| 3.5.10 | Action: assign_team | team_id set | P1 |
| 3.5.11 | Action: assign_user | assignee_id set | P1 |
| 3.5.12 | Action: set_priority | priority updated | P1 |
| 3.5.13 | Action: add_tags | Tags appended | P1 |
| 3.5.14 | Condition groups (OR between groups, AND within group) | Correct boolean logic | P1 |

---

## 4. Ticket Operations

### 4.1 Bulk Update (`POST /api/tickets/bulk-update`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 4.1.1 | Bulk update status for 3 tickets | All 3 updated, count returned | P0 |
| 4.1.2 | Empty ticket_ids | 400 "No ticket IDs provided" | P1 |
| 4.1.3 | >100 ticket_ids | 400 "Maximum 100 tickets" | P1 |
| 4.1.4 | Invalid update fields (not in allowed set) | 400 "No valid update fields" | P1 |
| 4.1.5 | Allowed fields: status, priority, assignee_id, team_id, escalation_level | All accepted | P1 |
| 4.1.6 | Changelog entries created per ticket per field | Entries with bulk_operation=True | P1 |

### 4.2 Bulk Tag (`POST /api/tickets/bulk-tag`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 4.2.1 | Add tags to 3 tickets | Tags appended (no duplicates) | P0 |
| 4.2.2 | Remove tags from 3 tickets | Tags removed | P0 |
| 4.2.3 | Simultaneous add and remove | Both operations applied | P1 |
| 4.2.4 | Empty ticket_ids | 400 | P1 |
| 4.2.5 | >100 ticket_ids | 400 | P1 |

### 4.3 Bulk Close (`POST /api/tickets/bulk-close`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 4.3.1 | Close 5 tickets | All set to "resolved" with resolved_at | P0 |
| 4.3.2 | Empty list | 400 | P1 |
| 4.3.3 | >100 tickets | 400 | P1 |

### 4.4 Merge Tickets (`POST /api/tickets/{ticket_id}/merge`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 4.4.1 | Merge source into target | Messages moved, merge_divider created, source status="merged" | P0 |
| 4.4.2 | Missing target_ticket_id | 400 "Target ticket ID required" | P1 |
| 4.4.3 | Non-existent source | 404 "Source ticket not found" | P0 |
| 4.4.4 | Non-existent target | 404 "Target ticket not found" | P0 |
| 4.4.5 | Source description preserved as customer_reply in target | Original content message created | P1 |
| 4.4.6 | Tags combined (deduped) | Combined tags on target | P1 |
| 4.4.7 | search_identifiers aggregated (for searchability) | Source IDs added to target | P1 |
| 4.4.8 | associated_emails aggregated | Source emails added to target | P1 |
| 4.4.9 | Merge divider timestamp = source created_at - 1 second | Appears before source messages in timeline | P2 |
| 4.4.10 | Merge color_index cycles 0-4 | Correct cycling | P2 |
| 4.4.11 | Changelog entry (change_type="merge") | Entry exists | P1 |
| 4.4.12 | Source ticket preserves pre_merge_status | Status saved for unmerge | P1 |
| 4.4.13 | Multiple merges into same target | All merged_tickets tracked | P1 |

### 4.5 Unmerge Tickets (`POST /api/tickets/{ticket_id}/unmerge/{source_ticket_id}`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 4.5.1 | Unmerge previously merged ticket | Messages moved back, source restored to pre_merge_status | P0 |
| 4.5.2 | Non-existent parent | 404 | P0 |
| 4.5.3 | Source not in merged_tickets | 400 "was not merged into" | P1 |
| 4.5.4 | Merge divider deleted | No lingering divider messages | P1 |
| 4.5.5 | search_identifiers and associated_emails cleaned up | Source's entries removed from target | P1 |
| 4.5.6 | System notes added to both tickets | Notes describe unmerge | P1 |
| 4.5.7 | Source ticket fields (merged_into, merged_at, merged_by) unset | Fields removed | P1 |

### 4.6 Merge Suggestions (`GET /api/tickets/{ticket_id}/merge-suggestions`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 4.6.1 | Ticket with same-customer tickets within 2 hours | Suggestions returned | P0 |
| 4.6.2 | No matching tickets | Empty suggestions | P1 |
| 4.6.3 | Ticket without customer_email | Empty suggestions | P1 |
| 4.6.4 | Excludes merged/closed/resolved tickets | Only open tickets suggested | P1 |

### 4.7 Link Tickets (`POST /api/tickets/{ticket_id}/link`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 4.7.1 | Link as "related" | Bidirectional link created (related↔related) | P0 |
| 4.7.2 | Link as "blocks" | Forward=blocks, reverse=blocked_by | P0 |
| 4.7.3 | Link as "blocked_by" | Forward=blocked_by, reverse=blocks | P0 |
| 4.7.4 | Link as "duplicates" | duplicates↔duplicates | P1 |
| 4.7.5 | Missing target_ticket_id | 400 | P1 |
| 4.7.6 | Non-existent source or target | 404 | P0 |

### 4.8 Unlink Tickets (`DELETE /api/tickets/{ticket_id}/unlink/{target_ticket_id}`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 4.8.1 | Unlink existing link | Both sides cleaned up | P0 |
| 4.8.2 | Unlink non-existing link | No error (idempotent) | P1 |

### 4.9 Split Ticket (`POST /api/tickets/{ticket_id}/split`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 4.9.1 | Split at valid index | New ticket created, messages after index moved | P0 |
| 4.9.2 | Missing split_at_index | 400 "Split index required" | P1 |
| 4.9.3 | split_at_index=0 | 400 "Invalid split index" | P1 |
| 4.9.4 | split_at_index > total messages | 400 "Invalid split index" | P1 |
| 4.9.5 | New ticket has split_from reference | Field set correctly | P1 |
| 4.9.6 | Bidirectional links created (split_from↔split_to) | Links on both tickets | P1 |
| 4.9.7 | Customer info, tags, priority copied to new ticket | Fields inherited | P1 |
| 4.9.8 | Assignee set to user who split | Current user assigned | P1 |
| 4.9.9 | System notes on both tickets | Notes describe split | P1 |
| 4.9.10 | Changelog entry (change_type="split") | Entry exists | P1 |

### 4.10 Merge Consecutive (`POST /api/tickets/{ticket_id}/merge-consecutive`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 4.10.1 | Merge consecutive same-customer tickets within 24h | Tickets closed, content added as note | P0 |
| 4.10.2 | No customer email on ticket | 400 "no customer email" | P1 |
| 4.10.3 | No consecutive tickets found | 200 with merged_count=0 | P1 |
| 4.10.4 | Customer with linked_emails — all emails searched | All emails matched | P1 |

---

## 5. Internal Notes & Activity

### 5.1 Add Internal Note (`POST /api/tickets/{ticket_id}/notes`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 5.1.1 | Add note with content | Note created with message_id, author info | P0 |
| 5.1.2 | Non-existent ticket | 404 | P0 |
| 5.1.3 | Duplicate detection: same content by same user within 5 seconds | Returns existing note (no duplicate) | P1 |
| 5.1.4 | Note with @mentions | mentioned_users added to ticket, notifications sent | P0 |
| 5.1.5 | Self-mention excluded from notification | No notification to author | P1 |
| 5.1.6 | Note type "internal_note" (default) | type field set | P1 |
| 5.1.7 | Note type "reply" | type field set | P1 |
| 5.1.8 | Webhook triggered (ticket.note_added) | Webhook fired | P1 |
| 5.1.9 | Ticket updated_at refreshed | Timestamp updated | P1 |

### 5.2 Get Notes (`GET /api/tickets/{ticket_id}/notes`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 5.2.1 | Get notes with pagination | Returns messages of allowed types, sorted by created_at ASC | P0 |
| 5.2.2 | Page 1, limit 100 (defaults) | Correct subset | P1 |
| 5.2.3 | Custom page and limit | Correct pagination | P1 |
| 5.2.4 | Includes types: internal_note, reply, merge_divider, system, customer_reply | All types returned | P1 |

### 5.3 Activity Feed (`GET /api/tickets/{ticket_id}/activity-feed`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 5.3.1 | Get full activity feed | Includes creation, changelog, merges, sorted by timestamp | P0 |
| 5.3.2 | Non-existent ticket | 404 | P0 |
| 5.3.3 | Status change activity has correct description "Status: X → Y" | Formatted correctly | P1 |
| 5.3.4 | Assignee change resolves user names | Names instead of IDs | P1 |
| 5.3.5 | Merged ticket changelog included | Activities from merged tickets appear | P1 |
| 5.3.6 | Icons and field labels correct | Correct mapping | P2 |

### 5.4 Changelog (`GET /api/tickets/{ticket_id}/changelog`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 5.4.1 | Get changelog sorted by changed_at DESC | Most recent first | P0 |
| 5.4.2 | User names resolved for changed_by | Names populated | P1 |
| 5.4.3 | Non-existent ticket | 404 | P0 |

### 5.5 Ticket Metadata (`GET /api/tickets/{ticket_id}/metadata`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 5.5.1 | Get metadata for existing ticket | Returns timestamps, stats (changelog_entries, notes_count), custom_fields | P0 |
| 5.5.2 | Non-existent ticket | 404 | P0 |

---

## 6. Tags & Starred Tickets

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 6.1 | Add tags (`POST /api/tickets/{ticket_id}/tags`) | Tags appended (no duplicates) | P0 |
| 6.2 | Remove tag (`DELETE /api/tickets/{ticket_id}/tags/{tag}`) | Tag removed | P0 |
| 6.3 | Add tag to non-existent ticket | 404 | P1 |
| 6.4 | Remove non-existent tag | No error (tag just not present) | P2 |
| 6.5 | Get starred tickets (`GET /api/tickets/starred`) | All tickets with is_starred=true, sorted by updated_at DESC | P0 |
| 6.6 | Get escalation counts (`GET /api/tickets/escalation-counts`) | Counts grouped by L1/L2/L3 and status, excludes merged/resolved/closed | P1 |

---

## 7. Team Management

### 7.1 Team CRUD

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 7.1.1 | Create team (`POST /api/teams`) | team_id generated, defaults applied | P0 |
| 7.1.2 | List teams (`GET /api/teams`) | All teams returned | P0 |
| 7.1.3 | Get team detail (`GET /api/teams/{team_id}`) | Full team with member details, on-shift info | P0 |
| 7.1.4 | Update team (`PUT /api/teams/{team_id}`) | Fields updated | P0 |
| 7.1.5 | Delete team (`DELETE /api/teams/{team_id}`) | Team removed | P0 |
| 7.1.6 | Non-existent team | 404 | P0 |

### 7.2 Team Members

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 7.2.1 | Add member (`POST /api/teams/{team_id}/members`) | user_id added to members array | P0 |
| 7.2.2 | Add duplicate member | No duplicate (idempotent) or 400 | P1 |
| 7.2.3 | Remove member (`DELETE /api/teams/{team_id}/members/{user_id}`) | Member removed | P0 |
| 7.2.4 | Get team tickets (`GET /api/teams/{team_id}/tickets`) | Paginated tickets filtered by team_id | P0 |
| 7.2.5 | Team tickets with status filter | Only matching status | P1 |
| 7.2.6 | Team tickets with unassigned_only=true | Only unassigned tickets | P1 |

---

## 8. Shift Management

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 8.1 | Create shift (`POST /api/shifts`) | shift_id generated, team linked | P0 |
| 8.2 | List shifts (`GET /api/shifts`) | All shifts, optionally filtered by team_id | P0 |
| 8.3 | Get shift (`GET /api/shifts/{shift_id}`) | Full shift detail | P0 |
| 8.4 | Update shift (`PUT /api/shifts/{shift_id}`) | Fields updated | P0 |
| 8.5 | Delete shift (`DELETE /api/shifts/{shift_id}`) | Shift removed | P0 |
| 8.6 | Assign user to shift (`POST /api/shifts/{shift_id}/assign`) | User-shift mapping created | P0 |
| 8.7 | Get on-shift members (`GET /api/shifts/on-shift`) | Users currently on shift based on time/day | P0 |
| 8.8 | Shift boundary: user at edge of start/end time | Correct inclusion/exclusion | P1 |
| 8.9 | Weekend shift (days_of_week includes 6,7) | Correctly active on weekends | P1 |
| 8.10 | Shift spanning midnight (start > end, e.g., 22:00-06:00) | Handles overnight correctly | P2 |

---

## 9. Leave Management

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 9.1 | Create leave (`POST /api/leaves`) | Leave created with auto-approved status | P0 |
| 9.2 | List leaves (`GET /api/leaves`) | Filtered by user_id, date range, status, type | P0 |
| 9.3 | Update leave (`PUT /api/leaves/{leave_id}`) | Fields updated, days recalculated | P0 |
| 9.4 | Delete leave (`DELETE /api/leaves/{leave_id}`) | Leave removed | P0 |
| 9.5 | Half-day leave | days calculated as 0.5 | P1 |
| 9.6 | Multi-day leave (inclusive) | Correct day count (start=01, end=03 = 3 days) | P1 |
| 9.7 | Team calendar (`GET /api/leaves/calendar`) | Calendar with conflict levels per day | P1 |
| 9.8 | Conflict detection (3+ people out) | conflict_level="high" | P1 |
| 9.9 | User leave summary by year | Grouped by leave type with totals | P1 |
| 9.10 | Real-time broadcast on leave create/update/delete | Socket.IO events emitted | P2 |

---

## 10. Customer Management

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 10.1 | List customers with search | Searches name, email, company, customer_id | P0 |
| 10.2 | List with customer_type filter (b2b/b2c) | Filtered correctly | P1 |
| 10.3 | List with priority_level filter | Filtered correctly | P1 |
| 10.4 | Each customer includes stats (total/open/resolved tickets, avg_csat) | Stats computed from aggregation | P0 |
| 10.5 | Get customer detail | Full stats, recent tickets, CSAT history, assigned agent details | P0 |
| 10.6 | Create customer | customer_id generated (CUST-XXXXXX), domain extracted, B2B/B2C auto-detected | P0 |
| 10.7 | Create with duplicate email | 400 "already exists" | P0 |
| 10.8 | Update customer | Fields updated, customer.updated webhook triggered | P0 |
| 10.9 | Setting company_domain upgrades B2C→B2B | customer_type auto-updated | P1 |
| 10.10 | Link email (`POST /api/customers/{id}/link-email`) | Email added to linked_emails | P0 |
| 10.11 | Link email already linked to another customer | 400 "Use merge instead" | P1 |
| 10.12 | Link email already linked to this customer | 400 "already linked" | P1 |
| 10.13 | Unlink email (`DELETE /api/customers/{id}/unlink-email/{email}`) | Email removed | P0 |
| 10.14 | Cannot unlink primary email | 400 "Cannot unlink primary email" | P0 |
| 10.15 | Merge customers (`POST /api/customers/merge`) | Source deleted, emails/tags/agents/notes/payments/custom_fields merged to target | P0 |
| 10.16 | Merge: source not found | 404 | P1 |
| 10.17 | Merge: target not found | 404 | P1 |
| 10.18 | Merge: net_payments summed | Correct total | P1 |
| 10.19 | Merge: custom_fields (target takes precedence) | Correct merge | P1 |
| 10.20 | Get customer tickets across all linked emails | All emails searched | P0 |
| 10.21 | B2B prospects list sorted by engagement score | Correct sorting | P1 |

---

## 11. Filters & Custom Inboxes

### 11.1 Advanced Filtering (`POST /api/tickets/filter`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 11.1.1 | Simple AND filter: status=open AND priority=high | Correct tickets returned | P0 |
| 11.1.2 | OR filter group | Correct tickets | P0 |
| 11.1.3 | Nested filter groups | Correct boolean logic | P1 |
| 11.1.4 | Operator: is (equals) | Exact match | P0 |
| 11.1.5 | Operator: is_not | Excludes value | P0 |
| 11.1.6 | Operator: is_one_of | Value in list | P0 |
| 11.1.7 | Operator: contains | Substring match | P1 |
| 11.1.8 | Operator: not_contains | No substring | P1 |
| 11.1.9 | Operator: is_empty / is_not_empty | Null/not-null checks | P1 |
| 11.1.10 | Operator: before / after (dates) | Date comparison | P1 |
| 11.1.11 | Pagination with filter | Correct page/limit | P0 |
| 11.1.12 | Sort by created_at, updated_at, priority | Correct sorting | P1 |
| 11.1.13 | Filter on custom_fields | Custom field values matched | P2 |

### 11.2 Custom Inboxes

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 11.2.1 | Create inbox (`POST /api/inboxes`) | inbox_id generated, filter_tree stored | P0 |
| 11.2.2 | List inboxes (`GET /api/inboxes`) | Returns user's own + shared inboxes | P0 |
| 11.2.3 | Get inbox (`GET /api/inboxes/{inbox_id}`) | Full inbox with filter_tree | P0 |
| 11.2.4 | Update inbox (`PUT /api/inboxes/{inbox_id}`) | Fields updated | P0 |
| 11.2.5 | Delete inbox (`DELETE /api/inboxes/{inbox_id}`) | Inbox removed | P0 |
| 11.2.6 | Share inbox (`POST /api/inboxes/{inbox_id}/share`) | user_ids added to shared_with | P0 |
| 11.2.7 | Unshare inbox | user_ids removed | P1 |
| 11.2.8 | Execute inbox filter (get matching tickets) | Filter applied, tickets returned | P0 |
| 11.2.9 | Only owner can edit/delete | 403 for non-owners | P1 |

---

## 12. CSAT

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 12.1 | Send CSAT survey (`POST /api/csat/send`) | Token generated, response record created | P0 |
| 12.2 | Submit rating via token (`POST /api/csat/{token}/rate`) | Rating saved (1-5) | P0 |
| 12.3 | Submit feedback via token (`POST /api/csat/{token}/feedback`) | Feedback text saved | P0 |
| 12.4 | Invalid/expired token | 404 or 400 | P0 |
| 12.5 | Rating out of range (0 or 6) | 422 (ge=1, le=5) | P1 |
| 12.6 | Get CSAT analytics | Avg rating, distribution, trends | P1 |
| 12.7 | CSAT page renders for public (no auth) | `/csat/:token` route is public | P0 |

---

## 13. Canned Responses

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 13.1 | Create canned response | response_id generated, shortcode validated | P0 |
| 13.2 | Shortcode regex: only a-z, A-Z, 0-9, _, - | Valid shortcodes accepted | P1 |
| 13.3 | Invalid shortcode (spaces, special chars) | 422 pattern validation | P1 |
| 13.4 | List canned responses | Returns all (global + personal) | P0 |
| 13.5 | Update canned response | Fields updated | P0 |
| 13.6 | Delete canned response | Response removed | P0 |
| 13.7 | Scope: global vs personal | Correct visibility | P1 |
| 13.8 | Title max length 100, content max length 5000 | Validation enforced | P1 |

---

## 14. Feature Requests

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 14.1 | Create feature request | feature_id generated | P0 |
| 14.2 | List feature requests with sorting | Default sort, status filter | P0 |
| 14.3 | Update feature request (status, priority, etc.) | Fields updated | P0 |
| 14.4 | Vote on feature request | Vote count incremented | P0 |
| 14.5 | Link ticket to feature request | linked_ticket_id set | P1 |
| 14.6 | Delete feature request | Request removed | P0 |
| 14.7 | Request types: feature, bug, improvement | All accepted | P1 |

---

## 15. SLA Policies & Escalation Rules

### 15.1 SLA Policies

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 15.1.1 | Get SLA policies (`GET /api/sla/policies`) | Returns active policies | P0 |
| 15.1.2 | Update SLA policies (admin) | Policies updated | P0 |
| 15.1.3 | Priority-specific SLAs (urgent: 15min first response) | Correct thresholds | P1 |
| 15.1.4 | Business hours calculation | SLA paused outside business hours | P1 |
| 15.1.5 | Get SLA status per ticket (`GET /api/sla/tickets/{ticket_id}`) | Returns current SLA status (met/at_risk/breached) | P0 |

### 15.2 Escalation Rules

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 15.2.1 | Create escalation rule | rule_id generated | P0 |
| 15.2.2 | Trigger types: first_response_warning, first_response_breach, resolution_warning, resolution_breach, idle_ticket | All accepted | P1 |
| 15.2.3 | trigger_threshold validation (1-10000) | Enforced | P1 |
| 15.2.4 | Priority filter (only for specific priorities) | Correct filtering | P1 |
| 15.2.5 | List escalation rules | Returns all with active filter | P0 |
| 15.2.6 | Update escalation rule | Fields updated | P0 |
| 15.2.7 | Delete escalation rule | Rule removed | P0 |

---

## 16. Admin & Settings

### 16.1 Custom Fields

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 16.1.1 | Create custom field (text, number, select, date, boolean) | field_id generated | P0 |
| 16.1.2 | List custom fields | All fields returned | P0 |
| 16.1.3 | Update custom field | Fields updated | P0 |
| 16.1.4 | Delete custom field | Field removed | P0 |
| 16.1.5 | Select field with options | Options array stored | P1 |
| 16.1.6 | Entity type: ticket or user | Correctly scoped | P1 |

### 16.2 Routing Rules (Admin)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 16.2.1 | Create routing rule | rule_id generated | P0 |
| 16.2.2 | List routing rules | All rules, sorted by priority | P0 |
| 16.2.3 | Update routing rule | Fields updated | P0 |
| 16.2.4 | Delete routing rule | Rule removed | P0 |
| 16.2.5 | Assignment methods: round_robin, manual, etc. | Accepted | P1 |

### 16.3 Admin Settings

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 16.3.1 | Get settings (`GET /api/admin/settings`) | Returns current settings | P0 |
| 16.3.2 | Update settings (`PUT /api/admin/settings`) | Settings persisted | P0 |
| 16.3.3 | Admin role required | 403 for non-admins | P0 |

---

## 17. Analytics & Reporting

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 17.1 | Dashboard summary (`GET /api/analytics/summary`) | Total tickets, by status, by priority counts | P0 |
| 17.2 | Overview metrics (`GET /api/analytics/overview`) | Ticket volume trends, resolution rates | P0 |
| 17.3 | Agent performance (`GET /api/analytics/agents`) | Per-agent stats (tickets handled, avg resolution time, CSAT) | P0 |
| 17.4 | Date range filtering on analytics | Correct scoping | P1 |
| 17.5 | Empty data period | Zero counts, no errors | P1 |
| 17.6 | Large date range performance | Responds within acceptable time | P2 |

---

## 18. Search & Presence

### 18.1 Search (`POST /api/search`)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 18.1.1 | Full-text search across all entities | Results by category (tickets, users, teams, customers, commands) | P0 |
| 18.1.2 | Search with operator `status:open` | Tickets filtered by status | P0 |
| 18.1.3 | Search with operator `priority:urgent` | Priority filter applied | P1 |
| 18.1.4 | Search with operator `assigned:me` | Tickets assigned to current user | P1 |
| 18.1.5 | Search with `type:ticket` filter | Only ticket results | P1 |
| 18.1.6 | Ticket ID search (TKT-XXXXXX) | Direct match | P0 |
| 18.1.7 | Merged ticket searchable by original ID | search_identifiers checked | P1 |
| 18.1.8 | Search suggestions / autocomplete | Operator completions returned | P1 |
| 18.1.9 | Empty query | Validation error or empty results | P1 |
| 18.1.10 | Command search (platform features) | Matching commands returned | P1 |
| 18.1.11 | Customer search by email | Aggregation returns ticket counts | P1 |
| 18.1.12 | Fuzzy matching (partial word overlap) | Relevant results with lower scores | P2 |

### 18.2 Presence & Notifications

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 18.2.1 | Get presence stats | Online user count and list | P1 |
| 18.2.2 | Get users viewing ticket | List of users at ticket location | P1 |
| 18.2.3 | Get notifications | User's notifications list | P1 |
| 18.2.4 | Mark notification as read | Status updated | P1 |

---

## 19. Webhooks

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 19.1 | Create webhook (`POST /api/webhooks`) | webhook_id generated | P0 |
| 19.2 | URL validation: must start with http/https | Invalid URL rejected | P0 |
| 19.3 | Event validation: only valid event types | Invalid events rejected | P0 |
| 19.4 | List webhooks | All webhooks for user | P0 |
| 19.5 | Update webhook | Fields updated | P0 |
| 19.6 | Delete webhook | Webhook removed | P0 |
| 19.7 | Webhook delivery with HMAC signature | X-Webhook-Signature header correct | P1 |
| 19.8 | Webhook retry on failure (3 attempts with delays 0, 5, 30s) | Retries logged | P1 |
| 19.9 | Webhook delivery logs | Logs with attempts, status, response | P1 |
| 19.10 | SSRF protection: private IP blocked | Delivery blocked, log entry with "blocked" status | P0 |
| 19.11 | SSRF: metadata endpoint (169.254.169.254) blocked | Blocked | P0 |
| 19.12 | SSRF: localhost blocked | Blocked | P0 |
| 19.13 | Webhook secret (optional) | Signature only included when secret set | P1 |
| 19.14 | Custom headers forwarded | Extra headers included in request | P1 |
| 19.15 | Webhook toggle active/inactive | Inactive webhooks not triggered | P1 |

---

## 20. Exports

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 20.1 | Export tickets as JSON | StreamingResponse with correct Content-Disposition | P0 |
| 20.2 | Export tickets as CSV | CSV with all fields flattened | P0 |
| 20.3 | Export with date range filter | Only matching tickets | P1 |
| 20.4 | Export with status filter | Only matching statuses | P1 |
| 20.5 | Include notes flag | Notes included/excluded | P1 |
| 20.6 | Include changelog flag | Changelog included/excluded | P1 |
| 20.7 | Include CSAT flag | CSAT data included/excluded | P1 |
| 20.8 | Export users | User data exported | P1 |
| 20.9 | Export teams | Team data exported | P1 |
| 20.10 | Empty export (no matching data) | "No data to export" response | P1 |

---

## 21. Email Integration

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 21.1 | Upload file attachment | File saved to /uploads, URL returned | P0 |
| 21.2 | File size limit enforcement | Oversized files rejected (50MB max) | P1 |
| 21.3 | Email-to-ticket conversion | Ticket created from email data | P0 |
| 21.4 | Email thread tracking (RFC Message-ID) | Thread linked via email_rfc_message_id | P1 |
| 21.5 | Get ticket email replies | Replies sorted by created_at ASC | P1 |
| 21.6 | Tickets by email lookup | Case-insensitive email match across customer_email, email_sender, email_from | P0 |
| 21.7 | Related tickets by same customer email | Up to 20 related tickets, excludes self | P0 |
| 21.8 | Email address extraction from "Name <email>" format | Correct extraction | P1 |
| 21.9 | HTML to plain text conversion | Scripts/styles removed, entities decoded | P1 |
| 21.10 | HTML sanitization for display | XSS vectors removed, safe tags preserved | P0 |

---

## 22. Knowledge Base

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 22.1 | List KB articles | Articles returned | P0 |
| 22.2 | Create KB article | Article created | P0 |
| 22.3 | Update KB article | Content updated | P0 |
| 22.4 | Delete KB article | Article removed | P0 |
| 22.5 | Public docs page renders (`/`, `/docs/:slug`) | MDX content rendered correctly | P0 |
| 22.6 | KB editor (protected, `/dashboard/kb-editor`) | Only authenticated users can access | P0 |
| 22.7 | KB search | Articles searchable by content | P1 |

---

## 23. Customer Portal

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 23.1 | Portal home loads (`/portal`) | Categories and content displayed | P0 |
| 23.2 | Portal category browsing (`/portal/category/:slug`) | Articles in category shown | P0 |
| 23.3 | Portal ticket submission (`/portal/submit`) | Ticket created via portal | P0 |
| 23.4 | Portal login | Customer authenticated | P0 |
| 23.5 | Portal my-tickets list | Customer's tickets shown | P0 |
| 23.6 | Portal ticket detail (`/portal/my-tickets/:ticketId`) | Full ticket with conversation | P0 |
| 23.7 | Default categories seeded on startup | seed_default_categories() runs | P1 |
| 23.8 | Portal auth context (PortalAuthContext) | Login/logout state management | P1 |

---

## 24. Real-time / WebSocket

### 24.1 Connection Lifecycle

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 24.1.1 | Connect via Socket.IO | 'connected' event received with sid and auth_timeout=30 | P0 |
| 24.1.2 | Authenticate within 30 seconds | 'authenticated' event with user_id and online_count | P0 |
| 24.1.3 | Fail to authenticate within 30 seconds | 'auth_error' + disconnect | P0 |
| 24.1.4 | Authenticate with invalid user_id (empty) | 'auth_error' "user_id required" | P1 |
| 24.1.5 | Authenticate with user_id >100 chars | 'auth_error' "Invalid user_id" | P1 |
| 24.1.6 | Authenticate with user_id containing special chars | 'auth_error' "Invalid user_id format" | P1 |
| 24.1.7 | Data >65KB in authenticate | 'auth_error' "Data too large" | P1 |
| 24.1.8 | Disconnect cleanup | Presence removed, 'user:offline' broadcast | P0 |
| 24.1.9 | User info sanitized (name≤100, email≤255, picture≤500) | Truncated values stored | P2 |

### 24.2 Presence & Location

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 24.2.1 | Join location (ticket:TKT-000001) | 'presence:sync' with current users, 'user:joined' to room | P0 |
| 24.2.2 | Leave location | 'user:left' broadcast to room | P0 |
| 24.2.3 | Get presence stats API | Online users listed | P1 |
| 24.2.4 | Get users viewing specific ticket | Correct users returned | P1 |

### 24.3 Typing Indicators

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 24.3.1 | Start typing | 'user:typing' broadcast to room (is_typing=true) | P0 |
| 24.3.2 | Stop typing | 'user:typing' with is_typing=false | P0 |
| 24.3.3 | Typing auto-expires after 5 seconds (TTL) | Typing status cleared automatically | P1 |
| 24.3.4 | Typing published to other instances via pub/sub | Cross-instance delivery | P2 |

### 24.4 Broadcasts

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 24.4.1 | Ticket created → 'ticket:created' to all clients | Event received | P0 |
| 24.4.2 | Ticket updated → 'ticket:update' to all clients | Event received with ticket data | P0 |
| 24.4.3 | Ticket deleted → 'ticket:deleted' to all clients | Event received | P0 |
| 24.4.4 | Mention notification → 'notification:mention' to specific user | Only mentioned user receives | P0 |
| 24.4.5 | Leave created/updated/deleted broadcasts | Events received | P1 |
| 24.4.6 | Cross-instance message deduplication (source_instance check) | No loops | P1 |
| 24.4.7 | Heartbeat keeps connection alive | Presence TTL extended | P1 |

---

## 25. Frontend UI & Navigation

### 25.1 Layout & Navigation

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 25.1.1 | Sidebar renders all navigation items | Dashboard, Tickets (All/Open/Waiting/Closed/Starred), Teams, Customers, etc. | P0 |
| 25.1.2 | Sidebar collapse/expand | Toggles correctly, persists preference | P0 |
| 25.1.3 | Active route highlighted in sidebar | Correct item highlighted | P0 |
| 25.1.4 | Theme toggle (dark/light) | Theme switches, persists across sessions | P0 |
| 25.1.5 | Command Palette (Cmd+K / Ctrl+K) | Opens/closes correctly | P0 |
| 25.1.6 | Keyboard shortcuts help (?) | Opens help modal | P1 |
| 25.1.7 | Escape closes overlays | Modals, drawers, command palette close | P0 |
| 25.1.8 | Responsive design: mobile viewport | Layout adapts | P1 |
| 25.1.9 | Responsive design: tablet viewport | Layout adapts | P1 |
| 25.1.10 | Protected routes redirect to /login when unauthenticated | Redirect works | P0 |
| 25.1.11 | Auth callback handles URL fragment session_id | AuthCallback component renders | P0 |

### 25.2 Dashboard

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 25.2.1 | Dashboard loads with ticket stats | Metric cards populated | P0 |
| 25.2.2 | Kanban board renders all status columns | Todo, In Progress, Waiting, Review, Resolved | P0 |
| 25.2.3 | Drag-and-drop ticket between columns | Status updated, reorder API called | P0 |
| 25.2.4 | Click ticket card opens TicketDrawer | Drawer slides in with ticket details | P0 |

### 25.3 Ticket Views

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 25.3.1 | All Tickets page loads with paginated list | Table renders, pagination works | P0 |
| 25.3.2 | Open Tickets page — shows only open statuses | Correct filtering | P0 |
| 25.3.3 | Waiting Tickets page — shows only waiting | Correct filtering | P0 |
| 25.3.4 | Closed Tickets page — shows only resolved/closed | Correct filtering | P0 |
| 25.3.5 | Starred Tickets page | Shows is_starred=true tickets | P0 |
| 25.3.6 | Custom Inbox page (by inbox_id) | Filter applied, tickets shown | P0 |
| 25.3.7 | Individual ticket URL (/ticket/:ticketId) | Direct ticket view loads | P0 |
| 25.3.8 | Infinite scroll / pagination on list views | Loads more data on scroll/click | P1 |

### 25.4 Ticket Drawer

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 25.4.1 | Drawer shows ticket details (title, status, priority, assignee, tags) | All fields rendered | P0 |
| 25.4.2 | Activity timeline renders notes, system messages, replies | All message types shown | P0 |
| 25.4.3 | Add internal note with rich text editor | Note submitted, appears in timeline | P0 |
| 25.4.4 | @mention autocomplete in note editor | User suggestions appear on @ type | P0 |
| 25.4.5 | Change status inline | Status updated, system message appears | P0 |
| 25.4.6 | Change priority inline | Priority updated | P0 |
| 25.4.7 | Change assignee | Assignee updated | P0 |
| 25.4.8 | Star/unstar ticket | is_starred toggled | P1 |
| 25.4.9 | View/edit tags | Tags displayed and editable | P1 |
| 25.4.10 | Merge ticket action | Merge modal opens | P1 |
| 25.4.11 | Link ticket action | Link modal opens | P1 |
| 25.4.12 | View linked tickets | Links shown with type labels | P1 |
| 25.4.13 | View merged ticket dividers | Color-coded merge sections | P1 |
| 25.4.14 | Custom fields displayed and editable | Custom fields from admin config | P1 |
| 25.4.15 | Real-time updates while drawer is open | Live updates via Socket.IO | P1 |

### 25.5 Create Ticket Modal

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 25.5.1 | Modal opens from "New Ticket" button | Form renders | P0 |
| 25.5.2 | Submit with valid data | Ticket created, modal closes, list refreshes | P0 |
| 25.5.3 | Form validation: empty title prevents submit | Submit button disabled or error shown | P0 |
| 25.5.4 | All form fields: title, description, priority, status, tags, customer_email | All rendered and submittable | P0 |
| 25.5.5 | Cancel closes modal without creating | No ticket created | P1 |

### 25.6 Filter Builder

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 25.6.1 | Add filter condition | Condition row appears | P0 |
| 25.6.2 | Remove filter condition | Row removed | P0 |
| 25.6.3 | Apply filter | Tickets filtered, results shown | P0 |
| 25.6.4 | Save as custom inbox | Inbox created with filter_tree | P0 |
| 25.6.5 | AND/OR toggle between conditions | Logic changes | P1 |
| 25.6.6 | Multiple condition groups | Nested filtering | P1 |

### 25.7 Other Pages

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 25.7.1 | Teams page loads with team list | Teams rendered | P0 |
| 25.7.2 | Customers page loads with customer list | Customers with stats rendered | P0 |
| 25.7.3 | Analytics page loads with charts/metrics | Visualizations rendered | P0 |
| 25.7.4 | Leave page loads with calendar/list | Leave management functional | P0 |
| 25.7.5 | Feature Requests page loads | Requests listed, voting works | P0 |
| 25.7.6 | Canned Responses page loads | Responses listed, CRUD works | P0 |
| 25.7.7 | Knowledge Base page loads | Articles listed | P0 |
| 25.7.8 | Admin page loads (admin role only) | Admin settings accessible | P0 |
| 25.7.9 | Settings page loads | Settings form rendered | P0 |
| 25.7.10 | Profile page loads | User profile displayed | P0 |
| 25.7.11 | Search results page | Results categorized and linked | P0 |
| 25.7.12 | CSAT page (public) | Rating form renders at /csat/:token | P0 |

---

## 26. Security & Input Validation

### 26.1 XSS Prevention

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 26.1.1 | `<script>alert('xss')</script>` in ticket title | Sanitized, script removed | P0 |
| 26.1.2 | `<img onerror=alert(1) src=x>` in description | Event handler stripped | P0 |
| 26.1.3 | HTML in internal notes — safe tags preserved | Bold, italic, links kept; scripts removed | P0 |
| 26.1.4 | `<iframe>` injection | Tag removed entirely | P0 |
| 26.1.5 | JavaScript: protocol in links | Sanitized | P1 |

### 26.2 SSRF Protection (Webhooks)

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 26.2.1 | Webhook URL pointing to 127.0.0.1 | Blocked | P0 |
| 26.2.2 | Webhook URL pointing to 10.x.x.x | Blocked | P0 |
| 26.2.3 | Webhook URL pointing to 192.168.x.x | Blocked | P0 |
| 26.2.4 | Webhook URL pointing to 169.254.169.254 | Blocked | P0 |
| 26.2.5 | Webhook URL with non-http scheme (ftp://) | Rejected | P0 |
| 26.2.6 | Webhook URL with no hostname | Rejected | P0 |
| 26.2.7 | Webhook URL that doesn't resolve (DNS) | Rejected | P1 |

### 26.3 Input Validation

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 26.3.1 | SQL injection in search query | No SQL execution (MongoDB, but test NoSQL injection) | P0 |
| 26.3.2 | MongoDB injection via $gt, $regex in request body | Pydantic validation prevents | P0 |
| 26.3.3 | Max request body size (50MB) | 413 for oversized requests | P1 |
| 26.3.4 | Invalid email format in customer_email | 422 EmailStr validation | P1 |
| 26.3.5 | Field length limits enforced (title 500, description 50000, etc.) | 422 on overflow | P1 |

### 26.4 Authentication Security

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 26.4.1 | Session cookie is httponly + secure + samesite=none | Cookie attributes correct | P0 |
| 26.4.2 | Session expires after 7 days | Expired session rejected | P0 |
| 26.4.3 | API key bcrypt verification (timing-safe) | No timing leaks | P1 |
| 26.4.4 | Rate limiting: 1000/hour, 100/minute global | Enforced per-IP | P0 |
| 26.4.5 | Rate limiting: 10/minute on auth/session | Enforced | P0 |
| 26.4.6 | Rate limiting: 10/hour on API key creation | Enforced | P1 |
| 26.4.7 | X-Request-ID header returned in all responses | Present | P1 |
| 26.4.8 | CORS allows only configured origins | Blocked from unauthorized origins | P0 |

---

## 27. Performance & Scalability

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 27.1 | List 1000+ tickets with pagination | Response within 2 seconds | P1 |
| 27.2 | Search across all entities with 10K+ tickets | Response within 3 seconds | P1 |
| 27.3 | Concurrent ticket updates (10 users updating different tickets) | No race conditions, all updates applied | P1 |
| 27.4 | WebSocket with 50 concurrent connections | All connections maintained | P2 |
| 27.5 | MongoDB indexes used for common queries | Explain plan shows index usage | P2 |
| 27.6 | Auto-close background task performance | Handles 1000+ resolved tickets efficiently | P2 |
| 27.7 | Bulk update 100 tickets | Completes within 5 seconds | P1 |
| 27.8 | Customer list with stats aggregation (1000+ customers) | Response within 5 seconds | P2 |
| 27.9 | Export 10K tickets as JSON | Streaming response, no memory issues | P2 |

---

## 28. Error Handling & Edge Cases

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 28.1 | Global exception handler catches unhandled errors | 500 with request_id, detail="An internal error occurred" | P0 |
| 28.2 | Request with X-Request-ID header | Same ID returned in response | P1 |
| 28.3 | Request without X-Request-ID | Generated UUID returned | P1 |
| 28.4 | MongoDB connection failure during health check | 503 with "unhealthy" status | P0 |
| 28.5 | Health check with missing required collections | "warning" status with missing list | P1 |
| 28.6 | Emergent Auth API down during login | 500 error | P1 |
| 28.7 | Concurrent creation of same customer (race condition) | Only one created (unique index) | P1 |
| 28.8 | Update ticket that was just deleted | 404 | P1 |
| 28.9 | Merge ticket into itself | Should be prevented | P1 |
| 28.10 | Split ticket with 0 messages | 400 "Invalid split index" | P1 |
| 28.11 | Link ticket to itself | Should be prevented or handled | P1 |
| 28.12 | Very long tag string (boundary: exactly 100 chars) | Accepted | P2 |
| 28.13 | Unicode characters in all text fields | Handled correctly | P1 |
| 28.14 | Empty string vs null vs missing field behavior | Consistent handling | P2 |

---

## 29. Data Integrity & Consistency

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 29.1 | Ticket ID uniqueness (unique index) | Duplicate insert fails | P0 |
| 29.2 | User email uniqueness (unique sparse index) | Duplicate insert fails | P0 |
| 29.3 | Session token uniqueness (unique index) | No duplicate sessions | P0 |
| 29.4 | API key SHA-256 uniqueness | No duplicate keys | P0 |
| 29.5 | Team ID uniqueness | No duplicate teams | P0 |
| 29.6 | Session TTL auto-expiry (MongoDB TTL index) | Expired sessions auto-deleted | P1 |
| 29.7 | CSAT token TTL auto-expiry | Expired tokens auto-deleted | P1 |
| 29.8 | Presence connection TTL (120 seconds) | Stale connections cleaned up | P1 |
| 29.9 | Counter collection atomicity (ticket_id generation) | No gaps or duplicates under concurrency | P0 |
| 29.10 | Changelog entries always written for ticket changes | No orphaned changes | P1 |
| 29.11 | Ticket customer_id linked when customer_email provided | Consistent linking | P1 |
| 29.12 | Domain extracted correctly from various email formats | name@domain.com, "Name" <email>, etc. | P1 |
| 29.13 | B2C email detection (gmail, yahoo, hotmail, etc.) | All B2C_EMAIL_DOMAINS matched | P1 |

---

## 30. Atlas Import

| # | Test Case | Expected Result | Priority |
|---|-----------|-----------------|----------|
| 30.1 | Import conversations from Atlas API | Tickets created with atlas_ prefixed metadata | P0 |
| 30.2 | Status mapping (OPEN→todo, CLOSED→resolved, etc.) | Correct mapping | P1 |
| 30.3 | Priority mapping (NO_PRIORITY→medium, URGENT→urgent) | Correct mapping | P1 |
| 30.4 | Message type mapping (AGENT→reply, CUSTOMER→customer_reply) | Correct mapping | P1 |
| 30.5 | Deduplication on re-import (atlas_conversation_id) | Duplicates skipped | P0 |
| 30.6 | Customer auto-creation during import | Customers linked correctly | P1 |
| 30.7 | Agent mapping by email | Agents matched to Trinity users | P1 |
| 30.8 | Import with status filter | Only matching conversations imported | P1 |
| 30.9 | Import with date range filter | Only matching period imported | P1 |
| 30.10 | Error handling: individual conversation failure | Continues, error accumulated in summary | P1 |
| 30.11 | Import summary returned with counts | tags_fetched, conversations_imported, errors, etc. | P1 |

---

## Test Case Summary

| Category | Test Cases | P0 | P1 | P2 |
|----------|-----------|-----|-----|-----|
| Authentication & Authorization | 35 | 16 | 14 | 5 |
| Ticket CRUD | 40 | 16 | 20 | 4 |
| Assignment & Routing | 22 | 8 | 14 | 0 |
| Ticket Operations | 42 | 14 | 26 | 2 |
| Notes & Activity | 17 | 5 | 11 | 1 |
| Tags & Starred | 6 | 2 | 3 | 1 |
| Team Management | 12 | 8 | 4 | 0 |
| Shift Management | 10 | 6 | 2 | 2 |
| Leave Management | 10 | 4 | 5 | 1 |
| Customer Management | 21 | 8 | 13 | 0 |
| Filters & Custom Inboxes | 22 | 8 | 12 | 2 |
| CSAT | 7 | 3 | 4 | 0 |
| Canned Responses | 8 | 3 | 5 | 0 |
| Feature Requests | 7 | 3 | 4 | 0 |
| SLA & Escalation | 12 | 4 | 8 | 0 |
| Admin & Settings | 11 | 5 | 6 | 0 |
| Analytics | 6 | 2 | 3 | 1 |
| Search & Presence | 16 | 3 | 12 | 1 |
| Webhooks | 15 | 5 | 10 | 0 |
| Exports | 10 | 2 | 8 | 0 |
| Email Integration | 10 | 3 | 7 | 0 |
| Knowledge Base | 7 | 4 | 3 | 0 |
| Customer Portal | 8 | 6 | 2 | 0 |
| Real-time / WebSocket | 18 | 7 | 8 | 3 |
| Frontend UI & Navigation | 35 | 22 | 11 | 2 |
| Security & Input Validation | 21 | 11 | 9 | 1 |
| Performance & Scalability | 9 | 0 | 5 | 4 |
| Error Handling & Edge Cases | 14 | 2 | 9 | 3 |
| Data Integrity | 13 | 5 | 8 | 0 |
| Atlas Import | 11 | 2 | 9 | 0 |

**TOTAL: ~464 test cases (P0: 186, P1: 260, P2: 31)**

---

## Execution Strategy

### Phase 1: Smoke Tests (P0 only)
- Run all 186 P0 test cases
- Focus: Auth flow, ticket CRUD, basic navigation, critical security
- Target: 100% pass rate

### Phase 2: Functional Tests (P0 + P1)
- Run remaining 260 P1 test cases
- Focus: Edge cases, validation, integrations, real-time features
- Target: 95% pass rate

### Phase 3: Robustness Tests (P2 + Performance)
- Run 31 P2 test cases + performance benchmarks
- Focus: Scalability, boundary conditions, cross-instance behavior
- Target: 90% pass rate

---

*Generated: 2026-02-17*
*Coverage: 175+ API endpoints, 20+ frontend pages, 57 backend utility functions*
