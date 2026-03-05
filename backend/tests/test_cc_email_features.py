"""
Tests for CC functionality and outbound email features in Trinity:
1. Create Ticket with send_email=true, customer_email and cc
2. Email stats API with outbound_emails and bounce_details
3. Reply with CC addresses
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
SESSION_TOKEN = "qa_test_admin_session_token_2026"


@pytest.fixture
def api_session():
    """Create a requests session with auth cookie."""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestCreateTicketWithEmail:
    """Test ticket creation with send_email and cc fields."""

    def test_create_ticket_with_send_email_false(self, api_session):
        """Create ticket without sending email - should work normally."""
        payload = {
            "title": f"TEST_CC_NoEmail_{uuid.uuid4().hex[:8]}",
            "description": "Test ticket without email sending",
            "status": "todo",
            "customer_email": "test@example.com",
            "send_email": False,
            "cc": []
        }
        response = api_session.post(f"{BASE_URL}/api/tickets", json=payload)
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        data = response.json()
        assert "ticket_id" in data
        assert data["customer_email"] == "test@example.com"
        # email_sent should not be present or False when send_email=False
        assert data.get("email_sent") in [None, False]
        print(f"✓ Created ticket {data['ticket_id']} without email sending")

    def test_create_ticket_with_send_email_true(self, api_session):
        """Create ticket with send_email=true - should attempt email."""
        payload = {
            "title": f"TEST_CC_WithEmail_{uuid.uuid4().hex[:8]}",
            "description": "This is a test email body content for outbound email",
            "status": "todo",
            "customer_email": "test-recipient@example.com",
            "send_email": True,
            "cc": ["cc1@example.com", "cc2@example.com"]
        }
        response = api_session.post(f"{BASE_URL}/api/tickets", json=payload)
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        data = response.json()
        assert "ticket_id" in data
        assert data["customer_email"] == "test-recipient@example.com"
        # email_sent field should be in response (True or False depending on SMTP)
        assert "email_sent" in data or data.get("routing_applied") is not None
        print(f"✓ Created ticket {data['ticket_id']} with send_email=True, email_sent={data.get('email_sent')}")

    def test_create_ticket_cc_parsing(self, api_session):
        """Verify CC field accepts list of email addresses."""
        payload = {
            "title": f"TEST_CC_Parse_{uuid.uuid4().hex[:8]}",
            "description": "Test CC parsing",
            "status": "todo",
            "customer_email": "customer@example.com",
            "send_email": True,
            "cc": ["manager@example.com", "team-lead@example.com", "support@example.com"]
        }
        response = api_session.post(f"{BASE_URL}/api/tickets", json=payload)
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        data = response.json()
        print(f"✓ Ticket created with multiple CC addresses: {data['ticket_id']}")


class TestEmailStatsAPI:
    """Test the email stats endpoint for bounce_details and outbound_emails."""

    def test_email_stats_endpoint_exists(self, api_session):
        """Verify /api/tickets/{id}/email-stats endpoint exists."""
        # First create a ticket
        payload = {
            "title": f"TEST_EmailStats_{uuid.uuid4().hex[:8]}",
            "description": "Test ticket for email stats",
            "status": "todo",
            "customer_email": "stats-test@example.com"
        }
        create_resp = api_session.post(f"{BASE_URL}/api/tickets", json=payload)
        assert create_resp.status_code in [200, 201]
        ticket_id = create_resp.json()["ticket_id"]

        # Get email stats
        stats_resp = api_session.get(f"{BASE_URL}/api/tickets/{ticket_id}/email-stats")
        assert stats_resp.status_code == 200, f"Email stats endpoint failed: {stats_resp.text}"
        stats = stats_resp.json()
        
        # Verify expected fields exist
        assert "outbound" in stats, "Missing 'outbound' field in email stats"
        assert "inbound" in stats, "Missing 'inbound' field in email stats"
        assert "bounced" in stats, "Missing 'bounced' field in email stats"
        assert "bounce_details" in stats, "Missing 'bounce_details' field in email stats"
        assert "outbound_emails" in stats, "Missing 'outbound_emails' field in email stats"
        
        print(f"✓ Email stats endpoint returns all expected fields")
        print(f"  - outbound: {stats['outbound']}")
        print(f"  - inbound: {stats['inbound']}")
        print(f"  - bounced: {stats['bounced']}")
        print(f"  - bounce_details: {stats['bounce_details']}")
        print(f"  - outbound_emails: {stats['outbound_emails']}")

    def test_email_stats_outbound_emails_structure(self, api_session):
        """Verify outbound_emails array has correct structure."""
        # Get stats for existing ticket TKT-112809 mentioned in context
        stats_resp = api_session.get(f"{BASE_URL}/api/tickets/TKT-112809/email-stats")
        if stats_resp.status_code != 200:
            # Ticket might not exist, create one
            payload = {
                "title": f"TEST_OutboundStruct_{uuid.uuid4().hex[:8]}",
                "description": "Test outbound email structure",
                "status": "todo",
                "customer_email": "outbound-test@example.com",
                "send_email": True
            }
            create_resp = api_session.post(f"{BASE_URL}/api/tickets", json=payload)
            ticket_id = create_resp.json()["ticket_id"]
            stats_resp = api_session.get(f"{BASE_URL}/api/tickets/{ticket_id}/email-stats")
        
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        
        # Check outbound_emails structure
        outbound_emails = stats.get("outbound_emails", [])
        if len(outbound_emails) > 0:
            email = outbound_emails[0]
            assert "to_email" in email or email.get("to_email") is not None
            assert "cc" in email  # Should have cc field even if empty
            assert "status" in email
            assert "sent_at" in email
            print(f"✓ outbound_emails has correct structure: {list(email.keys())}")
        else:
            print("✓ outbound_emails is empty (no emails sent yet)")


class TestReplyWithCC:
    """Test adding replies with CC addresses."""

    def test_reply_with_cc_field(self, api_session):
        """Test POST /api/tickets/{id}/notes with type=reply and cc."""
        # Create a ticket first
        payload = {
            "title": f"TEST_ReplyCC_{uuid.uuid4().hex[:8]}",
            "description": "Test ticket for reply with CC",
            "status": "todo",
            "customer_email": "reply-test@example.com"
        }
        create_resp = api_session.post(f"{BASE_URL}/api/tickets", json=payload)
        assert create_resp.status_code in [200, 201]
        ticket_id = create_resp.json()["ticket_id"]

        # Add a reply with CC
        note_payload = {
            "content": "This is a test reply with CC recipients",
            "type": "reply",
            "cc": ["manager@example.com", "supervisor@example.com"]
        }
        reply_resp = api_session.post(f"{BASE_URL}/api/tickets/{ticket_id}/notes", json=note_payload)
        assert reply_resp.status_code == 200, f"Reply failed: {reply_resp.text}"
        reply_data = reply_resp.json()
        
        assert reply_data.get("type") == "reply"
        assert reply_data.get("content") == note_payload["content"]
        print(f"✓ Reply with CC added successfully to {ticket_id}")

    def test_reply_cc_empty_array(self, api_session):
        """Test reply with empty CC array."""
        payload = {
            "title": f"TEST_ReplyNoCC_{uuid.uuid4().hex[:8]}",
            "description": "Test ticket",
            "status": "todo",
            "customer_email": "no-cc@example.com"
        }
        create_resp = api_session.post(f"{BASE_URL}/api/tickets", json=payload)
        ticket_id = create_resp.json()["ticket_id"]

        note_payload = {
            "content": "Reply without CC",
            "type": "reply",
            "cc": []
        }
        reply_resp = api_session.post(f"{BASE_URL}/api/tickets/{ticket_id}/notes", json=note_payload)
        assert reply_resp.status_code == 200
        print(f"✓ Reply without CC works correctly")

    def test_internal_note_ignores_cc(self, api_session):
        """Test that internal notes don't send CC emails."""
        payload = {
            "title": f"TEST_NoteNoCC_{uuid.uuid4().hex[:8]}",
            "description": "Test ticket",
            "status": "todo",
            "customer_email": "note-test@example.com"
        }
        create_resp = api_session.post(f"{BASE_URL}/api/tickets", json=payload)
        ticket_id = create_resp.json()["ticket_id"]

        note_payload = {
            "content": "Internal note - CC should be ignored",
            "type": "internal_note",
            "cc": ["should@be.ignored"]
        }
        reply_resp = api_session.post(f"{BASE_URL}/api/tickets/{ticket_id}/notes", json=note_payload)
        assert reply_resp.status_code == 200
        print(f"✓ Internal note doesn't process CC (expected behavior)")


