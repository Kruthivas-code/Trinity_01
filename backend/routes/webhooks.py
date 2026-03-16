"""
Routes for webhooks.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4
import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from database import (
    webhooks_collection, webhook_logs_collection, tickets_collection,
    messages_collection, WEBHOOK_EVENT_TYPES, AUTO_CLOSE_HOURS,
)
from dependencies import get_current_user, require_admin
from models.schemas import WebhookCreate, WebhookUpdate
from utils import serialize_doc, deliver_webhook, validate_webhook_url

router = APIRouter(prefix="/api", tags=["webhooks"])

# ==================== Webhooks API ====================

def serialize_webhook(webhook: dict) -> dict:
    """Serialize webhook document, hiding the secret for security"""
    result = serialize_doc(webhook)
    # Don't expose the actual secret - just indicate if one is set
    if result.get("secret"):
        result["secret"] = "********"  # Mask the secret
        result["has_secret"] = True
    else:
        result["has_secret"] = False
    return result

@router.get("/webhooks/events")
async def list_webhook_events(current_user: dict = Depends(get_current_user)):
    """List all available webhook event types"""
    return {
        "events": WEBHOOK_EVENT_TYPES,
        "descriptions": {
            "ticket.created": "Triggered when a new ticket is created",
            "ticket.updated": "Triggered when ticket fields are updated",
            "ticket.assigned": "Triggered when a ticket is assigned to a user or team",
            "ticket.status_changed": "Triggered when ticket status changes",
            "ticket.resolved": "Triggered when a ticket is closed (legacy alias for ticket.closed)",
            "ticket.closed": "Triggered when a ticket is closed",
            "ticket.deleted": "Triggered when a ticket is deleted",
            "ticket.reply_added": "Triggered when a reply is added to a ticket",
            "ticket.note_added": "Triggered when an internal note is added",
            "customer.created": "Triggered when a new customer is created",
            "customer.updated": "Triggered when customer information is updated",
            "sla.breach": "Triggered when an SLA is breached",
            "sla.warning": "Triggered when an SLA breach is imminent"
        }
    }


@router.get("/webhooks/logs")
async def get_all_webhook_logs(
    cursor: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    event: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Get all webhook delivery logs (admin only)"""
    query = {}
    if status:
        query["status"] = status
    if event:
        query["event"] = event

    logs = list(webhook_logs_collection.find(query).sort("created_at", -1).skip(cursor).limit(limit))
    total = webhook_logs_collection.count_documents(query)

    return {
        "data": [serialize_doc(log) for log in logs],
        "total": total,
        "cursor": cursor,
        "limit": limit
    }


@router.get("/webhooks")
async def list_webhooks(
    cursor: int = 0,
    limit: int = 20,
    current_user: dict = Depends(require_admin)
):
    """List all webhook subscriptions (admin only)"""
    webhooks = list(webhooks_collection.find().skip(cursor).limit(limit))
    total = webhooks_collection.count_documents({})
    
    return {
        "data": [serialize_webhook(w) for w in webhooks],
        "total": total,
        "cursor": cursor,
        "limit": limit
    }

