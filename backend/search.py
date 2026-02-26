"""
Trinity Comprehensive Search Module v2
Full-text search across ALL entities with operator support
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient, TEXT
import re
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# PLATFORM COMMANDS - Everything the user can do
# ============================================================================

PLATFORM_COMMANDS = [
    # Navigation - Main
    {"id": "nav-dashboard", "type": "command", "category": "Navigation", "title": "Dashboard", "subtitle": "Kanban board overview", "action": "/dashboard", "keywords": ["home", "main", "kanban", "board", "overview"]},
    {"id": "nav-all-tickets", "type": "command", "category": "Navigation", "title": "All Tickets", "subtitle": "View all tickets", "action": "/all-tickets", "keywords": ["tickets", "list", "all", "every"]},
    {"id": "nav-open-tickets", "type": "command", "category": "Navigation", "title": "Open Tickets", "subtitle": "Tickets in progress", "action": "/open-tickets", "keywords": ["open", "active", "pending", "working"]},
    {"id": "nav-waiting-tickets", "type": "command", "category": "Navigation", "title": "Waiting on Customer", "subtitle": "Awaiting response", "action": "/waiting-tickets", "keywords": ["waiting", "customer", "response", "pending"]},
    {"id": "nav-closed-tickets", "type": "command", "category": "Navigation", "title": "Closed Tickets", "subtitle": "Resolved tickets", "action": "/closed-tickets", "keywords": ["closed", "resolved", "done", "completed", "finished"]},
    {"id": "nav-teams", "type": "command", "category": "Navigation", "title": "Teams", "subtitle": "Manage teams", "action": "/teams", "keywords": ["teams", "groups", "members", "organization", "people"]},
    {"id": "nav-profile", "type": "command", "category": "Navigation", "title": "My Profile", "subtitle": "Your account settings", "action": "/profile", "keywords": ["profile", "account", "me", "my", "user"]},
    {"id": "nav-settings", "type": "command", "category": "Navigation", "title": "Settings", "subtitle": "App preferences", "action": "/settings", "keywords": ["settings", "preferences", "config", "options"]},
    {"id": "nav-admin", "type": "command", "category": "Navigation", "title": "Admin Panel", "subtitle": "System configuration", "action": "/admin", "keywords": ["admin", "administration", "configure", "system"]},
    
    # Admin sub-pages
    {"id": "admin-custom-fields", "type": "command", "category": "Admin", "title": "Custom Fields", "subtitle": "Manage ticket fields", "action": "/admin?tab=custom-fields", "keywords": ["custom", "fields", "attributes", "properties", "metadata"]},
    {"id": "admin-routing-rules", "type": "command", "category": "Admin", "title": "Routing Rules", "subtitle": "Automatic ticket routing", "action": "/admin?tab=routing-rules", "keywords": ["routing", "rules", "automation", "assignment", "auto"]},
    {"id": "admin-shifts", "type": "command", "category": "Admin", "title": "Shifts & Schedules", "subtitle": "Team schedules", "action": "/admin?tab=shifts", "keywords": ["shifts", "schedule", "time", "availability", "hours"]},
    {"id": "admin-general", "type": "command", "category": "Admin", "title": "General Settings", "subtitle": "System settings", "action": "/admin?tab=general", "keywords": ["general", "settings", "system", "config"]},
    
    # Actions
    {"id": "action-new-ticket", "type": "action", "category": "Actions", "title": "Create New Ticket", "subtitle": "Open a ticket", "action": "create_ticket", "keywords": ["new", "create", "add", "ticket", "issue", "request"]},
    {"id": "action-new-team", "type": "action", "category": "Actions", "title": "Create New Team", "subtitle": "Add a team", "action": "create_team", "keywords": ["new", "create", "add", "team", "group"]},
    {"id": "action-export-tickets", "type": "action", "category": "Actions", "title": "Export Tickets", "subtitle": "Download as CSV/JSON", "action": "export_tickets", "keywords": ["export", "download", "csv", "json", "backup", "tickets"]},
    {"id": "action-export-users", "type": "action", "category": "Actions", "title": "Export Users", "subtitle": "Download user list", "action": "export_users", "keywords": ["export", "download", "users", "agents"]},
    {"id": "action-theme-light", "type": "action", "category": "Actions", "title": "Switch to Light Mode", "subtitle": "Light theme", "action": "theme_light", "keywords": ["light", "theme", "bright", "day"]},
    {"id": "action-theme-dark", "type": "action", "category": "Actions", "title": "Switch to Dark Mode", "subtitle": "Dark theme", "action": "theme_dark", "keywords": ["dark", "theme", "night", "dim"]},
    {"id": "action-logout", "type": "action", "category": "Actions", "title": "Sign Out", "subtitle": "Log out of account", "action": "logout", "keywords": ["logout", "sign out", "exit", "leave"]},
    
    # Quick filters (search shortcuts)
    {"id": "filter-my-tickets", "type": "filter", "category": "Quick Filters", "title": "My Tickets", "subtitle": "Assigned to me", "action": "/search?q=assigned:me", "keywords": ["my", "mine", "assigned"]},
    {"id": "filter-urgent", "type": "filter", "category": "Quick Filters", "title": "Urgent Tickets", "subtitle": "High priority items", "action": "/search?q=priority:urgent", "keywords": ["urgent", "critical", "important", "asap"]},
    {"id": "filter-unassigned", "type": "filter", "category": "Quick Filters", "title": "Unassigned Tickets", "subtitle": "Need assignment", "action": "/search?q=assigned:none", "keywords": ["unassigned", "nobody", "available"]},
    {"id": "filter-today", "type": "filter", "category": "Quick Filters", "title": "Created Today", "subtitle": "New tickets", "action": "/search?q=created:today", "keywords": ["today", "new", "recent"]},
    {"id": "filter-overdue", "type": "filter", "category": "Quick Filters", "title": "Needs Attention", "subtitle": "Old open tickets", "action": "/search?q=status:open created:last-week", "keywords": ["overdue", "old", "attention", "stale"]},
]

# ============================================================================
# SEARCH OPERATORS
# ============================================================================

SEARCH_OPERATORS = {
    'status': ['open', 'in-progress', 'waiting', 'closed', 'new'],
    'priority': ['urgent', 'high', 'medium', 'low'],
    'assigned': ['me', 'none'],  # Also accepts @username
    'team': [],  # Dynamic - any team name
    'tag': [],  # Dynamic - any tag
    'escalation': ['L1', 'L2', 'L3', 'L4'],
    'source': ['email', 'manual', 'api'],
    'type': ['ticket', 'user', 'team', 'command', 'customer', 'shift', 'rule'],
    'created': ['today', 'yesterday', 'this-week', 'last-week', 'this-month', 'last-month'],
    'updated': ['today', 'yesterday', 'this-week', 'last-week'],
    'customer': [],  # Dynamic - email
    'domain': [],  # Dynamic - domain name
    'has': ['attachment', 'comment', 'tag'],
}


def parse_date_filter(value: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse natural language date filters into datetime range"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    date_ranges = {
        'today': (today_start, now),
        'yesterday': (today_start - timedelta(days=1), today_start),
        'this-week': (today_start - timedelta(days=today_start.weekday()), now),
        'last-week': (today_start - timedelta(days=today_start.weekday() + 7), 
                      today_start - timedelta(days=today_start.weekday())),
        'this-month': (today_start.replace(day=1), now),
        'last-month': ((today_start.replace(day=1) - timedelta(days=1)).replace(day=1),
                       today_start.replace(day=1)),
        'last-7-days': (today_start - timedelta(days=7), now),
        'last-30-days': (today_start - timedelta(days=30), now),
    }
    
    if value.lower() in date_ranges:
        return date_ranges[value.lower()]
    
    # Try parsing as date string (YYYY-MM-DD)
    try:
        parsed = datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        return (parsed, parsed + timedelta(days=1))
    except ValueError:
        pass
    
    return (None, None)


def parse_search_query(query: str) -> Tuple[str, Dict[str, str]]:
    """
    Parse search query with operators.
    Returns (text_query, operators_dict)
    
    Example: "billing issue status:open priority:urgent"
    Returns: ("billing issue", {"status": "open", "priority": "urgent"})
    """
    operators = {}
    text_parts = []
    
    # Regex to match operator:value patterns
    operator_pattern = r'(\w+):(\S+)'
    
    parts = query.split()
    for part in parts:
        match = re.match(operator_pattern, part)
        if match:
            op, val = match.groups()
            if op.lower() in SEARCH_OPERATORS or op.lower() in ['customer', 'domain', 'team', 'tag', 'assigned', 'uuid']:
                operators[op.lower()] = val.lower()
            else:
                text_parts.append(part)
        else:
            text_parts.append(part)
    
    return (' '.join(text_parts), operators)


class SearchEngine:
    """Comprehensive search engine for Trinity - indexes EVERYTHING"""
    
    def __init__(self, db):
        self.db = db
        self.tickets = db.tickets
        self.users = db.users
        self.teams = db.teams
        self.shifts = db.shifts
        self.routing_rules = db.routing_rules
        self.custom_fields = db.custom_fields
        
    def ensure_indexes(self):
        """Create text indexes for full-text search"""
        try:
            # Tickets - comprehensive text index including uuid
            self.tickets.create_index([
                ("title", TEXT),
                ("content", TEXT),
                ("description", TEXT),
                ("tags", TEXT),
                ("ticket_id", TEXT),
                ("uuid", TEXT),
                ("customer_email", TEXT),
                ("customer_name", TEXT),
                ("domain", TEXT)
            ], weights={
                "title": 10,
                "ticket_id": 10,
                "uuid": 10,
                "tags": 8,
                "customer_email": 5,
                "domain": 5,
                "content": 2,
                "description": 2,
                "customer_name": 3
            }, name="ticket_search_idx_v3", default_language="english")
            logger.info("Created ticket search index v3 with UUID")
        except Exception as e:
            logger.warning(f"Ticket index may already exist: {e}")
        
        try:
            self.users.create_index([
                ("name", TEXT),
                ("email", TEXT)
            ], weights={"name": 10, "email": 5}, name="user_search_idx_v2")
        except Exception as e:
            logger.warning(f"User index exists: {e}")
        
        try:
            self.teams.create_index([
                ("name", TEXT),
                ("type", TEXT),
                ("description", TEXT)
            ], weights={"name": 10, "type": 5, "description": 1}, name="team_search_idx_v2")
        except Exception as e:
            logger.warning(f"Team index exists: {e}")
        
        try:
            self.shifts.create_index([("name", TEXT)], name="shift_search_idx_v2")
        except Exception as e:
            logger.warning(f"Shift index exists: {e}")
        
        try:
            self.routing_rules.create_index([
                ("name", TEXT),
                ("description", TEXT)
            ], name="routing_rule_search_idx_v2")
        except Exception as e:
            logger.warning(f"Routing rule index exists: {e}")
        
        try:
            self.custom_fields.create_index([
                ("name", TEXT),
                ("description", TEXT)
            ], name="custom_field_search_idx")
        except Exception as e:
            logger.warning(f"Custom field index exists: {e}")
    
    def _fuzzy_match(self, query: str, text: str) -> float:
        """Calculate fuzzy match score (0-1)"""
        if not query or not text:
            return 0.0
        query, text = query.lower(), text.lower()
        if query == text:
            return 1.0
        if query in text:
            return 0.9
        query_words = set(query.split())
        text_words = set(text.split())
        if query_words & text_words:
            overlap = len(query_words & text_words) / len(query_words)
            return 0.5 + (overlap * 0.4)
        for word in text_words:
            if word.startswith(query) or query.startswith(word):
                return 0.4
        return 0.0
    
    def search_commands(self, query: str, limit: int = 10) -> List[Dict]:
        """Search platform commands/features/actions"""
        query_lower = query.lower()
        results = []
        
        for cmd in PLATFORM_COMMANDS:
            score = 0.0
            
            # Title match (highest weight)
            title_score = self._fuzzy_match(query_lower, cmd["title"].lower())
            score = max(score, title_score * 1.0)
            
            # Subtitle match
            if cmd.get("subtitle"):
                sub_score = self._fuzzy_match(query_lower, cmd["subtitle"].lower())
                score = max(score, sub_score * 0.7)
            
            # Keywords match
            for keyword in cmd.get("keywords", []):
                kw_score = self._fuzzy_match(query_lower, keyword)
                score = max(score, kw_score * 0.85)
            
            # Category match
            cat_score = self._fuzzy_match(query_lower, cmd["category"].lower())
            score = max(score, cat_score * 0.5)
            
            if score > 0.25:
                results.append({
                    **cmd,
                    "score": score,
                    "result_type": cmd["type"]
                })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def search_tickets(self, query: str, operators: Dict[str, str], limit: int = 20, current_user_id: str = None) -> List[Dict]:
        """Search tickets with operator support"""
        results = []
        seen_ids = set()
        
        # Build MongoDB query
        mongo_query = {}
        
        # Exclude merged tickets from search results (they should be found via parent)
        mongo_query['status'] = {'$ne': 'merged'}
        
        # Apply operators
        if 'status' in operators:
            mongo_query['status'] = operators['status']
        
        if 'priority' in operators:
            mongo_query['priority'] = operators['priority']
        
        if 'escalation' in operators:
            mongo_query['escalation_level'] = operators['escalation'].upper()
        
        if 'source' in operators:
            mongo_query['source'] = operators['source']
        
        if 'assigned' in operators:
            val = operators['assigned']
            if val == 'me' and current_user_id:
                mongo_query['assignee_id'] = current_user_id
            elif val == 'none':
                mongo_query['$or'] = [{'assignee_id': None}, {'assignee_id': {'$exists': False}}]
            elif val.startswith('@'):
                # Find user by name
                username = val[1:]
                user = self.users.find_one({'name': {'$regex': username, '$options': 'i'}})
                if user:
                    mongo_query['assignee_id'] = user.get('user_id')
        
        if 'team' in operators:
            team = self.teams.find_one({'name': {'$regex': operators['team'], '$options': 'i'}})
            if team:
                mongo_query['team_id'] = team.get('team_id')
        
        if 'tag' in operators:
            mongo_query['tags'] = {'$regex': operators['tag'], '$options': 'i'}
        
        if 'customer' in operators:
            # Search both customer_email and associated_emails
            email_pattern = operators['customer']
            mongo_query['$or'] = [
                {'customer_email': {'$regex': email_pattern, '$options': 'i'}},
                {'associated_emails': {'$regex': email_pattern, '$options': 'i'}}
            ]
        
        if 'domain' in operators:
            mongo_query['domain'] = {'$regex': operators['domain'], '$options': 'i'}
        
        if 'created' in operators:
            start, end = parse_date_filter(operators['created'])
            if start and end:
                mongo_query['created_at'] = {'$gte': start, '$lt': end}
        
        if 'updated' in operators:
            start, end = parse_date_filter(operators['updated'])
            if start and end:
                mongo_query['updated_at'] = {'$gte': start, '$lt': end}
        
        try:
            # Direct ticket ID match for numeric-only queries (e.g., "12345" → "TKT-12345")
            if query:
                stripped = query.strip()
                if re.match(r'^\d+$', stripped):
                    tkt_id = f'TKT-{stripped}'
                    direct_ticket = self.tickets.find_one({
                        'ticket_id': tkt_id,
                        'status': {'$ne': 'merged'}
                    })
                    if direct_ticket:
                        ticket_id = direct_ticket.get("ticket_id", str(direct_ticket.get("_id")))
                        seen_ids.add(ticket_id)
                        merged_info = direct_ticket.get("merged_tickets", [])
                        results.append({
                            "id": ticket_id,
                            "ticket_id": ticket_id,
                            "uuid": direct_ticket.get("uuid"),
                            "type": "ticket",
                            "result_type": "ticket",
                            "category": "Tickets",
                            "title": direct_ticket.get("title", "Untitled"),
                            "subtitle": f"#{ticket_id} • {direct_ticket.get('status', 'unknown')}",
                            "status": direct_ticket.get("status"),
                            "priority": direct_ticket.get("priority"),
                            "escalation_level": direct_ticket.get("escalation_level"),
                            "assignee_id": direct_ticket.get("assignee_id"),
                            "customer_email": direct_ticket.get("customer_email"),
                            "associated_emails": direct_ticket.get("associated_emails", []),
                            "domain": direct_ticket.get("domain"),
                            "tags": direct_ticket.get("tags", []),
                            "merged_tickets": merged_info,
                            "contains_merged_ticket": len(merged_info) > 0,
                            "created_at": direct_ticket.get("created_at").isoformat() if direct_ticket.get("created_at") else None,
                            "action": f"/all-tickets?ticket={ticket_id}",
                            "score": 25.0  # Highest score for exact numeric ID match
                        })
            
            # First check if query matches a search_identifier directly (merged ticket lookup)
            if query and len(query) >= 3:
                identifier_match = self.tickets.find_one({
                    'search_identifiers': {'$regex': f'^{re.escape(query)}', '$options': 'i'},
                    'status': {'$ne': 'merged'}
                })
                if identifier_match:
                    # Found via merged ticket identifier - add to results with high score
                    merged_ids = [m.get('ticket_id') for m in identifier_match.get('merged_tickets', [])]
                    matched_merged = query.upper() if query.upper().startswith('TKT-') else query
                    contains_merged = matched_merged in merged_ids or any(query.lower() in mid.lower() for mid in merged_ids)
                    
                    results.append({
                        "id": identifier_match.get("ticket_id", str(identifier_match.get("_id"))),
                        "ticket_id": identifier_match.get("ticket_id", str(identifier_match.get("_id"))),
                        "uuid": identifier_match.get("uuid"),
                        "type": "ticket",
                        "result_type": "ticket",
                        "category": "Tickets",
                        "title": identifier_match.get("title", "Untitled"),
                        "subtitle": f"#{identifier_match.get('ticket_id', 'N/A')} • {identifier_match.get('status', 'unknown')}",
                        "status": identifier_match.get("status"),
                        "priority": identifier_match.get("priority"),
                        "escalation_level": identifier_match.get("escalation_level"),
                        "assignee_id": identifier_match.get("assignee_id"),
                        "customer_email": identifier_match.get("customer_email"),
                        "associated_emails": identifier_match.get("associated_emails", []),
                        "domain": identifier_match.get("domain"),
                        "tags": identifier_match.get("tags", []),
                        "merged_tickets": identifier_match.get("merged_tickets", []),
                        "contains_merged_ticket": contains_merged,
                        "created_at": identifier_match.get("created_at").isoformat() if identifier_match.get("created_at") else None,
                        "action": f"/all-tickets?ticket={identifier_match.get('ticket_id')}",
                        "score": 20.0  # High score for direct identifier match
                    })
            
            # Text search if there's a query
            if query and len(query) >= 2:
                mongo_query['$text'] = {'$search': query}
                cursor = self.tickets.find(
                    mongo_query,
                    {'score': {'$meta': 'textScore'}}
                ).sort([('score', {'$meta': 'textScore'})]).limit(limit)
            else:
                # Just filter by operators
                cursor = self.tickets.find(mongo_query).sort('created_at', -1).limit(limit)
            
            seen_ids.update(r['ticket_id'] for r in results)  # Don't duplicate identifier matches
            
            for doc in cursor:
                ticket_id = doc.get("ticket_id", str(doc.get("_id")))
                if ticket_id in seen_ids:
                    continue
                seen_ids.add(ticket_id)
                
                merged_info = doc.get("merged_tickets", [])
                results.append({
                    "id": ticket_id,
                    "ticket_id": ticket_id,
                    "uuid": doc.get("uuid"),
                    "type": "ticket",
                    "result_type": "ticket",
                    "category": "Tickets",
                    "title": doc.get("title", "Untitled"),
                    "subtitle": f"#{doc.get('ticket_id', 'N/A')} • {doc.get('status', 'unknown')}",
                    "status": doc.get("status"),
                    "priority": doc.get("priority"),
                    "escalation_level": doc.get("escalation_level"),
                    "assignee_id": doc.get("assignee_id"),
                    "customer_email": doc.get("customer_email"),
                    "associated_emails": doc.get("associated_emails", []),
                    "domain": doc.get("domain"),
                    "tags": doc.get("tags", []),
                    "merged_tickets": merged_info,
                    "contains_merged_ticket": len(merged_info) > 0,
                    "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                    "action": f"/all-tickets?ticket={doc.get('ticket_id')}",
                    "score": doc.get("score", 0.5)
                })
        except Exception as e:
            logger.error(f"Ticket search error: {e}")
            # Fallback to regex search including search_identifiers and associated_emails
            if query:
                regex = {"$regex": query, "$options": "i"}
                fallback_query = {
                    "$or": [
                        {"title": regex},
                        {"content": regex},
                        {"ticket_id": regex},
                        {"customer_email": regex},
                        {"search_identifiers": regex},
                        {"associated_emails": regex},
                        {"external_id": regex},
                        {"uuid": regex}
                    ],
                    "status": {"$ne": "merged"}  # Exclude merged tickets
                }
                fallback_query.update({k: v for k, v in mongo_query.items() if k not in ['$text', 'status']})
                cursor = self.tickets.find(fallback_query).limit(limit)
                
                for doc in cursor:
                    ticket_id = doc.get("ticket_id", str(doc.get("_id")))
                    if ticket_id in seen_ids:
                        continue
                    merged_info = doc.get("merged_tickets", [])
                    results.append({
                        "id": ticket_id,
                        "ticket_id": ticket_id,
                        "uuid": doc.get("uuid"),
                        "type": "ticket",
                        "result_type": "ticket",
                        "category": "Tickets",
                        "title": doc.get("title", "Untitled"),
                        "subtitle": f"#{doc.get('ticket_id', 'N/A')} • {doc.get('status', 'unknown')}",
                        "status": doc.get("status"),
                        "priority": doc.get("priority"),
                        "merged_tickets": merged_info,
                        "contains_merged_ticket": len(merged_info) > 0,
                        "action": f"/all-tickets?ticket={doc.get('ticket_id')}",
                        "score": 0.5
                    })
        
        return results
    
    def search_users(self, query: str, limit: int = 10) -> List[Dict]:
        """Search users/agents"""
        results = []
        
        try:
            if query and len(query) >= 2:
                cursor = self.users.find(
                    {"$text": {"$search": query}},
                    {"score": {"$meta": "textScore"}}
                ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            else:
                cursor = self.users.find().limit(limit)
            
            for doc in cursor:
                results.append({
                    "id": doc.get("user_id", str(doc.get("_id"))),
                    "type": "user",
                    "result_type": "user",
                    "category": "Users",
                    "title": doc.get("name", "Unknown"),
                    "subtitle": doc.get("email", ""),
                    "picture": doc.get("picture"),
                    "email": doc.get("email"),
                    "action": f"/profile?user={doc.get('user_id')}",
                    "score": doc.get("score", 0.5)
                })
        except Exception as e:
            logger.error(f"User search error: {e}")
            regex = {"$regex": query, "$options": "i"}
            cursor = self.users.find({"$or": [{"name": regex}, {"email": regex}]}).limit(limit)
            for doc in cursor:
                results.append({
                    "id": doc.get("user_id"),
                    "type": "user",
                    "result_type": "user",
                    "category": "Users",
                    "title": doc.get("name", "Unknown"),
                    "subtitle": doc.get("email", ""),
                    "picture": doc.get("picture"),
                    "action": f"/profile?user={doc.get('user_id')}",
                    "score": 0.5
                })
        
        return results
    
    def search_teams(self, query: str, limit: int = 10) -> List[Dict]:
        """Search teams"""
        results = []
        regex = {"$regex": query, "$options": "i"} if query else {}
        
        try:
            if query:
                cursor = self.teams.find({"$or": [
                    {"name": regex}, {"type": regex}, {"description": regex}
                ]}).limit(limit)
            else:
                cursor = self.teams.find().limit(limit)
            
            for doc in cursor:
                results.append({
                    "id": doc.get("team_id", str(doc.get("_id"))),
                    "type": "team",
                    "result_type": "team",
                    "category": "Teams",
                    "title": doc.get("name", "Unknown Team"),
                    "subtitle": doc.get("type", "") or f"{doc.get('member_count', 0)} members",
                    "member_count": doc.get("member_count", 0),
                    "action": f"/teams?team={doc.get('team_id')}",
                    "score": 0.5
                })
        except Exception as e:
            logger.error(f"Team search error: {e}")
        
        return results
    
    def search_customers(self, query: str, limit: int = 10) -> List[Dict]:
        """Search customers (aggregated from tickets)"""
        results = []
        
        if not query or len(query) < 2:
            return results
        
        try:
            pipeline = [
                {"$match": {
                    "$or": [
                        {"customer_email": {"$regex": query, "$options": "i"}},
                        {"customer_name": {"$regex": query, "$options": "i"}},
                        {"domain": {"$regex": query, "$options": "i"}}
                    ]
                }},
                {"$group": {
                    "_id": {"$toLower": "$customer_email"},
                    "email": {"$first": "$customer_email"},
                    "name": {"$first": "$customer_name"},
                    "domain": {"$first": "$domain"},
                    "ticket_count": {"$sum": 1},
                    "last_ticket": {"$max": "$created_at"}
                }},
                {"$sort": {"ticket_count": -1}},
                {"$limit": limit}
            ]
            
            for doc in self.tickets.aggregate(pipeline):
                results.append({
                    "id": doc.get("_id"),
                    "type": "customer",
                    "result_type": "customer",
                    "category": "Customers",
                    "title": doc.get("name") or doc.get("email", "Unknown"),
                    "subtitle": f"{doc.get('email', '')} • {doc.get('ticket_count', 0)} tickets",
                    "email": doc.get("email"),
                    "domain": doc.get("domain"),
                    "ticket_count": doc.get("ticket_count"),
                    "action": f"/search?q=customer:{doc.get('email', '')}",
                    "score": 0.6
                })
        except Exception as e:
            logger.error(f"Customer search error: {e}")
        
        return results
    
    def search_shifts(self, query: str, limit: int = 5) -> List[Dict]:
        """Search shifts"""
        results = []
        regex = {"$regex": query, "$options": "i"} if query else {}
        
        cursor = self.shifts.find({"name": regex} if query else {}).limit(limit)
        
        for doc in cursor:
            results.append({
                "id": doc.get("shift_id", str(doc.get("_id"))),
                "type": "shift",
                "result_type": "shift",
                "category": "Shifts",
                "title": doc.get("name", "Unknown Shift"),
                "subtitle": f"{doc.get('start_time', '')} - {doc.get('end_time', '')}",
                "action": "/admin?tab=shifts",
                "score": 0.4
            })
        
        return results
    
    def search_routing_rules(self, query: str, limit: int = 5) -> List[Dict]:
        """Search routing rules"""
        results = []
        regex = {"$regex": query, "$options": "i"} if query else {}
        
        cursor = self.routing_rules.find({
            "$or": [{"name": regex}, {"description": regex}]
        } if query else {}).limit(limit)
        
        for doc in cursor:
            results.append({
                "id": doc.get("rule_id", str(doc.get("_id"))),
                "type": "routing_rule",
                "result_type": "routing_rule",
                "category": "Routing Rules",
                "title": doc.get("name", "Unknown Rule"),
                "subtitle": doc.get("description", ""),
                "active": doc.get("active", False),
                "action": "/admin?tab=routing-rules",
                "score": 0.4
            })
        
        return results
    
    def search_custom_fields(self, query: str, limit: int = 5) -> List[Dict]:
        """Search custom field definitions"""
        results = []
        regex = {"$regex": query, "$options": "i"} if query else {}
        
        cursor = self.custom_fields.find({
            "$or": [{"name": regex}, {"description": regex}]
        } if query else {}).limit(limit)
        
        for doc in cursor:
            results.append({
                "id": doc.get("field_id", str(doc.get("_id"))),
                "type": "custom_field",
                "result_type": "custom_field",
                "category": "Custom Fields",
                "title": doc.get("name", "Unknown Field"),
                "subtitle": f"{doc.get('field_type', '')} • {doc.get('entity_type', '')}",
                "action": "/admin?tab=custom-fields",
                "score": 0.3
            })
        
        return results
    
    def search_all(
        self, 
        query: str, 
        limit_per_category: int = 10,
        current_user_id: str = None,
        type_filter: str = None
    ) -> Dict[str, Any]:
        """
        Search across ALL entities
        
        Args:
            query: Search query (may include operators like status:open)
            limit_per_category: Max results per category
            current_user_id: For assigned:me filter
            type_filter: Optional - only search specific type (ticket, user, etc.)
        """
        if not query:
            return {"results": [], "total": 0, "by_category": {}, "operators": {}}
        
        # Parse operators from query
        text_query, operators = parse_search_query(query)
        
        # If type filter specified via operator
        if 'type' in operators:
            type_filter = operators['type']
        
        results_by_category = {}
        
        # Search each entity type (unless filtered)
        if not type_filter or type_filter == 'command':
            results_by_category['commands'] = self.search_commands(text_query or query, limit_per_category)
        
        if not type_filter or type_filter == 'ticket':
            results_by_category['tickets'] = self.search_tickets(
                text_query, operators, limit_per_category * 2, current_user_id
            )
        
        if not type_filter or type_filter == 'user':
            results_by_category['users'] = self.search_users(text_query or query, limit_per_category)
        
        if not type_filter or type_filter == 'team':
            results_by_category['teams'] = self.search_teams(text_query or query, limit_per_category)
        
        if not type_filter or type_filter == 'customer':
            results_by_category['customers'] = self.search_customers(text_query or query, limit_per_category)
        
        if not type_filter or type_filter == 'shift':
            results_by_category['shifts'] = self.search_shifts(text_query or query, 5)
        
        if not type_filter or type_filter == 'rule':
            results_by_category['routing_rules'] = self.search_routing_rules(text_query or query, 5)
        
        if not type_filter or type_filter == 'field':
            results_by_category['custom_fields'] = self.search_custom_fields(text_query or query, 5)
        
        # Flatten and sort all results
        all_results = []
        for category, items in results_by_category.items():
            all_results.extend(items)
        
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return {
            "query": query,
            "text_query": text_query,
            "operators": operators,
            "results": all_results,
            "total": len(all_results),
            "by_category": results_by_category
        }
    
    def get_search_suggestions(self, partial_query: str) -> List[Dict]:
        """Get autocomplete suggestions as user types"""
        suggestions = []
        
        # Suggest operators
        if ':' not in partial_query:
            for op in SEARCH_OPERATORS.keys():
                if op.startswith(partial_query.lower()):
                    suggestions.append({
                        "type": "operator",
                        "text": f"{op}:",
                        "description": f"Filter by {op}"
                    })
        
        # Suggest operator values
        if ':' in partial_query:
            parts = partial_query.split(':')
            if len(parts) == 2:
                op, val = parts[0].lower(), parts[1].lower()
                if op in SEARCH_OPERATORS:
                    for valid_val in SEARCH_OPERATORS[op]:
                        if valid_val.startswith(val):
                            suggestions.append({
                                "type": "operator_value",
                                "text": f"{op}:{valid_val}",
                                "description": f"{op} is {valid_val}"
                            })
        
        return suggestions[:10]


# Singleton
_search_engine = None

def get_search_engine(db) -> SearchEngine:
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine(db)
        _search_engine.ensure_indexes()
    return _search_engine
