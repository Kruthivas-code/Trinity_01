# Escalation & Shift Management Implementation Plan

## Overview
Implementing ticket escalation levels (L1, L2, L3) with team-based routing, shift management, and round-robin assignment within teams.

## Phase 1: Database Schema Updates (Status: IN PROGRESS)

### 1.1 Tickets Collection - Add escalation_level
```json
{
  "escalation_level": "L1",  // L1, L2, L3 - default L1
  "team_id": null,           // Assigned team
  "assigned_at": null,       // When assigned
  "escalated_at": null,      // When escalation changed
  "escalation_history": []   // Track escalation changes
}
```

### 1.2 Teams Collection - Enhance
```json
{
  "team_id": "team_xxx",
  "name": "L1 Support",
  "escalation_level": "L1",  // L1, L2, L3
  "description": "",
  "members": ["user_id_1", "user_id_2"],
  "lead_id": null,
  "last_assigned_idx": -1,   // For round-robin (already exists)
  "timezone": "Asia/Kolkata", // IST
  "created_at": "...",
  "updated_at": "..."
}
```

### 1.3 NEW: Shifts Collection
```json
{
  "shift_id": "shift_xxx",
  "team_id": "team_xxx",
  "name": "Morning Shift",
  "start_time": "09:00",     // IST time (HH:MM)
  "end_time": "17:00",       // IST time
  "days_of_week": [1,2,3,4,5], // 1=Mon, 7=Sun
  "is_active": true,
  "created_at": "...",
  "updated_at": "..."
}
```

### 1.4 NEW: User Shifts Collection (User-Shift Assignment)
```json
{
  "user_shift_id": "us_xxx",
  "user_id": "user_xxx",
  "team_id": "team_xxx",
  "shift_id": "shift_xxx",
  "is_primary": true,        // Primary team assignment
  "effective_from": "...",
  "effective_to": null,      // null = ongoing
  "created_at": "..."
}
```

## Phase 2: Backend APIs (Status: NOT STARTED)

### 2.1 Shift Management APIs
- `POST /api/shifts` - Create shift
- `GET /api/shifts` - List all shifts
- `GET /api/shifts/team/{team_id}` - Get shifts for a team
- `PUT /api/shifts/{shift_id}` - Update shift
- `DELETE /api/shifts/{shift_id}` - Delete shift

### 2.2 User-Shift Assignment APIs
- `POST /api/users/{user_id}/shifts` - Assign user to shift
- `GET /api/users/{user_id}/shifts` - Get user's shifts
- `DELETE /api/users/{user_id}/shifts/{shift_id}` - Remove from shift

### 2.3 On-Shift Query APIs
- `GET /api/teams/{team_id}/on-shift` - Get currently on-shift members
- `GET /api/teams/{team_id}/schedule` - Get team schedule overview

### 2.4 Ticket Assignment APIs (Enhanced)
- `PUT /api/tickets/{ticket_id}/escalate` - Change escalation level (triggers routing)
- `GET /api/tickets/assignment-options/{ticket_id}` - Get assignment dropdown data

### 2.5 Auto-Assignment Logic
- When escalation_level changes:
  1. Find team for that escalation level
  2. Get on-shift members from that team
  3. Round-robin assign to next available member
  4. If no one on shift, leave unassigned with team_id set

## Phase 3: Frontend Updates (Status: NOT STARTED)

### 3.1 Ticket Drawer
- Add escalation level dropdown (L1, L2, L3)
- Update assignee dropdown:
  - Section 1: Team Members (with on-shift indicator)
  - Section 2: Other Teams (grouped, click to escalate)

### 3.2 Admin Panel - Shift Management
- New tab: "Shifts & Schedules"
- Create/edit shifts per team
- Assign users to shifts
- Visual schedule view

### 3.3 Team Capacity View
- Who's currently on shift per team
- Upcoming shift changes
- Ticket load per person

## Implementation Order
1. ✅ Backend models & collections
2. ⬜ Shift CRUD APIs
3. ⬜ User-shift assignment APIs
4. ⬜ On-shift query logic (IST timezone)
5. ⬜ Auto-assignment on escalation change
6. ⬜ Frontend: Escalation dropdown in drawer
7. ⬜ Frontend: Enhanced assignee dropdown
8. ⬜ Frontend: Admin shift management UI
9. ⬜ Frontend: Capacity planning view

## Technical Notes
- All times stored in IST (Asia/Kolkata)
- Round-robin uses `last_assigned_idx` on team, increments modulo team size
- Unassigned tickets with team_id set = "waiting for on-shift agent"
- Admins can be on multiple teams (via multiple user_shifts entries)
