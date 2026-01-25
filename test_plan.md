# Trinity - Comprehensive Test Plan

## Overview
This test plan covers all major user flows in the Trinity support platform. Due to the scope, testing is divided into 4 phases.

## Phase 1: Core Navigation & Authentication
- [ ] Login page displays correctly
- [ ] App name shows "Trinity" throughout
- [ ] Successful test login
- [ ] Dashboard loads with Kanban board
- [ ] All sidebar navigation links work
- [ ] Light/dark mode toggle works
- [ ] Logout functionality

## Phase 2: Ticket Management
- [ ] View all tickets in list view
- [ ] Open ticket drawer
- [ ] Escalation level buttons (L1/L2/L3) work
- [ ] Assignee dropdown shows team members and other teams
- [ ] Priority selection works
- [ ] Status changes work (when assigned)
- [ ] Custom fields display and save
- [ ] Rich text editor for replies/notes
- [ ] Save button persists changes

## Phase 3: Shift & Team Management
- [ ] Admin → Shifts & Schedules tab loads
- [ ] Create new shift works
- [ ] Assign user to shift works
- [ ] Remove user from shift works
- [ ] Profile page shows "My Shifts"
- [ ] User can join a shift from profile
- [ ] User can leave a shift from profile
- [ ] Teams page loads and shows teams

## Phase 4: Settings & Export
- [ ] Settings page loads
- [ ] Theme switcher works
- [ ] Data export (JSON) - Tickets
- [ ] Data export (JSON) - Users
- [ ] Data export (JSON) - Teams
- [ ] Data export (JSON) - Shifts
- [ ] Data export (CSV) - Tickets
- [ ] Data export (CSV) - Users
- [ ] Data export (CSV) - Teams

## Test Execution Notes
- Use screenshot tool for UI verification
- Use curl for API testing
- Test both light and dark modes for key flows
