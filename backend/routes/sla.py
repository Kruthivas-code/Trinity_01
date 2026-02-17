"""
SLA policy routes: public SLA listing and per-ticket SLA status.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import logging

from database import (
    tickets_collection, sla_policies_collection,
    admin_settings_collection,
)
from dependencies import get_current_user
from utils import serialize_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["sla"])


@router.get("/sla-policies")
async def list_sla_policies(current_user: dict = Depends(get_current_user)):
    """List all SLA policies"""
    policies = list(sla_policies_collection.find({}, {"_id": 0}))
    if not policies:
        return [
            {"name": "Low Priority", "priority": "low", "first_response_minutes": 480, "resolution_minutes": 2880, "is_active": True},
            {"name": "Medium Priority", "priority": "medium", "first_response_minutes": 240, "resolution_minutes": 1440, "is_active": True},
            {"name": "High Priority", "priority": "high", "first_response_minutes": 60, "resolution_minutes": 480, "is_active": True},
            {"name": "Urgent Priority", "priority": "urgent", "first_response_minutes": 15, "resolution_minutes": 120, "is_active": True}
        ]
    return [serialize_doc(p) for p in policies]


@router.get("/sla/ticket/{ticket_id}")
async def get_ticket_sla_status(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get SLA status for a specific ticket"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    priority = ticket.get("priority", "medium")
    created_at = ticket.get("created_at")

    settings = admin_settings_collection.find_one({"type": "sla_settings"}) or {}
    priority_slas = settings.get("priority_slas", {
        "low": {"first_response_minutes": 480, "resolution_minutes": 2880},
        "medium": {"first_response_minutes": 240, "resolution_minutes": 1440},
        "high": {"first_response_minutes": 60, "resolution_minutes": 480},
        "urgent": {"first_response_minutes": 15, "resolution_minutes": 120}
    })

    sla = priority_slas.get(priority, priority_slas.get("medium"))
    first_response_mins = sla.get("first_response_minutes", 240)
    resolution_mins = sla.get("resolution_minutes", 1440)

    now = datetime.now(timezone.utc)
    elapsed_minutes = 0
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        elapsed_minutes = (now - created_at).total_seconds() / 60

    first_response_status = "breached" if elapsed_minutes > first_response_mins else "on_track"
    resolution_status = "breached" if elapsed_minutes > resolution_mins else "on_track"

    if ticket.get("status") in ("resolved", "closed"):
        resolved_at = ticket.get("resolved_at") or ticket.get("closed_at") or ticket.get("updated_at")
        if resolved_at and isinstance(resolved_at, datetime):
            if resolved_at.tzinfo is None:
                resolved_at = resolved_at.replace(tzinfo=timezone.utc)
            resolve_elapsed = (resolved_at - created_at).total_seconds() / 60
            resolution_status = "breached" if resolve_elapsed > resolution_mins else "met"
        first_response_status = "met"

    return {
        "ticket_id": ticket_id,
        "priority": priority,
        "sla_policy": {
            "first_response_minutes": first_response_mins,
            "resolution_minutes": resolution_mins
        },
        "elapsed_minutes": round(elapsed_minutes, 1),
        "first_response": {
            "status": first_response_status,
            "target_minutes": first_response_mins,
            "remaining_minutes": max(0, round(first_response_mins - elapsed_minutes, 1))
        },
        "resolution": {
            "status": resolution_status,
            "target_minutes": resolution_mins,
            "remaining_minutes": max(0, round(resolution_mins - elapsed_minutes, 1))
        },
        "ticket_status": ticket.get("status")
    }
