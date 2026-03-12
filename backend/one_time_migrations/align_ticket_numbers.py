"""
Align Trinity ticket IDs with Atlas conversation numbers.
==========================================================

Problem:
  Tickets have ticket_id != TKT-{atlas_number}. Their target slots are
  occupied by IMAP-only tickets (no atlas link) or chain-linked Atlas tickets.

Strategy:
  1. Clean up any _TMP_ prefixes from previous partial runs
  2. For each mismatched ticket, check if target is occupied
  3. If occupied by IMAP-only: rename IMAP ticket out of the way first
  4. If occupied by another Atlas ticket: use chain-swap logic
  5. Place the mismatched ticket at its correct TKT-{atlas_number}

Usage:
  python -m one_time_migrations.align_ticket_numbers          # dry run
  python -m one_time_migrations.align_ticket_numbers --apply  # apply changes
"""

import os
import sys
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db, tickets_collection

logger = logging.getLogger("align_ticket_numbers")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

REFERENCE_COLLECTIONS = [
    "messages", "email_threads", "ticket_changelog",
    "notifications", "email_replies", "csat_tokens", "csat_responses",
]

# Counter for generating unique IMAP IDs
_next_imap_id = None

def _get_next_imap_id():
    """Get the next available ticket number for IMAP relocation."""
    global _next_imap_id
    if _next_imap_id is None:
        # Find the highest existing ticket number
        pipeline = [
            {"$match": {"ticket_id": {"$regex": "^TKT-[0-9]+$"}}},
            {"$project": {"num": {"$toInt": {"$substr": ["$ticket_id", 4, -1]}}}},
            {"$sort": {"num": -1}},
            {"$limit": 1},
        ]
        result = list(tickets_collection.aggregate(pipeline))
        _next_imap_id = (result[0]["num"] + 1) if result else 100000
    _next_imap_id += 1
    return _next_imap_id


def _rename_ticket(old_id: str, new_id: str, dry_run: bool) -> int:
    """Rename a ticket_id and update all cross-collection references."""
    ref_count = 0
    if not dry_run:
        tickets_collection.update_one(
            {"ticket_id": old_id},
            {"$set": {"ticket_id": new_id}},
        )
        for col_name in REFERENCE_COLLECTIONS:
            result = db[col_name].update_many(
                {"ticket_id": old_id},
                {"$set": {"ticket_id": new_id}},
            )
            ref_count += result.modified_count
    return ref_count


def run_migration(dry_run: bool = True):
    logger.info(f"{'DRY RUN' if dry_run else 'APPLYING'} — Align ticket numbers with Atlas")

    stats = {"total_mismatched": 0, "renamed": 0, "imap_relocated": 0,
             "chains_resolved": 0, "refs_updated": 0, "skipped": 0}

    # Step 1: Build the full mismatch map (including _TMP_ prefixed from previous runs)
    mismatches = {}
    for t in tickets_collection.find(
        {"atlas_number": {"$exists": True, "$ne": None}},
        {"_id": 0, "ticket_id": 1, "atlas_number": 1},
    ):
        target = f"TKT-{t['atlas_number']}"
        if t["ticket_id"] != target:
            mismatches[t["ticket_id"]] = target

    stats["total_mismatched"] = len(mismatches)
    if not mismatches:
        logger.info("No mismatched ticket IDs found. Done.")
        return stats

    logger.info(f"Found {len(mismatches)} mismatched tickets to align")

    # Step 2: Process each mismatch
    processed = set()

    for current_id, target_id in list(mismatches.items()):
        if current_id in processed:
            continue

        # Check what's at the target slot
        occupier = tickets_collection.find_one(
            {"ticket_id": target_id},
            {"_id": 0, "ticket_id": 1, "atlas_number": 1, "atlas_conversation_id": 1},
        ) if not dry_run else None

        if dry_run or not occupier:
            # Target is free (or dry run) — direct rename
            refs = _rename_ticket(current_id, target_id, dry_run)
            stats["renamed"] += 1
            stats["refs_updated"] += refs
            processed.add(current_id)
            continue

        # Target is occupied
        occ_atlas_num = occupier.get("atlas_number")
        occ_atlas_conv = occupier.get("atlas_conversation_id")

        if not occ_atlas_conv:
            # Occupier is an IMAP-only ticket — relocate it to a new number
            new_imap_id = f"TKT-{_get_next_imap_id()}"
            refs = _rename_ticket(target_id, new_imap_id, dry_run)
            stats["imap_relocated"] += 1
            stats["refs_updated"] += refs
            logger.debug(f"  Relocated IMAP {target_id} → {new_imap_id}")

            # Now place the Atlas ticket
            refs = _rename_ticket(current_id, target_id, dry_run)
            stats["renamed"] += 1
            stats["refs_updated"] += refs
            processed.add(current_id)

        elif occ_atlas_num and f"TKT-{occ_atlas_num}" != target_id:
            # Occupier is also a mismatched Atlas ticket — chain swap
            # Park current to temp, place occupier first (if possible), then place current
            tmp_id = f"_SWAP_{current_id}"
            _rename_ticket(current_id, tmp_id, dry_run)

            # Try to place the occupier at ITS target
            occ_target = f"TKT-{occ_atlas_num}"
            occ_conflict = tickets_collection.find_one({"ticket_id": occ_target})
            if not occ_conflict:
                refs = _rename_ticket(target_id, occ_target, dry_run)
                stats["renamed"] += 1
                stats["refs_updated"] += refs
                processed.add(target_id)
                if target_id in mismatches:
                    processed.add(target_id)
            else:
                # Deeper chain — just relocate the occupier for now
                new_id = f"TKT-{_get_next_imap_id()}"
                refs = _rename_ticket(target_id, new_id, dry_run)
                stats["refs_updated"] += refs

            # Place current at its target (now free)
            refs = _rename_ticket(tmp_id, target_id, dry_run)
            stats["renamed"] += 1
            stats["refs_updated"] += refs
            stats["chains_resolved"] += 1
            processed.add(current_id)

        else:
            # Occupier has same atlas_number as its ticket_id — it's correct
            # This shouldn't happen, but skip to be safe
            stats["skipped"] += 1
            logger.warning(f"  SKIP {current_id} → {target_id}: occupier is correctly placed")

    # Final count
    still_mismatched = 0
    if not dry_run:
        for t in tickets_collection.find(
            {"atlas_number": {"$exists": True, "$ne": None}},
            {"_id": 0, "ticket_id": 1, "atlas_number": 1},
        ):
            if t["ticket_id"] != f"TKT-{t['atlas_number']}":
                still_mismatched += 1

    logger.info(f"\n{'='*60}")
    logger.info(f"Migration {'DRY RUN' if dry_run else 'COMPLETE'}")
    logger.info(f"  Total mismatched: {stats['total_mismatched']}")
    logger.info(f"  Renamed to correct ID: {stats['renamed']}")
    logger.info(f"  IMAP tickets relocated: {stats['imap_relocated']}")
    logger.info(f"  Chains resolved: {stats['chains_resolved']}")
    logger.info(f"  Refs updated: {stats['refs_updated']}")
    logger.info(f"  Still mismatched: {still_mismatched}")
    return stats


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    dry_run = "--apply" not in sys.argv
    if dry_run:
        print("\n  Run with --apply to execute changes.\n")
    run_migration(dry_run=dry_run)
