"""
Leave management routes.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from typing import Optional
import asyncio
import logging

from database import db, users_collection
from dependencies import get_current_user, require_lead_or_admin
from leave_management import get_leave_manager, LeaveRequest, LeaveUpdate
from realtime import broadcast_leave_created, broadcast_leave_updated, broadcast_leave_deleted
from utils import serialize_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["leaves"])


@router.get("/leaves")
async def get_leaves(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get leaves with optional filters"""
    leave_mgr = get_leave_manager(db)
    return await leave_mgr.get_leaves(user_id=user_id, status=status)


@router.post("/leaves")
async def create_leave(
    leave_data: LeaveRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new leave request"""
    leave_mgr = get_leave_manager(db)
    leave = leave_mgr.create_leave(leave_data.dict(), current_user["user_id"])
    asyncio.create_task(broadcast_leave_created(
        leave,
        {"user_id": current_user["user_id"], "name": current_user.get("name", "")}
    ))
    return leave


@router.get("/leaves/{leave_id}")
async def get_leave(
    leave_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific leave"""
    leave_mgr = get_leave_manager(db)
    leave = await leave_mgr.get_leave(leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    return leave


@router.put("/leaves/{leave_id}")
async def update_leave(
    leave_id: str,
    leave_data: LeaveUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a leave request"""
    leave_mgr = get_leave_manager(db)
    updated = await leave_mgr.update_leave(leave_id, leave_data.dict(exclude_unset=True), current_user["user_id"])
    if not updated:
        raise HTTPException(status_code=404, detail="Leave not found")
    asyncio.create_task(broadcast_leave_updated(
        leave_id, updated,
        {"user_id": current_user["user_id"], "name": current_user.get("name", "")}
    ))
    return updated


@router.delete("/leaves/{leave_id}")
async def delete_leave(
    leave_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a leave request"""
    leave_mgr = get_leave_manager(db)
    deleted = await leave_mgr.delete_leave(leave_id, current_user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Leave not found")
    asyncio.create_task(broadcast_leave_deleted(
        leave_id,
        {"user_id": current_user["user_id"], "name": current_user.get("name", "")}
    ))
    return {"message": "Leave deleted successfully"}


@router.put("/leaves/{leave_id}/approve")
async def approve_leave(
    leave_id: str,
    current_user: dict = Depends(require_lead_or_admin)
):
    """Approve a leave request"""
    leave_mgr = get_leave_manager(db)
    approved = await leave_mgr.approve_leave(leave_id, current_user["user_id"])
    if not approved:
        raise HTTPException(status_code=404, detail="Leave not found or already processed")
    asyncio.create_task(broadcast_leave_updated(
        leave_id, approved,
        {"user_id": current_user["user_id"], "name": current_user.get("name", "")}
    ))
    return approved


@router.put("/leaves/{leave_id}/reject")
async def reject_leave(
    leave_id: str,
    current_user: dict = Depends(require_lead_or_admin)
):
    """Reject a leave request"""
    leave_mgr = get_leave_manager(db)
    rejected = await leave_mgr.reject_leave(leave_id, current_user["user_id"])
    if not rejected:
        raise HTTPException(status_code=404, detail="Leave not found or already processed")
    asyncio.create_task(broadcast_leave_updated(
        leave_id, rejected,
        {"user_id": current_user["user_id"], "name": current_user.get("name", "")}
    ))
    return rejected
