"""
Atlas Shadow Mode — Real-Time Sync Engine
==========================================
Polls Atlas for recently active conversations and syncs new tickets,
new messages, and sidebar (internal note) content into Trinity.

Trinity takes precedence in conflicts: if a ticket was modified in
Trinity after the last sync, Atlas field changes are skipped (logged
as conflict).

State is persisted in MongoDB (`atlas_sync_state`, _type="shadow").
Runs as a daemon thread that auto-starts on server boot.
"""

import os
import re
import uuid
import html as html_lib
import logging
import time
import threading
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional

from database import (
    db, tickets_collection, messages_collection,
    users_collection, customers_collection,
)
from utils import generate_ticket_id

logger = logging.getLogger("atlas_shadow")

ATLAS_API = "https://api.atlas.so/v1"
ATLAS_KEY = os.environ.get("ATLAS_API_KEY", "")

# State collection (shared with backfill, different _type)
_state_col = db.atlas_backfill_state

# Thread control
_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

# Defaults
DEFAULT_POLL_INTERVAL = 60       # seconds between sync cycles
DEFAULT_LOOKBACK_MINUTES = 15    # how far back to look for updated conversations

# Field mappings (same as backfill)
STATUS_MAP = {
    "OPEN": "todo",
    "CLOSED": "closed",
    "SNOOZED": "waiting",
    "PENDING": "waiting",
    "IN_PROGRESS": "in_progress",
}

PRIORITY_MAP = {
    "NO_PRIORITY": "medium",
    "LOW": "low",
    "NORMAL": "medium",
    "HIGH": "high",
    "URGENT": "urgent",
}

MESSAGE_TYPE_MAP = {
    "AGENT": "reply",
    "CUSTOMER": "customer_reply",
    "BOT": "reply",
    "SYSTEM": "system",
}


# ══════════════════════════════════════════════════════════════
# State Management
# ══════════════════════════════════════════════════════════════

def _get_state() -> dict:
    state = _state_col.find_one({"_type": "shadow"}, {"_id": 0})
    if not state:
        return {
            "_type": "shadow",
            "status": "stopped",
            "poll_interval": DEFAULT_POLL_INTERVAL,
            "lookback_minutes": DEFAULT_LOOKBACK_MINUTES,
            "last_sync_at": None,
            "cycles_completed": 0,
            "conversations_checked": 0,
            "new_tickets_created": 0,
            "messages_synced": 0,
            "sidebars_synced": 0,
            "field_updates": 0,
            "conflicts_skipped": 0,
            "errors": [],
            "started_at": None,
        }
    return state


def _save_state(state: dict):
    state["_type"] = "shadow"
    _state_col.update_one({"_type": "shadow"}, {"$set": state}, upsert=True)


def get_sync_status() -> dict:
    state = _get_state()
    state.pop("_type", None)
    state["is_running"] = _worker_thread is not None and _worker_thread.is_alive()
    # Trim errors to last 20
    if len(state.get("errors", [])) > 20:
        state["errors"] = state["errors"][-20:]
    return state


# ══════════════════════════════════════════════════════════════
# Atlas API Helpers
# ══════════════════════════════════════════════════════════════

def _headers():
    return {"Accept": "application/json", "Authorization": f"Bearer {ATLAS_KEY}"}


def _parse_dt(val) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val, tz=timezone.utc)
        except (OSError, ValueError):
            return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except (ValueError, TypeError):
        return None


def _strip_html(html_str: str) -> str:
    if not html_str:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html_str, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    return text.strip()


def _customer_name(customer: dict) -> str:
    if not customer:
        return "Customer"
    first = customer.get("firstName") or ""
    last = customer.get("lastName") or ""
    full = f"{first} {last}".strip()
    return full or customer.get("email") or "Customer"


def _agent_name(agent: dict) -> str:
    if not agent:
        return None
    first = agent.get("firstName") or ""
    last = agent.get("lastName") or ""
    full = f"{first} {last}".strip()
    return full or agent.get("email") or "Agent"


def _extract_domain(email_addr: str) -> Optional[str]:
    if not email_addr or "@" not in email_addr:
        return None
    return email_addr.split("@", 1)[1].lower()


