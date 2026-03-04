"""
IMAP email poller for Trinity — reads inbound emails from Gmail and matches to tickets.
Production-grade with connection resilience, sanitization, retry processing.
Runs as a background daemon thread.

Matching pipeline (designed so 99 % of replies match on steps 1-4):
  1.  In-Reply-To  → exact match on stored message_ids
  2.  References    → any ref in the chain matches a stored message_id
  3.  Gmail Thread ID → same X-GM-THRID as an existing thread record
  4.  References overlap → any stored record shares a reference
  --- fallbacks (handle edge-cases / SES Message-ID rewrites) ---
  5.  Ticket ID in body  → "TKT-XXXXXX" in the quoted text
  6.  Subject + sender   → strip Re:/Fwd: and match title+customer_email
"""
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
import os
import re
import uuid
import html as html_lib
import logging
import time
import threading
from datetime import datetime, timezone, timedelta

from database import email_threads_collection, tickets_collection, messages_collection

logger = logging.getLogger("email_poller")

_poller_thread = None
_stop_event = threading.Event()

# ── DB indexes (idempotent, run once on import) ──────────────
try:
    email_threads_collection.create_index("message_id")
    email_threads_collection.create_index("gmail_thread_id")
    email_threads_collection.create_index("ticket_id")
    email_threads_collection.create_index([("ticket_id", 1), ("direction", 1), ("created_at", 1)])
except Exception:
    pass  # non-critical if indexes already exist or collection missing


def _get_env(key, default=""):
    return os.environ.get(key, default)


def _parse_email_date(msg) -> datetime:
    """Extract the Date header from an email and return a UTC datetime.
    Falls back to datetime.now(UTC) if parsing fails."""
    date_str = msg.get("Date", "")
    if date_str:
        try:
            dt = parsedate_to_datetime(date_str)
            # Convert to UTC if timezone-aware
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


# ── Header / body helpers ────────────────────────────────────

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


def _extract_email_parts(msg) -> dict:
    """Extract plain text, HTML, and a stripped summary from an email message.

    Returns:
        {
            "content":    cleaned plain text (quotes stripped) – for search/preview,
            "email_html": full HTML body (or "") – for rich rendering,
            "email_text": full plain text (or "") – for fallback rendering,
        }
    """
    text_body = ""
    html_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if "attachment" in cd:
                continue
            if ct == "text/plain" and not text_body:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        text_body = payload.decode("utf-8", errors="replace")
                except Exception:
                    try:
                        text_body = part.get_payload(decode=True).decode("latin-1", errors="replace")
                    except Exception:
                        pass
            elif ct == "text/html" and not html_body:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_body = payload.decode("utf-8", errors="replace")
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                raw = payload.decode("utf-8", errors="replace")
                ct = msg.get_content_type()
                if ct == "text/html":
                    html_body = raw
                else:
                    text_body = raw
        except Exception:
            text_body = str(msg.get_payload() or "")

    # Use whichever is available as the base for stripping
    base = text_body or html_body

    # Strip quoted text for the clean content field
    lines = base.split("\n")
    clean_lines = []
    for line in lines:
        stripped = line.strip()
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

    content = "\n".join(clean_lines).strip()
    content = _sanitize_body(content if content else base)

    return {
        "content": content,
        "email_html": html_body,
        "email_text": text_body,
    }


def _extract_reply_body(msg) -> str:
    """Legacy wrapper — returns only the stripped content string."""
    return _extract_email_parts(msg)["content"]


# ── Ticket matching pipeline ─────────────────────────────────

