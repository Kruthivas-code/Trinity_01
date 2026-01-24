# TickFlow - Development Plan

## Current Status: Phase 2 Frontend Implementation

---

## Phase 1: Foundation & Stabilization ✅ COMPLETE

### Completed
- [x] Sequential ticket IDs (TKT-000001 format)
- [x] Source tracking (email, manual, api, simulator, legacy)
- [x] Domain extraction from customer email
- [x] Tags system (add, remove on tickets)
- [x] API key authentication system
- [x] API key management UI in Settings
- [x] API key generation and revocation
- [x] Email simulator endpoint
- [x] Updated Pydantic models with new fields
- [x] Migrated existing tickets with tags/source fields
- [x] Full end-to-end testing (17 test steps passed)

---

## Phase 2: Team Structure & Basic Routing
**Status: BACKEND COMPLETE, FRONTEND IN PROGRESS**

### Backend ✅ Complete
- [x] Team CRUD (L1, L2, Specialist types)
- [x] User-to-team assignment (add/remove members)
- [x] Team inbox view endpoint
- [x] Round-robin ticket assignment
- [x] Internal notes on tickets (create/list)

### Frontend - In Progress
- [x] TeamsPage.js - Full implementation with:
  - Create team modal
  - Team cards with member list
  - Add/remove members
  - Delete teams
- [x] Internal Notes in TicketDrawer - Added:
  - Collapsible notes section
  - Add note form with Enter key support
  - Notes list with author and timestamp
  - Loading states
- [ ] Testing the new UI features

---

## Phase 3: Shift & Leave Management
**Status: NOT STARTED**

Key deliverables:
- Shift definition and assignment
- Leave management (vacation, sick, etc.)
- Shift-aware routing
- Coverage dashboard

---

## Quick Reference

### API Key Usage
```bash
# Use API key in header
curl -H "X-API-Key: tk_live_xxxxx" https://tixmaster.preview.emergentagent.com/api/tickets
```

### Ticket ID Format
- Old: `ticket_abc123def456`
- New: `TKT-000064`

### New Ticket Fields
- `source`: manual, email, api, simulator, legacy
- `tags`: ["billing", "urgent"]
- `domain`: extracted from customer_email
- `customer_email`: original email address

### Team Endpoints
- `GET /api/teams` - List all teams
- `POST /api/teams` - Create team
- `DELETE /api/teams/{team_id}` - Delete team
- `POST /api/teams/{team_id}/members` - Add member
- `DELETE /api/teams/{team_id}/members/{user_id}` - Remove member
- `GET /api/teams/{team_id}/inbox` - Team's assigned tickets
- `POST /api/teams/{team_id}/assign-ticket` - Round-robin assign

### Internal Notes Endpoints
- `POST /api/tickets/{ticket_id}/notes` - Add internal note
- `GET /api/tickets/{ticket_id}/notes` - Get ticket notes

---

## Files Modified (Phase 2)

### Backend
- `/app/backend/server.py` - Team CRUD, member management, notes, round-robin

### Frontend
- `/app/frontend/src/components/TeamsPage.js` - New team management page
- `/app/frontend/src/components/TicketDrawer.js` - Added internal notes UI
- `/app/frontend/src/components/Sidebar.js` - Added Teams nav link
- `/app/frontend/src/App.js` - Added /teams route

---

*Last Updated: January 2026*
