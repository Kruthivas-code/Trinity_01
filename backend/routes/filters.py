"""
Routes for advanced ticket filtering and custom inboxes.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pymongo import ASCENDING, DESCENDING
from datetime import datetime, timezone
import uuid
import re

from database import (
    tickets_collection, custom_inboxes_collection,
    custom_fields_collection, users_collection,
)
from dependencies import get_current_user
from models.schemas import FilterRequest, InboxCreate, InboxUpdate, InboxShare
from utils import serialize_doc

router = APIRouter(prefix="/api", tags=["filters"])

# ==================== Filter Engine ====================

FIELD_TYPE_MAP = {
    "status": "select",
    "priority": "select",
    "source": "select",
    "escalation_level": "select",
    "assignee_id": "user",
    "customer_email": "text",
    "title": "text",
    "description": "text",
    "created_at": "date",
    "updated_at": "date",
    "email_sender_name": "text",
    "email_to": "text",
    "ticket_id": "text",
    "tags": "array",
}

VALID_OPERATORS = {
    "text": ["is", "is_not", "contains", "not_contains", "is_empty", "is_not_empty"],
    "select": ["is", "is_not", "is_one_of", "is_not_one_of"],
    "date": ["is", "before", "after", "between"],
    "number": ["eq", "neq", "gt", "lt", "gte", "lte"],
    "boolean": ["is"],
    "user": ["is", "is_not", "is_one_of", "is_none", "is_not_none"],
    "array": ["contains", "not_contains", "is_empty", "is_not_empty"],
}


def _resolve_field_type(field_name: str) -> str:
    if field_name in FIELD_TYPE_MAP:
        return FIELD_TYPE_MAP[field_name]
    if field_name.startswith("custom_fields."):
        field_id = field_name.split(".", 1)[1]
        cf = custom_fields_collection.find_one({"field_id": field_id})
        if cf:
            return cf.get("field_type", "text")
    return "text"


def _parse_date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            pass
    return value


def _to_number(value):
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _condition_to_mongo(condition: dict) -> dict:
    field = condition["field"]
    op = condition["op"]
    value = condition.get("value")
    db_field = field

    if op == "is":
        return {db_field: value}
    elif op == "is_not":
        return {db_field: {"$ne": value}}
    elif op == "contains":
        if isinstance(value, str):
            return {db_field: {"$regex": re.escape(value), "$options": "i"}}
        return {db_field: value}
    elif op == "not_contains":
        if isinstance(value, str):
            return {db_field: {"$not": {"$regex": re.escape(value), "$options": "i"}}}
        return {db_field: {"$ne": value}}
    elif op == "is_one_of":
        return {db_field: {"$in": value if isinstance(value, list) else [value]}}
    elif op == "is_not_one_of":
        return {db_field: {"$nin": value if isinstance(value, list) else [value]}}
    elif op == "is_none":
        return {"$or": [{db_field: None}, {db_field: {"$exists": False}}]}
    elif op == "is_not_none":
        return {db_field: {"$ne": None, "$exists": True}}
    elif op == "is_empty":
        return {"$or": [{db_field: None}, {db_field: ""}, {db_field: {"$exists": False}}, {db_field: []}]}
    elif op == "is_not_empty":
        return {db_field: {"$nin": [None, "", []], "$exists": True}}
    elif op == "before":
        return {db_field: {"$lt": _parse_date(value)}}
    elif op == "after":
        return {db_field: {"$gt": _parse_date(value)}}
    elif op == "between":
        if isinstance(value, list) and len(value) == 2:
            return {db_field: {"$gte": _parse_date(value[0]), "$lte": _parse_date(value[1])}}
        return {}
    elif op == "eq":
        return {db_field: _to_number(value)}
    elif op == "neq":
        return {db_field: {"$ne": _to_number(value)}}
    elif op == "gt":
        return {db_field: {"$gt": _to_number(value)}}
    elif op == "lt":
        return {db_field: {"$lt": _to_number(value)}}
    elif op == "gte":
        return {db_field: {"$gte": _to_number(value)}}
    elif op == "lte":
        return {db_field: {"$lte": _to_number(value)}}
    return {}


def filter_tree_to_mongo(filter_tree: dict) -> dict:
    logic = filter_tree.get("logic", "and").lower()
    mongo_op = "$and" if logic == "and" else "$or"
    parts = []

    for cond in filter_tree.get("conditions", []):
        if cond.get("field") and "op" in cond:
            fragment = _condition_to_mongo(cond)
            if fragment:
                parts.append(fragment)

    for group in filter_tree.get("groups", []):
        sub_query = filter_tree_to_mongo(group)
        if sub_query:
            parts.append(sub_query)

    if not parts:
        return {}
    if len(parts) == 1:
        return parts[0]
    return {mongo_op: parts}


# ==================== Filter Routes ====================

@router.post("/filter/tickets")
async def filter_tickets(
    req: FilterRequest,
    current_user: dict = Depends(get_current_user)
):
    mongo_query = filter_tree_to_mongo(req.filter_tree.dict())
    if mongo_query:
        mongo_query = {"$and": [mongo_query, {"status": {"$ne": "merged"}}]}
    else:
        mongo_query = {"status": {"$ne": "merged"}}

    total = tickets_collection.count_documents(mongo_query)
    sort_dir = DESCENDING if req.sort_order == "desc" else ASCENDING
    skip = (req.page - 1) * req.limit

    tickets = list(
        tickets_collection.find(mongo_query)
        .sort(req.sort_by, sort_dir)
        .skip(skip)
        .limit(req.limit)
    )

    return {
        "tickets": [serialize_doc(t) for t in tickets],
        "total": total,
        "page": req.page,
        "limit": req.limit,
        "has_more": skip + req.limit < total
    }


@router.get("/filter/fields")
async def get_filter_fields(current_user: dict = Depends(get_current_user)):
    base_fields = [
        {"field": "status", "label": "Status", "type": "select",
         "options": ["todo", "in_progress", "waiting", "waiting_on_customer", "review", "resolved", "closed"]},
        {"field": "priority", "label": "Priority", "type": "select",
         "options": ["low", "medium", "high", "urgent"]},
        {"field": "source", "label": "Source", "type": "select",
         "options": ["email", "manual", "import", "api"]},
        {"field": "escalation_level", "label": "Escalation Level", "type": "select",
         "options": ["L1", "L2", "L3"]},
        {"field": "assignee_id", "label": "Assignee", "type": "user"},
        {"field": "customer_email", "label": "Customer Email", "type": "text"},
        {"field": "title", "label": "Title", "type": "text"},
        {"field": "description", "label": "Description", "type": "text"},
        {"field": "ticket_id", "label": "Ticket ID", "type": "text"},
        {"field": "email_sender_name", "label": "Sender Name", "type": "text"},
        {"field": "tags", "label": "Tags", "type": "array"},
        {"field": "created_at", "label": "Created Date", "type": "date"},
        {"field": "updated_at", "label": "Updated Date", "type": "date"},
    ]

    custom_fields = list(custom_fields_collection.find({"entity_type": "ticket"}))
    for cf in custom_fields:
        base_fields.append({
            "field": f"custom_fields.{cf['field_id']}",
            "label": cf["name"],
            "type": cf["field_type"],
            "options": cf.get("options", []),
            "is_custom": True
        })

    return base_fields


# ==================== Custom Inboxes CRUD ====================

@router.get("/inboxes")
async def get_inboxes(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    inboxes = list(custom_inboxes_collection.find({
        "$or": [
            {"owner_id": user_id},
            {"shared_with": user_id}
        ]
    }).sort("created_at", ASCENDING))
    return [serialize_doc(i) for i in inboxes]


@router.post("/inboxes")
async def create_inbox(
    data: InboxCreate,
    current_user: dict = Depends(get_current_user)
):
    inbox_id = f"inbox_{uuid.uuid4().hex[:12]}"
    inbox_doc = {
        "inbox_id": inbox_id,
        "name": data.name,
        "filter_tree": data.filter_tree.dict(),
        "color": data.color or "#6b7280",
        "icon": data.icon,
        "owner_id": current_user["user_id"],
        "shared_with": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    custom_inboxes_collection.insert_one(inbox_doc)
    return serialize_doc(inbox_doc)


@router.get("/inboxes/{inbox_id}")
async def get_inbox(inbox_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    inbox = custom_inboxes_collection.find_one({
        "inbox_id": inbox_id,
        "$or": [{"owner_id": user_id}, {"shared_with": user_id}]
    })
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    return serialize_doc(inbox)


@router.put("/inboxes/{inbox_id}")
async def update_inbox(
    inbox_id: str,
    data: InboxUpdate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    inbox = custom_inboxes_collection.find_one({
        "inbox_id": inbox_id,
        "$or": [{"owner_id": user_id}, {"shared_with": user_id}]
    })
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")

    update = {"updated_at": datetime.now(timezone.utc)}
    if data.name is not None:
        update["name"] = data.name
    if data.filter_tree is not None:
        update["filter_tree"] = data.filter_tree.dict()
    if data.color is not None:
        update["color"] = data.color
    if data.icon is not None:
        update["icon"] = data.icon

    custom_inboxes_collection.update_one({"inbox_id": inbox_id}, {"$set": update})
    updated = custom_inboxes_collection.find_one({"inbox_id": inbox_id})
    return serialize_doc(updated)


@router.delete("/inboxes/{inbox_id}")
async def delete_inbox(inbox_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    result = custom_inboxes_collection.delete_one({
        "inbox_id": inbox_id,
        "$or": [{"owner_id": user_id}, {"shared_with": user_id}]
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Inbox not found")
    return {"message": "Inbox deleted"}


@router.post("/inboxes/{inbox_id}/share")
async def share_inbox(
    inbox_id: str,
    data: InboxShare,
    current_user: dict = Depends(get_current_user)
):
    inbox = custom_inboxes_collection.find_one({
        "inbox_id": inbox_id,
        "owner_id": current_user["user_id"]
    })
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found or you are not the owner")

    created_copies = []
    for uid in data.user_ids:
        if uid == current_user["user_id"]:
            continue
        user = users_collection.find_one({"user_id": uid})
        if not user:
            continue
        copy_id = f"inbox_{uuid.uuid4().hex[:12]}"
        copy_doc = {
            "inbox_id": copy_id,
            "name": inbox["name"],
            "filter_tree": inbox["filter_tree"],
            "color": inbox.get("color", "#6b7280"),
            "icon": inbox.get("icon"),
            "owner_id": uid,
            "shared_with": [],
            "shared_from": {
                "inbox_id": inbox_id,
                "shared_by": current_user["user_id"],
                "shared_by_name": current_user.get("name", "Unknown"),
                "shared_at": datetime.now(timezone.utc).isoformat()
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        custom_inboxes_collection.insert_one(copy_doc)
        created_copies.append({"user_id": uid, "inbox_id": copy_id})

    return {"shared_with": created_copies, "total": len(created_copies)}


@router.get("/inboxes/{inbox_id}/tickets")
async def get_inbox_tickets(
    inbox_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    inbox = custom_inboxes_collection.find_one({
        "inbox_id": inbox_id,
        "$or": [{"owner_id": user_id}, {"shared_with": user_id}]
    })
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")

    mongo_query = filter_tree_to_mongo(inbox["filter_tree"])
    if mongo_query:
        mongo_query = {"$and": [mongo_query, {"status": {"$ne": "merged"}}]}
    else:
        mongo_query = {"status": {"$ne": "merged"}}

    total = tickets_collection.count_documents(mongo_query)
    sort_dir = DESCENDING if sort_order == "desc" else ASCENDING
    skip = (page - 1) * limit

    tickets = list(
        tickets_collection.find(mongo_query)
        .sort(sort_by, sort_dir)
        .skip(skip)
        .limit(limit)
    )

    return {
        "tickets": [serialize_doc(t) for t in tickets],
        "total": total,
        "page": page,
        "limit": limit,
        "has_more": skip + limit < total,
        "inbox": serialize_doc(inbox)
    }
