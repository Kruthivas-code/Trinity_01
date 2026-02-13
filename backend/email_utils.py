"""
Email utilities for production-grade email handling.

This module provides generic utilities:
- HTML to plain text conversion
- Preview generation
- Email address parsing
- Message-ID generation
- Threading header construction
- HTML sanitization
"""

import re
import uuid
from html import unescape
from html.parser import HTMLParser
from email.utils import parseaddr, formataddr, make_msgid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML while preserving structure."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_style = False
        self.in_script = False
        self.in_head = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'style':
            self.in_style = True
        elif tag == 'script':
            self.in_script = True
        elif tag == 'head':
            self.in_head = True
        elif tag in ('br', 'p', 'div', 'tr', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text_parts.append('\n')
        elif tag == 'td':
            self.text_parts.append(' ')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'style':
            self.in_style = False
        elif tag == 'script':
            self.in_script = False
        elif tag == 'head':
            self.in_head = False
        elif tag in ('p', 'div', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text_parts.append('\n')

    def handle_data(self, data):
        if not self.in_style and not self.in_script and not self.in_head:
            self.text_parts.append(data)

    def get_text(self):
        text = ''.join(self.text_parts)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()


def html_to_plain_text(html: str) -> str:
    """Convert HTML to plain text, preserving basic structure."""
    if not html:
        return ""
    try:
        text = unescape(html)
        parser = HTMLTextExtractor()
        parser.feed(text)
        return parser.get_text()
    except Exception as e:
        logger.warning(f"HTML parsing failed, falling back to regex: {e}")
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


def generate_preview(text: str, max_length: int = 150) -> str:
    """Generate a clean preview from text."""
    if not text:
        return ""
    preview = re.sub(r'\s+', ' ', text).strip()
    if len(preview) <= max_length:
        return preview
    truncated = preview[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.7:
        truncated = truncated[:last_space]
    return truncated.rstrip('.,;:!?') + '...'


def generate_message_id(domain: str = "tickflow.app") -> str:
    """Generate a valid RFC 2822 Message-ID."""
    unique_part = f"{uuid.uuid4().hex}.{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    return f"<{unique_part}@{domain}>"


def build_threading_headers(
    original_message_id: str,
    original_references: str = "",
) -> Dict[str, str]:
    """Build proper threading headers for a reply email (RFC 2822/5322)."""
    if not original_message_id:
        return {}
    in_reply_to = original_message_id
    references_list = []
    if original_references:
        references_list.extend(original_references.split())
    if original_message_id not in references_list:
        references_list.append(original_message_id)
    if len(references_list) > 10:
        references_list = references_list[:3] + references_list[-7:]
    return {
        'In-Reply-To': in_reply_to,
        'References': ' '.join(references_list)
    }


def sanitize_html_for_display(html: str) -> str:
    """Sanitize HTML for safe display while preserving email formatting."""
    if not html:
        return ""
    dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button']
    for tag in dangerous_tags:
        html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(f'<{tag}[^>]*/>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+on\w+\s*=\s*\S+', '', html, flags=re.IGNORECASE)
    html = re.sub(r'href\s*=\s*["\']javascript:[^"\']*["\']', 'href="#"', html, flags=re.IGNORECASE)
    return html


def extract_email_address(from_header: str) -> Optional[str]:
    """Extract just the email address from a From header."""
    if not from_header:
        return None
    name, email_addr = parseaddr(from_header)
    if email_addr and '@' in email_addr:
        return email_addr.lower()
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
    if match:
        return match.group(0).lower()
    return None


def format_sender_name(from_header: str) -> str:
    """Extract display name from From header, falling back to email."""
    if not from_header:
        return "Unknown"
    name, email_addr = parseaddr(from_header)
    if name:
        return name
    elif email_addr:
        return email_addr.split('@')[0].replace('.', ' ').title()
    return from_header
