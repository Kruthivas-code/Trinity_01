"""
Zeus (AI) Ticket Cleanup Job
=============================
Recurring job that:
1. Closes Zeus-assigned tickets with no reply in the last 48 hours
   (on both Trinity and Atlas)
2. Runs every 30 minutes as a background task
"""

import os
import logging
import requests
from datetime import datetime, timezone, timedelta

from database import db, tickets_collection, messages_collection

logger = logging.getLogger("zeus_cleanup")

ATLAS_API = "https://api.atlas.so/v1"
ATLAS_KEY = os.environ.get("ATLAS_API_KEY", "")
STALE_HOURS = 48


def _headers():
    return {"Accept": "application/json", "Authorization": f"Bearer {ATLAS_KEY}"}


def _close_on_atlas(atlas_conv_id: str) -> bool:
    """Close a conversation on Atlas. Returns True on success."""
    if not ATLAS_KEY or not atlas_conv_id:
        return False
    try:
        resp = requests.post(
            f"{ATLAS_API}/conversations/{atlas_conv_id}",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"status": "CLOSED"},
            timeout=15,
        )
        if resp.status_code in (200, 201, 204):
            return True
        logger.warning(f"[ZEUS] Atlas close failed for {atlas_conv_id}: {resp.status_code} {resp.text[:200]}")
        return False
    except Exception as e:
        logger.warning(f"[ZEUS] Atlas close error for {atlas_conv_id}: {e}")
        return False


def run_cleanup(batch_size: int = 500) -> dict:
    """
    Close a batch of Zeus-assigned tickets that are stale (> 48h since last message).
    Processes up to batch_size tickets per run. Recurring job handles the rest.
    Returns stats dict.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=STALE_HOURS)
    now = datetime.now(timezone.utc)

    stats = {
        "trinity_closed": 0,
        "atlas_closed": 0,
        "atlas_failed": 0,
        "remaining": 0,
        "run_at": now.isoformat(),
    }

    # Find open Zeus tickets with no recent messages
    query = {
        "atlas_assigned_to_zeus": True,
        "status": {"$ne": "closed"},
        "$or": [
            {"last_message_at": {"$lt": cutoff}},
            {"last_message_at": None},
            {"last_message_at": {"$exists": False}},
        ],
    }

    total_stale = tickets_collection.count_documents(query)
    stats["remaining"] = max(0, total_stale - batch_size)

    stale_tickets = list(tickets_collection.find(
        query,
        {"_id": 0, "ticket_id": 1, "atlas_conversation_id": 1, "status": 1,
         "last_message_at": 1},
    ).limit(batch_size))

    logger.info(f"[ZEUS] Found {len(stale_tickets)} stale Zeus tickets to close")

    for ticket in stale_tickets:
        ticket_id = ticket["ticket_id"]
        atlas_conv_id = ticket.get("atlas_conversation_id")

        # Close on Trinity
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": {
                "status": "closed",
                "closed_at": now,
                "resolved_at": now,
                "closed_by": "zeus_cleanup",
                "updated_at": now,
            }},
        )

        # Add system message
        messages_collection.insert_one({
            "message_id": f"sys_zeus_{ticket_id}_{int(now.timestamp())}",
            "ticket_id": ticket_id,
            "type": "system",
            "content": f"Auto-closed: AI-assigned ticket with no reply for {STALE_HOURS}+ hours",
            "author_name": "System",
            "source": "zeus_cleanup",
            "created_at": now,
        })

        stats["trinity_closed"] += 1

        # Close on Atlas (background, non-blocking)
        if atlas_conv_id:
            if _close_on_atlas(atlas_conv_id):
                stats["atlas_closed"] += 1
            else:
                stats["atlas_failed"] += 1

    # Save last run stats
    db.atlas_backfill_state.update_one(
        {"_type": "zeus_cleanup"},
        {"$set": {
            "_type": "zeus_cleanup",
            **stats,
            "last_run_at": now,
        }},
        upsert=True,
    )

    logger.info(
        f"[ZEUS] Cleanup done: {stats['trinity_closed']} closed on Trinity, "
        f"{stats['atlas_closed']} closed on Atlas, {stats['atlas_failed']} Atlas failures"
    )
    return stats


def get_cleanup_status() -> dict:
    """Get last cleanup run stats."""
    state = db.atlas_backfill_state.find_one({"_type": "zeus_cleanup"}, {"_id": 0, "_type": 0})
    if not state:
        return {"status": "never_run"}
    return state
