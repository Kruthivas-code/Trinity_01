"""
One-time migration: Remove zero-padding from ticket IDs.

Converts TKT-070723 → TKT-70723 across all collections.

Usage:
  python3 migrate_ticket_id_format.py              # dry-run
  python3 migrate_ticket_id_format.py --execute    # actually migrate
"""
import os
import sys
import re
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import (
    tickets_collection, messages_collection, db,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("ticket_id_migration")

# All collections that reference ticket_id
REFERENCE_COLLECTIONS = [
    "messages",
    "email_replies",
    "ticket_changelog",
    "email_threads",
    "csat_responses",
]

PADDED_RE = re.compile(r"^TKT-0+(\d+)$")


def strip_padding(ticket_id: str) -> str:
    """TKT-070723 → TKT-70723, TKT-000001 → TKT-1"""
    m = PADDED_RE.match(ticket_id)
    if m:
        return f"TKT-{m.group(1)}"
    return ticket_id


def run(dry_run=True):
    # Find all tickets with zero-padded IDs
    padded_tickets = list(tickets_collection.find(
        {"ticket_id": {"$regex": r"^TKT-0\d+$"}},
        {"_id": 0, "ticket_id": 1},
    ))

    logger.info(f"Found {len(padded_tickets)} tickets with zero-padded IDs")

    if dry_run:
        # Show samples
        for t in padded_tickets[:10]:
            old = t["ticket_id"]
            new = strip_padding(old)
            logger.info(f"  {old} → {new}")
        if len(padded_tickets) > 10:
            logger.info(f"  ... and {len(padded_tickets) - 10} more")
        logger.info("DRY RUN — pass --execute to migrate")
        return

    started = time.time()
    migrated = 0
    errors = 0

    for t in padded_tickets:
        old_id = t["ticket_id"]
        new_id = strip_padding(old_id)

        if old_id == new_id:
            continue

        try:
            # Update primary ticket
            tickets_collection.update_one(
                {"ticket_id": old_id},
                {"$set": {"ticket_id": new_id}},
            )

            # Update all reference collections
            for coll_name in REFERENCE_COLLECTIONS:
                coll = db[coll_name]
                coll.update_many(
                    {"ticket_id": old_id},
                    {"$set": {"ticket_id": new_id}},
                )

            migrated += 1

            if migrated % 5000 == 0:
                elapsed = time.time() - started
                rate = migrated / elapsed
                remaining = (len(padded_tickets) - migrated) / rate if rate > 0 else 0
                logger.info(f"  Progress: {migrated}/{len(padded_tickets)} ({rate:.0f}/s, ~{remaining:.0f}s left)")

        except Exception as e:
            errors += 1
            logger.warning(f"  ERROR migrating {old_id}: {e}")

    elapsed = time.time() - started
    logger.info(f"Done: {migrated} migrated, {errors} errors in {elapsed:.1f}s")


if __name__ == "__main__":
    execute = "--execute" in sys.argv
    run(dry_run=not execute)
