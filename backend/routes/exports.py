"""
Data export routes: comprehensive export system for tickets, users, teams, etc.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import logging
import json
import io

from pymongo import DESCENDING

from database import (
    db, tickets_collection, users_collection, teams_collection,
    customers_collection, messages_collection, ticket_changelog_collection,
    admin_settings_collection, csat_responses_collection,
)
from dependencies import get_current_user
from models.schemas import ExportRequest
from utils import (
    serialize_doc, serialize_for_export,
    generate_json_export, generate_csv_export,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["exports"])

# ==================== Data Export System ====================

from fastapi.responses import StreamingResponse

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

@router.post("/admin/export/tickets")
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


@router.post("/admin/export/full")
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
    
    # Canned Responses
    canned_responses = list(canned_responses_collection.find({}, {"_id": 0}))
    export_data["canned_responses"] = [serialize_for_export(cr) for cr in canned_responses]
    
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


@router.get("/admin/export/customers")
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
            "open_tickets": {"$sum": {"$cond": [{"$not": {"$in": ["$status", ["resolved", "closed"]]}}, 1, 0]}},
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


@router.get("/admin/export/analytics")
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

