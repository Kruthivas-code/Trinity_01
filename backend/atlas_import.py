"""
Atlas Import Module
==================
Fetches conversations, messages, and tags from Atlas (https://atlas.so) API
and maps them into Trinity's database schema.

Atlas API Docs: https://developers.atlas.so/reference
"""

import httpx
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

ATLAS_API_BASE = "https://api.atlas.so/v1"

# ==================== Atlas API Client ====================

class AtlasClient:
    """HTTP client for Atlas REST API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    async def _get(self, path: str, params: dict = None) -> dict:
        """Make an authenticated GET request to Atlas API."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                f"{ATLAS_API_BASE}{path}",
                headers=self.headers,
                params=params or {},
            )
            resp.raise_for_status()
            return resp.json()

    # ---- Paginated fetchers ----

    async def fetch_all_tags(self) -> List[dict]:
        """Fetch all tags. Returns list of tag objects."""
        try:
            data = await self._get("/tags")
            # The response may be a list directly or wrapped in { data: [...] }
            if isinstance(data, list):
                return data
            return data.get("data", data.get("tags", []))
        except Exception as e:
            logger.warning(f"[ATLAS] Failed to fetch tags: {e}")
            return []

    async def fetch_conversations(
        self,
        cursor: int = 0,
        limit: int = 100,
        status: str = None,
        start_date: str = None,
        end_date: str = None,
    ) -> dict:
        """Fetch a page of conversations."""
        params = {"cursor": cursor, "limit": limit}
        if status:
            params["status"] = status
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._get("/conversations", params)

    async def fetch_all_conversations(self, **kwargs) -> List[dict]:
        """Paginate through all conversations."""
        all_convos = []
        cursor = 0
        page_size = 100
        while True:
            page = await self.fetch_conversations(cursor=cursor, limit=page_size, **kwargs)
            items = page.get("data", [])
            all_convos.extend(items)
            total = page.get("total")
            if not items or (total is not None and len(all_convos) >= total):
                break
            cursor += len(items)
        return all_convos

    async def fetch_conversation(self, conversation_id: str) -> dict:
        """Fetch a single conversation by ID."""
        return await self._get(f"/conversations/{conversation_id}")

    async def fetch_messages(
        self, conversation_id: str, cursor: int = 0, limit: int = 100
    ) -> dict:
        """Fetch a page of messages for a conversation."""
        return await self._get(
            f"/conversations/{conversation_id}/messages",
            {"cursor": cursor, "limit": limit},
        )

    async def fetch_all_messages(self, conversation_id: str) -> List[dict]:
        """Paginate through all messages for a conversation."""
        all_msgs = []
        cursor = 0
        page_size = 100
        while True:
            page = await self.fetch_messages(conversation_id, cursor=cursor, limit=page_size)
            items = page.get("data", [])
            all_msgs.extend(items)
            total = page.get("total")
            if not items or (total is not None and len(all_msgs) >= total):
                break
            cursor += len(items)
        return all_msgs


# ==================== Field Mapping ====================

# Atlas ConversationStatus → Trinity status
STATUS_MAP = {
    "OPEN": "todo",
    "CLOSED": "closed",
    "SNOOZED": "waiting",
    "PENDING": "waiting",
    "IN_PROGRESS": "in_progress",
}

# Atlas ExternalConversationPriority → Trinity priority
PRIORITY_MAP = {
    "NO_PRIORITY": "medium",
    "LOW": "low",
    "NORMAL": "medium",
    "HIGH": "high",
    "URGENT": "urgent",
}

# Atlas message side → Trinity message type
MESSAGE_TYPE_MAP = {
    "AGENT": "reply",
    "CUSTOMER": "customer_reply",
    "BOT": "reply",
    "SYSTEM": "system",
}


