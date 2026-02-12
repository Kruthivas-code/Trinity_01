"""
Shared utility functions used across route modules.
"""
import re
import io
import csv
import json
import uuid
import hmac
import hashlib
import asyncio
import logging
import pytz
from datetime import datetime, timezone, time
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4
from email.utils import parseaddr

import bleach
import httpx
from bson import ObjectId
from fastapi.responses import StreamingResponse

from database import (
    db, tickets_collection, customers_collection, counters_collection,
    ticket_changelog_collection, webhooks_collection, webhook_logs_collection,
    B2C_EMAIL_DOMAINS, SYSTEM_TIMEZONE,
)

logger = logging.getLogger("server")


# ==================== Serialization ====================

def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        serialized = {}
        for key, value in doc.items():
            if key == "_id":
                continue
            elif isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = serialize_doc(value)
            elif isinstance(value, list):
                serialized[key] = [serialize_doc(item) if isinstance(item, dict) else item for item in value]
            else:
                serialized[key] = value

        if "ticket_id" in serialized:
            serialized["id"] = serialized["ticket_id"]
        if "user_id" in serialized and "id" not in serialized:
            serialized["id"] = serialized["user_id"]

        return serialized
    return doc


# ==================== Ticket Change Logging ====================

def log_ticket_change(ticket_id: str, uuid_str: str, field: str, old_value: Any, new_value: Any, changed_by: str, change_type: str = "update", metadata: dict = None):
    """Log a change to a ticket's metadata for audit purposes"""
    changelog_entry = {
        "changelog_id": f"cl_{uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "ticket_uuid": uuid_str,
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "change_type": change_type,
        "changed_by": changed_by,
        "changed_at": datetime.now(timezone.utc)
    }
    if metadata:
        changelog_entry["metadata"] = metadata
    ticket_changelog_collection.insert_one(changelog_entry)
    return changelog_entry


def log_ticket_changes_batch(ticket_id: str, uuid_str: str, changes: Dict[str, Tuple[Any, Any]], changed_by: str, change_type: str = "update"):
    """Log multiple changes at once"""
    entries = []
    timestamp = datetime.now(timezone.utc)
    for field, (old_value, new_value) in changes.items():
        if old_value != new_value:
            entry = {
                "changelog_id": f"cl_{uuid4().hex[:12]}",
                "ticket_id": ticket_id,
                "ticket_uuid": uuid_str,
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
                "change_type": change_type,
                "changed_by": changed_by,
                "changed_at": timestamp
            }
            entries.append(entry)
    if entries:
        ticket_changelog_collection.insert_many(entries)
    return entries


# ==================== ID Generation ====================

