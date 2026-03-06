"""
One-time migration: Align ticket numbers between Atlas and Trinity.

Steps:
  1. Delete non-Atlas tickets (email poller duplicates) and their references
  2. Rename Atlas tickets to use atlas_number (TKT-048694 -> TKT-003633)
  3. Update all referencing collections (messages, email_threads, etc.)
  4. Fix escalation_level from custom_fields.support_level
  5. Resolve UUID tags to human-readable names via Atlas API
  6. Reset the ticket counter to max(atlas_number) + 1

Usage:
    cd /app/backend && python3 scripts/ticket_number_migration.py
"""

import os
import sys
import logging
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from database import db, tickets_collection, messages_collection, counters_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("migration")

ATLAS_API = "https://api.atlas.so/v1"
ATLAS_KEY = os.environ.get("ATLAS_API_KEY", "")

# Collections that reference ticket_id
REF_COLLECTIONS = [
    "messages",
    "email_threads",
    "ticket_changelog",
    "notifications",
    "email_replies",
    "csat_tokens",
    "csat_responses",
]
# These use different field names
SPECIAL_REFS = {
    "feature_requests": "linked_ticket_ids",  # array field
    "knowledge_snippets": "source_ticket_id",
}


def step_1_delete_non_atlas():
    """Delete all non-Atlas tickets and their references."""
    logger.info("=== Step 1: Delete non-Atlas tickets ===")

    non_atlas_ids = [
        t["ticket_id"]
        for t in tickets_collection.find(
            {"atlas_conversation_id": {"$exists": False}},
            {"_id": 0, "ticket_id": 1},
        )
    ]
    count = len(non_atlas_ids)
    if count == 0:
        logger.info("No non-Atlas tickets to delete")
        return

    logger.info(f"Deleting {count} non-Atlas tickets and their references...")

    batch_size = 500
    for i in range(0, count, batch_size):
        batch = non_atlas_ids[i : i + batch_size]

        # Delete from referencing collections
        for col_name in REF_COLLECTIONS:
            col = db[col_name]
            r = col.delete_many({"ticket_id": {"$in": batch}})
            if r.deleted_count:
                logger.info(f"  {col_name}: deleted {r.deleted_count}")

        # Handle feature_requests (array field)
        db["feature_requests"].update_many(
            {"linked_ticket_ids": {"$in": batch}},
            {"$pullAll": {"linked_ticket_ids": batch}},
        )

        # Delete tickets
        r = tickets_collection.delete_many({"ticket_id": {"$in": batch}})
        logger.info(f"  Batch {i // batch_size + 1}: deleted {r.deleted_count} tickets")

    logger.info(f"Step 1 complete: deleted {count} non-Atlas tickets")


def step_2_rename_tickets():
    """Rename Atlas tickets to use atlas_number."""
    logger.info("=== Step 2: Rename Atlas tickets to atlas_number ===")

    # Build the rename map: old_id -> new_id
    atlas_tickets = list(
        tickets_collection.find(
            {"atlas_number": {"$exists": True}},
            {"_id": 0, "ticket_id": 1, "atlas_number": 1},
        )
    )

    # Check if already migrated (ticket_id matches atlas_number)
    already_done = 0
    rename_map = {}
    for t in atlas_tickets:
        expected_id = f"TKT-{t['atlas_number']:06d}"
        if t["ticket_id"] == expected_id:
            already_done += 1
        else:
            rename_map[t["ticket_id"]] = expected_id

    if not rename_map:
        logger.info(f"All {already_done} tickets already have correct IDs")
        return

    logger.info(f"Renaming {len(rename_map)} tickets ({already_done} already correct)")

    # Check for collisions: new IDs that already exist as different tickets
    new_ids = set(rename_map.values())
    existing_ids = set(
        t["ticket_id"]
        for t in tickets_collection.find(
            {"ticket_id": {"$in": list(new_ids)}}, {"_id": 0, "ticket_id": 1}
        )
    )
    collisions = existing_ids - set(rename_map.keys())
    if collisions:
        logger.error(f"COLLISION: {len(collisions)} target IDs already exist: {list(collisions)[:5]}")
        logger.error("Aborting rename. Run step 1 first to clean up non-Atlas tickets.")
        return

    # Process renames in batches
    items = list(rename_map.items())
    batch_size = 200
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]

        for old_id, new_id in batch:
            # Rename in tickets collection
            tickets_collection.update_one(
                {"ticket_id": old_id}, {"$set": {"ticket_id": new_id}}
            )

            # Update referencing collections
            for col_name in REF_COLLECTIONS:
                db[col_name].update_many(
                    {"ticket_id": old_id}, {"$set": {"ticket_id": new_id}}
                )

            # Handle feature_requests (array field)
            db["feature_requests"].update_many(
                {"linked_ticket_ids": old_id},
                {"$set": {"linked_ticket_ids.$": new_id}},
            )

            # Handle knowledge_snippets
            db["knowledge_snippets"].update_many(
                {"source_ticket_id": old_id},
                {"$set": {"source_ticket_id": new_id}},
            )

            # Handle csat_tokens.ticket_title (not a ticket_id, but might contain the ID)
            # Skip - title is separate from ticket_id

        logger.info(
            f"  Batch {i // batch_size + 1}/{(len(items) + batch_size - 1) // batch_size}: "
            f"renamed {len(batch)} tickets"
        )

    logger.info(f"Step 2 complete: renamed {len(rename_map)} tickets")


