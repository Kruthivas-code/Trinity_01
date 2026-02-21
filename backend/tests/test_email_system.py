"""
Tests for the email service — send, receive, threading, retry.
"""
import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_env():
    env = {
        "SES_SMTP_USER": "test_user",
        "SES_SMTP_PASSWORD": "test_pass",
        "SES_SENDER_EMAIL": "support@emergent.sh",
        "SES_SENDER_NAME": "Emergent Support",
        "IMAP_HOST": "imap.gmail.com",
        "IMAP_USER": "hey@emergent.sh",
        "IMAP_PASSWORD": "testpass",
        "EMAIL_POLL_INTERVAL": "30",
    }
    with patch.dict(os.environ, env):
        yield env


class TestSESRegionDetection:
    def test_detect_region_caches_result(self, mock_env):
        from services.email_service import detect_ses_region, _working_smtp_host
        import services.email_service as svc
        svc._working_smtp_host = "email-smtp.us-east-1.amazonaws.com"
        result = detect_ses_region()
        assert result == "email-smtp.us-east-1.amazonaws.com"
        svc._working_smtp_host = None  # reset

    def test_detect_region_tries_all(self, mock_env):
        from services.email_service import detect_ses_region
        import services.email_service as svc
        svc._working_smtp_host = None
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = ConnectionError("fail")
            result = detect_ses_region()
            assert result is None


class TestSendEmail:
    def test_send_email_success(self, mock_env):
        from services.email_service import send_email
        import services.email_service as svc
        svc._working_smtp_host = "email-smtp.us-east-1.amazonaws.com"

        mock_server = MagicMock()
        with patch("smtplib.SMTP", return_value=mock_server):
            with patch.object(svc.email_threads_collection, "insert_one"):
                result = send_email(
                    to_email="customer@test.com",
                    subject="Test Subject",
                    html_body="<p>Hello</p>",
                    text_body="Hello",
                    ticket_id="TKT-001",
                )
                assert result is not None
                assert result["status"] == "sent"
                assert result["to_email"] == "customer@test.com"
                assert "threading_message_id" in result
                mock_server.starttls.assert_called_once()
                mock_server.login.assert_called_once()
                mock_server.sendmail.assert_called_once()

    def test_send_email_no_credentials(self):
        from services.email_service import send_email
        with patch.dict(os.environ, {"SES_SMTP_USER": "", "SES_SMTP_PASSWORD": ""}):
            result = send_email("to@test.com", "Subject", "<p>Hi</p>")
            assert result is None

    def test_send_email_stores_failed(self, mock_env):
        from services.email_service import send_email
        import services.email_service as svc
        svc._working_smtp_host = "email-smtp.us-east-1.amazonaws.com"

        with patch("smtplib.SMTP", side_effect=ConnectionError("fail")):
            with patch.object(svc.email_threads_collection, "insert_one") as mock_insert:
                result = send_email("to@test.com", "Subject", "<p>Hi</p>", ticket_id="TKT-002")
                assert result is None
                mock_insert.assert_called_once()
                doc = mock_insert.call_args[0][0]
                assert doc["direction"] == "outbound_failed"
                assert doc["status"] == "failed"


class TestThreadContext:
    def test_get_thread_context_empty(self, mock_env):
        from services.email_service import get_thread_context
        import services.email_service as svc
        with patch.object(svc.email_threads_collection, "find_one", return_value=None):
            ctx = get_thread_context("TKT-NONE")
            assert ctx["in_reply_to"] is None
            assert ctx["references"] == []


class TestRateLimit:
    def test_rate_limit_allows_initial(self, mock_env):
        from services.email_service import _check_rate_limit
        import services.email_service as svc
        svc._rate_count = 0
        svc._rate_window_start = 0
        assert _check_rate_limit() is True

    def test_rate_limit_blocks_excess(self, mock_env):
        from services.email_service import _check_rate_limit
        import services.email_service as svc
        import time
        svc._rate_window_start = time.time()
        svc._rate_count = 10  # at limit
        assert _check_rate_limit() is False


class TestEmailPoller:
    def test_decode_header_value(self, mock_env):
        from services.email_poller import _decode_header_value
        assert _decode_header_value("Simple Text") == "Simple Text"
        assert _decode_header_value(None) == ""
        assert _decode_header_value("") == ""

    def test_sanitize_body(self, mock_env):
        from services.email_poller import _sanitize_body
        assert _sanitize_body("Hello World") == "Hello World"
        assert "<script>" not in _sanitize_body("<script>alert('xss')</script>Hello")
        assert _sanitize_body("") == ""
        assert _sanitize_body(None) == ""
        # Test null byte removal
        assert "\x00" not in _sanitize_body("Hello\x00World")

    def test_is_own_email(self, mock_env):
        from services.email_poller import _is_own_email
        msg = MagicMock()
        msg.get.return_value = "support@emergent.sh"
        assert _is_own_email(msg) is True

        msg.get.return_value = "customer@external.com"
        assert _is_own_email(msg) is False

    def test_extract_reply_body_strips_quotes(self, mock_env):
        from services.email_poller import _extract_reply_body
        msg = MagicMock()
        msg.is_multipart.return_value = False
        msg.get_payload.return_value = b"New reply text\n\nOn Mon, Jan 1, 2026 John wrote:\n> Old message"
        msg.get_content_type.return_value = "text/plain"
        body = _extract_reply_body(msg)
        assert "New reply text" in body
        assert "Old message" not in body


class TestRetryMechanism:
    def test_retry_failed_emails_empty_queue(self, mock_env):
        from services.email_service import retry_failed_emails
        import services.email_service as svc
        with patch.object(svc.email_threads_collection, "find", return_value=[]):
            result = retry_failed_emails()
            assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
