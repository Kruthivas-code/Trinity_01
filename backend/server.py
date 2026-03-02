"""
Trinity API - Enterprise ticket management platform
Main application entry point. All routes are in backend/routes/.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import asyncio
import logging
import secrets
import uuid
import os

from database import (
    db, client, MONGO_URL,
    tickets_collection, users_collection, teams_collection,
    sessions_collection, customers_collection, messages_collection,
    ticket_changelog_collection, email_replies_collection,
    api_keys_collection, feature_requests_collection,
    csat_responses_collection, csat_tokens_collection,
    canned_responses_collection, routing_rules_collection,
    sla_escalation_rules_collection, custom_inboxes_collection,
    shifts_collection,
    AUTO_CLOSE_HOURS,
)
from realtime import sio, socket_app, initialize_realtime, start_pubsub, stop_pubsub
from adapters import set_database, get_lock_adapter
from search import get_search_engine
from rate_limiter import limiter
from utils import serialize_doc, generate_ticket_id, sanitize_html

# ==================== Logging ====================
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(record, 'request_id', '-')
        return True

for handler in logging.root.handlers:
    handler.addFilter(RequestIdFilter())

# ==================== Environment Validation ====================
def validate_environment():
    required_vars = ["MONGO_URL"]
    recommended_vars = ["ALLOWED_ORIGINS"]
    missing_required = [v for v in required_vars if not os.environ.get(v)]
    missing_recommended = [v for v in recommended_vars if not os.environ.get(v)]
    if missing_required:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_required)}")
    if missing_recommended:
        logger.warning(f"Missing recommended environment variables: {', '.join(missing_recommended)}")

validate_environment()

# ==================== App Creation ====================
tags_metadata = [
    {"name": "auth", "description": "Authentication, sessions, and API key management"},
    {"name": "users", "description": "User profiles, preferences, and role management"},
    {"name": "tickets", "description": "Core ticket CRUD, assignment, escalation, notes, and activity"},
    {"name": "ticket_ops", "description": "Bulk operations, merge, unmerge, link, split tickets"},
    {"name": "teams", "description": "Team CRUD and member management"},
    {"name": "shifts", "description": "Shift scheduling, assignment, and on-shift queries"},
    {"name": "filters", "description": "Advanced ticket filtering engine and custom inboxes"},
    {"name": "admin", "description": "Custom fields, settings, routing rules, SLA policies, and escalation rules"},
    {"name": "sla", "description": "SLA policy listing and per-ticket SLA status"},
    {"name": "analytics", "description": "Dashboard summaries, overview metrics, and agent performance"},
    {"name": "email", "description": "File uploads, imports, and email replies"},
    {"name": "customers", "description": "Customer CRUD, B2B prospects, email linking, and merge"},
    {"name": "csat", "description": "CSAT surveys, ratings, feedback, and analytics"},
    {"name": "canned_responses", "description": "Reusable response templates for ticket replies"},
    {"name": "feature_requests", "description": "Feature request tracking, voting, and ticket linking"},
    {"name": "leaves", "description": "Leave request management and approvals"},
    {"name": "exports", "description": "Data export for tickets, users, teams, and analytics"},
    {"name": "webhooks", "description": "Webhook subscription management and delivery logs"},
    {"name": "search", "description": "Search, suggestions, presence tracking, and notifications"},
    {"name": "health", "description": "System health checks"},
]

app = FastAPI(
    title="Trinity API",
    description="Enterprise ticket management platform with real-time collaboration, SLA tracking, team management, and analytics.",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=tags_metadata,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Mount Socket.IO
app.mount("/api/socket.io", socket_app)

# ==================== Include All Route Modules ====================
from routes.filters import router as filters_router
from routes.webhooks import router as webhooks_router
from routes.customers import router as customers_router
from routes.csat import router as csat_router
from routes.canned_responses import router as canned_responses_router
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.teams import router as teams_router
from routes.shifts import router as shifts_router
from routes.tickets import router as tickets_router
from routes.ticket_ops import router as ticket_ops_router
from routes.email import router as email_router
from routes.admin import router as admin_router
from routes.sla import router as sla_router
from routes.analytics import router as analytics_router
from routes.search_presence import router as search_presence_router
from routes.leaves import router as leaves_router
from routes.feature_requests import router as feature_requests_router
from routes.exports import router as exports_router
from routes.knowledge_base import router as knowledge_base_router
from routes.summaries import router as summaries_router
from routes.portal import router as portal_router, seed_default_categories
from routes.kb import router as kb_router

app.include_router(filters_router)
app.include_router(webhooks_router)
app.include_router(customers_router)
app.include_router(csat_router)
app.include_router(canned_responses_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(teams_router)
app.include_router(shifts_router)
app.include_router(tickets_router)
app.include_router(ticket_ops_router)
app.include_router(email_router)
app.include_router(admin_router)
app.include_router(sla_router)
app.include_router(analytics_router)
app.include_router(search_presence_router)
app.include_router(leaves_router)
app.include_router(feature_requests_router)
app.include_router(exports_router)
app.include_router(knowledge_base_router)
app.include_router(summaries_router)
app.include_router(portal_router)
app.include_router(kb_router)

# ==================== Middleware ====================
MAX_REQUEST_BODY_SIZE = 50 * 1024 * 1024  # 50MB

@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BODY_SIZE:
        return JSONResponse(status_code=413, content={"detail": "Request body too large. Maximum size is 50MB."})
    return await call_next(request)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.error(f"Unhandled exception: {str(exc)}", extra={"request_id": request_id}, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred", "request_id": request_id}
    )

# CORS
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",")
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == [""]:
    ALLOWED_ORIGINS = [
        "https://columns-rebuild.preview.emergentagent.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-API-Key", "X-Session-ID"],
)

# ==================== Health Check ====================
@app.get("/api/health", tags=["health"])
async def health():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "checks": {}
    }
    try:
        client.admin.command('ping')
        health_status["checks"]["database"] = {"status": "healthy", "type": "mongodb"}
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {"status": "unhealthy", "type": "mongodb", "error": "Connection failed"}
        logger.error(f"Health check database error: {e}")
    try:
        collections = db.list_collection_names()
        required = ["users", "tickets", "user_sessions"]
        missing = [c for c in required if c not in collections]
        health_status["checks"]["collections"] = {"status": "healthy" if not missing else "warning", "missing": missing or None}
    except Exception as e:
        health_status["checks"]["collections"] = {"status": "error", "error": "Check failed"}
        logger.error(f"Health check collections error: {e}")
    if health_status["status"] == "unhealthy":
        return JSONResponse(status_code=503, content=health_status)
    return health_status

# ==================== Background Tasks ====================
auto_close_task = None
_instance_id = os.environ.get('INSTANCE_ID', os.environ.get('HOSTNAME', f'instance_{secrets.token_hex(4)}'))


async def auto_close_resolved_tickets():
    lock_adapter = get_lock_adapter()
    lock_name = "auto_close_resolved_tickets"
    lock_ttl = 3600
    while True:
        acquired = False
        try:
            acquired = await lock_adapter.acquire(lock_name, _instance_id, lock_ttl)
            if not acquired:
                logger.info("[AUTO-CLOSE] Another instance holds the lock, skipping")
                await asyncio.sleep(3600)
                continue
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=AUTO_CLOSE_HOURS)
            query = {"status": "resolved", "resolved_at": {"$lte": cutoff_time}}
            tickets_to_close = list(tickets_collection.find(query, {"ticket_id": 1, "_id": 0}))
            if tickets_to_close:
                ticket_ids = [t["ticket_id"] for t in tickets_to_close]
                now = datetime.now(timezone.utc)
                tickets_collection.update_many(query, {"$set": {"status": "closed", "closed_at": now, "auto_closed": True, "updated_at": now}})
                system_messages = [
                    {"message_id": f"msg_{uuid4().hex[:12]}", "ticket_id": tid, "type": "system",
                     "text": f"Auto-closed after {AUTO_CLOSE_HOURS} hours in resolved status",
                     "created_by": "system", "created_at": now}
                    for tid in ticket_ids
                ]
                if system_messages:
                    messages_collection.insert_many(system_messages)
                logger.info(f"[AUTO-CLOSE] Auto-closed {len(ticket_ids)} resolved tickets")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"[AUTO-CLOSE] Error: {e}")
        finally:
            if acquired:
                await lock_adapter.release(lock_name, _instance_id)
        await asyncio.sleep(3600)


# ==================== Startup / Shutdown ====================
@app.on_event("startup")
async def startup_event():
    global auto_close_task
    from motor.motor_asyncio import AsyncIOMotorClient
    motor_client = AsyncIOMotorClient(MONGO_URL)
    motor_db = motor_client[os.environ.get('DB_NAME', 'tickflow')]
    set_database(motor_db)
    initialize_realtime(motor_db)
    await start_pubsub()
    await create_mongodb_indexes()
    auto_close_task = asyncio.create_task(auto_close_resolved_tickets())
    seed_default_categories()
    # Start email IMAP poller
    from services.email_poller import start_poller as start_email_poller
    start_email_poller()
    logger.info(f"[STARTUP] Instance {_instance_id} started")


async def create_mongodb_indexes():
    try:
        tickets_collection.create_index([("status", ASCENDING)], background=True)
        tickets_collection.create_index([("status", ASCENDING), ("resolved_at", ASCENDING)], background=True)
        tickets_collection.create_index([("assignee_id", ASCENDING), ("status", ASCENDING)], background=True)
        tickets_collection.create_index([("customer_email", ASCENDING)], background=True)
        tickets_collection.create_index([("customer_email", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("updated_at", DESCENDING)], background=True)
        tickets_collection.create_index([("priority", ASCENDING)], background=True)
        tickets_collection.create_index([("team_id", ASCENDING)], background=True)
        tickets_collection.create_index([("is_starred", ASCENDING)], background=True)
        tickets_collection.create_index([("mentioned_users", ASCENDING)], background=True)
        tickets_collection.create_index("ticket_id", unique=True, background=True)
        tickets_collection.create_index("uuid", unique=True, sparse=True, background=True)
        tickets_collection.create_index("atlas_conversation_id", unique=True, sparse=True, background=True)
        tickets_collection.create_index([("status", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("escalation_level", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("assignee_id", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index("email_rfc_message_id", unique=True, sparse=True, background=True)
        sessions_collection.create_index("session_token", unique=True, background=True)
        sessions_collection.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, background=True)
        sessions_collection.create_index([("user_id", ASCENDING)], background=True)
        users_collection.create_index("user_id", unique=True, background=True)
        users_collection.create_index("email", unique=True, sparse=True, background=True)
        customers_collection.create_index("atlas_user_id", unique=True, sparse=True, background=True)
        messages_collection.create_index([("ticket_id", ASCENDING), ("created_at", ASCENDING)], background=True)
        messages_collection.create_index([("ticket_id", ASCENDING)], background=True)
        messages_collection.create_index("atlas_message_id", unique=True, sparse=True, background=True)
        ticket_changelog_collection.create_index([("ticket_id", ASCENDING), ("changed_at", DESCENDING)], background=True)
        ticket_changelog_collection.create_index([("ticket_uuid", ASCENDING)], background=True)
        teams_collection.create_index("team_id", unique=True, background=True)
        api_keys_collection.create_index("key_hash", unique=True, background=True)
        api_keys_collection.create_index("key_sha256", unique=True, sparse=True, background=True)
        api_keys_collection.create_index([("user_id", ASCENDING)], background=True)
        feature_requests_collection.create_index("feature_id", unique=True, background=True)
        feature_requests_collection.create_index([("status", ASCENDING)], background=True)
        csat_responses_collection.create_index([("ticket_id", ASCENDING)], background=True)
        csat_tokens_collection.create_index("token", unique=True, background=True)
        csat_tokens_collection.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, background=True)
        tickets_collection.create_index([("email_thread_id", ASCENDING)], background=True)
        tickets_collection.create_index([("email_rfc_message_id", ASCENDING)], sparse=True, background=True)
        tickets_collection.create_index([("last_reply_message_id", ASCENDING)], sparse=True, background=True)
        tickets_collection.create_index([("email_thread_message_ids", ASCENDING)], sparse=True, background=True)
        email_replies_collection.create_index([("ticket_id", ASCENDING)], background=True)
        email_replies_collection.create_index("email_rfc_message_id", unique=True, sparse=True, background=True)
        # Email threads indexes
        from database import email_threads_collection
        email_threads_collection.create_index([("ticket_id", ASCENDING), ("created_at", DESCENDING)], background=True)
        email_threads_collection.create_index([("message_id", ASCENDING), ("direction", ASCENDING)], background=True)
        email_threads_collection.create_index([("direction", ASCENDING)], background=True)
        email_threads_collection.create_index([("gmail_thread_id", ASCENDING)], sparse=True, background=True)
        canned_responses_collection.create_index("response_id", unique=True, background=True)
        canned_responses_collection.create_index([("scope", ASCENDING), ("shortcode", ASCENDING)], background=True)
        routing_rules_collection.create_index("rule_id", unique=True, background=True)
        routing_rules_collection.create_index([("is_active", ASCENDING), ("priority", DESCENDING)], background=True)
        sla_escalation_rules_collection.create_index("rule_id", unique=True, background=True)
        sla_escalation_rules_collection.create_index([("is_active", ASCENDING), ("priority", DESCENDING)], background=True)
        shifts_collection.create_index("shift_id", unique=True, background=True)
        shifts_collection.create_index([("team_id", ASCENDING)], background=True)
        logger.info("[INDEXES] All MongoDB indexes created")
    except Exception as e:
        logger.warning(f"[INDEXES] Some indexes may already exist: {e}")
    try:
        tickets_collection.create_index([("source", ASCENDING)], background=True)
        tickets_collection.create_index([("tags", ASCENDING)], background=True)
        tickets_collection.create_index([("priority", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("source", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("status", ASCENDING), ("priority", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("assignee_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("email_sender_name", ASCENDING)], background=True)
    except Exception as e:
        logger.warning(f"[INDEXES] Advanced filtering indexes partial: {e}")
    try:
        custom_inboxes_collection.create_index("inbox_id", unique=True, background=True)
        custom_inboxes_collection.create_index([("owner_id", ASCENDING)], background=True)
        custom_inboxes_collection.create_index([("shared_with", ASCENDING)], background=True)
    except Exception as e:
        logger.warning(f"[INDEXES] Custom inboxes indexes partial: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    global auto_close_task
    await stop_pubsub()
    if auto_close_task:
        auto_close_task.cancel()
        try:
            await auto_close_task
        except asyncio.CancelledError:
            pass
    logger.info(f"[SHUTDOWN] Instance {_instance_id} shutdown complete")


# Initialize search engine
search_engine = get_search_engine(db)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
