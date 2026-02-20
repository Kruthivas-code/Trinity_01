"""
Email service for Trinity — handles sending via SES SMTP and receiving via IMAP.
"""
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from email.utils import formataddr, make_msgid, parseaddr
import os
import re
import uuid
import logging
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


def _get_env(key, default=""):
    return os.environ.get(key, default)


def detect_ses_region():
    """Try each SES SMTP region and return the first that connects."""
    global _working_smtp_host
    if _working_smtp_host:
        return _working_smtp_host

    user = _get_env("SES_SMTP_USER")
    password = _get_env("SES_SMTP_PASSWORD")

    for host in SES_SMTP_REGIONS:
        try:
            logger.info(f"Trying SES SMTP region: {host}")
            server = smtplib.SMTP(host, 587, timeout=10)
            server.starttls()
            server.login(user, password)
            server.quit()
            _working_smtp_host = host
            logger.info(f"SES SMTP region detected: {host}")
            return host
        except Exception as e:
            logger.debug(f"SES region {host} failed: {e}")
            continue

    logger.error("No SES SMTP region could connect")
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
    Returns dict with message_id and threading_message_id, or None on failure.
    """
    sender_email = _get_env("SES_SENDER_EMAIL", "support@emergent.sh")
    sender_name = _get_env("SES_SENDER_NAME", "Emergent Support")
    smtp_user = _get_env("SES_SMTP_USER")
    smtp_password = _get_env("SES_SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        logger.error("SES SMTP credentials not configured")
        return None

    smtp_host = detect_ses_region()
    if not smtp_host:
        logger.error("No working SES SMTP region found")
        _store_failed_email(to_email, subject, html_body, text_body, ticket_id, in_reply_to, references)
        return None

    # Build message
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

    # Attach bodies
    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP(smtp_host, 587, timeout=30)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(sender_email, [to_email], msg.as_string())
        server.quit()
        logger.info(f"Email sent to {to_email} | subject={subject} | ticket={ticket_id}")

        # Store in email_threads for threading
        thread_doc = {
            "thread_id": f"eth_{uuid.uuid4().hex[:12]}",
            "ticket_id": ticket_id,
            "message_id": threading_msg_id,
            "in_reply_to": in_reply_to,
            "references": references or [],
            "direction": "outbound",
            "from_email": sender_email,
            "to_email": to_email,
            "subject": subject,
            "created_at": datetime.now(timezone.utc),
        }
        email_threads_collection.insert_one(thread_doc)

        return {
            "status": "sent",
            "threading_message_id": threading_msg_id,
            "to_email": to_email,
        }

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        _store_failed_email(to_email, subject, html_body, text_body, ticket_id, in_reply_to, references)
        return None


def _store_failed_email(to_email, subject, html_body, text_body, ticket_id, in_reply_to, references):
    """Store failed emails for retry."""
    try:
        email_threads_collection.insert_one({
            "thread_id": f"eth_{uuid.uuid4().hex[:12]}",
            "ticket_id": ticket_id,
            "direction": "outbound_failed",
            "from_email": _get_env("SES_SENDER_EMAIL", "support@emergent.sh"),
            "to_email": to_email,
            "subject": subject,
            "html_body": html_body,
            "text_body": text_body,
            "in_reply_to": in_reply_to,
            "references": references or [],
            "retry_count": 0,
            "created_at": datetime.now(timezone.utc),
        })
    except Exception as e:
        logger.error(f"Failed to store failed email for retry: {e}")


def get_thread_context(ticket_id: str) -> dict:
    """Get the latest outbound Message-ID and full references chain for a ticket."""
    threads = list(
        email_threads_collection.find(
            {"ticket_id": ticket_id, "direction": "outbound"},
            {"_id": 0, "message_id": 1, "references": 1},
        ).sort("created_at", -1).limit(1)
    )
    if not threads:
        return {"in_reply_to": None, "references": []}

    latest = threads[0]
    all_refs = list(
        email_threads_collection.find(
            {"ticket_id": ticket_id, "direction": {"$in": ["outbound", "inbound"]}},
            {"_id": 0, "message_id": 1},
        ).sort("created_at", 1)
    )
    ref_chain = [t["message_id"] for t in all_refs if t.get("message_id")]

    return {
        "in_reply_to": latest.get("message_id"),
        "references": ref_chain,
    }


def send_ticket_confirmation(ticket_id: str, customer_email: str, customer_name: str, subject: str):
    """Send ticket confirmation email to customer."""
    from services.email_templates import ticket_confirmation_html, ticket_confirmation_text

    html = ticket_confirmation_html(ticket_id, customer_name, subject)
    text = ticket_confirmation_text(ticket_id, customer_name, subject)

    return send_email(
        to_email=customer_email,
        subject=f"Re: {subject}",
        html_body=html,
        text_body=text,
        ticket_id=ticket_id,
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
