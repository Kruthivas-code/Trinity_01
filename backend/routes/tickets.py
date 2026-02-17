"""
Core ticket routes: CRUD, escalation, assignment, team inbox, notes, activity,
tags, starred, metadata, changelog, reorder, by-email, related, replies.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request, BackgroundTasks
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import uuid4
import uuid
import re
import asyncio
import logging

from pymongo import ASCENDING, DESCENDING

from database import (
    db, tickets_collection, users_collection, teams_collection,
    messages_collection, ticket_changelog_collection, email_replies_collection,
)
from dependencies import get_current_user
from models.schemas import (
    TicketCreate, TicketUpdate, TicketReorder, TicketAssign,
    TicketEscalate, InternalNoteCreate,
)
from ticket_helpers import (
    run_routing_rules, round_robin_assign, auto_assign_on_escalation,
    handle_ticket_reopen_reassignment,
)
from utils import (
    serialize_doc, log_ticket_change, log_ticket_changes_batch,
    generate_ticket_id, extract_domain, get_or_create_customer,
    trigger_webhooks,
)
from realtime import (
    broadcast_ticket_update, broadcast_ticket_created,
    broadcast_ticket_deleted, broadcast_mention_notification,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tickets"])


# ==================== Ticket Escalation ====================

@router.put("/tickets/{ticket_id}/escalate")
async def escalate_ticket(
    ticket_id: str,
    escalation: TicketEscalate,
    current_user: dict = Depends(get_current_user)
):
    """Escalate a ticket to a higher level (L1/L2/L3) and auto-assign to the appropriate team."""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    old_level = ticket.get("escalation_level", "L1")
    new_level = escalation.escalation_level
    if new_level not in ["L1", "L2", "L3"]:
        raise HTTPException(status_code=400, detail="Invalid escalation level. Must be L1, L2, or L3")
    escalation_record = {
        "from_level": old_level,
        "to_level": new_level,
        "reason": escalation.reason,
        "escalated_by": current_user["user_id"],
        "escalated_at": datetime.now(timezone.utc).isoformat()
    }
    assignment_result = auto_assign_on_escalation(ticket_id, new_level)
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$push": {"escalation_history": escalation_record}, "$set": {"escalated_at": datetime.now(timezone.utc)}}
    )
    updated_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    return {"ticket": serialize_doc(updated_ticket), "assignment": assignment_result, "escalation": escalation_record}


@router.get("/tickets/{ticket_id}/assignment-options")
async def get_ticket_assignment_options(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get available assignment options (team members and other teams) for a ticket."""
    from routes.shifts import is_user_on_shift, get_on_shift_members
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    current_team_id = ticket.get("team_id")
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
    all_teams = list(teams_collection.find({}, {"_id": 0, "team_id": 1, "name": 1, "escalation_level": 1}))
    other_teams = []
    for team in all_teams:
        if team.get("team_id") != current_team_id:
            team_data = serialize_doc(team)
            team_data["on_shift_count"] = len(get_on_shift_members(team.get("team_id")))
            other_teams.append(team_data)
    other_teams.sort(key=lambda t: t.get("escalation_level", "L1"))
    return {
        "ticket_id": ticket_id,
        "current_team": serialize_doc(current_team) if current_team else None,
        "current_escalation_level": ticket.get("escalation_level", "L1"),
        "team_members": team_members,
        "other_teams": other_teams
    }


@router.post("/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: str,
    assignment: TicketAssign,
    current_user: dict = Depends(get_current_user)
):
    """Assign a ticket to a specific user and/or team. Uses round-robin if no assignee specified."""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    update_data = {"updated_at": datetime.now(timezone.utc)}
    if assignment.team_id:
        update_data["team_id"] = assignment.team_id
        if not assignment.assignee_id:
            assignee = round_robin_assign(assignment.team_id)
            if assignee:
                update_data["assignee_id"] = assignee
    if assignment.assignee_id:
        update_data["assignee_id"] = assignment.assignee_id
        users_collection.update_one({"user_id": assignment.assignee_id}, {"$inc": {"current_ticket_count": 1}})
    tickets_collection.update_one({"ticket_id": ticket_id}, {"$set": update_data})
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


