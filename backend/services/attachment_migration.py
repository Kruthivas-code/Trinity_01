"""
Attachment Migration Engine
============================
Resumable background job that downloads attachments from Atlas CDN
(and optionally Discord CDN) and re-uploads them to Emergent Object Storage.

Updates the `attachments[].url` field in messages to point to a proxy
endpoint, preserving the original URL in `attachments[].original_url`.

State is persisted in MongoDB for resumability across restarts.
"""

import os
import re
import uuid
import logging
import time
import threading
import mimetypes
import requests
from datetime import datetime, timezone
from typing import Optional

from database import db, messages_collection

logger = logging.getLogger("attachment_migration")

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
APP_PREFIX = "trinity/attachments"

# State collection
_state_col = db.atlas_backfill_state

# Thread control
_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

# Module-level storage key (init once)
_storage_key: Optional[str] = None

# CDN domains to migrate (these will break after Atlas cutover)
MIGRATE_DOMAINS = ["files.atlas.so", "cdn.discordapp.com", "media.discordapp.net"]

# Batch size per cycle
BATCH_SIZE = 50
# Delay between downloads (seconds) to avoid rate limiting
DOWNLOAD_DELAY = 0.3
# Max file size to download (100 MB)
MAX_FILE_SIZE = 100 * 1024 * 1024
# Max consecutive batch failures before circuit-breaking
MAX_CONSECUTIVE_FAILURES = 3
# Backoff sleep (seconds) when circuit breaks
CIRCUIT_BREAK_SLEEP = 300  # 5 minutes
# Max retries per individual attachment before marking permanently failed
MAX_ATTACHMENT_RETRIES = 3


def _init_storage() -> str:
    """Initialize storage, return storage key. Call once."""
    global _storage_key
    if _storage_key:
        return _storage_key
    if not EMERGENT_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")
    resp = requests.post(
        f"{STORAGE_URL}/init",
        json={"emergent_key": EMERGENT_KEY},
        timeout=30,
    )
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    logger.info("[ATTACH] Storage initialized")
    return _storage_key


def _upload_to_storage(path: str, data: bytes, content_type: str) -> dict:
    """Upload file to Emergent Object Storage."""
    key = _init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def _get_from_storage(path: str) -> tuple:
    """Download file from Emergent Object Storage. Returns (bytes, content_type)."""
    key = _init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def _should_migrate(url: str) -> bool:
    """Check if this URL belongs to a CDN that needs migration."""
    if not url or not url.startswith("https://"):
        return False
    for domain in MIGRATE_DOMAINS:
        if domain in url:
            return True
    return False


def _guess_content_type(url: str, filename: str = "") -> str:
    """Guess content type from URL or filename."""
    for src in [filename, url]:
        if src:
            ct, _ = mimetypes.guess_type(src)
            if ct:
                return ct
    return "application/octet-stream"


def _get_state() -> dict:
    state = _state_col.find_one({"_type": "attachment_migration"}, {"_id": 0})
    if not state:
        return {
            "_type": "attachment_migration",
            "status": "idle",
            "total_attachments": 0,
            "migrated": 0,
            "skipped": 0,
            "failed": 0,
            "bytes_transferred": 0,
            "started_at": None,
            "last_run_at": None,
            "errors": [],
        }
    return state


def _save_state(state: dict):
    state["_type"] = "attachment_migration"
    _state_col.update_one(
        {"_type": "attachment_migration"}, {"$set": state}, upsert=True
    )


def get_migration_status() -> dict:
    state = _get_state()
    state.pop("_type", None)
    state["is_running"] = _worker_thread is not None and _worker_thread.is_alive()
    if len(state.get("errors", [])) > 20:
        state["errors"] = state["errors"][-20:]
    return state


