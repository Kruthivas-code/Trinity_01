"""
Email routes: IMAP sync, Gmail integration, file upload, import, atlas import, email reply.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request, File, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from datetime import datetime, timedelta, timezone
from typing import Optional
from email.utils import parseaddr
from html import unescape
import uuid
import os
import re
import io
import csv
import json
import base64
import asyncio
import httpx
import traceback
import logging

from pymongo import ASCENDING, DESCENDING

from database import (
    db, tickets_collection, users_collection, messages_collection,
    email_replies_collection, gmail_tokens_collection,
    GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REDIRECT_URI,
    GMAIL_WATCH_EMAIL, GMAIL_SYNC_QUERY, GMAIL_SCOPES,
)
from dependencies import get_current_user
from models.schemas import EmailReplyRequest, SimulatedEmail, AtlasImportRequest
from utils import (
    serialize_doc, generate_ticket_id, get_or_create_customer,
    extract_domain, sanitize_html, trigger_webhooks,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["email"])

# Gmail OAuth imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
except ImportError:
    logger.warning("Google API libraries not installed - Gmail integration unavailable")

# File upload config
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "uploads")
if not os.path.exists(UPLOAD_DIR):
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def get_gmail_flow():
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
    credentials = Credentials(
        token=credentials_dict.get("access_token"),
        refresh_token=credentials_dict.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET
    )
    return build("gmail", "v1", credentials=credentials)


def parse_email_body(payload):
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                if "data" in part.get("body", {}):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    break
            elif part["mimeType"] == "text/html" and not body:
                if "data" in part.get("body", {}):
                    html_body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    body = re.sub(r"<[^>]+>", "", html_body)
                    body = unescape(body)
            elif "parts" in part:
                body = parse_email_body(part)
                if body:
                    break
    elif "body" in payload and "data" in payload["body"]:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    return body.strip()


def extract_email_metadata(headers):
    metadata = {"from": "", "subject": "", "date": "", "message_id": "", "to": ""}
    for header in headers:
        name = header.get("name", "").lower()
        value = header.get("value", "")
        if name == "from":
            metadata["from"] = value
        elif name == "subject":
            metadata["subject"] = value
        elif name == "date":
            metadata["date"] = value
        elif name == "message-id":
            metadata["message_id"] = value
        elif name == "to":
            metadata["to"] = value
    return metadata


def find_existing_ticket_for_email(gmail_message_id, gmail_thread_id, headers):
    """Check for existing tickets matching this email for dedup and threading"""
    rfc_message_id = headers.get("message_id", "")
    if rfc_message_id:
        existing_ticket = tickets_collection.find_one({"email_rfc_message_id": rfc_message_id})
        if existing_ticket:
            return {"type": "duplicate_ticket", "ticket": existing_ticket}
    existing_ticket = tickets_collection.find_one({"email_message_id": gmail_message_id})
    if existing_ticket:
        return {"type": "duplicate_ticket", "ticket": existing_ticket}
    from database import email_replies_collection as erc
    existing_reply = erc.find_one({"gmail_message_id": gmail_message_id})
    if existing_reply:
        return {"type": "duplicate_reply", "reply": existing_reply}
    if gmail_thread_id:
        thread_ticket = tickets_collection.find_one({"email_thread_id": gmail_thread_id})
        if thread_ticket:
            return {"type": "thread_match", "ticket": thread_ticket}
    in_reply_to = headers.get("in_reply_to", "")
    if in_reply_to:
        ref_ticket = tickets_collection.find_one({
            "$or": [
                {"email_rfc_message_id": in_reply_to},
                {"last_reply_message_id": in_reply_to},
                {"email_thread_message_ids": in_reply_to}
            ]
        })
        if ref_ticket:
            return {"type": "thread_match", "ticket": ref_ticket}
    references = headers.get("references", "")
    if references:
        for ref in references.split():
            ref = ref.strip()
            if not ref:
                continue
            ref_ticket = tickets_collection.find_one({
                "$or": [
                    {"email_rfc_message_id": ref},
                    {"last_reply_message_id": ref},
                    {"email_thread_message_ids": ref}
                ]
            })
            if ref_ticket:
                return {"type": "thread_match", "ticket": ref_ticket}
    return None


def add_email_as_reply_to_ticket(ticket, gmail_message_id, gmail_thread_id, headers, content, source="gmail_sync"):
    """Add an email as a reply to an existing ticket"""
    from email_utils import extract_email_address as extract_email_addr, format_sender_name
    reply_id = f"reply_{uuid.uuid4().hex[:12]}"
    sender_email = extract_email_addr(headers.get("from", ""))
    sender_name = format_sender_name(headers.get("from", ""))
    email_replies_collection.insert_one({
        "reply_id": reply_id,
        "ticket_id": ticket["ticket_id"],
        "direction": "incoming",
        "from_email": sender_email,
        "from_name": sender_name,
        "to_email": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "body": (content.get("text") or "")[:50000],
        "body_html": (content.get("html") or "")[:100000],
        "email_rfc_message_id": headers.get("message_id", ""),
        "gmail_message_id": gmail_message_id,
        "source": source,
        "created_at": datetime.now(timezone.utc),
        "status": "received"
    })
    messages_collection.insert_one({
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "ticket_id": ticket["ticket_id"],
        "type": "customer_reply",
        "content": (content.get("text") or "")[:50000],
        "content_html": (content.get("html") or "")[:100000],
        "author_id": None,
        "author_name": sender_name,
        "author_email": sender_email,
        "email_reply_id": reply_id,
        "created_at": datetime.now(timezone.utc)
    })
    tickets_collection.update_one(
        {"ticket_id": ticket["ticket_id"]},
        {
            "$set": {"status": "todo", "updated_at": datetime.now(timezone.utc), "last_reply_message_id": headers.get("message_id", "")},
            "$push": {"email_thread_message_ids": headers.get("message_id", "")}
        }
    )


# IMAP Email Sync endpoint
@router.post("/email/sync")
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

@router.get("/email/status")
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
@router.post("/import")
async def import_tickets(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Import tickets from a JSON or CSV file upload."""
    MAX_IMPORT_SIZE = 5 * 1024 * 1024  # 5MB
    content = await file.read()
    if len(content) > MAX_IMPORT_SIZE:
        raise HTTPException(status_code=413, detail="Import file too large. Maximum size is 5MB.")
    
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