def _match_ticket(msg, gmail_thrid=None, body_text="") -> dict:
    """
    Match an inbound email to a ticket.

    The pipeline is ordered so that the most reliable signals come first.
    Steps 1-4 rely on email-standard threading headers and Gmail metadata.
    Steps 5-6 are defensive fallbacks for edge-cases (SES ID rewrites, header stripping).
    """
    in_reply_to = msg.get("In-Reply-To", "").strip()
    references_raw = msg.get("References", "")
    references = references_raw.split() if references_raw else []
    from_addr = parseaddr(msg.get("From", ""))[1].lower()
    subject = _decode_header_value(msg.get("Subject", ""))

    # Also check X-Ticket-ID custom header (set by our outbound emails)
    x_ticket_id = msg.get("X-Ticket-ID", "").strip()

    # 1. In-Reply-To  — the customer's client sets this to the Message-ID
    #    of the email they clicked "Reply" on.  Fastest, most precise match.
    if in_reply_to:
        thread = email_threads_collection.find_one(
            {"message_id": in_reply_to, "ticket_id": {"$ne": None}},
            {"_id": 0, "ticket_id": 1},
        )
        if thread and thread.get("ticket_id"):
            return {"ticket_id": thread["ticket_id"], "match_method": "in_reply_to"}

    # 2. References chain — walk backwards (most-recent first) to find
    #    any message_id we have on record.
    for ref in reversed(references):
        ref = ref.strip()
        if ref:
            thread = email_threads_collection.find_one(
                {"message_id": ref, "ticket_id": {"$ne": None}},
                {"_id": 0, "ticket_id": 1},
            )
            if thread and thread.get("ticket_id"):
                return {"ticket_id": thread["ticket_id"], "match_method": "references"}

    # 3. Gmail Thread ID — Gmail assigns a stable thread ID across the
    #    entire conversation, even when headers are mangled.
    if gmail_thrid:
        thread = email_threads_collection.find_one(
            {"gmail_thread_id": gmail_thrid, "ticket_id": {"$ne": None}},
            {"_id": 0, "ticket_id": 1},
        )
        if thread and thread.get("ticket_id"):
            return {"ticket_id": thread["ticket_id"], "match_method": "gmail_thread_id"}

    # 4. References overlap — an existing record shares at least one
    #    reference with this email (catches forwarded / CC'd threads).
    if references:
        thread = email_threads_collection.find_one(
            {"references": {"$in": references}, "ticket_id": {"$ne": None}},
            {"_id": 0, "ticket_id": 1},
        )
        if thread and thread.get("ticket_id"):
            return {"ticket_id": thread["ticket_id"], "match_method": "references_overlap"}

    # ── Fallbacks ────────────────────────────────────────────

    # 5a. X-Ticket-ID header (set by our outbound, may survive in reply)
    if x_ticket_id:
        ticket = tickets_collection.find_one(
            {"ticket_id": x_ticket_id},
            {"_id": 0, "ticket_id": 1},
        )
        if ticket:
            return {"ticket_id": x_ticket_id, "match_method": "x_ticket_id_header"}

    # 5b. Ticket ID in the email body (quoted reply text often includes "Ticket: TKT-XXXXXX")
    full_text = body_text or ""
    ticket_id_match = re.search(r"(?:Ticket|TKT)[-:\s]*(TKT-\d{4,})", full_text, re.IGNORECASE)
    if ticket_id_match:
        candidate_id = ticket_id_match.group(1)
        ticket = tickets_collection.find_one(
            {"ticket_id": candidate_id},
            {"_id": 0, "ticket_id": 1},
        )
        if ticket:
            return {"ticket_id": candidate_id, "match_method": "body_ticket_id"}

    # 6. Subject + sender — strip Re:/Fwd: and find a matching email-sourced
    #    ticket from the same customer.
    if subject and from_addr:
        clean_subject = re.sub(r"^(?:Re|Fwd|Fw)\s*:\s*", "", subject, flags=re.IGNORECASE).strip()
        # Strip multiple Re: layers  ("Re: Re: Re: ...")
        while re.match(r"^(?:Re|Fwd|Fw)\s*:\s*", clean_subject, re.IGNORECASE):
            clean_subject = re.sub(r"^(?:Re|Fwd|Fw)\s*:\s*", "", clean_subject, flags=re.IGNORECASE).strip()
        if clean_subject:
            ticket = tickets_collection.find_one(
                {
                    "customer_email": from_addr,
                    "title": clean_subject,
                    "source": "email",
                },
                {"_id": 0, "ticket_id": 1},
                sort=[("created_at", -1)],
            )
            if ticket:
                return {"ticket_id": ticket["ticket_id"], "match_method": "subject_email_match"}

    return None