def _fetch_tags() -> dict:
    try:
        resp = requests.get(f"{ATLAS_API}/tags", headers=_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        tags = data if isinstance(data, list) else data.get("data", data.get("tags", []))
        return {str(t.get("id", "")): (t.get("label") or t.get("name") or str(t.get("id", ""))) for t in tags if t.get("id")}
    except Exception as e:
        logger.warning(f"[SHADOW] Failed to fetch tags: {e}")
        return {}


def _build_agent_email_map() -> dict:
    all_users = list(users_collection.find({}, {"_id": 0, "user_id": 1, "email": 1}))
    return {u["email"].lower(): u["user_id"] for u in all_users if u.get("email")}


# ══════════════════════════════════════════════════════════════
# Customer helper
# ══════════════════════════════════════════════════════════════

def _get_or_create_customer(email_addr: str, name: str, atlas_customer: dict = None) -> Optional[dict]:
    if not email_addr:
        return None
    email_lower = email_addr.lower().strip()
    existing = customers_collection.find_one(
        {"email": {"$regex": f"^{re.escape(email_lower)}$", "$options": "i"}},
        {"_id": 0, "customer_id": 1},
    )
    if existing:
        return existing
    customer_id = f"cust_{uuid.uuid4().hex[:12]}"
    doc = {
        "customer_id": customer_id,
        "name": name or email_lower,
        "email": email_lower,
        "domain": _extract_domain(email_lower),
        "created_at": datetime.now(timezone.utc),
        "source": "atlas_sync",
    }
    if atlas_customer:
        atlas_cid = str(atlas_customer.get("id", ""))
        if atlas_cid:
            doc["atlas_customer_id"] = atlas_cid
    try:
        customers_collection.insert_one(doc)
        doc.pop("_id", None)
        return doc
    except Exception:
        return customers_collection.find_one(
            {"email": {"$regex": f"^{re.escape(email_lower)}$", "$options": "i"}},
            {"_id": 0, "customer_id": 1},
        )


# ══════════════════════════════════════════════════════════════
# Conversation → Ticket creation (for NEW conversations)
# ══════════════════════════════════════════════════════════════

def _create_ticket_from_conv(conv: dict, tag_lookup: dict, agent_email_map: dict) -> Optional[str]:
    """Create a new Trinity ticket from an Atlas conversation. Returns ticket_id or None."""
    customer = conv.get("customer") or {}
    assigned_agent = conv.get("assignedAgent") or {}
    stats = conv.get("statistics") or {}
    csat = conv.get("csat") or {}

    raw_tags = conv.get("tags") or []
    mapped_tags = [tag_lookup.get(str(t), str(t)) for t in raw_tags]

    atlas_status = (conv.get("status") or "OPEN").upper()
    atlas_priority = (conv.get("priority") or "NO_PRIORITY").upper()

    customer_email = customer.get("email") or (customer.get("defaultSenders") or {}).get("email")
    created_at = _parse_dt(conv.get("createdAt")) or _parse_dt(conv.get("startedAt")) or datetime.now(timezone.utc)

    # Use Atlas conversation number for ticket_id to maintain parity
    atlas_number = conv.get("number")
    if atlas_number:
        ticket_id = f"TKT-{atlas_number:06d}"
        # Check for collision (shouldn't happen, but safety)
        if tickets_collection.find_one({"ticket_id": ticket_id}):
            ticket_id = generate_ticket_id()
    else:
        ticket_id = generate_ticket_id()

    ticket_doc = {
        "ticket_id": ticket_id,
        "uuid": str(uuid.uuid4()),
        "title": conv.get("subject") or f"Conversation #{conv.get('number', '')}".strip(),
        "description": "",
        "status": STATUS_MAP.get(atlas_status, "todo"),
        "priority": PRIORITY_MAP.get(atlas_priority, "medium"),
        "escalation_level": (conv.get("customFields") or {}).get("support_level", "L1"),
        "order": 0,
        "source": "atlas",
        "tags": mapped_tags,
        "custom_fields": conv.get("customFields") or {},
        "is_starred": False,
        "created_by": "atlas_sync",
        "created_at": created_at,
        "updated_at": created_at,
        "customer_email": customer_email,
        "customer_name": _customer_name(customer),
        "customer_id": None,
        "domain": _extract_domain(customer_email) if customer_email else None,
        "assignee_id": None,
        "team_id": conv.get("assignedTeamId"),
        "atlas_conversation_id": str(conv.get("id", "")),
        "atlas_customer_id": str(conv.get("customerId", "")),
        "atlas_number": conv.get("number"),
        "atlas_status": conv.get("status"),
        "atlas_priority": conv.get("priority"),
        "atlas_assigned_agent_name": _agent_name(assigned_agent),
        "atlas_assigned_agent_email": assigned_agent.get("email"),
        "atlas_assigned_agent_id": conv.get("assignedAgentId") or assigned_agent.get("id"),
        "started_at": _parse_dt(conv.get("startedAt")),
        "closed_at": _parse_dt(conv.get("closedAt")),
        "started_channel": conv.get("startedChannel"),
        "atlas_csat_score": csat.get("score") if csat else None,
        "first_response_time": stats.get("firstResponseTime"),
        "avg_response_time": stats.get("avgResponseTime"),
        "total_resolution_time": stats.get("totalResolutionTime"),
        "last_synced_at": datetime.now(timezone.utc),
        "atlas_assigned_to_zeus": conv.get("assignedToZeus") or False,
    }

    # Link customer
    if customer_email:
        cust = _get_or_create_customer(customer_email, ticket_doc["customer_name"], atlas_customer=customer)
        if cust:
            ticket_doc["customer_id"] = cust.get("customer_id")

    # Map agent
    agent_email = assigned_agent.get("email")
    if agent_email and agent_email.lower() in agent_email_map:
        ticket_doc["assignee_id"] = agent_email_map[agent_email.lower()]

    # Last message snapshot
    last_msg = conv.get("lastMessage")
    if last_msg:
        ticket_doc["last_message_text"] = (_strip_html(last_msg.get("text") or ""))[:200]
        ticket_doc["last_message_at"] = _parse_dt(last_msg.get("sentAt"))
        if not conv.get("subject"):
            ticket_doc["description"] = (_strip_html(last_msg.get("text") or ""))[:5000]

    try:
        tickets_collection.insert_one(ticket_doc)
        ticket_doc.pop("_id", None)
        return ticket_id
    except Exception as e:
        # Duplicate atlas_conversation_id — already exists
        if "duplicate key" in str(e).lower():
            return None
        logger.error(f"[SHADOW] Error creating ticket: {e}")
        return None


# ══════════════════════════════════════════════════════════════
# Message sync (for existing AND new tickets)
# ══════════════════════════════════════════════════════════════

def _sync_messages(atlas_conv_id: str, ticket_id: str) -> int:
    """Fetch messages from Atlas and insert any new ones into Trinity. Returns count of new messages."""
    try:
        all_msgs = []
        cursor = 0
        while True:
            resp = requests.get(
                f"{ATLAS_API}/conversations/{atlas_conv_id}/messages",
                params={"cursor": cursor, "limit": 100},
                headers=_headers(),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", []) if isinstance(data, dict) else data
            all_msgs.extend(items)
            total = data.get("total", 0) if isinstance(data, dict) else len(items)
            if not items or len(all_msgs) >= total:
                break
            cursor += len(items)
    except Exception as e:
        logger.warning(f"[SHADOW] Failed to fetch messages for conv {atlas_conv_id}: {e}")
        return 0

    # Get existing atlas_message_ids for this ticket
    existing_ids = set()
    for doc in messages_collection.find({"ticket_id": ticket_id, "atlas_message_id": {"$exists": True}}, {"atlas_message_id": 1, "_id": 0}):
        existing_ids.add(doc.get("atlas_message_id"))

    new_count = 0
    for msg in all_msgs:
        atlas_msg_id = msg.get("id")
        if not atlas_msg_id or atlas_msg_id in existing_ids:
            continue

        side = (msg.get("side") or "CUSTOMER").upper()
        msg_type = MESSAGE_TYPE_MAP.get(side, "customer_reply")

        agent = msg.get("agent") or {}
        customer = msg.get("customer") or {}

        if side in ("AGENT", "BOT"):
            author_name = _agent_name(agent)
            author_email = agent.get("email")
        else:
            author_name = _customer_name(customer)
            author_email = customer.get("email")

        raw_text = msg.get("text") or ""
        plain_text = _strip_html(raw_text)
        if not plain_text:
            continue

        raw_attachments = msg.get("attachments") or []
        attachments = [
            {"name": a.get("name", ""), "url": a.get("url", ""), "size": a.get("size", 0)}
            for a in raw_attachments if a.get("url")
        ]

        msg_doc = {
            "message_id": f"atlas_msg_{atlas_msg_id}",
            "ticket_id": ticket_id,
            "type": msg_type,
            "content": plain_text[:10000],
            "email_html": raw_text if "<" in raw_text else None,
            "author_id": None,
            "author_name": author_name or "Unknown",
            "author_email": author_email,
            "source": "atlas",
            "mentions": [],
            "attachments": attachments if attachments else None,
            "created_at": _parse_dt(msg.get("sentAt")) or _parse_dt(msg.get("createdAt")) or datetime.now(timezone.utc),
            "atlas_message_id": atlas_msg_id,
            "atlas_conversation_id": atlas_conv_id,
            "atlas_side": msg.get("side"),
            "atlas_channel": msg.get("channel"),
        }

        try:
            messages_collection.insert_one(msg_doc)
            new_count += 1
        except Exception as e:
            if "duplicate key" not in str(e).lower():
                logger.warning(f"[SHADOW] Error inserting message {atlas_msg_id}: {e}")

    return new_count


# ══════════════════════════════════════════════════════════════
# Sidebar (internal notes) sync
# ══════════════════════════════════════════════════════════════

def _sync_sidebars(atlas_conv_id: str, ticket_id: str) -> int:
    """Fetch sidebars from Atlas and insert as internal notes in Trinity."""
    try:
        resp = requests.get(
            f"{ATLAS_API}/conversations/{atlas_conv_id}/sidebars",
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        sidebars = data.get("data", []) if isinstance(data, dict) else data
    except Exception as e:
        logger.warning(f"[SHADOW] Failed to fetch sidebars for conv {atlas_conv_id}: {e}")
        return 0

    if not sidebars:
        return 0

    new_count = 0
    for sidebar in sidebars:
        sidebar_id = sidebar.get("id")
        if not sidebar_id:
            continue

        # Each sidebar may have messages inside it
        sidebar_messages = sidebar.get("messages") or []
        if not sidebar_messages:
            # Try fetching sidebar messages
            try:
                detail_resp = requests.get(
                    f"{ATLAS_API}/conversations/{atlas_conv_id}/sidebars",
                    headers=_headers(),
                    timeout=15,
                )
                # Sidebars endpoint returns list; messages are embedded
            except Exception:
                pass

        for smsg in sidebar_messages:
            smsg_id = f"sidebar_{sidebar_id}_{smsg.get('id', uuid.uuid4().hex[:8])}"

            # Check if already synced
            exists = messages_collection.find_one({"atlas_message_id": smsg_id}, {"_id": 0, "message_id": 1})
            if exists:
                continue

            agent = smsg.get("agent") or smsg.get("user") or {}
            text = _strip_html(smsg.get("text") or smsg.get("content") or "")
            if not text:
                continue

            msg_doc = {
                "message_id": f"msg_{uuid.uuid4().hex[:12]}",
                "ticket_id": ticket_id,
                "type": "note",
                "content": text[:10000],
                "author_id": None,
                "author_name": _agent_name(agent) or "Atlas Agent",
                "author_email": agent.get("email"),
                "source": "atlas_sidebar",
                "is_internal": True,
                "created_at": _parse_dt(smsg.get("createdAt")) or _parse_dt(smsg.get("sentAt")) or datetime.now(timezone.utc),
                "atlas_message_id": smsg_id,
                "atlas_conversation_id": atlas_conv_id,
            }

            try:
                messages_collection.insert_one(msg_doc)
                new_count += 1
            except Exception as e:
                if "duplicate key" not in str(e).lower():
                    logger.warning(f"[SHADOW] Error inserting sidebar msg: {e}")

    return new_count


# ══════════════════════════════════════════════════════════════
# Field sync (status, priority, assignee) with conflict detection
# ══════════════════════════════════════════════════════════════

def _sync_fields(conv: dict, ticket: dict, agent_email_map: dict) -> tuple:
    """
    Compare Atlas conversation fields with Trinity ticket fields.
    Only update if Trinity hasn't been modified since last sync (Trinity precedence).
    Returns (updates_applied: int, conflicts: int).
    """
    atlas_conv_id = str(conv.get("id", ""))
    ticket_id = ticket["ticket_id"]

    last_synced = ticket.get("last_synced_at")
    trinity_updated = ticket.get("updated_at")

    # If Trinity was modified after last sync, skip most field updates (Trinity precedence)
    # BUT always propagate assignment changes from Atlas (Atlas owns assignments)
    if last_synced and trinity_updated and trinity_updated > last_synced:
        # Trinity was modified independently — don't overwrite status/priority/etc.
        # Still update atlas_ metadata fields, last_synced_at, AND assignment
        assigned_agent = conv.get("assignedAgent") or {}
        metadata_update = {
            "atlas_status": conv.get("status"),
            "atlas_priority": conv.get("priority"),
            "atlas_assigned_agent_name": _agent_name(assigned_agent),
            "atlas_assigned_agent_email": assigned_agent.get("email"),
            "last_synced_at": datetime.now(timezone.utc),
        }
        # Always propagate assignment changes even during conflict
        agent_email = assigned_agent.get("email")
        if agent_email:
            new_assignee = agent_email_map.get(agent_email.lower())
            if new_assignee and ticket.get("assignee_id") != new_assignee:
                metadata_update["assignee_id"] = new_assignee
        elif ticket.get("assignee_id"):
            # Atlas unassigned the agent — clear Trinity assignment
            metadata_update["assignee_id"] = None

        tickets_collection.update_one({"ticket_id": ticket_id}, {"$set": metadata_update})
        real = sum(1 for k in metadata_update if k == "assignee_id")
        return real, 1 if real == 0 else 0

    # Build field updates
    updates = {}
    atlas_status = (conv.get("status") or "OPEN").upper()
    atlas_priority = (conv.get("priority") or "NO_PRIORITY").upper()
    assigned_agent = conv.get("assignedAgent") or {}

    mapped_status = STATUS_MAP.get(atlas_status, "todo")
    if ticket.get("status") != mapped_status:
        updates["status"] = mapped_status

    mapped_priority = PRIORITY_MAP.get(atlas_priority, "medium")
    if ticket.get("priority") != mapped_priority:
        updates["priority"] = mapped_priority

    agent_email = assigned_agent.get("email")
    if agent_email:
        new_assignee = agent_email_map.get(agent_email.lower())
        if new_assignee and ticket.get("assignee_id") != new_assignee:
            updates["assignee_id"] = new_assignee
    elif ticket.get("assignee_id"):
        # Atlas unassigned the agent — clear Trinity assignment
        updates["assignee_id"] = None

    # Tags
    raw_tags = conv.get("tags") or []
    if raw_tags:
        # We'd need tag_lookup here, skip for now if no changes detected
        pass

    # Custom fields from Atlas
    custom_fields = conv.get("customFields")
    if custom_fields and custom_fields != ticket.get("custom_fields"):
        updates["custom_fields"] = custom_fields
        # Sync escalation_level from support_level custom field
        support_level = custom_fields.get("support_level")
        if support_level and ticket.get("escalation_level") != support_level:
            updates["escalation_level"] = support_level

    # Closed at
    closed_at = _parse_dt(conv.get("closedAt"))
    if closed_at and not ticket.get("closed_at"):
        updates["closed_at"] = closed_at
        updates["resolved_at"] = closed_at

    # CSAT
    csat = conv.get("csat") or {}
    if csat.get("score") and not ticket.get("atlas_csat_score"):
        updates["atlas_csat_score"] = csat.get("score")
        updates["atlas_csat_comment"] = csat.get("comment")

    # Always update metadata
    updates["atlas_status"] = conv.get("status")
    updates["atlas_priority"] = conv.get("priority")
    updates["atlas_assigned_agent_name"] = _agent_name(assigned_agent)
    updates["atlas_assigned_agent_email"] = assigned_agent.get("email")
    updates["atlas_assigned_to_zeus"] = conv.get("assignedToZeus") or False
    updates["last_synced_at"] = datetime.now(timezone.utc)

    # Stats
    stats = conv.get("statistics") or {}
    if stats.get("firstResponseTime"):
        updates["first_response_time"] = stats["firstResponseTime"]
    if stats.get("avgResponseTime"):
        updates["avg_response_time"] = stats["avgResponseTime"]
    if stats.get("totalResolutionTime"):
        updates["total_resolution_time"] = stats["totalResolutionTime"]

    if updates:
        tickets_collection.update_one({"ticket_id": ticket_id}, {"$set": updates})

    # Count real field changes (excluding metadata-only updates)
    real_changes = sum(1 for k in updates if k not in ("atlas_status", "atlas_priority", "atlas_assigned_agent_name", "atlas_assigned_agent_email", "last_synced_at", "first_response_time", "avg_response_time", "total_resolution_time"))
    return real_changes, 0


# ══════════════════════════════════════════════════════════════
# Main Sync Cycle
# ══════════════════════════════════════════════════════════════

def _run_sync_cycle(state: dict, tag_lookup: dict, agent_email_map: dict) -> dict:
    """
    Run a single sync cycle: fetch recent Atlas conversations and sync.
    Returns stats dict.
    """
    lookback = state.get("lookback_minutes", DEFAULT_LOOKBACK_MINUTES)
    start_date = (datetime.now(timezone.utc) - timedelta(minutes=lookback)).strftime("%Y-%m-%dT%H:%M:%SZ")

    cycle_stats = {
        "conversations_checked": 0,
        "new_tickets": 0,
        "messages_synced": 0,
        "sidebars_synced": 0,
        "field_updates": 0,
        "conflicts": 0,
    }

    cursor = 0
    while not _stop_event.is_set():
        try:
            resp = requests.get(
                f"{ATLAS_API}/conversations",
                params={"startDate": start_date, "cursor": cursor, "limit": 100},
                headers=_headers(),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            convs = data.get("data", [])
            total = data.get("total", 0)

            if not convs:
                break

            for conv in convs:
                if _stop_event.is_set():
                    break

                atlas_conv_id = str(conv.get("id", ""))
                if not atlas_conv_id:
                    continue

                cycle_stats["conversations_checked"] += 1

                # Check if ticket already exists in Trinity
                existing_ticket = tickets_collection.find_one(
                    {"atlas_conversation_id": atlas_conv_id},
                    {"_id": 0, "ticket_id": 1, "status": 1, "priority": 1,
                     "assignee_id": 1, "updated_at": 1, "last_synced_at": 1,
                     "custom_fields": 1, "closed_at": 1, "atlas_csat_score": 1},
                )

                if existing_ticket:
                    # Existing ticket — sync new messages + field changes
                    ticket_id = existing_ticket["ticket_id"]

                    new_msgs = _sync_messages(atlas_conv_id, ticket_id)
                    cycle_stats["messages_synced"] += new_msgs

                    new_sidebars = _sync_sidebars(atlas_conv_id, ticket_id)
                    cycle_stats["sidebars_synced"] += new_sidebars

                    field_updates, conflicts = _sync_fields(conv, existing_ticket, agent_email_map)
                    cycle_stats["field_updates"] += field_updates
                    cycle_stats["conflicts"] += conflicts

                    # Update ticket timestamp if new content was synced
                    if new_msgs > 0 or new_sidebars > 0:
                        tickets_collection.update_one(
                            {"ticket_id": ticket_id},
                            {"$set": {"updated_at": datetime.now(timezone.utc)}},
                        )
                else:
                    # New conversation — check if IMAP already created a ticket for this email
                    customer_email = ((conv.get("customer") or {}).get("email") or "").lower().strip()
                    conv_title = (conv.get("title") or conv.get("subject") or "").strip()
                    imap_match = None
                    if customer_email and conv_title:
                        imap_match = tickets_collection.find_one(
                            {
                                "atlas_conversation_id": {"$exists": False},
                                "customer_email": customer_email,
                                "title": conv_title,
                            },
                            {"_id": 0, "ticket_id": 1},
                        )

                    if imap_match:
                        # Link IMAP ticket to Atlas conversation
                        ticket_id = imap_match["ticket_id"]
                        atlas_number = conv.get("number")
                        new_ticket_id = f"TKT-{atlas_number:06d}" if atlas_number else ticket_id
                        link_fields = {
                            "atlas_conversation_id": atlas_conv_id,
                            "atlas_number": atlas_number,
                        }
                        # Rename ticket_id to match Atlas number if possible
                        if new_ticket_id != ticket_id and not tickets_collection.find_one({"ticket_id": new_ticket_id}):
                            link_fields["ticket_id"] = new_ticket_id
                            # Update references
                            for ref_col in ["messages", "email_threads", "ticket_changelog",
                                            "notifications", "email_replies", "csat_tokens", "csat_responses"]:
                                db[ref_col].update_many(
                                    {"ticket_id": ticket_id},
                                    {"$set": {"ticket_id": new_ticket_id}},
                                )
                            ticket_id = new_ticket_id
                        tickets_collection.update_one(
                            {"ticket_id": imap_match["ticket_id"]},
                            {"$set": link_fields},
                        )
                        logger.info(f"[SYNC] Linked IMAP ticket {ticket_id} to Atlas conv {atlas_conv_id}")
                        cycle_stats["new_tickets"] += 1
                    else:
                        # No IMAP match — create new ticket
                        ticket_id = _create_ticket_from_conv(conv, tag_lookup, agent_email_map)

                    if ticket_id:
                        if not imap_match:
                            cycle_stats["new_tickets"] += 1
                        # Sync messages for the new/linked ticket
                        new_msgs = _sync_messages(atlas_conv_id, ticket_id)
                        cycle_stats["messages_synced"] += new_msgs
                        # Sync sidebars
                        new_sidebars = _sync_sidebars(atlas_conv_id, ticket_id)
                        cycle_stats["sidebars_synced"] += new_sidebars

                # Brief delay to avoid hammering Atlas API
                time.sleep(0.2)

            cursor += len(convs)
            if cursor >= total:
                break

        except requests.Timeout:
            logger.warning(f"[SHADOW] Timeout at cursor {cursor}, retrying...")
            time.sleep(5)
            continue
        except Exception as e:
            logger.error(f"[SHADOW] Error in sync cycle at cursor {cursor}: {e}")
            break

    return cycle_stats


# ══════════════════════════════════════════════════════════════
# Active Tickets Re-check (catch changes to older conversations)
# ══════════════════════════════════════════════════════════════

def _recheck_active_tickets(agent_email_map: dict, batch_size: int = 50) -> dict:
    """
    Re-check Atlas-origin tickets for new messages AND field updates.
    This catches updates to conversations that fall outside the lookback window.
    Processes a batch each cycle to spread the load.
    """
    stats = {"messages_synced": 0, "checked": 0, "field_updates": 0}

    # Main batch: active (non-closed) tickets, oldest-synced first
    active_tickets = list(tickets_collection.find(
        {
            "atlas_conversation_id": {"$exists": True, "$ne": None},
            "status": {"$nin": ["closed"]},
        },
        {"_id": 0, "ticket_id": 1, "atlas_conversation_id": 1, "last_synced_at": 1},
    ).sort("last_synced_at", 1).limit(batch_size))

    # Small batch: recently-closed tickets that haven't been synced in a while
    # (catches Atlas reopening a closed ticket)
    stale_threshold = datetime.now(timezone.utc) - timedelta(hours=2)
    closed_batch = list(tickets_collection.find(
        {
            "atlas_conversation_id": {"$exists": True, "$ne": None},
            "status": "closed",
            "last_synced_at": {"$lt": stale_threshold},
        },
        {"_id": 0, "ticket_id": 1, "atlas_conversation_id": 1, "last_synced_at": 1},
    ).sort("last_synced_at", 1).limit(5))

    all_tickets = active_tickets + closed_batch

    for ticket in all_tickets:
        if _stop_event.is_set():
            break

        atlas_conv_id = ticket["atlas_conversation_id"]
        ticket_id = ticket["ticket_id"]

        # Sync messages
        new_msgs = _sync_messages(atlas_conv_id, ticket_id)
        stats["messages_synced"] += new_msgs
        stats["checked"] += 1

        # Fetch conversation from Atlas to sync field updates
        try:
            resp = requests.get(
                f"{ATLAS_API}/conversations/{atlas_conv_id}",
                headers=_headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                conv = resp.json()
                full_ticket = tickets_collection.find_one(
                    {"ticket_id": ticket_id}, {"_id": 0}
                )
                if full_ticket:
                    field_changes, _ = _sync_fields(conv, full_ticket, agent_email_map)
                    stats["field_updates"] += field_changes
        except Exception as e:
            logger.debug(f"[SHADOW] Recheck field sync error for {ticket_id}: {e}")

        # Update last_synced_at even if no changes
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": {"last_synced_at": datetime.now(timezone.utc)}},
        )

        if new_msgs > 0:
            tickets_collection.update_one(
                {"ticket_id": ticket_id},
                {"$set": {"updated_at": datetime.now(timezone.utc)}},
            )

        time.sleep(0.2)

    return stats


# ══════════════════════════════════════════════════════════════
# Daemon Loop
# ══════════════════════════════════════════════════════════════

def _sync_loop():
    """Main daemon loop — runs continuously until stopped."""
    logger.info("[SHADOW] Sync daemon started")

    state = _get_state()
    state["status"] = "running"
    state["started_at"] = datetime.now(timezone.utc)
    _save_state(state)

    # Fetch tags once per startup
    tag_lookup = _fetch_tags()
    agent_email_map = _build_agent_email_map()
    logger.info(f"[SHADOW] Loaded {len(tag_lookup)} tags, {len(agent_email_map)} agent mappings")

    # Refresh agent map periodically
    last_agent_refresh = time.time()
    AGENT_REFRESH_INTERVAL = 300  # 5 minutes

    while not _stop_event.is_set():
        try:
            # Refresh agent map periodically
            if time.time() - last_agent_refresh > AGENT_REFRESH_INTERVAL:
                agent_email_map = _build_agent_email_map()
                last_agent_refresh = time.time()

            state = _get_state()

            # Phase 1: Sync recent conversations (new + updated within lookback window)
            cycle_stats = _run_sync_cycle(state, tag_lookup, agent_email_map)

            # Phase 2: Re-check active (non-closed) Atlas tickets for new messages
            recheck_stats = _recheck_active_tickets(agent_email_map)

            # Update state
            state = _get_state()
            state["cycles_completed"] = state.get("cycles_completed", 0) + 1
            state["conversations_checked"] = state.get("conversations_checked", 0) + cycle_stats["conversations_checked"]
            state["new_tickets_created"] = state.get("new_tickets_created", 0) + cycle_stats["new_tickets"]
            state["messages_synced"] = state.get("messages_synced", 0) + cycle_stats["messages_synced"] + recheck_stats["messages_synced"]
            state["sidebars_synced"] = state.get("sidebars_synced", 0) + cycle_stats["sidebars_synced"]
            state["field_updates"] = state.get("field_updates", 0) + cycle_stats["field_updates"] + recheck_stats.get("field_updates", 0)
            state["conflicts_skipped"] = state.get("conflicts_skipped", 0) + cycle_stats["conflicts"]
            state["last_sync_at"] = datetime.now(timezone.utc)
            state["status"] = "running"
            _save_state(state)

            total_new = cycle_stats["new_tickets"] + cycle_stats["messages_synced"] + recheck_stats["messages_synced"] + cycle_stats["sidebars_synced"] + recheck_stats.get("field_updates", 0)
            if total_new > 0:
                logger.info(
                    f"[SHADOW] Cycle #{state['cycles_completed']}: "
                    f"checked={cycle_stats['conversations_checked']} new_tickets={cycle_stats['new_tickets']} "
                    f"msgs={cycle_stats['messages_synced']}+{recheck_stats['messages_synced']} "
                    f"sidebars={cycle_stats['sidebars_synced']} field_updates={cycle_stats['field_updates']}+{recheck_stats.get('field_updates', 0)} "
                    f"conflicts={cycle_stats['conflicts']} recheck={recheck_stats['checked']}"
                )
            else:
                logger.debug(f"[SHADOW] Cycle #{state['cycles_completed']}: no changes")

        except Exception as e:
            logger.error(f"[SHADOW] Error in sync loop: {e}")
            state = _get_state()
            errors = state.get("errors", [])
            errors.append({"time": datetime.now(timezone.utc).isoformat(), "error": str(e)})
            state["errors"] = errors[-50:]
            _save_state(state)

        # Wait for next cycle
        poll_interval = _get_state().get("poll_interval", DEFAULT_POLL_INTERVAL)
        _stop_event.wait(poll_interval)

    # Stopped
    state = _get_state()
    state["status"] = "stopped"
    _save_state(state)
    logger.info("[SHADOW] Sync daemon stopped")


# ══════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════

def start_sync() -> dict:
    """Start the shadow sync daemon."""
    global _worker_thread
    if not ATLAS_KEY:
        return {"error": "No ATLAS_API_KEY configured"}
    if _worker_thread and _worker_thread.is_alive():
        return {"message": "Sync is already running", "status": "running"}
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_sync_loop, daemon=True, name="atlas_shadow_sync")
    _worker_thread.start()
    return {"message": "Shadow sync started", "status": "running"}


def stop_sync() -> dict:
    """Stop the shadow sync daemon."""
    global _worker_thread
    if not _worker_thread or not _worker_thread.is_alive():
        return {"message": "Sync is not running", "status": "stopped"}
    _stop_event.set()
    _worker_thread.join(timeout=10)
    _worker_thread = None
    state = _get_state()
    state["status"] = "stopped"
    _save_state(state)
    return {"message": "Shadow sync stopped", "status": "stopped"}


def update_config(poll_interval: int = None, lookback_minutes: int = None) -> dict:
    """Update sync configuration. Changes take effect on next cycle."""
    state = _get_state()
    if poll_interval is not None:
        state["poll_interval"] = max(10, min(poll_interval, 600))
    if lookback_minutes is not None:
        state["lookback_minutes"] = max(5, min(lookback_minutes, 120))
    _save_state(state)
    return {"message": "Config updated", "poll_interval": state["poll_interval"], "lookback_minutes": state["lookback_minutes"]}


def auto_start_on_boot():
    """Called on server startup. Auto-starts the sync daemon if Atlas key is configured."""
    if not ATLAS_KEY:
        logger.info("[SHADOW] No ATLAS_API_KEY — shadow sync disabled")
        return
    logger.info("[SHADOW] Auto-starting shadow sync on boot...")
    start_sync()
