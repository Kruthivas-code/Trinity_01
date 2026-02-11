"""
IMAP Email Sync Module for Trinity

Connects to a Gmail mailbox via IMAP and converts incoming emails into tickets.
Uses UID-based tracking to ensure no emails are missed.
"""

import imaplib
import email
import email.message
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
import os
import re
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

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


def fetch_emails_by_uid(config: Dict[str, Any], last_uid: int = 0) -> Tuple[List[Dict[str, Any]], int]:
    """
    Connect to IMAP server and fetch emails with UID greater than last_uid.

    Uses IMAP UID commands for reliable, gap-free email fetching.

    Args:
        config: IMAP connection config
        last_uid: The last processed UID. Fetches emails with UID > last_uid.
                  Use 0 to fetch all emails.

    Returns:
        Tuple of (list of parsed email dicts, highest UID processed)
    """
    imap_email = config["email"]
    imap_password = config["password"]
    imap_server = config["server"]
    imap_port = config["port"]

    if not imap_email or not imap_password:
        logger.debug("[IMAP] No IMAP credentials configured, skipping")
        return [], last_uid

    emails = []
    max_uid = last_uid
    conn = None

    try:
        conn = imaplib.IMAP4_SSL(imap_server, imap_port)
        conn.login(imap_email, imap_password)
        conn.select("INBOX", readonly=True)

        # UID SEARCH for emails with UID > last_uid
        # UID range: (last_uid+1):* means "from last_uid+1 to the latest"
        if last_uid > 0:
            search_range = f"{last_uid + 1}:*"
            status, data = conn.uid("SEARCH", None, f"UID {search_range}")
        else:
            # First run: fetch all emails in inbox
            status, data = conn.uid("SEARCH", None, "ALL")

        if status != "OK" or not data[0]:
            logger.debug("[IMAP] No new emails found")
            return [], last_uid

        uid_list = data[0].split()
        # Filter out UIDs <= last_uid (IMAP range search can include the boundary)
        uid_list = [uid for uid in uid_list if int(uid) > last_uid]

        if not uid_list:
            logger.debug("[IMAP] No new emails after UID filtering")
            return [], last_uid

        logger.info(f"[IMAP] Found {len(uid_list)} new email(s) (UIDs > {last_uid})")

        for uid in uid_list:
            uid_int = int(uid)
            try:
                status, data = conn.uid("FETCH", uid, "(RFC822)")
                if status != "OK" or not data or not data[0]:
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                from_header = decode_mime_header(msg.get("From", ""))
                to_header = decode_mime_header(msg.get("To", ""))
                cc_header = decode_mime_header(msg.get("Cc", ""))
                subject = decode_mime_header(msg.get("Subject", ""))
                message_id = msg.get("Message-ID", "").strip()
                in_reply_to = msg.get("In-Reply-To", "").strip()
                references = msg.get("References", "").strip()
                email_date = parse_email_date(msg)

                _, sender_email = parseaddr(from_header)
                sender_email = sender_email.lower() if sender_email else ""

                sender_name, _ = parseaddr(from_header)
                if not sender_name:
                    sender_name = sender_email.split("@")[0].replace(".", " ").title() if sender_email else "Unknown"

                body = extract_body(msg)

                preview = (body["text"] or "")[:150].strip()
                if len(body["text"] or "") > 150:
                    preview += "..."

                emails.append({
                    "imap_uid": uid_int,
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

                if uid_int > max_uid:
                    max_uid = uid_int

            except Exception as e:
                logger.error(f"[IMAP] Error parsing email UID {uid}: {e}")
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

    return emails, max_uid


# Keep the old function signature for backward compatibility with the manual sync endpoint
def fetch_new_emails(config: Dict[str, Any], since_minutes: int = 2, fetch_all: bool = False) -> List[Dict[str, Any]]:
    """Legacy wrapper - calls fetch_emails_by_uid with uid=0 to fetch all."""
    emails, _ = fetch_emails_by_uid(config, last_uid=0)
    return emails
