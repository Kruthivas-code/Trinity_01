"""
IMAP Email Sync Module for Trinity

Connects to a Gmail mailbox via IMAP and converts incoming emails into tickets.
Uses UID-based tracking to ensure no emails are missed.
Supports IMAP IDLE for near-realtime push notifications (~1-5s latency).
"""

import imaplib
import email
import email.message
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
import os
import re
import socket
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Callable, Optional

logger = logging.getLogger(__name__)

# IDLE re-issue interval (Gmail drops IDLE after ~29 min)
IDLE_RENEW_SECONDS = 25 * 60  # 25 minutes
# How long to wait for IDLE responses before re-checking
IDLE_POLL_SECONDS = 30


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


def _parse_raw_email(uid_int: int, raw_email: bytes) -> Optional[Dict[str, Any]]:
    """Parse a raw email into our standard dict format."""
    try:
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

        return {
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
        }
    except Exception as e:
        logger.error(f"[IMAP] Error parsing email UID {uid_int}: {e}")
        return None


def _close_connection(conn):
    """Force-close an IMAP connection without hanging."""
    if not conn:
        return
    try:
        conn.socket().settimeout(0.5)
        conn.logout()
    except Exception:
        pass
    try:
        conn.socket().close()
    except Exception:
        pass


def fetch_emails_by_uid(config: Dict[str, Any], last_uid: int = 0) -> Tuple[List[Dict[str, Any]], int]:
    """
    Connect to IMAP server and fetch emails with UID greater than last_uid.
    Uses IMAP UID commands for reliable, gap-free email fetching.
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
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)
        try:
            conn = imaplib.IMAP4_SSL(imap_server, imap_port)
        finally:
            socket.setdefaulttimeout(old_timeout)
        conn.socket().settimeout(30)
        conn.login(imap_email, imap_password)
        conn.select("INBOX", readonly=True)

        if last_uid > 0:
            search_range = f"{last_uid + 1}:*"
            status, data = conn.uid("SEARCH", None, f"UID {search_range}")
        else:
            status, data = conn.uid("SEARCH", None, "ALL")

        if status != "OK" or not data[0]:
            logger.debug("[IMAP] No new emails found")
            return [], last_uid

        uid_list = data[0].split()
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
                parsed = _parse_raw_email(uid_int, data[0][1])
                if parsed:
                    emails.append(parsed)
                    if uid_int > max_uid:
                        max_uid = uid_int
            except Exception as e:
                logger.error(f"[IMAP] Error fetching email UID {uid}: {e}")
                continue

    except imaplib.IMAP4.error as e:
        logger.error(f"[IMAP] IMAP error: {e}")
    except Exception as e:
        logger.error(f"[IMAP] Connection error: {e}")
    finally:
        _close_connection(conn)

    return emails, max_uid


def get_current_max_uid(config: Dict[str, Any]) -> int:
    """Get the current highest UID in the INBOX without fetching any emails."""
    imap_email = config["email"]
    imap_password = config["password"]
    imap_server = config["server"]
    imap_port = config["port"]

    if not imap_email or not imap_password:
        return 0

    conn = None
    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)
        try:
            conn = imaplib.IMAP4_SSL(imap_server, imap_port)
        finally:
            socket.setdefaulttimeout(old_timeout)
        conn.socket().settimeout(30)
        conn.login(imap_email, imap_password)
        typ, data = conn.select("INBOX", readonly=True)
        msg_count = int(data[0]) if typ == "OK" else 0

        if msg_count == 0:
            return 0

        typ2, data2 = conn.fetch(str(msg_count), "(UID)")
        if typ2 == "OK" and data2:
            match = re.search(rb"UID (\d+)", data2[0] if isinstance(data2[0], bytes) else data2[0][0])
            if match:
                return int(match.group(1))
        return 0
    except Exception as e:
        logger.error(f"[IMAP] Error getting max UID: {e}")
        return 0
    finally:
        _close_connection(conn)


# ============================================================
# IMAP IDLE - Push-based near-realtime email monitoring
# ============================================================

class IMAPIdleWatcher:
    """
    Watches a Gmail IMAP inbox using IDLE for near-realtime email notifications.
    
    When new mail arrives, calls the on_new_mail callback with the list of new
    parsed emails and the new max UID.
    
    Architecture:
    - Runs in a background thread (IMAP IDLE is blocking)
    - Maintains a persistent connection to Gmail IMAP
    - Uses IDLE command to wait for server-side notifications
    - Renews IDLE every 25 minutes (Gmail drops after ~29 min)
    - Auto-reconnects on any failure with exponential backoff
    - Uses UID tracking to never miss emails
    """
    
    def __init__(self, config: Dict[str, Any], last_uid: int = 0,
                 on_new_mail: Optional[Callable] = None):
        self.config = config
        self.last_uid = last_uid
        self.on_new_mail = on_new_mail
        self._client = None
        self._stop_event = threading.Event()
        self._thread = None
        self._backoff = 5  # seconds, grows on repeated failures
    
    def start(self):
        """Start the IDLE watcher in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("[IDLE] Watcher already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="imap-idle")
        self._thread.start()
        logger.info("[IDLE] Watcher started")
    
    def stop(self):
        """Stop the IDLE watcher gracefully."""
        self._stop_event.set()
        self._disconnect()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("[IDLE] Watcher stopped")
    
    def update_last_uid(self, uid: int):
        """Update the last processed UID (called after successful processing)."""
        if uid > self.last_uid:
            self.last_uid = uid
    
    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
    
    def _connect(self):
        """Establish IMAP connection using imapclient."""
        from imapclient import IMAPClient
        
        self._disconnect()
        
        logger.info(f"[IDLE] Connecting to {self.config['server']}:{self.config['port']}")
        client = IMAPClient(
            self.config["server"],
            port=self.config["port"],
            ssl=True,
            timeout=30
        )
        client.login(self.config["email"], self.config["password"])
        client.select_folder("INBOX", readonly=True)
        
        # Verify IDLE is supported
        capabilities = client.capabilities()
        if b"IDLE" not in capabilities:
            raise RuntimeError("Server does not support IMAP IDLE")
        
        self._client = client
        self._backoff = 5  # Reset backoff on successful connection
        logger.info("[IDLE] Connected and INBOX selected")
    
    def _disconnect(self):
        """Disconnect the IMAP client."""
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
            self._client = None
    
    def _fetch_new_emails(self) -> Tuple[List[Dict[str, Any]], int]:
        """Fetch new emails using UID tracking on the current connection."""
        if not self._client:
            return [], self.last_uid
        
        emails = []
        max_uid = self.last_uid
        
        # Search for UIDs > last_uid
        if self.last_uid > 0:
            criteria = f"UID {self.last_uid + 1}:*"
        else:
            criteria = "ALL"
        
        uids = self._client.search(criteria)
        # Filter UIDs > last_uid (IMAP range can include boundary)
        uids = [u for u in uids if u > self.last_uid]
        
        if not uids:
            return [], self.last_uid
        
        logger.info(f"[IDLE] Found {len(uids)} new email(s) (UIDs > {self.last_uid})")
        
        # Fetch full message for each new UID
        for uid in uids:
            try:
                response = self._client.fetch([uid], ["RFC822"])
                if uid in response and b"RFC822" in response[uid]:
                    raw = response[uid][b"RFC822"]
                    parsed = _parse_raw_email(uid, raw)
                    if parsed:
                        emails.append(parsed)
                        if uid > max_uid:
                            max_uid = uid
            except Exception as e:
                logger.error(f"[IDLE] Error fetching UID {uid}: {e}")
                continue
        
        return emails, max_uid
    
    def _run_loop(self):
        """Main loop: connect → IDLE → process → repeat."""
        logger.info("[IDLE] Background thread started")
        
        while not self._stop_event.is_set():
            try:
                self._connect()
                
                # Initial check for any emails that arrived since last sync
                new_emails, new_max_uid = self._fetch_new_emails()
                if new_emails and self.on_new_mail:
                    self.on_new_mail(new_emails, new_max_uid)
                    self.last_uid = new_max_uid
                
                # Enter IDLE loop
                idle_start = time.monotonic()
                
                while not self._stop_event.is_set():
                    # Start IDLE
                    self._client.idle()
                    logger.debug("[IDLE] Entered IDLE mode, waiting for notifications...")
                    
                    # Wait for server responses (blocks until data or timeout)
                    try:
                        responses = self._client.idle_check(timeout=IDLE_POLL_SECONDS)
                    except Exception as e:
                        logger.warning(f"[IDLE] idle_check error: {e}")
                        self._client.idle_done()
                        break  # Reconnect
                    
                    # Exit IDLE mode to process
                    try:
                        self._client.idle_done()
                    except Exception as e:
                        logger.warning(f"[IDLE] idle_done error: {e}")
                        break  # Reconnect
                    
                    if self._stop_event.is_set():
                        break
                    
                    # Check if we got a meaningful response (EXISTS = new mail)
                    has_new_mail = any(
                        b"EXISTS" in (r[1] if isinstance(r, tuple) and len(r) > 1 else b"")
                        for r in responses
                    ) if responses else False
                    
                    if has_new_mail:
                        logger.info("[IDLE] New mail notification received!")
                        new_emails, new_max_uid = self._fetch_new_emails()
                        if new_emails and self.on_new_mail:
                            self.on_new_mail(new_emails, new_max_uid)
                            self.last_uid = new_max_uid
                    
                    # Renew IDLE before Gmail drops the connection (~29 min)
                    elapsed = time.monotonic() - idle_start
                    if elapsed >= IDLE_RENEW_SECONDS:
                        logger.debug("[IDLE] Renewing connection (25 min elapsed)")
                        break  # Will reconnect in outer loop
                
            except Exception as e:
                if self._stop_event.is_set():
                    break
                logger.error(f"[IDLE] Error in watcher loop: {e}")
                self._disconnect()
                
                # Exponential backoff: 5s, 10s, 20s, 40s, max 60s
                logger.info(f"[IDLE] Reconnecting in {self._backoff}s...")
                self._stop_event.wait(self._backoff)
                self._backoff = min(self._backoff * 2, 60)
        
        self._disconnect()
        logger.info("[IDLE] Background thread exiting")
