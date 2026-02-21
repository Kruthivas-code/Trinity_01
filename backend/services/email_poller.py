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


def _match_ticket(msg, gmail_thrid=None) -> dict:
    """
    Match an inbound email to a ticket.
    Priority: In-Reply-To -> References -> Gmail Thread ID.
    """
    in_reply_to = msg.get("In-Reply-To", "").strip()
    references_raw = msg.get("References", "")
    references = references_raw.split() if references_raw else []

    # 1. Match by In-Reply-To
    if in_reply_to:
        thread = email_threads_collection.find_one(
            {"message_id": in_reply_to, "direction": {"$in": ["outbound", "outbound_gmail"]}},
            {"_id": 0, "ticket_id": 1},
        )
        if thread and thread.get("ticket_id"):
            return {"ticket_id": thread["ticket_id"], "match_method": "in_reply_to"}

    # 2. Match by References chain (newest first)
    for ref in reversed(references):
        ref = ref.strip()
        if ref:
            thread = email_threads_collection.find_one(
                {"message_id": ref, "direction": {"$in": ["outbound", "outbound_gmail"]}},
                {"_id": 0, "ticket_id": 1},
            )
            if thread and thread.get("ticket_id"):
                return {"ticket_id": thread["ticket_id"], "match_method": "references"}

    # 3. Match by Gmail Thread ID
    if gmail_thrid:
        thread = email_threads_collection.find_one(
            {"gmail_thread_id": gmail_thrid, "ticket_id": {"$ne": None}},
            {"_id": 0, "ticket_id": 1},
        )
        if thread and thread.get("ticket_id"):
            return {"ticket_id": thread["ticket_id"], "match_method": "gmail_thread_id"}

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
    """Connect to IMAP, fetch unread emails from INBOX and new sent emails."""
    host = _get_env("IMAP_HOST", "imap.gmail.com")
    user = _get_env("IMAP_USER")
    password = _get_env("IMAP_PASSWORD")

    if not user or not password:
        return

    mail = None
    try:
        mail = imaplib.IMAP4_SSL(host, 993)
        mail.login(user, password)

        # 1. Process INBOX (incoming customer emails)
        mail.select("INBOX")
        status, data = mail.search(None, "UNSEEN")
        if status == "OK" and data[0]:
            email_ids = data[0].split()
            logger.info(f"[POLL] INBOX: {len(email_ids)} unread")
            for eid in email_ids:
                try:
                    _process_email(mail, eid, folder="inbox")
                except Exception as e:
                    logger.error(f"[POLL] INBOX error {eid}: {e}", exc_info=True)

        # 2. Process Sent Mail (detect agent replies from Gmail)
        _poll_sent_folder(mail)

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


def _get_last_sent_uid():
    """Get the last processed UID from the Sent folder."""
    state = email_threads_collection.find_one(
        {"_type": "sent_sync_state"},
        {"_id": 0, "last_uid": 1},
    )
    return state.get("last_uid", 0) if state else 0


