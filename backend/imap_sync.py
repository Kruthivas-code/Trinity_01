"""
IMAP Email Sync Module for Trinity

Connects to a Gmail mailbox via IMAP and converts incoming emails into tickets.
Supports threading: replies to existing tickets are added as messages.
"""

import imaplib
import email
import email.message
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
import os
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def get_imap_config() -> Dict[str, Any]:
    """Read IMAP config from environment."""
    return {
        "email": os.environ.get("IMAP_EMAIL"),
        "password": os.environ.get("IMAP_PASSWORD"),
        "server": os.environ.get("IMAP_SERVER", "imap.gmail.com"),
        "port": int(os.environ.get("IMAP_PORT", "993")),
    }


def decode_mime_header(value: str) -> str:
    """Decode a MIME-encoded header value."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def extract_body(msg: email.message.Message) -> Dict[str, str]:
    """Extract plain text and HTML body from an email message."""
    text_body = ""
    html_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                continue
            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if content_type == "text/plain" and not text_body:
                    text_body = decoded
                elif content_type == "text/html" and not html_body:
                    html_body = decoded
            except Exception as e:
                logger.warning(f"Failed to decode email part: {e}")
    else:
        content_type = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if content_type == "text/plain":
                    text_body = decoded
                elif content_type == "text/html":
                    html_body = decoded
        except Exception as e:
            logger.warning(f"Failed to decode email body: {e}")

    # Fallback: convert HTML to plain text if no text body
    if not text_body and html_body:
        text_body = re.sub(r"<[^>]+>", " ", html_body)
        text_body = re.sub(r"\s+", " ", text_body).strip()

    return {"text": text_body, "html": html_body}


def parse_email_date(msg: email.message.Message) -> datetime:
    """Parse the Date header into a timezone-aware datetime."""
    date_str = msg.get("Date", "")
    if date_str:
        try:
            return parsedate_to_datetime(date_str).astimezone(timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def fetch_new_emails(config: Dict[str, Any], since_uid: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Connect to IMAP server and fetch new (UNSEEN) emails.

    Args:
        config: IMAP connection config
        since_uid: Only fetch emails with UID greater than this (optional)

    Returns:
        List of parsed email dicts
    """
    imap_email = config["email"]
    imap_password = config["password"]
    imap_server = config["server"]
    imap_port = config["port"]

    if not imap_email or not imap_password:
        logger.debug("[IMAP] No IMAP credentials configured, skipping")
        return []

    emails = []
    conn = None
    try:
        conn = imaplib.IMAP4_SSL(imap_server, imap_port)
        conn.login(imap_email, imap_password)
        conn.select("INBOX")

        # Search for unseen emails
        search_criteria = "UNSEEN"
        if since_uid:
            search_criteria = f"(UNSEEN UID {since_uid}:*)"

        status, msg_ids = conn.search(None, search_criteria)
        if status != "OK" or not msg_ids[0]:
            return []

        id_list = msg_ids[0].split()
        logger.info(f"[IMAP] Found {len(id_list)} unseen emails")

        for msg_id in id_list:
            try:
                status, data = conn.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extract headers
                from_header = decode_mime_header(msg.get("From", ""))
                to_header = decode_mime_header(msg.get("To", ""))
                cc_header = decode_mime_header(msg.get("Cc", ""))
                subject = decode_mime_header(msg.get("Subject", ""))
                message_id = msg.get("Message-ID", "").strip()
                in_reply_to = msg.get("In-Reply-To", "").strip()
                references = msg.get("References", "").strip()
                email_date = parse_email_date(msg)

                # Extract sender email
                _, sender_email = parseaddr(from_header)
                sender_email = sender_email.lower() if sender_email else ""

                # Extract sender name
                sender_name, _ = parseaddr(from_header)
                if not sender_name:
                    sender_name = sender_email.split("@")[0].replace(".", " ").title() if sender_email else "Unknown"

                # Extract body
                body = extract_body(msg)

                # Generate preview
                preview = (body["text"] or "")[:150].strip()
                if len(body["text"] or "") > 150:
                    preview += "..."

                emails.append({
                    "imap_msg_id": msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                    "message_id": message_id,
                    "in_reply_to": in_reply_to,
                    "references": references,
                    "from_header": from_header,
                    "sender_email": sender_email,
                    "sender_name": sender_name,
                    "to": to_header,
                    "cc": cc_header,
                    "subject": subject,
                    "date": email_date,
                    "text": body["text"],
                    "html": body["html"],
                    "preview": preview,
                })
            except Exception as e:
                logger.error(f"[IMAP] Error parsing email {msg_id}: {e}")
                continue

    except imaplib.IMAP4.error as e:
        logger.error(f"[IMAP] IMAP error: {e}")
    except Exception as e:
        logger.error(f"[IMAP] Connection error: {e}")
    finally:
        if conn:
            try:
                conn.close()
                conn.logout()
            except Exception:
                pass

    return emails