# ── Dedup / own-email helpers ────────────────────────────────

def _is_already_processed(message_id: str) -> bool:
    if not message_id:
        return False
    return email_threads_collection.find_one({"message_id": message_id}) is not None


def _is_own_email(msg) -> bool:
    from_addr = parseaddr(msg.get("From", ""))[1].lower()
    sender_email = _get_env("SES_SENDER_EMAIL", "support@emergent.sh").lower()
    # Also check hey@ alias
    imap_user = _get_env("IMAP_USER", "").lower()
    return from_addr in (sender_email, imap_user)


# ── New ticket creation ──────────────────────────────────────

def _create_ticket_from_email(from_name: str, from_addr: str, subject: str, body: str,
                              email_parts: dict = None, email_date: datetime = None,
                              mail=None, gmail_thrid: str = None):
    """Create a new ticket from an inbound email that doesn't match any existing ticket.
    If a Gmail Thread ID and IMAP connection are available, fetches the full thread history."""
    from utils import generate_ticket_id

    if not from_addr or not body.strip():
        return None

    ticket_id = generate_ticket_id()
    title = subject.strip()[:200] if subject.strip() else f"Email from {from_addr}"
    email_date = email_date or datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)

    # If we have a Gmail Thread ID + IMAP connection, fetch full thread first
    thread_messages = []
    if mail and gmail_thrid:
        thread_messages = _fetch_full_thread(mail, gmail_thrid)

    if thread_messages:
        # Sort by email date (oldest first) for chronological ordering
        thread_messages.sort(key=lambda m: m["email_date"])

        # Use the oldest email's date as the ticket creation date
        oldest_date = thread_messages[0]["email_date"]
        tickets_collection.insert_one({
            "ticket_id": ticket_id,
            "uuid": str(uuid.uuid4()),
            "title": title,
            "description": thread_messages[0]["body"][:10000],
            "status": "todo",
            "priority": "medium",
            "tags": ["email"],
            "source": "email",
            "customer_email": from_addr,
            "customer_name": from_name or from_addr,
            "created_at": oldest_date,
            "updated_at": now,
            "last_message_at": thread_messages[-1]["email_date"],
            "last_customer_message_at": thread_messages[-1]["email_date"],
            "assignee_id": None,
            "escalation_level": "L1",
        })

        for i, tm in enumerate(thread_messages):
            msg_type = "original" if i == 0 else "customer_reply"
            # Skip if this specific message_id was already processed
            if tm["message_id"] and _is_already_processed(tm["message_id"]):
                # Still store the thread record for future matching
                _store_thread_record(tm, ticket_id, "thread_backfill")
                continue

            messages_collection.insert_one({
                "message_id": f"msg_{uuid.uuid4().hex[:12]}",
                "ticket_id": ticket_id,
                "type": msg_type,
                "content": tm["body"][:10000],
                "email_html": tm.get("email_html", ""),
                "email_text": tm.get("email_text", ""),
                "author_id": None,
                "author_name": tm["from_name"],
                "author_email": tm["from_addr"],
                "source": "email",
                "created_at": tm["email_date"],
                "email_date": tm["email_date"],
            })
            _store_thread_record(tm, ticket_id, "thread_backfill")

        logger.info(f"[THREAD] Captured {len(thread_messages)} messages for {ticket_id} (thread {gmail_thrid})")
    else:
        # No thread history available — create ticket with just this email
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
            "created_at": email_date,
            "updated_at": now,
            "last_message_at": email_date,
            "last_customer_message_at": email_date,
            "assignee_id": None,
            "escalation_level": "L1",
        })

        parts = email_parts or {}
        messages_collection.insert_one({
            "message_id": f"msg_{uuid.uuid4().hex[:12]}",
            "ticket_id": ticket_id,
            "type": "original",
            "content": body.strip()[:10000],
            "email_html": parts.get("email_html", ""),
            "email_text": parts.get("email_text", ""),
            "author_id": None,
            "author_name": from_name or from_addr,
            "author_email": from_addr,
            "source": "email",
            "created_at": email_date,
            "email_date": email_date,
        })

    return ticket_id


