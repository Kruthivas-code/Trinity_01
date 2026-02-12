from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Response, Request, Cookie, Header, Security, BackgroundTasks, Query
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone, time
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson import ObjectId
import os
import json
import csv
import io
import uuid
import httpx
import base64
import re
import secrets
import hashlib
import pytz
import asyncio
import logging
import traceback
import bleach
import shutil
from email.utils import parseaddr
from html import unescape
from dotenv import load_dotenv
from functools import wraps
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import bcrypt
# Centralized modules
from database import (
    db, client, MONGO_URL,
    users_collection, tickets_collection, sessions_collection, api_keys_collection,
    counters_collection, gmail_tokens_collection, email_threads_collection,
    email_replies_collection, teams_collection, messages_collection,
    custom_fields_collection, admin_settings_collection, shifts_collection,
    user_shifts_collection, routing_rules_collection, sla_escalation_rules_collection,
    ticket_changelog_collection, feature_requests_collection, customers_collection,
    csat_responses_collection, csat_tokens_collection, canned_responses_collection,
    sla_policies_collection, webhooks_collection, webhook_logs_collection,
    custom_inboxes_collection, notifications_collection,
    WEBHOOK_EVENT_TYPES, B2C_EMAIL_DOMAINS, SYSTEM_TIMEZONE,
    MAX_TITLE_LENGTH, MAX_DESCRIPTION_LENGTH, MAX_TAGS, MAX_TAG_LENGTH,
    MAX_CUSTOM_FIELD_VALUE_LENGTH, VALID_STATUSES, VALID_PRIORITIES,
    VALID_ESCALATION_LEVELS, VALID_SOURCES, VALID_ROLES,
    GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REDIRECT_URI,
    GMAIL_WATCH_EMAIL, GMAIL_SYNC_QUERY, GMAIL_SCOPES,
    EMERGENT_AUTH_URL, ALLOWED_DOMAIN,
)
from dependencies import (
    get_current_user, get_api_key_user, verify_api_key, generate_api_key,
    require_role, require_admin, require_lead_or_admin,
    API_KEY_HEADER,
)
from models.schemas import (
    SessionCreate, TicketCreate, TicketUpdate, TicketReorder, UserPreferences,
    APIKeyCreate, APIKeyResponse, TeamCreate, TeamUpdate, TeamMemberAdd,
    UserRoleUpdate, InternalNoteCreate, TicketAssign, ShiftCreate, ShiftUpdate,
    UserShiftAssign, TicketEscalate, RoutingRuleCondition, RoutingRuleAction,
    RoutingRuleCreate, RoutingRuleUpdate, SLAEscalationRuleCreate,
    SLAEscalationRuleUpdate, SLAPolicyPriority, SLAPoliciesUpdate, SLAPolicy,
    EmailReplyRequest, SimulatedEmail, CustomFieldCreate, CustomFieldUpdate,
    ExportRequest, AtlasImportRequest, WebhookCreate, WebhookUpdate,
    CustomerCreate, CustomerUpdate, LinkEmailRequest, MergeCustomersRequest,
    CSATRequest, CSATFeedbackRequest, CSATRatingRequest, CannedResponseCreate,
    CannedResponseUpdate, SearchQuery, FeatureRequestCreate, FeatureRequestUpdate,
    BulkUpdateRequest, BulkTagRequest,
    FilterCondition, FilterGroup, FilterRequest, InboxCreate, InboxUpdate, InboxShare,
)
from utils import (
    serialize_doc, log_ticket_change, log_ticket_changes_batch,
    generate_ticket_id, generate_customer_id,
    extract_email_address, extract_domain, is_b2c_email,
    detect_company_from_domain, get_or_create_customer,
    sanitize_html, deliver_webhook, trigger_webhooks,
)

# Add filter for request_id - needed BEFORE configuring basicConfig
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'request_id'):
            record.request_id = 'no-request-id'
        return True

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add filter to ALL existing handlers on root logger
root_logger = logging.getLogger()
request_id_filter = RequestIdFilter()
for handler in root_logger.handlers:
    handler.addFilter(request_id_filter)

# Also add to root logger itself for any future handlers
root_logger.addFilter(request_id_filter)

logger = logging.getLogger(__name__)

# Real-time and Search imports
from realtime import (
    sio, socket_app, broadcast_ticket_update, broadcast_ticket_created, 
    broadcast_ticket_deleted, get_presence_stats, get_users_viewing_ticket, 
    broadcast_leave_created, broadcast_leave_updated, broadcast_leave_deleted, 
    broadcast_mention_notification, initialize_realtime, start_pubsub, stop_pubsub
)
from search import get_search_engine
from leave_management import get_leave_manager, LeaveRequest, LeaveUpdate

# Distributed adapters for multi-instance support
from adapters import set_database, get_lock_adapter

# Load environment variables from .env file
load_dotenv()

# ==================== Environment Validation ====================
def validate_environment():
    """Validate required environment variables at startup"""
    required_vars = ["MONGO_URL"]
    recommended_vars = ["ALLOWED_ORIGINS", "GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET"]
    
    missing_required = []
    missing_recommended = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_required.append(var)
    
    for var in recommended_vars:
        if not os.environ.get(var):
            missing_recommended.append(var)
    
    if missing_required:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_required)}")
    
    if missing_recommended:
        logger.warning(f"Missing recommended environment variables: {', '.join(missing_recommended)}")

# Validate environment on module load
validate_environment()

# ==================== Rate Limiting Setup ====================
# Note: Rate limiter will be reconfigured with MongoDB storage after db connection
# This initial limiter uses in-memory storage as a fallback
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour", "100/minute"],
    strategy="fixed-window",
    storage_uri="memory://"  # Will be replaced with MongoDB after connection
)

# Gmail API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = FastAPI(
    title="Trinity API",
    description="Enterprise ticket management platform with real-time collaboration",
    version="2.0.0"
)

# Add rate limiting to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Mount Socket.IO for WebSocket support
# Socket.IO handles /api/socket.io/ routes (path prefix is NOT stripped by ingress)
app.mount("/api/socket.io", socket_app)

# Include extracted route modules
from routes.filters import router as filters_router
from routes.webhooks import router as webhooks_router
from routes.customers import router as customers_router
from routes.csat import router as csat_router
from routes.canned_responses import router as canned_responses_router
app.include_router(filters_router)
app.include_router(webhooks_router)
app.include_router(customers_router)
app.include_router(csat_router)
app.include_router(canned_responses_router)

# ==================== Request ID Middleware ====================
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request for tracing"""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# ==================== Global Exception Handler ====================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to prevent information leakage"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    # Log the full error with traceback (visible in server logs)
    logger.error(
        f"Unhandled exception: {str(exc)}", 
        extra={"request_id": request_id},
        exc_info=True
    )
    
    # Always return safe error response - never expose internal details
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred",
            "request_id": request_id
        }
    )

# CORS - Allow specific origins for security
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",")
# Default to preview URL if not set
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == [""]:
    ALLOWED_ORIGINS = [
        "https://filter-inbox-fix.preview.emergentagent.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

# Filter out empty strings
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]

# Allowed methods and headers (more restrictive than *)
ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
ALLOWED_HEADERS = [
    "Authorization", 
    "Content-Type", 
    "X-Request-ID", 
    "X-API-Key",
    "X-Session-ID"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
)

# Background tasks
AUTO_CLOSE_HOURS = 24
auto_close_task = None
email_sync_task = None
_instance_id = os.environ.get('INSTANCE_ID', os.environ.get('HOSTNAME', f'instance_{secrets.token_hex(4)}'))

async def auto_close_resolved_tickets():
    """
    Background task that runs every hour to close tickets resolved more than 24 hours ago.
    Uses distributed locking to ensure only one instance runs this task.
    """
    lock_adapter = get_lock_adapter()
    lock_name = "auto_close_resolved_tickets"
    lock_ttl = 3600  # 1 hour lock
    
    while True:
        acquired = False
        try:
            # Try to acquire distributed lock
            acquired = await lock_adapter.acquire(lock_name, _instance_id, lock_ttl)
            
            if not acquired:
                logger.info("[AUTO-CLOSE] Another instance holds the lock, skipping this run")
                await asyncio.sleep(3600)  # Wait an hour before trying again
                continue
            
            logger.info(f"[AUTO-CLOSE] Lock acquired by {_instance_id}, running auto-close task")
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=AUTO_CLOSE_HOURS)
            
            # Find resolved tickets older than 24 hours
            query = {
                "status": "resolved",
                "resolved_at": {"$lte": cutoff_time}
            }
            
            # Get ticket IDs for system messages
            tickets_to_close = list(tickets_collection.find(query, {"ticket_id": 1, "_id": 0}))
            
            if tickets_to_close:
                ticket_ids = [t["ticket_id"] for t in tickets_to_close]
                now = datetime.now(timezone.utc)
                
                # Batch update all tickets at once
                result = tickets_collection.update_many(
                    query,
                    {"$set": {
                        "status": "closed",
                        "closed_at": now,
                        "auto_closed": True,
                        "updated_at": now
                    }}
                )
                
                # Batch insert system messages
                system_messages = [
                    {
                        "message_id": f"msg_{uuid4().hex[:12]}",
                        "ticket_id": tid,
                        "type": "system",
                        "text": f"Auto-closed after {AUTO_CLOSE_HOURS} hours in resolved status",
                        "created_by": "system",
                        "created_at": now
                    }
                    for tid in ticket_ids
                ]
                if system_messages:
                    messages_collection.insert_many(system_messages)
                
                closed_count = result.modified_count
                logger.info(f"[AUTO-CLOSE] Auto-closed {closed_count} resolved tickets")
                
        except asyncio.CancelledError:
            logger.info("[AUTO-CLOSE] Task cancelled")
            raise
        except Exception as e:
            logger.error(f"[AUTO-CLOSE] Error in auto-close task: {e}")
        finally:
            # Release lock if we acquired it
            if acquired:
                await lock_adapter.release(lock_name, _instance_id)
                logger.info(f"[AUTO-CLOSE] Lock released by {_instance_id}")
        
        # Run every hour
        await asyncio.sleep(3600)


async def auto_sync_emails():
    """
    Background task that monitors the IMAP mailbox using IDLE for near-realtime sync.
    
    Uses IMAP IDLE (push) instead of polling - new emails appear in ~1-5 seconds.
    Falls back to UID-based polling every 60s if IDLE fails.
    """
    # Wait a bit before starting to let the app fully initialize
    await asyncio.sleep(10)
    
    imap_sync_state = db.imap_sync_state
    
    from imap_sync import get_imap_config, fetch_emails_by_uid, get_current_max_uid, IMAPIdleWatcher
    
    config = get_imap_config()
    if not config["email"] or not config["password"]:
        logger.info("[EMAIL-SYNC] IMAP not configured, email sync disabled")
        return
    
    # Read or seed the last processed UID
    state = imap_sync_state.find_one({"_id": "imap_last_uid"})
    last_uid = state["last_uid"] if state else 0
    
    if last_uid == 0:
        loop = asyncio.get_event_loop()
        seed_uid = await loop.run_in_executor(None, lambda: get_current_max_uid(config))
        if seed_uid > 0:
            imap_sync_state.update_one(
                {"_id": "imap_last_uid"},
                {"$set": {"last_uid": seed_uid, "updated_at": datetime.now(timezone.utc), "seeded": True}},
                upsert=True
            )
            last_uid = seed_uid
            logger.info(f"[EMAIL-SYNC] Seeded initial UID to {seed_uid}")
    
    # Get reference to the running event loop for thread-safe callbacks
    loop = asyncio.get_event_loop()
    
    def on_new_mail(new_emails, new_max_uid):
        """Called from the IDLE thread when new mail arrives."""
        # Schedule the async processing on the event loop
        asyncio.run_coroutine_threadsafe(
            _process_new_emails(new_emails, new_max_uid),
            loop
        )
    
    async def _process_new_emails(new_emails, new_max_uid):
        """Process new emails: create tickets/replies and broadcast."""
        created_count = 0
        reply_count = 0
        
        for eml in new_emails:
            if eml["message_id"]:
                existing = tickets_collection.find_one({"email_rfc_message_id": eml["message_id"]})
                if existing:
                    continue
                existing_reply = email_replies_collection.find_one({"email_rfc_message_id": eml["message_id"]})
                if existing_reply:
                    continue
            
            existing_thread_ticket = None
            
            if eml["in_reply_to"]:
                existing_thread_ticket = tickets_collection.find_one({
                    "$or": [
                        {"email_rfc_message_id": eml["in_reply_to"]},
                        {"last_reply_message_id": eml["in_reply_to"]},
                        {"email_thread_message_ids": eml["in_reply_to"]}
                    ]
                })
                if not existing_thread_ticket:
                    sent_reply = email_replies_collection.find_one({
                        "our_message_id": eml["in_reply_to"],
                        "direction": "outgoing"
                    })
                    if sent_reply:
                        existing_thread_ticket = tickets_collection.find_one({"ticket_id": sent_reply["ticket_id"]})
            
            if not existing_thread_ticket and eml["references"]:
                for ref in eml["references"].split():
                    ref = ref.strip()
                    if not ref:
                        continue
                    existing_thread_ticket = tickets_collection.find_one({
                        "$or": [
                            {"email_rfc_message_id": ref},
                            {"last_reply_message_id": ref},
                            {"email_thread_message_ids": ref}
                        ]
                    })
                    if existing_thread_ticket:
                        break
            
            if existing_thread_ticket:
                sanitized_html_content = sanitize_html(eml["html"][:100000]) if eml["html"] else None
                
                reply_id = f"reply_{uuid.uuid4().hex[:12]}"
                email_replies_collection.insert_one({
                    "reply_id": reply_id,
                    "ticket_id": existing_thread_ticket["ticket_id"],
                    "direction": "incoming",
                    "from_email": eml["sender_email"],
                    "from_name": eml["sender_name"],
                    "to_email": eml["to"],
                    "subject": eml["subject"] or "Re: " + existing_thread_ticket.get("title", ""),
                    "body": (eml["text"] or "")[:50000],
                    "body_html": sanitized_html_content,
                    "email_rfc_message_id": eml["message_id"],
                    "email_in_reply_to": eml["in_reply_to"],
                    "email_references": eml["references"],
                    "email_date": eml["date"].isoformat() if eml["date"] else None,
                    "created_at": datetime.now(timezone.utc),
                    "status": "received"
                })
                
                messages_collection.insert_one({
                    "message_id": f"msg_{uuid.uuid4().hex[:12]}",
                    "ticket_id": existing_thread_ticket["ticket_id"],
                    "type": "customer_reply",
                    "content": (eml["text"] or "")[:50000],
                    "content_html": sanitized_html_content,
                    "author_id": None,
                    "author_name": eml["sender_name"],
                    "author_email": eml["sender_email"],
                    "email_reply_id": reply_id,
                    "email_date": eml["date"].isoformat() if eml["date"] else None,
                    "created_at": datetime.now(timezone.utc)
                })
                
                tickets_collection.update_one(
                    {"ticket_id": existing_thread_ticket["ticket_id"]},
                    {
                        "$set": {
                            "status": "todo",
                            "updated_at": datetime.now(timezone.utc),
                            "last_customer_reply_at": datetime.now(timezone.utc),
                            "last_reply_message_id": eml["message_id"]
                        },
                        "$push": {
                            "email_thread_message_ids": eml["message_id"]
                        }
                    }
                )
                reply_count += 1
                logger.info(f"[EMAIL-SYNC] Added reply to ticket {existing_thread_ticket['ticket_id']} from {eml['sender_email']}")
                
                try:
                    from realtime import broadcast_ticket_update
                    updated_ticket = tickets_collection.find_one({"ticket_id": existing_thread_ticket["ticket_id"]})
                    await broadcast_ticket_update(
                        existing_thread_ticket["ticket_id"],
                        "updated",
                        serialize_doc(updated_ticket),
                        {"user_id": "system", "name": "Email Sync"}
                    )
                except Exception as e:
                    logger.error(f"[EMAIL-SYNC] FAILED to broadcast ticket:update: {e}", exc_info=True)
                
                continue
            
            # --- New ticket ---
            ticket_id = generate_ticket_id()
            sanitized_html_content = sanitize_html(eml["html"][:100000]) if eml["html"] else None
            
            ticket_doc = {
                "ticket_id": ticket_id,
                "uuid": str(uuid.uuid4()),
                "title": (eml["subject"] or "No Subject")[:200],
                "description": (eml["text"] or "")[:5000],
                "status": "todo",
                "priority": "medium",
                "source": "email",
                "email_rfc_message_id": eml["message_id"],
                "email_references": eml["references"],
                "email_in_reply_to": eml["in_reply_to"],
                "email_sender": eml["from_header"],
                "email_sender_name": eml["sender_name"],
                "customer_email": eml["sender_email"],
                "email_to": eml["to"],
                "email_cc": eml["cc"],
                "email_date": eml["date"].isoformat() if eml["date"] else None,
                "email_html": sanitized_html_content,
                "email_text": (eml["text"] or "")[:50000],
                "email_preview": eml["preview"],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "assignee_id": None,
                "escalation_level": "L1"
            }
            tickets_collection.insert_one(ticket_doc)
            created_count += 1
            
            try:
                from realtime import broadcast_ticket_created
                await broadcast_ticket_created(serialize_doc(ticket_doc), {"user_id": "system", "name": "Email Sync"})
                logger.info(f"[EMAIL-SYNC] Broadcast ticket:created for {ticket_id}")
            except Exception as e:
                logger.error(f"[EMAIL-SYNC] FAILED to broadcast ticket:created: {e}", exc_info=True)
        
        # Persist the new max UID
        if new_max_uid > last_uid:
            imap_sync_state.update_one(
                {"_id": "imap_last_uid"},
                {"$set": {"last_uid": new_max_uid, "updated_at": datetime.now(timezone.utc)}},
                upsert=True
            )
            # Update the watcher's state too
            if idle_watcher:
                idle_watcher.update_last_uid(new_max_uid)
        
        if created_count > 0 or reply_count > 0:
            logger.info(f"[EMAIL-SYNC] Created {created_count} tickets, added {reply_count} replies")
    
    # Start the IDLE watcher
    idle_watcher = IMAPIdleWatcher(config, last_uid=last_uid, on_new_mail=on_new_mail)
    idle_watcher.start()
    logger.info("[EMAIL-SYNC] IMAP IDLE watcher started for near-realtime sync")
    
    # Keep this task alive and monitor the watcher
    try:
        while True:
            await asyncio.sleep(30)
            if not idle_watcher.is_running:
                logger.warning("[EMAIL-SYNC] IDLE watcher died, restarting...")
                idle_watcher.start()
    except asyncio.CancelledError:
        logger.info("[EMAIL-SYNC] Task cancelled, stopping IDLE watcher")
        idle_watcher.stop()
        raise



@app.on_event("startup")
async def startup_event():
    """Start background tasks and initialize distributed adapters on app startup"""
    global auto_close_task, email_sync_task
    
    # Initialize distributed adapters with the database
    # Note: We need to use async motor client for the adapters
    from motor.motor_asyncio import AsyncIOMotorClient
    motor_client = AsyncIOMotorClient(MONGO_URL)
    motor_db = motor_client[os.environ.get('DB_NAME', 'tickflow')]
    
    # Set up adapters for distributed presence and locking
    set_database(motor_db)
    
    # Initialize realtime module with async database
    initialize_realtime(motor_db)
    
    # Start pub/sub listener for cross-instance messaging
    await start_pubsub()
    
    # Create MongoDB indexes for query performance (idempotent - safe to call multiple times)
    await create_mongodb_indexes()
    
    # Start the background tasks (with distributed locking)
    auto_close_task = asyncio.create_task(auto_close_resolved_tickets())
    email_sync_task = asyncio.create_task(auto_sync_emails())
    
    logger.info(f"[STARTUP] Instance {_instance_id} started with distributed adapters and email sync")


async def create_mongodb_indexes():
    """
    Create MongoDB indexes for optimal query performance.
    These indexes improve performance for the most common queries.
    """
    try:
        # Tickets collection indexes
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
        # Compound indexes for paginated queries
        tickets_collection.create_index([("status", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("escalation_level", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("assignee_id", ASCENDING), ("created_at", DESCENDING)], background=True)
        # Index for auto-close query
        tickets_collection.create_index([("status", ASCENDING), ("resolved_at", ASCENDING)], background=True)
        # Index for email dedup
        tickets_collection.create_index("email_rfc_message_id", unique=True, sparse=True, background=True)
        logger.info("[INDEXES] Created tickets collection indexes")
        
        # User sessions collection indexes  
        sessions_collection.create_index("session_token", unique=True, background=True)
        sessions_collection.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, background=True)
        sessions_collection.create_index([("user_id", ASCENDING)], background=True)
        logger.info("[INDEXES] Created user_sessions collection indexes")
        
        # Users collection indexes
        users_collection.create_index("user_id", unique=True, background=True)
        users_collection.create_index("email", unique=True, sparse=True, background=True)
        logger.info("[INDEXES] Created users collection indexes")
        
        # Customers collection indexes (Atlas import deduplication)
        customers_collection.create_index("atlas_user_id", unique=True, sparse=True, background=True)
        logger.info("[INDEXES] Created customers collection indexes")
        
        # Messages collection indexes
        messages_collection.create_index([("ticket_id", ASCENDING), ("created_at", ASCENDING)], background=True)
        messages_collection.create_index([("ticket_id", ASCENDING)], background=True)
        messages_collection.create_index("atlas_message_id", unique=True, sparse=True, background=True)
        logger.info("[INDEXES] Created messages collection indexes")
        
        # Ticket changelog indexes
        ticket_changelog_collection.create_index([("ticket_id", ASCENDING), ("changed_at", DESCENDING)], background=True)
        ticket_changelog_collection.create_index([("ticket_uuid", ASCENDING)], background=True)
        logger.info("[INDEXES] Created ticket_changelog collection indexes")
        
        # Teams collection indexes
        teams_collection.create_index("team_id", unique=True, background=True)
        logger.info("[INDEXES] Created teams collection indexes")
        
        # API keys collection indexes
        api_keys_collection.create_index("key_hash", unique=True, background=True)
        api_keys_collection.create_index([("user_id", ASCENDING)], background=True)
        logger.info("[INDEXES] Created api_keys collection indexes")
        
        # Feature requests collection indexes
        feature_requests_collection.create_index("feature_id", unique=True, background=True)
        feature_requests_collection.create_index([("status", ASCENDING)], background=True)
        logger.info("[INDEXES] Created feature_requests collection indexes")
        
        # CSAT collections indexes
        csat_responses_collection.create_index([("ticket_id", ASCENDING)], background=True)
        csat_tokens_collection.create_index("token", unique=True, background=True)
        csat_tokens_collection.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, background=True)
        logger.info("[INDEXES] Created CSAT collection indexes")
        
        # Email threading indexes - for fallback thread matching
        tickets_collection.create_index([("email_thread_id", ASCENDING)], background=True)
        tickets_collection.create_index([("email_rfc_message_id", ASCENDING)], sparse=True, background=True)
        tickets_collection.create_index([("last_reply_message_id", ASCENDING)], sparse=True, background=True)
        tickets_collection.create_index([("email_thread_message_ids", ASCENDING)], sparse=True, background=True)
        email_replies_collection.create_index([("ticket_id", ASCENDING)], background=True)
        email_replies_collection.create_index([("gmail_message_id", ASCENDING)], sparse=True, background=True)
        email_replies_collection.create_index([("our_message_id", ASCENDING)], sparse=True, background=True)
        email_replies_collection.create_index("email_rfc_message_id", unique=True, sparse=True, background=True)
        logger.info("[INDEXES] Created email threading indexes")
        
        # Canned responses indexes
        canned_responses_collection.create_index("response_id", unique=True, background=True)
        canned_responses_collection.create_index([("scope", ASCENDING), ("shortcode", ASCENDING)], background=True)
        canned_responses_collection.create_index([("created_by", ASCENDING)], background=True)
        logger.info("[INDEXES] Created canned_responses collection indexes")
        
        # Routing rules indexes
        routing_rules_collection.create_index("rule_id", unique=True, background=True)
        routing_rules_collection.create_index([("is_active", ASCENDING), ("priority", DESCENDING)], background=True)
        logger.info("[INDEXES] Created routing_rules collection indexes")
        
        # SLA escalation rules indexes
        sla_escalation_rules_collection.create_index("rule_id", unique=True, background=True)
        sla_escalation_rules_collection.create_index([("is_active", ASCENDING), ("priority", DESCENDING)], background=True)
        logger.info("[INDEXES] Created sla_escalation_rules collection indexes")
        
        # Shifts indexes
        shifts_collection.create_index("shift_id", unique=True, background=True)
        shifts_collection.create_index([("team_id", ASCENDING)], background=True)
        logger.info("[INDEXES] Created shifts collection indexes")
        
        logger.info("[INDEXES] All MongoDB indexes created successfully")
    except Exception as e:
        logger.warning(f"[INDEXES] Some indexes may already exist: {e}")
    
    # Advanced filtering indexes - separate try block to ensure creation
    try:
        tickets_collection.create_index([("source", ASCENDING)], background=True)
        tickets_collection.create_index([("tags", ASCENDING)], background=True)
        tickets_collection.create_index([("priority", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("source", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("status", ASCENDING), ("priority", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("assignee_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)], background=True)
        tickets_collection.create_index([("email_sender_name", ASCENDING)], background=True)
        logger.info("[INDEXES] Created advanced filtering indexes")
    except Exception as e:
        logger.warning(f"[INDEXES] Advanced filtering indexes partial: {e}")
    
    try:
        custom_inboxes_collection.create_index("inbox_id", unique=True, background=True)
        custom_inboxes_collection.create_index([("owner_id", ASCENDING)], background=True)
        custom_inboxes_collection.create_index([("shared_with", ASCENDING)], background=True)
        logger.info("[INDEXES] Created custom_inboxes collection indexes")
    except Exception as e:
        logger.warning(f"[INDEXES] Custom inboxes indexes partial: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cancel background tasks and cleanup on app shutdown"""
    global auto_close_task
    
    # Stop pub/sub listener
    await stop_pubsub()
    
    if auto_close_task:
        auto_close_task.cancel()
        try:
            await auto_close_task
        except asyncio.CancelledError:
            pass
        logger.info("[SHUTDOWN] Auto-close background task cancelled")
    
    logger.info(f"[SHUTDOWN] Instance {_instance_id} shutdown complete")

