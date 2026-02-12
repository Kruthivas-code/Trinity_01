"""
User profile, preferences, listing, and role management routes.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional
import logging

from database import users_collection, teams_collection
from dependencies import get_current_user, require_admin
from models.schemas import UserPreferences, UserRoleUpdate
from utils import serialize_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users/me")
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get the authenticated user's full profile."""
    return current_user


@router.put("/users/me/preferences")
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


@router.get("/users")
async def get_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get users with pagination and optional search"""
    limit = min(limit, 500)

    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]

    total = users_collection.count_documents(query)

    users = list(users_collection.find(
        query,
        {"password": 0}
    ).skip(skip).limit(limit))

    result = []
    for user in users:
        serialized = serialize_doc(user)
        if "id" not in serialized:
            if "user_id" in user:
                serialized["id"] = user["user_id"]
            elif "_id" in user:
                serialized["id"] = str(user["_id"])
        result.append(serialized)

    return {
        "items": result,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(result) < total
    }


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_data: UserRoleUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update user role and team assignment - requires admin role"""
    update_data = {
        "role": role_data.role,
        "updated_at": datetime.now(timezone.utc)
    }

    if role_data.team_id is not None:
        update_data["team_id"] = role_data.team_id
    if role_data.skills is not None:
        update_data["skills"] = role_data.skills
    if role_data.max_tickets is not None:
        update_data["max_tickets"] = role_data.max_tickets

    result = users_collection.update_one(
        {"user_id": user_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    if role_data.team_id:
        teams_collection.update_many(
            {"members": user_id},
            {"$pull": {"members": user_id}}
        )
        teams_collection.update_one(
            {"team_id": role_data.team_id},
            {"$addToSet": {"members": user_id}}
        )

    user = users_collection.find_one({"user_id": user_id}, {"_id": 0})
    return serialize_doc(user)