@router.post("/import/atlas")
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

@router.post("/upload/image")
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

@router.get("/uploads/{filename}")
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

@router.get("/gmail/status")
async def gmail_status(current_user: dict = Depends(get_current_user)):
    """Check if Gmail is connected"""
    token_doc = gmail_tokens_collection.find_one({"type": "gmail_oauth"})
    is_connected = token_doc is not None and "access_token" in token_doc
    return {
        "connected": is_connected,
        "watch_email": GMAIL_WATCH_EMAIL if is_connected else None,
        "configured": bool(GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET)
    }

@router.get("/gmail/connect")
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

@router.get("/auth/gmail/callback")
async def gmail_callback(code: str = None, state: str = None, error: str = None):
    """Handle Gmail OAuth callback"""
    frontend_url = "https://kb-email-refresh.preview.emergentagent.com"
    
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

@router.post("/gmail/disconnect")
async def gmail_disconnect(current_user: dict = Depends(get_current_user)):
    """Disconnect Gmail integration"""
    gmail_tokens_collection.delete_one({"type": "gmail_oauth"})
    return {"message": "Gmail disconnected successfully"}

@router.get("/gmail/emails")
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

@router.get("/gmail/email/{message_id}")
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

@router.post("/gmail/create-ticket/{message_id}")
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

@router.post("/gmail/sync")
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

@router.get("/settings/email")
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

@router.put("/settings/email")
async def update_email_settings(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Update email settings (admin only for now)"""
    # In production, this would update env vars or a config collection
    # For now, just return success as the email is set via env var
    return {"message": "Email settings updated"}

@router.post("/gmail/backfill-email-content")
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

@router.post("/tickets/{ticket_id}/reply")
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

@router.get("/tickets/{ticket_id}/replies")
async def get_ticket_email_replies(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all email replies for a ticket"""
    replies = list(email_replies_collection.find(
        {"ticket_id": ticket_id},
        sort=[("created_at", ASCENDING)]
    ))
    return {"replies": [serialize_doc(r) for r in replies]}

# ==================== Email Simulator (For Testing) ====================

@router.post("/email/simulate")
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

@router.post("/gmail/webhook")
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

@router.post("/gmail/watch/start")
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

@router.post("/gmail/watch/stop")
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
