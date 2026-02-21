"""
IMAP email poller for Trinity — reads inbound emails from Gmail and matches to tickets.
Production-grade with connection resilience, sanitization, retry processing.
Runs as a background daemon thread.
"""
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
import os
import re
import uuid
import html as html_lib
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
    try:
        parts = decode_header(raw)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(part)
        return "".join(decoded)
    except Exception:
        return str(raw)


def _sanitize_body(text: str) -> str:
    """Sanitize inbound email body — strip dangerous content, normalize whitespace."""
    if not text:
        return ""
    # Remove null bytes
    text = text.replace("\x00", "")
    # Strip HTML tags if present (we only want plain text in the DB)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # If still has HTML tags, strip them
    if re.search(r"<[^>]+>", text):
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = html_lib.unescape(text)
    # Normalize whitespace
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()[:10000]


def _extract_reply_body(msg) -> str:
    """Extract the reply body, stripping quoted text."""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="replace")
                except Exception:
                    try:
                        body = part.get_payload(decode=True).decode("latin-1", errors="replace")
                    except Exception:
                        pass
                break
        # Fallback to HTML if no plain text
        if not body.strip():
            for part in msg.walk():
                ct = part.get_content_type()
                cd = str(part.get("Content-Disposition", ""))
                if ct == "text/html" and "attachment" not in cd:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="replace")
                    except Exception:
                        pass
                    break
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")
        except Exception:
            body = str(msg.get_payload() or "")

    # Strip quoted text
    lines = body.split("\n")
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        # Stop at common quote markers
        if re.match(r"^On .+ wrote:\s*$", stripped):
            break
        if stripped.startswith(">"):
            continue
        if stripped == "---" or stripped.startswith("-----"):
            break
        if "Original Message" in stripped:
            break
        if re.match(r"^From:.+@", stripped):
            break
        if "Emergent Support" in stripped and "sent by" in stripped.lower():
            break
        clean_lines.append(line)

    result = "\n".join(clean_lines).strip()
    return _sanitize_body(result if result else body)


def _match_ticket(msg) -> dict:
    """
    Match an inbound email to a ticket.
    Priority: In-Reply-To -> References -> sender email + recent ticket.
    """
    in_reply_to = msg.get("In-Reply-To", "").strip()
    references_raw = msg.get("References", "")
    references = references_raw.split() if references_raw else []
    from_addr = parseaddr(msg.get("From", ""))[1].lower()

    # 1. Match by In-Reply-To
    if in_reply_to:
        thread = email_threads_collection.find_one(
            {"message_id": in_reply_to, "direction": "outbound"},
            {"_id": 0, "ticket_id": 1},
        )
        if thread and thread.get("ticket_id"):
            return {"ticket_id": thread["ticket_id"], "match_method": "in_reply_to"}

    # 2. Match by References chain (newest first)
    for ref in reversed(references):
        ref = ref.strip()
        if ref:
            thread = email_threads_collection.find_one(
                {"message_id": ref, "direction": "outbound"},
                {"_id": 0, "ticket_id": 1},
            )
            if thread and thread.get("ticket_id"):
                return {"ticket_id": thread["ticket_id"], "match_method": "references"}

    # 3. No fallback — only match via threading headers
    return None


def _is_already_processed(message_id: str) -> bool:
    if not message_id:
        return False
    return email_threads_collection.find_one({"message_id": message_id, "direction": "inbound"}) is not None


def _is_own_email(msg) -> bool:
    from_addr = parseaddr(msg.get("From", ""))[1].lower()
    sender_email = _get_env("SES_SENDER_EMAIL", "support@emergent.sh").lower()
    # Also check hey@ alias
    imap_user = _get_env("IMAP_USER", "").lower()
    return from_addr in (sender_email, imap_user)


def _create_ticket_from_email(from_name: str, from_addr: str, subject: str, body: str):
    """Create a new ticket from an inbound email that doesn't match any existing ticket."""
    from utils import generate_ticket_id

    if not from_addr or not body.strip():
        return None

    ticket_id = generate_ticket_id()
    title = subject.strip()[:200] if subject.strip() else f"Email from {from_addr}"
    now = datetime.now(timezone.utc)

    tickets_collection.insert_one({
        "ticket_id": ticket_id,
        "uuid": str(uuid.uuid4()),
        "title": title,
        "description": body.strip()[:10000],
        "status": "todo",
        "priority": "medium",
        "tags": ["email"],
        "source": "email",
        "customer_email": from_addr,
        "customer_name": from_name or from_addr,
        "created_at": now,
        "updated_at": now,
        "assignee_id": None,
        "escalation_level": "L1",
    })

    messages_collection.insert_one({
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "type": "original",
        "content": body.strip()[:10000],
        "author_id": None,
        "author_name": from_name or from_addr,
        "author_email": from_addr,
        "source": "email",
        "created_at": now,
    })

    return ticket_id