@router.post("/webhooks")
async def create_webhook(
    webhook: WebhookCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a new webhook subscription (admin only)"""
    try:
        validate_webhook_url(webhook.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook URL: {e}")

    webhook_id = f"wh_{uuid.uuid4().hex[:12]}"
    
    webhook_doc = {
        "webhook_id": webhook_id,
        "name": webhook.name,
        "url": webhook.url,
        "events": webhook.events,
        "secret": webhook.secret,
        "headers": webhook.headers or {},
        "is_active": webhook.is_active,
        "created_by": current_user.get("email"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "delivery_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "last_triggered_at": None
    }
    
    webhooks_collection.insert_one(webhook_doc)
    
    return {
        "message": "Webhook created successfully",
        "webhook": serialize_webhook(webhook_doc)
    }

@router.get("/webhooks/events")
async def list_webhook_events(current_user: dict = Depends(get_current_user)):
    """List all available webhook event types"""
    return {
        "events": WEBHOOK_EVENT_TYPES,
        "descriptions": {
            "ticket.created": "Triggered when a new ticket is created",
            "ticket.updated": "Triggered when ticket fields are updated",
            "ticket.assigned": "Triggered when a ticket is assigned to a user or team",
            "ticket.status_changed": "Triggered when ticket status changes",
            "ticket.resolved": "Triggered when a ticket is closed (legacy alias for ticket.closed)",
            "ticket.closed": "Triggered when a ticket is closed",
            "ticket.deleted": "Triggered when a ticket is deleted",
            "ticket.reply_added": "Triggered when a reply is added to a ticket",
            "ticket.note_added": "Triggered when an internal note is added",
            "customer.created": "Triggered when a new customer is created",
            "customer.updated": "Triggered when customer information is updated",
            "sla.breach": "Triggered when an SLA is breached",
            "sla.warning": "Triggered when an SLA breach is imminent"
        }
    }

@router.get("/webhooks/{webhook_id}")
async def get_webhook(
    webhook_id: str,
    current_user: dict = Depends(require_admin)
):
    """Get a specific webhook subscription (admin only)"""
    webhook = webhooks_collection.find_one({"webhook_id": webhook_id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return serialize_webhook(webhook)

@router.put("/webhooks/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    webhook_update: WebhookUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update a webhook subscription (admin only)"""
    webhook = webhooks_collection.find_one({"webhook_id": webhook_id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if webhook_update.name is not None:
        update_data["name"] = webhook_update.name
    if webhook_update.url is not None:
        update_data["url"] = webhook_update.url
    if webhook_update.events is not None:
        update_data["events"] = webhook_update.events
    if webhook_update.secret is not None:
        update_data["secret"] = webhook_update.secret
    if webhook_update.headers is not None:
        update_data["headers"] = webhook_update.headers
    if webhook_update.is_active is not None:
        update_data["is_active"] = webhook_update.is_active
    
    webhooks_collection.update_one(
        {"webhook_id": webhook_id},
        {"$set": update_data}
    )
    
    updated_webhook = webhooks_collection.find_one({"webhook_id": webhook_id})
    return {
        "message": "Webhook updated successfully",
        "webhook": serialize_webhook(updated_webhook)
    }

@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete a webhook subscription (admin only)"""
    result = webhooks_collection.delete_one({"webhook_id": webhook_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Also delete associated logs
    webhook_logs_collection.delete_many({"webhook_id": webhook_id})
    
    return {"message": "Webhook deleted successfully"}

@router.get("/webhooks/{webhook_id}/logs")
async def get_webhook_logs(
    webhook_id: str,
    cursor: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Get delivery logs for a webhook (admin only)"""
    webhook = webhooks_collection.find_one({"webhook_id": webhook_id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    query = {"webhook_id": webhook_id}
    if status:
        query["status"] = status
    
    logs = list(webhook_logs_collection.find(query).sort("created_at", -1).skip(cursor).limit(limit))
    total = webhook_logs_collection.count_documents(query)
    
    return {
        "data": [serialize_doc(log) for log in logs],
        "total": total,
        "cursor": cursor,
        "limit": limit
    }

@router.get("/webhooks/logs")
async def get_all_webhook_logs(
    cursor: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    event: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Get all webhook delivery logs (admin only)"""
    query = {}
    if status:
        query["status"] = status
    if event:
        query["event"] = event
    
    logs = list(webhook_logs_collection.find(query).sort("created_at", -1).skip(cursor).limit(limit))
    total = webhook_logs_collection.count_documents(query)
    
    return {
        "data": [serialize_doc(log) for log in logs],
        "total": total,
        "cursor": cursor,
        "limit": limit
    }

@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    current_user: dict = Depends(require_admin)
):
    """Send a test event to a webhook (admin only)"""
    webhook = webhooks_collection.find_one({"webhook_id": webhook_id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    test_payload = {
        "ticket_id": "TKT-TEST",
        "title": "Test Webhook Event",
        "description": "This is a test webhook delivery from Trinity",
        "status": "todo",
        "priority": "medium",
        "test": True
    }
    
    # Deliver synchronously for test so we can return the result
    success = await deliver_webhook(webhook, "test.webhook", test_payload)
    
    # Get the latest log
    latest_log = webhook_logs_collection.find_one(
        {"webhook_id": webhook_id},
        sort=[("created_at", -1)]
    )
    
    return {
        "success": success,
        "message": "Test webhook delivered successfully" if success else "Test webhook delivery failed",
        "log": serialize_doc(latest_log) if latest_log else None
    }

@router.post("/webhooks/{webhook_id}/retry/{log_id}")
async def retry_webhook_delivery(
    webhook_id: str,
    log_id: str,
    current_user: dict = Depends(require_admin)
):
    """Retry a failed webhook delivery (admin only)"""
    webhook = webhooks_collection.find_one({"webhook_id": webhook_id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    log = webhook_logs_collection.find_one({"log_id": log_id, "webhook_id": webhook_id})
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    
    if log.get("status") == "delivered":
        raise HTTPException(status_code=400, detail="Cannot retry a successful delivery")
    
    # Re-deliver using the original payload
    original_payload = log.get("request_body", {}).get("data", {})
    event_type = log.get("event", "unknown")
    
    success = await deliver_webhook(webhook, event_type, original_payload)
    
    return {
        "success": success,
        "message": "Webhook retry delivered successfully" if success else "Webhook retry failed"
    }

@router.post("/admin/trigger-auto-close")
async def trigger_auto_close(current_user: dict = Depends(get_current_user)):
    """Manually trigger the auto-close process (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=AUTO_CLOSE_HOURS)
    
    query = {"status": "closed", "resolved_at": {"$lte": cutoff_time}}
    resolved_tickets = list(tickets_collection.find(query, {"ticket_id": 1, "_id": 0}))
    closed_tickets = [t["ticket_id"] for t in resolved_tickets]
    
    if closed_tickets:
        now = datetime.now(timezone.utc)
        # Batch update all resolved tickets at once
        tickets_collection.update_many(
            {"ticket_id": {"$in": closed_tickets}},
            {"$set": {"status": "closed", "closed_at": now, "auto_closed": True, "updated_at": now}}
        )
        # Batch insert system messages
        system_messages = [
            {
                "message_id": f"msg_{uuid4().hex[:12]}",
                "ticket_id": tid,
                "type": "system",
                "text": f"Auto-closed after {AUTO_CLOSE_HOURS} hours in resolved status",
                "created_by": "system",
                "created_at": now
            }
            for tid in closed_tickets
        ]
        messages_collection.insert_many(system_messages)
    
    return {
        "message": f"Auto-closed {len(closed_tickets)} tickets",
        "closed_tickets": closed_tickets
    }

