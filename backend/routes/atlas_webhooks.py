"""
Atlas Webhook Handler — receives real-time events from Atlas and syncs to Trinity.
Replaces polling for new tickets, status changes, assignments, messages, tags, and priority.
"""

import logging
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from database import tickets_collection
from services.atlas_sync import (
    _create_ticket_from_conv,
    _sync_messages,
    _sync_sidebars,
    _sync_fields,
    _build_agent_email_map,
    _fetch_tags,
    _headers,
    STATUS_MAP,
    PRIORITY_MAP,
    ATLAS_API,
)
import requests as http_requests

logger = logging.getLogger("atlas_webhooks")

router = APIRouter(prefix="/api", tags=["webhooks"])

# Cache agent/tag maps (rebuilt every 5 minutes via background refresh)
_cache = {"agent_map": {}, "tag_map": {}, "last_refresh": None}
CACHE_TTL_SECONDS = 300


def _get_maps():
    now = datetime.now(timezone.utc)
    if not _cache["last_refresh"] or (now - _cache["last_refresh"]).total_seconds() > CACHE_TTL_SECONDS:
        _cache["agent_map"] = _build_agent_email_map()
        _cache["tag_map"] = _fetch_tags()
        _cache["last_refresh"] = now
    return _cache["agent_map"], _cache["tag_map"]


def _fetch_conversation(conv_id: str) -> dict:
    """Fetch full conversation details from Atlas API."""
    try:
        resp = http_requests.get(
            f"{ATLAS_API}/conversations/{conv_id}",
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"[WEBHOOK] Failed to fetch conversation {conv_id}: {e}")
        return {}


def _extract_conversation_id(payload: dict) -> str:
    """Extract conversation ID from various payload shapes."""
    # Try common patterns
    for key in ("conversationId", "conversation_id", "id"):
        if key in payload and isinstance(payload[key], str):
            return payload[key]
    # Nested under conversation/data
    for wrapper in ("conversation", "data", "payload"):
        nested = payload.get(wrapper)
        if isinstance(nested, dict):
            for key in ("id", "conversationId", "conversation_id"):
                if key in nested:
                    return str(nested[key])
    return ""


def _handle_conversation_created(payload: dict):
    """Handle new conversation — create ticket + sync messages."""
    agent_map, tag_map = _get_maps()
    conv_id = _extract_conversation_id(payload)

    # Check if we already have it
    if conv_id and tickets_collection.find_one({"atlas_conversation_id": conv_id}, {"_id": 0, "ticket_id": 1}):
        logger.info(f"[WEBHOOK] Conversation {conv_id} already exists, skipping create")
        return

    # Try to get full conversation from payload, or fetch from API
    conv = payload.get("conversation") or payload.get("data") or {}
    if not conv.get("id") and conv_id:
        conv = _fetch_conversation(conv_id)

    if not conv.get("id"):
        logger.warning(f"[WEBHOOK] Could not get conversation data for created event")
        return

    ticket_id = _create_ticket_from_conv(conv, tag_map, agent_map)
    if ticket_id:
        atlas_id = str(conv.get("id", ""))
        _sync_messages(atlas_id, ticket_id)
        _sync_sidebars(atlas_id, ticket_id)
        logger.info(f"[WEBHOOK] Created ticket {ticket_id} from conversation #{conv.get('number')}")


def _handle_field_change(payload: dict, change_type: str):
    """Handle status/agent/priority/tag changes — update existing ticket fields."""
    agent_map, _ = _get_maps()
    conv_id = _extract_conversation_id(payload)

    if not conv_id:
        logger.warning(f"[WEBHOOK] No conversation ID in {change_type} event")
        return

    ticket = tickets_collection.find_one(
        {"atlas_conversation_id": conv_id},
        {"_id": 0},
    )

    if not ticket:
        # Ticket doesn't exist yet — create it
        logger.info(f"[WEBHOOK] Ticket for {conv_id} not found, creating from {change_type} event")
        _handle_conversation_created(payload)
        return

    # Fetch fresh conversation from Atlas to get current state
    conv = _fetch_conversation(conv_id)
    if not conv.get("id"):
        return

    updates_applied, conflicts = _sync_fields(conv, ticket, agent_map)
    logger.info(f"[WEBHOOK] {change_type}: ticket {ticket['ticket_id']} — {updates_applied} updates, {conflicts} conflicts")


