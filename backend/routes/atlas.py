"""
Atlas sync routes — Backfill control, status, and real-time sync management.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import logging
import os
import time
import requests

from dependencies import get_current_user
from database import db, tickets_collection, users_collection
from services.atlas_backfill import (
    start_backfill, stop_backfill, reset_backfill,
    get_status, test_batch, import_atlas_agents,
    run_enrichment_pass, get_enrichment_status, stop_enrichment,
)
from services.atlas_sync import (
    start_sync, stop_sync, get_sync_status, update_config as update_sync_config,
)
from services.attachment_migration import (
    start_migration, stop_migration, reset_migration,
    get_migration_status, _get_from_storage, _init_storage,
    reset_failed_attachments,
)
from services.zeus_cleanup import run_cleanup, get_cleanup_status

logger = logging.getLogger("atlas_routes")

router = APIRouter(prefix="/api/admin/atlas", tags=["atlas"])


class BackfillStartRequest(BaseModel):
    max_batches: Optional[int] = None


class TestBatchRequest(BaseModel):
    count: int = 100


@router.get("/backfill/status")
async def backfill_status(current_user: dict = Depends(get_current_user)):
    """Get current backfill progress."""
    return get_status()


@router.post("/backfill/start")
async def backfill_start(
    req: BackfillStartRequest = BackfillStartRequest(),
    current_user: dict = Depends(get_current_user),
):
    """Start or resume the Atlas historical backfill."""
    result = start_backfill(max_batches=req.max_batches)
    return result


@router.post("/backfill/stop")
async def backfill_stop(current_user: dict = Depends(get_current_user)):
    """Gracefully stop the running backfill. Can be resumed later."""
    result = stop_backfill()
    return result


@router.post("/backfill/reset")
async def backfill_reset(current_user: dict = Depends(get_current_user)):
    """Reset backfill state to start from scratch. Stop first if running."""
    result = reset_backfill()
    return result


@router.post("/backfill/test")
async def backfill_test(
    req: TestBatchRequest = TestBatchRequest(),
    current_user: dict = Depends(get_current_user),
):
    """Run a test batch import (synchronous, blocking). Returns sample results."""
    if req.count > 200:
        raise HTTPException(status_code=400, detail="Test batch max 200 conversations")
    result = test_batch(count=req.count)
    return result


@router.post("/agents/import")
async def atlas_import_agents(current_user: dict = Depends(get_current_user)):
    """Import all Atlas agents into Trinity users. Safe to re-run (upserts by email)."""
    result = import_atlas_agents()
    return result


@router.post("/backfill/enrich")
async def backfill_enrich(current_user: dict = Depends(get_current_user)):
    """Start the enrichment pass for previously-imported tickets (runs in background)."""
    result = run_enrichment_pass()
    return result


@router.get("/backfill/enrich/status")
async def enrichment_status(current_user: dict = Depends(get_current_user)):
    """Get current enrichment progress."""
    return get_enrichment_status()


@router.post("/backfill/enrich/stop")
async def enrichment_stop(current_user: dict = Depends(get_current_user)):
    """Stop the enrichment pass."""
    return stop_enrichment()


# ══════════════════════════════════════════════════════════════
# Shadow Sync (Real-Time)
# ══════════════════════════════════════════════════════════════

class SyncConfigUpdate(BaseModel):
    poll_interval: Optional[int] = None
    lookback_minutes: Optional[int] = None


@router.get("/sync/status")
async def sync_status(current_user: dict = Depends(get_current_user)):
    """Get current shadow sync status and stats."""
    return get_sync_status()


@router.post("/sync/start")
async def sync_start(current_user: dict = Depends(get_current_user)):
    """Start the Atlas shadow sync daemon."""
    return start_sync()


@router.post("/sync/stop")
async def sync_stop(current_user: dict = Depends(get_current_user)):
    """Stop the Atlas shadow sync daemon."""
    return stop_sync()


@router.patch("/sync/config")
async def sync_config(req: SyncConfigUpdate, current_user: dict = Depends(get_current_user)):
    """Update sync configuration (poll interval, lookback window)."""
    return update_sync_config(
        poll_interval=req.poll_interval,
        lookback_minutes=req.lookback_minutes,
    )


# ══════════════════════════════════════════════════════════════
# Attachment Migration
# ══════════════════════════════════════════════════════════════

@router.get("/attachments/status")
async def attachment_status(current_user: dict = Depends(get_current_user)):
    """Get attachment migration status."""
    return get_migration_status()


@router.post("/attachments/start")
async def attachment_start(current_user: dict = Depends(get_current_user)):
    """Start attachment migration from Atlas CDN to Emergent storage."""
    return start_migration()


@router.post("/attachments/stop")
async def attachment_stop(current_user: dict = Depends(get_current_user)):
    """Stop attachment migration (resumable)."""
    return stop_migration()


@router.post("/attachments/reset")
async def attachment_reset(current_user: dict = Depends(get_current_user)):
    """Reset attachment migration state."""
    return reset_migration()


@router.post("/attachments/reset-failed")
async def attachment_reset_failed(current_user: dict = Depends(get_current_user)):
    """Reset failed attachments so they can be retried when storage is restored."""
    return reset_failed_attachments()



# ══════════════════════════════════════════════════════════════
# Zeus (AI) Ticket Cleanup
# ══════════════════════════════════════════════════════════════

@router.get("/zeus/status")
async def zeus_status(current_user: dict = Depends(get_current_user)):
    """Get last Zeus cleanup run stats."""
    return get_cleanup_status()


@router.post("/zeus/run")
async def zeus_run_now(current_user: dict = Depends(get_current_user)):
    """Trigger an immediate Zeus cleanup run."""
    import asyncio
    stats = await asyncio.get_event_loop().run_in_executor(None, run_cleanup)
    return stats



# ══════════════════════════════════════════════════════════════
# Atlas API Health Test
# ══════════════════════════════════════════════════════════════

@router.get("/test")
async def atlas_api_test(current_user: dict = Depends(get_current_user)):
    """1-click Atlas API connectivity and health test."""
    api_key = os.environ.get("ATLAS_API_KEY", "")
    masked_key = f"...{api_key[-6:]}" if len(api_key) > 6 else "NOT SET"

    result = {
        "key_masked": masked_key,
        "key_set": bool(api_key),
        "connection": "unknown",
        "status_code": None,
        "response_time_ms": None,
        "total_conversations": None,
        "error": None,
    }

    if not api_key:
        result["connection"] = "error"
        result["error"] = "ATLAS_API_KEY not configured"
        return result

    try:
        start = time.time()
        resp = requests.get(
            "https://api.atlas.so/v1/conversations",
            params={"limit": 1},
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=10,
        )
        elapsed = round((time.time() - start) * 1000)
        result["status_code"] = resp.status_code
        result["response_time_ms"] = elapsed

        if resp.status_code == 200:
            data = resp.json()
            result["connection"] = "healthy"
            result["total_conversations"] = data.get("total", 0)
        elif resp.status_code == 401:
            result["connection"] = "auth_failed"
            result["error"] = "API key is invalid or expired"
        else:
            result["connection"] = "error"
            result["error"] = f"HTTP {resp.status_code}"
    except requests.Timeout:
        result["connection"] = "timeout"
        result["error"] = "Request timed out (>10s)"
    except Exception as e:
        result["connection"] = "error"
        result["error"] = str(e)[:200]

    return result


# ══════════════════════════════════════════════════════════════
# Data Parity Overview
# ══════════════════════════════════════════════════════════════

@router.get("/parity")
async def atlas_parity(current_user: dict = Depends(get_current_user)):
    """Data parity stats between Trinity and Atlas."""
    trinity_total = tickets_collection.count_documents({})
    atlas_linked = tickets_collection.count_documents(
        {"atlas_conversation_id": {"$exists": True, "$ne": None}}
    )
    imap_only = trinity_total - atlas_linked

    # Mismatched ticket IDs
    pipeline = [
        {"$match": {"atlas_number": {"$exists": True, "$ne": None}}},
        {"$project": {
            "_id": 0,
            "match": {"$eq": ["$ticket_id", {"$concat": ["TKT-", {"$toString": "$atlas_number"}]}]},
        }},
        {"$group": {"_id": "$match", "count": {"$sum": 1}}},
    ]
    mismatch_agg = {r["_id"]: r["count"] for r in tickets_collection.aggregate(pipeline)}
    matched = mismatch_agg.get(True, 0)
    mismatched = mismatch_agg.get(False, 0)

    # Full sync state
    shadow_state = db.atlas_backfill_state.find_one({"_type": "shadow"}, {"_id": 0})
    full_sync = (shadow_state or {}).get("full_sync", {})

    # Get actual total from Atlas API (not just the 45-day window)
    atlas_total = 0
    try:
        api_key = os.environ.get("ATLAS_API_KEY", "")
        if api_key:
            resp = requests.get(
                "https://api.atlas.so/v1/conversations",
                params={"limit": 1},
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                timeout=10,
            )
            if resp.status_code == 200:
                atlas_total = resp.json().get("total", 0)
    except Exception:
        atlas_total = full_sync.get("total", 0)  # fallback to window total

    # Users parity
    total_users = users_collection.count_documents({})
    imported_local = users_collection.count_documents(
        {"email": {"$regex": r"@imported\.local$", "$options": "i"}}
    )

    parity_pct = round((atlas_linked / atlas_total * 100), 1) if atlas_total > 0 else 0

    return {
        "trinity_total": trinity_total,
        "atlas_total": atlas_total,
        "atlas_linked": atlas_linked,
        "imap_only": imap_only,
        "missing_from_trinity": max(0, atlas_total - atlas_linked),
        "ticket_ids_matched": matched,
        "ticket_ids_mismatched": mismatched,
        "parity_pct": parity_pct,
        "full_sync": {
            "cursor": full_sync.get("cursor", 0),
            "total": full_sync.get("total", 0),
            "completed_passes": full_sync.get("completed_passes", 0),
            "last_completed_at": full_sync.get("last_completed_at"),
        },
        "users": {
            "total": total_users,
            "imported_local_emails": imported_local,
        },
    }



# ==================== Sync Health Audit ====================

_STATUS_MAP = {"OPEN": "todo", "CLOSED": "closed", "SNOOZED": "waiting", "PENDING": "waiting", "IN_PROGRESS": "todo"}
_PRIORITY_MAP = {"NO_PRIORITY": "medium", "LOW": "low", "NORMAL": "medium", "MEDIUM": "medium", "HIGH": "high", "URGENT": "urgent"}


@router.get("/sync-health")
async def sync_health_audit(current_user: dict = Depends(get_current_user)):
    """
    Run a live sync health audit: sample conversations from Atlas,
    compare field-by-field with Trinity, and return a detailed report.
    Auto-runs on page load — no manual trigger needed.
    """
    from datetime import timedelta
    from services.atlas_sync import _get_state, FULL_SYNC_WINDOW_DAYS, FULL_SYNC_BATCH_SIZE, DEFAULT_LOOKBACK_MINUTES

    atlas_key = os.environ.get("ATLAS_API_KEY", "")
    if not atlas_key:
        raise HTTPException(status_code=500, detail="ATLAS_API_KEY not configured")

    headers = {"Accept": "application/json", "Authorization": f"Bearer {atlas_key}"}
    now = datetime.now(timezone.utc)

    # Sample from 4 time windows (50 each = 200 total)
    windows = [
        {"label": "Last 6 hours", "days": 0.25},
        {"label": "1-3 days", "days": 3},
        {"label": "3-7 days", "days": 7},
        {"label": "7-14 days", "days": 14},
    ]

    window_results = []
    total_checked = total_clean = total_diffs = total_missing = 0
    all_diffs = []

    for w in windows:
        start = (now - timedelta(days=w["days"])).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            resp = requests.get(
                "https://api.atlas.so/v1/conversations",
                params={"startDate": start, "limit": 50},
                headers=headers, timeout=20,
            )
            if resp.status_code != 200:
                window_results.append({"label": w["label"], "error": f"Atlas API {resp.status_code}"})
                continue
            convs = resp.json().get("data", [])
        except Exception as e:
            window_results.append({"label": w["label"], "error": str(e)})
            continue

        clean = diffs = missing = 0
        for conv in convs:
            atlas_id = str(conv.get("id", ""))
            atlas_status = conv.get("status", "")
            atlas_priority = conv.get("priority", "")
            atlas_zeus = conv.get("assignedToZeus", False)
            atlas_agent = conv.get("assignedAgent") or {}
            atlas_num = conv.get("number")

            trinity = tickets_collection.find_one(
                {"atlas_conversation_id": atlas_id},
                {"_id": 0, "ticket_id": 1, "status": 1, "atlas_status": 1, "priority": 1,
                 "atlas_assigned_to_zeus": 1, "atlas_assigned_agent_email": 1, "last_synced_at": 1}
            )
            if not trinity:
                missing += 1
                continue

            exp_status = _STATUS_MAP.get(atlas_status.upper(), "todo")
            exp_priority = _PRIORITY_MAP.get((atlas_priority or "NO_PRIORITY").upper(), "medium")
            issues = []
            if trinity.get("status") != exp_status:
                issues.append({"field": "status", "trinity": trinity.get("status"), "atlas": atlas_status})
            if trinity.get("atlas_status") != atlas_status:
                issues.append({"field": "atlas_status", "trinity": trinity.get("atlas_status"), "atlas": atlas_status})
            if trinity.get("priority") != exp_priority:
                issues.append({"field": "priority", "trinity": trinity.get("priority"), "atlas": atlas_priority})
            if trinity.get("atlas_assigned_to_zeus") != atlas_zeus:
                issues.append({"field": "zeus", "trinity": str(trinity.get("atlas_assigned_to_zeus")), "atlas": str(atlas_zeus)})
            if trinity.get("atlas_assigned_agent_email") != atlas_agent.get("email"):
                issues.append({"field": "agent", "trinity": trinity.get("atlas_assigned_agent_email") or "none", "atlas": atlas_agent.get("email") or "none"})

            if issues:
                diffs += 1
                if len(all_diffs) < 15:
                    ls = trinity.get("last_synced_at")
                    sync_age = None
                    if ls:
                        if ls.tzinfo is None:
                            ls = ls.replace(tzinfo=timezone.utc)
                        sync_age = round((now - ls).total_seconds() / 60)
                    all_diffs.append({
                        "ticket": trinity.get("ticket_id"),
                        "atlas_num": atlas_num,
                        "issues": issues,
                        "synced_minutes_ago": sync_age,
                    })
            else:
                clean += 1

        pct = round(clean / len(convs) * 100) if convs else 0
        window_results.append({
            "label": w["label"],
            "checked": len(convs),
            "clean": clean,
            "diffs": diffs,
            "missing": missing,
            "pct": pct,
        })
        total_checked += len(convs)
        total_clean += clean
        total_diffs += diffs
        total_missing += missing

    # Linking stats
    total_tickets = tickets_collection.count_documents({})
    linked = tickets_collection.count_documents({"atlas_conversation_id": {"$ne": None}})
    non_closed_unlinked = tickets_collection.count_documents({
        "$or": [{"atlas_conversation_id": None}, {"atlas_conversation_id": {"$exists": False}}],
        "status": {"$ne": "closed"},
    })

    # Open ticket breakdown
    non_closed = tickets_collection.count_documents({"status": {"$ne": "closed"}})
    zeus = tickets_collection.count_documents({"status": {"$ne": "closed"}, "atlas_assigned_to_zeus": True})
    human_assigned = tickets_collection.count_documents({
        "status": {"$ne": "closed"}, "atlas_assigned_to_zeus": {"$ne": True}, "assignee_id": {"$ne": None},
    })
    human_unassigned = tickets_collection.count_documents({
        "status": {"$ne": "closed"}, "atlas_assigned_to_zeus": {"$ne": True}, "assignee_id": None,
    })

    # Sync engine state
    state = _get_state()
    fs = state.get("full_sync", {})
    cursor = fs.get("cursor", 0)
    fs_total = fs.get("total", 0)
    remaining = fs_total - cursor
    eta_minutes = round(remaining / FULL_SYNC_BATCH_SIZE) if FULL_SYNC_BATCH_SIZE else 0

    overall_pct = round(total_clean / total_checked * 100, 1) if total_checked else 0
    grade = "A" if overall_pct >= 98 else "B" if overall_pct >= 90 else "C" if overall_pct >= 70 else "F"

    return {
        "grade": grade,
        "overall_pct": overall_pct,
        "total_checked": total_checked,
        "total_clean": total_clean,
        "total_diffs": total_diffs,
        "total_missing": total_missing,
        "windows": window_results,
        "diffs": all_diffs,
        "linking": {
            "total_tickets": total_tickets,
            "linked": linked,
            "linked_pct": round(linked / total_tickets * 100, 1) if total_tickets else 0,
            "non_closed_unlinked": non_closed_unlinked,
        },
        "open_tickets": {
            "total": non_closed,
            "zeus": zeus,
            "human_assigned": human_assigned,
            "human_unassigned": human_unassigned,
        },
        "engine": {
            "status": state.get("status", "unknown"),
            "is_running": state.get("status") == "running",
            "cycles": state.get("cycles_completed", 0),
            "phase2_cursor": cursor,
            "phase2_total": fs_total,
            "phase2_pct": round(cursor / fs_total * 100) if fs_total else 0,
            "phase2_passes": fs.get("completed_passes", 0),
            "phase2_eta_minutes": eta_minutes,
            "window_days": FULL_SYNC_WINDOW_DAYS,
            "batch_size": FULL_SYNC_BATCH_SIZE,
            "lookback_minutes": DEFAULT_LOOKBACK_MINUTES,
        },
        "timestamp": now.isoformat(),
    }
