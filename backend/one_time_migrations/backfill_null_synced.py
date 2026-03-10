"""
One-time backfill: Resync messages for all tickets with null/missing last_synced_at.

These tickets were synced before the last_synced_at field was introduced and may
have missing messages that the recheck phase couldn't catch (the "dead zone" bug).

Usage:
  python3 backfill_null_synced.py              # dry-run (report only)
  python3 backfill_null_synced.py --execute    # actually sync messages

Safe to run multiple times — idempotent (skips already-synced messages).
"""
import os
import sys
import time
import logging
from datetime import datetime, timezone

# Add parent dir so we can import from the backend package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import tickets_collection, messages_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("backfill")

# Reuse the sync engine
from services.atlas_sync import _sync_messages

BATCH_SIZE = 100
RATE_LIMIT_DELAY = 0.3  # seconds between Atlas API calls


def run(dry_run=True):
    query = {
        "atlas_conversation_id": {"$exists": True, "$ne": None},
        "$or": [
            {"last_synced_at": None},
            {"last_synced_at": {"$exists": False}},
        ],
    }

    total = tickets_collection.count_documents(query)
    logger.info(f"[BACKFILL] Found {total} tickets with null last_synced_at")

    if dry_run:
        logger.info("[BACKFILL] DRY RUN — pass --execute to actually sync")
        # Show breakdown by status
        for status in ["todo", "waiting", "closed"]:
            count = tickets_collection.count_documents({**query, "status": status})
            logger.info(f"  {status}: {count}")
        return

    processed = 0
    synced_msgs = 0
    errors = 0
    started = time.time()

    while True:
        batch = list(tickets_collection.find(
            query,
            {"_id": 0, "ticket_id": 1, "atlas_conversation_id": 1, "status": 1},
        ).limit(BATCH_SIZE))

        if not batch:
            break

        for ticket in batch:
            tid = ticket["ticket_id"]
            atlas_id = ticket["atlas_conversation_id"]

            try:
                new_msgs = _sync_messages(atlas_id, tid)
                synced_msgs += new_msgs

                # Mark as synced so it won't be picked up again
                tickets_collection.update_one(
                    {"ticket_id": tid},
                    {"$set": {"last_synced_at": datetime.now(timezone.utc)}},
                )

                processed += 1
                if new_msgs > 0:
                    logger.info(f"  {tid}: +{new_msgs} new messages")

                if processed % 500 == 0:
                    elapsed = time.time() - started
                    rate = processed / elapsed * 60
                    remaining = (total - processed) / rate if rate > 0 else 0
                    logger.info(f"[BACKFILL] Progress: {processed}/{total} ({synced_msgs} msgs, {errors} errors, {rate:.0f}/min, ~{remaining:.0f} min left)")

            except Exception as e:
                errors += 1
                logger.warning(f"  {tid}: ERROR — {e}")
                # Still mark as synced to avoid infinite retry loop
                tickets_collection.update_one(
                    {"ticket_id": tid},
                    {"$set": {"last_synced_at": datetime.now(timezone.utc)}},
                )

            time.sleep(RATE_LIMIT_DELAY)

    elapsed = time.time() - started
    logger.info(f"[BACKFILL] Done: {processed}/{total} tickets, {synced_msgs} new messages, {errors} errors in {elapsed:.0f}s")


if __name__ == "__main__":
    execute = "--execute" in sys.argv
    run(dry_run=not execute)
