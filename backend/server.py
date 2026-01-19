from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
import os
import json
import csv
import io

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

# Security
SECRET_KEY = "tickflow-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

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
            if key == "_id" and isinstance(value, ObjectId):
                serialized["id"] = str(value)
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
        return serialized
    return doc

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return serialize_doc(user)

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TicketCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    status: str = "backlog"
    assignee_id: Optional[str] = None

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None

class TicketReorder(BaseModel):
    ticket_id: str
    new_status: str
    new_order: int

# Routes
@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Auth endpoints
@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    # Check if user exists
    existing_user = users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_doc = {
        "email": user_data.email,
        "password": get_password_hash(user_data.password),
        "name": user_data.name,
        "role": "user",
        "created_at": datetime.utcnow()
    }
    result = users_collection.insert_one(user_doc)
    
    # Create token
    access_token = create_access_token(data={"sub": str(result.inserted_id)})
    
    user_doc["_id"] = result.inserted_id
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": serialize_doc(user_doc)
    }

@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    user = users_collection.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": serialize_doc(user)
    }

# User endpoints
@app.get("/api/users/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

@app.get("/api/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    users = list(users_collection.find({}))
    return [serialize_doc(user) for user in users]

# Ticket endpoints
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
    # Get max order for the status
    max_order_ticket = tickets_collection.find_one(
        {"status": ticket_data.status},
        sort=[("order", DESCENDING)]
    )
    next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
    
    ticket_doc = {
        "title": ticket_data.title,
        "description": ticket_data.description,
        "status": ticket_data.status,
        "assignee_id": ticket_data.assignee_id,
        "order": next_order,
        "created_by": current_user["id"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = tickets_collection.insert_one(ticket_doc)
    ticket_doc["_id"] = result.inserted_id
    
    return serialize_doc(ticket_doc)

@app.get("/api/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    ticket = tickets_collection.find_one({"_id": ObjectId(ticket_id)})
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
        {"_id": ObjectId(ticket_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = tickets_collection.find_one({"_id": ObjectId(ticket_id)})
    return serialize_doc(ticket)

@app.delete("/api/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    result = tickets_collection.delete_one({"_id": ObjectId(ticket_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"message": "Ticket deleted successfully"}

@app.post("/api/tickets/reorder")
async def reorder_tickets(
    reorder_data: TicketReorder,
    current_user: dict = Depends(get_current_user)
):
    ticket = tickets_collection.find_one({"_id": ObjectId(reorder_data.ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    old_status = ticket["status"]
    new_status = reorder_data.new_status
    
    # Update the ticket's status and order
    tickets_collection.update_one(
        {"_id": ObjectId(reorder_data.ticket_id)},
        {"$set": {"status": new_status, "order": reorder_data.new_order, "updated_at": datetime.utcnow()}}
    )
    
    # Reorder other tickets in the new status
    tickets_in_new_status = list(tickets_collection.find(
        {"status": new_status, "_id": {"$ne": ObjectId(reorder_data.ticket_id)}}
    ).sort("order", ASCENDING))
    
    for idx, t in enumerate(tickets_in_new_status):
        new_order = idx if idx < reorder_data.new_order else idx + 1
        tickets_collection.update_one(
            {"_id": t["_id"]},
            {"$set": {"order": new_order}}
        )
    
    return {"message": "Tickets reordered successfully"}

# Analytics endpoint
@app.get("/api/analytics/summary")
async def get_analytics_summary(current_user: dict = Depends(get_current_user)):
    # Count by status
    status_counts = {}
    for status in ["backlog", "todo", "in_progress", "review", "done"]:
        count = tickets_collection.count_documents({"status": status})
        status_counts[status] = count
    
    # Count by assignee
    pipeline = [
        {"$match": {"assignee_id": {"$ne": None}}},
        {"$group": {"_id": "$assignee_id", "count": {"$sum": 1}}}
    ]
    assignee_counts = list(tickets_collection.aggregate(pipeline))
    
    # My tickets
    my_tickets_count = tickets_collection.count_documents({"assignee_id": current_user["id"]})
    
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
    tickets = list(tickets_collection.find({}))
    tickets_data = [serialize_doc(ticket) for ticket in tickets]
    
    if format == "csv":
        output = io.StringIO()
        if tickets_data:
            fieldnames = ["id", "title", "description", "status", "assignee_id", "order", "created_at", "updated_at"]
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
            ticket_doc = {
                "title": item.get("title", "Imported Ticket"),
                "description": item.get("description", ""),
                "status": item.get("status", "backlog"),
                "assignee_id": item.get("assignee_id"),
                "order": int(item.get("order", 0)),
                "created_by": current_user["id"],
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