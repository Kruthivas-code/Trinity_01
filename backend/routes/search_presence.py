"""
Search, presence, and notification routes.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from typing import Optional
import logging

from database import (
    db, tickets_collection, users_collection, customers_collection,
    notifications_collection,
)
from dependencies import get_current_user
from search import get_search_engine
from realtime import get_presence_stats, get_users_viewing_ticket
from models.schemas import SearchQuery
from utils import serialize_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/notifications")
async def get_notifications(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get notifications for the current user"""
    notifications = list(notifications_collection.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit))
    return [serialize_doc(n) for n in notifications]


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark notification as read"""
    result = notifications_collection.update_one(
        {"notification_id": notification_id, "user_id": current_user["user_id"]},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}


@router.post("/search")
async def search_tickets(
    query: SearchQuery,
    current_user: dict = Depends(get_current_user)
):
    """Search tickets using text search"""
    search_engine = get_search_engine(db)
    results = search_engine.search_all(
        query=query.query,
        limit_per_category=query.limit if hasattr(query, 'limit') else 20,
        current_user_id=current_user.get("user_id")
    )
    return results


@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str = Query("", min_length=1),
    current_user: dict = Depends(get_current_user)
):
    """Get search suggestions/autocomplete"""
    if len(q) < 2:
        return {"suggestions": []}

    ticket_suggestions = list(tickets_collection.find(
        {"title": {"$regex": q, "$options": "i"}},
        {"_id": 0, "ticket_id": 1, "title": 1, "status": 1}
    ).limit(5))

    customer_suggestions = list(customers_collection.find(
        {"$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}}
        ]},
        {"_id": 0, "customer_id": 1, "name": 1, "email": 1}
    ).limit(3))

    user_suggestions = list(users_collection.find(
        {"$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}}
        ]},
        {"_id": 0, "user_id": 1, "name": 1, "email": 1}
    ).limit(3))

    return {
        "suggestions": {
            "tickets": [serialize_doc(t) for t in ticket_suggestions],
            "customers": [serialize_doc(c) for c in customer_suggestions],
            "users": [serialize_doc(u) for u in user_suggestions]
        }
    }


@router.get("/presence/stats")
async def presence_stats(current_user: dict = Depends(get_current_user)):
    """Get presence statistics"""
    return await get_presence_stats()


@router.get("/presence/ticket/{ticket_id}")
async def ticket_presence(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get users viewing a specific ticket"""
    return {"users": await get_users_viewing_ticket(ticket_id)}
