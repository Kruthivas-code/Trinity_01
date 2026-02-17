# Production Readiness Plan

## Phase 1: Critical Security Fixes [COMPLETED]
- [x] Add `require_admin` to all admin.py routes (17 endpoints)
- [x] Fix portal category/plan CRUD authorization (`require_admin`)
- [x] Add `re.escape()` to customer/KB search regex (NoSQL injection fix)
- [x] Sanitize error messages in auth.py, email.py, knowledge_base.py
- [x] Externalize hardcoded CSAT base URL to environment variable
- [x] Add rate limiting to portal register (5/min) and login (10/min)
- [x] Strengthen portal password policy (8 chars, uppercase, digit)

## Phase 2: Performance & Scalability [COMPLETED]

### 2A. Fix N+1 Query Patterns (Critical)
**Problem:** Several endpoints run individual DB queries per item in a loop, causing O(N) database round-trips.

| File | Endpoint | Issue |
|------|----------|-------|
| `customers.py` | `GET /customers` (list) | Runs 2 aggregation pipelines per customer (ticket stats + CSAT stats) inside a for-loop |
| `analytics.py` | `GET /analytics/agents` | Runs 1 aggregation pipeline per agent inside a for-loop |
| `exports.py` | `POST /admin/export/tickets` | Runs up to 3 queries per ticket (notes, changelog, CSAT) in a for-loop |
| `exports.py` | `POST /admin/export/full` | Same as above — queries notes/changelog per ticket |
| `tickets.py` | `GET /tickets/{id}/activity-feed` | Queries `users_collection.find_one()` per changelog entry (assignee lookups) — partially mitigated by batch at end |
| `ticket_ops.py` | `POST /tickets/bulk-tag` | Runs 1-2 update_one calls per ticket instead of bulk write |
| `webhooks.py` | `POST /admin/trigger-auto-close` | Runs update_one + insert_one per ticket instead of using update_many + insert_many |
| `exports.py` | `GET /admin/export/analytics` | N+1 for agent name lookup inside loop |

### 2B. Add Missing Pagination / Enforce Limits (High)
**Problem:** Several endpoints return unbounded result sets, which will cause OOM or timeouts with large data.

| File | Endpoint | Issue |
|------|----------|-------|
| `tickets.py` | `GET /tickets/starred` | No pagination — returns ALL starred tickets |
| `tickets.py` | `GET /tickets/by-email/{email}` | No pagination — returns ALL tickets for a customer email |
| `tickets.py` | `GET /tickets/{id}/activity-feed` | No pagination — loads ALL changelog + messages |
| `tickets.py` | `GET /tickets/{id}/changelog` | No pagination — returns ALL changelog entries |
| `search_presence.py` | `GET /search/suggestions` | Uses unescaped `q` in regex (NoSQL injection) |
| `exports.py` | `POST /admin/export/tickets` | Loads ALL matching tickets into memory at once |

### 2C. Optimize Bulk Operations (Moderate)
**Problem:** Bulk operations use per-item updates instead of batch writes.

| File | Endpoint | Issue |
|------|----------|-------|
| `ticket_ops.py` | `POST /tickets/bulk-update` | Changelog inserts use per-item insert_one in a loop |
| `ticket_ops.py` | `POST /tickets/bulk-tag` | Per-item update_one instead of bulk write |
| `webhooks.py` | `POST /admin/trigger-auto-close` | Per-item update + insert instead of batch |
| `tickets.py` | `POST /tickets/reorder` | Per-item update_one for each ticket in status column |

### 2D. Search Suggestions Regex Injection (Security + Perf)
**Problem:** `search_presence.py` `GET /search/suggestions` passes user input `q` directly into `$regex` without `re.escape()`.

## Phase 3: Frontend Architecture
- [ ] Create centralized API client (axios interceptors, error handling)
- [ ] Break up TicketDrawer.js (3715 lines) into smaller components
- [ ] Add React Error Boundaries
- [ ] Remove console.log statements from production code

## Phase 4: Code Quality & DevOps
- [ ] Migrate Pydantic validators from v1 to v2 style
- [ ] Standardize API response format across all endpoints
- [ ] Remove duplicate KB modules (kb.py vs knowledge_base.py)
- [ ] Add production Dockerfile with proper multi-stage build

## Phase 5: Testing & Validation
- [ ] Add unit tests for critical business logic
- [ ] Add integration tests for auth flows
- [ ] Add load testing for identified bottleneck endpoints
- [ ] End-to-end test for ticket lifecycle