def _storage_health_probe() -> bool:
    """Quick probe to check if storage uploads are working."""
    try:
        key = _init_storage()
        resp = requests.put(
            f"{STORAGE_URL}/objects/trinity/attachments/_health_probe.txt",
            headers={"X-Storage-Key": key, "Content-Type": "text/plain"},
            data=b"probe",
            timeout=15,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _migrate_batch(state: dict) -> dict:
    """Process a batch of messages with unmigrated attachments. Returns stats."""
    stats = {"migrated": 0, "skipped": 0, "failed": 0, "bytes": 0}

    # Find messages with attachments still pointing to migrate-domains
    # Exclude attachments already marked as permanently failed
    query = {
        "attachments": {
            "$elemMatch": {
                "url": {"$regex": "|".join(re.escape(d) for d in MIGRATE_DOMAINS)},
                "storage_path": {"$exists": False},
            }
        }
    }

    messages = list(
        messages_collection.find(query, {"_id": 0})
        .sort("message_id", 1)
        .limit(BATCH_SIZE)
    )

    if not messages:
        return stats

    for msg in messages:
        if _stop_event.is_set():
            break

        message_id = msg["message_id"]
        attachments = msg.get("attachments", [])
        updated = False

        for i, att in enumerate(attachments):
            original_url = att.get("url", "")
            if not _should_migrate(original_url):
                # Mark malformed URLs so they don't get re-queried
                if original_url and any(d in original_url for d in MIGRATE_DOMAINS) and not original_url.startswith("https://"):
                    attachments[i]["migration_error"] = "malformed_url"
                    attachments[i]["storage_path"] = "FAILED"
                    updated = True
                    stats["skipped"] += 1
                continue

            # Already migrated (has storage_path)
            if att.get("storage_path"):
                stats["skipped"] += 1
                continue

            # Check if permanently failed
            retry_count = att.get("migration_retries", 0)
            if retry_count >= MAX_ATTACHMENT_RETRIES:
                stats["skipped"] += 1
                continue

            try:
                # Download from CDN
                dl = requests.get(original_url, timeout=60, stream=True)
                if dl.status_code != 200:
                    attachments[i]["migration_retries"] = retry_count + 1
                    attachments[i]["last_migration_error"] = f"download_{dl.status_code}"
                    if retry_count + 1 >= MAX_ATTACHMENT_RETRIES:
                        attachments[i]["storage_path"] = "FAILED"
                        attachments[i]["migration_error"] = f"download_failed_{dl.status_code}"
                    updated = True
                    stats["failed"] += 1
                    continue

                content_length = int(dl.headers.get("Content-Length", 0))
                if content_length > MAX_FILE_SIZE:
                    attachments[i]["storage_path"] = "FAILED"
                    attachments[i]["migration_error"] = "too_large"
                    updated = True
                    stats["skipped"] += 1
                    continue

                data = dl.content
                if len(data) > MAX_FILE_SIZE:
                    attachments[i]["storage_path"] = "FAILED"
                    attachments[i]["migration_error"] = "too_large"
                    updated = True
                    stats["skipped"] += 1
                    continue

                # Determine storage path
                filename = att.get("name", "")
                ext = ""
                if filename and "." in filename:
                    ext = filename.rsplit(".", 1)[1].lower()
                elif "." in original_url.split("?")[0].split("/")[-1]:
                    ext = original_url.split("?")[0].split("/")[-1].rsplit(".", 1)[1].lower()

                file_uuid = uuid.uuid4().hex[:16]
                storage_path = f"{APP_PREFIX}/{file_uuid}"
                if ext:
                    storage_path += f".{ext}"

                content_type = dl.headers.get("Content-Type") or _guess_content_type(original_url, filename)

                # Upload to Emergent storage
                result = _upload_to_storage(storage_path, data, content_type)

                # Update attachment in DB
                attachments[i]["original_url"] = original_url
                attachments[i]["storage_path"] = result["path"]
                attachments[i]["storage_size"] = result.get("size", len(data))
                attachments[i]["content_type"] = content_type
                attachments[i]["migrated_at"] = datetime.now(timezone.utc)
                # Update URL to proxy endpoint
                attachments[i]["url"] = f"/api/files/{result['path']}"
                updated = True

                stats["migrated"] += 1
                stats["bytes"] += len(data)

                time.sleep(DOWNLOAD_DELAY)

            except requests.Timeout:
                attachments[i]["migration_retries"] = retry_count + 1
                attachments[i]["last_migration_error"] = "timeout"
                if retry_count + 1 >= MAX_ATTACHMENT_RETRIES:
                    attachments[i]["storage_path"] = "FAILED"
                    attachments[i]["migration_error"] = "timeout"
                updated = True
                stats["failed"] += 1
                logger.warning(f"[ATTACH] Timeout downloading {original_url[:80]}")
            except Exception as e:
                attachments[i]["migration_retries"] = retry_count + 1
                attachments[i]["last_migration_error"] = str(e)[:200]
                if retry_count + 1 >= MAX_ATTACHMENT_RETRIES:
                    attachments[i]["storage_path"] = "FAILED"
                    attachments[i]["migration_error"] = str(e)[:200]
                updated = True
                stats["failed"] += 1
                logger.warning(f"[ATTACH] Error migrating {original_url[:80]}: {e}")

        # Update message attachments in DB
        if updated:
            messages_collection.update_one(
                {"message_id": message_id},
                {"$set": {"attachments": attachments}},
            )

    return stats


def _migration_loop():
    """Main migration loop — processes batches until done or stopped."""
    logger.info("[ATTACH] Migration started")

    try:
        _init_storage()
    except Exception as e:
        logger.error(f"[ATTACH] Failed to init storage: {e}")
        state = _get_state()
        state["status"] = "error"
        state["errors"] = state.get("errors", []) + [
            {"time": datetime.now(timezone.utc).isoformat(), "error": str(e)}
        ]
        _save_state(state)
        return

    state = _get_state()
    state["status"] = "running"
    state["started_at"] = state.get("started_at") or datetime.now(timezone.utc)
    _save_state(state)

    # Count total attachments to migrate
    pipeline = [
        {"$match": {"attachments": {"$exists": True, "$ne": None, "$not": {"$size": 0}}}},
        {"$unwind": "$attachments"},
        {"$match": {
            "attachments.url": {"$regex": "|".join(re.escape(d) for d in MIGRATE_DOMAINS)},
            "attachments.storage_path": {"$exists": False},
        }},
        {"$count": "total"},
    ]
    result = list(messages_collection.aggregate(pipeline))
    total = result[0]["total"] if result else 0
    state["total_attachments"] = total
    _save_state(state)
    logger.info(f"[ATTACH] {total} attachments to migrate")

    consecutive_full_failures = 0

    while not _stop_event.is_set():
        try:
            # Circuit breaker: if storage is consistently failing, back off
            if consecutive_full_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.warning(
                    f"[ATTACH] Circuit breaker: {consecutive_full_failures} consecutive "
                    f"full-batch failures. Storage probe..."
                )
                if _storage_health_probe():
                    logger.info("[ATTACH] Storage probe passed, resuming migration")
                    consecutive_full_failures = 0
                else:
                    logger.warning(
                        f"[ATTACH] Storage still down, sleeping {CIRCUIT_BREAK_SLEEP}s..."
                    )
                    state = _get_state()
                    state["status"] = "waiting_storage"
                    state["last_run_at"] = datetime.now(timezone.utc)
                    _save_state(state)
                    _stop_event.wait(CIRCUIT_BREAK_SLEEP)
                    continue

            batch_stats = _migrate_batch(state)

            state = _get_state()
            state["migrated"] += batch_stats["migrated"]
            state["skipped"] += batch_stats["skipped"]
            state["failed"] += batch_stats["failed"]
            state["bytes_transferred"] += batch_stats["bytes"]
            state["last_run_at"] = datetime.now(timezone.utc)
            state["status"] = "running"
            _save_state(state)

            total_processed = batch_stats["migrated"] + batch_stats["skipped"] + batch_stats["failed"]
            if total_processed > 0:
                # Track consecutive failures for circuit breaker
                if batch_stats["migrated"] == 0 and batch_stats["failed"] > 0 and batch_stats["skipped"] == 0:
                    consecutive_full_failures += 1
                else:
                    consecutive_full_failures = 0

                mb = batch_stats["bytes"] / (1024 * 1024)
                logger.info(
                    f"[ATTACH] Batch: migrated={batch_stats['migrated']} "
                    f"skipped={batch_stats['skipped']} failed={batch_stats['failed']} "
                    f"({mb:.1f} MB) | Total: {state['migrated']}/{state['total_attachments']}"
                )
            else:
                # No more attachments to process
                logger.info(f"[ATTACH] Migration complete. Total migrated: {state['migrated']}")
                state["status"] = "completed"
                _save_state(state)
                break

            # Brief pause between batches
            time.sleep(1)

        except Exception as e:
            logger.error(f"[ATTACH] Error in migration loop: {e}")
            state = _get_state()
            errors = state.get("errors", [])
            errors.append({"time": datetime.now(timezone.utc).isoformat(), "error": str(e)})
            state["errors"] = errors[-50:]
            _save_state(state)
            time.sleep(5)

    if _stop_event.is_set():
        state = _get_state()
        state["status"] = "paused"
        _save_state(state)
        logger.info("[ATTACH] Migration paused")


def start_migration() -> dict:
    """Start the attachment migration."""
    global _worker_thread
    if not EMERGENT_KEY:
        return {"error": "EMERGENT_LLM_KEY not configured"}
    if _worker_thread and _worker_thread.is_alive():
        return {"message": "Migration is already running", **get_migration_status()}
    _stop_event.clear()
    _worker_thread = threading.Thread(
        target=_migration_loop, daemon=True, name="attachment_migration"
    )
    _worker_thread.start()
    return {"message": "Attachment migration started", "status": "running"}


def stop_migration() -> dict:
    """Stop the attachment migration (resumable)."""
    global _worker_thread
    if not _worker_thread or not _worker_thread.is_alive():
        return {"message": "Migration is not running", **get_migration_status()}
    _stop_event.set()
    _worker_thread.join(timeout=15)
    _worker_thread = None
    return {"message": "Migration stopped (resumable)", **get_migration_status()}


def reset_migration() -> dict:
    """Reset migration state to start fresh. Does NOT delete already-uploaded files."""
    if _worker_thread and _worker_thread.is_alive():
        return {"error": "Stop migration first"}
    _state_col.delete_one({"_type": "attachment_migration"})
    return {"message": "Migration state reset"}


def reset_failed_attachments() -> dict:
    """Reset retry counters on failed attachments so they can be retried.
    Call this after storage service is restored."""
    result = messages_collection.update_many(
        {"attachments.storage_path": "FAILED"},
        {"$unset": {
            "attachments.$[elem].storage_path": "",
            "attachments.$[elem].migration_error": "",
            "attachments.$[elem].migration_retries": "",
            "attachments.$[elem].last_migration_error": "",
        }},
        array_filters=[{"elem.storage_path": "FAILED"}],
    )
    return {
        "message": f"Reset {result.modified_count} messages with failed attachments",
        "modified": result.modified_count,
    }


def auto_resume_migration():
    """Resume migration on startup if it was running or paused."""
    state = _get_state()
    status = state.get("status", "idle")
    if status in ("running", "paused"):
        migrated = state.get("migrated", 0)
        total = state.get("total_attachments", 0)
        logger.info(
            f"[ATTACH] Auto-resuming migration (was {status}, {migrated}/{total} done)"
        )
        start_migration()
    else:
        logger.info(f"[ATTACH] Migration status={status}, not resuming")
