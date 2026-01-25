"""
Trinity Comprehensive Search Module
Full-text search across all entities with fuzzy matching
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pymongo import MongoClient, TEXT
from bson import ObjectId
import re
import logging

logger = logging.getLogger(__name__)

# Platform commands/features for search
PLATFORM_COMMANDS = [
    # Navigation
    {"id": "nav-dashboard", "type": "command", "category": "Navigation", "title": "Go to Dashboard", "description": "View Kanban board and ticket overview", "action": "/dashboard", "keywords": ["home", "main", "kanban", "board"]},
    {"id": "nav-all-tickets", "type": "command", "category": "Navigation", "title": "All Tickets", "description": "View all tickets in the system", "action": "/all-tickets", "keywords": ["tickets", "list", "all"]},
    {"id": "nav-open-tickets", "type": "command", "category": "Navigation", "title": "Open Tickets", "description": "View tickets that are open", "action": "/open-tickets", "keywords": ["open", "active", "pending"]},
    {"id": "nav-waiting-tickets", "type": "command", "category": "Navigation", "title": "Waiting on Customer", "description": "View tickets waiting for customer response", "action": "/waiting-tickets", "keywords": ["waiting", "customer", "response"]},
    {"id": "nav-closed-tickets", "type": "command", "category": "Navigation", "title": "Closed Tickets", "description": "View resolved tickets", "action": "/closed-tickets", "keywords": ["closed", "resolved", "done", "completed"]},
    {"id": "nav-teams", "type": "command", "category": "Navigation", "title": "Teams", "description": "Manage teams and members", "action": "/teams", "keywords": ["teams", "groups", "members", "organization"]},
    {"id": "nav-profile", "type": "command", "category": "Navigation", "title": "My Profile", "description": "View and edit your profile", "action": "/profile", "keywords": ["profile", "account", "me", "settings"]},
    {"id": "nav-settings", "type": "command", "category": "Navigation", "title": "Settings", "description": "App settings and preferences", "action": "/settings", "keywords": ["settings", "preferences", "config", "theme"]},
    {"id": "nav-admin", "type": "command", "category": "Navigation", "title": "Admin Panel", "description": "Admin settings and configuration", "action": "/admin", "keywords": ["admin", "administration", "configure", "custom fields"]},
    
    # Actions
    {"id": "action-new-ticket", "type": "action", "category": "Actions", "title": "Create New Ticket", "description": "Create a new support ticket", "action": "create_ticket", "keywords": ["new", "create", "add", "ticket"]},
    {"id": "action-new-team", "type": "action", "category": "Actions", "title": "Create New Team", "description": "Create a new team", "action": "create_team", "keywords": ["new", "create", "add", "team"]},
    {"id": "action-export", "type": "action", "category": "Actions", "title": "Export Data", "description": "Export tickets, users, or teams", "action": "export", "keywords": ["export", "download", "backup", "csv", "json"]},
    {"id": "action-theme-toggle", "type": "action", "category": "Actions", "title": "Toggle Theme", "description": "Switch between light and dark mode", "action": "toggle_theme", "keywords": ["theme", "dark", "light", "mode", "appearance"]},
    {"id": "action-logout", "type": "action", "category": "Actions", "title": "Sign Out", "description": "Log out of your account", "action": "logout", "keywords": ["logout", "sign out", "exit"]},
    
    # Admin Features
    {"id": "admin-custom-fields", "type": "command", "category": "Admin", "title": "Custom Fields", "description": "Manage custom ticket and user fields", "action": "/admin?tab=custom-fields", "keywords": ["custom", "fields", "attributes", "properties"]},
    {"id": "admin-routing-rules", "type": "command", "category": "Admin", "title": "Routing Rules", "description": "Configure automatic ticket routing", "action": "/admin?tab=routing-rules", "keywords": ["routing", "rules", "automation", "assignment"]},
    {"id": "admin-shifts", "type": "command", "category": "Admin", "title": "Shifts & Schedules", "description": "Manage shift schedules", "action": "/admin?tab=shifts", "keywords": ["shifts", "schedule", "time", "availability"]},
]


class SearchEngine:
    """Comprehensive search engine for Trinity"""
    
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
            # Tickets - weighted text index
            self.tickets.create_index([
                ("title", TEXT),
                ("content", TEXT),
                ("tags", TEXT),
                ("ticket_number", TEXT)
            ], weights={
                "title": 10,
                "ticket_number": 8,
                "tags": 5,
                "content": 1
            }, name="ticket_search_idx", default_language="english")
            logger.info("Created ticket search index")
        except Exception as e:
            logger.warning(f"Ticket index may already exist: {e}")
        
        try:
            # Users
            self.users.create_index([
                ("name", TEXT),
                ("email", TEXT)
            ], weights={
                "name": 10,
                "email": 5
            }, name="user_search_idx")
            logger.info("Created user search index")
        except Exception as e:
            logger.warning(f"User index may already exist: {e}")
        
        try:
            # Teams
            self.teams.create_index([
                ("name", TEXT),
                ("type", TEXT),
                ("description", TEXT)
            ], weights={
                "name": 10,
                "type": 5,
                "description": 1
            }, name="team_search_idx")
            logger.info("Created team search index")
        except Exception as e:
            logger.warning(f"Team index may already exist: {e}")
        
        try:
            # Shifts
            self.shifts.create_index([
                ("name", TEXT)
            ], name="shift_search_idx")
            logger.info("Created shift search index")
        except Exception as e:
            logger.warning(f"Shift index may already exist: {e}")
        
        try:
            # Routing rules
            self.routing_rules.create_index([
                ("name", TEXT),
                ("description", TEXT)
            ], name="routing_rule_search_idx")
            logger.info("Created routing rule search index")
        except Exception as e:
            logger.warning(f"Routing rule index may already exist: {e}")
    
    def _fuzzy_match(self, query: str, text: str) -> float:
        """Calculate fuzzy match score (0-1)"""
        if not query or not text:
            return 0.0
        
        query = query.lower()
        text = text.lower()
        
        # Exact match
        if query in text:
            return 1.0
        
        # Word match
        query_words = set(query.split())
        text_words = set(text.split())
        if query_words & text_words:
            return 0.8
        
        # Prefix match
        for word in text_words:
            if word.startswith(query) or query.startswith(word):
                return 0.6
        
        return 0.0
    
    def search_commands(self, query: str, limit: int = 5) -> List[Dict]:
        """Search platform commands/features"""
        query_lower = query.lower()
        results = []
        
        for cmd in PLATFORM_COMMANDS:
            score = 0.0
            
            # Check title
            title_score = self._fuzzy_match(query_lower, cmd["title"].lower())
            score = max(score, title_score * 1.0)
            
            # Check description
            desc_score = self._fuzzy_match(query_lower, cmd["description"].lower())
            score = max(score, desc_score * 0.7)
            
            # Check keywords
            for keyword in cmd.get("keywords", []):
                kw_score = self._fuzzy_match(query_lower, keyword)
                score = max(score, kw_score * 0.9)
            
            if score > 0.3:
                results.append({
                    **cmd,
                    "score": score
                })
        
        # Sort by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def search_tickets(self, query: str, limit: int = 10) -> List[Dict]:
        """Search tickets using text index"""
        results = []
        
        try:
            # Try text search first
            cursor = self.tickets.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            for doc in cursor:
                results.append({
                    "id": doc.get("ticket_id", str(doc.get("_id"))),
                    "type": "ticket",
                    "category": "Tickets",
                    "title": doc.get("title", "Untitled"),
                    "description": f"#{doc.get('ticket_number', 'N/A')} - {doc.get('status', 'unknown')}",
                    "status": doc.get("status"),
                    "priority": doc.get("priority"),
                    "action": f"/all-tickets?ticket={doc.get('ticket_id')}",
                    "score": doc.get("score", 0),
                    "metadata": {
                        "ticket_number": doc.get("ticket_number"),
                        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None
                    }
                })
        except Exception as e:
            logger.error(f"Ticket search error: {e}")
            # Fallback to regex search
            regex = {"$regex": query, "$options": "i"}
            cursor = self.tickets.find({
                "$or": [
                    {"title": regex},
                    {"content": regex},
                    {"ticket_number": regex}
                ]
            }).limit(limit)
            
            for doc in cursor:
                results.append({
                    "id": doc.get("ticket_id", str(doc.get("_id"))),
                    "type": "ticket",
                    "category": "Tickets",
                    "title": doc.get("title", "Untitled"),
                    "description": f"#{doc.get('ticket_number', 'N/A')} - {doc.get('status', 'unknown')}",
                    "status": doc.get("status"),
                    "priority": doc.get("priority"),
                    "action": f"/all-tickets?ticket={doc.get('ticket_id')}",
                    "score": 0.5
                })
        
        return results
    
    def search_users(self, query: str, limit: int = 5) -> List[Dict]:
        """Search users"""
        results = []
        
        try:
            cursor = self.users.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            for doc in cursor:
                results.append({
                    "id": doc.get("user_id", str(doc.get("_id"))),
                    "type": "user",
                    "category": "Users",
                    "title": doc.get("name", "Unknown"),
                    "description": doc.get("email", ""),
                    "picture": doc.get("picture"),
                    "action": f"/profile?user={doc.get('user_id')}",
                    "score": doc.get("score", 0)
                })
        except Exception as e:
            logger.error(f"User search error: {e}")
            # Fallback
            regex = {"$regex": query, "$options": "i"}
            cursor = self.users.find({
                "$or": [{"name": regex}, {"email": regex}]
            }).limit(limit)
            
            for doc in cursor:
                results.append({
                    "id": doc.get("user_id", str(doc.get("_id"))),
                    "type": "user",
                    "category": "Users",
                    "title": doc.get("name", "Unknown"),
                    "description": doc.get("email", ""),
                    "picture": doc.get("picture"),
                    "action": f"/profile?user={doc.get('user_id')}",
                    "score": 0.5
                })
        
        return results
    
    def search_teams(self, query: str, limit: int = 5) -> List[Dict]:
        """Search teams"""
        results = []
        
        try:
            cursor = self.teams.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            for doc in cursor:
                results.append({
                    "id": doc.get("team_id", str(doc.get("_id"))),
                    "type": "team",
                    "category": "Teams",
                    "title": doc.get("name", "Unknown Team"),
                    "description": doc.get("type", "") or doc.get("description", ""),
                    "action": f"/teams?team={doc.get('team_id')}",
                    "score": doc.get("score", 0),
                    "metadata": {
                        "member_count": doc.get("member_count", 0)
                    }
                })
        except Exception as e:
            logger.error(f"Team search error: {e}")
            regex = {"$regex": query, "$options": "i"}
            cursor = self.teams.find({
                "$or": [{"name": regex}, {"type": regex}]
            }).limit(limit)
            
            for doc in cursor:
                results.append({
                    "id": doc.get("team_id", str(doc.get("_id"))),
                    "type": "team",
                    "category": "Teams",
                    "title": doc.get("name", "Unknown Team"),
                    "description": doc.get("type", ""),
                    "action": f"/teams?team={doc.get('team_id')}",
                    "score": 0.5
                })
        
        return results
    
    def search_shifts(self, query: str, limit: int = 3) -> List[Dict]:
        """Search shifts"""
        results = []
        
        regex = {"$regex": query, "$options": "i"}
        cursor = self.shifts.find({"name": regex}).limit(limit)
        
        for doc in cursor:
            results.append({
                "id": doc.get("shift_id", str(doc.get("_id"))),
                "type": "shift",
                "category": "Shifts",
                "title": doc.get("name", "Unknown Shift"),
                "description": f"{doc.get('start_time', '')} - {doc.get('end_time', '')}",
                "action": "/admin?tab=shifts",
                "score": 0.5
            })
        
        return results
    
    def search_routing_rules(self, query: str, limit: int = 3) -> List[Dict]:
        """Search routing rules"""
        results = []
        
        regex = {"$regex": query, "$options": "i"}
        cursor = self.routing_rules.find({
            "$or": [{"name": regex}, {"description": regex}]
        }).limit(limit)
        
        for doc in cursor:
            results.append({
                "id": doc.get("rule_id", str(doc.get("_id"))),
                "type": "routing_rule",
                "category": "Routing Rules",
                "title": doc.get("name", "Unknown Rule"),
                "description": doc.get("description", ""),
                "action": "/admin?tab=routing-rules",
                "score": 0.5,
                "metadata": {
                    "active": doc.get("active", False)
                }
            })
        
        return results
    
    def search_all(self, query: str, limit_per_category: int = 5) -> Dict[str, List]:
        """Search across all entities"""
        if not query or len(query) < 2:
            return {"results": [], "total": 0}
        
        results = {
            "commands": self.search_commands(query, limit_per_category),
            "tickets": self.search_tickets(query, limit_per_category),
            "users": self.search_users(query, limit_per_category),
            "teams": self.search_teams(query, limit_per_category),
            "shifts": self.search_shifts(query, 3),
            "routing_rules": self.search_routing_rules(query, 3)
        }
        
        # Flatten and sort all results
        all_results = []
        for category, items in results.items():
            all_results.extend(items)
        
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return {
            "results": all_results,
            "total": len(all_results),
            "by_category": results
        }
    
    def get_recent_searches(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get user's recent searches (placeholder for future implementation)"""
        # TODO: Implement search history storage
        return []
    
    def save_search(self, user_id: str, query: str):
        """Save search to history (placeholder for future implementation)"""
        # TODO: Implement search history storage
        pass


# Singleton instance creator
_search_engine = None

def get_search_engine(db) -> SearchEngine:
    """Get or create search engine instance"""
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine(db)
        _search_engine.ensure_indexes()
    return _search_engine