@router.post("/routing/auto-assign")
async def auto_assign_ticket(
    ticket_id: str,
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Auto-assign a ticket to the next available agent in a team via round-robin."""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    assignee = round_robin_assign(team_id)
    if not assignee:
        raise HTTPException(status_code=400, detail="No available agents in team")
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"assignee_id": assignee, "team_id": team_id, "updated_at": datetime.now(timezone.utc)}}
    )
    return {"ticket_id": ticket_id, "assignee_id": assignee, "team_id": team_id}


# ==================== Team Inbox ====================

@router.get("/teams/{team_id}/tickets")
async def get_team_tickets(
    team_id: str,
    status: Optional[str] = None,
    unassigned_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """List tickets assigned to a team with optional status and assignment filters."""
    team = teams_collection.find_one({"team_id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    query = {"team_id": team_id}
    if status:
        query["status"] = status
    if unassigned_only:
        query["assignee_id"] = None
    tickets = list(tickets_collection.find(query, {"_id": 0}).sort("created_at", DESCENDING).skip(skip).limit(limit))
    total = tickets_collection.count_documents(query)
    return {"tickets": [serialize_doc(t) for t in tickets], "total": total, "team_id": team_id, "team_name": team["name"]}


# ==================== Internal Notes ====================

@router.post("/tickets/{ticket_id}/notes")
async def add_internal_note(
    ticket_id: str,
    note: InternalNoteCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Add an internal note or reply to a ticket. Supports @mentions with notifications."""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    five_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=5)
    existing_duplicate = messages_collection.find_one({
        "ticket_id": ticket_id, "author_id": current_user["user_id"],
        "content": note.content, "created_at": {"$gte": five_seconds_ago}
    })
    if existing_duplicate:
        return serialize_doc(existing_duplicate)
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    mentions = note.mentions or []
    note_doc = {
        "message_id": message_id, "ticket_id": ticket_id,
        "type": note.type or "internal_note", "content": note.content,
        "author_id": current_user["user_id"], "author_name": current_user.get("name", "Unknown"),
        "author_email": current_user.get("email"), "mentions": mentions,
        "created_at": datetime.now(timezone.utc)
    }
    messages_collection.insert_one(note_doc)
    update_fields = {"updated_at": datetime.now(timezone.utc)}
    if mentions:
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": update_fields, "$addToSet": {"mentioned_users": {"$each": mentions}}}
        )
        for mentioned_user_id in mentions:
            if mentioned_user_id != current_user["user_id"]:
                background_tasks.add_task(
                    broadcast_mention_notification, mentioned_user_id, ticket_id,
                    ticket.get("title", ""), current_user.get("name", "Unknown"), note.content[:100]
                )
    else:
        tickets_collection.update_one({"ticket_id": ticket_id}, {"$set": update_fields})
    asyncio.create_task(trigger_webhooks("ticket.note_added", {
        "ticket_id": ticket_id, "ticket_title": ticket.get("title", ""),
        "note": serialize_doc(note_doc), "added_by": current_user.get("name", current_user["user_id"])
    }))
    return serialize_doc(note_doc)


