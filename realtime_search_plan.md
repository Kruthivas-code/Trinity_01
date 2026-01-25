# Trinity - Real-time Collaboration & Comprehensive Search

## Implementation Plan

### Phase 1: Backend Infrastructure ✅ COMPLETED
- [x] Install Socket.IO with Redis adapter for horizontal scaling
- [x] Create WebSocket connection handler with authentication
- [x] Set up presence tracking system with heartbeats
- [x] Create MongoDB text indexes for full-text search
- [x] Set up search aggregation pipeline

### Phase 2: Real-time Events System ✅ COMPLETED
- [x] Basic ticket broadcast events (structure created)
- [x] Integrate broadcasts into ticket CRUD endpoints
- [x] User presence tracking per ticket/view
- [x] "User is typing" indicators (backend ready)
- [ ] Conflict detection (optimistic locking - future enhancement)
- [ ] Conflict resolution UI (future enhancement)

### Phase 3: Search Backend ✅ COMPLETED
- [x] Multi-collection search API endpoint
- [x] Ticket search (title, content, tags, custom fields)
- [x] User search (name, email, role)
- [x] Team search (name, type, description)
- [x] Shift & Routing Rules search
- [x] Platform features/commands indexing
- [x] Fuzzy matching with similarity scoring

### Phase 4: Frontend - Real-time Collaboration ⏳ IN PROGRESS
- [x] Socket.IO client integration (RealtimeContext)
- [x] Basic presence state management
- [ ] Presence indicators (avatars showing who's viewing)
- [ ] Live update toasts/notifications
- [ ] "Someone is editing" indicators
- [ ] Real-time ticket list updates
- [ ] Collaborative editing with cursor positions (stretch)

### Phase 5: Frontend - Command Palette Search ✅ COMPLETED
- [x] Cmd+K / Ctrl+K global shortcut
- [x] Search modal with categories
- [x] Instant results with keyboard navigation
- [x] Recent searches history
- [x] Quick actions (navigate, create, etc.)

### Phase 6: Frontend - Universal Search UI ✅ COMPLETED (1/25/2026)
- [x] GlobalHeader component with central search bar
- [x] Dynamic page title based on route
- [x] Quick search dropdown with live results
- [x] "New Ticket" button in header
- [x] Search results page (`/search` route)
- [x] Filters sidebar (Result type, Quick filters)
- [x] Export functionality
- [x] Expandable category sections

### Phase 7: Testing & Optimization
- [ ] WebSocket connection resilience
- [ ] Search performance benchmarks
- [ ] Edge case handling
- [ ] Mobile responsiveness

---

## Technical Architecture

### Real-time Stack
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  Socket.IO  │────▶│    Redis    │
│  (Browser)  │◀────│   Server    │◀────│   Pub/Sub   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   MongoDB   │
                    └─────────────┘
```

### Event Types
- `ticket:update` - Ticket data changed
- `ticket:viewing` - User started viewing ticket
- `ticket:left` - User left ticket view
- `ticket:typing` - User is typing in ticket
- `presence:sync` - Sync all active users
- `notification:new` - New notification

### Search Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Cmd+K     │────▶│  Search API │────▶│   MongoDB   │
│   Modal     │◀────│  /api/search│◀────│ Text Index  │
└─────────────┘     └─────────────┘     └─────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│  Results: Tickets | Users | Teams | Commands | ...  │
└─────────────────────────────────────────────────────┘
```

### MongoDB Indexes Required
```javascript
// Tickets - compound text index
db.tickets.createIndex({
  title: "text",
  content: "text",
  tags: "text"
}, { weights: { title: 10, tags: 5, content: 1 } })

// Users
db.users.createIndex({ name: "text", email: "text" })

// Teams
db.teams.createIndex({ name: "text", type: "text", description: "text" })
```

---

## Data Models

### Presence Document
```python
{
  "user_id": "uuid",
  "user_name": "string",
  "user_picture": "url",
  "location": {
    "type": "ticket" | "dashboard" | "admin",
    "id": "ticket_id or null"
  },
  "last_heartbeat": "datetime",
  "socket_id": "string"
}
```

### Ticket Version (for conflict resolution)
```python
{
  "ticket_id": "uuid",
  "version": 1,  # Incremented on each update
  "last_modified_by": "user_id",
  "last_modified_at": "datetime"
}
```

---

## Status
- **Current Phase**: 1 - Backend Infrastructure
- **Started**: 2025-01-25
