"""
IMAP email poller for Trinity — reads inbound emails from Gmail and matches to tickets.
Runs as a background thread.
"""
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
import os
import re
import uuid
import logging
import time
import threading
from datetime import datetime, timezone

from database import email_threads_collection, tickets_collection, messages_collection

logger = logging.getLogger("email_poller")

_poller_thread = None
_stop_event = threading.Event()


def _get_env(key, default=""):
    return os.environ.get(key, default)


def _decode_header_value(raw):
    """Decode an email header value that may be encoded."""
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _extract_reply_body(msg) -> str:
    """Extract the reply body, stripping quoted text."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    body = part.get_payload(decode=True).decode("latin-1", errors="replace")
                break
        if not body:
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/html":
                    try:
                        html = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        body = re.sub(r"<[^>]+>", "", html)
                        body = re.sub(r"\s+", " ", body).strip()
                    except Exception:
                        pass
                    break
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        except Exception:
            body = str(msg.get_payload())

    # Strip quoted text (lines starting with > or "On ... wrote:")
    lines = body.split("\n")
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^On .+ wrote:$", stripped):
            break
        if re.match(r"^>", stripped):
            continue
        if stripped.startswith("---"):
            break
        if "Original Message" in stripped:
            break
        if "Emergent Support" in stripped and "sent by" in stripped.lower():
            break
        clean_lines.append(line)

    result = "\n".join(clean_lines).strip()
    return result if result else body.strip()


def _match_ticket(msg) -> dict:
    """
    Match an inbound email to a ticket.
    Priority: In-Reply-To → References → sender + recent ticket.
    Returns {"ticket_id": ..., "match_method": ...} or None.
    """
    in_reply_to = msg.get("In-Reply-To", "").strip()
    references_raw = msg.get("References", "")
    references = references_raw.split() if references_raw else []
    from_addr = parseaddr(msg.get("From", ""))[1].lower()

    # 1. Match by In-Reply-To header
    if in_reply_to:
        thread = email_threads_collection.find_one(
            {"message_id": in_reply_to, "direction": "outbound"},
            {"_id": 0, "ticket_id": 1},
        )
        if thread and thread.get("ticket_id"):
            return {"ticket_id": thread["ticket_id"], "match_method": "in_reply_to"}

    # 2. Match by References chain
    for ref in reversed(references):
        ref = ref.strip()
        if ref:
            thread = email_threads_collection.find_one(
                {"message_id": ref, "direction": "outbound"},
                {"_id": 0, "ticket_id": 1},
            )
            if thread and thread.get("ticket_id"):
                return {"ticket_id": thread["ticket_id"], "match_method": "references"}

    # 3. Fallback: match by sender email + most recent open ticket
    if from_addr:
        ticket = tickets_collection.find_one(
            {
                "customer_email": from_addr,
                "status": {"$nin": ["closed"]},
            },
            {"_id": 0, "ticket_id": 1},
            sort=[("updated_at", -1)],
        )
        if ticket:
            return {"ticket_id": ticket["ticket_id"], "match_method": "sender_fallback"}

    return None


def _is_already_processed(message_id: str) -> bool:
    """Check if this email Message-ID has already been processed."""
    if not message_id:
        return False
    return email_threads_collection.find_one(
        {"message_id": message_id, "direction": "inbound"}
    ) is not None


def _is_own_email(msg) -> bool:
    """Check if this email was sent by us (to avoid processing our own outbound emails)."""
    from_addr = parseaddr(msg.get("From", ""))[1].lower()
    sender_email = _get_env("SES_SENDER_EMAIL", "support@emergent.sh").lower()
    return from_addr == sender_email


def poll_inbox():
    """Connect to IMAP, fetch unread emails, process them."""
    host = _get_env("IMAP_HOST", "imap.gmail.com")
    user = _get_env("IMAP_USER")
    password = _get_env("IMAP_PASSWORD")

    if not user or not password:
        logger.error("IMAP credentials not configured")
        return

    mail = None
    try:
        mail = imaplib.IMAP4_SSL(host, 993)
        mail.login(user, password)
        mail.select("INBOX")

        # Search for unseen emails
        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            logger.warning(f"IMAP search failed: {status}")
            return

        email_ids = data[0].split()
        if not email_ids:
            return

        logger.info(f"Found {len(email_ids)} unread email(s)")

        for eid in email_ids:
            try:
                _process_email(mail, eid)
            except Exception as e:
                logger.error(f"Error processing email {eid}: {e}", exc_info=True)

    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP error: {e}")
    except Exception as e:
        logger.error(f"IMAP connection error: {e}", exc_info=True)
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def _process_email(mail, eid):
    """Process a single email by ID."""
    status, msg_data = mail.fetch(eid, "(RFC822)")
    if status != "OK":
        return

    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    # Skip our own outbound emails
    if _is_own_email(msg):
        return

    message_id = msg.get("Message-ID", "").strip()

    # Skip already processed
    if _is_already_processed(message_id):
        logger.debug(f"Skipping already processed email: {message_id}")
        return

    from_name, from_addr = parseaddr(msg.get("From", ""))
    from_name = _decode_header_value(from_name) or from_addr
    subject = _decode_header_value(msg.get("Subject", ""))
    body = _extract_reply_body(msg)

    if not body.strip():
        logger.debug(f"Skipping empty email from {from_addr}")
        return

    # Match to ticket
    match = _match_ticket(msg)

    if match:
        ticket_id = match["ticket_id"]
        logger.info(f"Inbound email matched to {ticket_id} via {match['match_method']} | from={from_addr}")

        # Add reply as customer message in ticket
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        messages_collection.insert_one({
            "message_id": msg_id,
            "ticket_id": ticket_id,
            "type": "customer_reply",
            "content": body.strip()[:10000],
            "author_id": None,
            "author_name": from_name,
            "author_email": from_addr,
            "source": "email",
            "created_at": datetime.now(timezone.utc),
        })

        # Update ticket
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": {
                "status": "todo",
                "updated_at": datetime.now(timezone.utc),
                "last_customer_reply_at": datetime.now(timezone.utc),
            }},
        )
    else:
        logger.info(f"Inbound email from {from_addr} did not match any ticket | subject={subject}")

    # Store in email_threads for dedup and threading
    in_reply_to = msg.get("In-Reply-To", "").strip()
    references_raw = msg.get("References", "")
    references = references_raw.split() if references_raw else []

    email_threads_collection.insert_one({
        "thread_id": f"eth_{uuid.uuid4().hex[:12]}",
        "ticket_id": match["ticket_id"] if match else None,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "references": references,
        "direction": "inbound",
        "from_email": from_addr,
        "to_email": _get_env("SES_SENDER_EMAIL", "support@emergent.sh"),
        "subject": subject,
        "body_preview": body[:200] if body else "",
        "matched": match is not None,
        "match_method": match["match_method"] if match else None,
        "created_at": datetime.now(timezone.utc),
    })


def _poller_loop():
    """Background loop that polls IMAP inbox at regular intervals."""
    interval = int(_get_env("EMAIL_POLL_INTERVAL", "30"))
    logger.info(f"Email poller started | interval={interval}s")

    # Initial delay to let app start up
    time.sleep(5)

    backoff = 1
    while not _stop_event.is_set():
        try:
            poll_inbox()
            backoff = 1  # Reset on success
        except Exception as e:
            logger.error(f"Poller error (backoff={backoff}s): {e}")
            backoff = min(backoff * 2, 300)  # Max 5 min backoff

        _stop_event.wait(timeout=max(interval, backoff))


def start_poller():
    """Start the IMAP poller in a background daemon thread."""
    global _poller_thread
    if _poller_thread and _poller_thread.is_alive():
        logger.warning("Email poller already running")
        return

    user = _get_env("IMAP_USER")
    password = _get_env("IMAP_PASSWORD")
    if not user or not password:
        logger.warning("IMAP credentials not set — email poller disabled")
        return

    _stop_event.clear()
    _poller_thread = threading.Thread(target=_poller_loop, daemon=True, name="email-poller")
    _poller_thread.start()
    logger.info("Email poller thread started")


def stop_poller():
    """Stop the IMAP poller."""
    _stop_event.set()
    if _poller_thread:
        _poller_thread.join(timeout=10)
    logger.info("Email poller stopped")
