"""
Atlas sync routes — Backfill control, status, and real-time sync management.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import logging

from dependencies import get_current_user
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
