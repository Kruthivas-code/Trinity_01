"""
Unified Atlas Sync Engine — 5-Layer Architecture
=================================================
Consolidates all Atlas↔Trinity data synchronization into a single service.

Layer 1: Webhooks    — Real-time event processing (called by HTTP handler)
Layer 2: Poller      — Safety-net polling for recent conversations (every 60s)
Layer 3: Full Crawl  — Historical reconciliation walk (batch per cycle)
Layer 4: Push-back   — Trinity → Atlas field/assignment sync
Layer 5: Sweep       — Separate module (ticket_sweep.py)

State is persisted in MongoDB (`atlas_backfill_state`, _type="shadow").
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

logger = logging.getLogger("atlas_sync")

# ══════════════════════════════════════════════════════════════
# Constants & Field Mappings
# ══════════════════════════════════════════════════════════════

ATLAS_API = "https://api.atlas.so/v1"
ATLAS_KEY = os.environ.get("ATLAS_API_KEY", "")

# State collection (shared with other services like zeus_cleanup, attachment_migration)
_state_col = db.atlas_backfill_state

# Thread control
_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

# Defaults
DEFAULT_POLL_INTERVAL = 30       # seconds between sync cycles (was 60)
DEFAULT_LOOKBACK_MINUTES = 60    # how far back to look for new conversations
FULL_SYNC_WINDOW_DAYS = 90       # covers long-tail open tickets
HOT_BATCH_SIZE = 500             # conversations per hot-crawl batch (active tickets)
COLD_BATCH_SIZE = 500            # conversations per cold-crawl batch (all tickets)
FULL_SYNC_BATCH_SIZE = COLD_BATCH_SIZE  # backward compat alias
HOT_STATUSES = ["OPEN", "PENDING", "SNOOZED"]  # statuses for hot crawl

# Atlas → Trinity field mappings
STATUS_MAP = {
    "OPEN": "todo",
    "CLOSED": "closed",
    "SNOOZED": "waiting",
    "PENDING": "waiting",
    "IN_PROGRESS": "todo",
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

# Trinity → Atlas reverse mappings (Layer 4: Push-back)
_REVERSE_STATUS_MAP = {
    "todo": "OPEN",
    "in_progress": "OPEN",
    "waiting": "SNOOZED",
    "closed": "CLOSED",
}

_REVERSE_PRIORITY_MAP = {
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "urgent": "URGENT",
}


# ══════════════════════════════════════════════════════════════
# Shared Lookup Cache
# ══════════════════════════════════════════════════════════════

_lookup_cache = {
    "agent_email_map": {},
    "tag_lookup": {},
    "agent_last_refresh": 0,
    "tag_last_refresh": 0,
}
_AGENT_CACHE_TTL = 300   # 5 minutes
_TAG_CACHE_TTL = 600     # 10 minutes


def _get_cached_agent_map() -> dict:
    """Get agent email→user_id map, refreshing if stale."""
    now = time.time()
    if now - _lookup_cache["agent_last_refresh"] > _AGENT_CACHE_TTL:
        _lookup_cache["agent_email_map"] = _build_agent_email_map()
        _lookup_cache["agent_last_refresh"] = now
    return _lookup_cache["agent_email_map"]


def _get_cached_tag_lookup() -> dict:
    """Get tag UUID→name map, refreshing if stale."""
    now = time.time()
    if now - _lookup_cache["tag_last_refresh"] > _TAG_CACHE_TTL:
        _lookup_cache["tag_lookup"] = _fetch_tags()
        _lookup_cache["tag_last_refresh"] = now
    return _lookup_cache["tag_lookup"]


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
    """Fetch all tags from Atlas. Returns {uuid: label_name}."""
    try:
        resp = requests.get(f"{ATLAS_API}/tags", headers=_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        tags = data if isinstance(data, list) else data.get("data", data.get("tags", []))
        return {str(t.get("id", "")): (t.get("label") or t.get("name") or str(t.get("id", ""))) for t in tags if t.get("id")}
    except Exception as e:
        logger.warning(f"[SYNC] Failed to fetch tags: {e}")
        return {}


def _build_agent_email_map() -> dict:
    """Build email→user_id map from Trinity users."""
    all_users = list(users_collection.find({}, {"_id": 0, "user_id": 1, "email": 1}))
    return {u["email"].lower(): u["user_id"] for u in all_users if u.get("email")}


def _fetch_atlas_users() -> list:
    """Fetch all users (agents) from Atlas API."""
    try:
        resp = requests.get(f"{ATLAS_API}/users", headers=_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", data) if isinstance(data, dict) else data
    except Exception as e:
        logger.error(f"Failed to fetch Atlas users: {e}")
        return []


def _fetch_conversation(conv_id: str) -> dict:
    """Fetch full conversation details from Atlas API."""
    try:
        resp = requests.get(
            f"{ATLAS_API}/conversations/{conv_id}",
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"[SYNC] Failed to fetch conversation {conv_id}: {e}")
        return {}


# Atlas agent ID cache (for push-back layer)
_atlas_agent_cache = {"map": {}, "last_refresh": None}
_ATLAS_AGENT_CACHE_TTL = 300  # 5 minutes


def _get_atlas_agent_id_by_email(email: str) -> Optional[str]:
    """Look up Atlas agent ID by email. Uses a cached mapping."""
    now = datetime.now(timezone.utc)
    if (
        not _atlas_agent_cache["last_refresh"]
        or (now - _atlas_agent_cache["last_refresh"]).total_seconds() > _ATLAS_AGENT_CACHE_TTL
    ):
        atlas_users = _fetch_atlas_users()
        _atlas_agent_cache["map"] = {
            u["email"].lower(): u["id"]
            for u in atlas_users
            if u.get("email") and u.get("id")
        }
        _atlas_agent_cache["last_refresh"] = now
    return _atlas_agent_cache["map"].get(email.lower()) if email else None


# Tag name→UUID reverse cache (for push-back layer)
_tag_name_to_id_cache = {"map": {}, "last_refresh": None}
_TAG_NAME_CACHE_TTL = 600  # 10 minutes


def _get_tag_name_to_id_map() -> dict:
    """Get or refresh the tag name→UUID reverse lookup."""
    now = datetime.now(timezone.utc)
    if (
        not _tag_name_to_id_cache["last_refresh"]
        or (now - _tag_name_to_id_cache["last_refresh"]).total_seconds() > _TAG_NAME_CACHE_TTL
    ):
        tags = _fetch_tags()
        _tag_name_to_id_cache["map"] = {name.lower(): uid for uid, name in tags.items()}
        _tag_name_to_id_cache["last_refresh"] = now
    return _tag_name_to_id_cache["map"]


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
            "webhook_events_processed": 0,
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
    if len(state.get("errors", [])) > 20:
        state["errors"] = state["errors"][-20:]
    return state


# ══════════════════════════════════════════════════════════════
# Shared Sync Logic: Customer
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
# Shared Sync Logic: Ticket Creation
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

    atlas_number = conv.get("number")
    if atlas_number:
        ticket_id = f"TKT-{atlas_number}"
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

    if customer_email:
        cust = _get_or_create_customer(customer_email, ticket_doc["customer_name"], atlas_customer=customer)
        if cust:
            ticket_doc["customer_id"] = cust.get("customer_id")

    agent_email = assigned_agent.get("email")
    if agent_email and agent_email.lower() in agent_email_map:
        ticket_doc["assignee_id"] = agent_email_map[agent_email.lower()]

    last_msg = conv.get("lastMessage")
    if last_msg:
        ticket_doc["last_message_text"] = (_strip_html(last_msg.get("text") or ""))[:200]
        ticket_doc["last_message_at"] = _parse_dt(last_msg.get("sentAt"))
        if not conv.get("subject"):
            ticket_doc["description"] = (_strip_html(last_msg.get("text") or ""))[:5000]

    try:
        tickets_collection.insert_one(ticket_doc)
        ticket_doc.pop("_id", None)
        try:
            from ticket_helpers import run_routing_rules
            if not ticket_doc.get("atlas_assigned_to_zeus"):
                run_routing_rules(ticket_doc)
        except Exception as e:
            logger.warning(f"[SYNC] Routing rules failed for {ticket_id}: {e}")
        return ticket_id
    except Exception as e:
        if "duplicate key" in str(e).lower():
            return None
        logger.error(f"[SYNC] Error creating ticket: {e}")
        return None


def _create_or_link_ticket(conv: dict, tag_lookup: dict, agent_email_map: dict) -> Optional[str]:
    """
    For a new Atlas conversation, either link it to an existing IMAP ticket
    or create a new Trinity ticket. Returns ticket_id or None.
    """
    atlas_conv_id = str(conv.get("id", ""))
    atlas_number = conv.get("number")
    customer_email = ((conv.get("customer") or {}).get("email") or "").lower().strip()
    conv_title = (conv.get("title") or conv.get("subject") or "").strip()

    # Match 1: Try by ticket_id (TKT-{number})
    if atlas_number:
        expected_tid = f"TKT-{atlas_number}"
        existing_by_id = tickets_collection.find_one(
            {"ticket_id": expected_tid, "$or": [
                {"atlas_conversation_id": None},
                {"atlas_conversation_id": {"$exists": False}},
            ]},
            {"_id": 0, "ticket_id": 1},
        )
        if existing_by_id:
            tickets_collection.update_one(
                {"ticket_id": expected_tid},
                {"$set": {
                    "atlas_conversation_id": atlas_conv_id,
                    "atlas_number": atlas_number,
                }},
            )
            logger.info(f"[SYNC] Linked ticket {expected_tid} to Atlas conv {atlas_conv_id} (by ticket_id)")
            return expected_tid

    # Match 2: Try by customer_email + title
    if customer_email and conv_title:
        imap_match = tickets_collection.find_one(
            {
                "$or": [
                    {"atlas_conversation_id": None},
                    {"atlas_conversation_id": {"$exists": False}},
                ],
                "customer_email": customer_email,
                "title": conv_title,
            },
            {"_id": 0, "ticket_id": 1},
        )
        if imap_match:
            ticket_id = imap_match["ticket_id"]
            new_ticket_id = f"TKT-{atlas_number}" if atlas_number else ticket_id
            link_fields = {
                "atlas_conversation_id": atlas_conv_id,
                "atlas_number": atlas_number,
            }
            if new_ticket_id != ticket_id and not tickets_collection.find_one({"ticket_id": new_ticket_id}):
                link_fields["ticket_id"] = new_ticket_id
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
            logger.info(f"[SYNC] Linked IMAP ticket {ticket_id} to Atlas conv {atlas_conv_id} (by email+title)")
            return ticket_id

    return _create_ticket_from_conv(conv, tag_lookup, agent_email_map)


# ══════════════════════════════════════════════════════════════
# Shared Sync Logic: Messages
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
        logger.warning(f"[SYNC] Failed to fetch messages for conv {atlas_conv_id}: {e}")
        return 0

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
                logger.warning(f"[SYNC] Error inserting message {atlas_msg_id}: {e}")

    return new_count


# ══════════════════════════════════════════════════════════════
# Shared Sync Logic: Sidebars (Internal Notes)
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
        logger.warning(f"[SYNC] Failed to fetch sidebars for conv {atlas_conv_id}: {e}")
        return 0

    if not sidebars:
        return 0

    new_count = 0
    for sidebar in sidebars:
        sidebar_id = sidebar.get("id")
        if not sidebar_id:
            continue

        sidebar_messages = sidebar.get("messages") or []
        for smsg in sidebar_messages:
            smsg_id = f"sidebar_{sidebar_id}_{smsg.get('id', uuid.uuid4().hex[:8])}"

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
                    logger.warning(f"[SYNC] Error inserting sidebar msg: {e}")

    return new_count


# ══════════════════════════════════════════════════════════════
# Shared Sync Logic: Field Sync (Atlas → Trinity)
# ══════════════════════════════════════════════════════════════

def _sync_fields(conv: dict, ticket: dict, agent_email_map: dict, tag_lookup: dict = None) -> tuple:
    """
    Sync Atlas conversation fields into Trinity ticket.
    Atlas is the source of truth for status, priority, tags, and metadata.
    Only assignment is protected (5-min window after Trinity-side change).
    Returns (updates_applied: int, conflicts: int).
    """
    ticket_id = ticket["ticket_id"]

    # Check if Trinity recently made an assignment change (protect for 5 min)
    trinity_assigned_at = ticket.get("trinity_assigned_at")
    assignment_protected = False
    if trinity_assigned_at:
        if trinity_assigned_at.tzinfo is None:
            trinity_assigned_at = trinity_assigned_at.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - trinity_assigned_at).total_seconds()
        if age < 300:
            assignment_protected = True

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

    # Assignment sync (skip if Trinity recently made an assignment)
    if not assignment_protected:
        agent_email = assigned_agent.get("email")
        if agent_email:
            new_assignee = agent_email_map.get(agent_email.lower())
            if new_assignee and ticket.get("assignee_id") != new_assignee:
                updates["assignee_id"] = new_assignee
        elif ticket.get("assignee_id"):
            updates["assignee_id"] = None
    else:
        logger.debug(f"[SYNC] Skipping assignment overwrite for {ticket_id} — Trinity assignment protected")

    # Tags
    raw_tags = conv.get("tags") or []
    if raw_tags and tag_lookup:
        mapped_tags = [tag_lookup.get(str(t), str(t)) for t in raw_tags]
        if sorted(mapped_tags) != sorted(ticket.get("tags") or []):
            updates["tags"] = mapped_tags

    # Custom fields
    custom_fields = conv.get("customFields")
    if custom_fields and custom_fields != ticket.get("custom_fields"):
        updates["custom_fields"] = custom_fields
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

    real_changes = sum(1 for k in updates if k not in (
        "atlas_status", "atlas_priority", "atlas_assigned_agent_name",
        "atlas_assigned_agent_email", "last_synced_at",
        "first_response_time", "avg_response_time", "total_resolution_time",
    ))
    return real_changes, 0


# ══════════════════════════════════════════════════════════════
# Layer 1: Webhook Handlers
# ══════════════════════════════════════════════════════════════

def _extract_conversation_id(payload: dict) -> str:
    """Extract conversation ID from various webhook payload shapes."""
    for key in ("conversationId", "conversation_id", "id"):
        if key in payload and isinstance(payload[key], str):
            return payload[key]
    for wrapper in ("conversation", "data", "payload"):
        nested = payload.get(wrapper)
        if isinstance(nested, dict):
            for key in ("id", "conversationId", "conversation_id"):
                if key in nested:
                    return str(nested[key])
    return ""


def _webhook_conversation_created(payload: dict):
    """Handle new conversation — create ticket + sync messages."""
    agent_map = _get_cached_agent_map()
    tag_map = _get_cached_tag_lookup()
    conv_id = _extract_conversation_id(payload)

    if conv_id and tickets_collection.find_one({"atlas_conversation_id": conv_id}, {"_id": 0, "ticket_id": 1}):
        logger.info(f"[WEBHOOK] Conversation {conv_id} already exists, skipping create")
        return

    conv = payload.get("conversation") or payload.get("data") or {}
    if not conv.get("id") and conv_id:
        conv = _fetch_conversation(conv_id)

    if not conv.get("id"):
        logger.warning("[WEBHOOK] Could not get conversation data for created event")
        return

    ticket_id = _create_ticket_from_conv(conv, tag_map, agent_map)
    if ticket_id:
        atlas_id = str(conv.get("id", ""))
        _sync_messages(atlas_id, ticket_id)
        _sync_sidebars(atlas_id, ticket_id)
        logger.info(f"[WEBHOOK] Created ticket {ticket_id} from conversation #{conv.get('number')}")


def _webhook_field_change(payload: dict, change_type: str):
    """Handle status/agent/priority changes — update existing ticket fields."""
    agent_map = _get_cached_agent_map()
    conv_id = _extract_conversation_id(payload)

    if not conv_id:
        logger.warning(f"[WEBHOOK] No conversation ID in {change_type} event")
        return

    ticket = tickets_collection.find_one(
        {"atlas_conversation_id": conv_id},
        {"_id": 0},
    )

    if not ticket:
        logger.info(f"[WEBHOOK] Ticket for {conv_id} not found, creating from {change_type} event")
        _webhook_conversation_created(payload)
        return

    conv = _fetch_conversation(conv_id)
    if not conv.get("id"):
        return

    updates_applied, conflicts = _sync_fields(conv, ticket, agent_map)

    tickets_collection.update_one(
        {"ticket_id": ticket["ticket_id"]},
        {"$set": {"updated_at": datetime.now(timezone.utc)}},
    )

    logger.info(f"[WEBHOOK] {change_type}: ticket {ticket['ticket_id']} — {updates_applied} updates, {conflicts} conflicts")


def _webhook_new_message(payload: dict):
    """Handle new message — sync messages + update ticket timestamps + sync fields."""
    conv_id = _extract_conversation_id(payload)
    if not conv_id:
        logger.warning("[WEBHOOK] No conversation ID in new message event")
        return

    ticket = tickets_collection.find_one(
        {"atlas_conversation_id": conv_id},
        {"_id": 0},
    )

    if not ticket:
        logger.info(f"[WEBHOOK] Ticket for {conv_id} not found, creating from message event")
        _webhook_conversation_created(payload)
        return

    ticket_id = ticket["ticket_id"]
    new_msgs = _sync_messages(conv_id, ticket_id)

    now = datetime.now(timezone.utc)
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"updated_at": now, "last_message_at": now}},
    )

    # Also sync field changes (status, priority, assignee may have changed)
    agent_map = _get_cached_agent_map()
    conv = _fetch_conversation(conv_id)
    if conv.get("id"):
        _sync_fields(conv, ticket, agent_map)

    if new_msgs:
        logger.info(f"[WEBHOOK] Synced {new_msgs} new messages for {ticket_id}")
    else:
        logger.debug(f"[WEBHOOK] Message event for {ticket_id}, no new messages found")


def _webhook_tags_changed(payload: dict):
    """Handle tag changes — update ticket tags + sync all fields."""
    conv_id = _extract_conversation_id(payload)
    if not conv_id:
        return

    ticket = tickets_collection.find_one(
        {"atlas_conversation_id": conv_id},
        {"_id": 0},
    )
    if not ticket:
        _webhook_conversation_created(payload)
        return

    conv = _fetch_conversation(conv_id)
    if not conv.get("id"):
        return

    agent_map = _get_cached_agent_map()
    tag_map = _get_cached_tag_lookup()

    raw_tags = conv.get("tags") or []
    mapped_tags = [tag_map.get(str(t), str(t)) for t in raw_tags]
    tickets_collection.update_one(
        {"ticket_id": ticket["ticket_id"]},
        {"$set": {"tags": mapped_tags, "updated_at": datetime.now(timezone.utc)}},
    )
    logger.info(f"[WEBHOOK] Updated tags for {ticket['ticket_id']}: {mapped_tags}")

    _sync_fields(conv, ticket, agent_map)


# Webhook event type → handler mapping
_WEBHOOK_HANDLERS = {
    "conversation.created": _webhook_conversation_created,
    "conversation_created": _webhook_conversation_created,
    "conversation.agent_changed": lambda p: _webhook_field_change(p, "agent_changed"),
    "conversation_agent_changed": lambda p: _webhook_field_change(p, "agent_changed"),
    "conversation.status_changed": lambda p: _webhook_field_change(p, "status_changed"),
    "conversation_status_changed": lambda p: _webhook_field_change(p, "status_changed"),
    "conversation.priority_changed": lambda p: _webhook_field_change(p, "priority_changed"),
    "conversation_priority_changed": lambda p: _webhook_field_change(p, "priority_changed"),
    "conversation.tags_changed": _webhook_tags_changed,
    "conversation_tags_changed": _webhook_tags_changed,
    "message.received": _webhook_new_message,
    "new_message_received": _webhook_new_message,
    "message.created": _webhook_new_message,
    "sidebar.created": lambda p: _webhook_field_change(p, "sidebar_created"),
    "sidebar.message_created": lambda p: _webhook_field_change(p, "sidebar_message"),
    "conversation.custom_fields": lambda p: _webhook_field_change(p, "custom_fields"),
    "conversation_custom_fields": lambda p: _webhook_field_change(p, "custom_fields"),
}


def handle_webhook_event(event_type: str, payload: dict):
    """
    Main entry point for Layer 1 (Webhooks).
    Called by the thin HTTP handler in routes/atlas_webhooks.py.
    """
    handler = _WEBHOOK_HANDLERS.get(event_type)

    if handler:
        handler(payload)
    else:
        # Unknown event type — try to infer from payload
        logger.info(f"[WEBHOOK] Unknown event type '{event_type}', attempting inference")
        conv_id = _extract_conversation_id(payload)
        if conv_id:
            exists = tickets_collection.find_one(
                {"atlas_conversation_id": conv_id},
                {"_id": 0, "ticket_id": 1},
            )
            if exists:
                _webhook_field_change(payload, f"inferred_{event_type or 'unknown'}")
            else:
                _webhook_conversation_created(payload)

    # Track webhook events in state
    try:
        _state_col.update_one(
            {"_type": "shadow"},
            {"$inc": {"webhook_events_processed": 1}},
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
# Layer 2: Poller (Realtime Sync — Safety Net)
# ══════════════════════════════════════════════════════════════

def _run_realtime_sync(state: dict, tag_lookup: dict, agent_email_map: dict) -> dict:
    """
    Layer 2: Fetch Atlas conversations updated in the last N minutes
    and sync new tickets, messages, sidebars, and field changes.
    Safety net for anything webhooks might miss.
    """
    lookback = state.get("lookback_minutes", DEFAULT_LOOKBACK_MINUTES)
    start_date = (datetime.now(timezone.utc) - timedelta(minutes=lookback)).strftime("%Y-%m-%dT%H:%M:%SZ")

    stats = {
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

                stats["conversations_checked"] += 1

                existing_ticket = tickets_collection.find_one(
                    {"atlas_conversation_id": atlas_conv_id},
                    {"_id": 0, "ticket_id": 1, "status": 1, "priority": 1,
                     "assignee_id": 1, "updated_at": 1, "last_synced_at": 1,
                     "custom_fields": 1, "closed_at": 1, "atlas_csat_score": 1,
                     "trinity_assigned_at": 1, "tags": 1, "escalation_level": 1},
                )

                if existing_ticket:
                    ticket_id = existing_ticket["ticket_id"]
                    new_msgs = _sync_messages(atlas_conv_id, ticket_id)
                    stats["messages_synced"] += new_msgs
                    new_sidebars = _sync_sidebars(atlas_conv_id, ticket_id)
                    stats["sidebars_synced"] += new_sidebars
                    field_updates, conflicts = _sync_fields(conv, existing_ticket, agent_email_map, tag_lookup)
                    stats["field_updates"] += field_updates
                    stats["conflicts"] += conflicts
                    if new_msgs > 0 or new_sidebars > 0:
                        tickets_collection.update_one(
                            {"ticket_id": ticket_id},
                            {"$set": {"updated_at": datetime.now(timezone.utc)}},
                        )
                else:
                    ticket_id = _create_or_link_ticket(conv, tag_lookup, agent_email_map)
                    if ticket_id:
                        stats["new_tickets"] += 1
                        new_msgs = _sync_messages(atlas_conv_id, ticket_id)
                        stats["messages_synced"] += new_msgs
                        new_sidebars = _sync_sidebars(atlas_conv_id, ticket_id)
                        stats["sidebars_synced"] += new_sidebars

                time.sleep(0.05)

            cursor += len(convs)
            if cursor >= total:
                break

        except requests.Timeout:
            logger.warning(f"[POLLER] Timeout at cursor {cursor}, retrying...")
            time.sleep(5)
            continue
        except Exception as e:
            logger.error(f"[POLLER] Error in realtime sync at cursor {cursor}: {e}")
            break

    return stats


# ══════════════════════════════════════════════════════════════
# Layer 3: Two-Tier Crawl (Hot + Cold)
# ══════════════════════════════════════════════════════════════
# Hot Crawl: OPEN + PENDING + SNOOZED only (~2K convos, full pass in ~3-5 min)
# Cold Crawl: All conversations in 90-day window (~46K, full pass in ~45 min)

_TICKET_PROJECTION = {
    "_id": 0, "ticket_id": 1, "status": 1, "priority": 1,
    "assignee_id": 1, "updated_at": 1, "last_synced_at": 1,
    "custom_fields": 1, "closed_at": 1, "atlas_csat_score": 1,
    "trinity_assigned_at": 1, "tags": 1, "escalation_level": 1,
}


def _process_conversation_batch(convs: list, tag_lookup: dict, agent_email_map: dict, skip_messages_if_recent: int = 0) -> dict:
    """
    Process a batch of Atlas conversations — shared by both hot and cold crawls.
    If skip_messages_if_recent > 0, skip message sync for tickets synced within that many seconds.
    """
    stats = {"checked": 0, "new_tickets": 0, "messages_synced": 0,
             "field_updates": 0, "sidebars_synced": 0}

    now = datetime.now(timezone.utc)

    for conv in convs:
        if _stop_event.is_set():
            break

        atlas_conv_id = str(conv.get("id", ""))
        if not atlas_conv_id:
            continue

        stats["checked"] += 1

        existing_ticket = tickets_collection.find_one(
            {"atlas_conversation_id": atlas_conv_id},
            _TICKET_PROJECTION,
        )

        if existing_ticket:
            ticket_id = existing_ticket["ticket_id"]

            # Always sync fields (cheap — no API call, just compares conv data)
            field_updates, _ = _sync_fields(conv, existing_ticket, agent_email_map, tag_lookup)
            stats["field_updates"] += field_updates

            # Skip message sync if ticket was recently synced (avoids redundant API calls)
            should_sync_messages = True
            if skip_messages_if_recent > 0:
                last_synced = existing_ticket.get("last_synced_at")
                if last_synced:
                    if last_synced.tzinfo is None:
                        last_synced = last_synced.replace(tzinfo=timezone.utc)
                    if (now - last_synced).total_seconds() < skip_messages_if_recent:
                        should_sync_messages = False

            if should_sync_messages:
                new_msgs = _sync_messages(atlas_conv_id, ticket_id)
                stats["messages_synced"] += new_msgs
                new_sidebars = _sync_sidebars(atlas_conv_id, ticket_id)
                stats["sidebars_synced"] += new_sidebars
                if new_msgs > 0 or new_sidebars > 0:
                    tickets_collection.update_one(
                        {"ticket_id": ticket_id},
                        {"$set": {"updated_at": now}},
                    )
        else:
            ticket_id = _create_or_link_ticket(conv, tag_lookup, agent_email_map)
            if ticket_id:
                stats["new_tickets"] += 1
                new_msgs = _sync_messages(atlas_conv_id, ticket_id)
                stats["messages_synced"] += new_msgs
                new_sidebars = _sync_sidebars(atlas_conv_id, ticket_id)
                stats["sidebars_synced"] += new_sidebars

        time.sleep(0.03)

    return stats


def _run_hot_crawl_batch(state: dict, tag_lookup: dict, agent_email_map: dict) -> dict:
    """
    Hot Crawl: Cycle through OPEN, PENDING, SNOOZED conversations.
    ~2,300 total. At 500/batch, full pass completes in ~5 batches = ~3-5 minutes.
    Catches status/agent changes on active tickets that webhooks don't cover.
    """
    hot = state.get("hot_crawl", {
        "status_idx": 0,
        "cursor": 0,
        "completed_passes": 0,
        "total": 0,
    })

    status_idx = hot.get("status_idx", 0)
    cursor = hot.get("cursor", 0)

    if status_idx >= len(HOT_STATUSES):
        # All statuses done — pass complete
        hot["status_idx"] = 0
        hot["cursor"] = 0
        hot["completed_passes"] = hot.get("completed_passes", 0) + 1
        hot["last_completed_at"] = datetime.now(timezone.utc).isoformat()
        state["hot_crawl"] = hot
        _save_state(state)
        logger.info(f"[HOT] Pass #{hot['completed_passes']} complete")
        return {"checked": 0, "new_tickets": 0, "messages_synced": 0,
                "field_updates": 0, "sidebars_synced": 0}

    current_status = HOT_STATUSES[status_idx]

    try:
        resp = requests.get(
            f"{ATLAS_API}/conversations",
            params={"status": current_status, "cursor": cursor, "limit": HOT_BATCH_SIZE},
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        convs = data.get("data", [])
        total = data.get("total", 0)

        if not convs:
            # This status is exhausted — move to next
            hot["status_idx"] = status_idx + 1
            hot["cursor"] = 0
            state["hot_crawl"] = hot
            _save_state(state)
            return {"checked": 0, "new_tickets": 0, "messages_synced": 0,
                    "field_updates": 0, "sidebars_synced": 0}

        # Skip message sync if synced in last 120s (hot crawl focuses on field changes)
        stats = _process_conversation_batch(convs, tag_lookup, agent_email_map, skip_messages_if_recent=120)

        # Advance cursor
        new_cursor = cursor + len(convs)
        if new_cursor >= total:
            hot["status_idx"] = status_idx + 1
            hot["cursor"] = 0
        else:
            hot["cursor"] = new_cursor

        hot["total"] = total
        hot["current_status"] = current_status
        state["hot_crawl"] = hot
        _save_state(state)

        if stats["field_updates"] > 0 or stats["new_tickets"] > 0:
            logger.info(
                f"[HOT] {current_status}: batch={stats['checked']} "
                f"fields={stats['field_updates']} new={stats['new_tickets']} "
                f"cursor={hot.get('cursor', 0)}/{total}"
            )

    except requests.Timeout:
        logger.warning(f"[HOT] Timeout on {current_status} cursor={cursor}")
    except Exception as e:
        logger.error(f"[HOT] Error on {current_status} cursor={cursor}: {e}")

    return stats


def _run_cold_crawl_batch(state: dict, tag_lookup: dict, agent_email_map: dict) -> dict:
    """
    Cold Crawl: Walk through ALL Atlas conversations (including CLOSED) in the
    90-day window. At 500/batch, full pass takes ~45 minutes (vs old ~4 hours).
    Background reconciliation — catches everything eventually.
    """
    stats = {"checked": 0, "new_tickets": 0, "messages_synced": 0,
             "field_updates": 0, "sidebars_synced": 0}

    cold = state.get("full_sync", {})
    cursor = cold.get("cursor", 0)
    window_start = (datetime.now(timezone.utc) - timedelta(days=FULL_SYNC_WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        resp = requests.get(
            f"{ATLAS_API}/conversations",
            params={"startDate": window_start, "cursor": cursor, "limit": COLD_BATCH_SIZE},
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        convs = data.get("data", [])
        total = data.get("total", 0)

        if not convs:
            cold["cursor"] = 0
            cold["completed_passes"] = cold.get("completed_passes", 0) + 1
            cold["last_completed_at"] = datetime.now(timezone.utc).isoformat()
            state["full_sync"] = cold
            _save_state(state)
            logger.info(f"[COLD] Pass #{cold['completed_passes']} complete. Total={cold.get('total', 0)}")
            return stats

        stats = _process_conversation_batch(convs, tag_lookup, agent_email_map)

        # Advance cursor
        new_cursor = cursor + len(convs)
        if new_cursor >= total:
            cold["cursor"] = 0
            cold["completed_passes"] = cold.get("completed_passes", 0) + 1
            cold["last_completed_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"[COLD] Pass #{cold['completed_passes']} complete. Total={total}")
        else:
            cold["cursor"] = new_cursor

        cold["total"] = total
        state["full_sync"] = cold
        _save_state(state)

    except requests.Timeout:
        logger.warning(f"[COLD] Timeout at cursor {cursor}")
    except Exception as e:
        logger.error(f"[COLD] Error at cursor {cursor}: {e}")

    return stats


# ══════════════════════════════════════════════════════════════
# Layer 4: Push-back (Trinity → Atlas)
# ══════════════════════════════════════════════════════════════

def sync_assignment_to_atlas(ticket_id: str, assignee_user_id: Optional[str]) -> bool:
    """Push an assignment change from Trinity to Atlas."""
    if not ATLAS_KEY:
        return False
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        return False
    atlas_conv_id = ticket.get("atlas_conversation_id")
    if not atlas_conv_id:
        return False

    atlas_agent_id = None
    if assignee_user_id:
        user = users_collection.find_one({"user_id": assignee_user_id}, {"_id": 0, "email": 1})
        if user and user.get("email"):
            atlas_agent_id = _get_atlas_agent_id_by_email(user["email"])
            if not atlas_agent_id:
                logger.warning(f"No Atlas agent for {user['email']}, skipping Atlas sync")
                return False
        else:
            return False

    try:
        resp = requests.post(
            f"{ATLAS_API}/conversations/{atlas_conv_id}",
            headers=_headers(),
            json={"assignedAgentId": atlas_agent_id},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"[PUSH] Assignment: ticket={ticket_id} agent={atlas_agent_id or 'unassigned'}")
        return True
    except Exception as e:
        logger.error(f"[PUSH] Assignment failed for {ticket_id}: {e}")
        return False


def sync_ticket_to_atlas(ticket_id: str, changed_fields: dict) -> bool:
    """
    Push field changes from Trinity to Atlas. Atlas remains the source of truth.

    changed_fields: dict of Trinity field names → new values, e.g.:
        {"status": "closed", "priority": "high", "tags": ["billing", "urgent"]}
    """
    if not ATLAS_KEY:
        return False

    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0, "atlas_conversation_id": 1})
    if not ticket:
        return False
    atlas_conv_id = ticket.get("atlas_conversation_id")
    if not atlas_conv_id:
        return False

    atlas_payload = {}

    if "status" in changed_fields:
        atlas_status = _REVERSE_STATUS_MAP.get(changed_fields["status"])
        if atlas_status:
            atlas_payload["status"] = atlas_status

    if "priority" in changed_fields:
        atlas_priority = _REVERSE_PRIORITY_MAP.get(changed_fields["priority"])
        if atlas_priority:
            atlas_payload["priority"] = atlas_priority

    if "tags" in changed_fields:
        tag_map = _get_tag_name_to_id_map()
        atlas_tags = []
        for tag_name in (changed_fields["tags"] or []):
            tag_id = tag_map.get(tag_name.lower())
            if tag_id:
                atlas_tags.append(tag_id)
        atlas_payload["tags"] = atlas_tags

    if "custom_fields" in changed_fields:
        atlas_payload["customFields"] = changed_fields["custom_fields"]

    if "assignee_id" in changed_fields:
        sync_assignment_to_atlas(ticket_id, changed_fields["assignee_id"])

    if not atlas_payload:
        return True

    try:
        resp = requests.post(
            f"{ATLAS_API}/conversations/{atlas_conv_id}",
            headers=_headers(),
            json=atlas_payload,
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"[PUSH] Fields synced: ticket={ticket_id} fields={list(atlas_payload.keys())}")
        return True
    except Exception as e:
        logger.error(f"[PUSH] Field sync failed for {ticket_id}: {e} payload={atlas_payload}")
        return False


def sync_tags_to_atlas(ticket_id: str) -> bool:
    """Push current tag list from Trinity ticket to Atlas."""
    if not ATLAS_KEY:
        return False
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0, "atlas_conversation_id": 1, "tags": 1})
    if not ticket or not ticket.get("atlas_conversation_id"):
        return False
    return sync_ticket_to_atlas(ticket_id, {"tags": ticket.get("tags", [])})


# ══════════════════════════════════════════════════════════════
# Daemon Loop (Layers 2 + 3)
# ══════════════════════════════════════════════════════════════

def _sync_loop():
    """
    Main daemon loop:
    - Layer 2 (Poller): catches newly created conversations
    - Layer 3 Hot Crawl: syncs active tickets (OPEN/PENDING/SNOOZED) every ~3-5 min
    - Layer 3 Cold Crawl: full historical reconciliation every ~45 min
    - Layer 1 (Webhooks) runs independently via HTTP
    - Layer 4 (Push-back) runs on demand from ticket mutation endpoints
    """
    logger.info("[SYNC] Unified sync engine started (L2 + L3-Hot + L3-Cold)")

    state = _get_state()
    state["status"] = "running"
    state["started_at"] = datetime.now(timezone.utc)
    if "full_sync" not in state:
        state["full_sync"] = {"cursor": 0, "completed_passes": 0, "total": 0}
    if "hot_crawl" not in state:
        state["hot_crawl"] = {"status_idx": 0, "cursor": 0, "completed_passes": 0, "total": 0}
    _save_state(state)

    # Prime the shared caches
    tag_lookup = _fetch_tags()
    agent_email_map = _build_agent_email_map()
    _lookup_cache["tag_lookup"] = tag_lookup
    _lookup_cache["agent_email_map"] = agent_email_map
    _lookup_cache["tag_last_refresh"] = time.time()
    _lookup_cache["agent_last_refresh"] = time.time()
    logger.info(f"[SYNC] Loaded {len(tag_lookup)} tags, {len(agent_email_map)} agent mappings")

    while not _stop_event.is_set():
        try:
            # Refresh caches
            tag_lookup = _get_cached_tag_lookup()
            agent_email_map = _get_cached_agent_map()

            state = _get_state()

            # Layer 2: Poller (catches new conversations by creation date)
            realtime_stats = _run_realtime_sync(state, tag_lookup, agent_email_map)

            # Layer 3 Hot: Active tickets (OPEN/PENDING/SNOOZED) — fast pass
            hot_stats = _run_hot_crawl_batch(state, tag_lookup, agent_email_map)

            # Layer 3 Cold: All conversations — background reconciliation
            cold_stats = _run_cold_crawl_batch(state, tag_lookup, agent_email_map)

            # Update state
            state = _get_state()
            state["cycles_completed"] = state.get("cycles_completed", 0) + 1
            state["conversations_checked"] = state.get("conversations_checked", 0) + realtime_stats["conversations_checked"]
            state["new_tickets_created"] = (
                state.get("new_tickets_created", 0)
                + realtime_stats["new_tickets"] + hot_stats.get("new_tickets", 0) + cold_stats.get("new_tickets", 0)
            )
            state["messages_synced"] = (
                state.get("messages_synced", 0)
                + realtime_stats["messages_synced"] + hot_stats.get("messages_synced", 0) + cold_stats.get("messages_synced", 0)
            )
            state["sidebars_synced"] = (
                state.get("sidebars_synced", 0)
                + realtime_stats["sidebars_synced"] + hot_stats.get("sidebars_synced", 0) + cold_stats.get("sidebars_synced", 0)
            )
            state["field_updates"] = (
                state.get("field_updates", 0)
                + realtime_stats["field_updates"] + hot_stats.get("field_updates", 0) + cold_stats.get("field_updates", 0)
            )
            state["conflicts_skipped"] = state.get("conflicts_skipped", 0) + realtime_stats["conflicts"]
            state["last_sync_at"] = datetime.now(timezone.utc)
            state["status"] = "running"
            _save_state(state)

            # Log cycle summary
            total_activity = (
                realtime_stats["new_tickets"] + realtime_stats["messages_synced"]
                + hot_stats.get("new_tickets", 0) + hot_stats.get("field_updates", 0)
                + cold_stats.get("new_tickets", 0) + cold_stats.get("messages_synced", 0)
            )
            if total_activity > 0 or hot_stats.get("checked", 0) > 0 or cold_stats.get("checked", 0) > 0:
                hs = state.get("hot_crawl", {})
                cs = state.get("full_sync", {})
                hot_status = HOT_STATUSES[hs.get("status_idx", 0)] if hs.get("status_idx", 0) < len(HOT_STATUSES) else "DONE"
                logger.info(
                    f"[SYNC] Cycle #{state['cycles_completed']}: "
                    f"L2[new={realtime_stats['new_tickets']} msgs={realtime_stats['messages_synced']}] "
                    f"HOT[{hot_status} batch={hot_stats.get('checked',0)} fields={hot_stats.get('field_updates',0)} pass#{hs.get('completed_passes',0)}] "
                    f"COLD[batch={cold_stats.get('checked',0)} new={cold_stats.get('new_tickets',0)} "
                    f"cursor={cs.get('cursor',0)}/{cs.get('total',0)} pass#{cs.get('completed_passes',0)}]"
                )
            else:
                logger.debug(f"[SYNC] Cycle #{state['cycles_completed']}: idle")

        except Exception as e:
            logger.error(f"[SYNC] Error in sync loop: {e}")
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
    logger.info("[SYNC] Unified sync engine stopped")


# ══════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════

def start_sync() -> dict:
    """Start the unified sync engine."""
    global _worker_thread
    if not ATLAS_KEY:
        return {"error": "No ATLAS_API_KEY configured"}
    if _worker_thread and _worker_thread.is_alive():
        return {"message": "Sync is already running", "status": "running"}
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_sync_loop, daemon=True, name="atlas_unified_sync")
    _worker_thread.start()
    return {"message": "Unified sync engine started", "status": "running"}


def stop_sync() -> dict:
    """Stop the unified sync engine."""
    global _worker_thread
    if not _worker_thread or not _worker_thread.is_alive():
        return {"message": "Sync is not running", "status": "stopped"}
    _stop_event.set()
    _worker_thread.join(timeout=10)
    _worker_thread = None
    state = _get_state()
    state["status"] = "stopped"
    _save_state(state)
    return {"message": "Unified sync engine stopped", "status": "stopped"}


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
    """Called on server startup. Auto-starts the sync engine if Atlas key is configured."""
    if not ATLAS_KEY:
        logger.info("[SYNC] No ATLAS_API_KEY — sync engine disabled")
        return
    logger.info("[SYNC] Auto-starting unified sync engine on boot...")
    start_sync()
