"""
Atlas sync routes — Backfill control, status, and real-time sync management.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from dependencies import get_current_user
from services.atlas_backfill import (
    start_backfill, stop_backfill, reset_backfill,
    get_status, test_batch, import_atlas_agents,
    run_enrichment_pass, get_enrichment_status, stop_enrichment,
)

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