def _handle_new_message(payload: dict):
    """Handle new message — sync messages for existing ticket."""
    conv_id = _extract_conversation_id(payload)
    if not conv_id:
        logger.warning("[WEBHOOK] No conversation ID in new message event")
        return

    ticket = tickets_collection.find_one(
        {"atlas_conversation_id": conv_id},
        {"_id": 0, "ticket_id": 1},
    )

    if not ticket:
        # Ticket doesn't exist — create it first
        logger.info(f"[WEBHOOK] Ticket for {conv_id} not found, creating from message event")
        _handle_conversation_created(payload)
        return

    new_msgs = _sync_messages(conv_id, ticket["ticket_id"])
    if new_msgs:
        logger.info(f"[WEBHOOK] Synced {new_msgs} new messages for {ticket['ticket_id']}")


def _handle_tags_changed(payload: dict):
    """Handle tag changes — update ticket tags."""
    conv_id = _extract_conversation_id(payload)
    if not conv_id:
        return

    ticket = tickets_collection.find_one(
        {"atlas_conversation_id": conv_id},
        {"_id": 0, "ticket_id": 1},
    )
    if not ticket:
        _handle_conversation_created(payload)
        return

    # Fetch fresh conversation for updated tags
    conv = _fetch_conversation(conv_id)
    if not conv.get("id"):
        return

    _, tag_map = _get_maps()
    raw_tags = conv.get("tags") or []
    mapped_tags = [tag_map.get(str(t), str(t)) for t in raw_tags]

    tickets_collection.update_one(
        {"ticket_id": ticket["ticket_id"]},
        {"$set": {"tags": mapped_tags, "updated_at": datetime.now(timezone.utc)}},
    )
    logger.info(f"[WEBHOOK] Updated tags for {ticket['ticket_id']}: {mapped_tags}")


# Event type → handler mapping
EVENT_HANDLERS = {
    "conversation.created": _handle_conversation_created,
    "conversation_created": _handle_conversation_created,
    "conversation.agent_changed": lambda p: _handle_field_change(p, "agent_changed"),
    "conversation_agent_changed": lambda p: _handle_field_change(p, "agent_changed"),
    "conversation.status_changed": lambda p: _handle_field_change(p, "status_changed"),
    "conversation_status_changed": lambda p: _handle_field_change(p, "status_changed"),
    "conversation.priority_changed": lambda p: _handle_field_change(p, "priority_changed"),
    "conversation_priority_changed": lambda p: _handle_field_change(p, "priority_changed"),
    "conversation.tags_changed": _handle_tags_changed,
    "conversation_tags_changed": _handle_tags_changed,
    "message.received": _handle_new_message,
    "new_message_received": _handle_new_message,
    "message.created": _handle_new_message,
}


@router.post("/webhooks/atlas")
async def atlas_webhook(request: Request):
    """
    Receive webhook events from Atlas.
    Returns 200 immediately to avoid Atlas retries, processes in-band.
    """
    try:
        body = await request.body()
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.warning(f"[WEBHOOK] Non-JSON body received: {body[:500]}")
            return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)

        # Log raw payload for debugging (first 2000 chars)
        logger.info(f"[WEBHOOK] Received: {json.dumps(payload, default=str)[:2000]}")

        # Try to determine event type from payload
        event_type = (
            payload.get("event")
            or payload.get("eventType")
            or payload.get("event_type")
            or payload.get("type")
            or ""
        ).lower().strip()

        handler = EVENT_HANDLERS.get(event_type)

        if handler:
            handler(payload)
        else:
            # Unknown event type — try to infer from payload contents
            logger.info(f"[WEBHOOK] Unknown event type '{event_type}', attempting inference")
            conv_id = _extract_conversation_id(payload)
            if conv_id:
                exists = tickets_collection.find_one(
                    {"atlas_conversation_id": conv_id},
                    {"_id": 0, "ticket_id": 1},
                )
                if exists:
                    _handle_field_change(payload, f"inferred_{event_type or 'unknown'}")
                else:
                    _handle_conversation_created(payload)

        return JSONResponse({"status": "ok"})

    except Exception as e:
        logger.error(f"[WEBHOOK] Error processing webhook: {e}", exc_info=True)
        return JSONResponse({"status": "ok"})


@router.get("/webhooks/atlas/health")
async def atlas_webhook_health():
    """Health check for webhook endpoint — useful for Atlas verification."""
    return {"status": "ok", "service": "trinity-atlas-webhook", "timestamp": datetime.now(timezone.utc).isoformat()}
