"""
Email utilities for production-grade email handling.

This module provides:
- Email parsing (HTML, plain text, headers)
- Email threading (Message-ID, In-Reply-To, References)
- Preview generation
- Safe HTML rendering preparation
- Inline/CID image extraction and embedding
"""

import re
import base64
import uuid
from html import unescape
from html.parser import HTMLParser
from email.utils import parseaddr, formataddr, make_msgid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
import logging

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """
    Extract plain text from HTML while preserving structure.
    Handles common email HTML patterns.
    """
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
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()


def html_to_plain_text(html: str) -> str:
    """
    Convert HTML to plain text, preserving basic structure.
    
    Args:
        html: Raw HTML string
        
    Returns:
        Plain text with normalized whitespace
    """
    if not html:
        return ""
    
    try:
        # First, decode HTML entities
        text = unescape(html)
        
        # Use the parser for better extraction
        parser = HTMLTextExtractor()
        parser.feed(text)
        return parser.get_text()
    except Exception as e:
        logger.warning(f"HTML parsing failed, falling back to regex: {e}")
        # Fallback: simple regex-based extraction
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


def generate_preview(text: str, max_length: int = 150) -> str:
    """
    Generate a clean preview from text.
    
    Args:
        text: Source text (plain text, not HTML)
        max_length: Maximum preview length
        
    Returns:
        Clean preview string
    """
    if not text:
        return ""
    
    # Normalize whitespace
    preview = re.sub(r'\s+', ' ', text).strip()
    
    # Truncate intelligently (at word boundary)
    if len(preview) <= max_length:
        return preview
    
    # Find last space before max_length
    truncated = preview[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.7:  # Only truncate at word if reasonable
        truncated = truncated[:last_space]
    
    return truncated.rstrip('.,;:!?') + '...'


def parse_email_content(payload: dict) -> Dict[str, str]:
    """
    Parse email payload and extract all content types.
    
    Args:
        payload: Gmail API message payload
        
    Returns:
        Dictionary with:
        - html: Raw HTML content (if available)
        - text: Plain text content
        - preview: Short preview for list views
    """
    html_body = ""
    text_body = ""
    
    def extract_parts(payload_part):
        nonlocal html_body, text_body
        
        mime_type = payload_part.get('mimeType', '')
        body_data = payload_part.get('body', {}).get('data', '')
        
        if body_data:
            try:
                decoded = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                
                if mime_type == 'text/plain' and not text_body:
                    text_body = decoded
                elif mime_type == 'text/html' and not html_body:
                    html_body = decoded
            except Exception as e:
                logger.warning(f"Failed to decode email part: {e}")
        
        # Recurse into nested parts
        for part in payload_part.get('parts', []):
            extract_parts(part)
    
    extract_parts(payload)
    
    # If no plain text, convert HTML to text
    if not text_body and html_body:
        text_body = html_to_plain_text(html_body)
    
    # Generate preview from plain text
    preview = generate_preview(text_body)
    
    return {
        'html': html_body,
        'text': text_body,
        'preview': preview
    }


def extract_email_headers(headers: list) -> Dict[str, str]:
    """
    Extract relevant headers from email.
    
    Args:
        headers: List of header dicts from Gmail API
        
    Returns:
        Dictionary with normalized header values
    """
    result = {
        'from': '',
        'to': '',
        'cc': '',
        'subject': '',
        'date': '',
        'message_id': '',      # RFC 2822 Message-ID (for threading)
        'in_reply_to': '',     # For thread chain
        'references': '',      # For thread chain
    }
    
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        
        if name == 'from':
            result['from'] = value
        elif name == 'to':
            result['to'] = value
        elif name == 'cc':
            result['cc'] = value
        elif name == 'subject':
            result['subject'] = value
        elif name == 'date':
            result['date'] = value
        elif name == 'message-id':
            result['message_id'] = value
        elif name == 'in-reply-to':
            result['in_reply_to'] = value
        elif name == 'references':
            result['references'] = value
    
    return result


def generate_message_id(domain: str = "tickflow.app") -> str:
    """
    Generate a valid RFC 2822 Message-ID.
    
    Format: <unique-id@domain>
    
    Args:
        domain: Domain for the Message-ID
        
    Returns:
        Valid Message-ID string
    """
    unique_part = f"{uuid.uuid4().hex}.{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    return f"<{unique_part}@{domain}>"


def build_threading_headers(
    original_message_id: str,
    original_references: str = "",
    original_in_reply_to: str = ""
) -> Dict[str, str]:
    """
    Build proper threading headers for a reply email.
    
    Following RFC 2822 and RFC 5322 specifications:
    - In-Reply-To: Should contain the Message-ID of the email being replied to
    - References: Should contain the In-Reply-To value of the parent, followed by
                  the parent's References (if any), followed by the parent's Message-ID
    
    Args:
        original_message_id: Message-ID of the email being replied to
        original_references: References header from original email (optional)
        original_in_reply_to: In-Reply-To header from original email (optional)
        
    Returns:
        Dictionary with In-Reply-To and References headers
    """
    if not original_message_id:
        return {}
    
    # In-Reply-To is always the Message-ID of the direct parent
    in_reply_to = original_message_id
    
    # References should be the chain of all Message-IDs in the thread
    # Format: oldest-message-id ... parent-message-id
    references_list = []
    
    if original_references:
        # Split existing references and add them
        refs = original_references.split()
        references_list.extend(refs)
    
    # Add the parent's Message-ID if not already in references
    if original_message_id and original_message_id not in references_list:
        references_list.append(original_message_id)
    
    # Limit references to prevent header from getting too long (RFC recommends)
    # Keep first and last few if too many
    if len(references_list) > 10:
        references_list = references_list[:3] + references_list[-7:]
    
    references = ' '.join(references_list)
    
    return {
        'In-Reply-To': in_reply_to,
        'References': references
    }


def sanitize_html_for_display(html: str) -> str:
    """
    Sanitize HTML for safe display while preserving email formatting.
    
    This is a basic sanitizer. For production, consider using a library
    like bleach or DOMPurify (on frontend).
    
    Args:
        html: Raw HTML string
        
    Returns:
        Sanitized HTML safe for rendering
    """
    if not html:
        return ""
    
    # Remove potentially dangerous tags
    dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button']
    for tag in dangerous_tags:
        html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(f'<{tag}[^>]*/>', '', html, flags=re.IGNORECASE)
    
    # Remove event handlers
    html = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+on\w+\s*=\s*\S+', '', html, flags=re.IGNORECASE)
    
    # Remove javascript: URLs
    html = re.sub(r'href\s*=\s*["\']javascript:[^"\']*["\']', 'href="#"', html, flags=re.IGNORECASE)
    
    return html


def extract_email_address(from_header: str) -> Optional[str]:
    """
    Extract just the email address from a From header.
    
    Handles formats like:
    - "John Doe <john@example.com>"
    - "john@example.com"
    - "<john@example.com>"
    
    Args:
        from_header: Raw From header value
        
    Returns:
        Email address or None
    """
    if not from_header:
        return None
    
    # Use email.utils.parseaddr for robust parsing
    name, email = parseaddr(from_header)
    
    if email and '@' in email:
        return email.lower()
    
    # Fallback: try regex
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
    if match:
        return match.group(0).lower()
    
    return None


def format_sender_name(from_header: str) -> str:
    """
    Extract display name from From header, falling back to email.
    
    Args:
        from_header: Raw From header value
        
    Returns:
        Display name or email address
    """
    if not from_header:
        return "Unknown"
    
    name, email = parseaddr(from_header)
    
    if name:
        return name
    elif email:
        # Use part before @ as name
        return email.split('@')[0].replace('.', ' ').title()
    
    return from_header