def _store_thread_record(tm: dict, ticket_id: str, match_method: str):
    """Store an email_threads record for a thread-backfilled message."""
    if tm.get("message_id") and _is_already_processed(tm["message_id"]):
        # Update existing record to link to this ticket
        email_threads_collection.update_one(
            {"message_id": tm["message_id"]},
            {"$set": {"ticket_id": ticket_id, "match_method": match_method}},
        )
        return

    email_threads_collection.insert_one({
        "thread_id": f"eth_{uuid.uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "message_id": tm.get("message_id", ""),
        "in_reply_to": tm.get("in_reply_to", ""),
        "references": tm.get("references", []),
        "gmail_thread_id": tm.get("gmail_thrid"),
        "direction": "inbound" if not tm.get("is_own") else "outbound",
        "status": "processed",
        "from_email": tm["from_addr"],
        "to_email": _get_env("SES_SENDER_EMAIL", "support@emergent.sh"),
        "subject": tm.get("subject", "")[:500],
        "body_preview": tm.get("body", "")[:200],
        "matched": True,
        "match_method": match_method,
        "email_date": tm["email_date"],
        "created_at": datetime.now(timezone.utc),
    })


def _fetch_full_thread(mail, gmail_thrid: str) -> list:
    """Fetch ALL messages in a Gmail thread by X-GM-THRID, regardless of age.
    Returns a list of parsed message dicts sorted for chronological insertion."""
    messages = []
    try:
        # Gmail-specific IMAP extension: search by thread ID
        status, data = mail.search(None, f"X-GM-THRID {gmail_thrid}")
        if status != "OK" or not data[0]:
            return messages

        thread_eids = data[0].split()
        logger.info(f"[THREAD] Found {len(thread_eids)} emails in thread {gmail_thrid}")

        sender_email = _get_env("SES_SENDER_EMAIL", "support@emergent.sh").lower()
        imap_user = _get_env("IMAP_USER", "").lower()

        for eid in thread_eids:
            try:
                status2, msg_data2 = mail.fetch(eid, "(RFC822)")
                if status2 != "OK" or not msg_data2 or not msg_data2[0]:
                    continue

                raw = msg_data2[0][1]
                msg = email.message_from_bytes(raw)

                msg_id = msg.get("Message-ID", "").strip()
                from_name, from_addr = parseaddr(msg.get("From", ""))
                from_name = _decode_header_value(from_name) or from_addr
                from_addr_lower = from_addr.lower()
                is_own = from_addr_lower in (sender_email, imap_user)

                subject = _decode_header_value(msg.get("Subject", ""))
                parts = _extract_email_parts(msg)
                msg_date = _parse_email_date(msg)

                in_reply_to = msg.get("In-Reply-To", "").strip()
                refs_raw = msg.get("References", "")
                refs = refs_raw.split() if refs_raw else []

                messages.append({
                    "message_id": msg_id,
                    "from_name": from_name,
                    "from_addr": from_addr,
                    "subject": subject,
                    "body": parts["content"],
                    "email_html": parts.get("email_html", ""),
                    "email_text": parts.get("email_text", ""),
                    "email_date": msg_date,
                    "in_reply_to": in_reply_to,
                    "references": refs,
                    "gmail_thrid": gmail_thrid,
                    "is_own": is_own,
                })
            except Exception as e:
                logger.error(f"[THREAD] Error fetching eid {eid} in thread {gmail_thrid}: {e}")

    except Exception as e:
        logger.error(f"[THREAD] IMAP search X-GM-THRID {gmail_thrid} failed: {e}")

    return messages


