from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Response, Request, Cookie, Header, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
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
from email.utils import parseaddr
from html import unescape
from dotenv import load_dotenv
from functools import wraps

# Load environment variables from .env file
load_dotenv()

# Gmail API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = FastAPI(
    title="TickFlow API",
    description="Enterprise ticket management platform",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# API Key Security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# ==================== Utility Functions ====================

def generate_ticket_id() -> str:
    """Generate sequential ticket ID (TKT-000001 format)"""
    counter = counters_collection.find_one_and_update(
        {"_id": "ticket_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return f"TKT-{counter['seq']:06d}"

def extract_domain(email: str) -> Optional[str]:
    """Extract domain from email address"""
    if not email:
        return None
    try:
        # Handle "Name <email@domain.com>" format
        _, addr = parseaddr(email)
        if '@' in addr:
            return addr.split('@')[1].lower()
    except:
        pass
    return None

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

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None

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
    type: str = "l1"  # l1, l2, specialist
    description: Optional[str] = ""

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
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

class TicketAssign(BaseModel):
    assignee_id: Optional[str] = None
    team_id: Optional[str] = None

# Routes
@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "version": "1.0.0"}

# Emergent Auth endpoints
@app.post("/api/auth/session")
async def create_session(session_data: SessionCreate, response: Response):
    """Exchange session_id for session_token"""
    try:
        print(f"[AUTH] Received session_id: {session_data.session_id[:20]}...")
        
        # Call Emergent Auth API to get user data
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"[AUTH] Calling Emergent Auth API: {EMERGENT_AUTH_URL}")
            auth_response = await client.get(
                EMERGENT_AUTH_URL,
                headers={"X-Session-ID": session_data.session_id}
            )
            print(f"[AUTH] Emergent Auth response status: {auth_response.status_code}")
        
        if auth_response.status_code != 200:
            print(f"[AUTH] Invalid session_id, status: {auth_response.status_code}")
            raise HTTPException(status_code=401, detail="Invalid session_id")
        
        user_data = auth_response.json()
        print(f"[AUTH] Got user data: {user_data.get('email')}")
        
        # Verify email domain (skip if ALLOWED_DOMAIN is None)
        email = user_data.get("email", "")
        if ALLOWED_DOMAIN and not email.endswith(f"@{ALLOWED_DOMAIN}"):
            print(f"[AUTH] Domain mismatch: {email} vs @{ALLOWED_DOMAIN}")
            raise HTTPException(
                status_code=403,
                detail=f"Access restricted to @{ALLOWED_DOMAIN} emails only"
            )
        
        print(f"[AUTH] Email verified: {email}")
        session_token = user_data["session_token"]
        
        # Generate user_id if new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        
        # Create or update user in database
        print(f"[AUTH] Upserting user: {email}")
        result = users_collection.update_one(
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
        print("[AUTH] Fetching user document")
        user_doc = users_collection.find_one({"email": email}, {"_id": 0})
        if not user_doc:
            raise Exception(f"User document not found after upsert: {email}")
        
        # If user_id doesn't exist (old user from previous auth system), add it
        if "user_id" not in user_doc:
            print("[AUTH] Old user detected, adding user_id field")
            new_user_id = f"user_{uuid.uuid4().hex[:12]}"
            users_collection.update_one(
                {"email": email},
                {"$set": {"user_id": new_user_id}}
            )
            user_doc["user_id"] = new_user_id
        
        actual_user_id = user_doc["user_id"]
        print(f"[AUTH] User ID: {actual_user_id}")
        
        # Store session
        print("[AUTH] Storing session")
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
        print("[AUTH] Setting cookie")
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=7 * 24 * 60 * 60,  # 7 days
            path="/"
        )
        
        print("[AUTH] Success! Returning user data")
        return serialize_doc(user_doc)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] ERROR: {type(e).__name__}: {str(e)}")
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
    users = list(users_collection.find({}, {"_id": 0}))
    return [serialize_doc(user) for user in users]

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
@app.get("/api/tickets")
async def get_tickets(
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if assignee_id:
        query["assignee_id"] = assignee_id
    
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
    
    # Generate sequential ticket ID
    ticket_id = generate_ticket_id()
    
    # Extract domain from customer email if provided
    domain = extract_domain(ticket_data.customer_email) if ticket_data.customer_email else None
    
    ticket_doc = {
        "ticket_id": ticket_id,
        "title": ticket_data.title,
        "description": ticket_data.description,
        "status": ticket_data.status,
        "assignee_id": ticket_data.assignee_id,
        "priority": ticket_data.priority,
        "order": next_order,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        # New fields
        "source": ticket_data.source or "manual",
        "tags": ticket_data.tags or [],
        "customer_email": ticket_data.customer_email,
        "domain": domain
    }
    
    tickets_collection.insert_one(ticket_doc)
    return serialize_doc(ticket_doc)

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
    update_data = {k: v for k, v in ticket_data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    return serialize_doc(ticket)

@app.delete("/api/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    result = tickets_collection.delete_one({"ticket_id": ticket_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"message": "Ticket deleted successfully"}

@app.post("/api/tickets/reorder")
async def reorder_tickets(
    reorder_data: TicketReorder,
    current_user: dict = Depends(get_current_user)
):
    ticket = tickets_collection.find_one({"ticket_id": reorder_data.ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    old_status = ticket["status"]
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
    for status in ["todo", "in_progress", "waiting", "review", "resolved"]:
        count = tickets_collection.count_documents({" status": status})
        status_counts[status] = count
    
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
    frontend_url = "https://tickflow-7.preview.emergentagent.com"
    
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
        
        print("[GMAIL] OAuth tokens stored successfully")
        return RedirectResponse(url=f"{frontend_url}/settings?gmail_connected=true")
    
    except Exception as e:
        print(f"[GMAIL] OAuth error: {str(e)}")
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
        print(f"[GMAIL] Error fetching emails: {str(e)}")
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
        print(f"[GMAIL] Error fetching email detail: {str(e)}")
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
        print(f"[GMAIL] Created ticket {ticket_id} from email {message_id}")
        
        return serialize_doc(ticket_doc)
    
    except Exception as e:
        print(f"[GMAIL] Error creating ticket from email: {str(e)}")
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
        print(f"[GMAIL] Syncing with query: {search_query}")
        
        results = service.users().messages().list(
            userId='me',
            maxResults=max_emails,
            q=search_query
        ).execute()
        
        messages = results.get('messages', [])
        print(f"[GMAIL] Found {len(messages)} emails matching query")
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
        print(f"[GMAIL] Error syncing emails: {str(e)}")
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
        print(f"[EMAIL MOCK] Would send email to {reply.to_email}: {reply.subject}")
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
            print(f"[EMAIL] Error sending: {str(e)}")
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
    print(f"[EMAIL SIM] Created ticket {ticket_id} from simulated email")
    
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
        except:
            # Fall back to form data (common for email webhooks)
            form = await request.form()
            data = dict(form)
        
        print(f"[EMAIL WEBHOOK] Received: {data}")
        
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
        print(f"[EMAIL WEBHOOK] Created ticket {ticket_id}")
        
        return {"status": "created", "ticket_id": ticket_id}
        
    except Exception as e:
        print(f"[EMAIL WEBHOOK] Error: {str(e)}")
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
        print(f"[GMAIL WEBHOOK] Received notification: {body}")
        
        # Decode the Pub/Sub message
        if 'message' in body:
            import base64
            message_data = body['message'].get('data', '')
            if message_data:
                decoded = base64.urlsafe_b64decode(message_data).decode('utf-8')
                notification = json.loads(decoded)
                print(f"[GMAIL WEBHOOK] Decoded notification: {notification}")
                
                # Get the history ID to fetch new messages
                history_id = notification.get('historyId')
                email_address = notification.get('emailAddress')
                
                if history_id:
                    # Trigger background sync
                    await process_gmail_notification(history_id, email_address)
        
        # Always return 200 to acknowledge receipt
        return {"status": "ok"}
    
    except Exception as e:
        print(f"[GMAIL WEBHOOK] Error processing notification: {str(e)}")
        # Still return 200 to prevent retries
        return {"status": "error", "message": str(e)}

async def process_gmail_notification(history_id: str, email_address: str):
    """Process a Gmail push notification by fetching new messages"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        print("[GMAIL WEBHOOK] No Gmail tokens found")
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
            
            print(f"[GMAIL WEBHOOK] Found {len(messages_added)} new messages")
            
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
                print(f"[GMAIL WEBHOOK] Created ticket {ticket_id} from email {msg_id}")
        
        # Update stored history ID
        gmail_tokens_collection.update_one(
            {"type": "gmail_watch"},
            {"$set": {"history_id": history_id}},
            upsert=True
        )
        
    except Exception as e:
        print(f"[GMAIL WEBHOOK] Error processing: {str(e)}")

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
        
        print(f"[GMAIL] Watch started: {watch_response}")
        
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
        print(f"[GMAIL] Error starting watch: {str(e)}")
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
        print(f"[GMAIL] Error stopping watch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop watch: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)