def step_3_fix_escalation_levels():
    """Update escalation_level from custom_fields.support_level."""
    logger.info("=== Step 3: Fix escalation levels ===")

    valid_levels = {"L1", "L2", "L3"}

    for level in ["L1", "L2", "L3"]:
        result = tickets_collection.update_many(
            {
                "atlas_conversation_id": {"$exists": True},
                "custom_fields.support_level": level,
                "escalation_level": {"$ne": level},
            },
            {"$set": {"escalation_level": level}},
        )
        if result.modified_count:
            logger.info(f"  Set escalation_level={level} for {result.modified_count} tickets")

    logger.info("Step 3 complete")


def step_4_resolve_tags():
    """Resolve UUID tags to human-readable names using Atlas API."""
    logger.info("=== Step 4: Resolve UUID tags ===")

    if not ATLAS_KEY:
        logger.error("No ATLAS_API_KEY — skipping tag resolution")
        return

    # Fetch tag lookup from Atlas
    headers = {"Authorization": f"Bearer {ATLAS_KEY}", "Accept": "application/json"}
    resp = requests.get(f"{ATLAS_API}/tags?limit=500", headers=headers, timeout=30)
    if not resp.ok:
        logger.error(f"Failed to fetch tags: {resp.status_code}")
        return

    data = resp.json()
    tags = data if isinstance(data, list) else data.get("data", data.get("tags", []))
    tag_lookup = {}
    for t in tags:
        tid = str(t.get("id", ""))
        tname = t.get("label") or t.get("name") or tid
        if tid:
            tag_lookup[tid] = tname

    logger.info(f"Fetched {len(tag_lookup)} tag mappings from Atlas")

    # Find tickets with UUID tags and resolve them
    import re
    uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-")

    cursor = tickets_collection.find(
        {"atlas_conversation_id": {"$exists": True}, "tags": {"$exists": True, "$ne": []}},
        {"_id": 0, "ticket_id": 1, "tags": 1},
    )

    updated = 0
    for ticket in cursor:
        old_tags = ticket.get("tags", [])
        new_tags = []
        changed = False
        for tag in old_tags:
            if uuid_pattern.match(str(tag)) and str(tag) in tag_lookup:
                new_tags.append(tag_lookup[str(tag)])
                changed = True
            else:
                new_tags.append(tag)

        if changed:
            tickets_collection.update_one(
                {"ticket_id": ticket["ticket_id"]},
                {"$set": {"tags": new_tags}},
            )
            updated += 1

    logger.info(f"Step 4 complete: resolved tags on {updated} tickets")


def step_5_reset_counter():
    """Reset the ticket counter to max(atlas_number) + 1."""
    logger.info("=== Step 5: Reset ticket counter ===")

    pipeline = [
        {"$match": {"atlas_number": {"$exists": True}}},
        {"$group": {"_id": None, "max_num": {"$max": "$atlas_number"}}},
    ]
    result = list(tickets_collection.aggregate(pipeline))
    if not result:
        logger.warning("No atlas_number found — skipping counter reset")
        return

    max_num = result[0]["max_num"]
    new_seq = max_num  # generate_ticket_id does $inc first, so next ID = max_num + 1

    counters_collection.update_one(
        {"_id": "ticket_id"},
        {"$set": {"seq": new_seq}},
        upsert=True,
    )
    logger.info(f"Counter reset: seq={new_seq} (next ticket will be TKT-{new_seq + 1:06d})")
    logger.info("Step 5 complete")


def run_migration():
    """Run the full migration."""
    logger.info("=" * 60)
    logger.info("TICKET NUMBER MIGRATION — Starting")
    logger.info("=" * 60)

    # Pre-flight checks
    atlas_count = tickets_collection.count_documents({"atlas_conversation_id": {"$exists": True}})
    non_atlas_count = tickets_collection.count_documents({"atlas_conversation_id": {"$exists": False}})
    logger.info(f"Before: {atlas_count} Atlas tickets, {non_atlas_count} non-Atlas tickets")

    step_1_delete_non_atlas()
    step_2_rename_tickets()
    step_3_fix_escalation_levels()
    step_4_resolve_tags()
    step_5_reset_counter()

    # Post-flight summary
    final_count = tickets_collection.count_documents({})
    logger.info("=" * 60)
    logger.info(f"MIGRATION COMPLETE: {final_count} tickets remain")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_migration()