# MongoDB rate limiter (now that db is imported from database.py)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour", "100/minute"],
    strategy="fixed-window",
    storage_uri=MONGO_URL,
    storage_options={"database_name": os.environ.get("DB_NAME")}
)
app.state.limiter = limiter
logger.info("[STARTUP] Rate limiting initialized with MongoDB backend")

# Phase 6: Initialize Search Engine
search_engine = get_search_engine(db)

# ==================== Utility Functions ====================


# Utility functions (log_ticket_change, serialize_doc, etc.) now in utils.py
# Webhook delivery (deliver_webhook, trigger_webhooks) now in utils.py


# Routes
@app.get("/api/health")
async def health():
    """
    Comprehensive health check endpoint.
    Checks database connectivity and returns system status.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "checks": {}
    }
    
    # Check MongoDB connectivity
    try:
        # Ping the database
        client.admin.command('ping')
        health_status["checks"]["database"] = {
            "status": "healthy",
            "type": "mongodb"
        }
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "type": "mongodb",
            "error": "Connection failed"
        }
        # Log full error for debugging
        logger.error(f"Health check database error: {e}")
    
    # Check if required collections exist
    try:
        collections = db.list_collection_names()
        required_collections = ["users", "tickets", "user_sessions"]
        missing = [c for c in required_collections if c not in collections]
        health_status["checks"]["collections"] = {
            "status": "healthy" if not missing else "warning",
            "missing": missing if missing else None
        }
    except Exception as e:
        health_status["checks"]["collections"] = {
            "status": "error",
            "error": "Check failed"
        }
        # Log full error for debugging
        logger.error(f"Health check collections error: {e}")
    
    # Return appropriate status code
    if health_status["status"] == "unhealthy":
        return JSONResponse(status_code=503, content=health_status)
    
    return health_status

# Emergent Auth endpoints
@app.post("/api/auth/session")
@limiter.limit("10/minute")  # Rate limit authentication attempts
async def create_session(request: Request, session_data: SessionCreate, response: Response):
    """Exchange session_id for session_token"""
    try:
        logger.info(f"[AUTH] Received session_id: {session_data.session_id[:20]}...")
        
        # Call Emergent Auth API to get user data
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"[AUTH] Calling Emergent Auth API: {EMERGENT_AUTH_URL}")
            auth_response = await client.get(
                EMERGENT_AUTH_URL,
                headers={"X-Session-ID": session_data.session_id}
            )
            logger.info(f"[AUTH] Emergent Auth response status: {auth_response.status_code}")
        
        if auth_response.status_code != 200:
            logger.info(f"[AUTH] Invalid session_id, status: {auth_response.status_code}")
            raise HTTPException(status_code=401, detail="Invalid session_id")
        
        user_data = auth_response.json()
        logger.info(f"[AUTH] Got user data: {user_data.get('email')}")
        
        # Verify email domain (skip if ALLOWED_DOMAIN is None)
        email = user_data.get("email", "")
        if ALLOWED_DOMAIN and not email.endswith(f"@{ALLOWED_DOMAIN}"):
            logger.info(f"[AUTH] Domain mismatch: {email} vs @{ALLOWED_DOMAIN}")
            raise HTTPException(
                status_code=403,
                detail=f"Access restricted to @{ALLOWED_DOMAIN} emails only"
            )
        
        logger.info(f"[AUTH] Email verified: {email}")
        session_token = user_data["session_token"]
        
        # Generate user_id if new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        
        # Create or update user in database
        logger.info(f"[AUTH] Upserting user: {email}")
        users_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "email": email,
                    "name": user_data.get("name", ""),
                    "picture": user_data.get("picture", ""),
                    "updated_at": datetime.now(timezone.utc)
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "created_at": datetime.now(timezone.utc),
                    "preferences": {"theme": "dark"}
                }
            },
            upsert=True
        )
        
        # Get the user document to get the actual user_id
        logger.info("[AUTH] Fetching user document")
        user_doc = users_collection.find_one({"email": email}, {"_id": 0})
        if not user_doc:
            raise Exception(f"User document not found after upsert: {email}")
        
        # If user_id doesn't exist (old user from previous auth system), add it
        if "user_id" not in user_doc:
            logger.info("[AUTH] Old user detected, adding user_id field")
            new_user_id = f"user_{uuid.uuid4().hex[:12]}"
            users_collection.update_one(
                {"email": email},
                {"$set": {"user_id": new_user_id}}
            )
            user_doc["user_id"] = new_user_id
        
        actual_user_id = user_doc["user_id"]
        logger.info(f"[AUTH] User ID: {actual_user_id}")
        
        # Store session
        logger.info("[AUTH] Storing session")
        sessions_collection.update_one(
            {"session_token": session_token},
            {
                "$set": {
                    "user_id": actual_user_id,
                    "session_token": session_token,
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
                    "created_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        # Set httpOnly cookie
        logger.info("[AUTH] Setting cookie")
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=7 * 24 * 60 * 60,  # 7 days
            path="/"
        )
        
        logger.info("[AUTH] Success! Returning user data")
        return serialize_doc(user_doc)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"[AUTH] ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user data"""
    return current_user

