"""
Fix @imported.local placeholder emails and merge ghost user records.
==================================================================

Problem:
  25 users were imported with placeholder emails like 'animesh@imported.local'.
  When these users log in via Google OAuth with their real email (animesh@emergent.sh),
  the auth flow creates a NEW "ghost" user record because the email doesn't match.
  This results in TWO records for the same person — tickets reference the imported
  user_id, but the session uses the ghost user_id.

Fix:
  1. For each @imported.local user, look up their real email via Atlas API (using atlas_user_id)
  2. If a ghost record with the real email exists, merge it into the imported record
  3. Update the imported record's email to the real email
  4. Update ALL references from ghost user_id to imported user_id across all collections

Usage:
  python -m one_time_migrations.fix_imported_local_emails          # dry run (default)
  python -m one_time_migrations.fix_imported_local_emails --apply  # apply changes
"""

import os
import sys
import logging
import requests
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db, users_collection, tickets_collection, messages_collection, sessions_collection

logger = logging.getLogger("fix_imported_local")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ATLAS_API = "https://api.atlas.so/v1"
ATLAS_KEY = os.environ.get("ATLAS_API_KEY", "")


def _fetch_atlas_agent_email_by_id(atlas_user_id: str) -> str:
    """Look up an Atlas agent's real email by their Atlas user ID."""
    if not ATLAS_KEY or not atlas_user_id:
        return ""
    try:
        resp = requests.get(
            f"{ATLAS_API}/users",
            params={"limit": 200},
            headers={"Authorization": f"Bearer {ATLAS_KEY}", "Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        agents = data.get("data", data) if isinstance(data, dict) else data
        for agent in agents:
            if str(agent.get("id", "")) == str(atlas_user_id):
                return (agent.get("email") or "").lower().strip()
    except Exception as e:
        logger.error(f"Atlas API lookup failed for {atlas_user_id}: {e}")
    return ""


def _build_atlas_id_to_email_map() -> dict:
    """Build a complete atlas_user_id → real_email mapping from Atlas API."""
    if not ATLAS_KEY:
        logger.error("No ATLAS_API_KEY configured")
        return {}
    all_agents = []
    cursor = 0
    while True:
        try:
            resp = requests.get(
                f"{ATLAS_API}/users",
                params={"cursor": cursor, "limit": 200},
                headers={"Authorization": f"Bearer {ATLAS_KEY}", "Accept": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            agents = data.get("data", data) if isinstance(data, dict) else data
            if not agents:
                break
            all_agents.extend(agents)
            total = data.get("total", 0) if isinstance(data, dict) else 0
            if len(all_agents) >= total or not total:
                break
            cursor += len(agents)
        except Exception as e:
            logger.error(f"Failed to fetch Atlas users at cursor {cursor}: {e}")
            break

    mapping = {}
    for agent in all_agents:
        aid = str(agent.get("id", ""))
        email = (agent.get("email") or "").lower().strip()
        if aid and email:
            mapping[aid] = email
    logger.info(f"Built Atlas mapping: {len(mapping)} agents")
    return mapping


# Collections that reference user_id in various fields
USER_ID_REFERENCES = [
    ("tickets", "assignee_id"),
    ("tickets", "created_by"),
    ("messages", "created_by"),
    ("messages", "author_id"),
    ("sessions", "user_id"),
    ("user_sessions", "user_id"),
    ("ticket_changelog", "changed_by"),
    ("api_keys", "created_by"),
    ("email_replies", "user_id"),
    ("notifications", "user_id"),
    ("canned_responses", "created_by"),
    ("feature_requests", "created_by"),
    ("leaves", "user_id"),
    ("kb_articles", "created_by"),
    ("kb_articles", "updated_by"),
]


def run_migration(dry_run: bool = True):
    """
    Main migration logic.

    Phase 1: Build atlas_user_id → real_email map from Atlas API
    Phase 2: Find all @imported.local users
    Phase 3: For each, resolve real email and check for ghost records
    Phase 4: Merge ghosts into imported records, update all references
    """
    logger.info(f"{'DRY RUN' if dry_run else 'APPLYING CHANGES'} — Fix @imported.local emails")

    # Phase 1: Build mapping
    atlas_map = _build_atlas_id_to_email_map()
    if not atlas_map:
        logger.warning("Could not build Atlas mapping. Will try name-based fallback.")

    # Phase 2: Find all @imported.local users
    imported_users = list(users_collection.find(
        {"email": {"$regex": r"@imported\.local$", "$options": "i"}},
        {"_id": 0}
    ))
    logger.info(f"Found {len(imported_users)} @imported.local users")

    if not imported_users:
        logger.info("No @imported.local records found. Migration complete (nothing to do).")
        return {"imported_found": 0, "fixed": 0, "ghosts_merged": 0}

    stats = {"imported_found": len(imported_users), "fixed": 0, "ghosts_merged": 0, "errors": [], "skipped": []}

    for imp_user in imported_users:
        imp_user_id = imp_user["user_id"]
        imp_email = imp_user["email"]
        imp_atlas_id = imp_user.get("atlas_user_id", "")
        imp_name = imp_user.get("name", "")

        # Phase 3: Resolve real email
        real_email = ""
        if imp_atlas_id and imp_atlas_id in atlas_map:
            real_email = atlas_map[imp_atlas_id]
        if not real_email:
            real_email = _fetch_atlas_agent_email_by_id(imp_atlas_id)

        if not real_email:
            msg = f"SKIP {imp_email} ({imp_name}): could not resolve real email (atlas_user_id={imp_atlas_id})"
            logger.warning(msg)
            stats["skipped"].append(msg)
            continue

        logger.info(f"RESOLVE: {imp_email} → {real_email} (user_id={imp_user_id}, atlas_id={imp_atlas_id})")

        # Phase 4: Check for ghost record
        ghost = users_collection.find_one({"email": real_email, "user_id": {"$ne": imp_user_id}}, {"_id": 0})

        if ghost:
            ghost_user_id = ghost["user_id"]
            logger.info(f"  GHOST found: {ghost_user_id} ({real_email}) — will merge into {imp_user_id}")

            if not dry_run:
                # Update all references from ghost user_id to imported user_id
                for col_name, field_name in USER_ID_REFERENCES:
                    col = db[col_name]
                    result = col.update_many(
                        {field_name: ghost_user_id},
                        {"$set": {field_name: imp_user_id}}
                    )
                    if result.modified_count > 0:
                        logger.info(f"    Updated {result.modified_count} docs in {col_name}.{field_name}")

                # Delete ghost record
                users_collection.delete_one({"user_id": ghost_user_id})
                logger.info(f"    Deleted ghost user record: {ghost_user_id}")
            else:
                # Dry run: count references
                for col_name, field_name in USER_ID_REFERENCES:
                    col = db[col_name]
                    count = col.count_documents({field_name: ghost_user_id})
                    if count > 0:
                        logger.info(f"    [DRY] Would update {count} docs in {col_name}.{field_name}")
                logger.info(f"    [DRY] Would delete ghost: {ghost_user_id}")

            stats["ghosts_merged"] += 1
        else:
            logger.info(f"  No ghost record for {real_email}")

        # Update imported record's email to real email
        if not dry_run:
            users_collection.update_one(
                {"user_id": imp_user_id},
                {"$set": {
                    "email": real_email,
                    "updated_at": datetime.now(timezone.utc),
                    "_email_migrated_from": imp_email,
                    "_email_migrated_at": datetime.now(timezone.utc),
                }}
            )
            logger.info(f"  Updated email: {imp_email} → {real_email}")
        else:
            logger.info(f"  [DRY] Would update email: {imp_email} → {real_email}")

        stats["fixed"] += 1

    logger.info(f"\n{'='*60}")
    logger.info(f"Migration {'DRY RUN' if dry_run else 'COMPLETE'}")
    logger.info(f"  Imported records found: {stats['imported_found']}")
    logger.info(f"  Fixed: {stats['fixed']}")
    logger.info(f"  Ghosts merged: {stats['ghosts_merged']}")
    logger.info(f"  Skipped: {len(stats['skipped'])}")
    if stats["skipped"]:
        for s in stats["skipped"]:
            logger.info(f"    - {s}")
    return stats


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    dry_run = "--apply" not in sys.argv
    if dry_run:
        print("\n  Run with --apply to execute changes.\n")
    run_migration(dry_run=dry_run)
