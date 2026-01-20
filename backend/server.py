from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Response, Request, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
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
from email.utils import parseaddr
from html import unescape

# Gmail API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = FastAPI()

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

# Emergent Auth Configuration
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
ALLOWED_DOMAIN = "emergent.sh"

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

async def get_current_user(request: Request, session_token: Optional[str] = Cookie(None)):
    """Get current user from session token (cookie or header)"""
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

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[str] = None

class TicketReorder(BaseModel):
    ticket_id: str
    new_status: str
    new_order: int

class UserPreferences(BaseModel):
    theme: Optional[str] = "dark"

# Routes
@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

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
        
        # Verify email domain
        email = user_data.get("email", "")
        if not email.endswith(f"@{ALLOWED_DOMAIN}"):
            print(f"[AUTH] Domain mismatch: {email} vs @{ALLOWED_DOMAIN}")
            raise HTTPException(
                status_code=403,
                detail=f"Access restricted to @{ALLOWED_DOMAIN} emails only"
            )
        
        print(f"[AUTH] Email domain verified: {email}")
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
        print(f"[AUTH] Fetching user document")
        user_doc = users_collection.find_one({"email": email}, {"_id": 0})
        if not user_doc:
            raise Exception(f"User document not found after upsert: {email}")
        
        # If user_id doesn't exist (old user from previous auth system), add it
        if "user_id" not in user_doc:
            print(f"[AUTH] Old user detected, adding user_id field")
            new_user_id = f"user_{uuid.uuid4().hex[:12]}"
            users_collection.update_one(
                {"email": email},
                {"$set": {"user_id": new_user_id}}
            )
            user_doc["user_id"] = new_user_id
        
        actual_user_id = user_doc["user_id"]
        print(f"[AUTH] User ID: {actual_user_id}")
        
        # Store session
        print(f"[AUTH] Storing session")
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
        print(f"[AUTH] Setting cookie")
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=7 * 24 * 60 * 60,  # 7 days
            path="/"
        )
        
        print(f"[AUTH] Success! Returning user data")
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
    
    ticket_id = f"ticket_{uuid.uuid4().hex[:12]}"
    ticket_doc = {
        "ticket_id": ticket_id,
        "title": ticket_data.title,
        "description": ticket_data.description,
        "status": ticket_data.status,
        "assignee_id": ticket_data.assignee_id,
        "priority": ticket_data.priority,
        "order": next_order,
        "created_by": current_user["user_id"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
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
            headers={"Content-Disposition": f"attachment; filename=tickets.csv"}
        )
    else:
        return Response(
            content=json.dumps(tickets_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=tickets.json"}
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
            ticket_id = f"ticket_{uuid.uuid4().hex[:12]}"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)