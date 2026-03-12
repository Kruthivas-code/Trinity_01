"""
Deduplicate historical IMAP messages.
======================================

Scans for duplicate messages on the same ticket with identical content.
Keeps the earliest message and removes duplicates.

This handles both:
  - Atlas-sourced duplicates (same atlas_message_id on same ticket)
  - IMAP-sourced duplicates (same content hash on same ticket)

Usage:
  python -m one_time_migrations.dedup_messages          # dry run
  python -m one_time_migrations.dedup_messages --apply  # apply changes
"""

import os
import sys
import hashlib
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import messages_collection

logger = logging.getLogger("dedup_messages")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def run_migration(dry_run: bool = True):
    logger.info(f"{'DRY RUN' if dry_run else 'APPLYING'} — Deduplicate messages")

    stats = {"atlas_dupes": 0, "content_dupes": 0, "deleted": 0}

    # Phase 1: Deduplicate by atlas_message_id + ticket_id
    logger.info("Phase 1: Checking Atlas message duplicates...")
    pipeline = [
        {"$match": {"atlas_message_id": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": {"ticket_id": "$ticket_id", "atlas_msg_id": "$atlas_message_id"},
            "count": {"$sum": 1},
            "msg_ids": {"$push": "$message_id"},
            "created_dates": {"$push": "$created_at"},
        }},
        {"$match": {"count": {"$gt": 1}}},
    ]
    atlas_dupes = list(messages_collection.aggregate(pipeline, allowDiskUse=True))
    stats["atlas_dupes"] = len(atlas_dupes)

    for group in atlas_dupes:
        # Keep the first (oldest) message, delete the rest
        msg_ids = group["msg_ids"]
        to_delete = msg_ids[1:]  # keep first
        stats["deleted"] += len(to_delete)
        if not dry_run:
            messages_collection.delete_many({"message_id": {"$in": to_delete}})
        else:
            logger.info(f"  [DRY] Would delete {len(to_delete)} dupes for atlas_msg={group['_id']['atlas_msg_id'][:16]}...")

    logger.info(f"  Atlas duplicate groups: {stats['atlas_dupes']}, excess: {stats['deleted']}")

    # Phase 2: Deduplicate IMAP messages by content hash + ticket_id
    logger.info("Phase 2: Checking IMAP content duplicates...")
    # Only check non-atlas, non-system messages
    imap_pipeline = [
        {"$match": {
            "atlas_message_id": {"$exists": False},
            "type": {"$in": ["customer_reply", "original", "reply", "email", None]},
        }},
        {"$group": {
            "_id": "$ticket_id",
            "msgs": {"$push": {
                "message_id": "$message_id",
                "content": {"$ifNull": ["$content", {"$ifNull": ["$text", ""]}]},
                "created_at": "$created_at",
            }},
            "count": {"$sum": 1},
        }},
        {"$match": {"count": {"$gt": 1}}},
    ]

    content_dupes_deleted = 0
    for group in messages_collection.aggregate(imap_pipeline, allowDiskUse=True):
        seen_hashes = {}
        for msg in sorted(group["msgs"], key=lambda m: str(m.get("created_at", ""))):
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            h = hashlib.md5(content.encode()).hexdigest()
            if h in seen_hashes:
                content_dupes_deleted += 1
                stats["content_dupes"] += 1
                if not dry_run:
                    messages_collection.delete_one({"message_id": msg["message_id"]})
            else:
                seen_hashes[h] = msg["message_id"]

    stats["deleted"] += content_dupes_deleted
    logger.info(f"  Content duplicate messages: {content_dupes_deleted}")

    logger.info(f"\n{'='*60}")
    logger.info(f"Dedup {'DRY RUN' if dry_run else 'COMPLETE'}")
    logger.info(f"  Atlas duplicates: {stats['atlas_dupes']} groups")
    logger.info(f"  Content duplicates: {stats['content_dupes']}")
    logger.info(f"  Total deleted: {stats['deleted']}")
    return stats


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    dry_run = "--apply" not in sys.argv
    if dry_run:
        print("\n  Run with --apply to execute changes.\n")
    run_migration(dry_run=dry_run)
