"""
Atlas conversation sync — imports agent replies from Atlas into Trinity tickets.
One-time 30-day sync + ongoing periodic sync.
"""
import os
import re
import uuid
import json
import logging
import time
import requests
from datetime import datetime, timezone, timedelta

from database import (
    tickets_collection, messages_collection, email_threads_collection, db
)

logger = logging.getLogger("atlas_sync")

ATLAS_API = "https://api.atlas.so/v1"
ATLAS_KEY = os.environ.get("ATLAS_API_KEY", "")

# Sync state collection
atlas_sync_state = db.atlas_sync_state


def _headers():
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {ATLAS_KEY}",
    }


def _get_sync_cursor():
    """Get the last synced cursor position."""
    state = atlas_sync_state.find_one({"_type": "sync_cursor"})
    return state.get("cursor", 0) if state else 0


def _set_sync_cursor(cursor):
    atlas_sync_state.update_one(
        {"_type": "sync_cursor"},
        {"$set": {"cursor": cursor, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


def _find_trinity_ticket(customer_email):
    """Find a Trinity ticket by customer email. Returns the most recent open one."""
    if not customer_email:
        return None
    ticket = tickets_collection.find_one(
        {"customer_email": {"$regex": f"^{re.escape(customer_email)}$", "$options": "i"}},
        {"_id": 0, "ticket_id": 1, "title": 1},
        sort=[("created_at", -1)],
    )
    return ticket


def _is_message_synced(atlas_msg_id):
    """Check if an Atlas message has already been synced."""
    return messages_collection.find_one({"atlas_message_id": atlas_msg_id}) is not None


def _strip_html(html):
    """Strip HTML tags to get plain text."""
    if not html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    import html as html_lib
    text = html_lib.unescape(text)
    return text.strip()


def sync_conversation(conv_id, customer_email, conv_subject):
    """Sync messages from a single Atlas conversation into Trinity."""
    try:
        resp = requests.get(
            f"{ATLAS_API}/conversations/{conv_id}/messages",
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning(f"[ATLAS] Failed to fetch messages for {conv_id}: {resp.status_code}")
            return 0

        data = resp.json()
        msgs = data if isinstance(data, list) else data.get("data", data.get("messages", []))

        # Find the matching Trinity ticket
        ticket = _find_trinity_ticket(customer_email)
        if not ticket:
            return 0

        ticket_id = ticket["ticket_id"]
        synced = 0

        for msg in msgs:
            side = msg.get("side")
            # Only sync agent and bot replies (customer messages already come via IMAP)
            if side not in ("agent", "bot"):
                continue

            atlas_msg_id = msg.get("id")
            if not atlas_msg_id:
                continue

            # Skip already synced
            if _is_message_synced(atlas_msg_id):
                continue

            agent = msg.get("agent") or {}
            agent_name = f"{agent.get('firstName', '')} {agent.get('lastName', '')}".strip()
            agent_email = agent.get("email", "")
            text_html = msg.get("text", "")
            text_plain = _strip_html(text_html)
            created_at = msg.get("createdAt") or msg.get("sentAt")

            if not text_plain:
                continue

            # Convert epoch to datetime
            if isinstance(created_at, (int, float)):
                created_dt = datetime.fromtimestamp(created_at, tz=timezone.utc)
            else:
                created_dt = datetime.now(timezone.utc)

            msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            messages_collection.insert_one({
                "message_id": msg_id,
                "ticket_id": ticket_id,
                "type": "reply",
                "content": text_plain[:10000],
                "author_id": None,
                "author_name": agent_name or "Atlas Agent",
                "author_email": agent_email,
                "source": "atlas",
                "atlas_message_id": atlas_msg_id,
                "created_at": created_dt,
            })
            synced += 1

        if synced:
            tickets_collection.update_one(
                {"ticket_id": ticket_id},
                {"$set": {"updated_at": datetime.now(timezone.utc)}},
            )
            logger.info(f"[ATLAS] Synced {synced} agent messages into {ticket_id} from conv {conv_id}")

        return synced

    except requests.Timeout:
        logger.warning(f"[ATLAS] Timeout fetching messages for {conv_id}")
        return 0
    except Exception as e:
        logger.error(f"[ATLAS] Error syncing conv {conv_id}: {e}")
        return 0


def run_sync(start_cursor=42200, batch_size=100, max_batches=None):
    """
    Run the Atlas sync from a starting cursor.
    Fetches conversations in batches and syncs agent messages.
    """
    if not ATLAS_KEY:
        logger.error("[ATLAS] No API key configured")
        return

    cursor = start_cursor
    total_synced = 0
    total_convs = 0
    batch_count = 0
    skipped = 0

    logger.info(f"[ATLAS] Starting sync from cursor {cursor}")

    while True:
        if max_batches and batch_count >= max_batches:
            break

        try:
            resp = requests.get(
                f"{ATLAS_API}/conversations",
                params={"cursor": cursor, "limit": batch_size},
                headers=_headers(),
                timeout=15,
            )
            if resp.status_code != 200:
                logger.error(f"[ATLAS] API error {resp.status_code}")
                break

            data = resp.json()
            convs = data.get("data", [])
            total_api = data.get("total", 0)

            if not convs:
                logger.info(f"[ATLAS] No more conversations at cursor {cursor}")
                break

            for conv in convs:
                total_convs += 1
                channel = conv.get("startedChannel", "")
                customer = conv.get("customer") or {}
                customer_email = customer.get("email")
                conv_id = conv.get("id")
                conv_subject = conv.get("subject", "")

                # Only sync EMAIL conversations with a customer email
                if channel != "EMAIL" or not customer_email:
                    skipped += 1
                    continue

                synced = sync_conversation(conv_id, customer_email, conv_subject)
                total_synced += synced

            cursor += batch_size
            batch_count += 1
            _set_sync_cursor(cursor)

            if batch_count % 10 == 0:
                logger.info(f"[ATLAS] Progress: cursor={cursor} convs={total_convs} synced={total_synced} skipped={skipped}")

            # Rate limit: ~2 requests per conversation (list + messages), keep it gentle
            time.sleep(0.5)

        except requests.Timeout:
            logger.warning(f"[ATLAS] Timeout at cursor {cursor}, retrying")
            time.sleep(5)
            continue
        except Exception as e:
            logger.error(f"[ATLAS] Error at cursor {cursor}: {e}")
            time.sleep(5)
            cursor += batch_size
            continue

    logger.info(f"[ATLAS] Sync complete: convs={total_convs} synced={total_synced} skipped={skipped} final_cursor={cursor}")
    return {"conversations": total_convs, "messages_synced": total_synced, "skipped": skipped}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    run_sync(start_cursor=42200)