def _parse_dt(val) -> Optional[datetime]:
    """Safely parse an ISO datetime string into a timezone-aware datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _customer_name(customer: dict) -> str:
    """Build display name from Atlas customer object."""
    if not customer:
        return "Customer"
    first = customer.get("firstName") or ""
    last = customer.get("lastName") or ""
    full = f"{first} {last}".strip()
    return full or customer.get("email") or "Customer"


def _agent_name(agent: dict) -> str:
    """Build display name from Atlas agent/user object."""
    if not agent:
        return None
    first = agent.get("firstName") or ""
    last = agent.get("lastName") or ""
    full = f"{first} {last}".strip()
    return full or agent.get("email") or "Agent"


def build_tag_lookup(tags: List[dict]) -> Dict[str, str]:
    """
    Build a mapping of Atlas tag-ID → tag-name.
    Atlas tags can have 'id' and 'name' fields.
    """
    lookup = {}
    for tag in tags:
        tag_id = str(tag.get("id", ""))
        tag_name = tag.get("name") or tag.get("label") or tag_id
        if tag_id:
            lookup[tag_id] = tag_name
    return lookup


def map_conversation_to_ticket(
    conv: dict,
    tag_lookup: Dict[str, str],
    generate_ticket_id_fn,
    importer_user_id: str,
) -> dict:
    """
    Transform an Atlas conversation dict into a Trinity ticket document.
    """
    customer = conv.get("customer") or {}
    assigned_agent = conv.get("assignedAgent") or {}
    stats = conv.get("statistics") or {}
    csat = conv.get("csat") or {}
    account = customer.get("account") or {}

    # Map tags from UUIDs to names
    raw_tags = conv.get("tags") or []
    mapped_tags = []
    for t in raw_tags:
        tag_str = str(t)
        mapped_tags.append(tag_lookup.get(tag_str, tag_str))

    # Map status
    atlas_status = (conv.get("status") or "OPEN").upper()
    trinity_status = STATUS_MAP.get(atlas_status, "todo")

    # Map priority
    atlas_priority = (conv.get("priority") or "NO_PRIORITY").upper()
    trinity_priority = PRIORITY_MAP.get(atlas_priority, "medium")

    # Determine snoozed state
    snoozed_until = _parse_dt(conv.get("snoozedUntil"))
    is_snoozed = atlas_status == "SNOOZED" or snoozed_until is not None

    # Customer email
    customer_email = (
        customer.get("email")
        or (customer.get("defaultSenders") or {}).get("email")
        or None
    )

    # Timestamps
    created_at = _parse_dt(conv.get("createdAt")) or _parse_dt(conv.get("startedAt")) or datetime.now(timezone.utc)
    closed_at = _parse_dt(conv.get("closedAt"))
    assigned_at = _parse_dt(conv.get("assignedAt"))
    started_at = _parse_dt(conv.get("startedAt"))

    now = datetime.now(timezone.utc)  # noqa: F841

    ticket_id = generate_ticket_id_fn()

    ticket_doc = {
        # ---- Core Trinity fields ----
        "ticket_id": ticket_id,
        "uuid": str(uuid.uuid4()),
        "title": conv.get("subject") or f"Conversation #{conv.get('number', '')}".strip(),
        "description": "",  # Will be populated from first message
        "status": trinity_status,
        "priority": trinity_priority,
        "escalation_level": (conv.get("customFields") or conv.get("custom_fields") or {}).get("support_level", "L1"),
        "order": 0,
        "source": "atlas",
        "tags": mapped_tags,
        "custom_fields": conv.get("customFields") or {},
        "is_starred": False,
        "snoozed": is_snoozed,
        "created_by": importer_user_id,
        "created_at": created_at,
        "updated_at": _parse_dt(conv.get("closedAt")) or created_at,

        # ---- Customer info ----
        "customer_email": customer_email,
        "customer_name": _customer_name(customer),
        "customer_phone": customer.get("phoneNumber"),
        "customer_id": None,  # Will be set by get_or_create_customer later
        "domain": None,       # Will be set by extract_domain later

        # ---- Assignment ----
        "assignee_id": None,  # Mapped later by agent email lookup
        "team_id": conv.get("assignedTeamId"),

        # ---- Atlas-specific preserved fields ----
        "atlas_conversation_id": str(conv.get("id", "")),
        "atlas_customer_id": str(conv.get("customerId", "")),
        "atlas_number": conv.get("number"),
        "atlas_status": conv.get("status"),
        "atlas_priority": conv.get("priority"),
        "atlas_assigned_agent_id": conv.get("assignedAgentId") or (assigned_agent.get("id") if assigned_agent else None),
        "atlas_assigned_agent_name": _agent_name(assigned_agent),
        "atlas_assigned_agent_email": assigned_agent.get("email"),
        "atlas_assigned_team_id": conv.get("assignedTeamId"),

        # ---- Timestamps ----
        "started_at": started_at,
        "closed_at": closed_at,
        "closed_by": conv.get("closedBy"),
        "assigned_at": assigned_at,
        "assigned_by": conv.get("assignedBy"),
        "snoozed_until": snoozed_until,

        # ---- Channel info ----
        "started_channel": conv.get("startedChannel"),
        "started_sub_channel": conv.get("startedSubChannel"),

        # ---- Environment ----
        "browser": conv.get("browser"),
        "operating_system": conv.get("operatingSystem"),

        # ---- Statistics ----
        "first_response_time": stats.get("firstResponseTime"),
        "avg_response_time": stats.get("avgResponseTime"),
        "total_resolution_time": stats.get("totalResolutionTime"),

        # ---- CSAT (inline from conversation) ----
        "atlas_csat_score": csat.get("score"),
        "atlas_csat_comment": csat.get("comment"),

        # ---- Customer extended info ----
        "customer_external_user_id": customer.get("externalUserId"),
        "customer_company_id": customer.get("companyId") or customer.get("accountId"),
        "customer_company_name": account.get("name"),
        "customer_company_email": account.get("email"),
        "customer_company_website": account.get("website"),
        "customer_company_external_id": account.get("externalId"),
        "customer_custom_fields": customer.get("customFields") or {},

        # ---- Last message snapshot (for list display) ----
        "last_message_text": None,
        "last_message_at": None,

        # ---- Updated by ----
        "updated_by": conv.get("updatedBy"),
    }

    # Populate last_message snapshot if present
    last_msg = conv.get("lastMessage")
    if last_msg:
        ticket_doc["last_message_text"] = (last_msg.get("text") or "")[:200]
        ticket_doc["last_message_at"] = _parse_dt(last_msg.get("sentAt"))
        # Use last message text as description if no subject
        if not conv.get("subject"):
            ticket_doc["description"] = (last_msg.get("text") or "")[:5000]

    return ticket_doc


def map_message_to_note(
    msg: dict,
    ticket_id: str,
    atlas_conversation_id: str,
) -> dict:
    """
    Transform an Atlas message dict into a Trinity message document.
    """
    side = (msg.get("side") or "CUSTOMER").upper()
    msg_type = MESSAGE_TYPE_MAP.get(side, "customer_reply")

    agent = msg.get("agent") or {}
    customer = msg.get("customer") or {}

    # Determine author info based on side
    if side in ("AGENT", "BOT"):
        author_name = _agent_name(agent)
        author_email = agent.get("email")
        author_id = str(agent.get("id", "")) or None
    else:
        author_name = _customer_name(customer)
        author_email = customer.get("email")
        author_id = str(customer.get("id", "")) or None

    return {
        "message_id": f"atlas_msg_{msg.get('id', uuid.uuid4().hex[:12])}",
        "ticket_id": ticket_id,
        "type": msg_type,
        "content": msg.get("text") or "",
        "author_id": author_id,
        "author_name": author_name or "Unknown",
        "author_email": author_email,
        "mentions": [],
        "created_at": _parse_dt(msg.get("sentAt")) or datetime.now(timezone.utc),

        # ---- Atlas-specific preserved fields ----
        "atlas_message_id": msg.get("id"),
        "atlas_conversation_id": atlas_conversation_id,
        "atlas_side": msg.get("side"),
        "atlas_type": msg.get("type"),
        "atlas_channel": msg.get("channel"),
    }


# ==================== Import Orchestrator ====================

async def run_atlas_import(
    api_key: str,
    db_collections: dict,
    generate_ticket_id_fn,
    get_or_create_customer_fn,
    extract_domain_fn,
    importer_user_id: str,
    status_filter: str = None,
    start_date: str = None,
    end_date: str = None,
) -> dict:
    """
    Full Atlas import pipeline:
    1. Fetch all tags (for ID→name mapping)
    2. Fetch all conversations (paginated)
    3. For each conversation, fetch all messages
    4. Map and insert into Trinity DB with deduplication

    Returns a summary dict with counts and errors.
    """
    tickets_col = db_collections["tickets"]
    messages_col = db_collections["messages"]
    users_col = db_collections["users"]

    client = AtlasClient(api_key)
    summary = {
        "tags_fetched": 0,
        "conversations_fetched": 0,
        "conversations_imported": 0,
        "conversations_skipped_duplicate": 0,
        "messages_imported": 0,
        "customers_created": 0,
        "agents_mapped": 0,
        "errors": [],
    }

    # ---- Step 1: Fetch tags ----
    logger.info("[ATLAS IMPORT] Fetching tags...")
    tags = await client.fetch_all_tags()
    tag_lookup = build_tag_lookup(tags)
    summary["tags_fetched"] = len(tags)
    logger.info(f"[ATLAS IMPORT] Fetched {len(tags)} tags")

    # ---- Step 2: Fetch conversations ----
    logger.info("[ATLAS IMPORT] Fetching conversations...")
    fetch_kwargs = {}
    if status_filter:
        fetch_kwargs["status"] = status_filter
    if start_date:
        fetch_kwargs["start_date"] = start_date
    if end_date:
        fetch_kwargs["end_date"] = end_date

    conversations = await client.fetch_all_conversations(**fetch_kwargs)
    summary["conversations_fetched"] = len(conversations)
    logger.info(f"[ATLAS IMPORT] Fetched {len(conversations)} conversations")

    # Pre-build agent email → user_id lookup from existing Trinity users
    all_users = list(users_col.find({}, {"_id": 0, "user_id": 1, "email": 1, "name": 1}))
    agent_email_map = {u["email"].lower(): u["user_id"] for u in all_users if u.get("email")}

    # ---- Step 3: Process each conversation ----
    for conv in conversations:
        atlas_id = str(conv.get("id", ""))
        try:
            # Deduplication check
            existing = tickets_col.find_one({"atlas_conversation_id": atlas_id})
            if existing:
                summary["conversations_skipped_duplicate"] += 1
                continue

            # Map conversation → ticket
            ticket_doc = map_conversation_to_ticket(
                conv, tag_lookup, generate_ticket_id_fn, importer_user_id
            )

            # Link customer in Trinity
            if ticket_doc["customer_email"]:
                customer = get_or_create_customer_fn(
                    ticket_doc["customer_email"],
                    ticket_doc.get("customer_name"),
                )
                if customer:
                    ticket_doc["customer_id"] = customer.get("customer_id")
                    summary["customers_created"] += 1
                ticket_doc["domain"] = extract_domain_fn(ticket_doc["customer_email"])

            # Map assigned agent email → Trinity user_id
            agent_email = ticket_doc.get("atlas_assigned_agent_email")
            if agent_email and agent_email.lower() in agent_email_map:
                ticket_doc["assignee_id"] = agent_email_map[agent_email.lower()]
                summary["agents_mapped"] += 1

            # Fetch messages for this conversation
            messages = await client.fetch_all_messages(atlas_id)

            # Set description from first customer message
            for msg in messages:
                if (msg.get("side") or "").upper() == "CUSTOMER":
                    ticket_doc["description"] = (msg.get("text") or "")[:5000]
                    break

            # Insert ticket
            tickets_col.insert_one(ticket_doc)
            # Remove _id that mongo added
            ticket_doc.pop("_id", None)

            # Insert messages
            msg_count = 0
            for msg in messages:
                note_doc = map_message_to_note(
                    msg,
                    ticket_doc["ticket_id"],
                    atlas_id,
                )
                messages_col.insert_one(note_doc)
                msg_count += 1

            summary["messages_imported"] += msg_count
            summary["conversations_imported"] += 1

        except httpx.HTTPStatusError as e:
            err = f"HTTP {e.response.status_code} fetching messages for {atlas_id}: {str(e)}"
            logger.error(f"[ATLAS IMPORT] {err}")
            summary["errors"].append(err)
        except Exception as e:
            err = f"Error processing conversation {atlas_id}: {str(e)}"
            logger.error(f"[ATLAS IMPORT] {err}")
            summary["errors"].append(err)

    logger.info(
        f"[ATLAS IMPORT] Done. Imported {summary['conversations_imported']} conversations, "
        f"{summary['messages_imported']} messages, "
        f"skipped {summary['conversations_skipped_duplicate']} duplicates."
    )

    return summary