def _set_last_sent_uid(uid):
    """Store the last processed Sent folder UID."""
    email_threads_collection.update_one(
        {"_type": "sent_sync_state"},
        {"$set": {"last_uid": uid, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


def _poll_sent_folder(mail):
    """Poll Gmail Sent Mail for agent replies sent outside Trinity."""
    try:
        status, _ = mail.select('"[Gmail]/Sent Mail"', readonly=True)
        if status != "OK":
            return

        last_uid = _get_last_sent_uid()

        # Fetch emails with UID greater than our last processed
        if last_uid > 0:
            search_criteria = f"(UID {last_uid + 1}:*)"
        else:
            # First run: only look at emails from the last 24 hours
            from datetime import timedelta
            since_date = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%d-%b-%Y")
            search_criteria = f'(SINCE "{since_date}")'

        status, data = mail.uid("search", None, search_criteria)
        if status != "OK" or not data[0]:
            return

        uids = data[0].split()
        if not uids:
            return

        new_count = 0
        max_uid = last_uid
        for uid in uids:
            uid_int = int(uid)
            if uid_int <= last_uid:
                continue
            if uid_int > max_uid:
                max_uid = uid_int
            try:
                _process_sent_email(mail, uid)
                new_count += 1
            except Exception as e:
                logger.error(f"[SENT] Error processing UID {uid}: {e}", exc_info=True)

        if max_uid > last_uid:
            _set_last_sent_uid(max_uid)

        if new_count:
            logger.info(f"[SENT] Processed {new_count} sent email(s)")

    except Exception as e:
        logger.error(f"[SENT] Error polling sent folder: {e}", exc_info=True)


def _process_sent_email(mail, uid):
    """Process a sent email — detect if it's a reply to a ticket thread."""
    status, msg_data = mail.uid("fetch", uid, "(RFC822 X-GM-THRID)")
    if status != "OK" or not msg_data or not msg_data[0]:
        return

    # Extract Gmail Thread ID
    gmail_thrid = None
    if isinstance(msg_data[0][0], bytes):
        thrid_match = re.search(rb"X-GM-THRID (\d+)", msg_data[0][0])
        if thrid_match:
            gmail_thrid = thrid_match.group(1).decode()

    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    message_id = msg.get("Message-ID", "").strip()
    if _is_already_processed(message_id):
        return

    from_name, from_addr = parseaddr(msg.get("From", ""))
    sender_email = _get_env("SES_SENDER_EMAIL", "support@emergent.sh").lower()
    imap_user = _get_env("IMAP_USER", "").lower()

    # Only process emails sent FROM our support address
    if from_addr.lower() not in (sender_email, imap_user):
        return

    in_reply_to = msg.get("In-Reply-To", "").strip()
    references_raw = msg.get("References", "")
    references = references_raw.split() if references_raw else []
    subject = _decode_header_value(msg.get("Subject", ""))
    to_addr = parseaddr(msg.get("To", ""))[1]
    body = _extract_reply_body(msg)

    # Match to ticket via threading headers
    ticket_id = None
    match_method = None

    # 1. Check In-Reply-To against our inbound email records
    if in_reply_to:
        thread = email_threads_collection.find_one(
            {"message_id": in_reply_to, "direction": "inbound"},
            {"_id": 0, "ticket_id": 1},
        )
        if thread and thread.get("ticket_id"):
            ticket_id = thread["ticket_id"]
            match_method = "in_reply_to"

    # 2. Check References
    if not ticket_id:
        for ref in reversed(references):
            ref = ref.strip()
            if ref:
                thread = email_threads_collection.find_one(
                    {"message_id": ref, "direction": "inbound"},
                    {"_id": 0, "ticket_id": 1},
                )
                if thread and thread.get("ticket_id"):
                    ticket_id = thread["ticket_id"]
                    match_method = "references"
                    break

    # 3. Check Gmail Thread ID
    if not ticket_id and gmail_thrid:
        thread = email_threads_collection.find_one(
            {"gmail_thread_id": gmail_thrid, "ticket_id": {"$ne": None}},
            {"_id": 0, "ticket_id": 1},
        )
        if thread and thread.get("ticket_id"):
            ticket_id = thread["ticket_id"]
            match_method = "gmail_thread_id"

    if ticket_id and body.strip():
        from_name = _decode_header_value(from_name) or from_addr
        logger.info(f"[SENT] Matched {ticket_id} via {match_method} to={to_addr}")

        # Add as agent reply in the ticket
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        messages_collection.insert_one({
            "message_id": msg_id,
            "ticket_id": ticket_id,
            "type": "reply",
            "content": body.strip()[:10000],
            "author_id": None,
            "author_name": from_name or "Support Agent",
            "author_email": from_addr,
            "source": "email",
            "created_at": datetime.now(timezone.utc),
        })

        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": {"updated_at": datetime.now(timezone.utc)}},
        )

    # Store for dedup and threading
    email_threads_collection.insert_one({
        "thread_id": f"eth_{uuid.uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "references": references,
        "gmail_thread_id": gmail_thrid,
        "direction": "outbound_gmail",
        "status": "processed",
        "from_email": from_addr,
        "to_email": to_addr,
        "subject": subject[:500],
        "body_preview": body[:200] if body else "",
        "matched": ticket_id is not None,
        "match_method": match_method,
        "created_at": datetime.now(timezone.utc),
    })


BOUNCE_SENDERS = {
    "mailer-daemon", "postmaster", "mail-daemon", "mailerdaemon",
    "noreply", "no-reply", "auto-reply", "autoreply",
}

BOUNCE_SUBJECT_PATTERNS = [
    r"delivery.*(?:fail|status|notification)",
    r"undeliverable",
    r"returned mail",
    r"mail delivery.*failed",
    r"failure notice",
    r"bounce",
    r"rejected",
    r"could not.*deliver",
]


def _is_bounce_email(from_addr: str, subject: str) -> bool:
    """Detect if an email is a bounce/delivery failure notification."""
    local_part = from_addr.split("@")[0].lower() if "@" in from_addr else from_addr.lower()
    if local_part in BOUNCE_SENDERS:
        return True
    subject_lower = subject.lower()
    for pattern in BOUNCE_SUBJECT_PATTERNS:
        if re.search(pattern, subject_lower):
            return True
    return False


def _handle_bounce(msg, from_addr: str, subject: str, body: str, message_id: str):
    """Process a bounce email — find the original outbound email and mark it as bounced."""
    in_reply_to = msg.get("In-Reply-To", "").strip()
    references_raw = msg.get("References", "")
    references = references_raw.split() if references_raw else []

    # Try to find the original outbound email that bounced
    bounced_ticket_id = None
    for ref in [in_reply_to] + references:
        ref = ref.strip()
        if ref:
            thread = email_threads_collection.find_one(
                {"message_id": ref, "direction": "outbound"},
                {"_id": 0, "ticket_id": 1, "to_email": 1},
            )
            if thread:
                bounced_ticket_id = thread.get("ticket_id")
                # Mark the outbound email as bounced
                email_threads_collection.update_one(
                    {"message_id": ref, "direction": "outbound"},
                    {"$set": {"status": "bounced", "bounce_reason": subject[:200], "bounced_at": datetime.now(timezone.utc)}},
                )
                logger.warning(f"[BOUNCE] Ticket {bounced_ticket_id} — email to {thread.get('to_email')} bounced: {subject[:80]}")
                break

    # Also try to extract bounced address from body
    if not bounced_ticket_id and body:
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", body)
        if email_match:
            bounced_addr = email_match.group(0).lower()
            thread = email_threads_collection.find_one(
                {"to_email": bounced_addr, "direction": "outbound"},
                {"_id": 0, "ticket_id": 1, "message_id": 1},
                sort=[("created_at", -1)],
            )
            if thread:
                bounced_ticket_id = thread.get("ticket_id")
                email_threads_collection.update_one(
                    {"message_id": thread["message_id"], "direction": "outbound"},
                    {"$set": {"status": "bounced", "bounce_reason": subject[:200], "bounced_at": datetime.now(timezone.utc)}},
                )
                logger.warning(f"[BOUNCE] Ticket {bounced_ticket_id} — email to {bounced_addr} bounced (body match): {subject[:80]}")

    # Store the bounce record
    email_threads_collection.insert_one({
        "thread_id": f"eth_{uuid.uuid4().hex[:12]}",
        "ticket_id": bounced_ticket_id,
        "message_id": message_id,
        "direction": "bounce",
        "status": "processed",
        "from_email": from_addr,
        "subject": subject[:500],
        "body_preview": body[:200] if body else "",
        "created_at": datetime.now(timezone.utc),
    })

    if not bounced_ticket_id:
        logger.info(f"[BOUNCE] Unmatched bounce from={from_addr} subject={subject[:60]}")


def _process_email(mail, eid, folder="inbox"):
    """Process a single inbound email by sequence ID."""
    # Fetch with Gmail Thread ID
    status, msg_data = mail.fetch(eid, "(RFC822 X-GM-THRID)")
    if status != "OK" or not msg_data or not msg_data[0]:
        return

    # Extract Gmail Thread ID
    gmail_thrid = None
    if isinstance(msg_data[0][0], bytes):
        thrid_match = re.search(rb"X-GM-THRID (\d+)", msg_data[0][0])
        if thrid_match:
            gmail_thrid = thrid_match.group(1).decode()

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

    # Detect bounce/delivery failure notifications
    if _is_bounce_email(from_addr, subject):
        _handle_bounce(msg, from_addr, subject, body, message_id)
        return

    if not body.strip():
        return

    match = _match_ticket(msg, gmail_thrid=gmail_thrid)

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
        "ticket_id": match["ticket_id"] if match else (ticket_id if not match else None),
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "references": references,
        "gmail_thread_id": gmail_thrid,
        "direction": "inbound",
        "status": "processed",
        "from_email": from_addr,
        "to_email": _get_env("SES_SENDER_EMAIL", "support@emergent.sh"),
        "subject": subject[:500],
        "body_preview": body[:200],
        "matched": match is not None,
        "match_method": match["match_method"] if match else "new_ticket",
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
