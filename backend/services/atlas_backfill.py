"""
Atlas Backfill Service — Resumable Historical Data Import
=========================================================
Imports all Atlas conversations into Trinity with full resume capability.

State is persisted in MongoDB after every batch, so the process can be
interrupted (pod sleep, process kill) and resumed from the exact same
position on next startup.

State collection: `atlas_backfill_state` (single document)
"""

import os
import re
import uuid
import logging
import time
import threading
import requests
from datetime import datetime, timezone
from typing import Optional

from database import (
    db, tickets_collection, messages_collection,
    users_collection, customers_collection,
)
from utils import generate_ticket_id

logger = logging.getLogger("atlas_backfill")

ATLAS_API = "https://api.atlas.so/v1"
ATLAS_KEY = os.environ.get("ATLAS_API_KEY", "")

# State collection
_state_col = db.atlas_backfill_state

# Thread control
_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

# ── Status constants ──
STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_PAUSED = "paused"
STATUS_COMPLETED = "completed"
STATUS_ERROR = "error"

BATCH_SIZE = 100
REQUEST_TIMEOUT = 60
BATCH_DELAY = 0.5  # seconds between batches

# ── Atlas field mapping ──
STATUS_MAP = {
    "OPEN": "todo",
    "CLOSED": "resolved",
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
    """Get current backfill state from MongoDB."""
    state = _state_col.find_one({"_type": "backfill"}, {"_id": 0})
    if not state:
        return {
            "_type": "backfill",
            "status": STATUS_IDLE,
            "cursor": 0,
            "total_in_atlas": 0,
            "conversations_fetched": 0,
            "conversations_imported": 0,
            "conversations_skipped": 0,
            "messages_imported": 0,
            "customers_created": 0,
            "agents_mapped": 0,
            "errors": [],
            "last_batch_at": None,
            "started_at": None,
            "completed_at": None,
            "tags_fetched": 0,
        }
    return state


def _save_state(state: dict):
    """Persist state to MongoDB (upsert)."""
    state["_type"] = "backfill"
    _state_col.update_one(
        {"_type": "backfill"},
        {"$set": state},
        upsert=True,
    )


def get_status() -> dict:
    """Public: return current backfill status for API."""
    state = _get_state()
    state.pop("_type", None)
    # Trim errors to last 20 for display
    if len(state.get("errors", [])) > 20:
        state["errors"] = state["errors"][-20:]
    return state


# ══════════════════════════════════════════════════════════════
# Atlas API helpers
# ══════════════════════════════════════════════════════════════

def _headers():
    return {"Accept": "application/json", "Authorization": f"Bearer {ATLAS_KEY}"}


def _fetch_tags() -> dict:
    """Fetch all tags and return id→label mapping."""
    try:
        resp = requests.get(f"{ATLAS_API}/tags", headers=_headers(), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        tags = data if isinstance(data, list) else data.get("data", data.get("tags", []))
        lookup = {}
        for t in tags:
            tag_id = str(t.get("id", ""))
            tag_label = t.get("label") or t.get("name") or tag_id
            if tag_id:
                lookup[tag_id] = tag_label
        return lookup
    except Exception as e:
        logger.warning(f"[BACKFILL] Failed to fetch tags: {e}")
        return {}


def _fetch_conversations(cursor: int, limit: int) -> dict:
    """Fetch a page of conversations."""
    resp = requests.get(
        f"{ATLAS_API}/conversations",
        params={"cursor": cursor, "limit": limit},
        headers=_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _fetch_messages(conversation_id: str) -> list:
    """Fetch all messages for a conversation (paginated)."""
    all_msgs = []
    cursor = 0
    while True:
        resp = requests.get(
            f"{ATLAS_API}/conversations/{conversation_id}/messages",
            params={"cursor": cursor, "limit": 100},
            headers=_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", []) if isinstance(data, dict) else data
        all_msgs.extend(items)
        total = data.get("total", 0) if isinstance(data, dict) else len(items)
        if not items or len(all_msgs) >= total:
            break
        cursor += len(items)
    return all_msgs


# ══════════════════════════════════════════════════════════════
# Data Mapping
# ══════════════════════════════════════════════════════════════

def _parse_dt(val) -> Optional[datetime]:
    """Parse epoch int or ISO string to UTC datetime."""
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


def _strip_html(html: str) -> str:
    """Strip HTML tags to plain text."""
    if not html:
        return ""
    import html as html_lib
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    return text.strip()


def _extract_domain(email_addr: str) -> Optional[str]:
    """Extract domain from email address."""
    if not email_addr or "@" not in email_addr:
        return None
    return email_addr.split("@", 1)[1].lower()


def _get_or_create_customer(email_addr: str, name: str) -> Optional[dict]:
    """Find or create a customer record by email."""
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
        "source": "atlas_import",
    }
    try:
        customers_collection.insert_one(doc)
        doc.pop("_id", None)
        return doc
    except Exception:
        # Might be a race condition duplicate
        return customers_collection.find_one(
            {"email": {"$regex": f"^{re.escape(email_lower)}$", "$options": "i"}},
            {"_id": 0, "customer_id": 1},
        )


def _map_conversation(conv: dict, tag_lookup: dict, agent_email_map: dict) -> dict:
    """Map an Atlas conversation to a Trinity ticket document."""
    customer = conv.get("customer") or {}
    assigned_agent = conv.get("assignedAgent") or {}
    stats = conv.get("statistics") or {}

    # Tags
    raw_tags = conv.get("tags") or []
    mapped_tags = [tag_lookup.get(str(t), str(t)) for t in raw_tags]

    # Status & priority
    atlas_status = (conv.get("status") or "OPEN").upper()
    atlas_priority = (conv.get("priority") or "NO_PRIORITY").upper()

    # Customer email
    customer_email = (
        customer.get("email")
        or (customer.get("defaultSenders") or {}).get("email")
    )

    created_at = _parse_dt(conv.get("createdAt")) or _parse_dt(conv.get("startedAt")) or datetime.now(timezone.utc)

    ticket_id = generate_ticket_id()

    ticket_doc = {
        "ticket_id": ticket_id,
        "uuid": str(uuid.uuid4()),
        "title": conv.get("subject") or f"Conversation #{conv.get('number', '')}".strip(),
        "description": "",
        "status": STATUS_MAP.get(atlas_status, "todo"),
        "priority": PRIORITY_MAP.get(atlas_priority, "medium"),
        "escalation_level": "L1",
        "order": 0,
        "source": "atlas",
        "tags": mapped_tags,
        "custom_fields": conv.get("customFields") or {},
        "is_starred": False,
        "created_by": "atlas_import",
        "created_at": created_at,
        "updated_at": _parse_dt(conv.get("closedAt")) or created_at,
        # Customer
        "customer_email": customer_email,
        "customer_name": _customer_name(customer),
        "customer_phone": customer.get("phoneNumber"),
        "customer_id": None,
        "domain": _extract_domain(customer_email) if customer_email else None,
        # Assignment
        "assignee_id": None,
        "team_id": conv.get("assignedTeamId"),
        # Atlas metadata
        "atlas_conversation_id": str(conv.get("id", "")),
        "atlas_customer_id": str(conv.get("customerId", "")),
        "atlas_number": conv.get("number"),
        "atlas_status": conv.get("status"),
        "atlas_priority": conv.get("priority"),
        "atlas_assigned_agent_name": _agent_name(assigned_agent),
        "atlas_assigned_agent_email": assigned_agent.get("email"),
        # Timestamps
        "started_at": _parse_dt(conv.get("startedAt")),
        "closed_at": _parse_dt(conv.get("closedAt")),
        "assigned_at": _parse_dt(conv.get("assignedAt")),
        # Channel
        "started_channel": conv.get("startedChannel"),
        # Stats
        "first_response_time": stats.get("firstResponseTime"),
        "avg_response_time": stats.get("avgResponseTime"),
        "total_resolution_time": stats.get("totalResolutionTime"),
    }

    # Link customer
    if customer_email:
        cust = _get_or_create_customer(customer_email, ticket_doc["customer_name"])
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

    return ticket_doc


def _map_message(msg: dict, ticket_id: str, atlas_conversation_id: str) -> dict:
    """Map an Atlas message to a Trinity message document."""
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

    return {
        "message_id": f"atlas_msg_{msg.get('id', uuid.uuid4().hex[:12])}",
        "ticket_id": ticket_id,
        "type": msg_type,
        "content": _strip_html(raw_text)[:10000],
        "email_html": raw_text if "<" in raw_text else None,
        "author_id": None,
        "author_name": author_name or "Unknown",
        "author_email": author_email,
        "source": "atlas",
        "mentions": [],
        "created_at": _parse_dt(msg.get("sentAt")) or _parse_dt(msg.get("createdAt")) or datetime.now(timezone.utc),
        "atlas_message_id": msg.get("id"),
        "atlas_conversation_id": atlas_conversation_id,
        "atlas_side": msg.get("side"),
        "atlas_channel": msg.get("channel"),
    }


# ══════════════════════════════════════════════════════════════
# Core Backfill Loop
# ══════════════════════════════════════════════════════════════

def _run_backfill(max_batches: int = None):
    """
    Main backfill loop. Runs in a thread.
    Resumes from last saved cursor. Saves state after every batch.
    """
    if not ATLAS_KEY:
        logger.error("[BACKFILL] No ATLAS_API_KEY configured in .env")
        return

    state = _get_state()

    # If completed, don't re-run unless explicitly reset
    if state["status"] == STATUS_COMPLETED:
        logger.info("[BACKFILL] Already completed. Reset state to re-run.")
        return

    # Mark as running
    state["status"] = STATUS_RUNNING
    if not state.get("started_at"):
        state["started_at"] = datetime.now(timezone.utc)
    _save_state(state)

    # ── Fetch tags once ──
    logger.info("[BACKFILL] Fetching Atlas tags...")
    tag_lookup = _fetch_tags()
    state["tags_fetched"] = len(tag_lookup)
    _save_state(state)
    logger.info(f"[BACKFILL] Got {len(tag_lookup)} tags")

    # ── Build agent email → user_id lookup ──
    all_users = list(users_collection.find({}, {"_id": 0, "user_id": 1, "email": 1}))
    agent_email_map = {u["email"].lower(): u["user_id"] for u in all_users if u.get("email")}

    cursor = state.get("cursor", 0)
    batch_count = 0

    logger.info(f"[BACKFILL] Starting from cursor={cursor}")

    while not _stop_event.is_set():
        if max_batches and batch_count >= max_batches:
            logger.info(f"[BACKFILL] Reached max_batches={max_batches}, pausing.")
            state["status"] = STATUS_PAUSED
            _save_state(state)
            return

        try:
            # Fetch batch
            page = _fetch_conversations(cursor, BATCH_SIZE)
            convs = page.get("data", [])
            total = page.get("total", 0)

            if not state.get("total_in_atlas") or total > 0:
                state["total_in_atlas"] = total

            if not convs:
                logger.info(f"[BACKFILL] No more conversations at cursor={cursor}. Done!")
                state["status"] = STATUS_COMPLETED
                state["completed_at"] = datetime.now(timezone.utc)
                _save_state(state)
                return

            # Process each conversation
            for conv in convs:
                if _stop_event.is_set():
                    state["status"] = STATUS_PAUSED
                    _save_state(state)
                    return

                atlas_id = str(conv.get("id", ""))
                state["conversations_fetched"] += 1

                try:
                    # Dedup check
                    if tickets_collection.find_one({"atlas_conversation_id": atlas_id}, {"_id": 1}):
                        state["conversations_skipped"] += 1
                        continue

                    # Map conversation → ticket
                    ticket_doc = _map_conversation(conv, tag_lookup, agent_email_map)

                    if ticket_doc.get("customer_id"):
                        state["customers_created"] += 1
                    if ticket_doc.get("assignee_id"):
                        state["agents_mapped"] += 1

                    # Fetch messages
                    messages = _fetch_messages(atlas_id)

                    # Set description from first customer message
                    for msg in messages:
                        if (msg.get("side") or "").upper() == "CUSTOMER":
                            ticket_doc["description"] = (_strip_html(msg.get("text") or ""))[:5000]
                            break

                    # Set first message type
                    first_msg_done = False

                    # Insert ticket
                    tickets_collection.insert_one(ticket_doc)
                    ticket_doc.pop("_id", None)

                    # Insert messages
                    msg_count = 0
                    for i, msg in enumerate(messages):
                        note_doc = _map_message(msg, ticket_doc["ticket_id"], atlas_id)
                        # First message is "original"
                        if not first_msg_done:
                            note_doc["type"] = "original"
                            first_msg_done = True
                        try:
                            messages_collection.insert_one(note_doc)
                            msg_count += 1
                        except Exception:
                            pass  # Skip duplicate messages (unique index on atlas_message_id)

                    state["messages_imported"] += msg_count
                    state["conversations_imported"] += 1

                except requests.Timeout:
                    err = f"Timeout fetching messages for {atlas_id}"
                    logger.warning(f"[BACKFILL] {err}")
                    state["errors"].append(f"{datetime.now(timezone.utc).isoformat()}: {err}")
                    time.sleep(2)
                except Exception as e:
                    err = f"Error on conv {atlas_id}: {type(e).__name__}: {str(e)[:200]}"
                    logger.error(f"[BACKFILL] {err}")
                    state["errors"].append(f"{datetime.now(timezone.utc).isoformat()}: {err}")
                    # Keep only last 100 errors
                    if len(state["errors"]) > 100:
                        state["errors"] = state["errors"][-100:]

            # ── Save state after each batch ──
            cursor += len(convs)
            state["cursor"] = cursor
            state["last_batch_at"] = datetime.now(timezone.utc)
            _save_state(state)

            batch_count += 1
            if batch_count % 10 == 0:
                logger.info(
                    f"[BACKFILL] Progress: cursor={cursor} "
                    f"imported={state['conversations_imported']} "
                    f"skipped={state['conversations_skipped']} "
                    f"msgs={state['messages_imported']} "
                    f"total={state.get('total_in_atlas', '?')}"
                )

            time.sleep(BATCH_DELAY)

        except requests.Timeout:
            logger.warning(f"[BACKFILL] Timeout at cursor={cursor}, retrying in 5s")
            time.sleep(5)
        except requests.HTTPError as e:
            if e.response and e.response.status_code == 429:
                logger.warning("[BACKFILL] Rate limited, backing off 30s")
                time.sleep(30)
            else:
                err = f"HTTP error at cursor={cursor}: {e}"
                logger.error(f"[BACKFILL] {err}")
                state["errors"].append(f"{datetime.now(timezone.utc).isoformat()}: {err}")
                state["status"] = STATUS_ERROR
                _save_state(state)
                return
        except Exception as e:
            err = f"Unexpected error at cursor={cursor}: {type(e).__name__}: {str(e)[:200]}"
            logger.error(f"[BACKFILL] {err}")
            state["errors"].append(f"{datetime.now(timezone.utc).isoformat()}: {err}")
            state["status"] = STATUS_ERROR
            _save_state(state)
            return

    # If we got here, stop was requested
    state["status"] = STATUS_PAUSED
    _save_state(state)
    logger.info(f"[BACKFILL] Paused at cursor={cursor}")


# ══════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════

def start_backfill(max_batches: int = None) -> dict:
    """Start or resume the backfill in a background thread."""
    global _worker_thread

    if _worker_thread and _worker_thread.is_alive():
        return {"status": "already_running", "message": "Backfill is already running"}

    state = _get_state()
    if state["status"] == STATUS_COMPLETED:
        return {"status": "completed", "message": "Backfill already completed. Reset to re-run."}

    _stop_event.clear()
    _worker_thread = threading.Thread(
        target=_run_backfill,
        kwargs={"max_batches": max_batches},
        daemon=True,
        name="atlas-backfill",
    )
    _worker_thread.start()
    return {"status": "started", "message": f"Backfill started from cursor={state.get('cursor', 0)}"}


def stop_backfill() -> dict:
    """Gracefully stop the backfill. It will save state and can be resumed."""
    global _worker_thread

    if not _worker_thread or not _worker_thread.is_alive():
        return {"status": "not_running", "message": "Backfill is not running"}

    _stop_event.set()
    _worker_thread.join(timeout=30)
    return {"status": "stopped", "message": "Backfill stopped. Can be resumed."}


def reset_backfill() -> dict:
    """Reset backfill state to allow re-running from scratch."""
    global _worker_thread

    if _worker_thread and _worker_thread.is_alive():
        return {"status": "error", "message": "Stop the backfill first before resetting"}

    _state_col.delete_one({"_type": "backfill"})
    return {"status": "reset", "message": "Backfill state cleared. Ready to start fresh."}


def test_batch(count: int = 100) -> dict:
    """Run a test batch synchronously (blocking) and return results."""
    if not ATLAS_KEY:
        return {"error": "No ATLAS_API_KEY configured"}

    tag_lookup = _fetch_tags()
    all_users = list(users_collection.find({}, {"_id": 0, "user_id": 1, "email": 1}))
    agent_email_map = {u["email"].lower(): u["user_id"] for u in all_users if u.get("email")}

    page = _fetch_conversations(0, count)
    convs = page.get("data", [])
    total = page.get("total", 0)

    results = {
        "total_in_atlas": total,
        "batch_size": len(convs),
        "tags": len(tag_lookup),
        "imported": 0,
        "skipped_duplicate": 0,
        "skipped_no_messages": 0,
        "messages_imported": 0,
        "errors": [],
        "sample_tickets": [],
    }

    for conv in convs:
        atlas_id = str(conv.get("id", ""))
        try:
            if tickets_collection.find_one({"atlas_conversation_id": atlas_id}, {"_id": 1}):
                results["skipped_duplicate"] += 1
                continue

            ticket_doc = _map_conversation(conv, tag_lookup, agent_email_map)
            messages = _fetch_messages(atlas_id)

            for msg in messages:
                if (msg.get("side") or "").upper() == "CUSTOMER":
                    ticket_doc["description"] = (_strip_html(msg.get("text") or ""))[:5000]
                    break

            tickets_collection.insert_one(ticket_doc)
            ticket_doc.pop("_id", None)

            msg_count = 0
            first_msg_done = False
            for msg in messages:
                note_doc = _map_message(msg, ticket_doc["ticket_id"], atlas_id)
                if not first_msg_done:
                    note_doc["type"] = "original"
                    first_msg_done = True
                try:
                    messages_collection.insert_one(note_doc)
                    msg_count += 1
                except Exception:
                    pass

            results["imported"] += 1
            results["messages_imported"] += msg_count

            if len(results["sample_tickets"]) < 5:
                results["sample_tickets"].append({
                    "ticket_id": ticket_doc["ticket_id"],
                    "title": ticket_doc["title"],
                    "status": ticket_doc["status"],
                    "customer_email": ticket_doc.get("customer_email"),
                    "channel": ticket_doc.get("started_channel"),
                    "messages": msg_count,
                })

            time.sleep(0.3)  # gentle rate limit

        except Exception as e:
            results["errors"].append(f"{atlas_id}: {str(e)[:200]}")

    return results


def auto_resume_on_startup():
    """Called on server startup. Resumes backfill if it was interrupted (pod sleep, process kill)."""
    state = _get_state()
    if state["status"] in (STATUS_RUNNING, STATUS_PAUSED):
        cursor = state.get("cursor", 0)
        imported = state.get("conversations_imported", 0)
        logger.info(f"[BACKFILL] Found incomplete backfill at cursor={cursor} (imported={imported}). Auto-resuming...")
        state["status"] = STATUS_PAUSED
        _save_state(state)
        start_backfill()
