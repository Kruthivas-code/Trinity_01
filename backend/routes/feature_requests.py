"""
Feature requests routes: CRUD and ticket linking.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import logging

from pymongo import DESCENDING

from database import (
    tickets_collection, feature_requests_collection,
)
from dependencies import get_current_user
from models.schemas import FeatureRequestCreate, FeatureRequestUpdate
from utils import serialize_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["feature_requests"])


@router.post("/feature-requests")
async def create_feature_request(
    data: FeatureRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new feature request"""
    fr_id = f"fr_{uuid.uuid4().hex[:12]}"
    fr_doc = {
        "feature_request_id": fr_id,
        "title": data.title,
        "description": data.description or "",
        "status": "new",
        "priority": data.priority or "medium",
        "category": data.request_type,
        "tags": [],
        "linked_ticket_ids": [data.linked_ticket_id] if data.linked_ticket_id else [],
        "vote_count": 0,
        "voters": [],
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    feature_requests_collection.insert_one(fr_doc)
    return serialize_doc(fr_doc)


@router.get("/feature-requests")
async def list_feature_requests(
    status: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """List feature requests with optional filters"""
    query = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    total = feature_requests_collection.count_documents(query)
    items = list(feature_requests_collection.find(query, {"_id": 0}).sort("created_at", DESCENDING).skip(skip).limit(limit))
    return {
        "items": [serialize_doc(fr) for fr in items],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/feature-requests/{fr_id}")
async def get_feature_request(
    fr_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a feature request by ID with linked ticket details."""
    fr = feature_requests_collection.find_one({"feature_request_id": fr_id}, {"_id": 0})
    if not fr:
        raise HTTPException(status_code=404, detail="Feature request not found")
    if fr.get("linked_ticket_ids"):
        linked_tickets = list(tickets_collection.find(
            {"ticket_id": {"$in": fr["linked_ticket_ids"]}},
            {"_id": 0, "ticket_id": 1, "title": 1, "status": 1, "priority": 1}
        ))
        fr["linked_tickets"] = [serialize_doc(t) for t in linked_tickets]
    return serialize_doc(fr)


@router.put("/feature-requests/{fr_id}")
async def update_feature_request(
    fr_id: str,
    data: FeatureRequestUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a feature request's fields."""
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    update_data["updated_at"] = datetime.now(timezone.utc)
    result = feature_requests_collection.update_one(
        {"feature_request_id": fr_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Feature request not found")
    fr = feature_requests_collection.find_one({"feature_request_id": fr_id}, {"_id": 0})
    return serialize_doc(fr)


@router.delete("/feature-requests/{fr_id}")
async def delete_feature_request(
    fr_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a feature request by ID."""
    result = feature_requests_collection.delete_one({"feature_request_id": fr_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feature request not found")
    return {"message": "Feature request deleted"}


@router.post("/feature-requests/{fr_id}/vote")
async def vote_feature_request(
    fr_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Toggle vote on a feature request. Removes vote if already voted."""
    fr = feature_requests_collection.find_one({"feature_request_id": fr_id})
    if not fr:
        raise HTTPException(status_code=404, detail="Feature request not found")
    user_id = current_user["user_id"]
    if user_id in fr.get("voters", []):
        feature_requests_collection.update_one(
            {"feature_request_id": fr_id},
            {"$pull": {"voters": user_id}, "$inc": {"vote_count": -1}}
        )
        return {"voted": False, "vote_count": fr.get("vote_count", 1) - 1}
    else:
        feature_requests_collection.update_one(
            {"feature_request_id": fr_id},
            {"$addToSet": {"voters": user_id}, "$inc": {"vote_count": 1}}
        )
        return {"voted": True, "vote_count": fr.get("vote_count", 0) + 1}


@router.post("/feature-requests/{fr_id}/link/{ticket_id}")
async def link_ticket_to_feature_request(
    fr_id: str,
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Link a ticket to a feature request for tracking related customer feedback."""
    fr = feature_requests_collection.find_one({"feature_request_id": fr_id})
    if not fr:
        raise HTTPException(status_code=404, detail="Feature request not found")
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    feature_requests_collection.update_one(
        {"feature_request_id": fr_id},
        {"$addToSet": {"linked_ticket_ids": ticket_id}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$addToSet": {"linked_feature_requests": fr_id}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": "Ticket linked to feature request"}


@router.delete("/feature-requests/{fr_id}/link/{ticket_id}")
async def unlink_ticket_from_feature_request(
    fr_id: str,
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove the link between a ticket and a feature request."""
    feature_requests_collection.update_one(
        {"feature_request_id": fr_id},
        {"$pull": {"linked_ticket_ids": ticket_id}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$pull": {"linked_feature_requests": fr_id}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": "Ticket unlinked from feature request"}