@app.post("/api/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Logout user and clear session"""
    if session_token:
        sessions_collection.delete_one({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}

# ==================== Shift-Start Assignment Trigger ====================

@app.post("/api/auth/shift-start")
async def trigger_shift_assignment(current_user: dict = Depends(get_current_user)):
    """
    Trigger shift-start auto-assignment of queued tickets.
    Called when a user logs in or connects to real-time (WebSocket).
    
    Only assigns tickets if:
    1. Auto-assignment and auto-reassign settings are enabled
    2. User is currently on shift for their team(s)
    3. There are queued/unassigned tickets
    """
    assigned = trigger_shift_start_assignment(current_user["user_id"])
    
    return {
        "triggered": True,
        "user_id": current_user["user_id"],
        "tickets_assigned": len(assigned),
        "assigned_tickets": assigned
    }

# ==================== API Key Management ====================

@app.post("/api/auth/api-keys")
@limiter.limit("10/hour")  # Rate limit API key creation
async def create_api_key(
    request: Request,
    key_data: APIKeyCreate,
    current_user: dict = Depends(get_current_user)
):
    """Generate a new API key"""
    key, key_hash = generate_api_key()
    key_id = f"key_{uuid.uuid4().hex[:12]}"
    
    api_key_doc = {
        "key_id": key_id,
        "key_hash": key_hash,
        "key_prefix": key[:12],  # Store prefix for identification
        "name": key_data.name,
        "description": key_data.description,
        "created_by": current_user["user_id"],
        "created_by_email": current_user.get("email"),
        "created_at": datetime.now(timezone.utc),
        "last_used_at": None,
        "usage_count": 0,
        "revoked": False
    }
    
    api_keys_collection.insert_one(api_key_doc)
    
    # Return the key only once - it won't be retrievable later
    return {
        "key_id": key_id,
        "name": key_data.name,
        "key": key,  # Only shown once!
        "created_at": api_key_doc["created_at"].isoformat(),
        "message": "Save this key securely - it won't be shown again!"
    }

@app.get("/api/auth/api-keys")
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    """List all API keys for the current user"""
    keys = list(api_keys_collection.find(
        {"created_by": current_user["user_id"], "revoked": {"$ne": True}},
        {"key_hash": 0}  # Don't return the hash
    ))
    
    return [
        {
            "key_id": k["key_id"],
            "name": k["name"],
            "key_prefix": k.get("key_prefix", "***"),
            "description": k.get("description", ""),
            "created_at": k["created_at"].isoformat() if isinstance(k["created_at"], datetime) else k["created_at"],
            "last_used_at": k["last_used_at"].isoformat() if k.get("last_used_at") else None,
            "usage_count": k.get("usage_count", 0)
        }
        for k in keys
    ]

@app.delete("/api/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Revoke an API key"""
    result = api_keys_collection.update_one(
        {"key_id": key_id, "created_by": current_user["user_id"]},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"message": "API key revoked"}

# User profile endpoints
@app.get("/api/users/me")
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    return current_user

@app.put("/api/users/me/preferences")
async def update_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user)
):
    """Update user preferences (theme, etc.)"""
    users_collection.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {"preferences": preferences.dict(), "updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": "Preferences updated"}

@app.get("/api/users")
async def get_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get users with pagination and optional search"""
    # Cap the limit to prevent excessive data retrieval
    limit = min(limit, 500)
    
    query = {}
    if search:
        # Search by name or email
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count for pagination info
    total = users_collection.count_documents(query)
    
    users = list(users_collection.find(
        query, 
        {"password": 0}
    ).skip(skip).limit(limit))
    
    result = []
    for user in users:
        serialized = serialize_doc(user)
        # Ensure id is set from user_id or _id
        if "id" not in serialized:
            if "user_id" in user:
                serialized["id"] = user["user_id"]
            elif "_id" in user:
                serialized["id"] = str(user["_id"])
        result.append(serialized)
    
    return {
        "items": result,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(result) < total
    }

# ==================== Phase 2: Team Management ====================

@app.post("/api/teams")
async def create_team(
    team_data: TeamCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new team"""
    team_id = f"team_{uuid.uuid4().hex[:12]}"
    
    team_doc = {
        "team_id": team_id,
        "name": team_data.name,
        "escalation_level": team_data.escalation_level,  # L1, L2, L3
        "description": team_data.description,
        "members": [],
        "lead_id": None,
        "last_assigned_idx": -1,  # For round-robin
        "timezone": SYSTEM_TIMEZONE,  # Default to IST
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    teams_collection.insert_one(team_doc)
    return serialize_doc(team_doc)

@app.get("/api/teams")
async def get_teams(current_user: dict = Depends(get_current_user)):
    """List all teams - optimized to avoid N+1 queries"""
    teams = list(teams_collection.find({}, {"_id": 0}))
    
    # Batch fetch all users who are members of any team (single query)
    all_member_ids = set()
    for team in teams:
        all_member_ids.update(team.get("members", []))
    
    # Single query to get all users
    all_users = {}
    if all_member_ids:
        users_list = list(users_collection.find(
            {"user_id": {"$in": list(all_member_ids)}},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1}
        ))
        all_users = {u["user_id"]: u for u in users_list}
    
    # Batch fetch all shift assignments (single query)
    all_shifts = {}
    user_shift_docs = list(user_shifts_collection.find(
        {"user_id": {"$in": list(all_member_ids)}},
        {"_id": 0}
    ))
    for us in user_shift_docs:
        if us["user_id"] not in all_shifts:
            all_shifts[us["user_id"]] = []
        all_shifts[us["user_id"]].append(us)
    
    # Batch fetch all active shifts (single query)
    shift_ids = set(us.get("shift_id") for us in user_shift_docs)
    active_shifts = {}
    if shift_ids:
        shifts_list = list(shifts_collection.find(
            {"shift_id": {"$in": list(shift_ids)}, "is_active": True},
            {"_id": 0}
        ))
        active_shifts = {s["shift_id"]: s for s in shifts_list}
    
    # Current time for shift calculations
    now = get_ist_now()
    current_weekday = now.isoweekday()
    current_time = now.time()
    
    def is_user_on_shift_cached(user_id: str, team_id: str) -> bool:
        """Check if user is on shift using cached data"""
        user_shifts_list = all_shifts.get(user_id, [])
        for us in user_shifts_list:
            if us.get("team_id") != team_id:
                continue
            shift = active_shifts.get(us.get("shift_id"))
            if not shift:
                continue
            if current_weekday not in shift.get("days_of_week", []):
                continue
            start = parse_time_str(shift.get("start_time", "00:00"))
            end = parse_time_str(shift.get("end_time", "23:59"))
            if start <= end:
                if start <= current_time <= end:
                    return True
            else:
                if current_time >= start or current_time <= end:
                    return True
        return False
    
    # Enrich teams with member details
    for team in teams:
        team["member_count"] = len(team.get("members", []))
        members = []
        on_shift_count = 0
        
        for member_id in team.get("members", []):
            user = all_users.get(member_id)
            if user:
                member = user.copy()
                member["is_on_shift"] = is_user_on_shift_cached(member_id, team.get("team_id"))
                if member["is_on_shift"]:
                    on_shift_count += 1
                members.append(member)
        
        team["member_details"] = members
        team["on_shift_count"] = on_shift_count
    
    return [serialize_doc(team) for team in teams]

@app.get("/api/teams/{team_id}")
async def get_team(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get team details"""
    team = teams_collection.find_one({"team_id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get member details
    if team.get("members"):
        members = list(users_collection.find(
            {"user_id": {"$in": team["members"]}},
            {"_id": 0}
        ))
        team["member_details"] = [serialize_doc(m) for m in members]
    
    return serialize_doc(team)

@app.put("/api/teams/{team_id}")
async def update_team(
    team_id: str,
    team_data: TeamUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update team details"""
    update_data = {k: v for k, v in team_data.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    result = teams_collection.update_one(
        {"team_id": team_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return teams_collection.find_one({"team_id": team_id}, {"_id": 0})

@app.delete("/api/teams/{team_id}")
async def delete_team(
    team_id: str,
    current_user: dict = Depends(require_lead_or_admin)  # Require lead or admin
):
    """Delete a team - requires lead or admin role"""
    # Remove team_id from all users first
    users_collection.update_many(
        {"team_id": team_id},
        {"$unset": {"team_id": ""}}
    )
    
    result = teams_collection.delete_one({"team_id": team_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")
    
    logger.info(f"Team {team_id} deleted by user {current_user.get('user_id')}")
    return {"message": "Team deleted"}

@app.post("/api/teams/{team_id}/members")
async def add_team_member(
    team_id: str,
    member: TeamMemberAdd,
    current_user: dict = Depends(get_current_user)
):
    """Add a member to a team"""
    # Verify team exists
    team = teams_collection.find_one({"team_id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verify user exists
    user = users_collection.find_one({"user_id": member.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Add to team members
    teams_collection.update_one(
        {"team_id": team_id},
        {
            "$addToSet": {"members": member.user_id},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    
    # Update user's team_id
    users_collection.update_one(
        {"user_id": member.user_id},
        {"$set": {"team_id": team_id, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Member added", "team_id": team_id, "user_id": member.user_id}

@app.delete("/api/teams/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a member from a team"""
    # Remove from team
    result = teams_collection.update_one(
        {"team_id": team_id},
        {
            "$pull": {"members": user_id},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Clear user's team_id
    users_collection.update_one(
        {"user_id": user_id},
        {"$unset": {"team_id": ""}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Member removed"}

# ==================== User Role Management ====================

@app.put("/api/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_data: UserRoleUpdate,
    current_user: dict = Depends(require_admin)  # Require admin role
):
    """Update user role and team assignment - requires admin role"""
    update_data = {
        "role": role_data.role,
        "updated_at": datetime.now(timezone.utc)
    }
    
    if role_data.team_id is not None:
        update_data["team_id"] = role_data.team_id
    if role_data.skills is not None:
        update_data["skills"] = role_data.skills
    if role_data.max_tickets is not None:
        update_data["max_tickets"] = role_data.max_tickets
    
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If team_id changed, update team memberships
    if role_data.team_id:
        # Remove from old teams
        teams_collection.update_many(
            {"members": user_id},
            {"$pull": {"members": user_id}}
        )
        # Add to new team
        teams_collection.update_one(
            {"team_id": role_data.team_id},
            {"$addToSet": {"members": user_id}}
        )
    
    user = users_collection.find_one({"user_id": user_id}, {"_id": 0})
    return serialize_doc(user)

# ==================== Shift Management ====================

@app.post("/api/shifts")
async def create_shift(
    shift_data: ShiftCreate,
    current_user: dict = Depends(require_lead_or_admin)  # Require lead or admin
):
    """Create a new shift for a team - requires lead or admin role"""
    # Verify team exists
    team = teams_collection.find_one({"team_id": shift_data.team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    shift_id = f"shift_{uuid.uuid4().hex[:12]}"
    
    shift_doc = {
        "shift_id": shift_id,
        "team_id": shift_data.team_id,
        "name": shift_data.name,
        "start_time": shift_data.start_time,
        "end_time": shift_data.end_time,
        "days_of_week": shift_data.days_of_week,
        "is_active": True,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    shifts_collection.insert_one(shift_doc)
    return serialize_doc(shift_doc)

@app.get("/api/shifts")
async def get_all_shifts(current_user: dict = Depends(get_current_user)):
    """Get all shifts"""
    shifts = list(shifts_collection.find({}, {"_id": 0}))
    
    # Enrich with team name, assigned user count, and user details
    for shift in shifts:
        team = teams_collection.find_one({"team_id": shift.get("team_id")}, {"_id": 0, "name": 1, "escalation_level": 1})
        if team:
            shift["team_name"] = team.get("name")
            shift["team_escalation_level"] = team.get("escalation_level")
        
        # Get users assigned to this shift
        user_shift_docs = list(user_shifts_collection.find({"shift_id": shift.get("shift_id")}, {"_id": 0}))
        user_ids = [us["user_id"] for us in user_shift_docs]
        
        shift["assigned_users_count"] = len(user_ids)
        
        if user_ids:
            users = list(users_collection.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1}
            ))
            shift["assigned_users"] = [serialize_doc(u) for u in users]
        else:
            shift["assigned_users"] = []
    
    return [serialize_doc(s) for s in shifts]

@app.get("/api/shifts/team/{team_id}")
async def get_team_shifts(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all shifts for a specific team"""
    shifts = list(shifts_collection.find({"team_id": team_id}, {"_id": 0}))
    
    # Enrich with assigned users
    for shift in shifts:
        user_shift_docs = list(user_shifts_collection.find({"shift_id": shift.get("shift_id")}, {"_id": 0}))
        user_ids = [us["user_id"] for us in user_shift_docs]
        
        if user_ids:
            users = list(users_collection.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1}
            ))
            shift["assigned_users"] = [serialize_doc(u) for u in users]
        else:
            shift["assigned_users"] = []
    
    return [serialize_doc(s) for s in shifts]

@app.put("/api/shifts/{shift_id}")
async def update_shift(
    shift_id: str,
    shift_data: ShiftUpdate,
    current_user: dict = Depends(require_lead_or_admin)  # Require lead or admin
):
    """Update a shift - requires lead or admin role"""
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if shift_data.name is not None:
        update_data["name"] = shift_data.name
    if shift_data.start_time is not None:
        update_data["start_time"] = shift_data.start_time
    if shift_data.end_time is not None:
        update_data["end_time"] = shift_data.end_time
    if shift_data.days_of_week is not None:
        update_data["days_of_week"] = shift_data.days_of_week
    if shift_data.is_active is not None:
        update_data["is_active"] = shift_data.is_active
    
    result = shifts_collection.update_one(
        {"shift_id": shift_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    shift = shifts_collection.find_one({"shift_id": shift_id}, {"_id": 0})
    return serialize_doc(shift)

@app.delete("/api/shifts/{shift_id}")
async def delete_shift(
    shift_id: str,
    current_user: dict = Depends(require_lead_or_admin)  # Require lead or admin
):
    """Delete a shift - requires lead or admin role"""
    result = shifts_collection.delete_one({"shift_id": shift_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    # Also remove user-shift assignments
    user_shifts_collection.delete_many({"shift_id": shift_id})
    
    return {"message": "Shift deleted successfully"}

# ==================== User Shift Assignments ====================

@app.post("/api/users/{user_id}/shifts")
async def assign_user_to_shift(
    user_id: str,
    assignment: UserShiftAssign,
    current_user: dict = Depends(get_current_user)
):
    """Assign a user to a shift"""
    # Verify user exists
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify shift exists
    shift = shifts_collection.find_one({"shift_id": assignment.shift_id})
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    # Check if assignment already exists
    existing = user_shifts_collection.find_one({
        "user_id": user_id,
        "shift_id": assignment.shift_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="User already assigned to this shift")
    
    user_shift_id = f"us_{uuid.uuid4().hex[:12]}"
    
    user_shift_doc = {
        "user_shift_id": user_shift_id,
        "user_id": user_id,
        "team_id": shift.get("team_id"),
        "shift_id": assignment.shift_id,
        "is_primary": assignment.is_primary,
        "effective_from": assignment.effective_from or datetime.now(timezone.utc).isoformat(),
        "effective_to": None,
        "created_at": datetime.now(timezone.utc)
    }
    
    user_shifts_collection.insert_one(user_shift_doc)
    return serialize_doc(user_shift_doc)

@app.get("/api/users/{user_id}/shifts")
async def get_user_shifts(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all shifts assigned to a user"""
    user_shift_docs = list(user_shifts_collection.find({"user_id": user_id}, {"_id": 0}))
    
    # Enrich with shift details
    for us_doc in user_shift_docs:
        shift = shifts_collection.find_one({"shift_id": us_doc.get("shift_id")}, {"_id": 0})
        if shift:
            us_doc["shift_details"] = serialize_doc(shift)
            # Get team name
            team = teams_collection.find_one({"team_id": shift.get("team_id")}, {"_id": 0, "name": 1})
            if team:
                us_doc["team_name"] = team.get("name")
    
    return [serialize_doc(us) for us in user_shift_docs]

@app.delete("/api/users/{user_id}/shifts/{shift_id}")
async def remove_user_from_shift(
    user_id: str,
    shift_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a user from a shift"""
    result = user_shifts_collection.delete_one({
        "user_id": user_id,
        "shift_id": shift_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User shift assignment not found")
    
    return {"message": "User removed from shift successfully"}

# ==================== On-Shift Queries ====================

@app.get("/api/teams/{team_id}/on-shift")
async def get_team_on_shift_members(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all team members currently on shift"""
    team = teams_collection.find_one({"team_id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    on_shift = get_on_shift_members(team_id)
    
    # Get current IST time for reference
    ist_now = get_ist_now()
    
    return {
        "team_id": team_id,
        "team_name": team.get("name"),
        "current_time_ist": ist_now.strftime("%Y-%m-%d %H:%M:%S"),
        "on_shift_count": len(on_shift),
        "on_shift_members": on_shift
    }

@app.get("/api/teams/{team_id}/schedule")
async def get_team_schedule(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get complete team schedule overview"""
    team = teams_collection.find_one({"team_id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    shifts = list(shifts_collection.find({"team_id": team_id, "is_active": True}, {"_id": 0}))
    
    schedule = []
    for shift in shifts:
        shift_data = serialize_doc(shift)
        
        # Get users assigned to this shift
        user_shift_docs = list(user_shifts_collection.find({"shift_id": shift.get("shift_id")}, {"_id": 0}))
        user_ids = [us["user_id"] for us in user_shift_docs]
        
        if user_ids:
            users = list(users_collection.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1}
            ))
            shift_data["members"] = [serialize_doc(u) for u in users]
        else:
            shift_data["members"] = []
        
        schedule.append(shift_data)
    
    # Get current IST time
    ist_now = get_ist_now()
    
    return {
        "team_id": team_id,
        "team_name": team.get("name"),
        "escalation_level": team.get("escalation_level"),
        "current_time_ist": ist_now.strftime("%Y-%m-%d %H:%M:%S"),
        "current_day": ist_now.strftime("%A"),
        "total_members": len(team.get("members", [])),
        "on_shift_now": len(get_on_shift_members(team_id)),
        "shifts": schedule
    }

# ==================== Ticket Escalation ====================

@app.put("/api/tickets/{ticket_id}/escalate")
async def escalate_ticket(
    ticket_id: str,
    escalation: TicketEscalate,
    current_user: dict = Depends(get_current_user)
):
    """Change ticket escalation level and auto-route to appropriate team"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    old_level = ticket.get("escalation_level", "L1")
    new_level = escalation.escalation_level
    
    if new_level not in ["L1", "L2", "L3"]:
        raise HTTPException(status_code=400, detail="Invalid escalation level. Must be L1, L2, or L3")
    
    # Record escalation in history
    escalation_record = {
        "from_level": old_level,
        "to_level": new_level,
        "reason": escalation.reason,
        "escalated_by": current_user["user_id"],
        "escalated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Auto-assign based on new escalation level
    assignment_result = auto_assign_on_escalation(ticket_id, new_level)
    
    # Update escalation history
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$push": {"escalation_history": escalation_record},
            "$set": {"escalated_at": datetime.now(timezone.utc)}
        }
    )
    
    # Get updated ticket
    updated_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    
    return {
        "ticket": serialize_doc(updated_ticket),
        "assignment": assignment_result,
        "escalation": escalation_record
    }

@app.get("/api/tickets/{ticket_id}/assignment-options")
async def get_ticket_assignment_options(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get assignment options for a ticket - team members and other teams"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    current_team_id = ticket.get("team_id")
    
    # Get current team members (if ticket is assigned to a team)
    team_members = []
    current_team = None
    if current_team_id:
        current_team = teams_collection.find_one({"team_id": current_team_id}, {"_id": 0})
        if current_team:
            for member_id in current_team.get("members", []):
                user = users_collection.find_one({"user_id": member_id}, {"_id": 0, "user_id": 1, "name": 1, "email": 1})
                if user:
                    user_data = serialize_doc(user)
                    user_data["is_on_shift"] = is_user_on_shift(member_id, current_team_id)
                    team_members.append(user_data)
    
    # Get other teams (grouped by escalation level)
    all_teams = list(teams_collection.find({}, {"_id": 0, "team_id": 1, "name": 1, "escalation_level": 1}))
    other_teams = []
    for team in all_teams:
        if team.get("team_id") != current_team_id:
            team_data = serialize_doc(team)
            team_data["on_shift_count"] = len(get_on_shift_members(team.get("team_id")))
            other_teams.append(team_data)
    
    # Sort other teams by escalation level
    other_teams.sort(key=lambda t: t.get("escalation_level", "L1"))
    
    return {
        "ticket_id": ticket_id,
        "current_team": serialize_doc(current_team) if current_team else None,
        "current_escalation_level": ticket.get("escalation_level", "L1"),
        "team_members": team_members,
        "other_teams": other_teams
    }

# ==================== Round Robin Assignment ====================

def get_available_agents(team_id: str) -> List[dict]:
    """Get available agents in a team for assignment"""
    team = teams_collection.find_one({"team_id": team_id})
    if not team or not team.get("members"):
        return []
    
    agents = list(users_collection.find({
        "user_id": {"$in": team["members"]},
        "status": {"$ne": "offline"},
        "on_leave": {"$ne": True}
    }))
    
    # Filter by capacity
    available = []
    for agent in agents:
        current_count = tickets_collection.count_documents({
            "assignee_id": agent["user_id"],
            "status": {"$nin": ["resolved", "closed"]}
        })
        max_tickets = agent.get("max_tickets", 10)
        if current_count < max_tickets:
            agent["current_ticket_count"] = current_count
            available.append(agent)
    
    return available

def round_robin_assign(team_id: str) -> Optional[str]:
    """Get next agent for round-robin assignment"""
    team = teams_collection.find_one({"team_id": team_id})
    if not team:
        return None
    
    available = get_available_agents(team_id)
    if not available:
        return None
    
    # Get last assigned index
    last_idx = team.get("last_assigned_idx", -1)
    
    # Find next available agent
    member_ids = [a["user_id"] for a in available]
    all_members = team.get("members", [])
    
    # Start from last_idx + 1 and wrap around
    for i in range(len(all_members)):
        idx = (last_idx + 1 + i) % len(all_members)
        member_id = all_members[idx]
        
        if member_id in member_ids:
            # Update last assigned index
            teams_collection.update_one(
                {"team_id": team_id},
                {"$set": {"last_assigned_idx": idx}}
            )
            return member_id
    
    return None

@app.post("/api/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: str,
    assignment: TicketAssign,
    current_user: dict = Depends(get_current_user)
):
    """Assign a ticket to a user or team"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    # If team specified, use round-robin
    if assignment.team_id:
        update_data["team_id"] = assignment.team_id
        
        if not assignment.assignee_id:
            # Auto-assign via round-robin
            assignee = round_robin_assign(assignment.team_id)
            if assignee:
                update_data["assignee_id"] = assignee
    
    # If specific assignee provided
    if assignment.assignee_id:
        update_data["assignee_id"] = assignment.assignee_id
        
        # Update assignee's ticket count
        users_collection.update_one(
            {"user_id": assignment.assignee_id},
            {"$inc": {"current_ticket_count": 1}}
        )
    
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": update_data}
    )
    
    # Log assignment in messages
    messages_collection.insert_one({
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "type": "system",
        "content": f"Ticket assigned to {update_data.get('assignee_id', 'team')}",
        "author_id": current_user["user_id"],
        "created_at": datetime.now(timezone.utc)
    })
    
    updated = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    return serialize_doc(updated)

@app.post("/api/routing/auto-assign")
async def auto_assign_ticket(
    ticket_id: str,
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Auto-assign a ticket using round-robin"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    assignee = round_robin_assign(team_id)
    if not assignee:
        raise HTTPException(status_code=400, detail="No available agents in team")
    
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {
            "assignee_id": assignee,
            "team_id": team_id,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return {"ticket_id": ticket_id, "assignee_id": assignee, "team_id": team_id}

# ==================== Team Inbox ====================

@app.get("/api/teams/{team_id}/tickets")
async def get_team_tickets(
    team_id: str,
    status: Optional[str] = None,
    unassigned_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get tickets for a team (team inbox)"""
    team = teams_collection.find_one({"team_id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    query = {"team_id": team_id}
    
    if status:
        query["status"] = status
    
    if unassigned_only:
        query["assignee_id"] = None
    
    tickets = list(tickets_collection.find(
        query,
        {"_id": 0}
    ).sort("created_at", DESCENDING).skip(skip).limit(limit))
    
    total = tickets_collection.count_documents(query)
    
    return {
        "tickets": [serialize_doc(t) for t in tickets],
        "total": total,
        "team_id": team_id,
        "team_name": team["name"]
    }

# ==================== Internal Notes ====================

@app.post("/api/tickets/{ticket_id}/notes")
async def add_internal_note(
    ticket_id: str,
    note: InternalNoteCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Add an internal note to a ticket"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Prevent duplicate submissions (same content within 5 seconds)
    five_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=5)
    existing_duplicate = messages_collection.find_one({
        "ticket_id": ticket_id,
        "author_id": current_user["user_id"],
        "content": note.content,
        "created_at": {"$gte": five_seconds_ago}
    })
    if existing_duplicate:
        # Return the existing note instead of creating a duplicate
        logger.info(f"[NOTES] Prevented duplicate note submission for ticket {ticket_id}")
        return serialize_doc(existing_duplicate)
    
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    mentions = note.mentions or []
    
    note_doc = {
        "message_id": message_id,
        "ticket_id": ticket_id,
        "type": note.type or "internal_note",
        "content": note.content,
        "author_id": current_user["user_id"],
        "author_name": current_user.get("name", "Unknown"),
        "author_email": current_user.get("email"),
        "mentions": mentions,
        "created_at": datetime.now(timezone.utc)
    }
    
    messages_collection.insert_one(note_doc)
    
    # Update ticket's updated_at and add mentioned users to ticket
    update_fields = {"updated_at": datetime.now(timezone.utc)}
    
    # Add mentioned users to ticket's mentioned_users array (for dashboard filtering)
    if mentions:
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {
                "$set": update_fields,
                "$addToSet": {"mentioned_users": {"$each": mentions}}
            }
        )
        
        # Broadcast mention notifications to mentioned users
        for mentioned_user_id in mentions:
            if mentioned_user_id != current_user["user_id"]:
                background_tasks.add_task(
                    broadcast_mention_notification,
                    mentioned_user_id,
                    ticket_id,
                    ticket.get("title", ""),
                    current_user.get("name", "Unknown"),
                    note.content[:100]
                )
    else:
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": update_fields}
        )
    
    # Trigger webhook for note added
    asyncio.create_task(trigger_webhooks("ticket.note_added", {
        "ticket_id": ticket_id,
        "ticket_title": ticket.get("title", ""),
        "note": serialize_doc(note_doc),
        "added_by": current_user.get("name", current_user["user_id"])
    }))
    
    return serialize_doc(note_doc)

@app.get("/api/tickets/{ticket_id}/notes")
async def get_ticket_notes(
    ticket_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get all notes, replies, and merged messages for a ticket"""
    query = {
        "ticket_id": ticket_id, 
        "type": {"$in": ["internal_note", "reply", "merge_divider", "system", "customer_reply"]}
    }
    
    total = messages_collection.count_documents(query)
    skip = (page - 1) * limit
    
    notes = list(messages_collection.find(query, {"_id": 0})
        .sort("created_at", ASCENDING)
        .skip(skip)
        .limit(limit))
    
    return {
        "messages": [serialize_doc(n) for n in notes],
        "total": total,
        "page": page,
        "has_more": skip + limit < total
    }

@app.get("/api/tickets/{ticket_id}/activity")
async def get_ticket_activity(
    ticket_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get all activity (notes, replies, system messages) for a ticket - for conversation view"""
    query = {"ticket_id": ticket_id}
    
    total = messages_collection.count_documents(query)
    skip = (page - 1) * limit
    
    messages = list(messages_collection.find(query, {"_id": 0})
        .sort("created_at", ASCENDING)
        .skip(skip)
        .limit(limit))
    
    return {
        "messages": [serialize_doc(m) for m in messages],
        "total": total,
        "page": page,
        "has_more": skip + limit < total
    }


@app.get("/api/tickets/{ticket_id}/activity-feed")
async def get_ticket_activity_feed(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive activity feed combining changelog and events for Activity tab"""
    
    # Get the main ticket
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    activities = []
    
    # 1. Add ticket creation event
    activities.append({
        "type": "created",
        "field": "ticket",
        "description": "Ticket created",
        "timestamp": ticket.get("created_at"),
        "user_id": ticket.get("created_by"),
        "icon": "plus"
    })
    
    # 2. Get changelog entries for this ticket
    changelog = list(ticket_changelog_collection.find(
        {"ticket_id": ticket_id},
        {"_id": 0}
    ))
    
    # Also get changelog for any merged tickets
    merged_tickets = ticket.get("merged_tickets", [])
    merged_ticket_ids = [m.get("ticket_id") for m in merged_tickets if m.get("ticket_id")]
    
    if merged_ticket_ids:
        merged_changelog = list(ticket_changelog_collection.find(
            {"ticket_id": {"$in": merged_ticket_ids}},
            {"_id": 0}
        ))
        changelog.extend(merged_changelog)
    
    # Map changelog to activity format
    field_icons = {
        "status": "activity",
        "assignee_id": "user",
        "priority": "alert-triangle",
        "team_id": "users",
        "tags": "tag",
        "merge": "git-merge",
        "unmerge": "git-branch",
        "split": "scissors",
        "is_starred": "star",
        "custom_fields": "file-text"
    }
    
    field_labels = {
        "status": "Status changed",
        "assignee_id": "Assigned",
        "priority": "Priority changed",
        "team_id": "Team changed",
        "tags": "Tags updated",
        "merge": "Ticket merged",
        "unmerge": "Ticket unmerged",
        "split": "Ticket split",
        "is_starred": "Starred",
        "custom_fields": "Custom field updated"
    }
    
    for entry in changelog:
        field = entry.get("field", "")
        old_val = entry.get("old_value")
        new_val = entry.get("new_value")
        
        # Format description based on field type
        if field == "assignee_id":
            # Get assignee name if possible
            assignee_name = None
            if new_val:
                assignee = users_collection.find_one({"user_id": new_val})
                assignee_name = assignee.get("name") if assignee else new_val
            if old_val is None or old_val == "None":
                description = f"Assigned to {assignee_name or 'Unknown'}"
            else:
                old_assignee = users_collection.find_one({"user_id": old_val})
                old_name = old_assignee.get("name") if old_assignee else old_val
                description = f"Reassigned from {old_name} to {assignee_name or 'Unknown'}"
        elif field == "status":
            description = f"Status: {old_val or 'none'} → {new_val}"
        elif field == "priority":
            description = f"Priority: {old_val} → {new_val}"
        elif field == "merge":
            description = f"Merged ticket {entry.get('metadata', {}).get('source_ticket_id', new_val)}"
        elif field == "unmerge":
            description = f"Unmerged ticket {new_val}"
        elif field == "is_starred":
            description = "Starred" if new_val else "Unstarred"
        else:
            description = f"{field_labels.get(field, field)}: {old_val} → {new_val}"
        
        activities.append({
            "type": entry.get("change_type", "update"),
            "field": field,
            "description": description,
            "old_value": old_val,
            "new_value": new_val,
            "timestamp": entry.get("changed_at"),
            "user_id": entry.get("changed_by"),
            "user_name": entry.get("changed_by_name"),
            "icon": field_icons.get(field, "edit"),
            "source_ticket_id": entry.get("ticket_id") if entry.get("ticket_id") != ticket_id else None,
            "metadata": entry.get("metadata")
        })
    
    # 3. Add merge events from messages (merge_divider type)
    merge_messages = list(messages_collection.find(
        {"ticket_id": ticket_id, "type": "merge_divider"},
        {"_id": 0}
    ))
    
    for msg in merge_messages:
        # Only add if not already in changelog
        source_id = msg.get("original_ticket_id")
        if source_id:
            # Check if this merge is already recorded in activities
            already_recorded = any(
                a.get("field") == "merge" and 
                (a.get("metadata") or {}).get("source_ticket_id") == source_id 
                for a in activities
            )
            if not already_recorded:
                activities.append({
                    "type": "merge",
                    "field": "merge",
                    "description": f"Merged ticket {source_id}: {msg.get('merged_ticket_title', '')}",
                    "timestamp": msg.get("created_at"),
                    "user_id": msg.get("created_by"),
                    "icon": "git-merge",
                    "source_ticket_id": source_id
                })
    
    # Resolve user names for activities without them
    user_ids = list(set(a.get("user_id") for a in activities if a.get("user_id") and not a.get("user_name")))
    if user_ids:
        users = {u["user_id"]: u.get("name", u["user_id"]) for u in users_collection.find({"user_id": {"$in": user_ids}})}
        for activity in activities:
            if activity.get("user_id") and not activity.get("user_name"):
                activity["user_name"] = users.get(activity["user_id"], activity["user_id"])
    
    # Sort by timestamp
    activities.sort(key=lambda x: x.get("timestamp") or datetime.min.replace(tzinfo=timezone.utc))
    
    return [serialize_doc(a) for a in activities]

# ==================== Tag Management ====================

@app.post("/api/tickets/{ticket_id}/tags")
async def add_tags(
    ticket_id: str,
    tags: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Add tags to a ticket"""
    result = tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$addToSet": {"tags": {"$each": tags}},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    return {"tags": ticket.get("tags", [])}

@app.delete("/api/tickets/{ticket_id}/tags/{tag}")
async def remove_tag(
    ticket_id: str,
    tag: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a tag from a ticket"""
    result = tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$pull": {"tags": tag},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    return {"tags": ticket.get("tags", [])}

# Ticket endpoints (protected)
@app.get("/api/tickets/starred")
async def get_starred_tickets(
    current_user: dict = Depends(get_current_user)
):
    """Get all starred tickets for display, regardless of status"""
    query = {"is_starred": True}
    tickets = list(tickets_collection.find(query).sort("updated_at", DESCENDING))
    return [serialize_doc(ticket) for ticket in tickets]


@app.get("/api/tickets/escalation-counts")
async def get_escalation_counts(
    current_user: dict = Depends(get_current_user)
):
    """Get ticket counts grouped by escalation level and status"""
    pipeline = [
        {"$match": {"status": {"$nin": ["merged", "resolved", "closed"]}}},
        {"$group": {
            "_id": {
                "escalation_level": {"$ifNull": ["$escalation_level", "L1"]},
                "status": "$status"
            },
            "count": {"$sum": 1}
        }}
    ]
    results = list(tickets_collection.aggregate(pipeline))
    
    counts = {"L1": {"total": 0}, "L2": {"total": 0}, "L3": {"total": 0}}
    for r in results:
        level = r["_id"]["escalation_level"]
        status = r["_id"]["status"]
        count = r["count"]
        if level not in counts:
            counts[level] = {"total": 0}
        counts[level][status] = count
        counts[level]["total"] += count
    
    return counts



@app.get("/api/tickets")
async def get_tickets(
    request: Request,
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    mentioned_user_id: Optional[str] = None,
    is_starred: Optional[bool] = None,
    include_merged: Optional[bool] = False,
    escalation_level: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: dict = Depends(get_current_user)
):
    query = {}
    
    # Support multiple status values via repeated query params
    status_values = request.query_params.getlist("status")
    if status_values:
        if len(status_values) == 1:
            query["status"] = status_values[0]
        else:
            query["status"] = {"$in": status_values}
    elif not include_merged:
        query["status"] = {"$ne": "merged"}
    
    if assignee_id:
        query["assignee_id"] = assignee_id
    if mentioned_user_id:
        query["mentioned_users"] = mentioned_user_id
    if is_starred is not None:
        query["is_starred"] = is_starred
    if escalation_level:
        query["escalation_level"] = escalation_level
    
    total = tickets_collection.count_documents(query)
    
    sort_dir = DESCENDING if sort_order == "desc" else ASCENDING
    skip = (page - 1) * limit
    
    tickets = list(
        tickets_collection.find(query)
        .sort(sort_by, sort_dir)
        .skip(skip)
        .limit(limit)
    )
    
    return {
        "tickets": [serialize_doc(ticket) for ticket in tickets],
        "total": total,
        "page": page,
        "limit": limit,
        "has_more": skip + limit < total
    }

@app.post("/api/tickets")
async def create_ticket(
    ticket_data: TicketCreate,
    current_user: dict = Depends(get_current_user)
):
    max_order_ticket = tickets_collection.find_one(
        {"status": ticket_data.status},
        sort=[("order", DESCENDING)]
    )
    next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
    
    # Generate sequential ticket ID and UUID
    ticket_id = generate_ticket_id()
    ticket_uuid = str(uuid4())
    
    # Extract domain from customer email if provided
    domain = extract_domain(ticket_data.customer_email) if ticket_data.customer_email else None
    
    # Auto-create or link customer
    customer_id = None
    if ticket_data.customer_email:
        customer = get_or_create_customer(ticket_data.customer_email)
        if customer:
            customer_id = customer.get("customer_id")
    
    now = datetime.now(timezone.utc)
    
    # Auto-assign to creator if no assignee specified
    assignee_id = ticket_data.assignee_id if ticket_data.assignee_id else current_user["user_id"]
    
    ticket_doc = {
        "ticket_id": ticket_id,
        "uuid": ticket_uuid,
        "title": ticket_data.title,
        "description": ticket_data.description,
        "status": ticket_data.status,
        "assignee_id": assignee_id,
        "priority": ticket_data.priority,
        "escalation_level": ticket_data.escalation_level or "L1",
        "order": next_order,
        "created_by": current_user["user_id"],
        "created_at": now,
        "updated_at": now,
        # New fields
        "source": ticket_data.source or "manual",
        "tags": ticket_data.tags or [],
        "customer_email": ticket_data.customer_email,
        "customer_id": customer_id,  # Link to customer entity
        "domain": domain,
        "is_starred": False,
        "snoozed": False
    }
    
    tickets_collection.insert_one(ticket_doc)
    
    # Log ticket creation in changelog
    log_ticket_change(
        ticket_id=ticket_id,
        uuid=ticket_uuid,
        field="ticket",
        old_value=None,
        new_value=ticket_doc.get("title"),
        changed_by=current_user["user_id"],
        change_type="create"
    )
    
    # Run routing rules on newly created ticket
    routing_result = run_routing_rules(ticket_doc)
    
    # Get the potentially updated ticket
    final_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    
    result = serialize_doc(final_ticket)
    result["routing_applied"] = routing_result.get("matched", False)
    result["routing_rule"] = routing_result.get("rule_name")
    
    # Broadcast real-time event
    asyncio.create_task(broadcast_ticket_created(
        result,
        {"user_id": current_user["user_id"], "name": current_user.get("name", "Unknown")}
    ))
    
    # Trigger webhooks for ticket.created
    asyncio.create_task(trigger_webhooks("ticket.created", result))
    
    return result

@app.get("/api/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return serialize_doc(ticket)

@app.put("/api/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    ticket_data: TicketUpdate,
    current_user: dict = Depends(get_current_user)
):
    # Get current ticket state for changelog
    current_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not current_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    update_data = {k: v for k, v in ticket_data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    # Set resolved_at timestamp when ticket is marked as resolved
    if "status" in update_data and update_data["status"] == "resolved":
        if current_ticket.get("status") != "resolved":
            update_data["resolved_at"] = datetime.now(timezone.utc)
    
    # Set closed_at timestamp when ticket is marked as closed
    if "status" in update_data and update_data["status"] == "closed":
        if current_ticket.get("status") != "closed":
            update_data["closed_at"] = datetime.now(timezone.utc)
    
    # Check for auto-reassignment on ticket reopen
    reassignment_info = None
    if "status" in update_data:
        reassignment_info = handle_ticket_reopen_reassignment(
            current_ticket, 
            update_data["status"],
            current_user["user_id"]
        )
        
        if reassignment_info and reassignment_info.get("reassigned"):
            # Apply reassignment to update_data
            update_data["assignee_id"] = reassignment_info.get("new_assignee_id")
            if reassignment_info.get("new_assignee_id") is None:
                # Unassign - also update status to queued
                update_data["status"] = "queued"
    
    # Build changelog entries for changed fields
    changes = {}
    for field, new_value in update_data.items():
        if field != "updated_at":
            old_value = current_ticket.get(field)
            if old_value != new_value:
                changes[field] = (old_value, new_value)
    
    result = tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Log changes to changelog
    if changes:
        log_ticket_changes_batch(
            ticket_id=ticket_id,
            uuid=current_ticket.get("uuid", ""),
            changes=changes,
            changed_by=current_user["user_id"],
            change_type="update"
        )
        
        # Create system messages for important changes (assignment, status)
        # These appear in the conversation timeline
        for field, (old_val, new_val) in changes.items():
            if field == "assignee_id":
                # Get assignee name
                assignee_name = "Unassigned"
                if new_val:
                    assignee = users_collection.find_one({"user_id": new_val})
                    assignee_name = assignee.get("name", new_val) if assignee else new_val
                messages_collection.insert_one({
                    "message_id": f"msg_{uuid4().hex[:12]}",
                    "ticket_id": ticket_id,
                    "type": "system",
                    "text": f"Assigned to {assignee_name}",
                    "created_by": current_user["user_id"],
                    "created_at": datetime.now(timezone.utc)
                })
            elif field == "status":
                status_label = new_val.replace("_", " ").title()
                messages_collection.insert_one({
                    "message_id": f"msg_{uuid4().hex[:12]}",
                    "ticket_id": ticket_id,
                    "type": "system",
                    "text": f"Status changed to {status_label}",
                    "created_by": current_user["user_id"],
                    "created_at": datetime.now(timezone.utc)
                })
            elif field == "priority":
                messages_collection.insert_one({
                    "message_id": f"msg_{uuid4().hex[:12]}",
                    "ticket_id": ticket_id,
                    "type": "system",
                    "text": f"Priority set to {new_val.title()}",
                    "created_by": current_user["user_id"],
                    "created_at": datetime.now(timezone.utc)
                })
    
    # Log auto-reassignment to changelog if it occurred
    if reassignment_info and reassignment_info.get("reassigned"):
        reason_text = "Original assignee not on shift" if reassignment_info.get("reason") == "original_assignee_off_shift" else "No agents on shift - ticket unassigned"
        log_ticket_change(
            ticket_id=ticket_id,
            uuid=current_ticket.get("uuid", ""),
            field="auto_reassignment",
            old_value=reassignment_info.get("old_assignee_name"),
            new_value=reassignment_info.get("new_assignee_name") or "Unassigned",
            changed_by="system",
            change_type="auto_reassign",
            metadata={"reason": reason_text}
        )
    
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    serialized = serialize_doc(ticket)
    
    # Add reassignment info to response if it occurred
    if reassignment_info:
        serialized["_reassignment_info"] = reassignment_info
    
    # Broadcast real-time event
    asyncio.create_task(broadcast_ticket_update(
        ticket_id, 
        'updated', 
        serialized,
        {"user_id": current_user["user_id"], "name": current_user.get("name", "Unknown")}
    ))
    
    # Trigger webhooks based on what changed
    asyncio.create_task(trigger_webhooks("ticket.updated", serialized))
    
    if changes:
        for field, (old_val, new_val) in changes.items():
            if field == "status":
                asyncio.create_task(trigger_webhooks("ticket.status_changed", {
                    **serialized,
                    "previous_status": old_val,
                    "new_status": new_val
                }))
                # Check for resolved/closed specifically
                if new_val == "resolved":
                    asyncio.create_task(trigger_webhooks("ticket.resolved", serialized))
                elif new_val == "closed":
                    asyncio.create_task(trigger_webhooks("ticket.closed", serialized))
            elif field == "assignee_id":
                asyncio.create_task(trigger_webhooks("ticket.assigned", {
                    **serialized,
                    "previous_assignee_id": old_val,
                    "new_assignee_id": new_val
                }))
    
    return serialized

@app.delete("/api/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Get ticket before deletion for changelog
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Log deletion
    log_ticket_change(
        ticket_id=ticket_id,
        uuid=ticket.get("uuid", ""),
        field="ticket",
        old_value=ticket.get("title"),
        new_value=None,
        changed_by=current_user["user_id"],
        change_type="delete"
    )
    
    result = tickets_collection.delete_one({"ticket_id": ticket_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Broadcast real-time event
    asyncio.create_task(broadcast_ticket_deleted(
        ticket_id,
        {"user_id": current_user["user_id"], "name": current_user.get("name", "Unknown")}
    ))
    
    # Trigger webhook for ticket.deleted
    asyncio.create_task(trigger_webhooks("ticket.deleted", serialize_doc(ticket)))
    
    return {"message": "Ticket deleted successfully"}

@app.get("/api/tickets/{ticket_id}/changelog")
async def get_ticket_changelog(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the full changelog/audit log for a ticket"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get all changelog entries for this ticket
    changelog = list(ticket_changelog_collection.find(
        {"ticket_id": ticket_id},
        {"_id": 0}
    ).sort("changed_at", DESCENDING))
    
    # Enrich with user names
    user_ids = list(set(entry.get("changed_by") for entry in changelog if entry.get("changed_by")))
    users = {u["user_id"]: u.get("name", "Unknown") for u in users_collection.find({"user_id": {"$in": user_ids}}, {"user_id": 1, "name": 1})}
    
    for entry in changelog:
        entry["changed_by_name"] = users.get(entry.get("changed_by"), "Unknown")
        if isinstance(entry.get("changed_at"), datetime):
            entry["changed_at"] = entry["changed_at"].isoformat()
    
    return changelog

@app.get("/api/tickets/{ticket_id}/metadata")
async def get_ticket_metadata(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive ticket metadata including timestamps and all fields"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get changelog summary
    changelog_count = ticket_changelog_collection.count_documents({"ticket_id": ticket_id})
    last_change = ticket_changelog_collection.find_one(
        {"ticket_id": ticket_id},
        {"_id": 0},
        sort=[("changed_at", DESCENDING)]
    )
    
    # Get notes/messages count
    notes_count = messages_collection.count_documents({"ticket_id": ticket_id})
    
    metadata = {
        "ticket_id": ticket.get("ticket_id"),
        "uuid": ticket.get("uuid"),
        "title": ticket.get("title"),
        "status": ticket.get("status"),
        "priority": ticket.get("priority"),
        "escalation_level": ticket.get("escalation_level"),
        "tags": ticket.get("tags", []),
        "source": ticket.get("source"),
        "customer_email": ticket.get("customer_email"),
        "domain": ticket.get("domain"),
        "assignee_id": ticket.get("assignee_id"),
        "team_id": ticket.get("team_id"),
        "is_starred": ticket.get("is_starred", False),
        "snoozed": ticket.get("snoozed", False),
        "custom_fields": ticket.get("custom_fields", {}),
        "timestamps": {
            "created_at": ticket.get("created_at").isoformat() if isinstance(ticket.get("created_at"), datetime) else ticket.get("created_at"),
            "updated_at": ticket.get("updated_at").isoformat() if isinstance(ticket.get("updated_at"), datetime) else ticket.get("updated_at"),
            "last_change": last_change.get("changed_at").isoformat() if last_change and isinstance(last_change.get("changed_at"), datetime) else None
        },
        "stats": {
            "changelog_entries": changelog_count,
            "notes_count": notes_count
        },
        "created_by": ticket.get("created_by")
    }
    
    return metadata

@app.post("/api/tickets/reorder")
async def reorder_tickets(
    reorder_data: TicketReorder,
    current_user: dict = Depends(get_current_user)
):
    ticket = tickets_collection.find_one({"ticket_id": reorder_data.ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    new_status = reorder_data.new_status
    
    tickets_collection.update_one(
        {"ticket_id": reorder_data.ticket_id},
        {"$set": {"status": new_status, "order": reorder_data.new_order, "updated_at": datetime.utcnow()}}
    )
    
    tickets_in_new_status = list(tickets_collection.find(
        {"status": new_status, "ticket_id": {"$ne": reorder_data.ticket_id}}
    ).sort("order", ASCENDING))
    
    for idx, t in enumerate(tickets_in_new_status):
        new_order = idx if idx < reorder_data.new_order else idx + 1
        tickets_collection.update_one(
            {"ticket_id": t["ticket_id"]},
            {"$set": {"order": new_order}}
        )
    
    return {"message": "Tickets reordered successfully"}

# Analytics endpoint
@app.get("/api/analytics/summary")
async def get_analytics_summary(current_user: dict = Depends(get_current_user)):
    pipeline = [
        {"$facet": {
            "by_status": [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ],
            "by_assignee": [
                {"$match": {"assignee_id": {"$ne": None}}},
                {"$group": {"_id": "$assignee_id", "count": {"$sum": 1}}}
            ],
            "my_tickets": [
                {"$match": {"assignee_id": current_user["user_id"]}},
                {"$count": "count"}
            ],
            "total": [
                {"$count": "count"}
            ]
        }}
    ]
    result = list(tickets_collection.aggregate(pipeline))
    facets = result[0] if result else {}
    
    status_counts = {s: 0 for s in ["todo", "in_progress", "waiting", "review", "resolved"]}
    for item in facets.get("by_status", []):
        if item["_id"] in status_counts:
            status_counts[item["_id"]] = item["count"]
    
    my_count = facets.get("my_tickets", [{}])
    my_tickets_count = my_count[0].get("count", 0) if my_count else 0
    
    total_list = facets.get("total", [{}])
    total = total_list[0].get("count", 0) if total_list else 0
    
    return {
        "by_status": status_counts,
        "by_assignee": [{"assignee_id": item["_id"], "count": item["count"]} for item in facets.get("by_assignee", [])],
        "my_tickets": my_tickets_count,
        "total": total
    }

# Export endpoint
@app.get("/api/export")
async def export_tickets(
    format: str = "json",
    current_user: dict = Depends(get_current_user)
):
    from starlette.responses import StreamingResponse
    
    fieldnames = ["ticket_id", "title", "description", "status", "assignee_id", "priority", "order", "created_at", "updated_at"]
    
    if format == "csv":
        def csv_generator():
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            yield output.getvalue()
            
            for ticket in tickets_collection.find({}, {"_id": 0}).batch_size(500):
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
                writer.writerow(serialize_doc(ticket))
                yield output.getvalue()
        
        return StreamingResponse(
            csv_generator(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=tickets.csv"}
        )
    else:
        def json_generator():
            yield "[\n"
            first = True
            for ticket in tickets_collection.find({}, {"_id": 0}).batch_size(500):
                if not first:
                    yield ",\n"
                first = False
                yield json.dumps(serialize_doc(ticket))
            yield "\n]"
        
        return StreamingResponse(
            json_generator(),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=tickets.json"}
        )

# IMAP Email Sync endpoint
@app.post("/api/email/sync")
async def trigger_email_sync(
    fetch_all: bool = Query(False, description="If true, resets UID state and re-fetches all emails"),
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger IMAP email sync using UID-based tracking."""
    from imap_sync import get_imap_config, fetch_emails_by_uid
    
    config = get_imap_config()
    if not config["email"] or not config["password"]:
        raise HTTPException(status_code=400, detail="IMAP not configured")
    
    imap_sync_state = db.imap_sync_state
    
    # Determine starting UID
    if fetch_all:
        last_uid = 0
    else:
        state = imap_sync_state.find_one({"_id": "imap_last_uid"})
        last_uid = state["last_uid"] if state else 0
    
    loop = asyncio.get_event_loop()
    new_emails, new_max_uid = await loop.run_in_executor(
        None, lambda: fetch_emails_by_uid(config, last_uid=last_uid)
    )
    
    created_count = 0
    reply_count = 0
    skipped_count = 0
    
    for eml in new_emails:
        # Dedup
        if eml["message_id"]:
            existing = tickets_collection.find_one({"email_rfc_message_id": eml["message_id"]})
            if existing:
                skipped_count += 1
                continue
            existing_reply = email_replies_collection.find_one({"email_rfc_message_id": eml["message_id"]})
            if existing_reply:
                skipped_count += 1
                continue
        
        # Threading
        existing_thread_ticket = None
        if eml["in_reply_to"]:
            existing_thread_ticket = tickets_collection.find_one({
                "$or": [
                    {"email_rfc_message_id": eml["in_reply_to"]},
                    {"last_reply_message_id": eml["in_reply_to"]},
                    {"email_thread_message_ids": eml["in_reply_to"]}
                ]
            })
        
        if not existing_thread_ticket and eml["references"]:
            for ref in eml["references"].split():
                ref = ref.strip()
                if not ref:
                    continue
                existing_thread_ticket = tickets_collection.find_one({
                    "$or": [
                        {"email_rfc_message_id": ref},
                        {"last_reply_message_id": ref},
                        {"email_thread_message_ids": ref}
                    ]
                })
                if existing_thread_ticket:
                    break
        
        if existing_thread_ticket:
            sanitized_html_content = sanitize_html(eml["html"][:100000]) if eml["html"] else None
            reply_id = f"reply_{uuid.uuid4().hex[:12]}"
            email_replies_collection.insert_one({
                "reply_id": reply_id,
                "ticket_id": existing_thread_ticket["ticket_id"],
                "direction": "incoming",
                "from_email": eml["sender_email"],
                "from_name": eml["sender_name"],
                "to_email": eml["to"],
                "subject": eml["subject"] or "Re: " + existing_thread_ticket.get("title", ""),
                "body": (eml["text"] or "")[:50000],
                "body_html": sanitized_html_content,
                "email_rfc_message_id": eml["message_id"],
                "created_at": datetime.now(timezone.utc),
                "status": "received"
            })
            messages_collection.insert_one({
                "message_id": f"msg_{uuid.uuid4().hex[:12]}",
                "ticket_id": existing_thread_ticket["ticket_id"],
                "type": "customer_reply",
                "content": (eml["text"] or "")[:50000],
                "content_html": sanitized_html_content,
                "author_id": None,
                "author_name": eml["sender_name"],
                "author_email": eml["sender_email"],
                "email_reply_id": reply_id,
                "created_at": datetime.now(timezone.utc)
            })
            tickets_collection.update_one(
                {"ticket_id": existing_thread_ticket["ticket_id"]},
                {
                    "$set": {"status": "todo", "updated_at": datetime.now(timezone.utc), "last_reply_message_id": eml["message_id"]},
                    "$push": {"email_thread_message_ids": eml["message_id"]}
                }
            )
            reply_count += 1
            continue
        
        # New ticket
        ticket_id = generate_ticket_id()
        sanitized_html_content = sanitize_html(eml["html"][:100000]) if eml["html"] else None
        tickets_collection.insert_one({
            "ticket_id": ticket_id,
            "uuid": str(uuid.uuid4()),
            "title": (eml["subject"] or "No Subject")[:200],
            "description": (eml["text"] or "")[:5000],
            "status": "todo",
            "priority": "medium",
            "source": "email",
            "email_rfc_message_id": eml["message_id"],
            "email_references": eml["references"],
            "email_in_reply_to": eml["in_reply_to"],
            "email_sender": eml["from_header"],
            "email_sender_name": eml["sender_name"],
            "customer_email": eml["sender_email"],
            "email_to": eml["to"],
            "email_cc": eml["cc"],
            "email_date": eml["date"].isoformat() if eml["date"] else None,
            "email_html": sanitized_html_content,
            "email_text": (eml["text"] or "")[:50000],
            "email_preview": eml["preview"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "assignee_id": None,
            "escalation_level": "L1"
        })
        created_count += 1
    
    # Update UID state
    if new_max_uid > last_uid:
        imap_sync_state.update_one(
            {"_id": "imap_last_uid"},
            {"$set": {"last_uid": new_max_uid, "updated_at": datetime.now(timezone.utc)}},
            upsert=True
        )
    
    return {
        "status": "success",
        "emails_found": len(new_emails),
        "tickets_created": created_count,
        "replies_added": reply_count,
        "skipped_duplicates": skipped_count,
        "last_uid": new_max_uid
    }

@app.get("/api/email/status")
async def email_sync_status(current_user: dict = Depends(get_current_user)):
    """Check IMAP connection and sync status."""
    from imap_sync import get_imap_config
    import imaplib as imaplib_mod
    import socket as socket_mod
    
    config = get_imap_config()
    if not config["email"] or not config["password"]:
        return {"connected": False, "email": None, "error": "IMAP not configured"}
    
    # Get UID sync state
    imap_state = db.imap_sync_state.find_one({"_id": "imap_last_uid"})
    sync_info = {
        "last_uid": imap_state["last_uid"] if imap_state else 0,
        "last_synced": imap_state["updated_at"].isoformat() if imap_state and "updated_at" in imap_state else None,
        "seeded": imap_state.get("seeded", False) if imap_state else False
    }
    
    try:
        old_timeout = socket_mod.getdefaulttimeout()
        socket_mod.setdefaulttimeout(15)
        try:
            conn = imaplib_mod.IMAP4_SSL(config["server"], config["port"])
        finally:
            socket_mod.setdefaulttimeout(old_timeout)
        conn.socket().settimeout(15)
        conn.login(config["email"], config["password"])
        status, data = conn.select("INBOX", readonly=True)
        msg_count = int(data[0]) if status == "OK" else 0
        try:
            conn.socket().settimeout(0.5)
            conn.logout()
        except Exception:
            pass
        try:
            conn.socket().close()
        except Exception:
            pass
        return {"connected": True, "email": config["email"], "inbox_count": msg_count, "sync": sync_info, "mode": "idle"}
    except Exception as e:
        return {"connected": False, "email": config["email"], "error": str(e), "sync": sync_info, "mode": "idle"}

# Import endpoint
@app.post("/api/import")
async def import_tickets(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    content = await file.read()
    
    try:
        if file.filename.endswith(".json"):
            data = json.loads(content)
            if not isinstance(data, list):
                data = [data]
        elif file.filename.endswith(".csv"):
            csv_reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
            data = list(csv_reader)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use JSON or CSV.")
        
        imported_count = 0
        for item in data:
            ticket_id = generate_ticket_id()
            ticket_doc = {
                "ticket_id": ticket_id,
                "title": item.get("title", "Imported Ticket"),
                "description": item.get("description", ""),
                "status": item.get("status", "backlog"),
                "assignee_id": item.get("assignee_id"),
                "priority": item.get("priority", "medium"),
                "order": int(item.get("order", 0)),
                "created_by": current_user["user_id"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            tickets_collection.insert_one(ticket_doc)
            imported_count += 1
        
        return {
            "message": f"Successfully imported {imported_count} tickets",
            "count": imported_count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

# ==================== Atlas Import ====================

from atlas_import import run_atlas_import

@app.post("/api/import/atlas")
async def import_from_atlas(
    req: AtlasImportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Import conversations, messages, and tags from Atlas.

    Provide your Atlas API key and optionally filter by status/date range.
    The endpoint will:
    1. Fetch all tags from Atlas (for tag-ID → name resolution)
    2. Fetch conversations (paginated, with optional filters)
    3. For each conversation, fetch its messages
    4. Map Atlas data → Trinity schema and insert into the database
    5. Deduplicate by atlas_conversation_id (safe to re-run)

    Atlas field mapping:
    - status: OPEN→todo, CLOSED→resolved, SNOOZED→waiting
    - priority: NO_PRIORITY→medium, LOW→low, NORMAL→medium, HIGH→high, URGENT→urgent
    - messages side: AGENT→reply, CUSTOMER→customer_reply
    - All Atlas-specific fields (browser, OS, channel, statistics, CSAT, etc.) are preserved
    """
    db_collections = {
        "tickets": tickets_collection,
        "messages": messages_collection,
        "users": users_collection,
    }

    try:
        summary = await run_atlas_import(
            api_key=req.api_key,
            db_collections=db_collections,
            generate_ticket_id_fn=generate_ticket_id,
            get_or_create_customer_fn=get_or_create_customer,
            extract_domain_fn=extract_domain,
            importer_user_id=current_user["user_id"],
            status_filter=req.status,
            start_date=req.start_date,
            end_date=req.end_date,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid Atlas API key")
        if e.response.status_code == 403:
            raise HTTPException(status_code=403, detail="Atlas API key does not have sufficient permissions")
        raise HTTPException(
            status_code=502,
            detail=f"Atlas API error: HTTP {e.response.status_code} – {e.response.text[:200]}"
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Could not connect to Atlas API (api.atlas.so)")
    except Exception as e:
        logger.error(f"[ATLAS IMPORT] Unexpected error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    return {
        "success": True,
        "message": f"Imported {summary['conversations_imported']} conversations with {summary['messages_imported']} messages",
        "summary": summary,
    }

# ==================== File Upload ====================

# Configure upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed image types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@app.post("/api/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload an image file for use in replies"""
    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        file_ext = ".jpg"
    
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Generate URL
    image_url = f"/api/uploads/{unique_filename}"
    
    return {
        "success": True,
        "filename": unique_filename,
        "url": image_url,
        "size": len(content),
        "content_type": file.content_type
    }

@app.get("/api/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """Serve uploaded files"""
    # Sanitize filename to prevent directory traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine content type
    ext = os.path.splitext(safe_filename)[1].lower()
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }
    content_type = content_types.get(ext, "application/octet-stream")
    
    return FileResponse(file_path, media_type=content_type)

# ==================== Gmail Integration ====================

def get_gmail_flow():
    """Create Gmail OAuth flow"""
    client_config = {
        "web": {
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GMAIL_REDIRECT_URI]
        }
    }
    flow = Flow.from_client_config(client_config, scopes=GMAIL_SCOPES)
    flow.redirect_uri = GMAIL_REDIRECT_URI
    return flow

def get_gmail_service(credentials_dict: dict):
    """Build Gmail API service from stored credentials"""
    credentials = Credentials(
        token=credentials_dict.get("access_token"),
        refresh_token=credentials_dict.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET
    )
    return build('gmail', 'v1', credentials=credentials)

def parse_email_body(payload):
    """Extract text body from email payload"""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part.get('body', {}):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    break
            elif part['mimeType'] == 'text/html' and not body:
                if 'data' in part.get('body', {}):
                    html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    # Simple HTML to text conversion
                    body = re.sub(r'<[^>]+>', '', html_body)
                    body = unescape(body)
            elif 'parts' in part:
                body = parse_email_body(part)
                if body:
                    break
    elif 'body' in payload and 'data' in payload['body']:
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    
    return body.strip()

def extract_email_metadata(headers):
    """Extract From, Subject, Date from email headers"""
    metadata = {"from": "", "subject": "", "date": "", "message_id": "", "to": ""}
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        if name == 'from':
            metadata['from'] = value
        elif name == 'subject':
            metadata['subject'] = value
        elif name == 'date':
            metadata['date'] = value
        elif name == 'message-id':
            metadata['message_id'] = value
        elif name == 'to':
            metadata['to'] = value
    return metadata

@app.get("/api/gmail/status")
async def gmail_status(current_user: dict = Depends(get_current_user)):
    """Check if Gmail is connected"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    is_connected = token_doc is not None and "access_token" in token_doc
    return {
        "connected": is_connected,
        "watch_email": GMAIL_WATCH_EMAIL if is_connected else None,
        "configured": bool(GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET)
    }

@app.get("/api/gmail/connect")
async def gmail_connect(current_user: dict = Depends(get_current_user)):
    """Initiate Gmail OAuth flow"""
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET:
        raise HTTPException(status_code=400, detail="Gmail credentials not configured")
    
    flow = get_gmail_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # Store state for verification
    gmail_tokens_collection.update_one(
        {"type": "gmail_oauth_state"},
        {"$set": {"state": state, "created_at": datetime.now(timezone.utc)}},
        upsert=True
    )
    
    return {"authorization_url": authorization_url}

@app.get("/api/auth/gmail/callback")
async def gmail_callback(code: str = None, state: str = None, error: str = None):
    """Handle Gmail OAuth callback"""
    frontend_url = "https://filter-inbox-fix.preview.emergentagent.com"
    
    if error:
        return RedirectResponse(url=f"{frontend_url}/settings?gmail_error={error}")
    
    if not code:
        return RedirectResponse(url=f"{frontend_url}/settings?gmail_error=no_code")
    
    try:
        flow = get_gmail_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Store tokens
        gmail_tokens_collection.update_one(
            {"type": "gmail_oauth"},
            {
                "$set": {
                    "access_token": credentials.token,
                    "refresh_token": credentials.refresh_token,
                    "token_uri": credentials.token_uri,
                    "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        logger.info("[GMAIL] OAuth tokens stored successfully")
        return RedirectResponse(url=f"{frontend_url}/settings?gmail_connected=true")
    
    except Exception as e:
        logger.info(f"[GMAIL] OAuth error: {str(e)}")
        return RedirectResponse(url=f"{frontend_url}/settings?gmail_error={str(e)}")

@app.post("/api/gmail/disconnect")
async def gmail_disconnect(current_user: dict = Depends(get_current_user)):
    """Disconnect Gmail integration"""
    gmail_tokens_collection.delete_one({"type": "gmail_oauth"})
    return {"message": "Gmail disconnected successfully"}

@app.get("/api/gmail/emails")
async def get_gmail_emails(
    max_results: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Fetch recent emails from connected Gmail account"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    try:
        service = get_gmail_service(token_doc)
        
        # Get list of messages
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            labelIds=['INBOX']
        ).execute()
        
        messages = results.get('messages', [])
        emails = []
        
        for msg in messages:
            msg_detail = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            metadata = extract_email_metadata(msg_detail.get('payload', {}).get('headers', []))
            body = parse_email_body(msg_detail.get('payload', {}))
            
            # Truncate body for listing
            body_preview = body[:500] + "..." if len(body) > 500 else body
            
            emails.append({
                "id": msg['id'],
                "thread_id": msg_detail.get('threadId'),
                "from": metadata['from'],
                "subject": metadata['subject'],
                "date": metadata['date'],
                "body_preview": body_preview,
                "snippet": msg_detail.get('snippet', ''),
                "labels": msg_detail.get('labelIds', [])
            })
        
        return {"emails": emails, "count": len(emails)}
    
    except Exception as e:
        logger.info(f"[GMAIL] Error fetching emails: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch emails: {str(e)}")

@app.get("/api/gmail/email/{message_id}")
async def get_gmail_email_detail(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get full email details"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    try:
        service = get_gmail_service(token_doc)
        
        msg_detail = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        metadata = extract_email_metadata(msg_detail.get('payload', {}).get('headers', []))
        body = parse_email_body(msg_detail.get('payload', {}))
        
        return {
            "id": message_id,
            "thread_id": msg_detail.get('threadId'),
            "from": metadata['from'],
            "to": metadata['to'],
            "subject": metadata['subject'],
            "date": metadata['date'],
            "body": body,
            "labels": msg_detail.get('labelIds', [])
        }
    
    except Exception as e:
        logger.info(f"[GMAIL] Error fetching email detail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch email: {str(e)}")

@app.post("/api/gmail/create-ticket/{message_id}")
async def create_ticket_from_email(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Create a ticket from an email"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    # Check if ticket already exists for this email
    existing = tickets_collection.find_one({"email_message_id": message_id})
    if existing:
        return serialize_doc(existing)
    
    try:
        service = get_gmail_service(token_doc)
        
        msg_detail = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        metadata = extract_email_metadata(msg_detail.get('payload', {}).get('headers', []))
        body = parse_email_body(msg_detail.get('payload', {}))
        
        # Parse sender email
        _, sender_email = parseaddr(metadata['from'])
        
        # Create ticket
        ticket_id = generate_ticket_id()
        max_order_ticket = tickets_collection.find_one(
            {"status": "todo"},
            sort=[("order", DESCENDING)]
        )
        next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
        
        ticket_doc = {
            "ticket_id": ticket_id,
            "title": metadata['subject'] or "No Subject",
            "description": body,
            "status": "todo",
            "priority": "medium",
            "order": next_order,
            "created_by": current_user["user_id"],
            "assignee_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            # Email metadata
            "source": "email",
            "email_message_id": message_id,
            "email_thread_id": msg_detail.get('threadId'),
            "email_from": metadata['from'],
            "email_sender": sender_email,
            "email_date": metadata['date']
        }
        
        tickets_collection.insert_one(ticket_doc)
        logger.info(f"[GMAIL] Created ticket {ticket_id} from email {message_id}")
        
        return serialize_doc(ticket_doc)
    
    except Exception as e:
        logger.info(f"[GMAIL] Error creating ticket from email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")

@app.post("/api/gmail/sync")
async def sync_emails_to_tickets(
    max_emails: int = 100,
    query: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Sync emails matching query to tickets. Default syncs ALL inbox emails."""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(
            status_code=503, 
            detail="Gmail not connected. Please connect Gmail in Settings first."
        )
    
    try:
        service = get_gmail_service(token_doc)
        
        # Use provided query or default (all inbox emails)
        search_query = query if query else GMAIL_SYNC_QUERY
        logger.info(f"[GMAIL] Syncing with query: {search_query}, max: {max_emails}")
        
        results = service.users().messages().list(
            userId='me',
            maxResults=max_emails,
            q=search_query
        ).execute()
        
        messages = results.get('messages', [])
        logger.info(f"[GMAIL] Found {len(messages)} emails matching query")
        created_tickets = []
        skipped = 0
        
        # Import email utilities
        from email_utils import (
            extract_email_headers, 
            parse_email_content,
            extract_email_address as extract_email_addr,
            format_sender_name
        )
        
        added_replies = 0
        
        for msg in messages:
            msg_detail = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            gmail_thread_id = msg_detail.get('threadId')
            
            # Use improved email parsing
            payload = msg_detail.get('payload', {})
            headers = extract_email_headers(payload.get('headers', []))
            content = parse_email_content(payload)
            
            # Use shared helper for thread detection and deduplication
            existing = find_existing_ticket_for_email(msg['id'], gmail_thread_id, headers)
            
            if existing:
                if existing["type"] in ["duplicate_ticket", "duplicate_reply"]:
                    # Already processed
                    skipped += 1
                    continue
                elif existing["type"] == "thread_match":
                    # This is a reply to an existing thread - add as reply
                    add_email_as_reply_to_ticket(
                        ticket=existing["ticket"],
                        gmail_message_id=msg['id'],
                        gmail_thread_id=gmail_thread_id,
                        headers=headers,
                        content=content,
                        source="gmail_sync"
                    )
                    added_replies += 1
                    continue
            
            # No existing thread - create new ticket
            ticket_id = generate_ticket_id()
            max_order_ticket = tickets_collection.find_one(
                {"status": "todo"},
                sort=[("order", DESCENDING)]
            )
            next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
            
            ticket_doc = {
                "ticket_id": ticket_id,
                "uuid": str(uuid.uuid4()),
                "title": (headers['subject'] or "No Subject")[:200],
                "description": content['text'][:5000] if content['text'] else "",
                "status": "todo",
                "priority": "medium",
                "order": next_order,
                "created_by": current_user["user_id"],
                "assignee_id": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "source": "email",
                # Gmail internal IDs
                "email_message_id": msg['id'],
                "email_thread_id": gmail_thread_id,
                # RFC 2822 headers for proper threading
                "email_rfc_message_id": headers['message_id'],
                "email_references": headers['references'],
                "email_in_reply_to": headers['in_reply_to'],
                # Sender info
                "email_sender": headers['from'],
                "email_sender_name": format_sender_name(headers['from']),
                "customer_email": extract_email_addr(headers['from']),
                "email_to": headers['to'],
                "email_cc": headers['cc'],
                "email_date": headers['date'],
                # Content for rendering
                "email_html": content['html'][:100000] if content['html'] else None,
                "email_text": content['text'][:50000] if content['text'] else None,
                "email_preview": content['preview'],
                "escalation_level": "L1"
            }
            
            tickets_collection.insert_one(ticket_doc)
            created_tickets.append(serialize_doc(ticket_doc))
        
        return {
            "created": len(created_tickets),
            "added_replies": added_replies,
            "skipped": skipped,
            "tickets": created_tickets
        }
    
    except Exception as e:
        logger.info(f"[GMAIL] Error syncing emails: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to sync emails: {str(e)}")

@app.get("/api/settings/email")
async def get_email_settings(current_user: dict = Depends(get_current_user)):
    """Get email integration settings"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    watch_doc = gmail_tokens_collection.find_one({"type": "gmail_watch"})
    return {
        "gmail_connected": token_doc is not None and "access_token" in token_doc,
        "watch_email": GMAIL_WATCH_EMAIL,
        "configured": bool(GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET),
        "watch_active": watch_doc is not None and watch_doc.get("expiration", 0) > datetime.now(timezone.utc).timestamp() * 1000,
        "sync_query": GMAIL_SYNC_QUERY
    }

@app.put("/api/settings/email")
async def update_email_settings(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Update email settings (admin only for now)"""
    # In production, this would update env vars or a config collection
    # For now, just return success as the email is set via env var
    return {"message": "Email settings updated"}

@app.post("/api/gmail/backfill-email-content")
async def backfill_email_content(
    current_user: dict = Depends(get_current_user),
    limit: int = 50
):
    """
    Backfill email_html, email_text, and email_preview for existing email tickets.
    This fetches the full email content from Gmail API and updates tickets.
    """
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    try:
        service = get_gmail_service(token_doc)
        
        # Find email tickets without email_html populated
        tickets_to_update = list(tickets_collection.find({
            "source": "email",
            "email_message_id": {"$exists": True, "$ne": None},
            "$or": [
                {"email_html": {"$exists": False}},
                {"email_html": None}
            ]
        }).limit(limit))
        
        if not tickets_to_update:
            return {"message": "No tickets need backfilling", "updated": 0}
        
        from email_utils import extract_email_headers, parse_email_content, format_sender_name
        from email_utils import extract_email_address as extract_email_addr
        
        updated_count = 0
        errors = []
        
        for ticket in tickets_to_update:
            gmail_msg_id = ticket.get("email_message_id")
            if not gmail_msg_id:
                continue
                
            try:
                # Fetch full message from Gmail
                full_msg = service.users().messages().get(
                    userId='me',
                    id=gmail_msg_id,
                    format='full'
                ).execute()
                
                payload = full_msg.get('payload', {})
                headers = extract_email_headers(payload.get('headers', []))
                content = parse_email_content(payload)
                
                # Update the ticket with new content fields
                update_data = {
                    "email_rfc_message_id": headers['message_id'] or ticket.get('email_rfc_message_id'),
                    "email_references": headers['references'] or ticket.get('email_references'),
                    "email_in_reply_to": headers['in_reply_to'] or ticket.get('email_in_reply_to'),
                    "email_sender_name": format_sender_name(headers['from']) if headers['from'] else ticket.get('email_sender_name'),
                    "email_html": content['html'][:100000] if content['html'] else None,
                    "email_text": content['text'][:50000] if content['text'] else None,
                    "email_preview": content['preview'] or ticket.get('email_preview'),
                    "updated_at": datetime.now(timezone.utc)
                }
                
                # Remove None values to avoid overwriting existing data
                update_data = {k: v for k, v in update_data.items() if v is not None}
                
                tickets_collection.update_one(
                    {"ticket_id": ticket["ticket_id"]},
                    {"$set": update_data}
                )
                updated_count += 1
                
            except Exception as e:
                errors.append({"ticket_id": ticket.get("ticket_id"), "error": str(e)})
                logger.warning(f"[BACKFILL] Error updating ticket {ticket.get('ticket_id')}: {e}")
        
        return {
            "message": f"Backfilled {updated_count} tickets",
            "updated": updated_count,
            "total_found": len(tickets_to_update),
            "errors": errors[:10] if errors else []  # Limit error output
        }
        
    except Exception as e:
        logger.error(f"[BACKFILL] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Backfill failed: {str(e)}")

# ==================== Email Reply ====================

@app.post("/api/tickets/{ticket_id}/reply")
async def reply_to_ticket(
    ticket_id: str,
    reply: EmailReplyRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Reply to a ticket via email using Gmail API.
    Requires Gmail to be connected in Settings.
    """
    # Get the ticket
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Prevent duplicate email submissions (same content within 10 seconds)
    ten_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=10)
    existing_duplicate = email_replies_collection.find_one({
        "ticket_id": ticket_id,
        "sent_by": current_user["user_id"],
        "body": reply.body,
        "created_at": {"$gte": ten_seconds_ago}
    })
    if existing_duplicate:
        # Return the existing reply instead of sending duplicate email
        logger.info(f"[EMAIL] Prevented duplicate email submission for ticket {ticket_id}")
        return {
            "status": "sent",
            "message": "Email already sent (duplicate prevented)",
            "reply_id": existing_duplicate.get("reply_id"),
            "gmail_message_id": existing_duplicate.get("gmail_message_id"),
            "duplicate_prevented": True
        }
    
    # Verify Gmail is connected
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(
            status_code=503, 
            detail="Gmail not connected. Please connect Gmail in Settings before sending emails."
        )
    
    # Create reply record
    reply_id = f"reply_{uuid.uuid4().hex[:12]}"
    reply_doc = {
        "reply_id": reply_id,
        "ticket_id": ticket_id,
        "direction": "outgoing",  # Mark as outgoing (from agent to customer)
        "to_email": reply.to_email,
        "subject": reply.subject,
        "body": reply.body,
        "sent_by": current_user["user_id"],
        "sent_by_email": current_user.get("email"),
        "sent_by_name": current_user.get("name"),
        "created_at": datetime.now(timezone.utc)
    }
    
    try:
        service = get_gmail_service(token_doc)
        
        # Import email utilities for proper threading
        from email_utils import build_threading_headers, generate_message_id
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Build proper email with threading headers
        message = MIMEMultipart('alternative')
        message['To'] = reply.to_email
        message['Subject'] = reply.subject
        
        # Generate a proper Message-ID for this outgoing email
        our_message_id = generate_message_id("tickflow.app")
        message['Message-ID'] = our_message_id
        
        # Build threading headers using RFC 2822 Message-ID (not Gmail's internal ID)
        original_message_id = ticket.get('email_rfc_message_id') or ticket.get('email_message_id', '')
        original_references = ticket.get('email_references', '')
        
        if original_message_id:
            threading_headers = build_threading_headers(
                original_message_id=original_message_id,
                original_references=original_references
            )
            
            if threading_headers.get('In-Reply-To'):
                message['In-Reply-To'] = threading_headers['In-Reply-To']
            if threading_headers.get('References'):
                message['References'] = threading_headers['References']
        
        # Attach plain text body
        text_part = MIMEText(reply.body, 'plain', 'utf-8')
        message.attach(text_part)
        
        # Also attach HTML version for better formatting
        html_body = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; line-height: 1.5; color: #333;">
        {reply.body.replace(chr(10), '<br>')}
        </body>
        </html>
        """
        html_part = MIMEText(html_body, 'html', 'utf-8')
        message.attach(html_part)
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send with Gmail threadId for Gmail's internal threading
        send_body = {'raw': raw_message}
        if ticket.get('email_thread_id'):
            send_body['threadId'] = ticket.get('email_thread_id')
        
        send_result = service.users().messages().send(
            userId='me',
            body=send_body
        ).execute()
        
        reply_doc["status"] = "sent"
        reply_doc["gmail_message_id"] = send_result.get('id')
        reply_doc["our_message_id"] = our_message_id  # Store our Message-ID for future threading
        email_replies_collection.insert_one(reply_doc)
        
        # Update ticket with our reply's Message-ID for future thread chain
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {
                "$set": {
                    "status": "waiting",
                    "updated_at": datetime.now(timezone.utc),
                    "last_reply_at": datetime.now(timezone.utc),
                    "last_reply_message_id": our_message_id
                },
                "$push": {
                    "email_thread_message_ids": our_message_id
                }
            }
        )
        
        logger.info(f"[EMAIL] Reply sent for ticket {ticket_id} to {reply.to_email}, Gmail ID: {send_result.get('id')}, Message-ID: {our_message_id}")
        
        # Trigger webhook for reply added
        asyncio.create_task(trigger_webhooks("ticket.reply_added", {
            "ticket_id": ticket_id,
            "ticket_title": ticket.get("title", ""),
            "reply_id": reply_id,
            "to_email": reply.to_email,
            "subject": reply.subject,
            "sent_by": current_user.get("name", current_user["user_id"])
        }))
        
        return {
            "status": "sent",
            "message": "Email sent successfully",
            "reply_id": reply_id,
            "gmail_message_id": send_result.get('id'),
            "message_id": our_message_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EMAIL] Error sending reply: {str(e)}")
        reply_doc["status"] = "failed"
        reply_doc["error"] = str(e)
        email_replies_collection.insert_one(reply_doc)
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@app.get("/api/tickets/{ticket_id}/replies")
async def get_ticket_replies(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all replies for a ticket"""
    replies = list(email_replies_collection.find(
        {"ticket_id": ticket_id},
        sort=[("created_at", ASCENDING)]
    ))
    return {"replies": [serialize_doc(r) for r in replies]}

# ==================== Email Simulator (For Testing) ====================

@app.post("/api/email/simulate")
async def simulate_incoming_email(
    email: SimulatedEmail,
    current_user: dict = Depends(get_current_user)
):
    """
    Simulate an incoming email for testing purposes.
    Creates a ticket as if the email came through Gmail.
    """
    # Generate IDs
    message_id = f"sim_{uuid.uuid4().hex[:16]}"
    thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    ticket_id = generate_ticket_id()
    
    # Get next order
    max_order_ticket = tickets_collection.find_one(
        {"status": "todo"},
        sort=[("order", DESCENDING)]
    )
    next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
    
    # Create ticket from simulated email
    ticket_doc = {
        "ticket_id": ticket_id,
        "title": email.subject or "No Subject",
        "description": email.body,
        "status": "todo",
        "priority": "medium",
        "order": next_order,
        "created_by": "email_simulator",
        "assignee_id": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        # Email metadata
        "source": "email",
        "email_message_id": message_id,
        "email_thread_id": thread_id,
        "email_from": f"{email.from_name} <{email.from_email}>" if email.from_name else email.from_email,
        "email_sender": email.from_email,
        "email_to": email.to_email,
        "email_date": datetime.now(timezone.utc).isoformat(),
        "simulated": True
    }
    
    tickets_collection.insert_one(ticket_doc)
    logger.info(f"[EMAIL SIM] Created ticket {ticket_id} from simulated email")
    
    return {
        "status": "created",
        "ticket_id": ticket_id,
        "message": "Simulated email converted to ticket",
        "ticket": serialize_doc(ticket_doc)
    }

# ==================== Gmail Push Notifications (Webhooks) ====================

@app.post("/api/gmail/webhook")
async def gmail_webhook(request: Request):
    """
    Receive Gmail push notifications via Google Cloud Pub/Sub.
    This endpoint is called by Google when new emails arrive.
    """
    try:
        body = await request.json()
        logger.info(f"[GMAIL WEBHOOK] Received notification: {body}")
        
        # Decode the Pub/Sub message
        if 'message' in body:
            import base64
            message_data = body['message'].get('data', '')
            if message_data:
                decoded = base64.urlsafe_b64decode(message_data).decode('utf-8')
                notification = json.loads(decoded)
                logger.info(f"[GMAIL WEBHOOK] Decoded notification: {notification}")
                
                # Get the history ID to fetch new messages
                history_id = notification.get('historyId')
                email_address = notification.get('emailAddress')
                
                if history_id:
                    # Trigger background sync
                    await process_gmail_notification(history_id, email_address)
        
        # Always return 200 to acknowledge receipt
        return {"status": "ok"}
    
    except Exception as e:
        logger.info(f"[GMAIL WEBHOOK] Error processing notification: {str(e)}")
        # Still return 200 to prevent retries
        return {"status": "error", "message": str(e)}

async def process_gmail_notification(history_id: str, email_address: str):
    """Process a Gmail push notification by fetching new messages"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        logger.warning("[GMAIL WEBHOOK] No Gmail tokens found")
        return
    
    try:
        service = get_gmail_service(token_doc)
        
        # Get the stored history ID
        watch_doc = gmail_tokens_collection.find_one({"type": "gmail_watch"})
        stored_history_id = watch_doc.get("history_id") if watch_doc else None
        
        if stored_history_id:
            # Get history since last check
            history = service.users().history().list(
                userId='me',
                startHistoryId=stored_history_id,
                historyTypes=['messageAdded']
            ).execute()
            
            messages_added = []
            for record in history.get('history', []):
                for msg in record.get('messagesAdded', []):
                    messages_added.append(msg['message']['id'])
            
            logger.info(f"[GMAIL WEBHOOK] Found {len(messages_added)} new messages")
            
            # Process new messages with proper thread detection
            from email_utils import (
                extract_email_headers,
                parse_email_content,
                extract_email_address as extract_email_addr,
                format_sender_name
            )
            
            for msg_id in messages_added:
                msg_detail = service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='full'
                ).execute()
                
                # Only process inbox messages
                if 'INBOX' not in msg_detail.get('labelIds', []):
                    continue
                
                gmail_thread_id = msg_detail.get('threadId')
                
                # Use improved email parsing
                payload = msg_detail.get('payload', {})
                headers = extract_email_headers(payload.get('headers', []))
                content = parse_email_content(payload)
                
                # Use shared helper for thread detection and deduplication
                existing = find_existing_ticket_for_email(msg_id, gmail_thread_id, headers)
                
                if existing:
                    if existing["type"] in ["duplicate_ticket", "duplicate_reply"]:
                        # Already processed
                        continue
                    elif existing["type"] == "thread_match":
                        # This is a reply to an existing thread - add as reply
                        add_email_as_reply_to_ticket(
                            ticket=existing["ticket"],
                            gmail_message_id=msg_id,
                            gmail_thread_id=gmail_thread_id,
                            headers=headers,
                            content=content,
                            source="gmail_webhook"
                        )
                        logger.info(f"[GMAIL WEBHOOK] Added reply to ticket {existing['ticket']['ticket_id']} from {extract_email_addr(headers.get('from', ''))}")
                        continue
                
                # No existing thread - create new ticket
                _, sender_email = parseaddr(headers.get('from', ''))
                
                ticket_id = generate_ticket_id()
                max_order_ticket = tickets_collection.find_one(
                    {"status": "todo"},
                    sort=[("order", DESCENDING)]
                )
                next_order = (max_order_ticket["order"] + 1) if max_order_ticket and "order" in max_order_ticket else 0
                
                ticket_doc = {
                    "ticket_id": ticket_id,
                    "uuid": str(uuid.uuid4()),
                    "title": (headers.get('subject') or "No Subject")[:200],
                    "description": content.get('text', '')[:5000] if content.get('text') else "",
                    "status": "todo",
                    "priority": "medium",
                    "order": next_order,
                    "created_by": "system",
                    "assignee_id": None,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "source": "email",
                    "email_message_id": msg_id,
                    "email_thread_id": gmail_thread_id,
                    "email_rfc_message_id": headers.get('message_id', ''),
                    "email_references": headers.get('references', ''),
                    "email_in_reply_to": headers.get('in_reply_to', ''),
                    "email_from": headers.get('from', ''),
                    "email_sender": sender_email,
                    "email_sender_name": format_sender_name(headers.get('from', '')),
                    "customer_email": extract_email_addr(headers.get('from', '')),
                    "email_to": headers.get('to', ''),
                    "email_date": headers.get('date', ''),
                    "email_html": content.get('html', '')[:100000] if content.get('html') else None,
                    "email_text": content.get('text', '')[:50000] if content.get('text') else None,
                    "escalation_level": "L1"
                }
                
                tickets_collection.insert_one(ticket_doc)
                logger.info(f"[GMAIL WEBHOOK] Created ticket {ticket_id} from email {msg_id}")
        
        # Update stored history ID
        gmail_tokens_collection.update_one(
            {"type": "gmail_watch"},
            {"$set": {"history_id": history_id}},
            upsert=True
        )
        
    except Exception as e:
        logger.info(f"[GMAIL WEBHOOK] Error processing: {str(e)}")

@app.post("/api/gmail/watch/start")
async def start_gmail_watch(current_user: dict = Depends(get_current_user)):
    """
    Start watching Gmail inbox for new messages.
    Requires Cloud Pub/Sub topic to be configured.
    """
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    # Get Pub/Sub topic from env
    pubsub_topic = os.environ.get("GMAIL_PUBSUB_TOPIC", "")
    if not pubsub_topic:
        raise HTTPException(
            status_code=400, 
            detail="GMAIL_PUBSUB_TOPIC not configured. Please set up Cloud Pub/Sub first."
        )
    
    try:
        service = get_gmail_service(token_doc)
        
        # Start watching
        watch_response = service.users().watch(
            userId='me',
            body={
                'topicName': pubsub_topic,
                'labelIds': ['INBOX']
            }
        ).execute()
        
        logger.info(f"[GMAIL] Watch started: {watch_response}")
        
        # Store watch info
        gmail_tokens_collection.update_one(
            {"type": "gmail_watch"},
            {
                "$set": {
                    "history_id": watch_response.get('historyId'),
                    "expiration": watch_response.get('expiration'),
                    "started_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        return {
            "status": "watching",
            "history_id": watch_response.get('historyId'),
            "expiration": watch_response.get('expiration')
        }
    
    except Exception as e:
        logger.info(f"[GMAIL] Error starting watch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start watch: {str(e)}")

@app.post("/api/gmail/watch/stop")
async def stop_gmail_watch(current_user: dict = Depends(get_current_user)):
    """Stop watching Gmail inbox"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    if not token_doc or "access_token" not in token_doc:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    try:
        service = get_gmail_service(token_doc)
        service.users().stop(userId='me').execute()
        
        gmail_tokens_collection.delete_one({"type": "gmail_watch"})
        
        return {"status": "stopped"}
    
    except Exception as e:
        logger.info(f"[GMAIL] Error stopping watch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop watch: {str(e)}")

# ==================== Admin Panel Endpoints ====================

@app.get("/api/admin/custom-fields")
async def get_custom_fields(
    entity_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all custom fields, optionally filtered by entity type"""
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    
    fields = list(custom_fields_collection.find(query).sort("created_at", DESCENDING))
    return [serialize_doc(f) for f in fields]

@app.post("/api/admin/custom-fields")
async def create_custom_field(
    field_data: CustomFieldCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new custom field"""
    # Validate field type
    valid_types = ["text", "number", "select", "date", "boolean"]
    if field_data.field_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid field type. Must be one of: {valid_types}")
    
    # Validate entity type
    if field_data.entity_type not in ["ticket", "user"]:
        raise HTTPException(status_code=400, detail="Entity type must be 'ticket' or 'user'")
    
    # Check for duplicate name
    existing = custom_fields_collection.find_one({
        "name": field_data.name,
        "entity_type": field_data.entity_type
    })
    if existing:
        raise HTTPException(status_code=400, detail="A field with this name already exists")
    
    field_id = f"field_{uuid.uuid4().hex[:12]}"
    field_doc = {
        "field_id": field_id,
        "name": field_data.name,
        "field_type": field_data.field_type,
        "entity_type": field_data.entity_type,
        "options": field_data.options or [],
        "required": field_data.required,
        "description": field_data.description,
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user.get("user_id")
    }
    
    custom_fields_collection.insert_one(field_doc)
    return serialize_doc(field_doc)

@app.put("/api/admin/custom-fields/{field_id}")
async def update_custom_field(
    field_id: str,
    field_data: CustomFieldUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a custom field"""
    field = custom_fields_collection.find_one({"field_id": field_id})
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    update_data = {k: v for k, v in field_data.dict().items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        custom_fields_collection.update_one(
            {"field_id": field_id},
            {"$set": update_data}
        )
    
    updated = custom_fields_collection.find_one({"field_id": field_id})
    return serialize_doc(updated)

@app.delete("/api/admin/custom-fields/{field_id}")
async def delete_custom_field(
    field_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a custom field"""
    result = custom_fields_collection.delete_one({"field_id": field_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Field not found")
    return {"message": "Field deleted"}

@app.get("/api/admin/settings")
async def get_admin_settings(current_user: dict = Depends(get_current_user)):
    """Get all admin settings"""
    settings = admin_settings_collection.find_one({"type": "global"})
    if not settings:
        # Return defaults
        return {
            "company_name": "TickFlow",
            "support_email": "",
            "auto_assignment": True,
            "auto_reassign_reopened": False,
            "default_priority": "medium",
            "ticket_statuses": ["todo", "in_progress", "waiting", "review", "resolved"],
            "ticket_priorities": ["low", "medium", "high", "urgent"]
        }
    # Ensure new settings have defaults
    result = serialize_doc(settings)
    if "auto_reassign_reopened" not in result:
        result["auto_reassign_reopened"] = False
    return result

@app.put("/api/admin/settings")
async def update_admin_settings(
    settings: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update admin settings"""
    settings["type"] = "global"
    settings["updated_at"] = datetime.now(timezone.utc)
    settings["updated_by"] = current_user.get("user_id")
    
    admin_settings_collection.update_one(
        {"type": "global"},
        {"$set": settings},
        upsert=True
    )
    
    updated_settings = admin_settings_collection.find_one({"type": "global"}, {"_id": 0})
    return serialize_doc(updated_settings) if updated_settings else settings

# ==================== Routing Rules Endpoints ====================

@app.get("/api/admin/routing-rules")
async def get_routing_rules(current_user: dict = Depends(get_current_user)):
    """Get all routing rules"""
    rules = list(routing_rules_collection.find({}, {"_id": 0}).sort("priority", -1))
    return [serialize_doc(r) for r in rules]

@app.post("/api/admin/routing-rules")
async def create_routing_rule(
    rule_data: RoutingRuleCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new routing rule"""
    rule_id = f"rule_{uuid.uuid4().hex[:12]}"
    
    # Handle both new format (condition_groups) and legacy format (conditions)
    condition_groups = rule_data.condition_groups
    if not condition_groups and rule_data.conditions:
        # Convert legacy format to new format
        condition_groups = [rule_data.conditions]
    
    rule_doc = {
        "rule_id": rule_id,
        "name": rule_data.name,
        "description": rule_data.description,
        "condition_groups": condition_groups or [[{"field": "priority", "operator": "equals", "value": ""}]],
        "actions": rule_data.actions,
        "priority": rule_data.priority,
        "is_active": rule_data.is_active,
        "assignment_method": rule_data.assignment_method,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    routing_rules_collection.insert_one(rule_doc)
    return serialize_doc(rule_doc)

@app.put("/api/admin/routing-rules/{rule_id}")
async def update_routing_rule(
    rule_id: str,
    rule_data: RoutingRuleUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a routing rule"""
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if rule_data.name is not None:
        update_data["name"] = rule_data.name
    if rule_data.description is not None:
        update_data["description"] = rule_data.description
    if rule_data.condition_groups is not None:
        update_data["condition_groups"] = rule_data.condition_groups
    elif rule_data.conditions is not None:
        # Legacy support: convert to condition_groups
        update_data["condition_groups"] = [rule_data.conditions]
    if rule_data.actions is not None:
        update_data["actions"] = rule_data.actions
    if rule_data.priority is not None:
        update_data["priority"] = rule_data.priority
    if rule_data.is_active is not None:
        update_data["is_active"] = rule_data.is_active
    if rule_data.assignment_method is not None:
        update_data["assignment_method"] = rule_data.assignment_method
    
    result = routing_rules_collection.update_one(
        {"rule_id": rule_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = routing_rules_collection.find_one({"rule_id": rule_id}, {"_id": 0})
    return serialize_doc(rule)

@app.delete("/api/admin/routing-rules/{rule_id}")
async def delete_routing_rule(
    rule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a routing rule"""
    result = routing_rules_collection.delete_one({"rule_id": rule_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"message": "Rule deleted successfully"}

@app.post("/api/admin/routing-rules/test")
async def test_routing_rule(
    ticket_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Test routing rules against a sample ticket (dry run - no changes)"""
    rules = list(routing_rules_collection.find(
        {"is_active": True}, 
        {"_id": 0}
    ).sort("priority", -1))
    
    matched_rules = []
    for rule in rules:
        conditions = rule.get("conditions", [])
        all_match = True
        condition_results = []
        
        for condition in conditions:
            result = evaluate_condition(ticket_data, condition)
            condition_results.append({
                "condition": condition,
                "matched": result
            })
            if not result:
                all_match = False
        
        if all_match:
            matched_rules.append({
                "rule_id": rule.get("rule_id"),
                "rule_name": rule.get("name"),
                "priority": rule.get("priority"),
                "actions": rule.get("actions"),
                "condition_results": condition_results
            })
    
    return {
        "ticket_data": ticket_data,
        "matched_rules": matched_rules,
        "would_apply": matched_rules[0] if matched_rules else None
    }

@app.post("/api/tickets/{ticket_id}/route")
async def route_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger routing rules for a ticket"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    result = run_routing_rules(ticket)
    
    # Get updated ticket
    updated_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    
    return {
        "ticket": serialize_doc(updated_ticket),
        "routing_result": result
    }

# ==================== SLA Policies Endpoints ====================

@app.get("/api/admin/sla-policies")
async def get_sla_policies(current_user: dict = Depends(get_current_user)):
    """Get SLA policy settings"""
    settings = admin_settings_collection.find_one({"type": "sla_settings"}) or {}
    
    # Return default structure if not set
    return {
        "default_first_response_hours": settings.get("default_first_response_hours", 4),
        "default_resolution_hours": settings.get("default_resolution_hours", 24),
        "priority_slas": settings.get("priority_slas", {
            "low": {"first_response_minutes": 480, "resolution_minutes": 2880},      # 8h / 48h
            "medium": {"first_response_minutes": 240, "resolution_minutes": 1440},   # 4h / 24h
            "high": {"first_response_minutes": 60, "resolution_minutes": 480},       # 1h / 8h
            "urgent": {"first_response_minutes": 15, "resolution_minutes": 120}      # 15m / 2h
        }),
        "business_hours_only": settings.get("business_hours_only", False),
        "business_hours": settings.get("business_hours", {
            "start": "09:00",
            "end": "18:00",
            "days": [1, 2, 3, 4, 5]  # Mon-Fri
        }),
        "holidays": settings.get("holidays", []),
        "escalation_debounce_minutes": settings.get("escalation_debounce_minutes", 10)  # Default 10 min
    }

@app.put("/api/admin/sla-policies")
async def update_sla_policies(
    data: SLAPoliciesUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update SLA policy settings"""
    # Update only provided fields
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if data.default_first_response_hours is not None:
        update_data["default_first_response_hours"] = data.default_first_response_hours
    
    if data.default_resolution_hours is not None:
        update_data["default_resolution_hours"] = data.default_resolution_hours
    
    if data.priority_slas is not None:
        # Convert Pydantic models to dicts
        update_data["priority_slas"] = {
            k: v.dict() if hasattr(v, 'dict') else v 
            for k, v in data.priority_slas.items()
        }
    
    if data.business_hours_only is not None:
        update_data["business_hours_only"] = data.business_hours_only
    
    if data.business_hours is not None:
        update_data["business_hours"] = data.business_hours
    
    if data.holidays is not None:
        update_data["holidays"] = data.holidays
    
    if data.escalation_debounce_minutes is not None:
        update_data["escalation_debounce_minutes"] = data.escalation_debounce_minutes
    
    # Upsert the settings
    admin_settings_collection.update_one(
        {"type": "sla_settings"},
        {"$set": update_data},
        upsert=True
    )
    
    # Return updated settings
    updated = admin_settings_collection.find_one({"type": "sla_settings"}, {"_id": 0})
    return {
        "message": "SLA policies updated successfully",
        "settings": updated
    }

# ==================== SLA Escalation Rules Endpoints ====================

@app.get("/api/admin/sla-escalation-rules")
async def get_sla_escalation_rules(current_user: dict = Depends(get_current_user)):
    """Get all SLA escalation rules"""
    rules = list(sla_escalation_rules_collection.find({}, {"_id": 0}).sort("priority", -1))
    return [serialize_doc(r) for r in rules]

@app.post("/api/admin/sla-escalation-rules")
async def create_sla_escalation_rule(
    rule_data: SLAEscalationRuleCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new SLA escalation rule"""
    rule_id = f"sla_rule_{uuid.uuid4().hex[:12]}"
    
    rule_doc = {
        "rule_id": rule_id,
        "name": rule_data.name,
        "description": rule_data.description,
        "trigger_type": rule_data.trigger_type,
        "trigger_threshold": rule_data.trigger_threshold,
        "priority_filter": rule_data.priority_filter,
        "escalation_level_filter": rule_data.escalation_level_filter,
        "actions": rule_data.actions,
        "priority": rule_data.priority,
        "is_active": rule_data.is_active,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    sla_escalation_rules_collection.insert_one(rule_doc)
    return serialize_doc(rule_doc)

@app.put("/api/admin/sla-escalation-rules/{rule_id}")
async def update_sla_escalation_rule(
    rule_id: str,
    rule_data: SLAEscalationRuleUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an SLA escalation rule"""
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if rule_data.name is not None:
        update_data["name"] = rule_data.name
    if rule_data.description is not None:
        update_data["description"] = rule_data.description
    if rule_data.trigger_type is not None:
        update_data["trigger_type"] = rule_data.trigger_type
    if rule_data.trigger_threshold is not None:
        update_data["trigger_threshold"] = rule_data.trigger_threshold
    if rule_data.priority_filter is not None:
        update_data["priority_filter"] = rule_data.priority_filter
    if rule_data.escalation_level_filter is not None:
        update_data["escalation_level_filter"] = rule_data.escalation_level_filter
    if rule_data.actions is not None:
        update_data["actions"] = rule_data.actions
    if rule_data.priority is not None:
        update_data["priority"] = rule_data.priority
    if rule_data.is_active is not None:
        update_data["is_active"] = rule_data.is_active
    
    result = sla_escalation_rules_collection.update_one(
        {"rule_id": rule_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = sla_escalation_rules_collection.find_one({"rule_id": rule_id}, {"_id": 0})
    return serialize_doc(rule)

@app.delete("/api/admin/sla-escalation-rules/{rule_id}")
async def delete_sla_escalation_rule(
    rule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an SLA escalation rule"""
    result = sla_escalation_rules_collection.delete_one({"rule_id": rule_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"message": "Rule deleted successfully"}

@app.post("/api/admin/sla-escalation-rules/check")
async def run_sla_check(current_user: dict = Depends(get_current_user)):
    """Manually trigger SLA escalation check on all open tickets"""
    results = check_sla_escalations()
    return results

# ==================== Conversation History Endpoints ====================

@app.get("/api/tickets/by-email/{email}")
async def get_tickets_by_email(
    email: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all tickets from a specific email address"""
    # Normalize email
    email_lower = email.lower().strip()
    
    # Find tickets with matching customer_email
    tickets = list(tickets_collection.find({
        "$or": [
            {"customer_email": {"$regex": f"^{re.escape(email_lower)}$", "$options": "i"}},
            {"email_sender": {"$regex": f"^{re.escape(email_lower)}$", "$options": "i"}},
            {"email_from": {"$regex": re.escape(email_lower), "$options": "i"}}
        ]
    }).sort("created_at", DESCENDING))
    
    return [serialize_doc(t) for t in tickets]

@app.get("/api/tickets/{ticket_id}/related")
async def get_related_tickets(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get tickets from the same customer as this ticket"""
    # Find the ticket
    ticket = tickets_collection.find_one({
        "$or": [
            {"id": ticket_id},
            {"ticket_id": ticket_id}
        ]
    })
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get customer email - normalize it
    customer_email = ticket.get("customer_email") or ticket.get("email_sender")
    if not customer_email:
        return []
    
    # Extract just the email address from formats like "Name <email@domain.com>"
    customer_email_clean = customer_email.strip()
    if '<' in customer_email_clean and '>' in customer_email_clean:
        # Extract email from angle brackets
        match = re.search(r'<([^>]+)>', customer_email_clean)
        if match:
            customer_email_clean = match.group(1)
    
    customer_email_lower = customer_email_clean.lower()
    
    # Find other tickets from same customer using case-insensitive matching
    # Match both the original format and the cleaned email
    related = list(tickets_collection.find({
        "$and": [
            {"$or": [
                {"customer_email": customer_email},
                {"customer_email": customer_email_clean},
                {"customer_email": {"$regex": f"^{re.escape(customer_email_clean)}$", "$options": "i"}},
                {"email_sender": customer_email},
                {"email_sender": customer_email_clean},
                {"email_sender": {"$regex": f"^{re.escape(customer_email_clean)}$", "$options": "i"}},
                {"email_sender": {"$regex": f"<{re.escape(customer_email_clean)}>", "$options": "i"}}
            ]},
            {"ticket_id": {"$ne": ticket.get("ticket_id")}}
        ]
    }).sort("updated_at", DESCENDING).limit(20))
    
    return [serialize_doc(t) for t in related]


# ==================== SLA Management ====================

@app.get("/api/sla-policies")
async def list_sla_policies(current_user: dict = Depends(get_current_user)):
    """Get all SLA policies"""
    policies = list(sla_policies_collection.find({}, {"_id": 0}))
    return policies

@app.post("/api/sla-policies")
async def create_sla_policy(
    policy: SLAPolicy,
    current_user: dict = Depends(get_current_user)
):
    """Create a new SLA policy"""
    policy_id = f"sla_{uuid.uuid4().hex[:8]}"
    policy_doc = {
        "policy_id": policy_id,
        **policy.dict(),
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user.get("user_id")
    }
    sla_policies_collection.insert_one(policy_doc)
    return {"policy_id": policy_id, **policy.dict()}

@app.put("/api/sla-policies/{policy_id}")
async def update_sla_policy(
    policy_id: str,
    policy: SLAPolicy,
    current_user: dict = Depends(get_current_user)
):
    """Update an SLA policy"""
    result = sla_policies_collection.update_one(
        {"policy_id": policy_id},
        {"$set": {**policy.dict(), "updated_at": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"policy_id": policy_id, **policy.dict()}

@app.delete("/api/sla-policies/{policy_id}")
async def delete_sla_policy(
    policy_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an SLA policy"""
    result = sla_policies_collection.delete_one({"policy_id": policy_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"message": "Policy deleted"}

@app.get("/api/sla/ticket/{ticket_id}")
async def get_ticket_sla_status(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get SLA status for a specific ticket"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Find applicable SLA policy
    priority = ticket.get("priority", "medium")
    policy = sla_policies_collection.find_one(
        {"$or": [{"priority": priority}, {"priority": "all"}], "is_active": True},
        {"_id": 0}
    )
    
    if not policy:
        return {"ticket_id": ticket_id, "sla_policy": None, "status": "no_policy"}
    
    created_at = ticket.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    
    now = datetime.now(timezone.utc)
    hours_elapsed = (now - created_at).total_seconds() / 3600
    
    # Check first response
    first_response_at = ticket.get("first_response_at")
    first_response_status = "pending"
    first_response_hours = None
    
    if first_response_at:
        if isinstance(first_response_at, str):
            first_response_at = datetime.fromisoformat(first_response_at.replace("Z", "+00:00"))
        first_response_hours = (first_response_at - created_at).total_seconds() / 3600
        first_response_status = "met" if first_response_hours <= policy["first_response_hours"] else "breached"
    elif hours_elapsed > policy["first_response_hours"]:
        first_response_status = "breached"
    elif hours_elapsed > policy["first_response_hours"] * 0.75:
        first_response_status = "at_risk"
    
    # Check resolution
    resolved_at = ticket.get("resolved_at")
    resolution_status = "pending"
    resolution_hours = None
    
    if resolved_at:
        if isinstance(resolved_at, str):
            resolved_at = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
        resolution_hours = (resolved_at - created_at).total_seconds() / 3600
        resolution_status = "met" if resolution_hours <= policy["resolution_hours"] else "breached"
    elif ticket.get("status") not in ["resolved", "closed"]:
        if hours_elapsed > policy["resolution_hours"]:
            resolution_status = "breached"
        elif hours_elapsed > policy["resolution_hours"] * 0.75:
            resolution_status = "at_risk"
    
    return {
        "ticket_id": ticket_id,
        "sla_policy": policy,
        "first_response": {
            "target_hours": policy["first_response_hours"],
            "actual_hours": round(first_response_hours, 2) if first_response_hours else None,
            "status": first_response_status,
            "hours_remaining": max(0, policy["first_response_hours"] - hours_elapsed) if first_response_status == "pending" else None
        },
        "resolution": {
            "target_hours": policy["resolution_hours"],
            "actual_hours": round(resolution_hours, 2) if resolution_hours else None,
            "status": resolution_status,
            "hours_remaining": max(0, policy["resolution_hours"] - hours_elapsed) if resolution_status == "pending" else None
        },
        "hours_elapsed": round(hours_elapsed, 2)
    }


# ==================== Analytics API ====================

@app.get("/api/analytics/overview")
async def get_analytics_overview(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get overview analytics for the dashboard — fully aggregated server-side"""
    from_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    pipeline = [
        {"$facet": {
            "total": [{"$count": "count"}],
            "open": [
                {"$match": {"status": {"$nin": ["resolved", "closed"]}}},
                {"$count": "count"}
            ],
            "in_period": [
                {"$match": {"created_at": {"$gte": from_date}}},
                {"$count": "count"}
            ],
            "resolved_in_period": [
                {"$match": {"created_at": {"$gte": from_date}, "status": {"$in": ["resolved", "closed"]}}},
                {"$count": "count"}
            ],
            "priority_breakdown": [
                {"$match": {"status": {"$nin": ["resolved", "closed"]}}},
                {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
            ],
            "status_breakdown": [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ],
            "volume_trend": [
                {"$match": {"created_at": {"$gte": from_date}}},
                {"$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ],
            "resolution_times": [
                {"$match": {
                    "created_at": {"$gte": from_date},
                    "resolved_at": {"$ne": None}
                }},
                {"$project": {
                    "hours": {"$divide": [
                        {"$subtract": ["$resolved_at", "$created_at"]},
                        3600000  # ms to hours
                    ]}
                }},
                {"$group": {
                    "_id": None,
                    "avg_hours": {"$avg": "$hours"},
                    "sla_met": {"$sum": {"$cond": [{"$lte": ["$hours", 24]}, 1, 0]}},
                    "sla_breached": {"$sum": {"$cond": [{"$gt": ["$hours", 24]}, 1, 0]}}
                }}
            ],
            "top_assignees": [
                {"$match": {"created_at": {"$gte": from_date}, "assignee_id": {"$ne": None}}},
                {"$group": {"_id": "$assignee_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ]
        }}
    ]
    
    result = list(tickets_collection.aggregate(pipeline))
    facets = result[0] if result else {}
    
    def facet_count(key):
        v = facets.get(key, [])
        return v[0].get("count", 0) if v else 0
    
    # Priority breakdown
    priority_counts = {"urgent": 0, "high": 0, "medium": 0, "low": 0}
    for item in facets.get("priority_breakdown", []):
        if item["_id"] in priority_counts:
            priority_counts[item["_id"]] = item["count"]
    
    # Status breakdown
    status_counts = {"todo": 0, "in_progress": 0, "waiting": 0, "review": 0, "resolved": 0}
    for item in facets.get("status_breakdown", []):
        if item["_id"] in status_counts:
            status_counts[item["_id"]] = item["count"]
    
    # Volume trend
    volume_trend = [{"date": item["_id"], "count": item["count"]} for item in facets.get("volume_trend", [])]
    
    # Resolution times and SLA
    res_data = facets.get("resolution_times", [{}])
    res = res_data[0] if res_data else {}
    avg_resolution_hours = res.get("avg_hours")
    sla_met = res.get("sla_met", 0)
    sla_breached = res.get("sla_breached", 0)
    sla_compliance = (sla_met / (sla_met + sla_breached) * 100) if (sla_met + sla_breached) > 0 else None
    
    # Top assignees — batch-fetch user names
    top_raw = facets.get("top_assignees", [])
    assignee_ids = [a["_id"] for a in top_raw]
    user_map = {}
    if assignee_ids:
        for u in users_collection.find({"user_id": {"$in": assignee_ids}}, {"_id": 0, "user_id": 1, "name": 1}):
            user_map[u["user_id"]] = u.get("name", "Unknown")
    
    top_assignees = [
        {"user_id": a["_id"], "name": user_map.get(a["_id"], "Unknown"), "ticket_count": a["count"]}
        for a in top_raw
    ]
    
    return {
        "period_days": days,
        "summary": {
            "total_tickets": facet_count("total"),
            "open_tickets": facet_count("open"),
            "tickets_in_period": facet_count("in_period"),
            "resolved_in_period": facet_count("resolved_in_period"),
            "avg_resolution_hours": round(avg_resolution_hours, 1) if avg_resolution_hours else None,
            "sla_compliance_percent": round(sla_compliance, 1) if sla_compliance else None
        },
        "priority_breakdown": priority_counts,
        "status_breakdown": status_counts,
        "volume_trend": volume_trend,
        "top_assignees": top_assignees
    }

@app.get("/api/analytics/agents")
async def get_agent_analytics(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get per-agent performance analytics"""
    from_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get all tickets in range
    recent_tickets = list(tickets_collection.find({
        "created_at": {"$gte": from_date}
    }, {"_id": 0}))
    
    # Get all users
    users = {u["user_id"]: u for u in users_collection.find({}, {"_id": 0})}
    
    # Calculate per-agent stats
    agent_stats = {}
    for t in recent_tickets:
        assignee = t.get("assignee_id")
        if not assignee:
            continue
        
        if assignee not in agent_stats:
            user = users.get(assignee, {})
            agent_stats[assignee] = {
                "user_id": assignee,
                "name": user.get("name", "Unknown"),
                "email": user.get("email"),
                "tickets_assigned": 0,
                "tickets_resolved": 0,
                "resolution_times": [],
                "priorities": {"urgent": 0, "high": 0, "medium": 0, "low": 0}
            }
        
        agent_stats[assignee]["tickets_assigned"] += 1
        
        p = t.get("priority", "medium")
        if p in agent_stats[assignee]["priorities"]:
            agent_stats[assignee]["priorities"][p] += 1
        
        if t.get("status") in ["resolved", "closed"]:
            agent_stats[assignee]["tickets_resolved"] += 1
            
            if t.get("resolved_at") and t.get("created_at"):
                try:
                    created = datetime.fromisoformat(str(t["created_at"]).replace("Z", "+00:00"))
                    resolved = datetime.fromisoformat(str(t["resolved_at"]).replace("Z", "+00:00"))
                    agent_stats[assignee]["resolution_times"].append(
                        (resolved - created).total_seconds() / 3600
                    )
                except (ValueError, TypeError, KeyError):
                    pass
    
    # Calculate averages
    result = []
    for agent in agent_stats.values():
        avg_resolution = sum(agent["resolution_times"]) / len(agent["resolution_times"]) if agent["resolution_times"] else None
        result.append({
            "user_id": agent["user_id"],
            "name": agent["name"],
            "email": agent["email"],
            "tickets_assigned": agent["tickets_assigned"],
            "tickets_resolved": agent["tickets_resolved"],
            "resolution_rate": round(agent["tickets_resolved"] / agent["tickets_assigned"] * 100, 1) if agent["tickets_assigned"] > 0 else 0,
            "avg_resolution_hours": round(avg_resolution, 1) if avg_resolution else None,
            "priority_breakdown": agent["priorities"]
        })
    
    # Sort by tickets resolved
    result.sort(key=lambda x: -x["tickets_resolved"])
    
    return result


# canned_responses routes extracted to routes/canned_responses.py

# ==================== Bulk Operations ====================

@app.post("/api/tickets/bulk-update")
async def bulk_update_tickets(
    request: BulkUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Bulk update multiple tickets at once"""
    if not request.ticket_ids:
        raise HTTPException(status_code=400, detail="No ticket IDs provided")
    
    if len(request.ticket_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tickets per bulk operation")
    
    # Validate updates
    allowed_fields = {"status", "priority", "assignee_id", "team_id", "escalation_level"}
    update_fields = {k: v for k, v in request.updates.items() if k in allowed_fields}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid update fields provided")
    
    update_fields["updated_at"] = datetime.now(timezone.utc)
    
    # Perform bulk update
    result = tickets_collection.update_many(
        {"ticket_id": {"$in": request.ticket_ids}},
        {"$set": update_fields}
    )
    
    # Log to changelog for each ticket
    for ticket_id in request.ticket_ids:
        for field, new_value in update_fields.items():
            if field != "updated_at":
                ticket_changelog_collection.insert_one({
                    "changelog_id": f"cl_{uuid.uuid4().hex[:12]}",
                    "ticket_id": ticket_id,
                    "field": field,
                    "old_value": None,  # Unknown in bulk operation
                    "new_value": new_value,
                    "changed_by": current_user.get("user_id"),
                    "changed_by_name": current_user.get("name"),
                    "timestamp": datetime.now(timezone.utc),
                    "bulk_operation": True
                })
    
    return {
        "message": f"Updated {result.modified_count} tickets",
        "matched": result.matched_count,
        "modified": result.modified_count
    }

@app.post("/api/tickets/bulk-tag")
async def bulk_tag_tickets(
    request: BulkTagRequest,
    current_user: dict = Depends(get_current_user)
):
    """Bulk add or remove tags from multiple tickets"""
    if not request.ticket_ids:
        raise HTTPException(status_code=400, detail="No ticket IDs provided")
    
    if len(request.ticket_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tickets per bulk operation")
    
    modified_count = 0
    
    for ticket_id in request.ticket_ids:
        update_ops = {}
        
        if request.tags_to_add:
            update_ops["$addToSet"] = {"tags": {"$each": request.tags_to_add}}
        
        if request.tags_to_remove:
            update_ops["$pull"] = {"tags": {"$in": request.tags_to_remove}}
        
        if update_ops:
            # MongoDB doesn't allow $addToSet and $pull in same operation
            if request.tags_to_add:
                tickets_collection.update_one(
                    {"ticket_id": ticket_id},
                    {"$addToSet": {"tags": {"$each": request.tags_to_add}}}
                )
            if request.tags_to_remove:
                tickets_collection.update_one(
                    {"ticket_id": ticket_id},
                    {"$pull": {"tags": {"$in": request.tags_to_remove}}}
                )
            modified_count += 1
    
    return {
        "message": f"Updated tags for {modified_count} tickets",
        "tags_added": request.tags_to_add,
        "tags_removed": request.tags_to_remove
    }

@app.post("/api/tickets/bulk-close")
async def bulk_close_tickets(
    ticket_ids: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Bulk close multiple tickets"""
    if not ticket_ids:
        raise HTTPException(status_code=400, detail="No ticket IDs provided")
    
    if len(ticket_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tickets per bulk operation")
    
    now = datetime.now(timezone.utc)
    result = tickets_collection.update_many(
        {"ticket_id": {"$in": ticket_ids}},
        {"$set": {
            "status": "resolved",
            "resolved_at": now,
            "updated_at": now
        }}
    )
    
    return {
        "message": f"Closed {result.modified_count} tickets",
        "modified": result.modified_count
    }




# customers routes extracted to routes/customers.py

# csat routes extracted to routes/csat.py

# ==================== Search API ====================

@app.get("/api/search")
async def search(
    q: str,
    limit: int = 10,
    type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Comprehensive search across ALL entities.
    
    Supports operators:
    - status:open, status:closed
    - priority:urgent, priority:high
    - assigned:me, assigned:none, assigned:@username
    - team:teamname
    - tag:tagname
    - created:today, created:last-week, created:2024-01-15
    - customer:email@domain.com
    - domain:acme.com
    - escalation:L1, escalation:L2
    - type:ticket, type:user, type:team
    
    Example: /api/search?q=billing status:open priority:urgent
    """
    if not q or len(q) < 1:
        return {"results": [], "total": 0, "by_category": {}, "operators": {}, "tickets": []}
    
    results = search_engine.search_all(
        q, 
        limit_per_category=limit,
        current_user_id=current_user.get("user_id"),
        type_filter=type
    )
    # Add top-level tickets for backward compatibility with merge/link modals
    results["tickets"] = results.get("by_category", {}).get("tickets", [])
    return results

@app.get("/api/search/suggestions")
async def search_suggestions(
    q: str,
    current_user: dict = Depends(get_current_user)
):
    """Get autocomplete suggestions for search"""
    if not q:
        return {"suggestions": []}
    
    suggestions = search_engine.get_search_suggestions(q)
    return {"suggestions": suggestions}

@app.post("/api/search")
async def search_post(
    search_query: SearchQuery,
    current_user: dict = Depends(get_current_user)
):
    """Search with POST (for complex queries)"""
    results = search_engine.search_all(
        search_query.query, 
        limit_per_category=search_query.limit_per_category,
        current_user_id=current_user.get("user_id"),
        type_filter=search_query.type_filter
    )
    return results


# ==================== Real-time Presence API ====================

@app.get("/api/presence/stats")
async def get_presence_statistics(
    current_user: dict = Depends(get_current_user)
):
    """Get real-time presence statistics"""
    return await get_presence_stats()

@app.get("/api/presence/ticket/{ticket_id}")
async def get_ticket_viewers(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get users currently viewing a specific ticket"""
    viewers = await get_users_viewing_ticket(ticket_id)
    return {
        "ticket_id": ticket_id,
        "viewers": viewers,
        "count": len(viewers)
    }


# ==================== Health Check ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": {
            "realtime": True,
            "search": True,
            "leave_management": True
        }
    }


# ==================== Leave Management API ====================

leave_manager = get_leave_manager(db)

@app.post("/api/leaves")
async def create_leave(
    leave_data: LeaveRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Create a new leave entry (auto-approved)"""
    # Allow creating leave for self or others (minimal friction)
    if not leave_data.user_id:
        leave_data.user_id = current_user.get("user_id")
    
    leave = await leave_manager.create_leave(leave_data)
    
    # Broadcast to connected clients
    background_tasks.add_task(
        broadcast_leave_created,
        leave,
        {"user_id": current_user.get("user_id"), "name": current_user.get("name")}
    )
    
    return leave

@app.get("/api/leaves")
async def get_leaves(
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    leave_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get leaves with optional filters"""
    leaves = await leave_manager.get_leaves(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        leave_type=leave_type
    )
    return leaves

@app.get("/api/leaves/types")
async def get_leave_types(
    current_user: dict = Depends(get_current_user)
):
    """Get all available leave types"""
    types = await leave_manager.get_leave_types()
    return {"types": types}

@app.get("/api/leaves/calendar/{year}/{month}")
async def get_team_calendar(
    year: int,
    month: int,
    current_user: dict = Depends(get_current_user)
):
    """Get team calendar for a month"""
    calendar = await leave_manager.get_team_calendar(year, month)
    return {"year": year, "month": month, "days": calendar}

@app.get("/api/leaves/conflicts")
async def check_leave_conflicts(
    start_date: str,
    end_date: str,
    exclude_user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Check for leave conflicts on given dates"""
    conflicts = await leave_manager.check_conflicts(start_date, end_date, exclude_user_id)
    return conflicts

@app.get("/api/leaves/summary/{user_id}")
async def get_user_leave_summary(
    user_id: str,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get leave summary for a user"""
    summary = await leave_manager.get_user_leave_summary(user_id, year)
    return summary

@app.get("/api/leaves/{leave_id}")
async def get_leave(
    leave_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific leave entry"""
    leave = await leave_manager.get_leave(leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    return leave

@app.put("/api/leaves/{leave_id}")
async def update_leave(
    leave_id: str,
    update_data: LeaveUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Update a leave entry (admin can edit/deny)"""
    leave = await leave_manager.update_leave(leave_id, update_data)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    
    # Broadcast update
    background_tasks.add_task(
        broadcast_leave_updated,
        leave_id,
        leave,
        {"user_id": current_user.get("user_id"), "name": current_user.get("name")}
    )
    
    return leave

@app.delete("/api/leaves/{leave_id}")
async def delete_leave(
    leave_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Delete a leave entry"""
    deleted = await leave_manager.delete_leave(leave_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Leave not found")
    
    # Broadcast deletion
    background_tasks.add_task(
        broadcast_leave_deleted,
        leave_id,
        {"user_id": current_user.get("user_id"), "name": current_user.get("name")}
    )
    
    return {"message": "Leave deleted successfully"}


# ==================== Ticket Merge/Link/Split APIs ====================

@app.post("/api/tickets/{ticket_id}/merge")
async def merge_tickets(
    ticket_id: str,
    merge_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Merge this ticket into another ticket with full conversation consolidation"""
    target_ticket_id = merge_data.get("target_ticket_id")
    if not target_ticket_id:
        raise HTTPException(status_code=400, detail="Target ticket ID required")
    
    # Get both tickets
    source_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    target_ticket = tickets_collection.find_one({"ticket_id": target_ticket_id}, {"_id": 0})
    
    if not source_ticket:
        raise HTTPException(status_code=404, detail="Source ticket not found")
    if not target_ticket:
        raise HTTPException(status_code=404, detail="Target ticket not found")
    
    merge_timestamp = datetime.now(timezone.utc)
    
    # Determine the color index for this merge (cycle through 0-4)
    existing_merged = target_ticket.get("merged_tickets", [])
    color_index = len(existing_merged) % 5
    
    # Get the earliest timestamp from the source ticket for proper timeline ordering
    # The merge divider should appear BEFORE the source ticket's messages
    source_created_at = source_ticket.get("created_at", merge_timestamp)
    if isinstance(source_created_at, str):
        source_created_at = datetime.fromisoformat(source_created_at.replace("Z", "+00:00"))
    # Subtract 1 second so divider appears just before the first message
    divider_timestamp = source_created_at - timedelta(seconds=1)
    
    # Update existing messages: move to target ticket with merge metadata
    messages_collection.update_many(
        {"ticket_id": ticket_id},
        {"$set": {
            "ticket_id": target_ticket_id,
            "original_ticket_id": ticket_id,
            "merged_at": merge_timestamp,
            "merge_color_index": color_index
        }}
    )
    
    # Create a message from the source ticket's original content
    # This preserves the original ticket's description in the conversation
    if source_ticket.get("description"):
        original_content_msg = {
            "message_id": f"msg_{uuid4().hex[:12]}",
            "ticket_id": target_ticket_id,
            "type": "customer_reply",  # Treat as customer message for display
            "content": source_ticket.get("description", ""),
            "text": source_ticket.get("description", ""),
            "author_name": source_ticket.get("customer_name") or source_ticket.get("created_by_name") or "Customer",
            "author_email": source_ticket.get("customer_email"),
            "original_ticket_id": ticket_id,
            "merged_at": merge_timestamp,
            "merge_color_index": color_index,
            "merged_ticket_title": source_ticket.get("title", "Untitled"),
            "created_by": source_ticket.get("created_by", "import"),
            "created_at": source_ticket.get("created_at", merge_timestamp)
        }
        messages_collection.insert_one(original_content_msg)
    
    # Add a merge divider (visual separator showing the start of merged ticket messages)
    # Timestamp is set to just BEFORE the source ticket's creation so it appears first in timeline
    merge_note = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": target_ticket_id,
        "type": "merge_divider",
        "text": f"Merged from {ticket_id}: {source_ticket.get('title', 'Untitled')}",
        "original_ticket_id": ticket_id,
        "merged_ticket_title": source_ticket.get("title", "Untitled"),
        "merge_color_index": color_index,
        "created_by": current_user["user_id"],
        "created_at": divider_timestamp  # Use earlier timestamp so divider appears before messages
    }
    messages_collection.insert_one(merge_note)
    
    # Build merged ticket reference
    merged_ticket_ref = {
        "ticket_id": ticket_id,
        "original_title": source_ticket.get("title", "Untitled"),
        "merged_at": merge_timestamp,
        "merged_by": current_user["user_id"],
        "color_index": color_index,
        "message_count": messages_collection.count_documents({"original_ticket_id": ticket_id}),
        "original_status": source_ticket.get("status"),
        "original_priority": source_ticket.get("priority"),
        "original_customer_email": source_ticket.get("customer_email"),
    }
    
    # Collect all search identifiers from source
    source_identifiers = [ticket_id]
    if source_ticket.get("external_id"):
        source_identifiers.append(source_ticket["external_id"])
    if source_ticket.get("uuid"):
        source_identifiers.append(source_ticket["uuid"])
    # Include any identifiers source already had from previous merges
    source_identifiers.extend(source_ticket.get("search_identifiers", []))
    
    # Collect associated emails
    source_emails = []
    if source_ticket.get("customer_email"):
        source_emails.append(source_ticket["customer_email"])
    source_emails.extend(source_ticket.get("associated_emails", []))
    
    # Collect tags
    source_tags = source_ticket.get("tags", [])
    target_tags = target_ticket.get("tags", [])
    combined_tags = list(set(target_tags + source_tags))
    
    # Update target ticket with merged info
    existing_identifiers = target_ticket.get("search_identifiers", [target_ticket_id])
    existing_emails = target_ticket.get("associated_emails", [])
    if target_ticket.get("customer_email") and target_ticket["customer_email"] not in existing_emails:
        existing_emails.append(target_ticket["customer_email"])
    
    tickets_collection.update_one(
        {"ticket_id": target_ticket_id},
        {
            "$push": {"merged_tickets": merged_ticket_ref},
            "$set": {
                "search_identifiers": list(set(existing_identifiers + source_identifiers)),
                "associated_emails": list(set(existing_emails + source_emails)),
                "tags": combined_tags,
                "updated_at": merge_timestamp
            }
        }
    )
    
    # Mark source ticket as merged (soft delete but keep for unmerge)
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {
            "status": "merged",
            "merged_into": target_ticket_id,
            "merged_at": merge_timestamp,
            "merged_by": current_user["user_id"],
            "pre_merge_status": source_ticket.get("status", "todo")
        }}
    )
    
    # Log the change
    log_ticket_change(ticket_id, source_ticket.get("uuid", ""), "merge", None, target_ticket_id, current_user["user_id"], "merge")
    
    return {
        "message": f"Ticket {ticket_id} merged into {target_ticket_id}",
        "merged_ticket": merged_ticket_ref,
        "total_merged": len(existing_merged) + 1
    }


@app.post("/api/tickets/{ticket_id}/unmerge/{source_ticket_id}")
async def unmerge_ticket(
    ticket_id: str,
    source_ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unmerge a previously merged ticket, restoring it as a separate ticket"""
    # Get the parent ticket
    parent_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not parent_ticket:
        raise HTTPException(status_code=404, detail="Parent ticket not found")
    
    # Check if source_ticket_id is in merged_tickets
    merged_tickets = parent_ticket.get("merged_tickets", [])
    merged_ref = next((m for m in merged_tickets if m["ticket_id"] == source_ticket_id), None)
    
    if not merged_ref:
        raise HTTPException(status_code=400, detail=f"Ticket {source_ticket_id} was not merged into {ticket_id}")
    
    # Get the source ticket
    source_ticket = tickets_collection.find_one({"ticket_id": source_ticket_id}, {"_id": 0})
    if not source_ticket:
        raise HTTPException(status_code=404, detail="Merged ticket record not found")
    
    unmerge_timestamp = datetime.now(timezone.utc)
    
    # Move messages back to source ticket
    messages_collection.update_many(
        {"ticket_id": ticket_id, "original_ticket_id": source_ticket_id},
        {
            "$set": {"ticket_id": source_ticket_id},
            "$unset": {"original_ticket_id": "", "merged_at": "", "merge_color_index": ""}
        }
    )
    
    # Remove merge divider message
    messages_collection.delete_many({
        "ticket_id": ticket_id,
        "type": "merge_divider",
        "original_ticket_id": source_ticket_id
    })
    
    # Remove from merged_tickets array
    updated_merged = [m for m in merged_tickets if m["ticket_id"] != source_ticket_id]
    
    # Rebuild search_identifiers (remove source's identifiers)
    source_identifiers = [source_ticket_id]
    if source_ticket.get("external_id"):
        source_identifiers.append(source_ticket["external_id"])
    if source_ticket.get("uuid"):
        source_identifiers.append(source_ticket["uuid"])
    
    current_identifiers = parent_ticket.get("search_identifiers", [])
    updated_identifiers = [i for i in current_identifiers if i not in source_identifiers]
    
    # Rebuild associated_emails
    source_email = source_ticket.get("customer_email")
    current_emails = parent_ticket.get("associated_emails", [])
    updated_emails = [e for e in current_emails if e != source_email] if source_email else current_emails
    
    # Update parent ticket
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$set": {
                "merged_tickets": updated_merged,
                "search_identifiers": updated_identifiers,
                "associated_emails": updated_emails,
                "updated_at": unmerge_timestamp
            }
        }
    )
    
    # Restore source ticket
    restore_status = source_ticket.get("pre_merge_status", "todo")
    tickets_collection.update_one(
        {"ticket_id": source_ticket_id},
        {
            "$set": {
                "status": restore_status,
                "updated_at": unmerge_timestamp
            },
            "$unset": {
                "merged_into": "",
                "merged_at": "",
                "merged_by": "",
                "pre_merge_status": ""
            }
        }
    )
    
    # Add system note to both tickets
    unmerge_note_parent = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "type": "system",
        "text": f"Unmerged ticket {source_ticket_id}: {merged_ref.get('original_title', 'Untitled')}",
        "created_by": current_user["user_id"],
        "created_at": unmerge_timestamp
    }
    messages_collection.insert_one(unmerge_note_parent)
    
    unmerge_note_source = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": source_ticket_id,
        "type": "system",
        "text": f"Unmerged from ticket {ticket_id}",
        "created_by": current_user["user_id"],
        "created_at": unmerge_timestamp
    }
    messages_collection.insert_one(unmerge_note_source)
    
    # Log the change
    log_ticket_change(source_ticket_id, source_ticket.get("uuid", ""), "unmerge", ticket_id, None, current_user["user_id"], "unmerge")
    
    return {
        "message": f"Ticket {source_ticket_id} unmerged from {ticket_id}",
        "restored_ticket_id": source_ticket_id,
        "restored_status": restore_status,
        "remaining_merged": len(updated_merged)
    }


@app.get("/api/tickets/{ticket_id}/merge-suggestions")
async def get_merge_suggestions(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get auto-merge suggestions for a ticket based on same customer email within 2 hours"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    customer_email = ticket.get("customer_email")
    if not customer_email:
        return {"suggestions": []}
    
    ticket_created = ticket.get("created_at")
    if isinstance(ticket_created, str):
        ticket_created = datetime.fromisoformat(ticket_created.replace("Z", "+00:00"))
    
    # Find other open tickets from same customer within 2 hours
    two_hours_before = ticket_created - timedelta(hours=2)
    two_hours_after = ticket_created + timedelta(hours=2)
    
    suggestions = list(tickets_collection.find({
        "ticket_id": {"$ne": ticket_id},
        "customer_email": customer_email,
        "status": {"$nin": ["merged", "closed", "resolved"]},
        "created_at": {
            "$gte": two_hours_before,
            "$lte": two_hours_after
        }
    }, {"_id": 0, "ticket_id": 1, "title": 1, "status": 1, "created_at": 1, "priority": 1}))
    
    return {
        "suggestions": [serialize_doc(s) for s in suggestions],
        "rule": "Same customer email within 2 hours"
    }


@app.post("/api/tickets/{ticket_id}/link")
async def link_tickets(
    ticket_id: str,
    link_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Link this ticket to another ticket"""
    target_ticket_id = link_data.get("target_ticket_id")
    link_type = link_data.get("link_type", "related")  # related, blocks, blocked_by, duplicates
    
    if not target_ticket_id:
        raise HTTPException(status_code=400, detail="Target ticket ID required")
    
    # Get both tickets
    source_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    target_ticket = tickets_collection.find_one({"ticket_id": target_ticket_id}, {"_id": 0})
    
    if not source_ticket:
        raise HTTPException(status_code=404, detail="Source ticket not found")
    if not target_ticket:
        raise HTTPException(status_code=404, detail="Target ticket not found")
    
    # Add link to source ticket
    link_entry = {
        "ticket_id": target_ticket_id,
        "title": target_ticket.get("title"),
        "link_type": link_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$addToSet": {"linked_tickets": link_entry}}
    )
    
    # Add reverse link to target
    reverse_type = link_type
    if link_type == "blocks":
        reverse_type = "blocked_by"
    elif link_type == "blocked_by":
        reverse_type = "blocks"
    
    reverse_entry = {
        "ticket_id": ticket_id,
        "title": source_ticket.get("title"),
        "link_type": reverse_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    tickets_collection.update_one(
        {"ticket_id": target_ticket_id},
        {"$addToSet": {"linked_tickets": reverse_entry}}
    )
    
    # Return updated ticket
    updated_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    return serialize_doc(updated_ticket)


@app.delete("/api/tickets/{ticket_id}/unlink/{target_ticket_id}")
async def unlink_tickets(
    ticket_id: str,
    target_ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove link between two tickets"""
    # Remove link from source
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$pull": {"linked_tickets": {"ticket_id": target_ticket_id}}}
    )
    
    # Remove link from target
    tickets_collection.update_one(
        {"ticket_id": target_ticket_id},
        {"$pull": {"linked_tickets": {"ticket_id": ticket_id}}}
    )
    
    return {"message": "Tickets unlinked"}


@app.post("/api/tickets/{ticket_id}/split")
async def split_ticket(
    ticket_id: str,
    split_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Split a ticket at a specific message index"""
    split_at_index = split_data.get("split_at_index")
    new_ticket_title = split_data.get("new_ticket_title")
    
    if split_at_index is None:
        raise HTTPException(status_code=400, detail="Split index required")
    
    # Get original ticket
    original_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not original_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get all messages for this ticket
    messages = list(messages_collection.find({"ticket_id": ticket_id}, {"_id": 0}).sort("created_at", ASCENDING))
    
    if split_at_index <= 0 or split_at_index > len(messages):
        raise HTTPException(status_code=400, detail="Invalid split index")
    
    # Create new ticket - assign to the person who performed the split
    new_ticket_id = generate_ticket_id()
    new_uuid = str(uuid4())
    split_timestamp = datetime.now(timezone.utc)
    
    new_ticket = {
        "ticket_id": new_ticket_id,
        "uuid": new_uuid,
        "title": new_ticket_title or f"Split from {ticket_id}",
        "description": f"This ticket was split from {ticket_id}",
        "status": original_ticket.get("status", "todo"),
        "assignee_id": current_user["user_id"],  # Assign to who performed the split
        "priority": original_ticket.get("priority", "medium"),
        "escalation_level": original_ticket.get("escalation_level", "L1"),
        "customer_email": original_ticket.get("customer_email"),
        "customer_name": original_ticket.get("customer_name"),
        "domain": original_ticket.get("domain"),
        "tags": original_ticket.get("tags", []),
        "created_by": current_user["user_id"],
        "created_at": split_timestamp,
        "updated_at": split_timestamp,
        "split_from": ticket_id,
        "is_starred": False,
        "snoozed": False,
        # Auto-link back to original ticket
        "linked_tickets": [{
            "ticket_id": ticket_id,
            "title": original_ticket.get("title"),
            "link_type": "split_from",
            "created_at": split_timestamp.isoformat()
        }]
    }
    
    tickets_collection.insert_one(new_ticket)
    
    # Add link from original ticket to new ticket
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$addToSet": {"linked_tickets": {
            "ticket_id": new_ticket_id,
            "title": new_ticket.get("title"),
            "link_type": "split_to",
            "created_at": split_timestamp.isoformat()
        }}}
    )
    
    # Move messages after split point to new ticket
    messages_to_move = [m.get("message_id") for m in messages[split_at_index:]]
    if messages_to_move:
        messages_collection.update_many(
            {"message_id": {"$in": messages_to_move}},
            {"$set": {"ticket_id": new_ticket_id, "split_from": ticket_id}}
        )
    
    # Add system notes to both tickets
    split_note_original = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "type": "system",
        "text": f"Ticket split. {len(messages_to_move)} message(s) moved to {new_ticket_id}",
        "created_by": current_user["user_id"],
        "created_at": split_timestamp
    }
    messages_collection.insert_one(split_note_original)
    
    split_note_new = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": new_ticket_id,
        "type": "system",
        "text": f"This ticket was split from {ticket_id}",
        "created_by": current_user["user_id"],
        "created_at": split_timestamp
    }
    messages_collection.insert_one(split_note_new)
    
    # Log the change
    log_ticket_change(ticket_id, original_ticket.get("uuid", ""), "split", None, new_ticket_id, current_user["user_id"], "split")
    
    # Get updated original ticket for response
    updated_original = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    
    return {
        "message": "Ticket split successfully",
        "new_ticket_id": new_ticket_id,
        "messages_moved": len(messages_to_move),
        "updated_ticket": serialize_doc(updated_original) if updated_original else None
    }


# ==================== Feature Requests APIs ====================

@app.get("/api/feature-requests")
async def get_feature_requests(
    status: Optional[str] = None,
    request_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all feature requests"""
    query = {}
    if status:
        query["status"] = status
    if request_type:
        query["request_type"] = request_type
    
    requests = list(feature_requests_collection.find(query, {"_id": 0}).sort("mentions_count", DESCENDING))
    return [serialize_doc(r) for r in requests]

@app.post("/api/feature-requests")
async def create_feature_request(
    data: FeatureRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new feature request"""
    feature_request_id = f"FR-{str(uuid4().hex[:8]).upper()}"
    
    feature_request = {
        "feature_request_id": feature_request_id,
        "title": data.title,
        "description": data.description or "",
        "request_type": data.request_type,
        "priority": data.priority or "medium",
        "status": "new",
        "mentions_count": 1 if data.linked_ticket_id else 0,
        "linked_tickets": [data.linked_ticket_id] if data.linked_ticket_id else [],
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    feature_requests_collection.insert_one(feature_request)
    
    # If linked_ticket_id provided, update the ticket to add to its feature_request_ids array
    if data.linked_ticket_id:
        tickets_collection.update_one(
            {"ticket_id": data.linked_ticket_id},
            {"$addToSet": {"feature_request_ids": feature_request_id}}
        )
    
    return serialize_doc(feature_request)

@app.get("/api/feature-requests/{feature_request_id}")
async def get_feature_request(
    feature_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific feature request with linked tickets"""
    fr = feature_requests_collection.find_one({"feature_request_id": feature_request_id}, {"_id": 0})
    if not fr:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    # Get linked tickets details
    linked_tickets = []
    if fr.get("linked_tickets"):
        tickets = list(tickets_collection.find(
            {"ticket_id": {"$in": fr["linked_tickets"]}},
            {"_id": 0, "ticket_id": 1, "title": 1, "status": 1, "customer_email": 1, "created_at": 1}
        ))
        linked_tickets = [serialize_doc(t) for t in tickets]
    
    result = serialize_doc(fr)
    result["linked_ticket_details"] = linked_tickets
    return result

@app.put("/api/feature-requests/{feature_request_id}")
async def update_feature_request(
    feature_request_id: str,
    data: FeatureRequestUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a feature request"""
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    result = feature_requests_collection.update_one(
        {"feature_request_id": feature_request_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    fr = feature_requests_collection.find_one({"feature_request_id": feature_request_id}, {"_id": 0})
    return serialize_doc(fr)

@app.post("/api/tickets/{ticket_id}/feature-request")
async def link_ticket_to_feature_request(
    ticket_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Link a ticket to a feature request (supports multiple links)"""
    feature_request_id = data.get("feature_request_id")
    if not feature_request_id:
        raise HTTPException(status_code=400, detail="Feature request ID required")
    
    # Verify ticket exists
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Verify feature request exists
    fr = feature_requests_collection.find_one({"feature_request_id": feature_request_id}, {"_id": 0})
    if not fr:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    # Check if already linked
    current_links = ticket.get("feature_request_ids", [])
    if feature_request_id in current_links:
        return {"message": "Ticket already linked to this feature request"}
    
    # Add ticket to feature request's linked_tickets
    feature_requests_collection.update_one(
        {"feature_request_id": feature_request_id},
        {
            "$addToSet": {"linked_tickets": ticket_id},
            "$inc": {"mentions_count": 1}
        }
    )
    
    # Add feature request to ticket's feature_request_ids array
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$addToSet": {"feature_request_ids": feature_request_id}}
    )
    
    return {"message": "Ticket linked to feature request"}


@app.delete("/api/tickets/{ticket_id}/feature-request/{feature_request_id}")
async def unlink_ticket_from_feature_request(
    ticket_id: str,
    feature_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unlink a ticket from a feature request"""
    # Remove ticket from feature request's linked_tickets
    feature_requests_collection.update_one(
        {"feature_request_id": feature_request_id},
        {
            "$pull": {"linked_tickets": ticket_id},
            "$inc": {"mentions_count": -1}
        }
    )
    
    # Remove feature request from ticket's feature_request_ids array
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$pull": {"feature_request_ids": feature_request_id}}
    )
    
    return {"message": "Ticket unlinked from feature request"}


@app.get("/api/tickets/{ticket_id}/feature-requests")
async def get_ticket_feature_requests(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all feature requests linked to a ticket"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    feature_request_ids = ticket.get("feature_request_ids", [])
    
    # Also check legacy single feature_request_id field
    legacy_fr_id = ticket.get("feature_request_id")
    if legacy_fr_id and legacy_fr_id not in feature_request_ids:
        feature_request_ids.append(legacy_fr_id)
    
    if not feature_request_ids:
        return []
    
    feature_requests = list(feature_requests_collection.find(
        {"feature_request_id": {"$in": feature_request_ids}},
        {"_id": 0}
    ))
    
    return [serialize_doc(fr) for fr in feature_requests]


# ==================== Data Export System ====================

from fastapi.responses import StreamingResponse

def serialize_for_export(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if key == '_id':
            continue
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, list):
            result[key] = [serialize_for_export(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):
            result[key] = serialize_for_export(value)
        else:
            result[key] = value
    return result

@app.post("/api/admin/export/tickets")
async def admin_export_tickets(
    request: ExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """Export all tickets with metadata"""
    
    # Build query
    query = {}
    
    # Date filter
    if request.date_from or request.date_to:
        date_query = {}
        if request.date_from:
            try:
                from_date = datetime.fromisoformat(request.date_from.replace("Z", "+00:00"))
                date_query["$gte"] = from_date
            except ValueError:
                pass
        if request.date_to:
            try:
                to_date = datetime.fromisoformat(request.date_to.replace("Z", "+00:00"))
                date_query["$lte"] = to_date
            except ValueError:
                pass
        if date_query:
            query["created_at"] = date_query
    
    # Status filter
    if request.status_filter:
        query["status"] = {"$in": request.status_filter}
    
    # Fetch tickets
    tickets = list(tickets_collection.find(query, {"_id": 0}))
    
    # Enrich with related data
    export_data = []
    for ticket in tickets:
        ticket_export = serialize_for_export(ticket)
        ticket_id = ticket.get("ticket_id")
        
        # Add notes/replies
        if request.include_notes:
            notes = list(messages_collection.find(
                {"ticket_id": ticket_id}, {"_id": 0}
            ))
            ticket_export["notes"] = [serialize_for_export(n) for n in notes]
        
        # Add changelog
        if request.include_changelog:
            changelog = list(ticket_changelog_collection.find(
                {"ticket_id": ticket_id}, {"_id": 0}
            ).sort("timestamp", -1))
            ticket_export["changelog"] = [serialize_for_export(c) for c in changelog]
        
        # Add CSAT
        if request.include_csat:
            csat = csat_responses_collection.find_one(
                {"ticket_id": ticket_id}, {"_id": 0}
            )
            ticket_export["csat"] = serialize_for_export(csat) if csat else None
        
        export_data.append(ticket_export)
    
    # Generate export
    if request.format == "csv":
        return generate_csv_export(export_data, "tickets")
    else:
        return generate_json_export(export_data, "tickets")


@app.post("/api/admin/export/full")
async def export_full_data(
    request: ExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """Export complete system data"""
    
    export_data = {
        "export_info": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": current_user.get("email"),
            "format": request.format
        },
        "tickets": [],
        "users": [],
        "teams": [],
        "customers": [],
        "feature_requests": [],
        "sla_policies": [],
        "routing_rules": [],
        "templates": [],
        "custom_fields": [],
        "csat_responses": [],
        "leaves": []
    }
    
    # Tickets with all metadata
    tickets = list(tickets_collection.find({}, {"_id": 0}))
    for ticket in tickets:
        ticket_export = serialize_for_export(ticket)
        ticket_id = ticket.get("ticket_id")
        
        if request.include_notes:
            notes = list(messages_collection.find({"ticket_id": ticket_id}, {"_id": 0}))
            ticket_export["notes"] = [serialize_for_export(n) for n in notes]
        
        if request.include_changelog:
            changelog = list(ticket_changelog_collection.find({"ticket_id": ticket_id}, {"_id": 0}))
            ticket_export["changelog"] = [serialize_for_export(c) for c in changelog]
        
        export_data["tickets"].append(ticket_export)
    
    # Users
    users = list(users_collection.find({}, {"_id": 0, "password_hash": 0}))
    export_data["users"] = [serialize_for_export(u) for u in users]
    
    # Teams
    teams = list(teams_collection.find({}, {"_id": 0}))
    export_data["teams"] = [serialize_for_export(t) for t in teams]
    
    # Customers (aggregated from tickets)
    customers_agg = tickets_collection.aggregate([
        {"$match": {"customer_email": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": "$customer_email",
            "name": {"$first": "$customer_name"},
            "domain": {"$first": "$domain"},
            "ticket_count": {"$sum": 1},
            "first_ticket": {"$min": "$created_at"},
            "last_ticket": {"$max": "$created_at"}
        }}
    ])
    export_data["customers"] = [serialize_for_export({
        "email": c["_id"],
        "name": c.get("name"),
        "domain": c.get("domain"),
        "ticket_count": c.get("ticket_count"),
        "first_ticket": c.get("first_ticket"),
        "last_ticket": c.get("last_ticket")
    }) for c in customers_agg]
    
    # Feature Requests
    feature_requests = list(feature_requests_collection.find({}, {"_id": 0}))
    export_data["feature_requests"] = [serialize_for_export(fr) for fr in feature_requests]
    
    # SLA Policies
    sla_policies = list(sla_policies_collection.find({}, {"_id": 0}))
    export_data["sla_policies"] = [serialize_for_export(p) for p in sla_policies]
    
    # Routing Rules
    routing_rules = list(routing_rules_collection.find({}, {"_id": 0}))
    export_data["routing_rules"] = [serialize_for_export(r) for r in routing_rules]
    
    # Canned Responses
    canned_responses = list(canned_responses_collection.find({}, {"_id": 0}))
    export_data["canned_responses"] = [serialize_for_export(cr) for cr in canned_responses]
    
    # Custom Fields
    custom_fields = list(custom_fields_collection.find({}, {"_id": 0}))
    export_data["custom_fields"] = [serialize_for_export(cf) for cf in custom_fields]
    
    # CSAT Responses
    if request.include_csat:
        csat_responses = list(csat_responses_collection.find({}, {"_id": 0}))
        export_data["csat_responses"] = [serialize_for_export(c) for c in csat_responses]
    
    # Leaves - directly access the collection
    leaves = list(db.leaves.find({}, {"_id": 0}))
    export_data["leaves"] = [serialize_for_export(leave) for leave in leaves]
    
    # Generate export
    if request.format == "csv":
        # For full export, CSV will be a zip of multiple CSVs
        return generate_json_export(export_data, "full_export")
    else:
        return generate_json_export(export_data, "full_export")


@app.get("/api/admin/export/customers")
async def export_customers(
    format: str = "json",
    current_user: dict = Depends(get_current_user)
):
    """Export customer data with ticket history summary"""
    
    # Aggregate customer data
    pipeline = [
        {"$match": {"customer_email": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": "$customer_email",
            "name": {"$first": "$customer_name"},
            "domain": {"$first": "$domain"},
            "ticket_count": {"$sum": 1},
            "open_tickets": {"$sum": {"$cond": [{"$nin": ["$status", ["resolved", "closed"]]}, 1, 0]}},
            "resolved_tickets": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}},
            "first_contact": {"$min": "$created_at"},
            "last_contact": {"$max": "$created_at"},
            "priorities": {"$push": "$priority"},
            "tags": {"$push": "$tags"}
        }},
        {"$sort": {"ticket_count": -1}}
    ]
    
    customers = list(tickets_collection.aggregate(pipeline))
    
    export_data = []
    for c in customers:
        # Flatten tags
        all_tags = []
        for tag_list in c.get("tags", []):
            if tag_list:
                all_tags.extend(tag_list)
        unique_tags = list(set(all_tags))
        
        # Count priorities
        priorities = c.get("priorities", [])
        priority_counts = {
            "urgent": priorities.count("urgent"),
            "high": priorities.count("high"),
            "medium": priorities.count("medium"),
            "low": priorities.count("low")
        }
        
        export_data.append(serialize_for_export({
            "email": c["_id"],
            "name": c.get("name"),
            "domain": c.get("domain"),
            "ticket_count": c.get("ticket_count", 0),
            "open_tickets": c.get("open_tickets", 0),
            "resolved_tickets": c.get("resolved_tickets", 0),
            "first_contact": c.get("first_contact"),
            "last_contact": c.get("last_contact"),
            "priority_breakdown": priority_counts,
            "tags": unique_tags
        }))
    
    if format == "csv":
        return generate_csv_export(export_data, "customers")
    else:
        return generate_json_export(export_data, "customers")


@app.get("/api/admin/export/analytics")
async def export_analytics(
    days: int = 30,
    format: str = "json",
    current_user: dict = Depends(get_current_user)
):
    """Export analytics data"""
    from_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Ticket metrics by day
    pipeline = [
        {"$match": {"created_at": {"$gte": from_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "tickets_created": {"$sum": 1},
            "resolved": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}},
            "urgent": {"$sum": {"$cond": [{"$eq": ["$priority", "urgent"]}, 1, 0]}},
            "high": {"$sum": {"$cond": [{"$eq": ["$priority", "high"]}, 1, 0]}}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    daily_metrics = list(tickets_collection.aggregate(pipeline))
    
    # Agent metrics
    agent_pipeline = [
        {"$match": {"created_at": {"$gte": from_date}, "assignee_id": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": "$assignee_id",
            "assigned": {"$sum": 1},
            "resolved": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}}
        }}
    ]
    
    agent_metrics = list(tickets_collection.aggregate(agent_pipeline))
    
    # Enrich with user names
    for agent in agent_metrics:
        user = users_collection.find_one({"user_id": agent["_id"]}, {"_id": 0, "name": 1, "email": 1})
        agent["name"] = user.get("name") if user else "Unknown"
        agent["email"] = user.get("email") if user else None
    
    # CSAT metrics
    csat_metrics = list(csat_responses_collection.aggregate([
        {"$match": {"created_at": {"$gte": from_date}}},
        {"$group": {
            "_id": None,
            "total_responses": {"$sum": 1},
            "avg_rating": {"$avg": "$rating"},
            "five_star": {"$sum": {"$cond": [{"$eq": ["$rating", 5]}, 1, 0]}},
            "four_star": {"$sum": {"$cond": [{"$eq": ["$rating", 4]}, 1, 0]}},
            "three_star": {"$sum": {"$cond": [{"$eq": ["$rating", 3]}, 1, 0]}},
            "two_star": {"$sum": {"$cond": [{"$eq": ["$rating", 2]}, 1, 0]}},
            "one_star": {"$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}}
        }}
    ]))
    
    export_data = {
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "daily_metrics": [serialize_for_export({"date": d["_id"], **d}) for d in daily_metrics],
        "agent_metrics": [serialize_for_export(a) for a in agent_metrics],
        "csat_metrics": serialize_for_export(csat_metrics[0]) if csat_metrics else None
    }
    
    if format == "csv":
        # For analytics, export daily metrics as CSV
        return generate_csv_export(export_data["daily_metrics"], "analytics_daily")
    else:
        return generate_json_export(export_data, "analytics")


def generate_json_export(data, filename_prefix):
    """Generate JSON file download response"""
    json_str = json.dumps(data, indent=2, default=str)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    
    return StreamingResponse(
        io.StringIO(json_str),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


def generate_csv_export(data, filename_prefix):
    """Generate CSV file download response"""
    if not data:
        return StreamingResponse(
            io.StringIO("No data to export"),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_prefix}_empty.csv"}
        )
    
    # Flatten nested data for CSV
    flat_data = []
    for item in data:
        flat_item = {}
        for key, value in item.items():
            if isinstance(value, (list, dict)):
                flat_item[key] = json.dumps(value)
            else:
                flat_item[key] = value
        flat_data.append(flat_item)
    
    # Get all unique keys
    all_keys = set()
    for item in flat_data:
        all_keys.update(item.keys())
    all_keys = sorted(list(all_keys))
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(flat_data)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.csv"
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


# Admin endpoint to check auto-close status and manually trigger
@app.get("/api/admin/auto-close-status")
async def get_auto_close_status(current_user: dict = Depends(get_current_user)):
    """Get status of resolved tickets pending auto-close"""
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=AUTO_CLOSE_HOURS)
    
    # Tickets that will be auto-closed
    pending_close = list(tickets_collection.find({
        "status": "resolved",
        "resolved_at": {"$lte": cutoff_time}
    }, {"ticket_id": 1, "title": 1, "resolved_at": 1, "_id": 0}))
    
    # Tickets resolved but not yet 24 hours
    recently_resolved = list(tickets_collection.find({
        "status": "resolved",
        "resolved_at": {"$gt": cutoff_time}
    }, {"ticket_id": 1, "title": 1, "resolved_at": 1, "_id": 0}))
    
    # Recently auto-closed
    auto_closed = list(tickets_collection.find({
        "status": "closed",
        "auto_closed": True
    }, {"ticket_id": 1, "title": 1, "closed_at": 1, "_id": 0}).sort("closed_at", -1).limit(10))
    
    return {
        "pending_auto_close": len(pending_close),
        "pending_tickets": [serialize_doc(t) for t in pending_close],
        "recently_resolved_count": len(recently_resolved),
        "recently_auto_closed": [serialize_doc(t) for t in auto_closed]
    }


# webhooks routes extracted to routes/webhooks.py


# ============================================================
# Advanced Filter Engine + Custom Inboxes
# ============================================================
# Filter & Inbox routes extracted to routes/filters.py
# ============================================================
