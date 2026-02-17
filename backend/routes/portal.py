"""
Customer portal routes: auth, categories, ticket submission, tracking.
Public-facing endpoints — no Trinity admin auth required.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import secrets
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, Cookie
from pydantic import BaseModel, EmailStr
from pymongo import ASCENDING, DESCENDING
import bcrypt

from database import (
    portal_categories_collection, portal_customers_collection,
    portal_sessions_collection, tickets_collection,
    messages_collection, email_replies_collection,
    engineer_plans_collection,
)
from dependencies import get_current_user
from utils import serialize_doc, generate_ticket_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/portal", tags=["portal"])

SESSION_EXPIRY_DAYS = 30


# ==================== Models ====================

class CustomerRegister(BaseModel):
    name: str
    email: str
    password: str

class CustomerLogin(BaseModel):
    email: str
    password: str

class TicketSubmit(BaseModel):
    category_slug: str
    subcategory: Optional[str] = None
    subject: str
    description: str

class TicketReply(BaseModel):
    body: str

class HelpArticle(BaseModel):
    title: str
    url: str

class CategoryCreate(BaseModel):
    title: str
    slug: str
    description: Optional[str] = ""
    icon: Optional[str] = "HelpCircle"
    subtopics: Optional[list] = []
    help_articles: Optional[list] = []
    order: Optional[int] = 0

class CategoryUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    subtopics: Optional[list] = None
    help_articles: Optional[list] = None
    order: Optional[int] = None


# ==================== Customer Auth Helpers ====================

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def _create_session(customer_id: str) -> str:
    token = secrets.token_urlsafe(32)
    portal_sessions_collection.insert_one({
        "token": token,
        "customer_id": customer_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS),
    })
    return token

async def get_portal_customer(request: Request, portal_token: Optional[str] = Cookie(None)):
    """Get portal customer from session cookie."""
    token = portal_token
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = portal_sessions_collection.find_one({"token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires = session["expires_at"]
    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        portal_sessions_collection.delete_one({"token": token})
        raise HTTPException(status_code=401, detail="Session expired")
    customer = portal_customers_collection.find_one(
        {"customer_id": session["customer_id"]}, {"_id": 0, "password_hash": 0}
    )
    if not customer:
        raise HTTPException(status_code=401, detail="Customer not found")
    return customer


# ==================== Customer Auth ====================

@router.post("/auth/register")
async def register_customer(body: CustomerRegister):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    existing = portal_customers_collection.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    customer_id = f"cust_{uuid.uuid4().hex[:12]}"
    portal_customers_collection.insert_one({
        "customer_id": customer_id,
        "name": body.name.strip(),
        "email": body.email.lower().strip(),
        "password_hash": _hash_password(body.password),
        "created_at": datetime.now(timezone.utc),
    })
    token = _create_session(customer_id)
    return {
        "customer_id": customer_id,
        "name": body.name.strip(),
        "email": body.email.lower().strip(),
        "token": token,
    }


@router.post("/auth/login")
async def login_customer(body: CustomerLogin):
    customer = portal_customers_collection.find_one({"email": body.email.lower()})
    if not customer:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not _verify_password(body.password, customer["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _create_session(customer["customer_id"])
    return {
        "customer_id": customer["customer_id"],
        "name": customer["name"],
        "email": customer["email"],
        "token": token,
    }


@router.get("/auth/me")
async def get_me(customer: dict = Depends(get_portal_customer)):
    return customer


@router.post("/auth/logout")
async def logout_customer(request: Request, portal_token: Optional[str] = Cookie(None)):
    token = portal_token
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.replace("Bearer ", "")
    if token:
        portal_sessions_collection.delete_one({"token": token})
    return {"message": "Logged out"}


# ==================== Categories (Public) ====================

@router.get("/categories")
async def list_categories():
    cats = list(portal_categories_collection.find(
        {}, {"_id": 0}
    ).sort("order", ASCENDING))
    return {"categories": cats}


@router.get("/categories/{slug}")
async def get_category(slug: str):
    cat = portal_categories_collection.find_one({"slug": slug}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


# ==================== Categories (Admin) ====================

@router.post("/admin/categories")
async def create_category(body: CategoryCreate, current_user: dict = Depends(get_current_user)):
    existing = portal_categories_collection.find_one({"slug": body.slug})
    if existing:
        raise HTTPException(status_code=409, detail="Category slug already exists")
    doc = {
        "category_id": f"cat_{uuid.uuid4().hex[:8]}",
        "title": body.title,
        "slug": body.slug,
        "description": body.description or "",
        "icon": body.icon or "HelpCircle",
        "subtopics": body.subtopics or [],
        "help_articles": body.help_articles or [],
        "order": body.order or 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    portal_categories_collection.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/admin/categories/{slug}")
async def update_category(slug: str, body: CategoryUpdate, current_user: dict = Depends(get_current_user)):
    cat = portal_categories_collection.find_one({"slug": slug})
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    updates = {k: v for k, v in body.dict(exclude_unset=True).items() if v is not None}
    if "slug" in updates and updates["slug"] != slug:
        existing = portal_categories_collection.find_one({"slug": updates["slug"]})
        if existing:
            raise HTTPException(status_code=409, detail="Slug already in use")
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        portal_categories_collection.update_one({"slug": slug}, {"$set": updates})
    final_slug = updates.get("slug", slug)
    return portal_categories_collection.find_one({"slug": final_slug}, {"_id": 0})


@router.delete("/admin/categories/{slug}")
async def delete_category(slug: str, current_user: dict = Depends(get_current_user)):
    result = portal_categories_collection.delete_one({"slug": slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Deleted"}


# ==================== Engineer Plans ====================

class EngineerPlanCreate(BaseModel):
    title: str
    price: int
    hours: int
    period: str = "month"
    features: list = []
    active: bool = True

class EngineerPlanUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[int] = None
    hours: Optional[int] = None
    period: Optional[str] = None
    features: Optional[list] = None
    active: Optional[bool] = None

@router.get("/engineer-plans")
async def list_engineer_plans():
    plans = list(engineer_plans_collection.find({"active": True}, {"_id": 0}).sort("order", 1))
    return {"plans": plans}

@router.get("/admin/engineer-plans")
async def admin_list_engineer_plans(current_user: dict = Depends(get_current_user)):
    plans = list(engineer_plans_collection.find({}, {"_id": 0}).sort("order", 1))
    return {"plans": plans}

@router.post("/admin/engineer-plans")
async def create_engineer_plan(body: EngineerPlanCreate, current_user: dict = Depends(get_current_user)):
    plan_id = str(uuid.uuid4())[:8]
    doc = {
        "plan_id": plan_id,
        **body.dict(),
        "order": engineer_plans_collection.count_documents({}) + 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    engineer_plans_collection.insert_one(doc)
    doc.pop("_id", None)
    return doc

@router.put("/admin/engineer-plans/{plan_id}")
async def update_engineer_plan(plan_id: str, body: EngineerPlanUpdate, current_user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        engineer_plans_collection.update_one({"plan_id": plan_id}, {"$set": updates})
    return engineer_plans_collection.find_one({"plan_id": plan_id}, {"_id": 0})

@router.delete("/admin/engineer-plans/{plan_id}")
async def delete_engineer_plan(plan_id: str, current_user: dict = Depends(get_current_user)):
    result = engineer_plans_collection.delete_one({"plan_id": plan_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Deleted"}

def _seed_engineer_plans():
    if engineer_plans_collection.count_documents({}) == 0:
        engineer_plans_collection.insert_one({
            "plan_id": "dedicated-10",
            "title": "Dedicated Engineer",
            "price": 1000,
            "hours": 10,
            "period": "month",
            "features": [
                "Priority response within 1 hour",
                "1:1 video sessions with a senior engineer",
                "Direct Slack channel access",
                "Architecture review & code audit",
                "Custom integration assistance",
            ],
            "active": True,
            "order": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

_seed_engineer_plans()


# ==================== Inquiries ====================

class InquirySubmit(BaseModel):
    name: str
    email: str
    company: Optional[str] = ""
    message: str
    type: str  # partner, sales, engineer

@router.post("/inquiries")
async def submit_inquiry(body: InquirySubmit):
    """Public inquiry endpoint - creates a ticket tagged by inquiry type."""
    type_labels = {"partner": "Partner Program Inquiry", "sales": "Sales Inquiry", "engineer": "Dedicated Engineer Inquiry"}
    ticket_id = generate_ticket_id()
    ticket_doc = {
        "ticket_id": ticket_id,
        "uuid": str(uuid.uuid4()),
        "title": f"[{type_labels.get(body.type, 'Inquiry')}] from {body.name}",
        "description": f"Name: {body.name}\nEmail: {body.email}\nCompany: {body.company or 'N/A'}\n\n{body.message}",
        "status": "todo",
        "priority": "medium" if body.type != "engineer" else "high",
        "tags": [body.type, "inquiry"],
        "source": "portal",
        "portal_customer_email": body.email,
        "portal_customer_name": body.name,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    tickets_collection.insert_one(ticket_doc)
    return {"status": "ok", "ticket_id": ticket_id}


# ==================== Ticket Submission ====================

@router.post("/tickets")
async def submit_ticket(body: TicketSubmit, customer: dict = Depends(get_portal_customer)):
    ticket_id = generate_ticket_id()
    ticket_doc = {
        "ticket_id": ticket_id,
        "uuid": str(uuid.uuid4()),
        "title": body.subject.strip()[:200],
        "description": body.description.strip()[:10000],
        "status": "todo",
        "priority": "medium",
        "source": "portal",
        "portal_category": body.category_slug,
        "portal_subcategory": body.subcategory,
        "customer_email": customer["email"],
        "customer_name": customer["name"],
        "customer_id": customer["customer_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "assignee_id": None,
        "escalation_level": "L1",
    }
    tickets_collection.insert_one(ticket_doc)
    ticket_doc.pop("_id", None)

    messages_collection.insert_one({
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "type": "original",
        "content": body.description.strip()[:10000],
        "author_id": None,
        "author_name": customer["name"],
        "author_email": customer["email"],
        "created_at": datetime.now(timezone.utc),
    })

    return {"ticket_id": ticket_id, "status": "todo", "message": "Ticket submitted successfully"}


# ==================== Customer Tickets ====================

@router.get("/tickets")
async def list_my_tickets(
    status: Optional[str] = None,
    customer: dict = Depends(get_portal_customer),
):
    query = {"customer_email": customer["email"]}
    if status:
        query["status"] = status
    tickets = list(tickets_collection.find(
        query, {"_id": 0, "ticket_id": 1, "title": 1, "status": 1, "priority": 1,
                "portal_category": 1, "created_at": 1, "updated_at": 1}
    ).sort("updated_at", DESCENDING).limit(100))
    return {"tickets": [serialize_doc(t) for t in tickets]}


@router.get("/tickets/{ticket_id}")
async def get_my_ticket(ticket_id: str, customer: dict = Depends(get_portal_customer)):
    ticket = tickets_collection.find_one(
        {"ticket_id": ticket_id, "customer_email": customer["email"]}, {"_id": 0}
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    msgs = list(messages_collection.find(
        {"ticket_id": ticket_id},
        {"_id": 0, "message_id": 1, "type": 1, "content": 1, "author_name": 1,
         "author_email": 1, "created_at": 1}
    ).sort("created_at", ASCENDING))

    return {
        "ticket": serialize_doc(ticket),
        "messages": [serialize_doc(m) for m in msgs],
    }


@router.post("/tickets/{ticket_id}/reply")
async def reply_to_my_ticket(
    ticket_id: str,
    body: TicketReply,
    customer: dict = Depends(get_portal_customer),
):
    ticket = tickets_collection.find_one(
        {"ticket_id": ticket_id, "customer_email": customer["email"]}
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    messages_collection.insert_one({
        "message_id": msg_id,
        "ticket_id": ticket_id,
        "type": "customer_reply",
        "content": body.body.strip()[:10000],
        "author_id": None,
        "author_name": customer["name"],
        "author_email": customer["email"],
        "created_at": datetime.now(timezone.utc),
    })

    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {
            "status": "todo",
            "updated_at": datetime.now(timezone.utc),
            "last_customer_reply_at": datetime.now(timezone.utc),
        }}
    )

    return {"message_id": msg_id, "message": "Reply sent"}


# ==================== Seed Default Categories ====================

def seed_default_categories():
    """Seed the default categories if none exist."""
    if portal_categories_collection.count_documents({}) > 0:
        return
    defaults = [
        {"title": "Credits & Pricing", "slug": "credits-pricing", "icon": "CreditCard",
         "description": "Credit usage, types, refunds, and pricing plans",
         "subtopics": [
             {"name": "Credit Usage", "items": ["High usage", "How credits work"]},
             {"name": "Credit Types", "items": ["Referral credits", "Deployment charges", "Universal key charges"]},
             {"name": "Refunds", "items": []},
             {"name": "Pricing", "items": []},
         ]},
        {"title": "Subscription Management", "slug": "subscription-management", "icon": "Receipt",
         "description": "Plans, billing, upgrades, and payment methods",
         "subtopics": [
             {"name": "Plans", "items": ["Features by plan", "Enterprise plans"]},
             {"name": "Upgrade / Downgrade", "items": ["Annual plans", "Auto-renewal"]},
             {"name": "Payment methods", "items": []},
             {"name": "Invoices", "items": []},
         ]},
        {"title": "Custom Domain", "slug": "custom-domain", "icon": "Globe",
         "description": "Linking, DNS, routing, subdomains, and SSL",
         "subtopics": [
             {"name": "Linking", "items": []},
             {"name": "DNS", "items": []},
             {"name": "Routing", "items": []},
             {"name": "Subdomains", "items": []},
             {"name": "SSL", "items": []},
             {"name": "Permissions", "items": []},
         ]},
        {"title": "Features", "slug": "features", "icon": "Boxes",
         "description": "GitHub, forking, custom agents, rollback, and integrations",
         "subtopics": [
             {"name": "GitHub integration", "items": []},
             {"name": "Forking", "items": []},
             {"name": "Mobile vs Web", "items": []},
             {"name": "Custom agents", "items": []},
             {"name": "Rollback", "items": []},
             {"name": "Infra (+ DB)", "items": []},
             {"name": "Projects / Teams", "items": []},
             {"name": "Universal key", "items": []},
             {"name": "Integrations", "items": []},
         ]},
        {"title": "Account Management", "slug": "account-management", "icon": "UserCog",
         "description": "Password reset, account transfer, deletion, and privacy",
         "subtopics": [
             {"name": "Password reset", "items": []},
             {"name": "Account transfer", "items": []},
             {"name": "Account deletion", "items": []},
             {"name": "Privacy", "items": []},
         ]},
        {"title": "Security & Compliance", "slug": "security-compliance", "icon": "ShieldCheck",
         "description": "Compliance, data location, encryption, and export",
         "subtopics": [
             {"name": "Compliance", "items": []},
             {"name": "Data location", "items": []},
             {"name": "Encryption", "items": []},
             {"name": "Ownership", "items": []},
             {"name": "Export", "items": []},
         ]},
        {"title": "Deployments", "slug": "deployments", "icon": "Rocket",
         "description": "Preview vs production, build failures, and rollback",
         "subtopics": [
             {"name": "Preview vs Production", "items": []},
             {"name": "Build failures", "items": []},
             {"name": "Post-deployment issues", "items": []},
             {"name": "Health check", "items": []},
             {"name": "Rollback", "items": []},
             {"name": "Upgrade", "items": []},
             {"name": "CORS", "items": []},
             {"name": "Production outage", "items": []},
             {"name": "Changes not reflected", "items": []},
         ]},
        {"title": "Agent (Core AI System)", "slug": "agent-ai", "icon": "Bot",
         "description": "Tech stacks, code quality, bugs, and production readiness",
         "subtopics": [
             {"name": "Tech stacks", "items": []},
             {"name": "Code quality", "items": []},
             {"name": "Bugs", "items": []},
             {"name": "Production readiness", "items": []},
         ]},
        {"title": "Database", "slug": "database", "icon": "Database",
         "description": "Data sync, external DB, triggers, and export",
         "subtopics": [
             {"name": "Data sync", "items": []},
             {"name": "External DB", "items": []},
             {"name": "Triggers", "items": []},
             {"name": "Export", "items": []},
             {"name": "Preview vs Deployment behavior", "items": []},
         ]},
        {"title": "Mobile Builds", "slug": "mobile-builds", "icon": "Smartphone",
         "description": "Publish to store and technical issues",
         "subtopics": [
             {"name": "Publish to store", "items": []},
             {"name": "Technical issues", "items": []},
         ]},
    ]
    now = datetime.now(timezone.utc)
    for i, cat in enumerate(defaults):
        cat["category_id"] = f"cat_{uuid.uuid4().hex[:8]}"
        cat["order"] = i
        cat["created_at"] = now
        cat["updated_at"] = now
    portal_categories_collection.insert_many(defaults)
    logger.info(f"[PORTAL] Seeded {len(defaults)} default categories")