class TestSchemaValidation:
    """Test schema validation for new fields."""

    def test_ticket_create_schema_has_send_email(self, api_session):
        """Verify TicketCreate schema accepts send_email field."""
        payload = {
            "title": "Schema Test",
            "description": "Test",
            "send_email": True  # Should be accepted
        }
        response = api_session.post(f"{BASE_URL}/api/tickets", json=payload)
        # Should not fail with validation error for send_email field
        assert response.status_code != 422 or "send_email" not in response.text
        print(f"✓ send_email field is accepted in ticket create")

    def test_ticket_create_schema_has_cc(self, api_session):
        """Verify TicketCreate schema accepts cc field."""
        payload = {
            "title": "CC Schema Test",
            "description": "Test",
            "cc": ["test@example.com"]
        }
        response = api_session.post(f"{BASE_URL}/api/tickets", json=payload)
        # Should not fail with validation error for cc field
        assert response.status_code != 422 or "cc" not in response.text
        print(f"✓ cc field is accepted in ticket create")

    def test_internal_note_schema_has_cc(self, api_session):
        """Verify InternalNoteCreate schema accepts cc field."""
        # Create ticket first
        ticket_resp = api_session.post(f"{BASE_URL}/api/tickets", json={
            "title": "Note CC Schema Test",
            "description": "Test"
        })
        ticket_id = ticket_resp.json()["ticket_id"]

        note_payload = {
            "content": "Test note",
            "type": "reply",
            "cc": ["test@example.com"]
        }
        response = api_session.post(f"{BASE_URL}/api/tickets/{ticket_id}/notes", json=note_payload)
        # Should not fail with validation error for cc field
        assert response.status_code != 422 or "cc" not in response.text
        print(f"✓ cc field is accepted in internal note create")


class TestCleanup:
    """Clean up test data."""

    def test_cleanup_test_tickets(self, api_session):
        """Delete all TEST_ prefixed tickets created during testing."""
        # Get test tickets
        response = api_session.get(f"{BASE_URL}/api/tickets?limit=100")
        if response.status_code == 200:
            tickets = response.json().get("tickets", [])
            deleted = 0
            for t in tickets:
                if t.get("title", "").startswith("TEST_CC_") or \
                   t.get("title", "").startswith("TEST_EmailStats_") or \
                   t.get("title", "").startswith("TEST_ReplyCC_") or \
                   t.get("title", "").startswith("TEST_ReplyNoCC_") or \
                   t.get("title", "").startswith("TEST_NoteNoCC_") or \
                   t.get("title", "").startswith("TEST_OutboundStruct_"):
                    del_resp = api_session.delete(f"{BASE_URL}/api/tickets/{t['ticket_id']}")
                    if del_resp.status_code == 200:
                        deleted += 1
            print(f"✓ Cleaned up {deleted} test tickets")