def generate_ticket_id() -> str:
    """Generate sequential ticket ID (TKT-000001 format)"""
    counter = counters_collection.find_one_and_update(
        {"_id": "ticket_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return f"TKT-{counter['seq']:06d}"


def generate_customer_id() -> str:
    """Generate sequential customer ID (CUST-000001 format)"""
    counter = counters_collection.find_one_and_update(
        {"_id": "customer_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return f"CUST-{counter['seq']:06d}"


# ==================== Email Utilities ====================

def extract_email_address(from_header):
    """Extract just the email address from a 'From' header"""
    if not from_header:
        return None
    match = re.search(r'<([^>]+)>', from_header)
    if match:
        return match.group(1)
    if '@' in from_header:
        return from_header.strip()
    return None


def extract_domain(email: str) -> Optional[str]:
    """Extract domain from email address"""
    if not email:
        return None
    try:
        _, addr = parseaddr(email)
        if '@' in addr:
            return addr.split('@')[1].lower()
    except Exception:
        pass
    return None


def is_b2c_email(email: str) -> bool:
    """Check if email is from a common B2C provider"""
    domain = extract_domain(email)
    if not domain:
        return True
    return domain.lower() in B2C_EMAIL_DOMAINS


def detect_company_from_domain(domain: str) -> Optional[str]:
    """Try to extract company name from domain"""
    if not domain or domain.lower() in B2C_EMAIL_DOMAINS:
        return None
    parts = domain.split('.')
    if len(parts) >= 2:
        company = parts[0].replace('-', ' ').replace('_', ' ')
        return company.title()
    return None


# ==================== Customer Management ====================

def get_or_create_customer(email: str, name: str = None) -> dict:
    """Get existing customer by email or create new one."""
    if not email:
        return None

    email_lower = email.lower().strip()

    customer = customers_collection.find_one({
        "$or": [
            {"primary_email": email_lower},
            {"linked_emails": email_lower}
        ]
    })

    if customer:
        return serialize_doc(customer)

    domain = extract_domain(email_lower)
    is_b2c = is_b2c_email(email_lower)
    company_name = detect_company_from_domain(domain) if not is_b2c else None

    new_customer = {
        "customer_id": generate_customer_id(),
        "name": name or email_lower.split('@')[0].replace('.', ' ').replace('_', ' ').title(),
        "primary_email": email_lower,
        "linked_emails": [],
        "company_name": company_name,
        "company_domain": domain if not is_b2c else None,
        "customer_type": "b2b" if not is_b2c else "b2c",
        "priority_level": "standard",
        "net_payments": 0.0,
        "assigned_agents": [],
        "tags": [],
        "notes": "",
        "custom_fields": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    customers_collection.insert_one(new_customer)
    logger.info(f"Created new customer: {new_customer['customer_id']} for {email_lower}")
    return serialize_doc(new_customer)


# ==================== HTML Sanitization ====================

def sanitize_html(html_content: str) -> str:
    """Sanitize HTML content to prevent XSS attacks"""
    if not html_content:
        return html_content

    allowed_tags = [
        'p', 'br', 'b', 'i', 'u', 'strong', 'em', 'a', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'code',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'div', 'span', 'img',
        'hr', 'sub', 'sup'
    ]
    allowed_attrs = {
        '*': ['class', 'style'],
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'width', 'height'],
        'td': ['colspan', 'rowspan'],
        'th': ['colspan', 'rowspan']
    }

    return bleach.clean(
        html_content,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True
    )


# ==================== Webhook Delivery ====================

async def deliver_webhook(webhook: dict, event_type: str, payload: dict):
    """Deliver a webhook with retry logic and logging"""
    webhook_id = webhook.get("webhook_id")
    url = webhook.get("url")
    secret = webhook.get("secret")
    custom_headers = webhook.get("headers", {})

    delivery_payload = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "webhook_id": webhook_id,
        "data": payload
    }
    payload_json = json.dumps(delivery_payload, default=str)

    signature = None
    if secret:
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Trinity-Webhooks/1.0",
        "X-Webhook-Event": event_type,
        "X-Webhook-Delivery": f"del_{uuid.uuid4().hex[:12]}",
    }
    if signature:
        headers["X-Webhook-Signature"] = f"sha256={signature}"
    headers.update(custom_headers)

    log_entry = {
        "log_id": f"whl_{uuid.uuid4().hex[:12]}",
        "webhook_id": webhook_id,
        "event": event_type,
        "url": url,
        "request_headers": headers,
        "request_body": delivery_payload,
        "created_at": datetime.now(timezone.utc),
        "attempts": []
    }

    max_retries = 3
    retry_delays = [0, 5, 30]

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        for attempt in range(max_retries):
            if attempt > 0:
                await asyncio.sleep(retry_delays[attempt])

            attempt_record = {
                "attempt": attempt + 1,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            try:
                response = await http_client.post(url, content=payload_json, headers=headers)
                attempt_record["status_code"] = response.status_code
                attempt_record["response_body"] = response.text[:1000] if response.text else None

                if 200 <= response.status_code < 300:
                    attempt_record["success"] = True
                    log_entry["attempts"].append(attempt_record)
                    log_entry["status"] = "delivered"
                    log_entry["completed_at"] = datetime.now(timezone.utc)
                    webhook_logs_collection.insert_one(log_entry)

                    webhooks_collection.update_one(
                        {"webhook_id": webhook_id},
                        {
                            "$set": {"last_triggered_at": datetime.now(timezone.utc)},
                            "$inc": {"delivery_count": 1, "success_count": 1}
                        }
                    )
                    return True
                else:
                    attempt_record["success"] = False
                    attempt_record["error"] = f"HTTP {response.status_code}"

            except Exception as e:
                attempt_record["success"] = False
                attempt_record["error"] = str(e)

            log_entry["attempts"].append(attempt_record)

    log_entry["status"] = "failed"
    log_entry["completed_at"] = datetime.now(timezone.utc)
    webhook_logs_collection.insert_one(log_entry)

    webhooks_collection.update_one(
        {"webhook_id": webhook_id},
        {
            "$set": {"last_triggered_at": datetime.now(timezone.utc)},
            "$inc": {"delivery_count": 1, "failure_count": 1}
        }
    )
    return False


async def trigger_webhooks(event_type: str, payload: dict):
    """Trigger all webhooks subscribed to an event type"""
    webhooks = list(webhooks_collection.find({
        "is_active": True,
        "events": event_type
    }))
    for webhook in webhooks:
        asyncio.create_task(deliver_webhook(webhook, event_type, payload))


# ==================== Time Utilities ====================

def get_ist_now():
    """Get current time in IST timezone"""
    ist = pytz.timezone(SYSTEM_TIMEZONE)
    return datetime.now(ist)


def parse_time_str(time_str: str) -> time:
    """Parse time string (HH:MM) to time object"""
    try:
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return time(0, 0)


# ==================== Export Utilities ====================

def serialize_for_export(doc):
    """Convert MongoDB document to JSON-serializable format for export"""
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


def generate_json_export(data, filename_prefix):
    """Generate JSON file download response"""
    json_str = json.dumps(data, indent=2, default=str)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    return StreamingResponse(
        io.StringIO(json_str),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def generate_csv_export(data, filename_prefix):
    """Generate CSV file download response"""
    if not data:
        return StreamingResponse(
            io.StringIO("No data to export"),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_prefix}_empty.csv"}
        )
    flat_data = []
    for item in data:
        flat_item = {}
        for key, value in item.items():
            if isinstance(value, (list, dict)):
                flat_item[key] = json.dumps(value)
            else:
                flat_item[key] = value
        flat_data.append(flat_item)
    all_keys = sorted({k for item in flat_data for k in item.keys()})
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
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

