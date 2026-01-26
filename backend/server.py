from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Response, Request, Cookie, Header, Security, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone, time
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
import os
import json
import csv
import io
import uuid
import httpx
import base64
import re
import secrets
import hashlib
import pytz
import asyncio
import logging
from email.utils import parseaddr
from html import unescape
from dotenv import load_dotenv
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Real-time and Search imports
from realtime import sio, socket_app, broadcast_ticket_update, broadcast_ticket_created, broadcast_ticket_deleted, get_presence_stats, get_users_viewing_ticket, broadcast_leave_created, broadcast_leave_updated, broadcast_leave_deleted, broadcast_mention_notification
from search import get_search_engine
from leave_management import get_leave_manager, LeaveRequest, LeaveUpdate

# Load environment variables from .env file
load_dotenv()

# Gmail API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = FastAPI(
    title="Trinity API",
    description="Enterprise ticket management platform with real-time collaboration",
    version="2.0.0"
)

# Mount Socket.IO for WebSocket support
# Socket.IO will handle /socket.io/ routes
app.mount("/socket.io", socket_app)

# CORS - Allow specific origins for security
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",")
# Default to preview URL if not set
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == [""]:
    ALLOWED_ORIGINS = [
        "https://favorite-tickets.preview.emergentagent.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB
MONGO_URL = os.environ.get("MONGO_URL")
client = MongoClient(MONGO_URL)
db = client.tickflow
users_collection = db.users
tickets_collection = db.tickets
sessions_collection = db.user_sessions
api_keys_collection = db.api_keys
counters_collection = db.counters

# Emergent Auth Configuration
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
ALLOWED_DOMAIN = None  # Allow any email domain for testing

# Gmail OAuth Configuration
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")
GMAIL_REDIRECT_URI = os.environ.get("GMAIL_REDIRECT_URI", "")
GMAIL_WATCH_EMAIL = os.environ.get("GMAIL_WATCH_EMAIL", "")
# Query filter to sync only support-related emails (customize as needed)
GMAIL_SYNC_QUERY = os.environ.get("GMAIL_SYNC_QUERY", "from:usepylon.com OR to:support@emergent.sh OR from:support@emergent.sh")
# Mock mode - don't actually send emails
EMAIL_MOCK_MODE = os.environ.get("EMAIL_MOCK_MODE", "true").lower() == "true"

GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Gmail tokens collection
gmail_tokens_collection = db.gmail_tokens
email_threads_collection = db.email_threads

# Phase 2: Team & Notes collections
teams_collection = db.teams
messages_collection = db.messages  # For internal notes and replies

# Phase 3: Admin settings collections
custom_fields_collection = db.custom_fields  # Custom fields for tickets/users
admin_settings_collection = db.admin_settings  # General admin settings

# Phase 4: Shifts & Scheduling collections
shifts_collection = db.shifts  # Shift definitions per team
user_shifts_collection = db.user_shifts  # User-to-shift assignments

# Phase 5: Routing Rules
routing_rules_collection = db.routing_rules  # Ticket routing rules

# Phase 6: Initialize Search Engine
search_engine = get_search_engine(db)

# Phase 7: Ticket Changelog (audit log)
ticket_changelog_collection = db.ticket_changelog  # All metadata changes for tickets

# Phase 8: Feature Requests
feature_requests_collection = db.feature_requests  # Product feature requests linked to tickets

# Phase 9: Customers
customers_collection = db.customers  # Customer profiles with linked emails

# Common B2C email domains (for B2B prospect detection)
B2C_EMAIL_DOMAINS = {
    'gmail.com', 'googlemail.com', 'yahoo.com', 'yahoo.co.uk', 'yahoo.co.in',
    'hotmail.com', 'hotmail.co.uk', 'outlook.com', 'outlook.co.uk', 'live.com',
    'msn.com', 'aol.com', 'icloud.com', 'me.com', 'mac.com', 'protonmail.com',
    'proton.me', 'zoho.com', 'yandex.com', 'mail.com', 'gmx.com', 'gmx.net',
    'fastmail.com', 'tutanota.com', 'hey.com', 'pm.me', 'inbox.com',
    'rediffmail.com', 'qq.com', '163.com', '126.com', 'sina.com', 'sohu.com'
}

# Phase 13: CSAT (Customer Satisfaction)
csat_responses_collection = db.csat_responses  # CSAT ratings and feedback
csat_tokens_collection = db.csat_tokens  # Secure tokens for email rating links

# System timezone - IST
SYSTEM_TIMEZONE = "Asia/Kolkata"

# API Key Security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# ==================== Utility Functions ====================

def log_ticket_change(ticket_id: str, uuid: str, field: str, old_value: Any, new_value: Any, changed_by: str, change_type: str = "update", metadata: dict = None):
    """Log a change to a ticket's metadata for audit purposes"""
    changelog_entry = {
        "changelog_id": f"cl_{uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "ticket_uuid": uuid,
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "change_type": change_type,  # create, update, delete, auto_reassign
        "changed_by": changed_by,
        "changed_at": datetime.now(timezone.utc)
    }
    if metadata:
        changelog_entry["metadata"] = metadata
    ticket_changelog_collection.insert_one(changelog_entry)
    return changelog_entry

def log_ticket_changes_batch(ticket_id: str, uuid: str, changes: Dict[str, Tuple[Any, Any]], changed_by: str, change_type: str = "update"):
    """Log multiple changes at once"""
    entries = []
    timestamp = datetime.now(timezone.utc)
    for field, (old_value, new_value) in changes.items():
        if old_value != new_value:
            entry = {
                "changelog_id": f"cl_{uuid4().hex[:12]}",
                "ticket_id": ticket_id,
                "ticket_uuid": uuid,
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
                "change_type": change_type,
                "changed_by": changed_by,
                "changed_at": timestamp
            }
            entries.append(entry)
    if entries:
        ticket_changelog_collection.insert_many(entries)
    return entries

from uuid import uuid4

def generate_ticket_id() -> str:
    """Generate sequential ticket ID (TKT-000001 format)"""
    counter = counters_collection.find_one_and_update(
        {"_id": "ticket_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return f"TKT-{counter['seq']:06d}"

def generate_customer_id() -> str:
    """Generate sequential customer ID (CUST-000001 format)"""
    counter = counters_collection.find_one_and_update(
        {"_id": "customer_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return f"CUST-{counter['seq']:06d}"

def extract_domain(email: str) -> Optional[str]:
    """Extract domain from email address"""
    if not email:
        return None
    try:
        # Handle "Name <email@domain.com>" format
        _, addr = parseaddr(email)
        if '@' in addr:
            return addr.split('@')[1].lower()
    except Exception:
        pass
    return None

def is_b2c_email(email: str) -> bool:
    """Check if email is from a common B2C provider"""
    domain = extract_domain(email)
    if not domain:
        return True  # Default to B2C if unknown
    return domain.lower() in B2C_EMAIL_DOMAINS

def detect_company_from_domain(domain: str) -> Optional[str]:
    """Try to extract company name from domain"""
    if not domain or domain.lower() in B2C_EMAIL_DOMAINS:
        return None
    # Extract company name from domain (e.g., acme.com -> Acme)
    parts = domain.split('.')
    if len(parts) >= 2:
        company = parts[0].replace('-', ' ').replace('_', ' ')
        return company.title()
    return None

def get_or_create_customer(email: str, name: str = None) -> dict:
    """
    Get existing customer by email or create new one.
    Checks primary_email and linked_emails.
    """
    if not email:
        return None
    
    email_lower = email.lower().strip()
    
    # Check if customer exists with this email (primary or linked)
    customer = customers_collection.find_one({
        "$or": [
            {"primary_email": email_lower},
            {"linked_emails": email_lower}
        ]
    })
    
    if customer:
        return serialize_doc(customer)
    
    # Create new customer
    domain = extract_domain(email_lower)
    is_b2c = is_b2c_email(email_lower)
    company_name = detect_company_from_domain(domain) if not is_b2c else None
    
    new_customer = {
        "customer_id": generate_customer_id(),
        "name": name or email_lower.split('@')[0].replace('.', ' ').replace('_', ' ').title(),
        "primary_email": email_lower,
        "linked_emails": [],
        "company_name": company_name,
        "company_domain": domain if not is_b2c else None,
        "customer_type": "b2b" if not is_b2c else "b2c",
        "priority_level": "standard",  # standard, priority, vip
        "net_payments": 0.0,  # Total payments received
        "assigned_agents": [],  # User IDs of agents assigned to this customer
        "tags": [],
        "notes": "",
        "custom_fields": {},  # User-defined fields
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    customers_collection.insert_one(new_customer)
    logger.info(f"Created new customer: {new_customer['customer_id']} for {email_lower}")
    
    return serialize_doc(new_customer)

def generate_api_key() -> tuple:
    """Generate API key and its hash"""
    # Generate a secure random key
    key = f"tk_live_{secrets.token_urlsafe(32)}"
    # Hash for storage
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, key_hash

def verify_api_key(key: str) -> Optional[dict]:
    """Verify API key and return associated data"""
    if not key:
        return None
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    api_key_doc = api_keys_collection.find_one({
        "key_hash": key_hash,
        "revoked": {"$ne": True}
    })
    if api_key_doc:
        # Update last used
        api_keys_collection.update_one(
            {"_id": api_key_doc["_id"]},
            {"$set": {"last_used_at": datetime.now(timezone.utc)}, "$inc": {"usage_count": 1}}
        )
        return api_key_doc
    return None

# Helper functions
def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        serialized = {}
        for key, value in doc.items():
            if key == "_id":
                continue  # Skip MongoDB's _id
            elif isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = serialize_doc(value)
            elif isinstance(value, list):
                serialized[key] = [serialize_doc(item) if isinstance(item, dict) else item for item in value]
            else:
                serialized[key] = value
        
        # For backward compatibility: if ticket_id exists, also set id
        if "ticket_id" in serialized:
            serialized["id"] = serialized["ticket_id"]
        # For backward compatibility: if user_id exists, also set id
        if "user_id" in serialized and "id" not in serialized:
            serialized["id"] = serialized["user_id"]
        
        return serialized
    return doc

# ==================== Shift & Timezone Utilities ====================

def get_ist_now():
    """Get current datetime in IST timezone"""
    ist = pytz.timezone(SYSTEM_TIMEZONE)
    return datetime.now(ist)

def parse_time_str(time_str: str) -> time:
    """Parse HH:MM string to time object"""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))

def is_user_on_shift(user_id: str, team_id: str = None) -> bool:
    """Check if a user is currently on shift"""
    now = get_ist_now()
    current_weekday = now.isoweekday()  # 1=Monday, 7=Sunday
    current_time = now.time()
    
    # Find user's shift assignments
    query = {"user_id": user_id}
    if team_id:
        query["team_id"] = team_id
    
    user_shift_docs = list(user_shifts_collection.find(query))
    
    for us_doc in user_shift_docs:
        shift = shifts_collection.find_one({"shift_id": us_doc.get("shift_id"), "is_active": True})
        if not shift:
            continue
        
        # Check if today is a working day for this shift
        if current_weekday not in shift.get("days_of_week", []):
            continue
        
        # Check if current time is within shift hours
        start = parse_time_str(shift.get("start_time", "00:00"))
        end = parse_time_str(shift.get("end_time", "23:59"))
        
        # Handle overnight shifts (e.g., 22:00 to 06:00)
        if start <= end:
            # Normal shift (e.g., 09:00 to 17:00)
            if start <= current_time <= end:
                return True
        else:
            # Overnight shift (e.g., 22:00 to 06:00)
            if current_time >= start or current_time <= end:
                return True
    
    return False

def get_on_shift_members(team_id: str) -> List[dict]:
    """Get all members currently on shift for a team"""
    team = teams_collection.find_one({"team_id": team_id})
    if not team:
        return []
    
    on_shift_members = []
    for member_id in team.get("members", []):
        if is_user_on_shift(member_id, team_id):
            user = users_collection.find_one({"user_id": member_id}, {"_id": 0})
            if user:
                on_shift_members.append(serialize_doc(user))
    
    return on_shift_members

def get_team_for_escalation_level(escalation_level: str) -> Optional[dict]:
    """Find the team that handles a given escalation level"""
    team = teams_collection.find_one({"escalation_level": escalation_level}, {"_id": 0})
    return serialize_doc(team) if team else None

def shift_based_round_robin(team_id: str) -> Optional[str]:
    """
    Get next assignee using round-robin within on-shift team members.
    Returns user_id or None if no one is on shift.
    """
    on_shift = get_on_shift_members(team_id)
    if not on_shift:
        return None
    
    team = teams_collection.find_one({"team_id": team_id})
    if not team:
        return None
    
    # Get current index and calculate next
    last_idx = team.get("last_assigned_idx", -1)
    next_idx = (last_idx + 1) % len(on_shift)
    
    # Update the index
    teams_collection.update_one(
        {"team_id": team_id},
        {"$set": {"last_assigned_idx": next_idx}}
    )
    
    return on_shift[next_idx].get("user_id")

def auto_assign_on_escalation(ticket_id: str, escalation_level: str) -> dict:
    """
    Auto-assign a ticket based on escalation level.
    Returns assignment result with status.
    """
    # Find team for this escalation level
    team = get_team_for_escalation_level(escalation_level)
    if not team:
        return {
            "status": "no_team",
            "message": f"No team found for escalation level {escalation_level}",
            "team_id": None,
            "assignee_id": None
        }
    
    team_id = team.get("team_id")
    
    # Try shift-based round-robin assignment
    assignee_id = shift_based_round_robin(team_id)
    
    # Update ticket
    update_data = {
        "team_id": team_id,
        "escalation_level": escalation_level,
        "updated_at": datetime.now(timezone.utc)
    }
    
    if assignee_id:
        update_data["assignee_id"] = assignee_id
        update_data["assigned_at"] = datetime.now(timezone.utc)
        status = "assigned"
        message = f"Ticket assigned to team {team.get('name')} and user {assignee_id}"
    else:
        # No one on shift - ticket goes to team queue
        update_data["assignee_id"] = None
        status = "queued"
        message = f"Ticket queued for team {team.get('name')} - no agents currently on shift"
    
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": update_data}
    )
    
    return {
        "status": status,
        "message": message,
        "team_id": team_id,
        "team_name": team.get("name"),
        "assignee_id": assignee_id
    }

# ==================== Auto-Reassignment on Reopen ====================

def get_auto_reassign_setting() -> bool:
    """Get the auto_reassign_reopened setting from admin settings"""
    settings = admin_settings_collection.find_one({"type": "global"})
    if settings:
        return settings.get("auto_reassign_reopened", False)
    return False

def handle_ticket_reopen_reassignment(ticket: dict, new_status: str, changed_by: str) -> Optional[dict]:
    """
    Handle auto-reassignment when a ticket is reopened.
    Returns reassignment info if reassignment occurred, None otherwise.
    
    Conditions for reassignment:
    1. Setting is enabled
    2. Ticket is being reopened (from resolved/closed to another status)
    3. Original assignee is not on shift
    4. There are agents on shift to assign to
    """
    # Check if setting is enabled
    if not get_auto_reassign_setting():
        return None
    
    old_status = ticket.get("status", "")
    
    # Check if this is a reopen (from resolved/closed to active status)
    resolved_statuses = ["resolved", "closed"]
    active_statuses = ["todo", "in_progress", "waiting", "review", "assigned", "queued"]
    
    if old_status not in resolved_statuses or new_status not in active_statuses:
        return None
    
    current_assignee_id = ticket.get("assignee_id")
    team_id = ticket.get("team_id")
    
    # If no assignee or no team, nothing to reassign
    if not current_assignee_id or not team_id:
        return None
    
    # Check if current assignee is on shift
    if is_user_on_shift(current_assignee_id, team_id):
        # Assignee is on shift, no need to reassign
        return None
    
    # Current assignee is NOT on shift - try to reassign using round-robin
    new_assignee_id = shift_based_round_robin(team_id)
    
    if new_assignee_id:
        # Found someone on shift - reassign
        new_assignee = users_collection.find_one({"user_id": new_assignee_id}, {"_id": 0})
        old_assignee = users_collection.find_one({"user_id": current_assignee_id}, {"_id": 0})
        
        # Create notification for new assignee
        notification_doc = {
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "type": "ticket_reassigned",
            "user_id": new_assignee_id,
            "ticket_id": ticket.get("ticket_id"),
            "ticket_title": ticket.get("title"),
            "message": f"Ticket '{ticket.get('title')}' has been automatically reassigned to you because the original assignee is not on shift.",
            "from_user_id": current_assignee_id,
            "from_user_name": old_assignee.get("name", "Unknown") if old_assignee else "Unknown",
            "read": False,
            "created_at": datetime.now(timezone.utc)
        }
        db.notifications.insert_one(notification_doc)
        
        return {
            "reassigned": True,
            "old_assignee_id": current_assignee_id,
            "old_assignee_name": old_assignee.get("name", "Unknown") if old_assignee else "Unknown",
            "new_assignee_id": new_assignee_id,
            "new_assignee_name": new_assignee.get("name", "Unknown") if new_assignee else "Unknown",
            "reason": "original_assignee_off_shift"
        }
    else:
        # No one is on shift - unassign the ticket
        return {
            "reassigned": True,
            "old_assignee_id": current_assignee_id,
            "new_assignee_id": None,
            "new_assignee_name": None,
            "reason": "no_agents_on_shift"
        }

def trigger_shift_start_assignment(user_id: str) -> List[dict]:
    """
    Triggered when a user starts their shift (e.g., on login, WebSocket connect).
    Assigns queued/unassigned tickets to the user using round-robin.
    
    Returns list of assigned tickets.
    """
    # Check if auto-assignment setting is enabled
    settings = admin_settings_collection.find_one({"type": "global"})
    if not settings or not settings.get("auto_assignment", True):
        return []
    
    # Check if auto-reassign reopened is enabled (this setting also enables shift-start assignment)
    if not settings.get("auto_reassign_reopened", False):
        return []
    
    # Get user's teams
    user_shifts = list(user_shifts_collection.find({"user_id": user_id}))
    if not user_shifts:
        return []
    
    # Check if user is actually on shift right now
    team_ids = []
    for shift_assignment in user_shifts:
        team_id = shift_assignment.get("team_id")
        if team_id and is_user_on_shift(user_id, team_id):
            team_ids.append(team_id)
    
    if not team_ids:
        return []
    
    # Find queued/unassigned tickets for these teams
    queued_tickets = list(tickets_collection.find({
        "team_id": {"$in": team_ids},
        "$or": [
            {"assignee_id": None},
            {"assignee_id": ""},
            {"status": "queued"}
        ],
        "status": {"$nin": ["resolved", "closed"]}
    }).sort("created_at", 1).limit(5))  # Limit to 5 tickets per shift start
    
    assigned_tickets = []
    
    for ticket in queued_tickets:
        # Use shift-based round-robin for the ticket's team
        new_assignee_id = shift_based_round_robin(ticket.get("team_id"))
        
        if new_assignee_id:
            # Assign the ticket
            tickets_collection.update_one(
                {"ticket_id": ticket["ticket_id"]},
                {
                    "$set": {
                        "assignee_id": new_assignee_id,
                        "status": "assigned" if ticket.get("status") == "queued" else ticket.get("status"),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Log to changelog
            log_ticket_change(
                ticket_id=ticket["ticket_id"],
                uuid=ticket.get("uuid", ""),
                field="assignee_id",
                old_value=None,
                new_value=new_assignee_id,
                changed_by="system",
                change_type="shift_start_assignment",
                metadata={"trigger": "shift_start", "user_id": user_id}
            )
            
            # Create notification
            notification_doc = {
                "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
                "type": "ticket_assigned",
                "user_id": new_assignee_id,
                "ticket_id": ticket["ticket_id"],
                "ticket_title": ticket.get("title"),
                "message": f"Ticket '{ticket.get('title')}' has been assigned to you at shift start.",
                "read": False,
                "created_at": datetime.now(timezone.utc)
            }
            db.notifications.insert_one(notification_doc)
            
            assigned_tickets.append({
                "ticket_id": ticket["ticket_id"],
                "title": ticket.get("title"),
                "assigned_to": new_assignee_id
            })
    
    return assigned_tickets

# ==================== Routing Rule Engine ====================

def evaluate_condition(ticket: dict, condition: dict) -> bool:
    """Evaluate a single routing rule condition against a ticket"""
    field = condition.get("field", "")
    operator = condition.get("operator", "")
    value = condition.get("value")
    
    # Get ticket field value
    ticket_value = ticket.get(field)
    
    # Handle special fields
    if field == "tags":
        ticket_value = ticket.get("tags", [])
    elif field == "customer_email":
        ticket_value = ticket.get("customer_email", "")
    elif field == "domain":
        # Extract domain from customer email
        email = ticket.get("customer_email", "")
        ticket_value = email.split("@")[-1] if "@" in email else ""
    
    # Evaluate based on operator
    try:
        if operator == "equals":
            return str(ticket_value).lower() == str(value).lower()
        elif operator == "not_equals":
            return str(ticket_value).lower() != str(value).lower()
        elif operator == "contains":
            if isinstance(ticket_value, list):
                return any(str(value).lower() in str(v).lower() for v in ticket_value)
            return str(value).lower() in str(ticket_value).lower()
        elif operator == "not_contains":
            if isinstance(ticket_value, list):
                return not any(str(value).lower() in str(v).lower() for v in ticket_value)
            return str(value).lower() not in str(ticket_value).lower()
        elif operator == "starts_with":
            return str(ticket_value).lower().startswith(str(value).lower())
        elif operator == "ends_with":
            return str(ticket_value).lower().endswith(str(value).lower())
        elif operator == "in":
            # Value should be a list
            if isinstance(value, list):
                return str(ticket_value).lower() in [str(v).lower() for v in value]
            return str(ticket_value).lower() == str(value).lower()
        elif operator == "not_in":
            if isinstance(value, list):
                return str(ticket_value).lower() not in [str(v).lower() for v in value]
            return str(ticket_value).lower() != str(value).lower()
        elif operator == "exists":
            return ticket_value is not None and ticket_value != "" and ticket_value != []
        elif operator == "not_exists":
            return ticket_value is None or ticket_value == "" or ticket_value == []
        elif operator == "tag_includes":
            # Check if tags list includes the value
            tags = ticket.get("tags", [])
            return str(value).lower() in [str(t).lower() for t in tags]
        elif operator == "tag_excludes":
            tags = ticket.get("tags", [])
            return str(value).lower() not in [str(t).lower() for t in tags]
    except Exception as e:
        logger.error(f"[ROUTING] Error evaluating condition: {e}")
        return False
    
    return False

def apply_routing_actions(ticket_id: str, actions: list) -> dict:
    """Apply routing rule actions to a ticket"""
    updates = {}
    results = []
    
    for action in actions:
        action_type = action.get("type", "")
        action_value = action.get("value")
        
        if action_type == "assign_team":
            updates["team_id"] = action_value
            results.append(f"Assigned to team {action_value}")
        elif action_type == "assign_user":
            updates["assignee_id"] = action_value
            updates["assigned_at"] = datetime.now(timezone.utc)
            results.append(f"Assigned to user {action_value}")
        elif action_type == "set_priority":
            updates["priority"] = action_value
            results.append(f"Set priority to {action_value}")
        elif action_type == "set_escalation":
            updates["escalation_level"] = action_value
            results.append(f"Set escalation to {action_value}")
        elif action_type == "add_tag":
            # Need to append to existing tags
            ticket = tickets_collection.find_one({"ticket_id": ticket_id})
            existing_tags = ticket.get("tags", []) if ticket else []
            if action_value not in existing_tags:
                updates["tags"] = existing_tags + [action_value]
                results.append(f"Added tag {action_value}")
        elif action_type == "set_status":
            updates["status"] = action_value
            results.append(f"Set status to {action_value}")
    
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        updates["routed_at"] = datetime.now(timezone.utc)
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": updates}
        )
    
    return {"updates": updates, "results": results}

def run_routing_rules(ticket: dict) -> dict:
    """Run all active routing rules against a ticket, return first matching rule's actions"""
    
    # First, check if customer has assigned agents (takes priority)
    customer_email = ticket.get("customer_email")
    if customer_email:
        customer = customers_collection.find_one({
            "$or": [
                {"primary_email": customer_email.lower()},
                {"linked_emails": customer_email.lower()}
            ]
        })
        
        if customer and customer.get("assigned_agents"):
            # Route to one of the customer's assigned agents using round-robin
            assigned_agents = customer["assigned_agents"]
            
            # Find agent with least tickets among assigned agents who are on shift
            best_agent = None
            min_tickets = float('inf')
            
            for agent_id in assigned_agents:
                # Check if agent is on shift for any team
                if is_user_on_shift(agent_id):
                    ticket_count = tickets_collection.count_documents({
                        "assignee_id": agent_id,
                        "status": {"$nin": ["resolved", "closed"]}
                    })
                    if ticket_count < min_tickets:
                        min_tickets = ticket_count
                        best_agent = agent_id
            
            if best_agent:
                # Assign to customer's preferred agent
                tickets_collection.update_one(
                    {"ticket_id": ticket["ticket_id"]},
                    {"$set": {
                        "assignee_id": best_agent,
                        "status": "assigned",
                        "updated_at": datetime.now(timezone.utc)
                    }}
                )
                
                agent = users_collection.find_one({"user_id": best_agent}, {"_id": 0})
                agent_name = agent.get("name", "Unknown") if agent else "Unknown"
                
                logger.info(f"[ROUTING] Assigned ticket {ticket['ticket_id']} to customer's preferred agent {best_agent}")
                
                return {
                    "matched": True,
                    "rule_id": "customer_assigned_agent",
                    "rule_name": f"Customer preferred agent: {agent_name}",
                    "updates": {"assignee_id": best_agent, "status": "assigned"},
                    "results": [f"Routed to customer's assigned agent: {agent_name}"]
                }
    
    # Get all active rules, sorted by priority (higher first)
    rules = list(routing_rules_collection.find(
        {"is_active": True}, 
        {"_id": 0}
    ).sort("priority", -1))
    
    for rule in rules:
        conditions = rule.get("conditions", [])
        
        # All conditions must match (AND logic)
        all_match = True
        for condition in conditions:
            if not evaluate_condition(ticket, condition):
                all_match = False
                break
        
        if all_match:
            # Apply actions
            actions = rule.get("actions", [])
            result = apply_routing_actions(ticket.get("ticket_id"), actions)
            return {
                "matched": True,
                "rule_id": rule.get("rule_id"),
                "rule_name": rule.get("name"),
                **result
            }
    
    return {"matched": False, "rule_id": None, "rule_name": None, "updates": {}, "results": []}

async def get_api_key_user(api_key: str = Security(API_KEY_HEADER)) -> Optional[dict]:
    """Authenticate via API key - returns None if no key provided"""
    if not api_key:
        return None
    api_key_doc = verify_api_key(api_key)
    if api_key_doc:
        # Return a user-like object for API key auth
        return {
            "user_id": api_key_doc.get("created_by", "api"),
            "email": api_key_doc.get("created_by_email", "api@system"),
            "name": api_key_doc.get("name", "API Key"),
            "auth_type": "api_key",
            "api_key_id": api_key_doc.get("key_id")
        }
    return None

async def get_current_user(
    request: Request, 
    session_token: Optional[str] = Cookie(None),
    api_key: str = Security(API_KEY_HEADER)
):
    """Get current user from session token or API key"""
    # Try API key first
    if api_key:
        api_user = await get_api_key_user(api_key)
        if api_user:
            return api_user
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Try cookie first, then Authorization header
    token = session_token
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session in database
    session_doc = sessions_collection.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check if session expired
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        sessions_collection.delete_one({"session_token": token})
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user data
    user_doc = users_collection.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    return serialize_doc(user_doc)

# Models
class SessionCreate(BaseModel):
    session_id: str

class TicketCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    status: str = "todo"
    assignee_id: Optional[str] = None
    priority: Optional[str] = "medium"
    tags: Optional[List[str]] = []
    customer_email: Optional[str] = None
    source: Optional[str] = "manual"  # manual, email, api, simulator
    escalation_level: Optional[str] = "L1"  # L1, L2, L3 - default L1

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    escalation_level: Optional[str] = None  # L1, L2, L3
    team_id: Optional[str] = None
    is_starred: Optional[bool] = None
    snoozed: Optional[bool] = None

class TicketReorder(BaseModel):
    ticket_id: str
    new_status: str
    new_order: int

class UserPreferences(BaseModel):
    theme: Optional[str] = "dark"

class APIKeyCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class APIKeyResponse(BaseModel):
    key_id: str
    name: str
    key: Optional[str] = None  # Only returned on creation
    created_at: str
    last_used_at: Optional[str] = None

# Phase 2: Team Models
class TeamCreate(BaseModel):
    name: str
    escalation_level: str = "L1"  # L1, L2, L3
    description: Optional[str] = ""

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    escalation_level: Optional[str] = None  # L1, L2, L3
    description: Optional[str] = None
    lead_id: Optional[str] = None

class TeamMemberAdd(BaseModel):
    user_id: str

class UserRoleUpdate(BaseModel):
    role: str  # agent, lead, admin
    team_id: Optional[str] = None
    skills: Optional[List[str]] = None
    max_tickets: Optional[int] = 10

# Phase 2: Internal Notes Model
class InternalNoteCreate(BaseModel):
    content: str
    mentions: Optional[List[str]] = []  # List of user_ids to mention
    type: Optional[str] = "internal_note"  # internal_note or reply

class TicketAssign(BaseModel):
    assignee_id: Optional[str] = None
    team_id: Optional[str] = None

# Phase 4: Shift & Escalation Models
class ShiftCreate(BaseModel):
    team_id: str
    name: str
    start_time: str  # HH:MM format in IST
    end_time: str    # HH:MM format in IST
    days_of_week: List[int] = [1, 2, 3, 4, 5]  # 1=Monday, 7=Sunday

class ShiftUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    days_of_week: Optional[List[int]] = None
    is_active: Optional[bool] = None

class UserShiftAssign(BaseModel):
    shift_id: str
    is_primary: bool = True
    effective_from: Optional[str] = None  # ISO date string

class TicketEscalate(BaseModel):
    escalation_level: str  # L1, L2, L3
    reason: Optional[str] = None

# Phase 5: Routing Rule Models
class RoutingRuleCondition(BaseModel):
    field: str  # priority, tags, customer_email, escalation_level, title, description
    operator: str  # equals, contains, starts_with, ends_with, in, not_in, greater_than, less_than
    value: Any  # The value to compare against

class RoutingRuleAction(BaseModel):
    type: str  # assign_team, assign_user, set_priority, set_escalation, add_tag
    value: str  # team_id, user_id, priority value, escalation level, or tag name

class RoutingRuleCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    conditions: List[Dict[str, Any]]  # List of conditions (all must match - AND logic)
    actions: List[Dict[str, Any]]  # List of actions to perform
    priority: int = 0  # Higher priority rules run first
    is_active: bool = True

class RoutingRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None

# Routes
@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "version": "1.0.0"}

# Emergent Auth endpoints
@app.post("/api/auth/session")
async def create_session(session_data: SessionCreate, response: Response):
    """Exchange session_id for session_token"""
    try:
        logger.info(f"[AUTH] Received session_id: {session_data.session_id[:20]}...")
        
        # Call Emergent Auth API to get user data
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"[AUTH] Calling Emergent Auth API: {EMERGENT_AUTH_URL}")
            auth_response = await client.get(
                EMERGENT_AUTH_URL,
                headers={"X-Session-ID": session_data.session_id}
            )
            logger.info(f"[AUTH] Emergent Auth response status: {auth_response.status_code}")
        
        if auth_response.status_code != 200:
            logger.info(f"[AUTH] Invalid session_id, status: {auth_response.status_code}")
            raise HTTPException(status_code=401, detail="Invalid session_id")
        
        user_data = auth_response.json()
        logger.info(f"[AUTH] Got user data: {user_data.get('email')}")
        
        # Verify email domain (skip if ALLOWED_DOMAIN is None)
        email = user_data.get("email", "")
        if ALLOWED_DOMAIN and not email.endswith(f"@{ALLOWED_DOMAIN}"):
            logger.info(f"[AUTH] Domain mismatch: {email} vs @{ALLOWED_DOMAIN}")
            raise HTTPException(
                status_code=403,
                detail=f"Access restricted to @{ALLOWED_DOMAIN} emails only"
            )
        
        logger.info(f"[AUTH] Email verified: {email}")
        session_token = user_data["session_token"]
        
        # Generate user_id if new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        
        # Create or update user in database
        logger.info(f"[AUTH] Upserting user: {email}")
        users_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "email": email,
                    "name": user_data.get("name", ""),
                    "picture": user_data.get("picture", ""),
                    "updated_at": datetime.now(timezone.utc)
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "created_at": datetime.now(timezone.utc),
                    "preferences": {"theme": "dark"}
                }
            },
            upsert=True
        )
        
        # Get the user document to get the actual user_id
        logger.info("[AUTH] Fetching user document")
        user_doc = users_collection.find_one({"email": email}, {"_id": 0})
        if not user_doc:
            raise Exception(f"User document not found after upsert: {email}")
        
        # If user_id doesn't exist (old user from previous auth system), add it
        if "user_id" not in user_doc:
            logger.info("[AUTH] Old user detected, adding user_id field")
            new_user_id = f"user_{uuid.uuid4().hex[:12]}"
            users_collection.update_one(
                {"email": email},
                {"$set": {"user_id": new_user_id}}
            )
            user_doc["user_id"] = new_user_id
        
        actual_user_id = user_doc["user_id"]
        logger.info(f"[AUTH] User ID: {actual_user_id}")
        
        # Store session
        logger.info("[AUTH] Storing session")
        sessions_collection.update_one(
            {"session_token": session_token},
            {
                "$set": {
                    "user_id": actual_user_id,
                    "session_token": session_token,
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
                    "created_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        # Set httpOnly cookie
        logger.info("[AUTH] Setting cookie")
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=7 * 24 * 60 * 60,  # 7 days
            path="/"
        )
        
        logger.info("[AUTH] Success! Returning user data")
        return serialize_doc(user_doc)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"[AUTH] ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user data"""
    return current_user

@app.post("/api/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Logout user and clear session"""
    if session_token:
        sessions_collection.delete_one({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}

# ==================== Test Authentication (Development Only) ====================

@app.post("/api/auth/test-login")
async def test_login(response: Response):
    """
    Create a test session for automated testing.
    This endpoint should be disabled in production.
    """
    import os
    
    # Create or get test user
    test_user_id = "test_user_automation"
    test_email = "test@tickflow.local"
    test_name = "Test User"
    
    # Upsert test user
    users_collection.update_one(
        {"user_id": test_user_id},
        {"$set": {
            "user_id": test_user_id,
            "email": test_email,
            "name": test_name,
            "picture": None,
            "role": "admin",
            "created_at": datetime.now(timezone.utc),
            "last_login": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    # Create session token
    session_token = f"test_session_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    # Store session
    sessions_collection.update_one(
        {"session_token": session_token},
        {"$set": {
            "session_token": session_token,
            "user_id": test_user_id,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at
        }},
        upsert=True
    )
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=False,  # Allow non-HTTPS for testing
        samesite="lax",
        max_age=86400,
        path="/"
    )
    
    return {
        "message": "Test session created",
        "user": {
            "user_id": test_user_id,
            "email": test_email,
            "name": test_name,
            "role": "admin"
        },
        "session_token": session_token
    }

# ==================== Shift-Start Assignment Trigger ====================

@app.post("/api/auth/shift-start")
async def trigger_shift_assignment(current_user: dict = Depends(get_current_user)):
    """
    Trigger shift-start auto-assignment of queued tickets.
    Called when a user logs in or connects to real-time (WebSocket).
    
    Only assigns tickets if:
    1. Auto-assignment and auto-reassign settings are enabled
    2. User is currently on shift for their team(s)
    3. There are queued/unassigned tickets
    """
    assigned = trigger_shift_start_assignment(current_user["user_id"])
    
    return {
        "triggered": True,
        "user_id": current_user["user_id"],
        "tickets_assigned": len(assigned),
        "assigned_tickets": assigned
    }

# ==================== API Key Management ====================

@app.post("/api/auth/api-keys")
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: dict = Depends(get_current_user)
):
    """Generate a new API key"""
    key, key_hash = generate_api_key()
    key_id = f"key_{uuid.uuid4().hex[:12]}"
    
    api_key_doc = {
        "key_id": key_id,
        "key_hash": key_hash,
        "key_prefix": key[:12],  # Store prefix for identification
        "name": key_data.name,
        "description": key_data.description,
        "created_by": current_user["user_id"],
        "created_by_email": current_user.get("email"),
        "created_at": datetime.now(timezone.utc),
        "last_used_at": None,
        "usage_count": 0,
        "revoked": False
    }
    
    api_keys_collection.insert_one(api_key_doc)
    
    # Return the key only once - it won't be retrievable later
    return {
        "key_id": key_id,
        "name": key_data.name,
        "key": key,  # Only shown once!
        "created_at": api_key_doc["created_at"].isoformat(),
        "message": "Save this key securely - it won't be shown again!"
    }

@app.get("/api/auth/api-keys")
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    """List all API keys for the current user"""
    keys = list(api_keys_collection.find(
        {"created_by": current_user["user_id"], "revoked": {"$ne": True}},
        {"key_hash": 0}  # Don't return the hash
    ))
    
    return [
        {
            "key_id": k["key_id"],
            "name": k["name"],
            "key_prefix": k.get("key_prefix", "***"),
            "description": k.get("description", ""),
            "created_at": k["created_at"].isoformat() if isinstance(k["created_at"], datetime) else k["created_at"],
            "last_used_at": k["last_used_at"].isoformat() if k.get("last_used_at") else None,
            "usage_count": k.get("usage_count", 0)
        }
        for k in keys
    ]

@app.delete("/api/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Revoke an API key"""
    result = api_keys_collection.update_one(
        {"key_id": key_id, "created_by": current_user["user_id"]},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"message": "API key revoked"}

# User profile endpoints
@app.get("/api/users/me")
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    return current_user

@app.put("/api/users/me/preferences")
async def update_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user)
):
    """Update user preferences (theme, etc.)"""
    users_collection.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {"preferences": preferences.dict(), "updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": "Preferences updated"}

@app.get("/api/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    users = list(users_collection.find({}, {"password": 0}))  # Exclude password, but keep _id for now
    result = []
    for user in users:
        serialized = serialize_doc(user)
        # Ensure id is set from user_id or _id
        if "id" not in serialized:
            if "user_id" in user:
                serialized["id"] = user["user_id"]
            elif "_id" in user:
                serialized["id"] = str(user["_id"])
        result.append(serialized)
    return result

# ==================== Phase 2: Team Management ====================

@app.post("/api/teams")
async def create_team(
    team_data: TeamCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new team"""
    team_id = f"team_{uuid.uuid4().hex[:12]}"
    
    team_doc = {
        "team_id": team_id,
        "name": team_data.name,
        "escalation_level": team_data.escalation_level,  # L1, L2, L3
        "description": team_data.description,
        "members": [],
        "lead_id": None,
        "last_assigned_idx": -1,  # For round-robin
        "timezone": SYSTEM_TIMEZONE,  # Default to IST
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    teams_collection.insert_one(team_doc)
    return serialize_doc(team_doc)

@app.get("/api/teams")
async def get_teams(current_user: dict = Depends(get_current_user)):
    """List all teams"""
    teams = list(teams_collection.find({}, {"_id": 0}))
    
    # Enrich with member count and member details
    for team in teams:
        team["member_count"] = len(team.get("members", []))
        # Get member details with on-shift status
        if team.get("members"):
            members = list(users_collection.find(
                {"user_id": {"$in": team["members"]}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1}
            ))
            # Add on-shift status to each member
            for member in members:
                member["is_on_shift"] = is_user_on_shift(member["user_id"], team.get("team_id"))
            team["member_details"] = members
        # Count on-shift members
        team["on_shift_count"] = len(get_on_shift_members(team.get("team_id")))
    
    return [serialize_doc(team) for team in teams]

@app.get("/api/teams/{team_id}")
async def get_team(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get team details"""
    team = teams_collection.find_one({"team_id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get member details
    if team.get("members"):
        members = list(users_collection.find(
            {"user_id": {"$in": team["members"]}},
            {"_id": 0}
        ))
        team["member_details"] = [serialize_doc(m) for m in members]
    
    return serialize_doc(team)

@app.put("/api/teams/{team_id}")
async def update_team(
    team_id: str,
    team_data: TeamUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update team details"""
    update_data = {k: v for k, v in team_data.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    result = teams_collection.update_one(
        {"team_id": team_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return teams_collection.find_one({"team_id": team_id}, {"_id": 0})

@app.delete("/api/teams/{team_id}")
async def delete_team(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a team"""
    # Remove team_id from all users first
    users_collection.update_many(
        {"team_id": team_id},
        {"$unset": {"team_id": ""}}
    )
    
    result = teams_collection.delete_one({"team_id": team_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {"message": "Team deleted"}

@app.post("/api/teams/{team_id}/members")
async def add_team_member(
    team_id: str,
    member: TeamMemberAdd,
    current_user: dict = Depends(get_current_user)
):
    """Add a member to a team"""
    # Verify team exists
    team = teams_collection.find_one({"team_id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verify user exists
    user = users_collection.find_one({"user_id": member.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Add to team members
    teams_collection.update_one(
        {"team_id": team_id},
        {
            "$addToSet": {"members": member.user_id},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    
    # Update user's team_id
    users_collection.update_one(
        {"user_id": member.user_id},
        {"$set": {"team_id": team_id, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Member added", "team_id": team_id, "user_id": member.user_id}

@app.delete("/api/teams/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a member from a team"""
    # Remove from team
    result = teams_collection.update_one(
        {"team_id": team_id},
        {
            "$pull": {"members": user_id},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Clear user's team_id
    users_collection.update_one(
        {"user_id": user_id},
        {"$unset": {"team_id": ""}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Member removed"}

# ==================== User Role Management ====================

@app.put("/api/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_data: UserRoleUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user role and team assignment"""
    update_data = {
        "role": role_data.role,
        "updated_at": datetime.now(timezone.utc)
    }
    
    if role_data.team_id is not None:
        update_data["team_id"] = role_data.team_id
    if role_data.skills is not None:
        update_data["skills"] = role_data.skills
    if role_data.max_tickets is not None:
        update_data["max_tickets"] = role_data.max_tickets
    
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If team_id changed, update team memberships
    if role_data.team_id:
        # Remove from old teams
        teams_collection.update_many(
            {"members": user_id},
            {"$pull": {"members": user_id}}
        )
        # Add to new team
        teams_collection.update_one(
            {"team_id": role_data.team_id},
            {"$addToSet": {"members": user_id}}
        )
    
    user = users_collection.find_one({"user_id": user_id}, {"_id": 0})
    return serialize_doc(user)

# ==================== Shift Management ====================

@app.post("/api/shifts")
async def create_shift(
    shift_data: ShiftCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new shift for a team"""
    # Verify team exists
    team = teams_collection.find_one({"team_id": shift_data.team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    shift_id = f"shift_{uuid.uuid4().hex[:12]}"
    
    shift_doc = {
        "shift_id": shift_id,
        "team_id": shift_data.team_id,
        "name": shift_data.name,
        "start_time": shift_data.start_time,
        "end_time": shift_data.end_time,
        "days_of_week": shift_data.days_of_week,
        "is_active": True,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    shifts_collection.insert_one(shift_doc)
    return serialize_doc(shift_doc)

@app.get("/api/shifts")
async def get_all_shifts(current_user: dict = Depends(get_current_user)):
    """Get all shifts"""
    shifts = list(shifts_collection.find({}, {"_id": 0}))
    
    # Enrich with team name, assigned user count, and user details
    for shift in shifts:
        team = teams_collection.find_one({"team_id": shift.get("team_id")}, {"_id": 0, "name": 1, "escalation_level": 1})
        if team:
            shift["team_name"] = team.get("name")
            shift["team_escalation_level"] = team.get("escalation_level")
        
        # Get users assigned to this shift
        user_shift_docs = list(user_shifts_collection.find({"shift_id": shift.get("shift_id")}, {"_id": 0}))
        user_ids = [us["user_id"] for us in user_shift_docs]
        
        shift["assigned_users_count"] = len(user_ids)
        
        if user_ids:
            users = list(users_collection.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1}
            ))
            shift["assigned_users"] = [serialize_doc(u) for u in users]
        else:
            shift["assigned_users"] = []
    
    return [serialize_doc(s) for s in shifts]

@app.get("/api/shifts/team/{team_id}")
async def get_team_shifts(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all shifts for a specific team"""
    shifts = list(shifts_collection.find({"team_id": team_id}, {"_id": 0}))
    
    # Enrich with assigned users
    for shift in shifts:
        user_shift_docs = list(user_shifts_collection.find({"shift_id": shift.get("shift_id")}, {"_id": 0}))
        user_ids = [us["user_id"] for us in user_shift_docs]
        
        if user_ids:
            users = list(users_collection.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1}
            ))
            shift["assigned_users"] = [serialize_doc(u) for u in users]
        else:
            shift["assigned_users"] = []
    
    return [serialize_doc(s) for s in shifts]

@app.put("/api/shifts/{shift_id}")
async def update_shift(
    shift_id: str,
    shift_data: ShiftUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a shift"""
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if shift_data.name is not None:
        update_data["name"] = shift_data.name
    if shift_data.start_time is not None:
        update_data["start_time"] = shift_data.start_time
    if shift_data.end_time is not None:
        update_data["end_time"] = shift_data.end_time
    if shift_data.days_of_week is not None:
        update_data["days_of_week"] = shift_data.days_of_week
    if shift_data.is_active is not None:
        update_data["is_active"] = shift_data.is_active
    
    result = shifts_collection.update_one(
        {"shift_id": shift_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    shift = shifts_collection.find_one({"shift_id": shift_id}, {"_id": 0})
    return serialize_doc(shift)

@app.delete("/api/shifts/{shift_id}")
async def delete_shift(
    shift_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a shift"""
    result = shifts_collection.delete_one({"shift_id": shift_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    # Also remove user-shift assignments
    user_shifts_collection.delete_many({"shift_id": shift_id})
    
    return {"message": "Shift deleted successfully"}

# ==================== User Shift Assignments ====================

@app.post("/api/users/{user_id}/shifts")
async def assign_user_to_shift(
    user_id: str,
    assignment: UserShiftAssign,
    current_user: dict = Depends(get_current_user)
):
    """Assign a user to a shift"""
    # Verify user exists
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify shift exists
    shift = shifts_collection.find_one({"shift_id": assignment.shift_id})
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    # Check if assignment already exists
    existing = user_shifts_collection.find_one({
        "user_id": user_id,
        "shift_id": assignment.shift_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="User already assigned to this shift")
    
    user_shift_id = f"us_{uuid.uuid4().hex[:12]}"
    
    user_shift_doc = {
        "user_shift_id": user_shift_id,
        "user_id": user_id,
        "team_id": shift.get("team_id"),
        "shift_id": assignment.shift_id,
        "is_primary": assignment.is_primary,
        "effective_from": assignment.effective_from or datetime.now(timezone.utc).isoformat(),
        "effective_to": None,
        "created_at": datetime.now(timezone.utc)
    }
    
    user_shifts_collection.insert_one(user_shift_doc)
    return serialize_doc(user_shift_doc)

@app.get("/api/users/{user_id}/shifts")
async def get_user_shifts(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all shifts assigned to a user"""
    user_shift_docs = list(user_shifts_collection.find({"user_id": user_id}, {"_id": 0}))
    
    # Enrich with shift details
    for us_doc in user_shift_docs:
        shift = shifts_collection.find_one({"shift_id": us_doc.get("shift_id")}, {"_id": 0})
        if shift:
            us_doc["shift_details"] = serialize_doc(shift)
            # Get team name
            team = teams_collection.find_one({"team_id": shift.get("team_id")}, {"_id": 0, "name": 1})
            if team:
                us_doc["team_name"] = team.get("name")
    
    return [serialize_doc(us) for us in user_shift_docs]

@app.delete("/api/users/{user_id}/shifts/{shift_id}")
async def remove_user_from_shift(
    user_id: str,
    shift_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a user from a shift"""
    result = user_shifts_collection.delete_one({
        "user_id": user_id,
        "shift_id": shift_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User shift assignment not found")
    
    return {"message": "User removed from shift successfully"}

# ==================== On-Shift Queries ====================

@app.get("/api/teams/{team_id}/on-shift")
async def get_team_on_shift_members(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all team members currently on shift"""
    team = teams_collection.find_one({"team_id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    on_shift = get_on_shift_members(team_id)
    
    # Get current IST time for reference
    ist_now = get_ist_now()
    
    return {
        "team_id": team_id,
        "team_name": team.get("name"),
        "current_time_ist": ist_now.strftime("%Y-%m-%d %H:%M:%S"),
        "on_shift_count": len(on_shift),
        "on_shift_members": on_shift
    }

@app.get("/api/teams/{team_id}/schedule")
async def get_team_schedule(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get complete team schedule overview"""
    team = teams_collection.find_one({"team_id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    shifts = list(shifts_collection.find({"team_id": team_id, "is_active": True}, {"_id": 0}))
    
    schedule = []
    for shift in shifts:
        shift_data = serialize_doc(shift)
        
        # Get users assigned to this shift
        user_shift_docs = list(user_shifts_collection.find({"shift_id": shift.get("shift_id")}, {"_id": 0}))
        user_ids = [us["user_id"] for us in user_shift_docs]
        
        if user_ids:
            users = list(users_collection.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1}
            ))
            shift_data["members"] = [serialize_doc(u) for u in users]
        else:
            shift_data["members"] = []
        
        schedule.append(shift_data)
    
    # Get current IST time
    ist_now = get_ist_now()
    
    return {
        "team_id": team_id,
        "team_name": team.get("name"),
        "escalation_level": team.get("escalation_level"),
        "current_time_ist": ist_now.strftime("%Y-%m-%d %H:%M:%S"),
        "current_day": ist_now.strftime("%A"),
        "total_members": len(team.get("members", [])),
        "on_shift_now": len(get_on_shift_members(team_id)),
        "shifts": schedule
    }

# ==================== Ticket Escalation ====================

@app.put("/api/tickets/{ticket_id}/escalate")
async def escalate_ticket(
    ticket_id: str,
    escalation: TicketEscalate,
    current_user: dict = Depends(get_current_user)
):
    """Change ticket escalation level and auto-route to appropriate team"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    old_level = ticket.get("escalation_level", "L1")
    new_level = escalation.escalation_level
    
    if new_level not in ["L1", "L2", "L3"]:
        raise HTTPException(status_code=400, detail="Invalid escalation level. Must be L1, L2, or L3")
    
    # Record escalation in history
    escalation_record = {
        "from_level": old_level,
        "to_level": new_level,
        "reason": escalation.reason,
        "escalated_by": current_user["user_id"],
        "escalated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Auto-assign based on new escalation level
    assignment_result = auto_assign_on_escalation(ticket_id, new_level)
    
    # Update escalation history
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$push": {"escalation_history": escalation_record},
            "$set": {"escalated_at": datetime.now(timezone.utc)}
        }
    )
    
    # Get updated ticket
    updated_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    
    return {
        "ticket": serialize_doc(updated_ticket),
        "assignment": assignment_result,
        "escalation": escalation_record
    }

@app.get("/api/tickets/{ticket_id}/assignment-options")
async def get_ticket_assignment_options(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get assignment options for a ticket - team members and other teams"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    current_team_id = ticket.get("team_id")
    
    # Get current team members (if ticket is assigned to a team)
    team_members = []
    current_team = None
    if current_team_id:
        current_team = teams_collection.find_one({"team_id": current_team_id}, {"_id": 0})
        if current_team:
            for member_id in current_team.get("members", []):
                user = users_collection.find_one({"user_id": member_id}, {"_id": 0, "user_id": 1, "name": 1, "email": 1})
                if user:
                    user_data = serialize_doc(user)
                    user_data["is_on_shift"] = is_user_on_shift(member_id, current_team_id)
                    team_members.append(user_data)
    
    # Get other teams (grouped by escalation level)
    all_teams = list(teams_collection.find({}, {"_id": 0, "team_id": 1, "name": 1, "escalation_level": 1}))
    other_teams = []
    for team in all_teams:
        if team.get("team_id") != current_team_id:
            team_data = serialize_doc(team)
            team_data["on_shift_count"] = len(get_on_shift_members(team.get("team_id")))
            other_teams.append(team_data)
    
    # Sort other teams by escalation level
    other_teams.sort(key=lambda t: t.get("escalation_level", "L1"))
    
    return {
        "ticket_id": ticket_id,
        "current_team": serialize_doc(current_team) if current_team else None,
        "current_escalation_level": ticket.get("escalation_level", "L1"),
        "team_members": team_members,
        "other_teams": other_teams
    }

# ==================== Round Robin Assignment ====================

def get_available_agents(team_id: str) -> List[dict]:
    """Get available agents in a team for assignment"""
    team = teams_collection.find_one({"team_id": team_id})
    if not team or not team.get("members"):
        return []
    
    agents = list(users_collection.find({
        "user_id": {"$in": team["members"]},
        "status": {"$ne": "offline"},
        "on_leave": {"$ne": True}
    }))
    
    # Filter by capacity
    available = []
    for agent in agents:
        current_count = tickets_collection.count_documents({
            "assignee_id": agent["user_id"],
            "status": {"$nin": ["resolved", "closed"]}
        })
        max_tickets = agent.get("max_tickets", 10)
        if current_count < max_tickets:
            agent["current_ticket_count"] = current_count
            available.append(agent)
    
    return available

def round_robin_assign(team_id: str) -> Optional[str]:
    """Get next agent for round-robin assignment"""
    team = teams_collection.find_one({"team_id": team_id})
    if not team:
        return None
    
    available = get_available_agents(team_id)
    if not available:
        return None
    
    # Get last assigned index
    last_idx = team.get("last_assigned_idx", -1)
    
    # Find next available agent
    member_ids = [a["user_id"] for a in available]
    all_members = team.get("members", [])
    
    # Start from last_idx + 1 and wrap around
    for i in range(len(all_members)):
        idx = (last_idx + 1 + i) % len(all_members)
        member_id = all_members[idx]
        
        if member_id in member_ids:
            # Update last assigned index
            teams_collection.update_one(
                {"team_id": team_id},
                {"$set": {"last_assigned_idx": idx}}
            )
            return member_id
    
    return None

@app.post("/api/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: str,
    assignment: TicketAssign,
    current_user: dict = Depends(get_current_user)
):
    """Assign a ticket to a user or team"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    # If team specified, use round-robin
    if assignment.team_id:
        update_data["team_id"] = assignment.team_id
        
        if not assignment.assignee_id:
            # Auto-assign via round-robin
            assignee = round_robin_assign(assignment.team_id)
            if assignee:
                update_data["assignee_id"] = assignee
    
    # If specific assignee provided
    if assignment.assignee_id:
        update_data["assignee_id"] = assignment.assignee_id
        
        # Update assignee's ticket count
        users_collection.update_one(
            {"user_id": assignment.assignee_id},
            {"$inc": {"current_ticket_count": 1}}
        )
    
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": update_data}
    )
    
    # Log assignment in messages
    messages_collection.insert_one({
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "type": "system",
        "content": f"Ticket assigned to {update_data.get('assignee_id', 'team')}",
        "author_id": current_user["user_id"],
        "created_at": datetime.now(timezone.utc)
    })
    
    updated = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    return serialize_doc(updated)

@app.post("/api/routing/auto-assign")
async def auto_assign_ticket(
    ticket_id: str,
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Auto-assign a ticket using round-robin"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    assignee = round_robin_assign(team_id)
    if not assignee:
        raise HTTPException(status_code=400, detail="No available agents in team")
    
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {
            "assignee_id": assignee,
            "team_id": team_id,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return {"ticket_id": ticket_id, "assignee_id": assignee, "team_id": team_id}

# ==================== Team Inbox ====================

@app.get("/api/teams/{team_id}/tickets")
async def get_team_tickets(
    team_id: str,
    status: Optional[str] = None,
    unassigned_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get tickets for a team (team inbox)"""
    team = teams_collection.find_one({"team_id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    query = {"team_id": team_id}
    
    if status:
        query["status"] = status
    
    if unassigned_only:
        query["assignee_id"] = None
    
    tickets = list(tickets_collection.find(
        query,
        {"_id": 0}
    ).sort("created_at", DESCENDING).skip(skip).limit(limit))
    
    total = tickets_collection.count_documents(query)
    
    return {
        "tickets": [serialize_doc(t) for t in tickets],
        "total": total,
        "team_id": team_id,
        "team_name": team["name"]
    }

# ==================== Internal Notes ====================

@app.post("/api/tickets/{ticket_id}/notes")
async def add_internal_note(
    ticket_id: str,
    note: InternalNoteCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Add an internal note to a ticket"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    mentions = note.mentions or []
    
    note_doc = {
        "message_id": message_id,
        "ticket_id": ticket_id,
        "type": note.type or "internal_note",
        "content": note.content,
        "author_id": current_user["user_id"],
        "author_name": current_user.get("name", "Unknown"),
        "author_email": current_user.get("email"),
        "mentions": mentions,
        "created_at": datetime.now(timezone.utc)
    }
    
    messages_collection.insert_one(note_doc)
    
    # Update ticket's updated_at and add mentioned users to ticket
    update_fields = {"updated_at": datetime.now(timezone.utc)}
    
    # Add mentioned users to ticket's mentioned_users array (for dashboard filtering)
    if mentions:
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {
                "$set": update_fields,
                "$addToSet": {"mentioned_users": {"$each": mentions}}
            }
        )
        
        # Broadcast mention notifications to mentioned users
        for mentioned_user_id in mentions:
            if mentioned_user_id != current_user["user_id"]:
                background_tasks.add_task(
                    broadcast_mention_notification,
                    mentioned_user_id,
                    ticket_id,
                    ticket.get("title", ""),
                    current_user.get("name", "Unknown"),
                    note.content[:100]
                )
    else:
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": update_fields}
        )
    
    return serialize_doc(note_doc)

@app.get("/api/tickets/{ticket_id}/notes")
async def get_ticket_notes(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all notes and replies for a ticket"""
    # Return both internal_note and reply types
    notes = list(messages_collection.find(
        {"ticket_id": ticket_id, "type": {"$in": ["internal_note", "reply"]}},
        {"_id": 0}
    ).sort("created_at", ASCENDING))
    
    return [serialize_doc(n) for n in notes]

@app.get("/api/tickets/{ticket_id}/activity")
async def get_ticket_activity(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all activity (notes, replies, system messages) for a ticket"""
    messages = list(messages_collection.find(
        {"ticket_id": ticket_id},
        {"_id": 0}
    ).sort("created_at", ASCENDING))
    
    return [serialize_doc(m) for m in messages]

# ==================== Tag Management ====================

@app.post("/api/tickets/{ticket_id}/tags")
async def add_tags(
    ticket_id: str,
    tags: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Add tags to a ticket"""
    result = tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$addToSet": {"tags": {"$each": tags}},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    return {"tags": ticket.get("tags", [])}

@app.delete("/api/tickets/{ticket_id}/tags/{tag}")
async def remove_tag(
    ticket_id: str,
    tag: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a tag from a ticket"""
    result = tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$pull": {"tags": tag},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    return {"tags": ticket.get("tags", [])}

# Ticket endpoints (protected)
@app.get("/api/tickets/starred")
async def get_starred_tickets(
    current_user: dict = Depends(get_current_user)
):
    """Get all starred tickets for display, regardless of status"""
    query = {"is_starred": True}
    tickets = list(tickets_collection.find(query).sort("updated_at", DESCENDING))
    return [serialize_doc(ticket) for ticket in tickets]


@app.get("/api/tickets")
async def get_tickets(
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    mentioned_user_id: Optional[str] = None,
    is_starred: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if assignee_id:
        query["assignee_id"] = assignee_id
    if mentioned_user_id:
        query["mentioned_users"] = mentioned_user_id
    if is_starred is not None:
        query["is_starred"] = is_starred
    
    tickets = list(tickets_collection.find(query).sort("order", ASCENDING))
    return [serialize_doc(ticket) for ticket in tickets]

@app.post("/api/tickets")
async def create_ticket(
    ticket_data: TicketCreate,
    current_user: dict = Depends(get_current_user)
):
    max_order_ticket = tickets_collection.find_one(
        {"status": ticket_data.status},
        sort=[("order", DESCENDING)]
    )
    next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
    
    # Generate sequential ticket ID and UUID
    ticket_id = generate_ticket_id()
    ticket_uuid = str(uuid4())
    
    # Extract domain from customer email if provided
    domain = extract_domain(ticket_data.customer_email) if ticket_data.customer_email else None
    
    # Auto-create or link customer
    customer_id = None
    if ticket_data.customer_email:
        customer = get_or_create_customer(ticket_data.customer_email)
        if customer:
            customer_id = customer.get("customer_id")
    
    now = datetime.now(timezone.utc)
    
    ticket_doc = {
        "ticket_id": ticket_id,
        "uuid": ticket_uuid,
        "title": ticket_data.title,
        "description": ticket_data.description,
        "status": ticket_data.status,
        "assignee_id": ticket_data.assignee_id,
        "priority": ticket_data.priority,
        "escalation_level": ticket_data.escalation_level or "L1",
        "order": next_order,
        "created_by": current_user["user_id"],
        "created_at": now,
        "updated_at": now,
        # New fields
        "source": ticket_data.source or "manual",
        "tags": ticket_data.tags or [],
        "customer_email": ticket_data.customer_email,
        "customer_id": customer_id,  # Link to customer entity
        "domain": domain,
        "is_starred": False,
        "snoozed": False
    }
    
    tickets_collection.insert_one(ticket_doc)
    
    # Log ticket creation in changelog
    log_ticket_change(
        ticket_id=ticket_id,
        uuid=ticket_uuid,
        field="ticket",
        old_value=None,
        new_value=ticket_doc.get("title"),
        changed_by=current_user["user_id"],
        change_type="create"
    )
    
    # Run routing rules on newly created ticket
    routing_result = run_routing_rules(ticket_doc)
    
    # Get the potentially updated ticket
    final_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    
    result = serialize_doc(final_ticket)
    result["routing_applied"] = routing_result.get("matched", False)
    result["routing_rule"] = routing_result.get("rule_name")
    
    # Broadcast real-time event
    asyncio.create_task(broadcast_ticket_created(
        result,
        {"user_id": current_user["user_id"], "name": current_user.get("name", "Unknown")}
    ))
    
    return result

@app.get("/api/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return serialize_doc(ticket)

@app.put("/api/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    ticket_data: TicketUpdate,
    current_user: dict = Depends(get_current_user)
):
    # Get current ticket state for changelog
    current_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not current_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    update_data = {k: v for k, v in ticket_data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    # Check for auto-reassignment on ticket reopen
    reassignment_info = None
    if "status" in update_data:
        reassignment_info = handle_ticket_reopen_reassignment(
            current_ticket, 
            update_data["status"],
            current_user["user_id"]
        )
        
        if reassignment_info and reassignment_info.get("reassigned"):
            # Apply reassignment to update_data
            update_data["assignee_id"] = reassignment_info.get("new_assignee_id")
            if reassignment_info.get("new_assignee_id") is None:
                # Unassign - also update status to queued
                update_data["status"] = "queued"
    
    # Build changelog entries for changed fields
    changes = {}
    for field, new_value in update_data.items():
        if field != "updated_at":
            old_value = current_ticket.get(field)
            if old_value != new_value:
                changes[field] = (old_value, new_value)
    
    result = tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Log changes to changelog
    if changes:
        log_ticket_changes_batch(
            ticket_id=ticket_id,
            uuid=current_ticket.get("uuid", ""),
            changes=changes,
            changed_by=current_user["user_id"],
            change_type="update"
        )
    
    # Log auto-reassignment to changelog if it occurred
    if reassignment_info and reassignment_info.get("reassigned"):
        reason_text = "Original assignee not on shift" if reassignment_info.get("reason") == "original_assignee_off_shift" else "No agents on shift - ticket unassigned"
        log_ticket_change(
            ticket_id=ticket_id,
            uuid=current_ticket.get("uuid", ""),
            field="auto_reassignment",
            old_value=reassignment_info.get("old_assignee_name"),
            new_value=reassignment_info.get("new_assignee_name") or "Unassigned",
            changed_by="system",
            change_type="auto_reassign",
            metadata={"reason": reason_text}
        )
    
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    serialized = serialize_doc(ticket)
    
    # Add reassignment info to response if it occurred
    if reassignment_info:
        serialized["_reassignment_info"] = reassignment_info
    
    # Broadcast real-time event
    asyncio.create_task(broadcast_ticket_update(
        ticket_id, 
        'updated', 
        serialized,
        {"user_id": current_user["user_id"], "name": current_user.get("name", "Unknown")}
    ))
    
    return serialized

@app.delete("/api/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Get ticket before deletion for changelog
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Log deletion
    log_ticket_change(
        ticket_id=ticket_id,
        uuid=ticket.get("uuid", ""),
        field="ticket",
        old_value=ticket.get("title"),
        new_value=None,
        changed_by=current_user["user_id"],
        change_type="delete"
    )
    
    result = tickets_collection.delete_one({"ticket_id": ticket_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Broadcast real-time event
    asyncio.create_task(broadcast_ticket_deleted(
        ticket_id,
        {"user_id": current_user["user_id"], "name": current_user.get("name", "Unknown")}
    ))
    
    return {"message": "Ticket deleted successfully"}

@app.get("/api/tickets/{ticket_id}/changelog")
async def get_ticket_changelog(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the full changelog/audit log for a ticket"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get all changelog entries for this ticket
    changelog = list(ticket_changelog_collection.find(
        {"ticket_id": ticket_id},
        {"_id": 0}
    ).sort("changed_at", DESCENDING))
    
    # Enrich with user names
    user_ids = list(set(entry.get("changed_by") for entry in changelog if entry.get("changed_by")))
    users = {u["user_id"]: u.get("name", "Unknown") for u in users_collection.find({"user_id": {"$in": user_ids}}, {"user_id": 1, "name": 1})}
    
    for entry in changelog:
        entry["changed_by_name"] = users.get(entry.get("changed_by"), "Unknown")
        if isinstance(entry.get("changed_at"), datetime):
            entry["changed_at"] = entry["changed_at"].isoformat()
    
    return changelog

@app.get("/api/tickets/{ticket_id}/metadata")
async def get_ticket_metadata(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive ticket metadata including timestamps and all fields"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get changelog summary
    changelog_count = ticket_changelog_collection.count_documents({"ticket_id": ticket_id})
    last_change = ticket_changelog_collection.find_one(
        {"ticket_id": ticket_id},
        {"_id": 0},
        sort=[("changed_at", DESCENDING)]
    )
    
    # Get notes/messages count
    notes_count = messages_collection.count_documents({"ticket_id": ticket_id})
    
    metadata = {
        "ticket_id": ticket.get("ticket_id"),
        "uuid": ticket.get("uuid"),
        "title": ticket.get("title"),
        "status": ticket.get("status"),
        "priority": ticket.get("priority"),
        "escalation_level": ticket.get("escalation_level"),
        "tags": ticket.get("tags", []),
        "source": ticket.get("source"),
        "customer_email": ticket.get("customer_email"),
        "domain": ticket.get("domain"),
        "assignee_id": ticket.get("assignee_id"),
        "team_id": ticket.get("team_id"),
        "is_starred": ticket.get("is_starred", False),
        "snoozed": ticket.get("snoozed", False),
        "custom_fields": ticket.get("custom_fields", {}),
        "timestamps": {
            "created_at": ticket.get("created_at").isoformat() if isinstance(ticket.get("created_at"), datetime) else ticket.get("created_at"),
            "updated_at": ticket.get("updated_at").isoformat() if isinstance(ticket.get("updated_at"), datetime) else ticket.get("updated_at"),
            "last_change": last_change.get("changed_at").isoformat() if last_change and isinstance(last_change.get("changed_at"), datetime) else None
        },
        "stats": {
            "changelog_entries": changelog_count,
            "notes_count": notes_count
        },
        "created_by": ticket.get("created_by")
    }
    
    return metadata

@app.post("/api/tickets/reorder")
async def reorder_tickets(
    reorder_data: TicketReorder,
    current_user: dict = Depends(get_current_user)
):
    ticket = tickets_collection.find_one({"ticket_id": reorder_data.ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    new_status = reorder_data.new_status
    
    tickets_collection.update_one(
        {"ticket_id": reorder_data.ticket_id},
        {"$set": {"status": new_status, "order": reorder_data.new_order, "updated_at": datetime.utcnow()}}
    )
    
    tickets_in_new_status = list(tickets_collection.find(
        {"status": new_status, "ticket_id": {"$ne": reorder_data.ticket_id}}
    ).sort("order", ASCENDING))
    
    for idx, t in enumerate(tickets_in_new_status):
        new_order = idx if idx < reorder_data.new_order else idx + 1
        tickets_collection.update_one(
            {"ticket_id": t["ticket_id"]},
            {"$set": {"order": new_order}}
        )
    
    return {"message": "Tickets reordered successfully"}

# Analytics endpoint
@app.get("/api/analytics/summary")
async def get_analytics_summary(current_user: dict = Depends(get_current_user)):
    status_counts = {}
    for ticket_status in ["todo", "in_progress", "waiting", "review", "resolved"]:
        count = tickets_collection.count_documents({"status": ticket_status})
        status_counts[ticket_status] = count
    
    pipeline = [
        {"$match": {"assignee_id": {"$ne": None}}},
        {"$group": {"_id": "$assignee_id", "count": {"$sum": 1}}}
    ]
    assignee_counts = list(tickets_collection.aggregate(pipeline))
    
    my_tickets_count = tickets_collection.count_documents({"assignee_id": current_user["user_id"]})
    
    return {
        "by_status": status_counts,
        "by_assignee": [{"assignee_id": item["_id"], "count": item["count"]} for item in assignee_counts],
        "my_tickets": my_tickets_count,
        "total": tickets_collection.count_documents({})
    }

# Export endpoint
@app.get("/api/export")
async def export_tickets(
    format: str = "json",
    current_user: dict = Depends(get_current_user)
):
    tickets = list(tickets_collection.find({}, {"_id": 0}))
    tickets_data = [serialize_doc(ticket) for ticket in tickets]
    
    if format == "csv":
        output = io.StringIO()
        if tickets_data:
            fieldnames = ["ticket_id", "title", "description", "status", "assignee_id", "priority", "order", "created_at", "updated_at"]
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for ticket in tickets_data:
                writer.writerow(ticket)
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=tickets.csv"}
        )
    else:
        return Response(
            content=json.dumps(tickets_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=tickets.json"}
        )

# Import endpoint
@app.post("/api/import")
async def import_tickets(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    content = await file.read()
    
    try:
        if file.filename.endswith(".json"):
            data = json.loads(content)
            if not isinstance(data, list):
                data = [data]
        elif file.filename.endswith(".csv"):
            csv_reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
            data = list(csv_reader)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use JSON or CSV.")
        
        imported_count = 0
        for item in data:
            ticket_id = generate_ticket_id()
            ticket_doc = {
                "ticket_id": ticket_id,
                "title": item.get("title", "Imported Ticket"),
                "description": item.get("description", ""),
                "status": item.get("status", "backlog"),
                "assignee_id": item.get("assignee_id"),
                "priority": item.get("priority", "medium"),
                "order": int(item.get("order", 0)),
                "created_by": current_user["user_id"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            tickets_collection.insert_one(ticket_doc)
            imported_count += 1
        
        return {
            "message": f"Successfully imported {imported_count} tickets",
            "count": imported_count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

# ==================== Gmail Integration ====================

def get_gmail_flow():
    """Create Gmail OAuth flow"""
    client_config = {
        "web": {
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GMAIL_REDIRECT_URI]
        }
    }
    flow = Flow.from_client_config(client_config, scopes=GMAIL_SCOPES)
    flow.redirect_uri = GMAIL_REDIRECT_URI
    return flow

def get_gmail_service(credentials_dict: dict):
    """Build Gmail API service from stored credentials"""
    credentials = Credentials(
        token=credentials_dict.get("access_token"),
        refresh_token=credentials_dict.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET
    )
    return build('gmail', 'v1', credentials=credentials)

def parse_email_body(payload):
    """Extract text body from email payload"""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part.get('body', {}):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    break
            elif part['mimeType'] == 'text/html' and not body:
                if 'data' in part.get('body', {}):
                    html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    # Simple HTML to text conversion
                    body = re.sub(r'<[^>]+>', '', html_body)
                    body = unescape(body)
            elif 'parts' in part:
                body = parse_email_body(part)
                if body:
                    break
    elif 'body' in payload and 'data' in payload['body']:
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    
    return body.strip()

def extract_email_metadata(headers):
    """Extract From, Subject, Date from email headers"""
    metadata = {"from": "", "subject": "", "date": "", "message_id": "", "to": ""}
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        if name == 'from':
            metadata['from'] = value
        elif name == 'subject':
            metadata['subject'] = value
        elif name == 'date':
            metadata['date'] = value
        elif name == 'message-id':
            metadata['message_id'] = value
        elif name == 'to':
            metadata['to'] = value
    return metadata

@app.get("/api/gmail/status")
async def gmail_status(current_user: dict = Depends(get_current_user)):
    """Check if Gmail is connected"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    is_connected = token_doc is not None and "access_token" in token_doc
    return {
        "connected": is_connected,
        "watch_email": GMAIL_WATCH_EMAIL if is_connected else None,
        "configured": bool(GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET)
    }

@app.get("/api/gmail/connect")
async def gmail_connect(current_user: dict = Depends(get_current_user)):
    """Initiate Gmail OAuth flow"""
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET:
        raise HTTPException(status_code=400, detail="Gmail credentials not configured")
    
    flow = get_gmail_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # Store state for verification
    gmail_tokens_collection.update_one(
        {"type": "gmail_oauth_state"},
        {"$set": {"state": state, "created_at": datetime.now(timezone.utc)}},
        upsert=True
    )
    
    return {"authorization_url": authorization_url}

@app.get("/api/auth/gmail/callback")
async def gmail_callback(code: str = None, state: str = None, error: str = None):
    """Handle Gmail OAuth callback"""
    frontend_url = "https://favorite-tickets.preview.emergentagent.com"
    
    if error:
        return RedirectResponse(url=f"{frontend_url}/settings?gmail_error={error}")
    
    if not code:
        return RedirectResponse(url=f"{frontend_url}/settings?gmail_error=no_code")
    
    try:
        flow = get_gmail_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Store tokens
        gmail_tokens_collection.update_one(
            {"type": "gmail_oauth"},
            {
                "$set": {
                    "access_token": credentials.token,
                    "refresh_token": credentials.refresh_token,
                    "token_uri": credentials.token_uri,
                    "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        logger.info("[GMAIL] OAuth tokens stored successfully")
        return RedirectResponse(url=f"{frontend_url}/settings?gmail_connected=true")
    
    except Exception as e:
        logger.info(f"[GMAIL] OAuth error: {str(e)}")
        return RedirectResponse(url=f"{frontend_url}/settings?gmail_error={str(e)}")

@app.post("/api/gmail/disconnect")
async def gmail_disconnect(current_user: dict = Depends(get_current_user)):
    """Disconnect Gmail integration"""
    gmail_tokens_collection.delete_one({"type": "gmail_oauth"})
    return {"message": "Gmail disconnected successfully"}

@app.get("/api/gmail/emails")
async def get_gmail_emails(
    max_results: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Fetch recent emails from connected Gmail account"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    try:
        service = get_gmail_service(token_doc)
        
        # Get list of messages
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            labelIds=['INBOX']
        ).execute()
        
        messages = results.get('messages', [])
        emails = []
        
        for msg in messages:
            msg_detail = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            metadata = extract_email_metadata(msg_detail.get('payload', {}).get('headers', []))
            body = parse_email_body(msg_detail.get('payload', {}))
            
            # Truncate body for listing
            body_preview = body[:500] + "..." if len(body) > 500 else body
            
            emails.append({
                "id": msg['id'],
                "thread_id": msg_detail.get('threadId'),
                "from": metadata['from'],
                "subject": metadata['subject'],
                "date": metadata['date'],
                "body_preview": body_preview,
                "snippet": msg_detail.get('snippet', ''),
                "labels": msg_detail.get('labelIds', [])
            })
        
        return {"emails": emails, "count": len(emails)}
    
    except Exception as e:
        logger.info(f"[GMAIL] Error fetching emails: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch emails: {str(e)}")

@app.get("/api/gmail/email/{message_id}")
async def get_gmail_email_detail(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get full email details"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    try:
        service = get_gmail_service(token_doc)
        
        msg_detail = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        metadata = extract_email_metadata(msg_detail.get('payload', {}).get('headers', []))
        body = parse_email_body(msg_detail.get('payload', {}))
        
        return {
            "id": message_id,
            "thread_id": msg_detail.get('threadId'),
            "from": metadata['from'],
            "to": metadata['to'],
            "subject": metadata['subject'],
            "date": metadata['date'],
            "body": body,
            "labels": msg_detail.get('labelIds', [])
        }
    
    except Exception as e:
        logger.info(f"[GMAIL] Error fetching email detail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch email: {str(e)}")

@app.post("/api/gmail/create-ticket/{message_id}")
async def create_ticket_from_email(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Create a ticket from an email"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    # Check if ticket already exists for this email
    existing = tickets_collection.find_one({"email_message_id": message_id})
    if existing:
        return serialize_doc(existing)
    
    try:
        service = get_gmail_service(token_doc)
        
        msg_detail = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        metadata = extract_email_metadata(msg_detail.get('payload', {}).get('headers', []))
        body = parse_email_body(msg_detail.get('payload', {}))
        
        # Parse sender email
        _, sender_email = parseaddr(metadata['from'])
        
        # Create ticket
        ticket_id = generate_ticket_id()
        max_order_ticket = tickets_collection.find_one(
            {"status": "todo"},
            sort=[("order", DESCENDING)]
        )
        next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
        
        ticket_doc = {
            "ticket_id": ticket_id,
            "title": metadata['subject'] or "No Subject",
            "description": body,
            "status": "todo",
            "priority": "medium",
            "order": next_order,
            "created_by": current_user["user_id"],
            "assignee_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            # Email metadata
            "source": "email",
            "email_message_id": message_id,
            "email_thread_id": msg_detail.get('threadId'),
            "email_from": metadata['from'],
            "email_sender": sender_email,
            "email_date": metadata['date']
        }
        
        tickets_collection.insert_one(ticket_doc)
        logger.info(f"[GMAIL] Created ticket {ticket_id} from email {message_id}")
        
        return serialize_doc(ticket_doc)
    
    except Exception as e:
        logger.info(f"[GMAIL] Error creating ticket from email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")

@app.post("/api/gmail/sync")
async def sync_emails_to_tickets(
    max_emails: int = 20,
    query: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Sync emails matching query to tickets"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    try:
        service = get_gmail_service(token_doc)
        
        # Use provided query or default support query
        search_query = query if query else GMAIL_SYNC_QUERY
        logger.info(f"[GMAIL] Syncing with query: {search_query}")
        
        results = service.users().messages().list(
            userId='me',
            maxResults=max_emails,
            q=search_query
        ).execute()
        
        messages = results.get('messages', [])
        logger.info(f"[GMAIL] Found {len(messages)} emails matching query")
        created_tickets = []
        skipped = 0
        
        for msg in messages:
            # Check if ticket already exists
            existing = tickets_collection.find_one({"email_message_id": msg['id']})
            if existing:
                skipped += 1
                continue
            
            msg_detail = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            metadata = extract_email_metadata(msg_detail.get('payload', {}).get('headers', []))
            body = parse_email_body(msg_detail.get('payload', {}))
            
            _, sender_email = parseaddr(metadata['from'])
            
            ticket_id = generate_ticket_id()
            max_order_ticket = tickets_collection.find_one(
                {"status": "todo"},
                sort=[("order", DESCENDING)]
            )
            next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
            
            ticket_doc = {
                "ticket_id": ticket_id,
                "title": metadata['subject'] or "No Subject",
                "description": body,
                "status": "todo",
                "priority": "medium",
                "order": next_order,
                "created_by": current_user["user_id"],
                "assignee_id": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "source": "email",
                "email_message_id": msg['id'],
                "email_thread_id": msg_detail.get('threadId'),
                "email_from": metadata['from'],
                "email_sender": sender_email,
                "email_date": metadata['date']
            }
            
            tickets_collection.insert_one(ticket_doc)
            created_tickets.append(serialize_doc(ticket_doc))
        
        return {
            "created": len(created_tickets),
            "skipped": skipped,
            "tickets": created_tickets
        }
    
    except Exception as e:
        logger.info(f"[GMAIL] Error syncing emails: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to sync emails: {str(e)}")

@app.get("/api/settings/email")
async def get_email_settings(current_user: dict = Depends(get_current_user)):
    """Get email integration settings"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    watch_doc = gmail_tokens_collection.find_one({"type": "gmail_watch"})
    return {
        "gmail_connected": token_doc is not None and "access_token" in token_doc,
        "watch_email": GMAIL_WATCH_EMAIL,
        "configured": bool(GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET),
        "watch_active": watch_doc is not None and watch_doc.get("expiration", 0) > datetime.now(timezone.utc).timestamp() * 1000,
        "mock_mode": EMAIL_MOCK_MODE,
        "sync_query": GMAIL_SYNC_QUERY
    }

@app.put("/api/settings/email")
async def update_email_settings(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Update email settings (admin only for now)"""
    # In production, this would update env vars or a config collection
    # For now, just return success as the email is set via env var
    return {"message": "Email settings updated"}

# ==================== Email Reply (with Mock Mode) ====================

# Collection for storing email replies
email_replies_collection = db.email_replies

class EmailReplyRequest(BaseModel):
    ticket_id: str
    to_email: str
    subject: str
    body: str
    
@app.post("/api/tickets/{ticket_id}/reply")
async def reply_to_ticket(
    ticket_id: str,
    reply: EmailReplyRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Reply to a ticket via email.
    In mock mode, stores the reply but doesn't actually send.
    """
    # Get the ticket
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Create reply record
    reply_id = f"reply_{uuid.uuid4().hex[:12]}"
    reply_doc = {
        "reply_id": reply_id,
        "ticket_id": ticket_id,
        "to_email": reply.to_email,
        "subject": reply.subject,
        "body": reply.body,
        "sent_by": current_user["user_id"],
        "sent_by_email": current_user.get("email"),
        "sent_by_name": current_user.get("name"),
        "created_at": datetime.now(timezone.utc),
        "mock_mode": EMAIL_MOCK_MODE,
        "actually_sent": False
    }
    
    if EMAIL_MOCK_MODE:
        # Mock mode - just store the reply
        logger.info(f"[EMAIL MOCK] Would send email to {reply.to_email}: {reply.subject}")
        reply_doc["status"] = "mocked"
        email_replies_collection.insert_one(reply_doc)
        
        # Update ticket status to "waiting" (waiting on customer)
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {
                "$set": {
                    "status": "waiting",
                    "updated_at": datetime.now(timezone.utc),
                    "last_reply_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return {
            "status": "mocked",
            "message": "Reply saved (mock mode - email not actually sent)",
            "reply_id": reply_id
        }
    else:
        # Real mode - send via Gmail API
        token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
        if not token_doc or "access_token" not in token_doc:
            raise HTTPException(status_code=400, detail="Gmail not connected")
        
        try:
            service = get_gmail_service(token_doc)
            
            # Build the email
            from email.mime.text import MIMEText
            message = MIMEText(reply.body)
            message['to'] = reply.to_email
            message['subject'] = reply.subject
            
            # If replying to a thread, add references
            if ticket.get('email_thread_id'):
                message['In-Reply-To'] = ticket.get('email_message_id', '')
                message['References'] = ticket.get('email_message_id', '')
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            send_result = service.users().messages().send(
                userId='me',
                body={'raw': raw_message, 'threadId': ticket.get('email_thread_id')}
            ).execute()
            
            reply_doc["status"] = "sent"
            reply_doc["actually_sent"] = True
            reply_doc["gmail_message_id"] = send_result.get('id')
            email_replies_collection.insert_one(reply_doc)
            
            # Update ticket status
            tickets_collection.update_one(
                {"ticket_id": ticket_id},
                {
                    "$set": {
                        "status": "waiting",
                        "updated_at": datetime.now(timezone.utc),
                        "last_reply_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            return {
                "status": "sent",
                "message": "Email sent successfully",
                "reply_id": reply_id,
                "gmail_message_id": send_result.get('id')
            }
            
        except Exception as e:
            logger.error(f"[EMAIL] Error sending: {str(e)}")
            reply_doc["status"] = "failed"
            reply_doc["error"] = str(e)
            email_replies_collection.insert_one(reply_doc)
            raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@app.get("/api/tickets/{ticket_id}/replies")
async def get_ticket_replies(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all replies for a ticket"""
    replies = list(email_replies_collection.find(
        {"ticket_id": ticket_id},
        sort=[("created_at", ASCENDING)]
    ))
    return {"replies": [serialize_doc(r) for r in replies]}

# ==================== Email Simulator (For Testing) ====================

class SimulatedEmail(BaseModel):
    from_email: str
    from_name: Optional[str] = None
    to_email: str = "support@emergent.sh"
    subject: str
    body: str
    
@app.post("/api/email/simulate")
async def simulate_incoming_email(
    email: SimulatedEmail,
    current_user: dict = Depends(get_current_user)
):
    """
    Simulate an incoming email for testing purposes.
    Creates a ticket as if the email came through Gmail.
    """
    # Generate IDs
    message_id = f"sim_{uuid.uuid4().hex[:16]}"
    thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    ticket_id = generate_ticket_id()
    
    # Get next order
    max_order_ticket = tickets_collection.find_one(
        {"status": "todo"},
        sort=[("order", DESCENDING)]
    )
    next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
    
    # Create ticket from simulated email
    ticket_doc = {
        "ticket_id": ticket_id,
        "title": email.subject or "No Subject",
        "description": email.body,
        "status": "todo",
        "priority": "medium",
        "order": next_order,
        "created_by": "email_simulator",
        "assignee_id": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        # Email metadata
        "source": "email",
        "email_message_id": message_id,
        "email_thread_id": thread_id,
        "email_from": f"{email.from_name} <{email.from_email}>" if email.from_name else email.from_email,
        "email_sender": email.from_email,
        "email_to": email.to_email,
        "email_date": datetime.now(timezone.utc).isoformat(),
        "simulated": True
    }
    
    tickets_collection.insert_one(ticket_doc)
    logger.info(f"[EMAIL SIM] Created ticket {ticket_id} from simulated email")
    
    return {
        "status": "created",
        "ticket_id": ticket_id,
        "message": "Simulated email converted to ticket",
        "ticket": serialize_doc(ticket_doc)
    }

@app.post("/api/email/webhook")
async def inbound_email_webhook(request: Request):
    """
    Generic inbound email webhook.
    Accepts POST data from email forwarding services (Mailgun, SendGrid, etc.)
    Can also be used for manual testing.
    """
    try:
        # Try to parse as JSON first
        try:
            data = await request.json()
        except Exception:
            # Fall back to form data (common for email webhooks)
            form = await request.form()
            data = dict(form)
        
        logger.info(f"[EMAIL WEBHOOK] Received: {data}")
        
        # Extract email fields (handles multiple formats)
        from_email = data.get('from') or data.get('sender') or data.get('from_email', 'unknown@example.com')
        to_email = data.get('to') or data.get('recipient') or data.get('to_email', 'support@emergent.sh')
        subject = data.get('subject', 'No Subject')
        body = data.get('body') or data.get('text') or data.get('body-plain') or data.get('stripped-text', '')
        
        # Parse from_email if it contains name
        if '<' in str(from_email):
            import re
            match = re.match(r'([^<]*)<([^>]+)>', str(from_email))
            if match:
                from_name = match.group(1).strip()
                from_email = match.group(2).strip()
            else:
                from_name = None
        else:
            from_name = data.get('from_name')
        
        # Generate IDs
        message_id = data.get('Message-Id') or data.get('message_id') or f"webhook_{uuid.uuid4().hex[:16]}"
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
        ticket_id = generate_ticket_id()
        
        # Check for duplicate
        existing = tickets_collection.find_one({"email_message_id": message_id})
        if existing:
            return {"status": "duplicate", "ticket_id": existing.get("ticket_id")}
        
        # Get next order
        max_order_ticket = tickets_collection.find_one(
            {"status": "todo"},
            sort=[("order", DESCENDING)]
        )
        next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
        
        # Create ticket
        ticket_doc = {
            "ticket_id": ticket_id,
            "title": subject,
            "description": body,
            "status": "todo",
            "priority": "medium",
            "order": next_order,
            "created_by": "email_webhook",
            "assignee_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "source": "email",
            "email_message_id": message_id,
            "email_thread_id": thread_id,
            "email_from": f"{from_name} <{from_email}>" if from_name else from_email,
            "email_sender": from_email,
            "email_to": to_email,
            "email_date": data.get('date') or datetime.now(timezone.utc).isoformat(),
            "webhook_source": True
        }
        
        tickets_collection.insert_one(ticket_doc)
        logger.info(f"[EMAIL WEBHOOK] Created ticket {ticket_id}")
        
        return {"status": "created", "ticket_id": ticket_id}
        
    except Exception as e:
        logger.info(f"[EMAIL WEBHOOK] Error: {str(e)}")
        return {"status": "error", "message": str(e)}

# ==================== Gmail Push Notifications (Webhooks) ====================

@app.post("/api/gmail/webhook")
async def gmail_webhook(request: Request):
    """
    Receive Gmail push notifications via Google Cloud Pub/Sub.
    This endpoint is called by Google when new emails arrive.
    """
    try:
        body = await request.json()
        logger.info(f"[GMAIL WEBHOOK] Received notification: {body}")
        
        # Decode the Pub/Sub message
        if 'message' in body:
            import base64
            message_data = body['message'].get('data', '')
            if message_data:
                decoded = base64.urlsafe_b64decode(message_data).decode('utf-8')
                notification = json.loads(decoded)
                logger.info(f"[GMAIL WEBHOOK] Decoded notification: {notification}")
                
                # Get the history ID to fetch new messages
                history_id = notification.get('historyId')
                email_address = notification.get('emailAddress')
                
                if history_id:
                    # Trigger background sync
                    await process_gmail_notification(history_id, email_address)
        
        # Always return 200 to acknowledge receipt
        return {"status": "ok"}
    
    except Exception as e:
        logger.info(f"[GMAIL WEBHOOK] Error processing notification: {str(e)}")
        # Still return 200 to prevent retries
        return {"status": "error", "message": str(e)}

async def process_gmail_notification(history_id: str, email_address: str):
    """Process a Gmail push notification by fetching new messages"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        logger.warning("[GMAIL WEBHOOK] No Gmail tokens found")
        return
    
    try:
        service = get_gmail_service(token_doc)
        
        # Get the stored history ID
        watch_doc = gmail_tokens_collection.find_one({"type": "gmail_watch"})
        stored_history_id = watch_doc.get("history_id") if watch_doc else None
        
        if stored_history_id:
            # Get history since last check
            history = service.users().history().list(
                userId='me',
                startHistoryId=stored_history_id,
                historyTypes=['messageAdded']
            ).execute()
            
            messages_added = []
            for record in history.get('history', []):
                for msg in record.get('messagesAdded', []):
                    messages_added.append(msg['message']['id'])
            
            logger.info(f"[GMAIL WEBHOOK] Found {len(messages_added)} new messages")
            
            # Create tickets for new messages
            for msg_id in messages_added:
                existing = tickets_collection.find_one({"email_message_id": msg_id})
                if existing:
                    continue
                
                msg_detail = service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='full'
                ).execute()
                
                # Only process inbox messages
                if 'INBOX' not in msg_detail.get('labelIds', []):
                    continue
                
                metadata = extract_email_metadata(msg_detail.get('payload', {}).get('headers', []))
                body = parse_email_body(msg_detail.get('payload', {}))
                _, sender_email = parseaddr(metadata['from'])
                
                ticket_id = generate_ticket_id()
                max_order_ticket = tickets_collection.find_one(
                    {"status": "todo"},
                    sort=[("order", DESCENDING)]
                )
                next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
                
                ticket_doc = {
                    "ticket_id": ticket_id,
                    "title": metadata['subject'] or "No Subject",
                    "description": body,
                    "status": "todo",
                    "priority": "medium",
                    "order": next_order,
                    "created_by": "system",
                    "assignee_id": None,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "source": "email",
                    "email_message_id": msg_id,
                    "email_thread_id": msg_detail.get('threadId'),
                    "email_from": metadata['from'],
                    "email_sender": sender_email,
                    "email_date": metadata['date']
                }
                
                tickets_collection.insert_one(ticket_doc)
                logger.info(f"[GMAIL WEBHOOK] Created ticket {ticket_id} from email {msg_id}")
        
        # Update stored history ID
        gmail_tokens_collection.update_one(
            {"type": "gmail_watch"},
            {"$set": {"history_id": history_id}},
            upsert=True
        )
        
    except Exception as e:
        logger.info(f"[GMAIL WEBHOOK] Error processing: {str(e)}")

@app.post("/api/gmail/watch/start")
async def start_gmail_watch(current_user: dict = Depends(get_current_user)):
    """
    Start watching Gmail inbox for new messages.
    Requires Cloud Pub/Sub topic to be configured.
    """
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    # Get Pub/Sub topic from env
    pubsub_topic = os.environ.get("GMAIL_PUBSUB_TOPIC", "")
    if not pubsub_topic:
        raise HTTPException(
            status_code=400, 
            detail="GMAIL_PUBSUB_TOPIC not configured. Please set up Cloud Pub/Sub first."
        )
    
    try:
        service = get_gmail_service(token_doc)
        
        # Start watching
        watch_response = service.users().watch(
            userId='me',
            body={
                'topicName': pubsub_topic,
                'labelIds': ['INBOX']
            }
        ).execute()
        
        logger.info(f"[GMAIL] Watch started: {watch_response}")
        
        # Store watch info
        gmail_tokens_collection.update_one(
            {"type": "gmail_watch"},
            {
                "$set": {
                    "history_id": watch_response.get('historyId'),
                    "expiration": watch_response.get('expiration'),
                    "started_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        return {
            "status": "watching",
            "history_id": watch_response.get('historyId'),
            "expiration": watch_response.get('expiration')
        }
    
    except Exception as e:
        logger.info(f"[GMAIL] Error starting watch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start watch: {str(e)}")

@app.post("/api/gmail/watch/stop")
async def stop_gmail_watch(current_user: dict = Depends(get_current_user)):
    """Stop watching Gmail inbox"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    try:
        service = get_gmail_service(token_doc)
        service.users().stop(userId='me').execute()
        
        gmail_tokens_collection.delete_one({"type": "gmail_watch"})
        
        return {"status": "stopped"}
    
    except Exception as e:
        logger.info(f"[GMAIL] Error stopping watch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop watch: {str(e)}")

# ==================== Admin Panel Endpoints ====================

class CustomFieldCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    field_type: str = Field(..., description="text, number, select, date, boolean")
    entity_type: str = Field(..., description="ticket or user")
    options: Optional[List[str]] = None  # For select type
    required: bool = False
    description: Optional[str] = None

class CustomFieldUpdate(BaseModel):
    name: Optional[str] = None
    options: Optional[List[str]] = None
    required: Optional[bool] = None
    description: Optional[str] = None

@app.get("/api/admin/custom-fields")
async def get_custom_fields(
    entity_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all custom fields, optionally filtered by entity type"""
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    
    fields = list(custom_fields_collection.find(query).sort("created_at", DESCENDING))
    return [serialize_doc(f) for f in fields]

@app.post("/api/admin/custom-fields")
async def create_custom_field(
    field_data: CustomFieldCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new custom field"""
    # Validate field type
    valid_types = ["text", "number", "select", "date", "boolean"]
    if field_data.field_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid field type. Must be one of: {valid_types}")
    
    # Validate entity type
    if field_data.entity_type not in ["ticket", "user"]:
        raise HTTPException(status_code=400, detail="Entity type must be 'ticket' or 'user'")
    
    # Check for duplicate name
    existing = custom_fields_collection.find_one({
        "name": field_data.name,
        "entity_type": field_data.entity_type
    })
    if existing:
        raise HTTPException(status_code=400, detail="A field with this name already exists")
    
    field_id = f"field_{uuid.uuid4().hex[:12]}"
    field_doc = {
        "field_id": field_id,
        "name": field_data.name,
        "field_type": field_data.field_type,
        "entity_type": field_data.entity_type,
        "options": field_data.options or [],
        "required": field_data.required,
        "description": field_data.description,
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user.get("user_id")
    }
    
    custom_fields_collection.insert_one(field_doc)
    return serialize_doc(field_doc)

@app.put("/api/admin/custom-fields/{field_id}")
async def update_custom_field(
    field_id: str,
    field_data: CustomFieldUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a custom field"""
    field = custom_fields_collection.find_one({"field_id": field_id})
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    update_data = {k: v for k, v in field_data.dict().items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        custom_fields_collection.update_one(
            {"field_id": field_id},
            {"$set": update_data}
        )
    
    updated = custom_fields_collection.find_one({"field_id": field_id})
    return serialize_doc(updated)

@app.delete("/api/admin/custom-fields/{field_id}")
async def delete_custom_field(
    field_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a custom field"""
    result = custom_fields_collection.delete_one({"field_id": field_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Field not found")
    return {"message": "Field deleted"}

@app.get("/api/admin/settings")
async def get_admin_settings(current_user: dict = Depends(get_current_user)):
    """Get all admin settings"""
    settings = admin_settings_collection.find_one({"type": "global"})
    if not settings:
        # Return defaults
        return {
            "company_name": "TickFlow",
            "support_email": "",
            "auto_assignment": True,
            "auto_reassign_reopened": False,
            "default_priority": "medium",
            "ticket_statuses": ["todo", "in_progress", "waiting", "review", "resolved"],
            "ticket_priorities": ["low", "medium", "high", "urgent"]
        }
    # Ensure new settings have defaults
    result = serialize_doc(settings)
    if "auto_reassign_reopened" not in result:
        result["auto_reassign_reopened"] = False
    return result

@app.put("/api/admin/settings")
async def update_admin_settings(
    settings: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update admin settings"""
    settings["type"] = "global"
    settings["updated_at"] = datetime.now(timezone.utc)
    settings["updated_by"] = current_user.get("user_id")
    
    admin_settings_collection.update_one(
        {"type": "global"},
        {"$set": settings},
        upsert=True
    )
    
    updated_settings = admin_settings_collection.find_one({"type": "global"}, {"_id": 0})
    return serialize_doc(updated_settings) if updated_settings else settings

# ==================== Routing Rules Endpoints ====================

@app.get("/api/admin/routing-rules")
async def get_routing_rules(current_user: dict = Depends(get_current_user)):
    """Get all routing rules"""
    rules = list(routing_rules_collection.find({}, {"_id": 0}).sort("priority", -1))
    return [serialize_doc(r) for r in rules]

@app.post("/api/admin/routing-rules")
async def create_routing_rule(
    rule_data: RoutingRuleCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new routing rule"""
    rule_id = f"rule_{uuid.uuid4().hex[:12]}"
    
    rule_doc = {
        "rule_id": rule_id,
        "name": rule_data.name,
        "description": rule_data.description,
        "conditions": rule_data.conditions,
        "actions": rule_data.actions,
        "priority": rule_data.priority,
        "is_active": rule_data.is_active,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    routing_rules_collection.insert_one(rule_doc)
    return serialize_doc(rule_doc)

@app.put("/api/admin/routing-rules/{rule_id}")
async def update_routing_rule(
    rule_id: str,
    rule_data: RoutingRuleUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a routing rule"""
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if rule_data.name is not None:
        update_data["name"] = rule_data.name
    if rule_data.description is not None:
        update_data["description"] = rule_data.description
    if rule_data.conditions is not None:
        update_data["conditions"] = rule_data.conditions
    if rule_data.actions is not None:
        update_data["actions"] = rule_data.actions
    if rule_data.priority is not None:
        update_data["priority"] = rule_data.priority
    if rule_data.is_active is not None:
        update_data["is_active"] = rule_data.is_active
    
    result = routing_rules_collection.update_one(
        {"rule_id": rule_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = routing_rules_collection.find_one({"rule_id": rule_id}, {"_id": 0})
    return serialize_doc(rule)

@app.delete("/api/admin/routing-rules/{rule_id}")
async def delete_routing_rule(
    rule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a routing rule"""
    result = routing_rules_collection.delete_one({"rule_id": rule_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"message": "Rule deleted successfully"}

@app.post("/api/admin/routing-rules/test")
async def test_routing_rule(
    ticket_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Test routing rules against a sample ticket (dry run - no changes)"""
    rules = list(routing_rules_collection.find(
        {"is_active": True}, 
        {"_id": 0}
    ).sort("priority", -1))
    
    matched_rules = []
    for rule in rules:
        conditions = rule.get("conditions", [])
        all_match = True
        condition_results = []
        
        for condition in conditions:
            result = evaluate_condition(ticket_data, condition)
            condition_results.append({
                "condition": condition,
                "matched": result
            })
            if not result:
                all_match = False
        
        if all_match:
            matched_rules.append({
                "rule_id": rule.get("rule_id"),
                "rule_name": rule.get("name"),
                "priority": rule.get("priority"),
                "actions": rule.get("actions"),
                "condition_results": condition_results
            })
    
    return {
        "ticket_data": ticket_data,
        "matched_rules": matched_rules,
        "would_apply": matched_rules[0] if matched_rules else None
    }

@app.post("/api/tickets/{ticket_id}/route")
async def route_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger routing rules for a ticket"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    result = run_routing_rules(ticket)
    
    # Get updated ticket
    updated_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    
    return {
        "ticket": serialize_doc(updated_ticket),
        "routing_result": result
    }

# ==================== Conversation History Endpoints ====================

@app.get("/api/tickets/by-email/{email}")
async def get_tickets_by_email(
    email: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all tickets from a specific email address"""
    # Normalize email
    email_lower = email.lower().strip()
    
    # Find tickets with matching customer_email
    tickets = list(tickets_collection.find({
        "$or": [
            {"customer_email": {"$regex": f"^{re.escape(email_lower)}$", "$options": "i"}},
            {"email_sender": {"$regex": f"^{re.escape(email_lower)}$", "$options": "i"}},
            {"email_from": {"$regex": re.escape(email_lower), "$options": "i"}}
        ]
    }).sort("created_at", DESCENDING))
    
    return [serialize_doc(t) for t in tickets]

@app.get("/api/tickets/{ticket_id}/related")
async def get_related_tickets(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get tickets from the same customer as this ticket"""
    # Find the ticket
    ticket = tickets_collection.find_one({
        "$or": [
            {"id": ticket_id},
            {"ticket_id": ticket_id}
        ]
    })
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get customer email
    customer_email = ticket.get("customer_email") or ticket.get("email_sender")
    if not customer_email:
        return []
    
    # Find other tickets from same customer
    related = list(tickets_collection.find({
        "$and": [
            {"$or": [
                {"customer_email": {"$regex": f"^{re.escape(customer_email)}$", "$options": "i"}},
                {"email_sender": {"$regex": f"^{re.escape(customer_email)}$", "$options": "i"}}
            ]},
            {"id": {"$ne": ticket.get("id")}},
            {"ticket_id": {"$ne": ticket.get("ticket_id")}}
        ]
    }).sort("created_at", DESCENDING).limit(20))
    
    return [serialize_doc(t) for t in related]


# ==================== SLA Management ====================

sla_policies_collection = db.sla_policies

class SLAPolicy(BaseModel):
    name: str
    description: Optional[str] = None
    priority: str  # urgent, high, medium, low, or "all"
    first_response_hours: float  # Target hours for first response
    resolution_hours: float  # Target hours for resolution
    business_hours_only: bool = True
    is_active: bool = True

@app.get("/api/sla-policies")
async def get_sla_policies(current_user: dict = Depends(get_current_user)):
    """Get all SLA policies"""
    policies = list(sla_policies_collection.find({}, {"_id": 0}))
    return policies

@app.post("/api/sla-policies")
async def create_sla_policy(
    policy: SLAPolicy,
    current_user: dict = Depends(get_current_user)
):
    """Create a new SLA policy"""
    policy_id = f"sla_{uuid.uuid4().hex[:8]}"
    policy_doc = {
        "policy_id": policy_id,
        **policy.dict(),
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user.get("user_id")
    }
    sla_policies_collection.insert_one(policy_doc)
    return {"policy_id": policy_id, **policy.dict()}

@app.put("/api/sla-policies/{policy_id}")
async def update_sla_policy(
    policy_id: str,
    policy: SLAPolicy,
    current_user: dict = Depends(get_current_user)
):
    """Update an SLA policy"""
    result = sla_policies_collection.update_one(
        {"policy_id": policy_id},
        {"$set": {**policy.dict(), "updated_at": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"policy_id": policy_id, **policy.dict()}

@app.delete("/api/sla-policies/{policy_id}")
async def delete_sla_policy(
    policy_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an SLA policy"""
    result = sla_policies_collection.delete_one({"policy_id": policy_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"message": "Policy deleted"}

@app.get("/api/sla/ticket/{ticket_id}")
async def get_ticket_sla_status(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get SLA status for a specific ticket"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Find applicable SLA policy
    priority = ticket.get("priority", "medium")
    policy = sla_policies_collection.find_one(
        {"$or": [{"priority": priority}, {"priority": "all"}], "is_active": True},
        {"_id": 0}
    )
    
    if not policy:
        return {"ticket_id": ticket_id, "sla_policy": None, "status": "no_policy"}
    
    created_at = ticket.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    
    now = datetime.now(timezone.utc)
    hours_elapsed = (now - created_at).total_seconds() / 3600
    
    # Check first response
    first_response_at = ticket.get("first_response_at")
    first_response_status = "pending"
    first_response_hours = None
    
    if first_response_at:
        if isinstance(first_response_at, str):
            first_response_at = datetime.fromisoformat(first_response_at.replace("Z", "+00:00"))
        first_response_hours = (first_response_at - created_at).total_seconds() / 3600
        first_response_status = "met" if first_response_hours <= policy["first_response_hours"] else "breached"
    elif hours_elapsed > policy["first_response_hours"]:
        first_response_status = "breached"
    elif hours_elapsed > policy["first_response_hours"] * 0.75:
        first_response_status = "at_risk"
    
    # Check resolution
    resolved_at = ticket.get("resolved_at")
    resolution_status = "pending"
    resolution_hours = None
    
    if resolved_at:
        if isinstance(resolved_at, str):
            resolved_at = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
        resolution_hours = (resolved_at - created_at).total_seconds() / 3600
        resolution_status = "met" if resolution_hours <= policy["resolution_hours"] else "breached"
    elif ticket.get("status") not in ["resolved", "closed"]:
        if hours_elapsed > policy["resolution_hours"]:
            resolution_status = "breached"
        elif hours_elapsed > policy["resolution_hours"] * 0.75:
            resolution_status = "at_risk"
    
    return {
        "ticket_id": ticket_id,
        "sla_policy": policy,
        "first_response": {
            "target_hours": policy["first_response_hours"],
            "actual_hours": round(first_response_hours, 2) if first_response_hours else None,
            "status": first_response_status,
            "hours_remaining": max(0, policy["first_response_hours"] - hours_elapsed) if first_response_status == "pending" else None
        },
        "resolution": {
            "target_hours": policy["resolution_hours"],
            "actual_hours": round(resolution_hours, 2) if resolution_hours else None,
            "status": resolution_status,
            "hours_remaining": max(0, policy["resolution_hours"] - hours_elapsed) if resolution_status == "pending" else None
        },
        "hours_elapsed": round(hours_elapsed, 2)
    }


# ==================== Analytics API ====================

@app.get("/api/analytics/overview")
async def get_analytics_overview(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get overview analytics for the dashboard"""
    from_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    def parse_date(date_val):
        """Safely parse date and make it timezone-aware"""
        if date_val is None:
            return None
        if isinstance(date_val, datetime):
            if date_val.tzinfo is None:
                return date_val.replace(tzinfo=timezone.utc)
            return date_val
        try:
            dt = datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            return None
    
    # Get all tickets in range
    all_tickets = list(tickets_collection.find({}, {"_id": 0}))
    recent_tickets = []
    for t in all_tickets:
        created = parse_date(t.get("created_at"))
        if created and created >= from_date:
            recent_tickets.append(t)
    
    # Basic counts
    total_tickets = len(all_tickets)
    tickets_in_period = len(recent_tickets)
    open_tickets = len([t for t in all_tickets if t.get("status") not in ["resolved", "closed"]])
    resolved_in_period = len([t for t in recent_tickets if t.get("status") in ["resolved", "closed"]])
    
    # Priority breakdown
    priority_counts = {"urgent": 0, "high": 0, "medium": 0, "low": 0}
    for t in all_tickets:
        if t.get("status") not in ["resolved", "closed"]:
            p = t.get("priority", "medium")
            if p in priority_counts:
                priority_counts[p] += 1
    
    # Status breakdown
    status_counts = {"todo": 0, "in_progress": 0, "waiting": 0, "review": 0, "resolved": 0}
    for t in all_tickets:
        s = t.get("status", "todo")
        if s in status_counts:
            status_counts[s] += 1
    
    # Volume by day (last N days)
    volume_by_day = {}
    for t in recent_tickets:
        created = parse_date(t.get("created_at"))
        if created:
            date = created.strftime("%Y-%m-%d")
            volume_by_day[date] = volume_by_day.get(date, 0) + 1
    
    # Sort by date
    volume_trend = [{"date": k, "count": v} for k, v in sorted(volume_by_day.items())]
    
    # Average resolution time
    resolution_times = []
    for t in recent_tickets:
        created = parse_date(t.get("created_at"))
        resolved = parse_date(t.get("resolved_at"))
        if created and resolved:
            resolution_times.append((resolved - created).total_seconds() / 3600)
    
    avg_resolution_hours = sum(resolution_times) / len(resolution_times) if resolution_times else None
    
    # SLA compliance (simplified)
    sla_met = 0
    sla_breached = 0
    for t in recent_tickets:
        created = parse_date(t.get("created_at"))
        resolved = parse_date(t.get("resolved_at"))
        if created and resolved:
            hours = (resolved - created).total_seconds() / 3600
            # Default SLA: 24 hours for resolution
            if hours <= 24:
                sla_met += 1
            else:
                sla_breached += 1
    
    sla_compliance = (sla_met / (sla_met + sla_breached) * 100) if (sla_met + sla_breached) > 0 else None
    
    # Top assignees
    assignee_counts = {}
    for t in recent_tickets:
        assignee = t.get("assignee_id")
        if assignee:
            assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
    
    # Get user names
    top_assignees = []
    for user_id, count in sorted(assignee_counts.items(), key=lambda x: -x[1])[:5]:
        user = users_collection.find_one({"user_id": user_id}, {"_id": 0, "name": 1})
        top_assignees.append({
            "user_id": user_id,
            "name": user.get("name") if user else "Unknown",
            "ticket_count": count
        })
    
    return {
        "period_days": days,
        "summary": {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "tickets_in_period": tickets_in_period,
            "resolved_in_period": resolved_in_period,
            "avg_resolution_hours": round(avg_resolution_hours, 1) if avg_resolution_hours else None,
            "sla_compliance_percent": round(sla_compliance, 1) if sla_compliance else None
        },
        "priority_breakdown": priority_counts,
        "status_breakdown": status_counts,
        "volume_trend": volume_trend,
        "top_assignees": top_assignees
    }

@app.get("/api/analytics/agents")
async def get_agent_analytics(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get per-agent performance analytics"""
    from_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get all tickets in range
    recent_tickets = list(tickets_collection.find({
        "created_at": {"$gte": from_date}
    }, {"_id": 0}))
    
    # Get all users
    users = {u["user_id"]: u for u in users_collection.find({}, {"_id": 0})}
    
    # Calculate per-agent stats
    agent_stats = {}
    for t in recent_tickets:
        assignee = t.get("assignee_id")
        if not assignee:
            continue
        
        if assignee not in agent_stats:
            user = users.get(assignee, {})
            agent_stats[assignee] = {
                "user_id": assignee,
                "name": user.get("name", "Unknown"),
                "email": user.get("email"),
                "tickets_assigned": 0,
                "tickets_resolved": 0,
                "resolution_times": [],
                "priorities": {"urgent": 0, "high": 0, "medium": 0, "low": 0}
            }
        
        agent_stats[assignee]["tickets_assigned"] += 1
        
        p = t.get("priority", "medium")
        if p in agent_stats[assignee]["priorities"]:
            agent_stats[assignee]["priorities"][p] += 1
        
        if t.get("status") in ["resolved", "closed"]:
            agent_stats[assignee]["tickets_resolved"] += 1
            
            if t.get("resolved_at") and t.get("created_at"):
                try:
                    created = datetime.fromisoformat(str(t["created_at"]).replace("Z", "+00:00"))
                    resolved = datetime.fromisoformat(str(t["resolved_at"]).replace("Z", "+00:00"))
                    agent_stats[assignee]["resolution_times"].append(
                        (resolved - created).total_seconds() / 3600
                    )
                except (ValueError, TypeError, KeyError):
                    pass
    
    # Calculate averages
    result = []
    for agent in agent_stats.values():
        avg_resolution = sum(agent["resolution_times"]) / len(agent["resolution_times"]) if agent["resolution_times"] else None
        result.append({
            "user_id": agent["user_id"],
            "name": agent["name"],
            "email": agent["email"],
            "tickets_assigned": agent["tickets_assigned"],
            "tickets_resolved": agent["tickets_resolved"],
            "resolution_rate": round(agent["tickets_resolved"] / agent["tickets_assigned"] * 100, 1) if agent["tickets_assigned"] > 0 else 0,
            "avg_resolution_hours": round(avg_resolution, 1) if avg_resolution else None,
            "priority_breakdown": agent["priorities"]
        })
    
    # Sort by tickets resolved
    result.sort(key=lambda x: -x["tickets_resolved"])
    
    return result


# ==================== Reply Templates ====================

templates_collection = db.reply_templates

class ReplyTemplate(BaseModel):
    name: str
    category: Optional[str] = "general"
    content: str
    shortcut: Optional[str] = None  # e.g., "/thanks" to quick insert

@app.get("/api/templates")
async def get_templates(
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all reply templates"""
    query = {}
    if category:
        query["category"] = category
    templates = list(templates_collection.find(query, {"_id": 0}))
    return templates

@app.post("/api/templates")
async def create_template(
    template: ReplyTemplate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new reply template"""
    template_id = f"tmpl_{uuid.uuid4().hex[:8]}"
    template_doc = {
        "template_id": template_id,
        **template.dict(),
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user.get("user_id")
    }
    templates_collection.insert_one(template_doc)
    return {"template_id": template_id, **template.dict()}

@app.put("/api/templates/{template_id}")
async def update_template(
    template_id: str,
    template: ReplyTemplate,
    current_user: dict = Depends(get_current_user)
):
    """Update a reply template"""
    result = templates_collection.update_one(
        {"template_id": template_id},
        {"$set": {**template.dict(), "updated_at": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"template_id": template_id, **template.dict()}

@app.delete("/api/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a reply template"""
    result = templates_collection.delete_one({"template_id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted"}


# ==================== Bulk Operations ====================

class BulkUpdateRequest(BaseModel):
    ticket_ids: List[str]
    updates: dict  # Fields to update: status, priority, assignee_id, tags, etc.

@app.post("/api/tickets/bulk-update")
async def bulk_update_tickets(
    request: BulkUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Bulk update multiple tickets at once"""
    if not request.ticket_ids:
        raise HTTPException(status_code=400, detail="No ticket IDs provided")
    
    if len(request.ticket_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tickets per bulk operation")
    
    # Validate updates
    allowed_fields = {"status", "priority", "assignee_id", "team_id", "escalation_level"}
    update_fields = {k: v for k, v in request.updates.items() if k in allowed_fields}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid update fields provided")
    
    update_fields["updated_at"] = datetime.now(timezone.utc)
    
    # Perform bulk update
    result = tickets_collection.update_many(
        {"ticket_id": {"$in": request.ticket_ids}},
        {"$set": update_fields}
    )
    
    # Log to changelog for each ticket
    for ticket_id in request.ticket_ids:
        for field, new_value in update_fields.items():
            if field != "updated_at":
                ticket_changelog_collection.insert_one({
                    "changelog_id": f"cl_{uuid.uuid4().hex[:12]}",
                    "ticket_id": ticket_id,
                    "field": field,
                    "old_value": None,  # Unknown in bulk operation
                    "new_value": new_value,
                    "changed_by": current_user.get("user_id"),
                    "changed_by_name": current_user.get("name"),
                    "timestamp": datetime.now(timezone.utc),
                    "bulk_operation": True
                })
    
    return {
        "message": f"Updated {result.modified_count} tickets",
        "matched": result.matched_count,
        "modified": result.modified_count
    }

class BulkTagRequest(BaseModel):
    ticket_ids: List[str]
    tags_to_add: List[str] = []
    tags_to_remove: List[str] = []

@app.post("/api/tickets/bulk-tag")
async def bulk_tag_tickets(
    request: BulkTagRequest,
    current_user: dict = Depends(get_current_user)
):
    """Bulk add or remove tags from multiple tickets"""
    if not request.ticket_ids:
        raise HTTPException(status_code=400, detail="No ticket IDs provided")
    
    if len(request.ticket_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tickets per bulk operation")
    
    modified_count = 0
    
    for ticket_id in request.ticket_ids:
        update_ops = {}
        
        if request.tags_to_add:
            update_ops["$addToSet"] = {"tags": {"$each": request.tags_to_add}}
        
        if request.tags_to_remove:
            update_ops["$pull"] = {"tags": {"$in": request.tags_to_remove}}
        
        if update_ops:
            # MongoDB doesn't allow $addToSet and $pull in same operation
            if request.tags_to_add:
                tickets_collection.update_one(
                    {"ticket_id": ticket_id},
                    {"$addToSet": {"tags": {"$each": request.tags_to_add}}}
                )
            if request.tags_to_remove:
                tickets_collection.update_one(
                    {"ticket_id": ticket_id},
                    {"$pull": {"tags": {"$in": request.tags_to_remove}}}
                )
            modified_count += 1
    
    return {
        "message": f"Updated tags for {modified_count} tickets",
        "tags_added": request.tags_to_add,
        "tags_removed": request.tags_to_remove
    }

@app.post("/api/tickets/bulk-close")
async def bulk_close_tickets(
    ticket_ids: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Bulk close multiple tickets"""
    if not ticket_ids:
        raise HTTPException(status_code=400, detail="No ticket IDs provided")
    
    if len(ticket_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tickets per bulk operation")
    
    now = datetime.now(timezone.utc)
    result = tickets_collection.update_many(
        {"ticket_id": {"$in": ticket_ids}},
        {"$set": {
            "status": "resolved",
            "resolved_at": now,
            "updated_at": now
        }}
    )
    
    return {
        "message": f"Closed {result.modified_count} tickets",
        "modified": result.modified_count
    }


# ==================== Customer Management System ====================

class CustomerCreate(BaseModel):
    name: str
    primary_email: EmailStr
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    priority_level: Optional[str] = "standard"
    net_payments: Optional[float] = 0.0
    assigned_agents: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    notes: Optional[str] = ""
    custom_fields: Optional[Dict[str, Any]] = {}

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    priority_level: Optional[str] = None
    net_payments: Optional[float] = None
    assigned_agents: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

class LinkEmailRequest(BaseModel):
    email: EmailStr

class MergeCustomersRequest(BaseModel):
    source_customer_id: str  # Will be merged into target
    target_customer_id: str  # Will keep this customer

@app.get("/api/customers")
async def list_customers(
    search: Optional[str] = None,
    customer_type: Optional[str] = None,
    priority_level: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """List all customers with filtering and stats"""
    query = {}
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"primary_email": {"$regex": search, "$options": "i"}},
            {"linked_emails": {"$regex": search, "$options": "i"}},
            {"company_name": {"$regex": search, "$options": "i"}},
            {"customer_id": {"$regex": search, "$options": "i"}}
        ]
    
    if customer_type:
        query["customer_type"] = customer_type
    
    if priority_level:
        query["priority_level"] = priority_level
    
    if assigned_agent:
        query["assigned_agents"] = assigned_agent
    
    customers = list(customers_collection.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit))
    total = customers_collection.count_documents(query)
    
    # Add stats for each customer
    result = []
    for customer in customers:
        customer_emails = [customer["primary_email"]] + customer.get("linked_emails", [])
        
        # Get ticket stats
        ticket_stats = tickets_collection.aggregate([
            {"$match": {"customer_email": {"$in": customer_emails}}},
            {"$group": {
                "_id": None,
                "total_tickets": {"$sum": 1},
                "open_tickets": {"$sum": {"$cond": [{"$in": ["$status", ["todo", "in_progress", "waiting", "review"]]}, 1, 0]}},
                "resolved_tickets": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}}
            }}
        ])
        stats = list(ticket_stats)
        
        # Get CSAT average
        csat_stats = csat_responses_collection.aggregate([
            {"$match": {"customer_email": {"$in": customer_emails}, "rating": {"$ne": None}}},
            {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
        ])
        csat = list(csat_stats)
        
        customer_data = serialize_doc(customer)
        customer_data["stats"] = {
            "total_tickets": stats[0]["total_tickets"] if stats else 0,
            "open_tickets": stats[0]["open_tickets"] if stats else 0,
            "resolved_tickets": stats[0]["resolved_tickets"] if stats else 0,
            "avg_csat": round(csat[0]["avg_rating"], 1) if csat else None,
            "csat_count": csat[0]["count"] if csat else 0
        }
        result.append(customer_data)
    
    return {
        "customers": result,
        "total": total,
        "limit": limit,
        "skip": skip
    }

@app.get("/api/customers/b2b-prospects")
async def list_b2b_prospects(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """List B2B prospects (business domain customers) sorted by potential value"""
    pipeline = [
        {"$match": {"customer_type": "b2b"}},
        {"$lookup": {
            "from": "tickets",
            "let": {"emails": {"$concatArrays": [["$primary_email"], {"$ifNull": ["$linked_emails", []]}]}},
            "pipeline": [
                {"$match": {"$expr": {"$in": ["$customer_email", "$$emails"]}}}
            ],
            "as": "tickets"
        }},
        {"$addFields": {
            "ticket_count": {"$size": "$tickets"},
            "engagement_score": {"$add": [
                {"$multiply": [{"$size": "$tickets"}, 10]},
                {"$ifNull": ["$net_payments", 0]}
            ]}
        }},
        {"$sort": {"engagement_score": -1}},
        {"$limit": limit},
        {"$project": {"tickets": 0}}
    ]
    
    prospects = list(customers_collection.aggregate(pipeline))
    return [serialize_doc(p) for p in prospects]

@app.get("/api/customers/{customer_id}")
async def get_customer(
    customer_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get customer details with full stats"""
    customer = customers_collection.find_one({"customer_id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer_emails = [customer["primary_email"]] + customer.get("linked_emails", [])
    
    # Get detailed ticket stats
    ticket_pipeline = [
        {"$match": {"customer_email": {"$in": customer_emails}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    status_counts = {s["_id"]: s["count"] for s in tickets_collection.aggregate(ticket_pipeline)}
    
    # Get recent tickets
    recent_tickets = list(tickets_collection.find(
        {"customer_email": {"$in": customer_emails}},
        {"_id": 0, "ticket_id": 1, "title": 1, "status": 1, "priority": 1, "created_at": 1, "customer_email": 1}
    ).sort("created_at", -1).limit(10))
    
    # Get CSAT history
    csat_history = list(csat_responses_collection.find(
        {"customer_email": {"$in": customer_emails}},
        {"_id": 0}
    ).sort("created_at", -1).limit(10))
    
    # Get assigned agent details
    assigned_agents_details = []
    if customer.get("assigned_agents"):
        agents = list(users_collection.find(
            {"user_id": {"$in": customer["assigned_agents"]}},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1, "picture": 1}
        ))
        assigned_agents_details = agents
    
    result = serialize_doc(customer)
    result["stats"] = {
        "by_status": status_counts,
        "total_tickets": sum(status_counts.values()),
        "open_tickets": sum(status_counts.get(s, 0) for s in ["todo", "in_progress", "waiting", "review"]),
        "resolved_tickets": sum(status_counts.get(s, 0) for s in ["resolved", "closed"])
    }
    result["recent_tickets"] = [serialize_doc(t) for t in recent_tickets]
    result["csat_history"] = [serialize_doc(c) for c in csat_history]
    result["assigned_agents_details"] = assigned_agents_details
    
    return result

@app.post("/api/customers")
async def create_customer(
    customer_data: CustomerCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new customer"""
    email_lower = customer_data.primary_email.lower().strip()
    
    # Check if customer already exists
    existing = customers_collection.find_one({
        "$or": [
            {"primary_email": email_lower},
            {"linked_emails": email_lower}
        ]
    })
    if existing:
        raise HTTPException(status_code=400, detail="Customer with this email already exists")
    
    domain = extract_domain(email_lower)
    is_b2c = is_b2c_email(email_lower)
    
    new_customer = {
        "customer_id": generate_customer_id(),
        "name": customer_data.name,
        "primary_email": email_lower,
        "linked_emails": [],
        "company_name": customer_data.company_name or (detect_company_from_domain(domain) if not is_b2c else None),
        "company_domain": customer_data.company_domain or (domain if not is_b2c else None),
        "customer_type": "b2b" if (customer_data.company_domain or not is_b2c) else "b2c",
        "priority_level": customer_data.priority_level,
        "net_payments": customer_data.net_payments,
        "assigned_agents": customer_data.assigned_agents or [],
        "tags": customer_data.tags or [],
        "notes": customer_data.notes or "",
        "custom_fields": customer_data.custom_fields or {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    customers_collection.insert_one(new_customer)
    logger.info(f"Created customer {new_customer['customer_id']} by {current_user['user_id']}")
    
    return serialize_doc(new_customer)

@app.put("/api/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    customer_data: CustomerUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update customer details"""
    customer = customers_collection.find_one({"customer_id": customer_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    update_data = {k: v for k, v in customer_data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    # If company_domain is set and was B2C, upgrade to B2B
    if "company_domain" in update_data and update_data["company_domain"]:
        update_data["customer_type"] = "b2b"
    
    customers_collection.update_one(
        {"customer_id": customer_id},
        {"$set": update_data}
    )
    
    updated = customers_collection.find_one({"customer_id": customer_id}, {"_id": 0})
    return serialize_doc(updated)

@app.post("/api/customers/{customer_id}/link-email")
async def link_email_to_customer(
    customer_id: str,
    request: LinkEmailRequest,
    current_user: dict = Depends(get_current_user)
):
    """Link an additional email address to a customer"""
    customer = customers_collection.find_one({"customer_id": customer_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    email_lower = request.email.lower().strip()
    
    # Check if email is already linked to another customer
    existing = customers_collection.find_one({
        "customer_id": {"$ne": customer_id},
        "$or": [
            {"primary_email": email_lower},
            {"linked_emails": email_lower}
        ]
    })
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Email already belongs to customer {existing['customer_id']}. Use merge instead."
        )
    
    # Check if already linked
    if email_lower == customer["primary_email"] or email_lower in customer.get("linked_emails", []):
        raise HTTPException(status_code=400, detail="Email already linked to this customer")
    
    customers_collection.update_one(
        {"customer_id": customer_id},
        {
            "$addToSet": {"linked_emails": email_lower},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    
    logger.info(f"Linked email {email_lower} to customer {customer_id}")
    
    updated = customers_collection.find_one({"customer_id": customer_id}, {"_id": 0})
    return serialize_doc(updated)

@app.delete("/api/customers/{customer_id}/unlink-email/{email}")
async def unlink_email_from_customer(
    customer_id: str,
    email: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a linked email from a customer"""
    customer = customers_collection.find_one({"customer_id": customer_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    email_lower = email.lower().strip()
    
    if email_lower == customer["primary_email"]:
        raise HTTPException(status_code=400, detail="Cannot unlink primary email")
    
    customers_collection.update_one(
        {"customer_id": customer_id},
        {
            "$pull": {"linked_emails": email_lower},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    
    updated = customers_collection.find_one({"customer_id": customer_id}, {"_id": 0})
    return serialize_doc(updated)

@app.post("/api/customers/merge")
async def merge_customers(
    request: MergeCustomersRequest,
    current_user: dict = Depends(get_current_user)
):
    """Merge source customer into target customer"""
    source = customers_collection.find_one({"customer_id": request.source_customer_id})
    target = customers_collection.find_one({"customer_id": request.target_customer_id})
    
    if not source:
        raise HTTPException(status_code=404, detail="Source customer not found")
    if not target:
        raise HTTPException(status_code=404, detail="Target customer not found")
    
    # Collect all emails from source
    source_emails = [source["primary_email"]] + source.get("linked_emails", [])
    
    # Add to target's linked emails (excluding duplicates)
    existing_emails = set([target["primary_email"]] + target.get("linked_emails", []))
    new_emails = [e for e in source_emails if e not in existing_emails]
    
    # Merge other fields
    merged_tags = list(set(target.get("tags", []) + source.get("tags", [])))
    merged_agents = list(set(target.get("assigned_agents", []) + source.get("assigned_agents", [])))
    merged_notes = target.get("notes", "")
    if source.get("notes"):
        merged_notes += f"\n\n--- Merged from {source['customer_id']} ---\n{source['notes']}"
    
    # Combine net_payments
    merged_payments = (target.get("net_payments", 0) or 0) + (source.get("net_payments", 0) or 0)
    
    # Merge custom fields (target takes precedence)
    merged_custom = {**source.get("custom_fields", {}), **target.get("custom_fields", {})}
    
    # Update target
    customers_collection.update_one(
        {"customer_id": request.target_customer_id},
        {
            "$addToSet": {"linked_emails": {"$each": new_emails}},
            "$set": {
                "tags": merged_tags,
                "assigned_agents": merged_agents,
                "notes": merged_notes,
                "net_payments": merged_payments,
                "custom_fields": merged_custom,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    # Delete source customer
    customers_collection.delete_one({"customer_id": request.source_customer_id})
    
    logger.info(f"Merged customer {request.source_customer_id} into {request.target_customer_id}")
    
    updated = customers_collection.find_one({"customer_id": request.target_customer_id}, {"_id": 0})
    return {
        "message": "Customers merged successfully",
        "customer": serialize_doc(updated),
        "emails_added": new_emails
    }

@app.get("/api/customers/{customer_id}/tickets")
async def get_customer_tickets(
    customer_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get all tickets for a customer (across all linked emails)"""
    customer = customers_collection.find_one({"customer_id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer_emails = [customer["primary_email"]] + customer.get("linked_emails", [])
    
    query = {"customer_email": {"$in": customer_emails}}
    if status:
        query["status"] = status
    
    tickets = list(tickets_collection.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit))
    total = tickets_collection.count_documents(query)
    
    return {
        "tickets": [serialize_doc(t) for t in tickets],
        "total": total,
        "customer_emails": customer_emails
    }

@app.post("/api/tickets/{ticket_id}/merge-consecutive")
async def merge_consecutive_tickets(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Merge consecutive tickets from the same customer into this ticket.
    Useful for when customer sends multiple emails that should be one conversation.
    """
    target_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not target_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    customer_email = target_ticket.get("customer_email")
    if not customer_email:
        raise HTTPException(status_code=400, detail="Ticket has no customer email")
    
    # Get customer to find all their emails
    customer = customers_collection.find_one({
        "$or": [
            {"primary_email": customer_email.lower()},
            {"linked_emails": customer_email.lower()}
        ]
    })
    
    customer_emails = [customer_email.lower()]
    if customer:
        customer_emails = [customer["primary_email"]] + customer.get("linked_emails", [])
    
    # Find consecutive tickets from same customer within 24 hours
    target_created = target_ticket.get("created_at")
    if isinstance(target_created, str):
        target_created = datetime.fromisoformat(target_created.replace("Z", "+00:00"))
    
    time_window_start = target_created - timedelta(hours=24)
    time_window_end = target_created + timedelta(hours=24)
    
    consecutive_tickets = list(tickets_collection.find({
        "ticket_id": {"$ne": ticket_id},
        "customer_email": {"$in": customer_emails},
        "created_at": {"$gte": time_window_start, "$lte": time_window_end},
        "status": {"$nin": ["resolved", "closed"]}
    }).sort("created_at", 1))
    
    if not consecutive_tickets:
        return {"message": "No consecutive tickets found to merge", "merged_count": 0}
    
    merged_content = []
    merged_ticket_ids = []
    
    for ticket in consecutive_tickets:
        # Add ticket content to merged content
        merged_content.append({
            "from_ticket": ticket["ticket_id"],
            "title": ticket.get("title"),
            "content": ticket.get("content"),
            "created_at": ticket.get("created_at")
        })
        merged_ticket_ids.append(ticket["ticket_id"])
        
        # Mark source ticket as merged
        tickets_collection.update_one(
            {"ticket_id": ticket["ticket_id"]},
            {
                "$set": {
                    "status": "closed",
                    "merged_into": ticket_id,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
    
    # Add merged content as a note on target ticket
    if merged_content:
        note_content = "### Merged consecutive emails:\n\n"
        for item in merged_content:
            note_content += f"**From {item['from_ticket']}**: {item['title']}\n"
            note_content += f"{item['content']}\n\n---\n\n"
        
        messages_collection.insert_one({
            "message_id": f"msg_{uuid.uuid4().hex[:12]}",
            "ticket_id": ticket_id,
            "type": "note",
            "content": note_content,
            "author_id": "system",
            "author_name": "System",
            "is_internal": True,
            "created_at": datetime.now(timezone.utc)
        })
    
    return {
        "message": f"Merged {len(merged_ticket_ids)} consecutive tickets",
        "merged_count": len(merged_ticket_ids),
        "merged_tickets": merged_ticket_ids
    }


# ==================== CSAT (Customer Satisfaction) System ====================

class CSATRequest(BaseModel):
    ticket_id: str
    customer_email: str
    customer_name: Optional[str] = None

class CSATFeedbackRequest(BaseModel):
    feedback: Optional[str] = None
    was_resolved: Optional[bool] = None

# Generate secure token for CSAT email links
def generate_csat_token(ticket_id: str, customer_email: str) -> str:
    """Generate a secure, unique token for CSAT rating links"""
    random_part = secrets.token_urlsafe(32)
    return f"csat_{hashlib.sha256(f'{ticket_id}:{customer_email}:{random_part}'.encode()).hexdigest()[:24]}"

@app.post("/api/csat/send/{ticket_id}")
async def send_csat_survey(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate CSAT survey for a resolved ticket (email is MOCKED)"""
    # Get ticket
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    customer_email = ticket.get("customer_email")
    if not customer_email:
        raise HTTPException(status_code=400, detail="Ticket has no customer email")
    
    # Check if CSAT already sent
    existing = csat_tokens_collection.find_one({"ticket_id": ticket_id})
    if existing:
        return {
            "message": "CSAT survey already sent for this ticket",
            "token": existing.get("token"),
            "sent_at": existing.get("created_at"),
            "already_sent": True
        }
    
    # Generate token
    token = generate_csat_token(ticket_id, customer_email)
    
    # Store token
    token_doc = {
        "token": token,
        "ticket_id": ticket_id,
        "customer_email": customer_email,
        "customer_name": ticket.get("customer_name") or customer_email.split("@")[0],
        "ticket_title": ticket.get("title"),
        "resolved_by": ticket.get("assignee_id"),
        "resolved_by_name": None,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "used": False,
        "used_at": None
    }
    
    # Get resolver name
    if ticket.get("assignee_id"):
        resolver = users_collection.find_one({"user_id": ticket["assignee_id"]}, {"_id": 0, "name": 1})
        if resolver:
            token_doc["resolved_by_name"] = resolver.get("name")
    
    csat_tokens_collection.insert_one(token_doc)
    
    # Generate email content (MOCKED - not actually sent)
    base_url = "https://favorite-tickets.preview.emergentagent.com"
    
    email_content = {
        "to": customer_email,
        "subject": f"How was your experience? - {ticket.get('title', 'Your support request')}",
        "html": f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rate Your Experience</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        <tr>
            <td style="padding: 40px 30px; text-align: center; background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%);">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">✅ Your ticket has been resolved</h1>
            </td>
        </tr>
        <tr>
            <td style="padding: 30px;">
                <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 20px;">
                    Hi {token_doc['customer_name']},
                </p>
                <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 20px;">
                    Your support request has been resolved:
                </p>
                <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                    <p style="color: #6b7280; font-size: 14px; margin: 0 0 5px;">Ticket #{ticket_id}</p>
                    <p style="color: #111827; font-size: 18px; font-weight: 600; margin: 0;">{ticket.get('title', 'Support Request')}</p>
                    {f'<p style="color: #6b7280; font-size: 14px; margin: 10px 0 0;">Resolved by: {token_doc["resolved_by_name"]}</p>' if token_doc.get("resolved_by_name") else ''}
                </div>
                <div style="text-align: center; margin: 30px 0;">
                    <p style="color: #374151; font-size: 18px; font-weight: 600; margin: 0 0 20px;">How was your experience?</p>
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td style="text-align: center;">
                                <a href="{base_url}/csat/{token}?rating=1" style="display: inline-block; text-decoration: none; margin: 0 8px;">
                                    <span style="font-size: 36px;">⭐</span>
                                    <br><span style="color: #6b7280; font-size: 12px;">Terrible</span>
                                </a>
                                <a href="{base_url}/csat/{token}?rating=2" style="display: inline-block; text-decoration: none; margin: 0 8px;">
                                    <span style="font-size: 36px;">⭐⭐</span>
                                    <br><span style="color: #6b7280; font-size: 12px;">Poor</span>
                                </a>
                                <a href="{base_url}/csat/{token}?rating=3" style="display: inline-block; text-decoration: none; margin: 0 8px;">
                                    <span style="font-size: 36px;">⭐⭐⭐</span>
                                    <br><span style="color: #6b7280; font-size: 12px;">Okay</span>
                                </a>
                                <a href="{base_url}/csat/{token}?rating=4" style="display: inline-block; text-decoration: none; margin: 0 8px;">
                                    <span style="font-size: 36px;">⭐⭐⭐⭐</span>
                                    <br><span style="color: #6b7280; font-size: 12px;">Good</span>
                                </a>
                                <a href="{base_url}/csat/{token}?rating=5" style="display: inline-block; text-decoration: none; margin: 0 8px;">
                                    <span style="font-size: 36px;">⭐⭐⭐⭐⭐</span>
                                    <br><span style="color: #6b7280; font-size: 12px;">Excellent</span>
                                </a>
                            </td>
                        </tr>
                    </table>
                    <p style="color: #9ca3af; font-size: 14px; margin: 20px 0 0;">Click a star rating - takes just 1 second!</p>
                </div>
            </td>
        </tr>
        <tr>
            <td style="padding: 20px 30px; background-color: #f9fafb; text-align: center;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                    This survey expires in 7 days. Your feedback helps us improve.
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
        """,
        "text": f"""
Your ticket has been resolved!

Hi {token_doc['customer_name']},

Your support request has been resolved:
Ticket #{ticket_id}: {ticket.get('title', 'Support Request')}
{f"Resolved by: {token_doc['resolved_by_name']}" if token_doc.get("resolved_by_name") else ""}

How was your experience? Click a rating:

⭐ Terrible: {base_url}/csat/{token}?rating=1
⭐⭐ Poor: {base_url}/csat/{token}?rating=2  
⭐⭐⭐ Okay: {base_url}/csat/{token}?rating=3
⭐⭐⭐⭐ Good: {base_url}/csat/{token}?rating=4
⭐⭐⭐⭐⭐ Excellent: {base_url}/csat/{token}?rating=5

This survey expires in 7 days.
        """
    }
    
    # LOG THE EMAIL (MOCKED - NOT ACTUALLY SENT)
    logger.info(f"[MOCKED EMAIL] CSAT survey for ticket {ticket_id} to {customer_email}")
    logger.info(f"[MOCKED EMAIL] Rating links generated with token: {token}")
    
    return {
        "message": "CSAT survey generated (email MOCKED - not actually sent)",
        "token": token,
        "rating_url_template": f"{base_url}/csat/{token}?rating={{rating}}",
        "expires_at": token_doc["expires_at"],
        "email_preview": email_content,
        "mocked": True
    }


@app.get("/api/csat/rate")
async def submit_csat_rating(
    token: str,
    rating: int
):
    """Handle CSAT rating from email link (no auth required)"""
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Find token
    token_doc = csat_tokens_collection.find_one({"token": token})
    if not token_doc:
        raise HTTPException(status_code=404, detail="Invalid or expired survey link")
    
    # Check expiration
    expires_at = token_doc.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=400, detail="This survey link has expired")
    
    # Check if already responded
    existing_response = csat_responses_collection.find_one({"token": token})
    if existing_response:
        return {
            "message": "You have already submitted a rating for this ticket",
            "rating": existing_response.get("rating"),
            "already_submitted": True,
            "ticket_id": token_doc.get("ticket_id")
        }
    
    # Create CSAT response
    response_id = f"csat_{uuid.uuid4().hex[:12]}"
    csat_doc = {
        "response_id": response_id,
        "token": token,
        "ticket_id": token_doc.get("ticket_id"),
        "customer_email": token_doc.get("customer_email"),
        "customer_name": token_doc.get("customer_name"),
        "rating": rating,
        "feedback": None,
        "was_resolved": None,
        "resolved_by": token_doc.get("resolved_by"),
        "resolved_by_name": token_doc.get("resolved_by_name"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    csat_responses_collection.insert_one(csat_doc)
    
    # Mark token as used
    csat_tokens_collection.update_one(
        {"token": token},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}}
    )
    
    # Update ticket with CSAT score
    tickets_collection.update_one(
        {"ticket_id": token_doc.get("ticket_id")},
        {"$set": {
            "csat_score": rating,
            "csat_response_id": response_id,
            "csat_submitted_at": datetime.now(timezone.utc)
        }}
    )
    
    # If low rating (≤2), create alert notification for manager
    if rating <= 2:
        alert_doc = {
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "type": "low_csat_alert",
            "ticket_id": token_doc.get("ticket_id"),
            "customer_email": token_doc.get("customer_email"),
            "rating": rating,
            "resolved_by": token_doc.get("resolved_by"),
            "resolved_by_name": token_doc.get("resolved_by_name"),
            "created_at": datetime.now(timezone.utc),
            "read": False,
            "message": f"Low CSAT rating ({rating}/5) received for ticket {token_doc.get('ticket_id')} from {token_doc.get('customer_email')}"
        }
        # Store in a notifications collection (or could be sent via WebSocket)
        db.notifications.insert_one(alert_doc)
        logger.warning(f"[LOW CSAT ALERT] Rating {rating}/5 for ticket {token_doc.get('ticket_id')} - Manager notified")
    
    return {
        "message": "Thank you for your feedback!",
        "response_id": response_id,
        "rating": rating,
        "ticket_id": token_doc.get("ticket_id"),
        "can_add_feedback": True
    }


@app.post("/api/csat/{response_id}/feedback")
async def add_csat_feedback(
    response_id: str,
    request: CSATFeedbackRequest
):
    """Add optional feedback to CSAT response (no auth required)"""
    # Find response
    response = csat_responses_collection.find_one({"response_id": response_id})
    if not response:
        raise HTTPException(status_code=404, detail="CSAT response not found")
    
    # Update with feedback
    update_fields = {"updated_at": datetime.now(timezone.utc)}
    if request.feedback:
        update_fields["feedback"] = request.feedback
    if request.was_resolved is not None:
        update_fields["was_resolved"] = request.was_resolved
    
    csat_responses_collection.update_one(
        {"response_id": response_id},
        {"$set": update_fields}
    )
    
    # Also update ticket if feedback provided
    if request.feedback:
        tickets_collection.update_one(
            {"ticket_id": response.get("ticket_id")},
            {"$set": {"csat_feedback": request.feedback}}
        )
    
    return {
        "message": "Feedback submitted successfully",
        "response_id": response_id
    }


@app.get("/api/csat/ticket/{ticket_id}")
async def get_ticket_csat(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get CSAT data for a specific ticket"""
    # Check for response
    response = csat_responses_collection.find_one(
        {"ticket_id": ticket_id},
        {"_id": 0}
    )
    
    # Check for pending token
    token = csat_tokens_collection.find_one(
        {"ticket_id": ticket_id},
        {"_id": 0, "token": 0}  # Don't expose token
    )
    
    if response:
        return {
            "has_response": True,
            "rating": response.get("rating"),
            "feedback": response.get("feedback"),
            "was_resolved": response.get("was_resolved"),
            "submitted_at": response.get("created_at"),
            "customer_name": response.get("customer_name")
        }
    elif token:
        return {
            "has_response": False,
            "survey_sent": True,
            "sent_at": token.get("created_at"),
            "expires_at": token.get("expires_at"),
            "used": token.get("used", False)
        }
    else:
        return {
            "has_response": False,
            "survey_sent": False
        }


@app.get("/api/csat/analytics")
async def get_csat_analytics(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get CSAT analytics and metrics"""
    from_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get all responses in period
    responses = list(csat_responses_collection.find(
        {"created_at": {"$gte": from_date}},
        {"_id": 0}
    ))
    
    if not responses:
        return {
            "period_days": days,
            "total_responses": 0,
            "average_rating": None,
            "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "satisfaction_rate": None,
            "low_ratings": [],
            "by_agent": []
        }
    
    # Calculate metrics
    total = len(responses)
    ratings = [r.get("rating", 0) for r in responses]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Rating distribution
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings:
        if r in distribution:
            distribution[r] += 1
    
    # Satisfaction rate (4 or 5 stars)
    satisfied = len([r for r in ratings if r >= 4])
    satisfaction_rate = (satisfied / total * 100) if total > 0 else 0
    
    # Low ratings (≤2) with details
    low_ratings = [
        {
            "ticket_id": r.get("ticket_id"),
            "rating": r.get("rating"),
            "feedback": r.get("feedback"),
            "customer_email": r.get("customer_email"),
            "resolved_by_name": r.get("resolved_by_name"),
            "created_at": r.get("created_at")
        }
        for r in responses if r.get("rating", 5) <= 2
    ]
    
    # By agent
    agent_ratings = {}
    for r in responses:
        agent_id = r.get("resolved_by")
        if agent_id:
            if agent_id not in agent_ratings:
                agent_ratings[agent_id] = {
                    "user_id": agent_id,
                    "name": r.get("resolved_by_name", "Unknown"),
                    "ratings": [],
                    "count": 0
                }
            agent_ratings[agent_id]["ratings"].append(r.get("rating", 0))
            agent_ratings[agent_id]["count"] += 1
    
    by_agent = []
    for agent in agent_ratings.values():
        avg = sum(agent["ratings"]) / len(agent["ratings"]) if agent["ratings"] else 0
        by_agent.append({
            "user_id": agent["user_id"],
            "name": agent["name"],
            "response_count": agent["count"],
            "average_rating": round(avg, 2)
        })
    
    by_agent.sort(key=lambda x: -x["average_rating"])
    
    return {
        "period_days": days,
        "total_responses": total,
        "average_rating": round(avg_rating, 2),
        "rating_distribution": distribution,
        "satisfaction_rate": round(satisfaction_rate, 1),
        "low_ratings": low_ratings[:10],
        "by_agent": by_agent
    }


@app.get("/api/notifications")
async def get_notifications(
    current_user: dict = Depends(get_current_user)
):
    """Get notifications (including low CSAT alerts)"""
    notifications = list(db.notifications.find(
        {},
        {"_id": 0}
    ).sort("created_at", -1).limit(50))
    
    return notifications


@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark notification as read"""
    db.notifications.update_one(
        {"notification_id": notification_id},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc)}}
    )
    return {"message": "Notification marked as read"}


# ==================== Search API ====================

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit_per_category: int = Field(default=10, ge=1, le=50)
    type_filter: Optional[str] = None

@app.get("/api/search")
async def search(
    q: str,
    limit: int = 10,
    type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Comprehensive search across ALL entities.
    
    Supports operators:
    - status:open, status:closed
    - priority:urgent, priority:high
    - assigned:me, assigned:none, assigned:@username
    - team:teamname
    - tag:tagname
    - created:today, created:last-week, created:2024-01-15
    - customer:email@domain.com
    - domain:acme.com
    - escalation:L1, escalation:L2
    - type:ticket, type:user, type:team
    
    Example: /api/search?q=billing status:open priority:urgent
    """
    if not q or len(q) < 1:
        return {"results": [], "total": 0, "by_category": {}, "operators": {}, "tickets": []}
    
    results = search_engine.search_all(
        q, 
        limit_per_category=limit,
        current_user_id=current_user.get("user_id"),
        type_filter=type
    )
    # Add top-level tickets for backward compatibility with merge/link modals
    results["tickets"] = results.get("by_category", {}).get("tickets", [])
    return results

@app.get("/api/search/suggestions")
async def search_suggestions(
    q: str,
    current_user: dict = Depends(get_current_user)
):
    """Get autocomplete suggestions for search"""
    if not q:
        return {"suggestions": []}
    
    suggestions = search_engine.get_search_suggestions(q)
    return {"suggestions": suggestions}

@app.post("/api/search")
async def search_post(
    search_query: SearchQuery,
    current_user: dict = Depends(get_current_user)
):
    """Search with POST (for complex queries)"""
    results = search_engine.search_all(
        search_query.query, 
        limit_per_category=search_query.limit_per_category,
        current_user_id=current_user.get("user_id"),
        type_filter=search_query.type_filter
    )
    return results


# ==================== Real-time Presence API ====================

@app.get("/api/presence/stats")
async def get_presence_statistics(
    current_user: dict = Depends(get_current_user)
):
    """Get real-time presence statistics"""
    return get_presence_stats()

@app.get("/api/presence/ticket/{ticket_id}")
async def get_ticket_viewers(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get users currently viewing a specific ticket"""
    viewers = get_users_viewing_ticket(ticket_id)
    return {
        "ticket_id": ticket_id,
        "viewers": viewers,
        "count": len(viewers)
    }


# ==================== Health Check ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": {
            "realtime": True,
            "search": True,
            "leave_management": True
        }
    }


# ==================== Leave Management API ====================

leave_manager = get_leave_manager(db)

@app.post("/api/leaves")
async def create_leave(
    leave_data: LeaveRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Create a new leave entry (auto-approved)"""
    # Allow creating leave for self or others (minimal friction)
    if not leave_data.user_id:
        leave_data.user_id = current_user.get("user_id")
    
    leave = await leave_manager.create_leave(leave_data)
    
    # Broadcast to connected clients
    background_tasks.add_task(
        broadcast_leave_created,
        leave,
        {"user_id": current_user.get("user_id"), "name": current_user.get("name")}
    )
    
    return leave

@app.get("/api/leaves")
async def get_leaves(
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    leave_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get leaves with optional filters"""
    leaves = await leave_manager.get_leaves(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        leave_type=leave_type
    )
    return leaves

@app.get("/api/leaves/types")
async def get_leave_types(
    current_user: dict = Depends(get_current_user)
):
    """Get all available leave types"""
    types = await leave_manager.get_leave_types()
    return {"types": types}

@app.get("/api/leaves/calendar/{year}/{month}")
async def get_team_calendar(
    year: int,
    month: int,
    current_user: dict = Depends(get_current_user)
):
    """Get team calendar for a month"""
    calendar = await leave_manager.get_team_calendar(year, month)
    return {"year": year, "month": month, "days": calendar}

@app.get("/api/leaves/conflicts")
async def check_leave_conflicts(
    start_date: str,
    end_date: str,
    exclude_user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Check for leave conflicts on given dates"""
    conflicts = await leave_manager.check_conflicts(start_date, end_date, exclude_user_id)
    return conflicts

@app.get("/api/leaves/summary/{user_id}")
async def get_user_leave_summary(
    user_id: str,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get leave summary for a user"""
    summary = await leave_manager.get_user_leave_summary(user_id, year)
    return summary

@app.get("/api/leaves/{leave_id}")
async def get_leave(
    leave_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific leave entry"""
    leave = await leave_manager.get_leave(leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    return leave

@app.put("/api/leaves/{leave_id}")
async def update_leave(
    leave_id: str,
    update_data: LeaveUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Update a leave entry (admin can edit/deny)"""
    leave = await leave_manager.update_leave(leave_id, update_data)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    
    # Broadcast update
    background_tasks.add_task(
        broadcast_leave_updated,
        leave_id,
        leave,
        {"user_id": current_user.get("user_id"), "name": current_user.get("name")}
    )
    
    return leave

@app.delete("/api/leaves/{leave_id}")
async def delete_leave(
    leave_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Delete a leave entry"""
    deleted = await leave_manager.delete_leave(leave_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Leave not found")
    
    # Broadcast deletion
    background_tasks.add_task(
        broadcast_leave_deleted,
        leave_id,
        {"user_id": current_user.get("user_id"), "name": current_user.get("name")}
    )
    
    return {"message": "Leave deleted successfully"}


# ==================== Ticket Merge/Link/Split APIs ====================

@app.post("/api/tickets/{ticket_id}/merge")
async def merge_tickets(
    ticket_id: str,
    merge_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Merge this ticket into another ticket"""
    target_ticket_id = merge_data.get("target_ticket_id")
    if not target_ticket_id:
        raise HTTPException(status_code=400, detail="Target ticket ID required")
    
    # Get both tickets
    source_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    target_ticket = tickets_collection.find_one({"ticket_id": target_ticket_id}, {"_id": 0})
    
    if not source_ticket:
        raise HTTPException(status_code=404, detail="Source ticket not found")
    if not target_ticket:
        raise HTTPException(status_code=404, detail="Target ticket not found")
    
    # Move all messages from source to target
    messages_collection.update_many(
        {"ticket_id": ticket_id},
        {"$set": {"ticket_id": target_ticket_id, "merged_from": ticket_id}}
    )
    
    # Add a system note about the merge
    merge_note = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": target_ticket_id,
        "type": "system",
        "text": f"Merged from ticket {ticket_id}: {source_ticket.get('title')}",
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc)
    }
    messages_collection.insert_one(merge_note)
    
    # Mark source ticket as merged (soft delete)
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {
            "status": "merged",
            "merged_into": target_ticket_id,
            "merged_at": datetime.now(timezone.utc),
            "merged_by": current_user["user_id"]
        }}
    )
    
    # Log the change
    log_ticket_change(ticket_id, source_ticket.get("uuid", ""), "merge", None, target_ticket_id, current_user["user_id"], "merge")
    
    return {"message": f"Ticket {ticket_id} merged into {target_ticket_id}"}


@app.post("/api/tickets/{ticket_id}/link")
async def link_tickets(
    ticket_id: str,
    link_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Link this ticket to another ticket"""
    target_ticket_id = link_data.get("target_ticket_id")
    link_type = link_data.get("link_type", "related")  # related, blocks, blocked_by, duplicates
    
    if not target_ticket_id:
        raise HTTPException(status_code=400, detail="Target ticket ID required")
    
    # Get both tickets
    source_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    target_ticket = tickets_collection.find_one({"ticket_id": target_ticket_id}, {"_id": 0})
    
    if not source_ticket:
        raise HTTPException(status_code=404, detail="Source ticket not found")
    if not target_ticket:
        raise HTTPException(status_code=404, detail="Target ticket not found")
    
    # Add link to source ticket
    link_entry = {
        "ticket_id": target_ticket_id,
        "title": target_ticket.get("title"),
        "link_type": link_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$addToSet": {"linked_tickets": link_entry}}
    )
    
    # Add reverse link to target
    reverse_type = link_type
    if link_type == "blocks":
        reverse_type = "blocked_by"
    elif link_type == "blocked_by":
        reverse_type = "blocks"
    
    reverse_entry = {
        "ticket_id": ticket_id,
        "title": source_ticket.get("title"),
        "link_type": reverse_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    tickets_collection.update_one(
        {"ticket_id": target_ticket_id},
        {"$addToSet": {"linked_tickets": reverse_entry}}
    )
    
    # Return updated ticket
    updated_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    return serialize_doc(updated_ticket)


@app.delete("/api/tickets/{ticket_id}/unlink/{target_ticket_id}")
async def unlink_tickets(
    ticket_id: str,
    target_ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove link between two tickets"""
    # Remove link from source
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$pull": {"linked_tickets": {"ticket_id": target_ticket_id}}}
    )
    
    # Remove link from target
    tickets_collection.update_one(
        {"ticket_id": target_ticket_id},
        {"$pull": {"linked_tickets": {"ticket_id": ticket_id}}}
    )
    
    return {"message": "Tickets unlinked"}


@app.post("/api/tickets/{ticket_id}/split")
async def split_ticket(
    ticket_id: str,
    split_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Split a ticket at a specific message index"""
    split_at_index = split_data.get("split_at_index")
    new_ticket_title = split_data.get("new_ticket_title")
    
    if split_at_index is None:
        raise HTTPException(status_code=400, detail="Split index required")
    
    # Get original ticket
    original_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not original_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get all messages for this ticket
    messages = list(messages_collection.find({"ticket_id": ticket_id}, {"_id": 0}).sort("created_at", ASCENDING))
    
    if split_at_index <= 0 or split_at_index > len(messages):
        raise HTTPException(status_code=400, detail="Invalid split index")
    
    # Create new ticket
    new_ticket_id = generate_ticket_id()
    new_uuid = str(uuid4())
    
    new_ticket = {
        "ticket_id": new_ticket_id,
        "uuid": new_uuid,
        "title": new_ticket_title or f"Split from {ticket_id}",
        "description": f"This ticket was split from {ticket_id}",
        "status": original_ticket.get("status", "todo"),
        "assignee_id": original_ticket.get("assignee_id"),
        "priority": original_ticket.get("priority", "medium"),
        "escalation_level": original_ticket.get("escalation_level", "L1"),
        "customer_email": original_ticket.get("customer_email"),
        "domain": original_ticket.get("domain"),
        "tags": original_ticket.get("tags", []),
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "split_from": ticket_id,
        "is_starred": False,
        "snoozed": False
    }
    
    tickets_collection.insert_one(new_ticket)
    
    # Move messages after split point to new ticket
    messages_to_move = [m.get("message_id") for m in messages[split_at_index:]]
    if messages_to_move:
        messages_collection.update_many(
            {"message_id": {"$in": messages_to_move}},
            {"$set": {"ticket_id": new_ticket_id, "split_from": ticket_id}}
        )
    
    # Add system notes to both tickets
    split_note_original = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "type": "system",
        "text": f"Ticket split. {len(messages_to_move)} message(s) moved to {new_ticket_id}",
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc)
    }
    messages_collection.insert_one(split_note_original)
    
    split_note_new = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": new_ticket_id,
        "type": "system",
        "text": f"This ticket was split from {ticket_id}",
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc)
    }
    messages_collection.insert_one(split_note_new)
    
    # Log the change
    log_ticket_change(ticket_id, original_ticket.get("uuid", ""), "split", None, new_ticket_id, current_user["user_id"], "split")
    
    return {
        "message": "Ticket split successfully",
        "new_ticket_id": new_ticket_id,
        "messages_moved": len(messages_to_move)
    }


# ==================== Feature Requests APIs ====================

class FeatureRequestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    request_type: str = "feature"  # feature, bug_fix, enhancement
    priority: Optional[str] = "medium"  # low, medium, high, critical
    linked_ticket_id: Optional[str] = None

class FeatureRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    request_type: Optional[str] = None  # feature, bug_fix, enhancement
    priority: Optional[str] = None
    status: Optional[str] = None  # new, planned, in_progress, completed, archived

@app.get("/api/feature-requests")
async def get_feature_requests(
    status: Optional[str] = None,
    request_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all feature requests"""
    query = {}
    if status:
        query["status"] = status
    if request_type:
        query["request_type"] = request_type
    
    requests = list(feature_requests_collection.find(query, {"_id": 0}).sort("mentions_count", DESCENDING))
    return [serialize_doc(r) for r in requests]

@app.post("/api/feature-requests")
async def create_feature_request(
    data: FeatureRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new feature request"""
    feature_request_id = f"FR-{str(uuid4().hex[:8]).upper()}"
    
    feature_request = {
        "feature_request_id": feature_request_id,
        "title": data.title,
        "description": data.description or "",
        "request_type": data.request_type,
        "priority": data.priority or "medium",
        "status": "new",
        "mentions_count": 1 if data.linked_ticket_id else 0,
        "linked_tickets": [data.linked_ticket_id] if data.linked_ticket_id else [],
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    feature_requests_collection.insert_one(feature_request)
    
    # If linked_ticket_id provided, update the ticket to add to its feature_request_ids array
    if data.linked_ticket_id:
        tickets_collection.update_one(
            {"ticket_id": data.linked_ticket_id},
            {"$addToSet": {"feature_request_ids": feature_request_id}}
        )
    
    return serialize_doc(feature_request)

@app.get("/api/feature-requests/{feature_request_id}")
async def get_feature_request(
    feature_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific feature request with linked tickets"""
    fr = feature_requests_collection.find_one({"feature_request_id": feature_request_id}, {"_id": 0})
    if not fr:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    # Get linked tickets details
    linked_tickets = []
    if fr.get("linked_tickets"):
        tickets = list(tickets_collection.find(
            {"ticket_id": {"$in": fr["linked_tickets"]}},
            {"_id": 0, "ticket_id": 1, "title": 1, "status": 1, "customer_email": 1, "created_at": 1}
        ))
        linked_tickets = [serialize_doc(t) for t in tickets]
    
    result = serialize_doc(fr)
    result["linked_ticket_details"] = linked_tickets
    return result

@app.put("/api/feature-requests/{feature_request_id}")
async def update_feature_request(
    feature_request_id: str,
    data: FeatureRequestUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a feature request"""
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    result = feature_requests_collection.update_one(
        {"feature_request_id": feature_request_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    fr = feature_requests_collection.find_one({"feature_request_id": feature_request_id}, {"_id": 0})
    return serialize_doc(fr)

@app.post("/api/tickets/{ticket_id}/feature-request")
async def link_ticket_to_feature_request(
    ticket_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Link a ticket to a feature request (supports multiple links)"""
    feature_request_id = data.get("feature_request_id")
    if not feature_request_id:
        raise HTTPException(status_code=400, detail="Feature request ID required")
    
    # Verify ticket exists
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Verify feature request exists
    fr = feature_requests_collection.find_one({"feature_request_id": feature_request_id}, {"_id": 0})
    if not fr:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    # Check if already linked
    current_links = ticket.get("feature_request_ids", [])
    if feature_request_id in current_links:
        return {"message": "Ticket already linked to this feature request"}
    
    # Add ticket to feature request's linked_tickets
    feature_requests_collection.update_one(
        {"feature_request_id": feature_request_id},
        {
            "$addToSet": {"linked_tickets": ticket_id},
            "$inc": {"mentions_count": 1}
        }
    )
    
    # Add feature request to ticket's feature_request_ids array
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$addToSet": {"feature_request_ids": feature_request_id}}
    )
    
    return {"message": "Ticket linked to feature request"}


@app.delete("/api/tickets/{ticket_id}/feature-request/{feature_request_id}")
async def unlink_ticket_from_feature_request(
    ticket_id: str,
    feature_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unlink a ticket from a feature request"""
    # Remove ticket from feature request's linked_tickets
    feature_requests_collection.update_one(
        {"feature_request_id": feature_request_id},
        {
            "$pull": {"linked_tickets": ticket_id},
            "$inc": {"mentions_count": -1}
        }
    )
    
    # Remove feature request from ticket's feature_request_ids array
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$pull": {"feature_request_ids": feature_request_id}}
    )
    
    return {"message": "Ticket unlinked from feature request"}


@app.get("/api/tickets/{ticket_id}/feature-requests")
async def get_ticket_feature_requests(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all feature requests linked to a ticket"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    feature_request_ids = ticket.get("feature_request_ids", [])
    
    # Also check legacy single feature_request_id field
    legacy_fr_id = ticket.get("feature_request_id")
    if legacy_fr_id and legacy_fr_id not in feature_request_ids:
        feature_request_ids.append(legacy_fr_id)
    
    if not feature_request_ids:
        return []
    
    feature_requests = list(feature_requests_collection.find(
        {"feature_request_id": {"$in": feature_request_ids}},
        {"_id": 0}
    ))
    
    return [serialize_doc(fr) for fr in feature_requests]


# ==================== Data Export System ====================

from fastapi.responses import StreamingResponse

class ExportRequest(BaseModel):
    format: str = "json"  # json or csv
    include_notes: bool = True
    include_changelog: bool = True
    include_csat: bool = True
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    status_filter: Optional[List[str]] = None

def serialize_for_export(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if key == '_id':
            continue
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, list):
            result[key] = [serialize_for_export(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):
            result[key] = serialize_for_export(value)
        else:
            result[key] = value
    return result

@app.post("/api/admin/export/tickets")
async def admin_export_tickets(
    request: ExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """Export all tickets with metadata"""
    
    # Build query
    query = {}
    
    # Date filter
    if request.date_from or request.date_to:
        date_query = {}
        if request.date_from:
            try:
                from_date = datetime.fromisoformat(request.date_from.replace("Z", "+00:00"))
                date_query["$gte"] = from_date
            except ValueError:
                pass
        if request.date_to:
            try:
                to_date = datetime.fromisoformat(request.date_to.replace("Z", "+00:00"))
                date_query["$lte"] = to_date
            except ValueError:
                pass
        if date_query:
            query["created_at"] = date_query
    
    # Status filter
    if request.status_filter:
        query["status"] = {"$in": request.status_filter}
    
    # Fetch tickets
    tickets = list(tickets_collection.find(query, {"_id": 0}))
    
    # Enrich with related data
    export_data = []
    for ticket in tickets:
        ticket_export = serialize_for_export(ticket)
        ticket_id = ticket.get("ticket_id")
        
        # Add notes/replies
        if request.include_notes:
            notes = list(messages_collection.find(
                {"ticket_id": ticket_id}, {"_id": 0}
            ))
            ticket_export["notes"] = [serialize_for_export(n) for n in notes]
        
        # Add changelog
        if request.include_changelog:
            changelog = list(ticket_changelog_collection.find(
                {"ticket_id": ticket_id}, {"_id": 0}
            ).sort("timestamp", -1))
            ticket_export["changelog"] = [serialize_for_export(c) for c in changelog]
        
        # Add CSAT
        if request.include_csat:
            csat = csat_responses_collection.find_one(
                {"ticket_id": ticket_id}, {"_id": 0}
            )
            ticket_export["csat"] = serialize_for_export(csat) if csat else None
        
        export_data.append(ticket_export)
    
    # Generate export
    if request.format == "csv":
        return generate_csv_export(export_data, "tickets")
    else:
        return generate_json_export(export_data, "tickets")


@app.post("/api/admin/export/full")
async def export_full_data(
    request: ExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """Export complete system data"""
    
    export_data = {
        "export_info": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": current_user.get("email"),
            "format": request.format
        },
        "tickets": [],
        "users": [],
        "teams": [],
        "customers": [],
        "feature_requests": [],
        "sla_policies": [],
        "routing_rules": [],
        "templates": [],
        "custom_fields": [],
        "csat_responses": [],
        "leaves": []
    }
    
    # Tickets with all metadata
    tickets = list(tickets_collection.find({}, {"_id": 0}))
    for ticket in tickets:
        ticket_export = serialize_for_export(ticket)
        ticket_id = ticket.get("ticket_id")
        
        if request.include_notes:
            notes = list(messages_collection.find({"ticket_id": ticket_id}, {"_id": 0}))
            ticket_export["notes"] = [serialize_for_export(n) for n in notes]
        
        if request.include_changelog:
            changelog = list(ticket_changelog_collection.find({"ticket_id": ticket_id}, {"_id": 0}))
            ticket_export["changelog"] = [serialize_for_export(c) for c in changelog]
        
        export_data["tickets"].append(ticket_export)
    
    # Users
    users = list(users_collection.find({}, {"_id": 0, "password_hash": 0}))
    export_data["users"] = [serialize_for_export(u) for u in users]
    
    # Teams
    teams = list(teams_collection.find({}, {"_id": 0}))
    export_data["teams"] = [serialize_for_export(t) for t in teams]
    
    # Customers (aggregated from tickets)
    customers_agg = tickets_collection.aggregate([
        {"$match": {"customer_email": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": "$customer_email",
            "name": {"$first": "$customer_name"},
            "domain": {"$first": "$domain"},
            "ticket_count": {"$sum": 1},
            "first_ticket": {"$min": "$created_at"},
            "last_ticket": {"$max": "$created_at"}
        }}
    ])
    export_data["customers"] = [serialize_for_export({
        "email": c["_id"],
        "name": c.get("name"),
        "domain": c.get("domain"),
        "ticket_count": c.get("ticket_count"),
        "first_ticket": c.get("first_ticket"),
        "last_ticket": c.get("last_ticket")
    }) for c in customers_agg]
    
    # Feature Requests
    feature_requests = list(feature_requests_collection.find({}, {"_id": 0}))
    export_data["feature_requests"] = [serialize_for_export(fr) for fr in feature_requests]
    
    # SLA Policies
    sla_policies = list(sla_policies_collection.find({}, {"_id": 0}))
    export_data["sla_policies"] = [serialize_for_export(p) for p in sla_policies]
    
    # Routing Rules
    routing_rules = list(routing_rules_collection.find({}, {"_id": 0}))
    export_data["routing_rules"] = [serialize_for_export(r) for r in routing_rules]
    
    # Templates
    templates = list(templates_collection.find({}, {"_id": 0}))
    export_data["templates"] = [serialize_for_export(t) for t in templates]
    
    # Custom Fields
    custom_fields = list(custom_fields_collection.find({}, {"_id": 0}))
    export_data["custom_fields"] = [serialize_for_export(cf) for cf in custom_fields]
    
    # CSAT Responses
    if request.include_csat:
        csat_responses = list(csat_responses_collection.find({}, {"_id": 0}))
        export_data["csat_responses"] = [serialize_for_export(c) for c in csat_responses]
    
    # Leaves - directly access the collection
    leaves = list(db.leaves.find({}, {"_id": 0}))
    export_data["leaves"] = [serialize_for_export(leave) for leave in leaves]
    
    # Generate export
    if request.format == "csv":
        # For full export, CSV will be a zip of multiple CSVs
        return generate_json_export(export_data, "full_export")
    else:
        return generate_json_export(export_data, "full_export")


@app.get("/api/admin/export/customers")
async def export_customers(
    format: str = "json",
    current_user: dict = Depends(get_current_user)
):
    """Export customer data with ticket history summary"""
    
    # Aggregate customer data
    pipeline = [
        {"$match": {"customer_email": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": "$customer_email",
            "name": {"$first": "$customer_name"},
            "domain": {"$first": "$domain"},
            "ticket_count": {"$sum": 1},
            "open_tickets": {"$sum": {"$cond": [{"$nin": ["$status", ["resolved", "closed"]]}, 1, 0]}},
            "resolved_tickets": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}},
            "first_contact": {"$min": "$created_at"},
            "last_contact": {"$max": "$created_at"},
            "priorities": {"$push": "$priority"},
            "tags": {"$push": "$tags"}
        }},
        {"$sort": {"ticket_count": -1}}
    ]
    
    customers = list(tickets_collection.aggregate(pipeline))
    
    export_data = []
    for c in customers:
        # Flatten tags
        all_tags = []
        for tag_list in c.get("tags", []):
            if tag_list:
                all_tags.extend(tag_list)
        unique_tags = list(set(all_tags))
        
        # Count priorities
        priorities = c.get("priorities", [])
        priority_counts = {
            "urgent": priorities.count("urgent"),
            "high": priorities.count("high"),
            "medium": priorities.count("medium"),
            "low": priorities.count("low")
        }
        
        export_data.append(serialize_for_export({
            "email": c["_id"],
            "name": c.get("name"),
            "domain": c.get("domain"),
            "ticket_count": c.get("ticket_count", 0),
            "open_tickets": c.get("open_tickets", 0),
            "resolved_tickets": c.get("resolved_tickets", 0),
            "first_contact": c.get("first_contact"),
            "last_contact": c.get("last_contact"),
            "priority_breakdown": priority_counts,
            "tags": unique_tags
        }))
    
    if format == "csv":
        return generate_csv_export(export_data, "customers")
    else:
        return generate_json_export(export_data, "customers")


@app.get("/api/admin/export/analytics")
async def export_analytics(
    days: int = 30,
    format: str = "json",
    current_user: dict = Depends(get_current_user)
):
    """Export analytics data"""
    from_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Ticket metrics by day
    pipeline = [
        {"$match": {"created_at": {"$gte": from_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "tickets_created": {"$sum": 1},
            "resolved": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}},
            "urgent": {"$sum": {"$cond": [{"$eq": ["$priority", "urgent"]}, 1, 0]}},
            "high": {"$sum": {"$cond": [{"$eq": ["$priority", "high"]}, 1, 0]}}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    daily_metrics = list(tickets_collection.aggregate(pipeline))
    
    # Agent metrics
    agent_pipeline = [
        {"$match": {"created_at": {"$gte": from_date}, "assignee_id": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": "$assignee_id",
            "assigned": {"$sum": 1},
            "resolved": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}}
        }}
    ]
    
    agent_metrics = list(tickets_collection.aggregate(agent_pipeline))
    
    # Enrich with user names
    for agent in agent_metrics:
        user = users_collection.find_one({"user_id": agent["_id"]}, {"_id": 0, "name": 1, "email": 1})
        agent["name"] = user.get("name") if user else "Unknown"
        agent["email"] = user.get("email") if user else None
    
    # CSAT metrics
    csat_metrics = list(csat_responses_collection.aggregate([
        {"$match": {"created_at": {"$gte": from_date}}},
        {"$group": {
            "_id": None,
            "total_responses": {"$sum": 1},
            "avg_rating": {"$avg": "$rating"},
            "five_star": {"$sum": {"$cond": [{"$eq": ["$rating", 5]}, 1, 0]}},
            "four_star": {"$sum": {"$cond": [{"$eq": ["$rating", 4]}, 1, 0]}},
            "three_star": {"$sum": {"$cond": [{"$eq": ["$rating", 3]}, 1, 0]}},
            "two_star": {"$sum": {"$cond": [{"$eq": ["$rating", 2]}, 1, 0]}},
            "one_star": {"$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}}
        }}
    ]))
    
    export_data = {
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "daily_metrics": [serialize_for_export({"date": d["_id"], **d}) for d in daily_metrics],
        "agent_metrics": [serialize_for_export(a) for a in agent_metrics],
        "csat_metrics": serialize_for_export(csat_metrics[0]) if csat_metrics else None
    }
    
    if format == "csv":
        # For analytics, export daily metrics as CSV
        return generate_csv_export(export_data["daily_metrics"], "analytics_daily")
    else:
        return generate_json_export(export_data, "analytics")


def generate_json_export(data, filename_prefix):
    """Generate JSON file download response"""
    json_str = json.dumps(data, indent=2, default=str)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    
    return StreamingResponse(
        io.StringIO(json_str),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


def generate_csv_export(data, filename_prefix):
    """Generate CSV file download response"""
    if not data:
        return StreamingResponse(
            io.StringIO("No data to export"),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_prefix}_empty.csv"}
        )
    
    # Flatten nested data for CSV
    flat_data = []
    for item in data:
        flat_item = {}
        for key, value in item.items():
            if isinstance(value, (list, dict)):
                flat_item[key] = json.dumps(value)
            else:
                flat_item[key] = value
        flat_data.append(flat_item)
    
    # Get all unique keys
    all_keys = set()
    for item in flat_data:
        all_keys.update(item.keys())
    all_keys = sorted(list(all_keys))
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(flat_data)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.csv"
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)