# ── Bounce handling ──────────────────────────────────────────

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


# ── Inbox processing ─────────────────────────────────────────

def poll_inbox():
    """Connect to IMAP, fetch emails from INBOX (last 7 days, newest first) and sent emails."""
    host = _get_env("IMAP_HOST", "imap.gmail.com")
    user = _get_env("IMAP_USER")
    password = _get_env("IMAP_PASSWORD")

    if not user or not password:
        return

    mail = None
    try:
        mail = imaplib.IMAP4_SSL(host, 993)
        mail.login(user, password)

        # 1. Process INBOX — ALL emails from last 7 days (not just UNSEEN), newest first
        mail.select("INBOX")
        since_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%d-%b-%Y")
        status, data = mail.search(None, f'SINCE {since_date}')
        if status == "OK" and data[0]:
            email_ids = data[0].split()
            email_ids.reverse()  # newest first
            logger.info(f"[POLL] INBOX: {len(email_ids)} emails (last 7d, newest first)")
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


# ── Sent-folder polling ──────────────────────────────────────

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
        sent_date = _parse_email_date(msg)
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
            "created_at": sent_date,
            "email_date": sent_date,
        })

        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": {"updated_at": datetime.now(timezone.utc)}},
        )

    # Store for dedup and threading
    sent_date = _parse_email_date(msg)
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
        "email_date": sent_date,
        "created_at": datetime.now(timezone.utc),
    })


# ── Inbound email processing ────────────────────────────────

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
    parts = _extract_email_parts(msg)
    body = parts["content"]
    email_date = _parse_email_date(msg)

    # Detect bounce/delivery failure notifications
    if _is_bounce_email(from_addr, subject):
        _handle_bounce(msg, from_addr, subject, body, message_id)
        return

    if not body.strip():
        return

    # Use the full email text (including quoted text) for ticket ID extraction
    full_text = parts.get("email_text") or parts.get("email_html") or body
    match = _match_ticket(msg, gmail_thrid=gmail_thrid, body_text=full_text)

    if match:
        ticket_id = match["ticket_id"]
        logger.info(f"[INBOUND] Matched {ticket_id} via {match['match_method']} from={from_addr}")

        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        messages_collection.insert_one({
            "message_id": msg_id,
            "ticket_id": ticket_id,
            "type": "customer_reply",
            "content": body.strip()[:10000],
            "email_html": parts["email_html"],
            "email_text": parts["email_text"],
            "author_id": None,
            "author_name": from_name,
            "author_email": from_addr,
            "source": "email",
            "created_at": email_date,
            "email_date": email_date,
        })

        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": {
                "status": "todo",
                "updated_at": datetime.now(timezone.utc),
                "last_customer_reply_at": email_date,
                "last_message_at": email_date,
                "last_customer_message_at": email_date,
            }},
        )
    else:
        # Create a new ticket from this email, with full thread capture
        ticket_id = _create_ticket_from_email(
            from_name, from_addr, subject, body,
            email_parts=parts, email_date=email_date,
            mail=mail, gmail_thrid=gmail_thrid,
        )
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
        "gmail_thread_id": gmail_thrid,
        "direction": "inbound",
        "status": "processed",
        "from_email": from_addr,
        "to_email": _get_env("SES_SENDER_EMAIL", "support@emergent.sh"),
        "subject": subject[:500],
        "body_preview": body[:200],
        "matched": match is not None,
        "match_method": match["match_method"] if match else None,
        "email_date": email_date,
        "created_at": datetime.now(timezone.utc),
    })


# ── Background poller ────────────────────────────────────────

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