@router.get("/tickets/{ticket_id}/notes")
async def get_ticket_notes(
    ticket_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get paginated notes and messages for a ticket."""
    query = {"ticket_id": ticket_id, "type": {"$in": ["internal_note", "reply", "merge_divider", "system", "customer_reply"]}}
    total = messages_collection.count_documents(query)
    skip = (page - 1) * limit
    notes = list(messages_collection.find(query, {"_id": 0}).sort("created_at", ASCENDING).skip(skip).limit(limit))
    return {"messages": [serialize_doc(n) for n in notes], "total": total, "page": page, "has_more": skip + limit < total}


@router.get("/tickets/{ticket_id}/activity")
async def get_ticket_activity(
    ticket_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get paginated activity log (all message types) for a ticket."""
    query = {"ticket_id": ticket_id}
    total = messages_collection.count_documents(query)
    skip = (page - 1) * limit
    messages = list(messages_collection.find(query, {"_id": 0}).sort("created_at", ASCENDING).skip(skip).limit(limit))
    return {"messages": [serialize_doc(m) for m in messages], "total": total, "page": page, "has_more": skip + limit < total}


@router.get("/tickets/{ticket_id}/activity-feed")
async def get_ticket_activity_feed(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a rich activity feed for a ticket including changelog, merges, and system events."""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    activities = []
    activities.append({"type": "created", "field": "ticket", "description": "Ticket created", "timestamp": ticket.get("created_at"), "user_id": ticket.get("created_by"), "icon": "plus"})
    changelog = list(ticket_changelog_collection.find({"ticket_id": ticket_id}, {"_id": 0}))
    merged_tickets = ticket.get("merged_tickets", [])
    merged_ticket_ids = [m.get("ticket_id") for m in merged_tickets if m.get("ticket_id")]
    if merged_ticket_ids:
        merged_changelog = list(ticket_changelog_collection.find({"ticket_id": {"$in": merged_ticket_ids}}, {"_id": 0}))
        changelog.extend(merged_changelog)
    field_icons = {"status": "activity", "assignee_id": "user", "priority": "alert-triangle", "team_id": "users", "tags": "tag", "merge": "git-merge", "unmerge": "git-branch", "split": "scissors", "is_starred": "star", "custom_fields": "file-text"}
    field_labels = {"status": "Status changed", "assignee_id": "Assigned", "priority": "Priority changed", "team_id": "Team changed", "tags": "Tags updated", "merge": "Ticket merged", "unmerge": "Ticket unmerged", "split": "Ticket split", "is_starred": "Starred", "custom_fields": "Custom field updated"}
    for entry in changelog:
        field = entry.get("field", "")
        old_val = entry.get("old_value")
        new_val = entry.get("new_value")
        if field == "assignee_id":
            assignee_name = None
            if new_val:
                assignee = users_collection.find_one({"user_id": new_val})
                assignee_name = assignee.get("name") if assignee else new_val
            if old_val is None or old_val == "None":
                description = f"Assigned to {assignee_name or 'Unknown'}"
            else:
                old_assignee = users_collection.find_one({"user_id": old_val})
                old_name = old_assignee.get("name") if old_assignee else old_val
                description = f"Reassigned from {old_name} to {assignee_name or 'Unknown'}"
        elif field == "status":
            description = f"Status: {old_val or 'none'} → {new_val}"
        elif field == "priority":
            description = f"Priority: {old_val} → {new_val}"
        elif field == "merge":
            description = f"Merged ticket {entry.get('metadata', {}).get('source_ticket_id', new_val)}"
        elif field == "unmerge":
            description = f"Unmerged ticket {new_val}"
        elif field == "is_starred":
            description = "Starred" if new_val else "Unstarred"
        else:
            description = f"{field_labels.get(field, field)}: {old_val} → {new_val}"
        activities.append({
            "type": entry.get("change_type", "update"), "field": field, "description": description,
            "old_value": old_val, "new_value": new_val, "timestamp": entry.get("changed_at"),
            "user_id": entry.get("changed_by"), "user_name": entry.get("changed_by_name"),
            "icon": field_icons.get(field, "edit"),
            "source_ticket_id": entry.get("ticket_id") if entry.get("ticket_id") != ticket_id else None,
            "metadata": entry.get("metadata")
        })
    merge_messages = list(messages_collection.find({"ticket_id": ticket_id, "type": "merge_divider"}, {"_id": 0}))
    for msg in merge_messages:
        source_id = msg.get("original_ticket_id")
        if source_id:
            already_recorded = any(a.get("field") == "merge" and (a.get("metadata") or {}).get("source_ticket_id") == source_id for a in activities)
            if not already_recorded:
                activities.append({"type": "merge", "field": "merge", "description": f"Merged ticket {source_id}: {msg.get('merged_ticket_title', '')}", "timestamp": msg.get("created_at"), "user_id": msg.get("created_by"), "icon": "git-merge", "source_ticket_id": source_id})
    user_ids = list(set(a.get("user_id") for a in activities if a.get("user_id") and not a.get("user_name")))
    if user_ids:
        users = {u["user_id"]: u.get("name", u["user_id"]) for u in users_collection.find({"user_id": {"$in": user_ids}})}
        for activity in activities:
            if activity.get("user_id") and not activity.get("user_name"):
                activity["user_name"] = users.get(activity["user_id"], activity["user_id"])
    def _sort_key(x):
        ts = x.get("timestamp")
        if ts is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if isinstance(ts, datetime) and ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
    activities.sort(key=_sort_key)
    return [serialize_doc(a) for a in activities]


# ==================== Tag Management ====================

@router.post("/tickets/{ticket_id}/tags")
async def add_tags(ticket_id: str, tags: List[str], current_user: dict = Depends(get_current_user)):
    """Add one or more tags to a ticket."""
    result = tickets_collection.update_one({"ticket_id": ticket_id}, {"$addToSet": {"tags": {"$each": tags}}, "$set": {"updated_at": datetime.now(timezone.utc)}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    return {"tags": ticket.get("tags", [])}


@router.delete("/tickets/{ticket_id}/tags/{tag}")
async def remove_tag(ticket_id: str, tag: str, current_user: dict = Depends(get_current_user)):
    """Remove a single tag from a ticket."""
    result = tickets_collection.update_one({"ticket_id": ticket_id}, {"$pull": {"tags": tag}, "$set": {"updated_at": datetime.now(timezone.utc)}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    return {"tags": ticket.get("tags", [])}


# ==================== Starred & Escalation Counts ====================

@router.get("/tickets/starred")
async def get_starred_tickets(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    """Get starred tickets with pagination, sorted by last update."""
    query = {"is_starred": True}
    total = tickets_collection.count_documents(query)
    skip = (page - 1) * limit
    tickets = list(tickets_collection.find(query).sort("updated_at", DESCENDING).skip(skip).limit(limit))
    return {"tickets": [serialize_doc(ticket) for ticket in tickets], "total": total, "page": page, "has_more": skip + limit < total}


@router.get("/tickets/escalation-counts")
async def get_escalation_counts(current_user: dict = Depends(get_current_user)):
    """Get ticket counts grouped by escalation level (L1/L2/L3) and status."""
    pipeline = [
        {"$match": {"status": {"$nin": ["merged", "resolved", "closed"]}}},
        {"$group": {"_id": {"escalation_level": {"$ifNull": ["$escalation_level", "L1"]}, "status": "$status"}, "count": {"$sum": 1}}}
    ]
    results = list(tickets_collection.aggregate(pipeline))
    counts = {"L1": {"total": 0}, "L2": {"total": 0}, "L3": {"total": 0}}
    for r in results:
        level = r["_id"]["escalation_level"]
        status = r["_id"]["status"]
        count = r["count"]
        if level not in counts:
            counts[level] = {"total": 0}
        counts[level][status] = count
        counts[level]["total"] += count
    return counts


# ==================== Core Ticket CRUD ====================

@router.get("/tickets")
async def get_tickets(
    request: Request,
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    mentioned_user_id: Optional[str] = None,
    is_starred: Optional[bool] = None,
    include_merged: Optional[bool] = False,
    escalation_level: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: dict = Depends(get_current_user)
):
    """List tickets with filtering, pagination, and sorting. Supports multi-value status filter."""
    query = {}
    status_values = request.query_params.getlist("status")
    if status_values:
        if len(status_values) == 1:
            query["status"] = status_values[0]
        else:
            query["status"] = {"$in": status_values}
    elif not include_merged:
        query["status"] = {"$ne": "merged"}
    if assignee_id:
        query["assignee_id"] = assignee_id
    if mentioned_user_id:
        query["mentioned_users"] = mentioned_user_id
    if is_starred is not None:
        query["is_starred"] = is_starred
    if escalation_level:
        query["escalation_level"] = escalation_level
    total = tickets_collection.count_documents(query)
    sort_dir = DESCENDING if sort_order == "desc" else ASCENDING
    skip = (page - 1) * limit
    tickets = list(tickets_collection.find(query).sort(sort_by, sort_dir).skip(skip).limit(limit))
    return {"tickets": [serialize_doc(ticket) for ticket in tickets], "total": total, "page": page, "limit": limit, "has_more": skip + limit < total}


@router.post("/tickets")
async def create_ticket(
    ticket_data: TicketCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new ticket. Automatically runs routing rules and creates a customer record."""
    max_order_ticket = tickets_collection.find_one({"status": ticket_data.status}, sort=[("order", DESCENDING)])
    next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
    ticket_id = generate_ticket_id()
    ticket_uuid = str(uuid4())
    domain = extract_domain(ticket_data.customer_email) if ticket_data.customer_email else None
    customer_id = None
    if ticket_data.customer_email:
        customer = get_or_create_customer(ticket_data.customer_email)
        if customer:
            customer_id = customer.get("customer_id")
    now = datetime.now(timezone.utc)
    assignee_id = ticket_data.assignee_id if ticket_data.assignee_id else current_user["user_id"]
    ticket_doc = {
        "ticket_id": ticket_id, "uuid": ticket_uuid, "title": ticket_data.title,
        "description": ticket_data.description, "status": ticket_data.status,
        "assignee_id": assignee_id, "priority": ticket_data.priority,
        "escalation_level": ticket_data.escalation_level or "L1", "order": next_order,
        "created_by": current_user["user_id"], "created_at": now, "updated_at": now,
        "source": ticket_data.source or "manual", "tags": ticket_data.tags or [],
        "customer_email": ticket_data.customer_email, "customer_id": customer_id,
        "domain": domain, "is_starred": False, "snoozed": False
    }
    tickets_collection.insert_one(ticket_doc)
    log_ticket_change(ticket_id=ticket_id, uuid_str=ticket_uuid, field="ticket", old_value=None, new_value=ticket_doc.get("title"), changed_by=current_user["user_id"], change_type="create")
    routing_result = run_routing_rules(ticket_doc)
    final_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    result = serialize_doc(final_ticket)
    result["routing_applied"] = routing_result.get("matched", False)
    result["routing_rule"] = routing_result.get("rule_name")
    asyncio.create_task(broadcast_ticket_created(result, {"user_id": current_user["user_id"], "name": current_user.get("name", "Unknown")}))
    asyncio.create_task(trigger_webhooks("ticket.created", result))
    return result


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single ticket by ID."""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return serialize_doc(ticket)


@router.put("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    ticket_data: TicketUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a ticket's fields. Logs changes, handles reassignment on reopen, and triggers webhooks."""
    current_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not current_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    update_data = {k: v for k, v in ticket_data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    update_data["updated_at"] = datetime.now(timezone.utc)
    if "status" in update_data and update_data["status"] == "resolved" and current_ticket.get("status") != "resolved":
        update_data["resolved_at"] = datetime.now(timezone.utc)
    if "status" in update_data and update_data["status"] == "closed" and current_ticket.get("status") != "closed":
        update_data["closed_at"] = datetime.now(timezone.utc)
    reassignment_info = None
    if "status" in update_data:
        reassignment_info = handle_ticket_reopen_reassignment(current_ticket, update_data["status"], current_user["user_id"])
        if reassignment_info and reassignment_info.get("reassigned"):
            update_data["assignee_id"] = reassignment_info.get("new_assignee_id")
            if reassignment_info.get("new_assignee_id") is None:
                update_data["status"] = "queued"
    changes = {}
    for field, new_value in update_data.items():
        if field != "updated_at":
            old_value = current_ticket.get(field)
            if old_value != new_value:
                changes[field] = (old_value, new_value)
    result = tickets_collection.update_one({"ticket_id": ticket_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if changes:
        log_ticket_changes_batch(ticket_id=ticket_id, uuid_str=current_ticket.get("uuid", ""), changes=changes, changed_by=current_user["user_id"], change_type="update")
        for field, (old_val, new_val) in changes.items():
            if field == "assignee_id":
                assignee_name = "Unassigned"
                if new_val:
                    assignee = users_collection.find_one({"user_id": new_val})
                    assignee_name = assignee.get("name", new_val) if assignee else new_val
                messages_collection.insert_one({"message_id": f"msg_{uuid4().hex[:12]}", "ticket_id": ticket_id, "type": "system", "text": f"Assigned to {assignee_name}", "created_by": current_user["user_id"], "created_at": datetime.now(timezone.utc)})
            elif field == "status":
                messages_collection.insert_one({"message_id": f"msg_{uuid4().hex[:12]}", "ticket_id": ticket_id, "type": "system", "text": f"Status changed to {new_val.replace('_', ' ').title()}", "created_by": current_user["user_id"], "created_at": datetime.now(timezone.utc)})
            elif field == "priority":
                messages_collection.insert_one({"message_id": f"msg_{uuid4().hex[:12]}", "ticket_id": ticket_id, "type": "system", "text": f"Priority set to {new_val.title()}", "created_by": current_user["user_id"], "created_at": datetime.now(timezone.utc)})
    if reassignment_info and reassignment_info.get("reassigned"):
        reason_text = "Original assignee not on shift" if reassignment_info.get("reason") == "original_assignee_off_shift" else "No agents on shift - ticket unassigned"
        log_ticket_change(ticket_id=ticket_id, uuid_str=current_ticket.get("uuid", ""), field="auto_reassignment", old_value=reassignment_info.get("old_assignee_name"), new_value=reassignment_info.get("new_assignee_name") or "Unassigned", changed_by="system", change_type="auto_reassign", metadata={"reason": reason_text})
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    serialized = serialize_doc(ticket)
    if reassignment_info:
        serialized["_reassignment_info"] = reassignment_info
    asyncio.create_task(broadcast_ticket_update(ticket_id, 'updated', serialized, {"user_id": current_user["user_id"], "name": current_user.get("name", "Unknown")}))
    asyncio.create_task(trigger_webhooks("ticket.updated", serialized))
    if changes:
        for field, (old_val, new_val) in changes.items():
            if field == "status":
                asyncio.create_task(trigger_webhooks("ticket.status_changed", {**serialized, "previous_status": old_val, "new_status": new_val}))
                if new_val == "resolved":
                    asyncio.create_task(trigger_webhooks("ticket.resolved", serialized))
                elif new_val == "closed":
                    asyncio.create_task(trigger_webhooks("ticket.closed", serialized))
            elif field == "assignee_id":
                asyncio.create_task(trigger_webhooks("ticket.assigned", {**serialized, "previous_assignee_id": old_val, "new_assignee_id": new_val}))
    return serialized


@router.delete("/tickets/{ticket_id}")
async def delete_ticket(ticket_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a ticket by ID and broadcast the deletion event."""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    log_ticket_change(ticket_id=ticket_id, uuid_str=ticket.get("uuid", ""), field="ticket", old_value=ticket.get("title"), new_value=None, changed_by=current_user["user_id"], change_type="delete")
    result = tickets_collection.delete_one({"ticket_id": ticket_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    asyncio.create_task(broadcast_ticket_deleted(ticket_id, {"user_id": current_user["user_id"], "name": current_user.get("name", "Unknown")}))
    asyncio.create_task(trigger_webhooks("ticket.deleted", serialize_doc(ticket)))
    return {"message": "Ticket deleted successfully"}


@router.get("/tickets/{ticket_id}/changelog")
async def get_ticket_changelog(
    ticket_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get the change history for a ticket with user names resolved, with pagination."""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    query = {"ticket_id": ticket_id}
    total = ticket_changelog_collection.count_documents(query)
    skip = (page - 1) * limit
    changelog = list(ticket_changelog_collection.find(query, {"_id": 0}).sort("changed_at", DESCENDING).skip(skip).limit(limit))
    user_ids = list(set(entry.get("changed_by") for entry in changelog if entry.get("changed_by")))
    users = {u["user_id"]: u.get("name", "Unknown") for u in users_collection.find({"user_id": {"$in": user_ids}}, {"user_id": 1, "name": 1})}
    for entry in changelog:
        entry["changed_by_name"] = users.get(entry.get("changed_by"), "Unknown")
        if isinstance(entry.get("changed_at"), datetime):
            entry["changed_at"] = entry["changed_at"].isoformat()
    return {"changelog": changelog, "total": total, "page": page, "has_more": skip + limit < total}


@router.get("/tickets/{ticket_id}/metadata")
async def get_ticket_metadata(ticket_id: str, current_user: dict = Depends(get_current_user)):
    """Get rich metadata for a ticket including timestamps, stats, and custom fields."""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    changelog_count = ticket_changelog_collection.count_documents({"ticket_id": ticket_id})
    last_change = ticket_changelog_collection.find_one({"ticket_id": ticket_id}, {"_id": 0}, sort=[("changed_at", DESCENDING)])
    notes_count = messages_collection.count_documents({"ticket_id": ticket_id})
    return {
        "ticket_id": ticket.get("ticket_id"), "uuid": ticket.get("uuid"), "title": ticket.get("title"),
        "status": ticket.get("status"), "priority": ticket.get("priority"), "escalation_level": ticket.get("escalation_level"),
        "tags": ticket.get("tags", []), "source": ticket.get("source"), "customer_email": ticket.get("customer_email"),
        "domain": ticket.get("domain"), "assignee_id": ticket.get("assignee_id"), "team_id": ticket.get("team_id"),
        "is_starred": ticket.get("is_starred", False), "snoozed": ticket.get("snoozed", False),
        "custom_fields": ticket.get("custom_fields", {}),
        "timestamps": {
            "created_at": ticket.get("created_at").isoformat() if isinstance(ticket.get("created_at"), datetime) else ticket.get("created_at"),
            "updated_at": ticket.get("updated_at").isoformat() if isinstance(ticket.get("updated_at"), datetime) else ticket.get("updated_at"),
            "last_change": last_change.get("changed_at").isoformat() if last_change and isinstance(last_change.get("changed_at"), datetime) else None
        },
        "stats": {"changelog_entries": changelog_count, "notes_count": notes_count},
        "created_by": ticket.get("created_by")
    }


@router.post("/tickets/reorder")
async def reorder_tickets(reorder_data: TicketReorder, current_user: dict = Depends(get_current_user)):
    """Reorder a ticket within a status column (used by Kanban board drag-and-drop)."""
    ticket = tickets_collection.find_one({"ticket_id": reorder_data.ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    new_status = reorder_data.new_status
    tickets_collection.update_one({"ticket_id": reorder_data.ticket_id}, {"$set": {"status": new_status, "order": reorder_data.new_order, "updated_at": datetime.now(timezone.utc)}})
    tickets_in_new_status = list(tickets_collection.find({"status": new_status, "ticket_id": {"$ne": reorder_data.ticket_id}}).sort("order", ASCENDING))
    for idx, t in enumerate(tickets_in_new_status):
        new_order = idx if idx < reorder_data.new_order else idx + 1
        tickets_collection.update_one({"ticket_id": t["ticket_id"]}, {"$set": {"order": new_order}})
    return {"message": "Tickets reordered successfully"}


# ==================== Conversation History ====================

@router.get("/tickets/by-email/{email}")
async def get_tickets_by_email(
    email: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    """Get tickets associated with a customer email address, with pagination."""
    email_lower = email.lower().strip()
    query = {
        "$or": [
            {"customer_email": {"$regex": f"^{re.escape(email_lower)}$", "$options": "i"}},
            {"email_sender": {"$regex": f"^{re.escape(email_lower)}$", "$options": "i"}},
            {"email_from": {"$regex": re.escape(email_lower), "$options": "i"}}
        ]
    }
    total = tickets_collection.count_documents(query)
    skip = (page - 1) * limit
    tickets = list(tickets_collection.find(query).sort("created_at", DESCENDING).skip(skip).limit(limit))
    return {"tickets": [serialize_doc(t) for t in tickets], "total": total, "page": page, "has_more": skip + limit < total}


@router.get("/tickets/{ticket_id}/related")
async def get_related_tickets(ticket_id: str, current_user: dict = Depends(get_current_user)):
    """Find related tickets from the same customer email (up to 20 results)."""
    ticket = tickets_collection.find_one({"$or": [{"id": ticket_id}, {"ticket_id": ticket_id}]})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    customer_email = ticket.get("customer_email") or ticket.get("email_sender")
    if not customer_email:
        return []
    customer_email_clean = customer_email.strip()
    if '<' in customer_email_clean and '>' in customer_email_clean:
        match = re.search(r'<([^>]+)>', customer_email_clean)
        if match:
            customer_email_clean = match.group(1)
    related = list(tickets_collection.find({
        "$and": [
            {"$or": [
                {"customer_email": customer_email},
                {"customer_email": customer_email_clean},
                {"customer_email": {"$regex": f"^{re.escape(customer_email_clean)}$", "$options": "i"}},
                {"email_sender": customer_email},
                {"email_sender": customer_email_clean},
                {"email_sender": {"$regex": f"^{re.escape(customer_email_clean)}$", "$options": "i"}},
                {"email_sender": {"$regex": f"<{re.escape(customer_email_clean)}>", "$options": "i"}}
            ]},
            {"ticket_id": {"$ne": ticket.get("ticket_id")}}
        ]
    }).sort("updated_at", DESCENDING).limit(20))
    return [serialize_doc(t) for t in related]


@router.get("/tickets/{ticket_id}/replies")
async def get_ticket_replies(ticket_id: str, current_user: dict = Depends(get_current_user)):
    """Get all email replies associated with a ticket."""
    replies = list(email_replies_collection.find({"ticket_id": ticket_id}, sort=[("created_at", ASCENDING)]))
    return {"replies": [serialize_doc(r) for r in replies]}
