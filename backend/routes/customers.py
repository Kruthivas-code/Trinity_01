"""
Routes for customers.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import re
import uuid
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from pymongo import ASCENDING, DESCENDING
from database import (
    customers_collection, tickets_collection, users_collection,
    csat_responses_collection, messages_collection, B2C_EMAIL_DOMAINS,
)
from dependencies import get_current_user
from models.schemas import CustomerCreate, CustomerUpdate, LinkEmailRequest, MergeCustomersRequest
from utils import serialize_doc, extract_domain, is_b2c_email, detect_company_from_domain, generate_customer_id, trigger_webhooks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["customers"])

# ==================== Customer Management System ====================

@router.get("/customers")
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
        escaped_search = re.escape(search)
        query["$or"] = [
            {"name": {"$regex": escaped_search, "$options": "i"}},
            {"primary_email": {"$regex": escaped_search, "$options": "i"}},
            {"linked_emails": {"$regex": escaped_search, "$options": "i"}},
            {"company_name": {"$regex": escaped_search, "$options": "i"}},
            {"customer_id": {"$regex": escaped_search, "$options": "i"}}
        ]
    
    if customer_type:
        query["customer_type"] = customer_type
    
    if priority_level:
        query["priority_level"] = priority_level
    
    if assigned_agent:
        query["assigned_agents"] = assigned_agent
    
    customers = list(customers_collection.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit))
    total = customers_collection.count_documents(query)
    
    # Batch: collect all emails for all customers in this page
    all_emails = []
    customer_email_map = {}  # primary_email -> list of all emails for that customer
    for customer in customers:
        customer_emails = [customer["primary_email"]] + customer.get("linked_emails", [])
        customer_email_map[customer["primary_email"]] = customer_emails
        all_emails.extend(customer_emails)
    
    # Single aggregation for ticket stats grouped by customer_email
    ticket_stats_map = {}
    if all_emails:
        ticket_stats_pipeline = [
            {"$match": {"customer_email": {"$in": all_emails}}},
            {"$group": {
                "_id": "$customer_email",
                "total_tickets": {"$sum": 1},
                "open_tickets": {"$sum": {"$cond": [{"$in": ["$status", ["todo", "in_progress", "waiting", "review"]]}, 1, 0]}},
                "resolved_tickets": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}}
            }}
        ]
        for stat in tickets_collection.aggregate(ticket_stats_pipeline):
            ticket_stats_map[stat["_id"]] = stat
    
    # Single aggregation for CSAT stats grouped by customer_email
    csat_stats_map = {}
    if all_emails:
        csat_stats_pipeline = [
            {"$match": {"customer_email": {"$in": all_emails}, "rating": {"$ne": None}}},
            {"$group": {"_id": "$customer_email", "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
        ]
        for stat in csat_responses_collection.aggregate(csat_stats_pipeline):
            csat_stats_map[stat["_id"]] = stat
    
    # Assemble results using the batch lookups
    result = []
    for customer in customers:
        customer_emails = customer_email_map[customer["primary_email"]]
        
        # Sum stats across all emails for this customer
        total_tickets = 0
        open_tickets = 0
        resolved_tickets = 0
        total_csat_sum = 0.0
        total_csat_count = 0
        for email in customer_emails:
            ts = ticket_stats_map.get(email)
            if ts:
                total_tickets += ts["total_tickets"]
                open_tickets += ts["open_tickets"]
                resolved_tickets += ts["resolved_tickets"]
            cs = csat_stats_map.get(email)
            if cs:
                total_csat_sum += cs["avg_rating"] * cs["count"]
                total_csat_count += cs["count"]
        
        customer_data = serialize_doc(customer)
        customer_data["stats"] = {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "resolved_tickets": resolved_tickets,
            "avg_csat": round(total_csat_sum / total_csat_count, 1) if total_csat_count > 0 else None,
            "csat_count": total_csat_count
        }
        result.append(customer_data)
    
    return {
        "customers": result,
        "total": total,
        "limit": limit,
        "skip": skip
    }

@router.get("/customers/b2b-prospects")
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

@router.get("/customers/{customer_id}")
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

@router.post("/customers")
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
    
    result = serialize_doc(new_customer)
    
    # Trigger webhook for customer.created
    asyncio.create_task(trigger_webhooks("customer.created", result))
    
    return result

@router.put("/customers/{customer_id}")
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
    result = serialize_doc(updated)
    
    # Trigger webhook for customer.updated
    asyncio.create_task(trigger_webhooks("customer.updated", result))
    
    return result

@router.post("/customers/{customer_id}/link-email")
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

@router.delete("/customers/{customer_id}/unlink-email/{email}")
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

@router.post("/customers/merge")
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

@router.get("/customers/{customer_id}/tickets")
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

