# Escalation & Shift Management Implementation Plan

## Overview
Implementing ticket escalation levels (L1, L2, L3) with team-based routing, shift management, and round-robin assignment within teams.

## Phase 1: Database Schema Updates (Status: COMPLETED ✅)

### 1.1 Tickets Collection - Add escalation_level ✅
- Added `escalation_level` field (L1, L2, L3 - default L1)
- Added `team_id` for assigned team
- Added `escalation_history` array for tracking changes

### 1.2 Teams Collection - Enhanced ✅
- Added `escalation_level` field to teams (L1, L2, L3)
- Added `timezone` field (default: Asia/Kolkata)
- Teams: L1 Support, L2 Team, L3 Specialists created

### 1.3 NEW: Shifts Collection ✅
- shift_id, team_id, name
- start_time, end_time (HH:MM in IST)
- days_of_week (1=Mon, 7=Sun)
- is_active flag

### 1.4 NEW: User Shifts Collection ✅
- user_shift_id, user_id, team_id, shift_id
- is_primary, effective_from, effective_to

## Phase 2: Backend APIs (Status: COMPLETED ✅)

### 2.1 Shift Management APIs ✅
- POST /api/shifts - Create shift
- GET /api/shifts - List all shifts with assigned users
- GET /api/shifts/team/{team_id} - Get shifts for a team
- PUT /api/shifts/{shift_id} - Update shift
- DELETE /api/shifts/{shift_id} - Delete shift

### 2.2 User-Shift Assignment APIs ✅
- POST /api/users/{user_id}/shifts - Assign user to shift
- GET /api/users/{user_id}/shifts - Get user's shifts
- DELETE /api/users/{user_id}/shifts/{shift_id} - Remove from shift

### 2.3 On-Shift Query APIs ✅
- GET /api/teams/{team_id}/on-shift - Get currently on-shift members
- GET /api/teams/{team_id}/schedule - Get team schedule overview

### 2.4 Ticket Escalation APIs ✅
- PUT /api/tickets/{ticket_id}/escalate - Change escalation level (triggers routing)
- GET /api/tickets/{ticket_id}/assignment-options - Get assignment dropdown data

### 2.5 Auto-Assignment Logic ✅
- shift_based_round_robin() - Round-robin among on-shift members
- auto_assign_on_escalation() - Auto-route based on escalation level
- is_user_on_shift() - Check if user is currently on shift (IST timezone)

## Phase 3: Frontend Updates (Status: COMPLETED ✅)

### 3.1 Ticket Drawer ✅
- Escalation level buttons (L1, L2, L3) with visual highlighting
- Shows assigned team name below escalation buttons
- Enhanced assignee dropdown with:
  - Team members section with on-shift indicators
  - Other teams section for escalation (shows team name, escalation level, on-shift count)

### 3.2 Admin Panel - Shift Management ✅
- New "Shifts & Schedules" tab
- Create/delete shifts with:
  - Team selection
  - Shift name
  - Start/end time (IST)
  - Working days selector
- Visual shift cards showing:
  - Team and escalation level
  - Time range and days
  - Assigned users with avatars
  - Add/remove user buttons
- Team filter dropdown
- Assign users to shifts modal

## Technical Notes
- All times in IST (Asia/Kolkata)
- Round-robin uses last_assigned_idx, increments modulo on-shift team size
- Unassigned tickets with team_id = "waiting for on-shift agent"
- Admins can be on multiple teams via multiple user_shifts entries

## Test Data Created
- L1 Support team with Morning Shift (09:00-17:00 Mon-Fri)
- L1 Support team with Evening Shift (17:00-01:00 Mon-Sat)
- L2 Team with All Hours shift (00:00-23:59 all week)
- L3 Specialists team (no shifts yet)
- Rohit Mittal assigned to Morning Shift