def poll_inbox():
    """Connect to IMAP, fetch unread emails, process them."""
    host = _get_env("IMAP_HOST", "imap.gmail.com")
    user = _get_env("IMAP_USER")
    password = _get_env("IMAP_PASSWORD")

    if not user or not password:
        return

    mail = None
    try:
        mail = imaplib.IMAP4_SSL(host, 993)
        mail.login(user, password)
        mail.select("INBOX")

        status, data = mail.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            return

        email_ids = data[0].split()
        logger.info(f"[POLL] {len(email_ids)} unread email(s)")

        processed = 0
        errors = 0
        for eid in email_ids:
            try:
                _process_email(mail, eid)
                processed += 1
            except Exception as e:
                errors += 1
                logger.error(f"[POLL] Error processing email {eid}: {e}", exc_info=True)

        if processed or errors:
            logger.info(f"[POLL] Processed={processed} errors={errors}")

    except imaplib.IMAP4.abort as e:
        logger.error(f"[POLL] IMAP connection aborted: {e}")
    except imaplib.IMAP4.error as e:
        logger.error(f"[POLL] IMAP error: {e}")
    except (ConnectionError, OSError, TimeoutError) as e:
        logger.error(f"[POLL] Connection error: {e}")
    except Exception as e:
        logger.error(f"[POLL] Unexpected: {e}", exc_info=True)
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def _process_email(mail, eid):
    """Process a single email by ID."""
    status, msg_data = mail.fetch(eid, "(RFC822)")
    if status != "OK" or not msg_data or not msg_data[0]:
        return

    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    if _is_own_email(msg):
        return

    message_id = msg.get("Message-ID", "").strip()
    if _is_already_processed(message_id):
        return

    from_name, from_addr = parseaddr(msg.get("From", ""))
    from_name = _decode_header_value(from_name) or from_addr
    subject = _decode_header_value(msg.get("Subject", ""))
    body = _extract_reply_body(msg)

    if not body.strip():
        return

    match = _match_ticket(msg)

    if match:
        ticket_id = match["ticket_id"]
        logger.info(f"[INBOUND] Matched {ticket_id} via {match['match_method']} from={from_addr}")

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

        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": {
                "status": "todo",
                "updated_at": datetime.now(timezone.utc),
                "last_customer_reply_at": datetime.now(timezone.utc),
            }},
        )
    else:
        # Create a new ticket from this email
        ticket_id = _create_ticket_from_email(from_name, from_addr, subject, body)
        if ticket_id:
            match = {"ticket_id": ticket_id, "match_method": "new_ticket"}
            logger.info(f"[INBOUND] New ticket {ticket_id} from={from_addr} subject={subject[:60]}")
        else:
            logger.info(f"[INBOUND] Skipped from={from_addr} subject={subject[:60]}")

    # Store for dedup and threading
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
        "status": "processed",
        "from_email": from_addr,
        "to_email": _get_env("SES_SENDER_EMAIL", "support@emergent.sh"),
        "subject": subject[:500],
        "body_preview": body[:200],
        "matched": match is not None,
        "match_method": match["match_method"] if match else None,
        "created_at": datetime.now(timezone.utc),
    })


def _poller_loop():
    """Background loop: polls IMAP + processes retry queue."""
    interval = int(_get_env("EMAIL_POLL_INTERVAL", "30"))
    logger.info(f"[POLLER] Started | interval={interval}s")
    time.sleep(5)  # startup delay

    backoff = 1
    retry_cycle = 0

    while not _stop_event.is_set():
        try:
            poll_inbox()
            backoff = 1

            # Process retry queue every 5 cycles (~2.5 min at 30s interval)
            retry_cycle += 1
            if retry_cycle >= 5:
                retry_cycle = 0
                try:
                    from services.email_service import retry_failed_emails
                    retried = retry_failed_emails()
                    if retried:
                        logger.info(f"[RETRY] Retried {retried} email(s)")
                except Exception as e:
                    logger.error(f"[RETRY] Error: {e}")

        except Exception as e:
            logger.error(f"[POLLER] Error (backoff={backoff}s): {e}")
            backoff = min(backoff * 2, 300)

        _stop_event.wait(timeout=max(interval, backoff))


def start_poller():
    """Start the IMAP poller in a background daemon thread."""
    global _poller_thread
    if _poller_thread and _poller_thread.is_alive():
        logger.warning("[POLLER] Already running")
        return

    user = _get_env("IMAP_USER")
    password = _get_env("IMAP_PASSWORD")
    if not user or not password:
        logger.warning("[POLLER] IMAP credentials not set — disabled")
        return

    _stop_event.clear()
    _poller_thread = threading.Thread(target=_poller_loop, daemon=True, name="email-poller")
    _poller_thread.start()
    logger.info("[POLLER] Thread started")


def stop_poller():
    """Stop the IMAP poller."""
    _stop_event.set()
    if _poller_thread:
        _poller_thread.join(timeout=10)
    logger.info("[POLLER] Stopped")
