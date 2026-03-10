"""
Routes for file upload, data import, atlas import, and ticket email replies.
Email sending/receiving functionality is pending integration with a transactional provider.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request, File, UploadFile
from fastapi.responses import FileResponse
from datetime import datetime, timezone
from typing import Optional
import uuid
import os
import io
import csv
import json
import traceback
import logging

from pymongo import ASCENDING, DESCENDING

from database import (
    db, tickets_collection, users_collection, messages_collection,
    email_replies_collection, file_attachments_collection,
)
from dependencies import get_current_user
from models.schemas import AtlasImportRequest
from utils import (
    serialize_doc, generate_ticket_id, get_or_create_customer,
    extract_domain, sanitize_html, trigger_webhooks,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["email"])

# ==================== File Upload ====================

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_ATTACHMENT_TYPES = {
    # Images
    "image/jpeg", "image/png", "image/gif", "image/webp",
    # Documents
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Text
    "text/plain", "text/csv", "text/html",
    # Archives
    "application/zip", "application/x-zip-compressed",
    "application/gzip",
    # Other
    "application/json", "application/xml",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ATTACHMENT_SIZE = 7 * 1024 * 1024  # 7MB per file (SES 10MB total limit)


@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload an image file for use in replies"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")

    file_ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        file_ext = ".jpg"

    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as f:
        f.write(content)

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
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

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


# ==================== File Attachments (for outbound emails) ====================

@router.post("/attachments/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a file attachment for use in outbound email replies.
    Stores in local filesystem + metadata in MongoDB. Returns a file_id for referencing."""

    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{content_type}' not allowed. Supported: PDF, Word, Excel, PowerPoint, images, text, CSV, ZIP."
        )

    content = await file.read()
    if len(content) > MAX_ATTACHMENT_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_ATTACHMENT_SIZE // (1024*1024)}MB per attachment."
        )

    file_id = f"att_{uuid.uuid4().hex[:16]}"
    original_name = file.filename or "unnamed"
    ext = os.path.splitext(original_name)[1].lower()
    stored_name = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(file_path, "wb") as f:
        f.write(content)

    doc = {
        "file_id": file_id,
        "original_name": original_name,
        "stored_name": stored_name,
        "content_type": content_type,
        "size": len(content),
        "uploaded_by": current_user["user_id"],
        "uploaded_by_name": current_user.get("name"),
        "created_at": datetime.now(timezone.utc),
    }
    file_attachments_collection.insert_one(doc)
    doc.pop("_id", None)

    return {
        "file_id": file_id,
        "original_name": original_name,
        "content_type": content_type,
        "size": len(content),
        "download_url": f"/api/attachments/{file_id}",
    }


@router.get("/attachments/{file_id}")
async def download_attachment(file_id: str):
    """Download/serve a file attachment by file_id."""
    doc = file_attachments_collection.find_one({"file_id": file_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = os.path.join(UPLOAD_DIR, doc["stored_name"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Attachment file missing from storage")

    return FileResponse(
        file_path,
        media_type=doc.get("content_type", "application/octet-stream"),
        filename=doc["original_name"],
    )


@router.delete("/attachments/{file_id}")
async def delete_attachment(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an unused attachment. Only the uploader can delete."""
    doc = file_attachments_collection.find_one({"file_id": file_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if doc["uploaded_by"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the uploader can delete this attachment")

    file_path = os.path.join(UPLOAD_DIR, doc["stored_name"])
    if os.path.exists(file_path):
        os.remove(file_path)

    file_attachments_collection.delete_one({"file_id": file_id})
    return {"status": "deleted", "file_id": file_id}


# ==================== Data Import ====================

@router.post("/import")
async def import_tickets(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Import tickets from a JSON or CSV file upload."""
    MAX_IMPORT_SIZE = 5 * 1024 * 1024
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
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            tickets_collection.insert_one(ticket_doc)
            imported_count += 1

        return {
            "message": f"Successfully imported {imported_count} tickets",
            "count": imported_count
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Import failed: invalid JSON format")
    except csv.Error:
        raise HTTPException(status_code=400, detail="Import failed: invalid CSV format")
    except Exception as e:
        logger.error(f"[IMPORT] Unexpected error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail="Import failed due to an unexpected error")


# ==================== Atlas Import ====================

from atlas_import import run_atlas_import
import httpx

@router.post("/import/atlas")
async def import_from_atlas(
    req: AtlasImportRequest,
    current_user: dict = Depends(get_current_user)
):
    """Import conversations, messages, and tags from Atlas."""
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
            detail=f"Atlas API error: HTTP {e.response.status_code} - {e.response.text[:200]}"
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Could not connect to Atlas API (api.atlas.so)")
    except Exception:
        logger.error(f"[ATLAS IMPORT] Unexpected error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Atlas import failed due to an internal error")

    return {
        "success": True,
        "message": f"Imported {summary['conversations_imported']} conversations with {summary['messages_imported']} messages",
        "summary": summary,
    }


# ==================== Ticket Email Replies ====================

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


@router.post("/tickets/{ticket_id}/reply")
async def reply_to_ticket(
    ticket_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Reply to a ticket. Email sending is not yet configured.
    The reply is saved to the database for the conversation thread.
    """
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    body = await request.json()
    to_email = body.get("to_email", "")
    subject = body.get("subject", "")
    reply_body = body.get("body", "")

    reply_id = f"reply_{uuid.uuid4().hex[:12]}"
    reply_doc = {
        "reply_id": reply_id,
        "ticket_id": ticket_id,
        "direction": "outgoing",
        "to_email": to_email,
        "subject": subject,
        "body": reply_body,
        "sent_by": current_user["user_id"],
        "sent_by_email": current_user.get("email"),
        "sent_by_name": current_user.get("name"),
        "created_at": datetime.now(timezone.utc),
        "status": "saved"
    }

    email_replies_collection.insert_one(reply_doc)

    # Add as a message in the ticket conversation
    messages_collection.insert_one({
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "type": "reply",
        "content": reply_body,
        "author_id": current_user["user_id"],
        "author_name": current_user.get("name"),
        "email_reply_id": reply_id,
        "created_at": datetime.now(timezone.utc)
    })

    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {
            "status": "waiting",
            "updated_at": datetime.now(timezone.utc),
            "last_reply_at": datetime.now(timezone.utc),
        }}
    )

    return {
        "status": "saved",
        "message": "Reply saved. Email delivery is pending provider configuration.",
        "reply_id": reply_id,
    }
