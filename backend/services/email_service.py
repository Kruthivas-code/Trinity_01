"""
Email service for Trinity — handles sending via SES SMTP and receiving via IMAP.
Production-grade with retry queue, rate limiting, and structured logging.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, make_msgid
import os
import uuid
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from database import email_threads_collection, tickets_collection, messages_collection

logger = logging.getLogger("email_service")

# SES SMTP regions to try
SES_SMTP_REGIONS = [
    "email-smtp.us-east-1.amazonaws.com",
    "email-smtp.us-west-2.amazonaws.com",
    "email-smtp.eu-west-1.amazonaws.com",
    "email-smtp.ap-south-1.amazonaws.com",
    "email-smtp.ap-southeast-1.amazonaws.com",
    "email-smtp.eu-central-1.amazonaws.com",
]

_working_smtp_host = None
_send_lock = threading.Lock()

# Rate limiting: max 14 emails/sec (SES default is 14/sec)
_rate_window_start = 0.0
_rate_count = 0
_RATE_LIMIT = 10  # conservative limit per second


def _get_env(key, default=""):
    return os.environ.get(key, default)


def _check_rate_limit():
    """Simple sliding window rate limiter. Returns True if allowed."""
    global _rate_window_start, _rate_count
    now = time.time()
    if now - _rate_window_start >= 1.0:
        _rate_window_start = now
        _rate_count = 0
    if _rate_count >= _RATE_LIMIT:
        return False
    _rate_count += 1
    return True


def detect_ses_region():
    """Try each SES SMTP region and return the first that connects."""
    global _working_smtp_host
    if _working_smtp_host:
        return _working_smtp_host

    user = _get_env("SES_SMTP_USER")
    password = _get_env("SES_SMTP_PASSWORD")

    for host in SES_SMTP_REGIONS:
        try:
            logger.info(f"[SES] Trying region: {host}")
            server = smtplib.SMTP(host, 587, timeout=10)
            server.starttls()
            server.login(user, password)
            server.quit()
            _working_smtp_host = host
            logger.info(f"[SES] Region detected: {host}")
            return host
        except Exception as e:
            logger.debug(f"[SES] Region {host} failed: {e}")
            continue

    logger.error("[SES] No SMTP region could connect")
    return None


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    ticket_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[list] = None,
) -> Optional[dict]:
    """
    Send an email via SES SMTP with threading headers.
    Thread-safe with rate limiting and retry queue.
    """
    sender_email = _get_env("SES_SENDER_EMAIL", "support@emergent.sh")
    sender_name = _get_env("SES_SENDER_NAME", "Emergent Support")
    smtp_user = _get_env("SES_SMTP_USER")
    smtp_password = _get_env("SES_SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        logger.error("[SEND] SES SMTP credentials not configured")
        return None

    smtp_host = detect_ses_region()
    if not smtp_host:
        _store_failed_email(to_email, subject, html_body, text_body, ticket_id, in_reply_to, references, "no_smtp_region")
        return None

    # Rate limit check
    with _send_lock:
        if not _check_rate_limit():
            logger.warning(f"[SEND] Rate limit hit, queuing email to {to_email}")
            _store_failed_email(to_email, subject, html_body, text_body, ticket_id, in_reply_to, references, "rate_limited")
            return None

    # Build MIME message
    msg = MIMEMultipart("alternative")
    threading_msg_id = make_msgid(domain="emergent.sh")

    msg["From"] = formataddr((sender_name, sender_email))
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Message-ID"] = threading_msg_id
    msg["Reply-To"] = sender_email

    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = " ".join(references)

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP(smtp_host, 587, timeout=30)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(sender_email, [to_email], msg.as_string())
        server.quit()

        logger.info(f"[SEND] OK to={to_email} ticket={ticket_id} subject={subject[:60]}")

        # Store outbound thread record
        email_threads_collection.insert_one({
            "thread_id": f"eth_{uuid.uuid4().hex[:12]}",
            "ticket_id": ticket_id,
            "message_id": threading_msg_id,
            "in_reply_to": in_reply_to,
            "references": references or [],
            "direction": "outbound",
            "status": "sent",
            "from_email": sender_email,
            "to_email": to_email,
            "subject": subject,
            "created_at": datetime.now(timezone.utc),
        })

        return {
            "status": "sent",
            "threading_message_id": threading_msg_id,
            "to_email": to_email,
        }

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"[SEND] Auth failed: {e}")
        _store_failed_email(to_email, subject, html_body, text_body, ticket_id, in_reply_to, references, "auth_error")
        return None
    except smtplib.SMTPRecipientsRefused as e:
        logger.error(f"[SEND] Recipient refused: {to_email} — {e}")
        _store_failed_email(to_email, subject, html_body, text_body, ticket_id, in_reply_to, references, "recipient_refused")
        return None
    except Exception as e:
        logger.error(f"[SEND] Failed to={to_email}: {e}")
        _store_failed_email(to_email, subject, html_body, text_body, ticket_id, in_reply_to, references, "smtp_error")
        return None


def _store_failed_email(to_email, subject, html_body, text_body, ticket_id, in_reply_to, references, error_reason):
    """Store failed emails for retry."""
    try:
        email_threads_collection.insert_one({
            "thread_id": f"eth_{uuid.uuid4().hex[:12]}",
            "ticket_id": ticket_id,
            "direction": "outbound_failed",
            "status": "failed",
            "error_reason": error_reason,
            "from_email": _get_env("SES_SENDER_EMAIL", "support@emergent.sh"),
            "to_email": to_email,
            "subject": subject,
            "html_body": html_body,
            "text_body": text_body,
            "in_reply_to": in_reply_to,
            "references": references or [],
            "retry_count": 0,
            "max_retries": 5,
            "next_retry_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
        })
        logger.info(f"[RETRY] Queued failed email to={to_email} reason={error_reason}")
    except Exception as e:
        logger.error(f"[RETRY] Failed to queue: {e}")


def retry_failed_emails():
    """Process the retry queue. Called periodically by the poller."""
    now = datetime.now(timezone.utc)
    failed = list(email_threads_collection.find({
        "direction": "outbound_failed",
        "retry_count": {"$lt": 5},
        "next_retry_at": {"$lte": now},
    }).limit(10))

    if not failed:
        return 0

    retried = 0
    for doc in failed:
        result = send_email(
            to_email=doc["to_email"],
            subject=doc["subject"],
            html_body=doc.get("html_body", ""),
            text_body=doc.get("text_body"),
            ticket_id=doc.get("ticket_id"),
            in_reply_to=doc.get("in_reply_to"),
            references=doc.get("references"),
        )
        if result and result.get("status") == "sent":
            # Remove from failed queue
            email_threads_collection.delete_one({"_id": doc["_id"]})
            retried += 1
            logger.info(f"[RETRY] Success to={doc['to_email']} ticket={doc.get('ticket_id')}")
        else:
            # Increment retry count with exponential backoff
            new_count = doc["retry_count"] + 1
            backoff_seconds = min(60 * (2 ** new_count), 3600)  # max 1 hour
            from datetime import timedelta
            email_threads_collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "retry_count": new_count,
                    "next_retry_at": now + timedelta(seconds=backoff_seconds),
                    "last_retry_at": now,
                }},
            )
            logger.warning(f"[RETRY] Failed again to={doc['to_email']} attempt={new_count}/5 next_in={backoff_seconds}s")

    return retried


def get_thread_context(ticket_id: str) -> dict:
    """Get the latest Message-ID and full references chain for a ticket.
    
    Includes BOTH inbound and outbound emails so the first agent reply
    properly threads with the customer's original email.
    """
    # Get ALL emails for this ticket (inbound + outbound), oldest first
    all_emails = list(email_threads_collection.find(
        {
            "ticket_id": ticket_id,
            "direction": {"$in": ["outbound", "inbound", "outbound_gmail"]},
            "message_id": {"$exists": True, "$ne": ""},
        },
        {"_id": 0, "message_id": 1, "direction": 1, "created_at": 1},
    ).sort("created_at", 1))

    if not all_emails:
        return {"in_reply_to": None, "references": []}

    ref_chain = [t["message_id"] for t in all_emails if t.get("message_id")]

    # in_reply_to should be the LATEST email's message_id (inbound or outbound)
    latest = all_emails[-1]

    return {
        "in_reply_to": latest.get("message_id"),
        "references": ref_chain,
    }


def get_email_stats(ticket_id: str) -> dict:
    """Get email stats for a ticket (for dashboard display)."""
    pipeline = [
        {"$match": {"ticket_id": ticket_id}},
        {"$group": {
            "_id": "$direction",
            "count": {"$sum": 1},
        }},
    ]
    results = list(email_threads_collection.aggregate(pipeline))
    stats = {"outbound": 0, "inbound": 0, "failed": 0}
    for r in results:
        if r["_id"] == "outbound":
            stats["outbound"] = r["count"]
        elif r["_id"] == "inbound":
            stats["inbound"] = r["count"]
        elif r["_id"] == "outbound_failed":
            stats["failed"] = r["count"]
    return stats


def send_ticket_confirmation(ticket_id: str, customer_email: str, customer_name: str, subject: str):
    """Send ticket confirmation email to customer."""
    from services.email_templates import ticket_confirmation_html, ticket_confirmation_text

    ctx = get_thread_context(ticket_id)
    html = ticket_confirmation_html(ticket_id, customer_name, subject)
    text = ticket_confirmation_text(ticket_id, customer_name, subject)

    return send_email(
        to_email=customer_email,
        subject=f"Re: {subject}",
        html_body=html,
        text_body=text,
        ticket_id=ticket_id,
        in_reply_to=ctx["in_reply_to"],
        references=ctx["references"],
    )


def send_agent_reply_notification(ticket_id: str, customer_email: str, customer_name: str, original_subject: str, reply_content: str, agent_name: str):
    """Send agent reply notification to customer."""
    from services.email_templates import agent_reply_html, agent_reply_text

    ctx = get_thread_context(ticket_id)
    html = agent_reply_html(ticket_id, customer_name, original_subject, reply_content, agent_name)
    text = agent_reply_text(ticket_id, customer_name, original_subject, reply_content, agent_name)

    return send_email(
        to_email=customer_email,
        subject=f"Re: {original_subject}",
        html_body=html,
        text_body=text,
        ticket_id=ticket_id,
        in_reply_to=ctx["in_reply_to"],
        references=ctx["references"],
    )


def send_status_update(ticket_id: str, customer_email: str, customer_name: str, original_subject: str, new_status: str):
    """Send ticket status update email."""
    from services.email_templates import status_update_html, status_update_text

    ctx = get_thread_context(ticket_id)
    html = status_update_html(ticket_id, customer_name, original_subject, new_status)
    text = status_update_text(ticket_id, customer_name, original_subject, new_status)

    return send_email(
        to_email=customer_email,
        subject=f"Re: {original_subject}",
        html_body=html,
        text_body=text,
        ticket_id=ticket_id,
        in_reply_to=ctx["in_reply_to"],
        references=ctx["references"],
    )
