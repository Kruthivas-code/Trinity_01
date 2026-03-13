"""
Atlas Webhook HTTP Handler — thin layer that delegates to the unified sync engine.
All sync logic lives in services/atlas_sync.py (Layer 1: Webhooks).
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.atlas_sync import handle_webhook_event

logger = logging.getLogger("atlas_webhooks")

router = APIRouter(prefix="/api", tags=["webhooks"])


@router.post("/webhooks/atlas")
async def atlas_webhook(request: Request):
    """
    Receive webhook events from Atlas.
    Returns 200 immediately to avoid Atlas retries, processes in-band.
    """
    try:
        body = await request.body()
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.warning(f"[WEBHOOK] Non-JSON body received: {body[:500]}")
            return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)

        logger.info(f"[WEBHOOK] Received: {json.dumps(payload, default=str)[:2000]}")

        event_type = (
            payload.get("event")
            or payload.get("eventType")
            or payload.get("event_type")
            or payload.get("type")
            or ""
        ).lower().strip()

        handle_webhook_event(event_type, payload)

        return JSONResponse({"status": "ok"})

    except Exception as e:
        logger.error(f"[WEBHOOK] Error processing webhook: {e}", exc_info=True)
        return JSONResponse({"status": "ok"})


@router.get("/webhooks/atlas/health")
async def atlas_webhook_health():
    """Health check for webhook endpoint — useful for Atlas verification."""
    return {"status": "ok", "service": "trinity-atlas-webhook", "timestamp": datetime.now(timezone.utc).isoformat()}
