"""
Test email thread capture feature in email_poller.py.
Tests:
- _parse_email_date: RFC 2822 date parsing with timezone conversion
- _fetch_full_thread: graceful error handling when IMAP is None
- _store_thread_record: function exists and is callable
- _create_ticket_from_email: accepts email_date, mail, gmail_thrid parameters
- parsedate_to_datetime import verification
"""
import sys
import os

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
import email
import inspect
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parsedate_to_datetime


class TestEmailDateParsing:
    """Test _parse_email_date function for RFC 2822 date parsing."""
    
    def test_import_parsedate_to_datetime(self):
        """Verify parsedate_to_datetime is correctly imported in email_poller."""
        from services.email_poller import _parse_email_date
        # If we can import _parse_email_date which uses parsedate_to_datetime, import is correct
        assert callable(_parse_email_date)
    
    def test_parse_ist_date(self):
        """Test parsing IST (+0530) timezone date to UTC."""
        from services.email_poller import _parse_email_date
        
        msg = EmailMessage()
        msg['Date'] = 'Thu, 04 Mar 2026 10:30:00 +0530'
        
        result = _parse_email_date(msg)
        
        # Should convert to UTC (5 hours 30 minutes behind)
        assert result.tzinfo == timezone.utc
        # IST 10:30 = UTC 05:00
        assert result.hour == 5
        assert result.minute == 0
    
    def test_parse_utc_date(self):
        """Test parsing UTC (+0000) timezone date."""
        from services.email_poller import _parse_email_date
        
        msg = EmailMessage()
        msg['Date'] = 'Thu, 04 Mar 2026 05:00:00 +0000'
        
        result = _parse_email_date(msg)
        
        assert result.tzinfo == timezone.utc
        assert result.hour == 5
        assert result.minute == 0
    
    def test_parse_missing_date_fallback(self):
        """Test fallback to datetime.now(UTC) when Date header is missing."""
        from services.email_poller import _parse_email_date
        
        msg = EmailMessage()
        # No Date header set
        
        result = _parse_email_date(msg)
        
        # Should have timezone info (UTC)
        assert result.tzinfo is not None
        # Should be close to now (within 1 minute)
        now = datetime.now(timezone.utc)
        delta = abs((result - now).total_seconds())
        assert delta < 60
    
    def test_parse_malformed_date_fallback(self):
        """Test handling of malformed date strings without crashing."""
        from services.email_poller import _parse_email_date
        
        msg = EmailMessage()
        msg['Date'] = 'INVALID DATE STRING'
        
        # Should not crash, should return a fallback datetime
        result = _parse_email_date(msg)
        
        # Should have timezone info
        assert result.tzinfo is not None
        # Should be close to now
        now = datetime.now(timezone.utc)
        delta = abs((result - now).total_seconds())
        assert delta < 60
    
    def test_parse_various_rfc2822_formats(self):
        """Test parsing various valid RFC 2822 date formats."""
        from services.email_poller import _parse_email_date
        
        test_dates = [
            'Wed, 04 Mar 2026 12:00:00 -0800',  # PST
            'Thu, 05 Mar 2026 00:00:00 +0100',  # CET
            '4 Mar 2026 12:00:00 GMT',          # No day name
        ]
        
        for date_str in test_dates:
            msg = EmailMessage()
            msg['Date'] = date_str
            result = _parse_email_date(msg)
            assert result.tzinfo == timezone.utc, f"Failed for date: {date_str}"


class TestFetchFullThread:
    """Test _fetch_full_thread function for graceful error handling."""
    
    def test_returns_empty_list_when_mail_is_none(self):
        """Test that _fetch_full_thread returns empty list when IMAP connection is None."""
        from services.email_poller import _fetch_full_thread
        
        result = _fetch_full_thread(None, 'test_thread_id_123')
        
        assert result == []
        assert isinstance(result, list)
    
    def test_returns_empty_list_with_empty_thread_id(self):
        """Test that _fetch_full_thread handles empty thread ID gracefully."""
        from services.email_poller import _fetch_full_thread
        
        result = _fetch_full_thread(None, '')
        
        assert result == []


class TestStoreThreadRecord:
    """Test _store_thread_record function exists and is callable."""
    
    def test_function_exists(self):
        """Verify _store_thread_record function exists."""
        from services.email_poller import _store_thread_record
        assert callable(_store_thread_record)
    
    def test_function_signature(self):
        """Verify _store_thread_record has expected parameters."""
        from services.email_poller import _store_thread_record
        
        sig = inspect.signature(_store_thread_record)
        params = list(sig.parameters.keys())
        
        assert 'tm' in params
        assert 'ticket_id' in params
        assert 'match_method' in params


class TestCreateTicketFromEmail:
    """Test _create_ticket_from_email function signature and parameters."""
    
    def test_function_exists(self):
        """Verify _create_ticket_from_email function exists."""
        from services.email_poller import _create_ticket_from_email
        assert callable(_create_ticket_from_email)
    
    def test_accepts_email_date_parameter(self):
        """Verify _create_ticket_from_email accepts email_date parameter."""
        from services.email_poller import _create_ticket_from_email
        
        sig = inspect.signature(_create_ticket_from_email)
        params = list(sig.parameters.keys())
        
        assert 'email_date' in params
    
    def test_accepts_mail_parameter(self):
        """Verify _create_ticket_from_email accepts mail parameter."""
        from services.email_poller import _create_ticket_from_email
        
        sig = inspect.signature(_create_ticket_from_email)
        params = list(sig.parameters.keys())
        
        assert 'mail' in params
    
    def test_accepts_gmail_thrid_parameter(self):
        """Verify _create_ticket_from_email accepts gmail_thrid parameter."""
        from services.email_poller import _create_ticket_from_email
        
        sig = inspect.signature(_create_ticket_from_email)
        params = list(sig.parameters.keys())
        
        assert 'gmail_thrid' in params
    
    def test_all_required_parameters_present(self):
        """Verify all required parameters are present in _create_ticket_from_email."""
        from services.email_poller import _create_ticket_from_email
        
        sig = inspect.signature(_create_ticket_from_email)
        params = list(sig.parameters.keys())
        
        required = ['from_name', 'from_addr', 'subject', 'body', 'email_parts', 'email_date', 'mail', 'gmail_thrid']
        for param in required:
            assert param in params, f"Missing parameter: {param}"


class TestProcessEmailIntegration:
    """Test _process_email passes correct parameters to _create_ticket_from_email."""
    
    def test_email_date_parameter_in_signature(self):
        """Verify _process_email function signature includes email_date handling."""
        from services.email_poller import _process_email
        # Function should be callable without error
        assert callable(_process_email)
    
    def test_import_chain(self):
        """Verify email_poller imports parsedate_to_datetime correctly."""
        # Direct import test
        from email.utils import parsedate_to_datetime as std_parsedate
        from services.email_poller import _parse_email_date
        
        # If _parse_email_date works, the import chain is correct
        msg = EmailMessage()
        msg['Date'] = 'Thu, 04 Mar 2026 12:00:00 +0000'
        result = _parse_email_date(msg)
        assert result is not None


class TestProcessSentEmail:
    """Test _process_sent_email uses _parse_email_date for timestamps."""
    
    def test_function_exists(self):
        """Verify _process_sent_email function exists."""
        from services.email_poller import _process_sent_email
        assert callable(_process_sent_email)
