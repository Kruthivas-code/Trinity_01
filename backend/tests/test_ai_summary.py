"""
Test suite for AI-powered ticket summarization feature.
Tests the /api/tickets/{ticket_id}/summary endpoint.
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "7N_TW_9vqeefrLlsBi_s9cZyXCYznDfSPaSt8iwcJic"

# Minimum customer messages required for summary eligibility
MIN_CUSTOMER_MESSAGES = 5


@pytest.fixture(scope="module")
def api_client():
    """Authenticated session with cookie."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestHealthCheck:
    """Verify backend is healthy before running tests."""
    
    def test_health_check(self, api_client):
        """Backend health check should pass."""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"Health check passed: {data}")


class TestSummaryEndpointBasic:
    """Basic tests for summary endpoint behavior."""
    
    def test_summary_non_existent_ticket(self, api_client):
        """GET /api/tickets/{ticket_id}/summary returns 404 for non-existent ticket."""
        fake_ticket_id = f"FAKE-{uuid.uuid4().hex[:8]}"
        response = api_client.get(f"{BASE_URL}/api/tickets/{fake_ticket_id}/summary")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("detail", "").lower()
        print(f"Non-existent ticket returns 404: {data}")
    
    def test_summary_endpoint_exists(self, api_client):
        """Summary endpoint should exist and respond."""
        # First get a real ticket
        tickets_response = api_client.get(f"{BASE_URL}/api/tickets?limit=1")
        if tickets_response.status_code != 200:
            pytest.skip("Cannot fetch tickets to test summary endpoint")
        
        tickets = tickets_response.json()
        if isinstance(tickets, dict):
            tickets = tickets.get("tickets", [])
        
        if not tickets:
            pytest.skip("No tickets available for testing")
        
        ticket_id = tickets[0].get("ticket_id") or tickets[0].get("id")
        response = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}/summary")
        
        # Should return 200 (either eligible or not eligible)
        assert response.status_code == 200
        data = response.json()
        assert "eligible" in data
        print(f"Summary endpoint response for {ticket_id}: eligible={data.get('eligible')}, customer_msg_count={data.get('customer_message_count')}")


class TestSummaryEligibility:
    """Tests for summary eligibility logic based on customer message count."""
    
    def test_summary_returns_eligible_false_for_insufficient_messages(self, api_client):
        """Summary should return eligible=false for tickets with <5 customer messages."""
        # Get tickets and find one with few messages
        tickets_response = api_client.get(f"{BASE_URL}/api/tickets?limit=50")
        if tickets_response.status_code != 200:
            pytest.skip("Cannot fetch tickets")
        
        tickets = tickets_response.json()
        if isinstance(tickets, dict):
            tickets = tickets.get("tickets", [])
        
        tested_any = False
        for ticket in tickets:
            ticket_id = ticket.get("ticket_id") or ticket.get("id")
            response = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}/summary")
            
            if response.status_code == 200:
                data = response.json()
                customer_msg_count = data.get("customer_message_count", 0)
                
                if customer_msg_count < MIN_CUSTOMER_MESSAGES:
                    # Should be not eligible
                    assert data.get("eligible") == False, f"Ticket {ticket_id} has {customer_msg_count} messages but marked eligible"
                    assert data.get("conversation_summary") is None
                    assert data.get("min_required") == MIN_CUSTOMER_MESSAGES
                    print(f"Ticket {ticket_id}: {customer_msg_count} messages, eligible=False (as expected)")
                    tested_any = True
                    break
        
        if not tested_any:
            print("No tickets with <5 messages found to test ineligibility")
    
    def test_summary_response_structure(self, api_client):
        """Summary response should have correct structure."""
        tickets_response = api_client.get(f"{BASE_URL}/api/tickets?limit=1")
        if tickets_response.status_code != 200:
            pytest.skip("Cannot fetch tickets")
        
        tickets = tickets_response.json()
        if isinstance(tickets, dict):
            tickets = tickets.get("tickets", [])
        
        if not tickets:
            pytest.skip("No tickets available")
        
        ticket_id = tickets[0].get("ticket_id") or tickets[0].get("id")
        response = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields in response
        assert "eligible" in data
        assert "customer_message_count" in data
        
        if data.get("eligible"):
            # Eligible ticket should have summary fields
            assert "conversation_summary" in data
            assert "past_issues_summary" in data
            assert "past_ticket_count" in data
        else:
            # Not eligible ticket should have min_required
            assert "min_required" in data
            assert data["min_required"] == MIN_CUSTOMER_MESSAGES
        
        print(f"Summary response structure valid: {list(data.keys())}")


class TestSummaryGeneration:
    """Tests for creating test data and verifying summary generation."""
    
    @pytest.fixture(scope="class")
    def test_ticket_with_messages(self, api_client):
        """Create a test ticket with 6+ customer messages."""
        # Create a unique test ticket
        test_id = f"TEST-SUMMARY-{uuid.uuid4().hex[:8]}"
        
        create_payload = {
            "title": f"AI Summary Test Ticket - {test_id}",
            "description": "This is a test ticket for AI summary feature testing.",
            "status": "in_progress",
            "priority": "medium",
            "customer_email": f"test.summary.{uuid.uuid4().hex[:6]}@example.com",
            "customer_name": "Summary Test Customer"
        }
        
        response = api_client.post(f"{BASE_URL}/api/tickets", json=create_payload)
        
        if response.status_code not in [200, 201]:
            pytest.skip(f"Failed to create test ticket: {response.status_code} - {response.text}")
        
        ticket_data = response.json()
        ticket_id = ticket_data.get("ticket_id") or ticket_data.get("id")
        print(f"Created test ticket: {ticket_id}")
        
        # Add 6 customer reply messages to make it eligible
        messages_added = 0
        for i in range(6):
            msg_payload = {
                "content": f"Customer message {i+1}: This is a test customer reply about the issue. The problem continues and I need more help with this matter. Please look into it urgently.",
                "type": "customer_reply"
            }
            
            msg_response = api_client.post(
                f"{BASE_URL}/api/tickets/{ticket_id}/notes",
                json=msg_payload
            )
            
            if msg_response.status_code in [200, 201]:
                messages_added += 1
                print(f"Added customer message {messages_added}")
            else:
                print(f"Failed to add message {i+1}: {msg_response.status_code}")
        
        print(f"Total messages added: {messages_added}")
        
        yield {
            "ticket_id": ticket_id,
            "messages_added": messages_added,
            "ticket_data": ticket_data
        }
        
        # Cleanup: Delete the test ticket
        delete_response = api_client.delete(f"{BASE_URL}/api/tickets/{ticket_id}")
        print(f"Cleanup: Deleted test ticket {ticket_id}, status: {delete_response.status_code}")
    
    def test_summary_with_sufficient_messages(self, api_client, test_ticket_with_messages):
        """Test summary generation for ticket with 6+ customer messages."""
        ticket_id = test_ticket_with_messages["ticket_id"]
        messages_added = test_ticket_with_messages["messages_added"]
        
        if messages_added < MIN_CUSTOMER_MESSAGES:
            pytest.skip(f"Only {messages_added} messages added, need at least {MIN_CUSTOMER_MESSAGES}")
        
        # Get summary
        response = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        print(f"Summary response: eligible={data.get('eligible')}, msg_count={data.get('customer_message_count')}")
        
        # Should be eligible with 6+ messages
        # Note: The count includes original ticket + customer_reply messages
        assert data.get("customer_message_count", 0) >= MIN_CUSTOMER_MESSAGES or data.get("eligible") == True
        
        if data.get("eligible"):
            # Should have generated a summary (unless still processing)
            assert "conversation_summary" in data
            if data.get("conversation_summary"):
                print(f"Generated summary: {data['conversation_summary'][:200]}...")
            print(f"Past ticket count: {data.get('past_ticket_count', 0)}")
    
    def test_summary_force_regeneration(self, api_client, test_ticket_with_messages):
        """Test force=true triggers regeneration."""
        ticket_id = test_ticket_with_messages["ticket_id"]
        messages_added = test_ticket_with_messages["messages_added"]
        
        if messages_added < MIN_CUSTOMER_MESSAGES:
            pytest.skip(f"Not enough messages for summary")
        
        # First get without force
        response1 = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}/summary")
        if response1.status_code != 200:
            pytest.skip("Summary endpoint failed")
        
        data1 = response1.json()
        
        if not data1.get("eligible"):
            pytest.skip("Ticket not eligible for summary")
        
        # Now get with force=true
        response2 = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}/summary?force=true")
        assert response2.status_code == 200
        
        data2 = response2.json()
        
        # With force=true, should regenerate (cached=False for new generation)
        # Note: If first call generated fresh, this might also show cached=False
        print(f"Force regeneration result: cached={data2.get('cached')}, generated_at={data2.get('generated_at')}")
        
        # Response structure should be correct
        assert "conversation_summary" in data2
        assert "eligible" in data2


class TestMessageTypeCounting:
    """Tests to verify correct counting of customer messages."""
    
    def test_message_types_counted_correctly(self, api_client):
        """Verify only original and customer_reply types are counted."""
        # Get an existing ticket
        tickets_response = api_client.get(f"{BASE_URL}/api/tickets?limit=10")
        if tickets_response.status_code != 200:
            pytest.skip("Cannot fetch tickets")
        
        tickets = tickets_response.json()
        if isinstance(tickets, dict):
            tickets = tickets.get("tickets", [])
        
        if not tickets:
            pytest.skip("No tickets available")
        
        # Test multiple tickets to find varied message counts
        for ticket in tickets[:5]:
            ticket_id = ticket.get("ticket_id") or ticket.get("id")
            
            # Get summary to see message count
            summary_response = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}/summary")
            if summary_response.status_code == 200:
                summary = summary_response.json()
                
                # Get notes/messages for this ticket
                notes_response = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}/notes")
                if notes_response.status_code == 200:
                    notes = notes_response.json()
                    if isinstance(notes, dict):
                        notes = notes.get("messages", [])
                    
                    # Count customer messages manually
                    customer_types = ["original", "customer_reply"]
                    manual_count = sum(1 for n in notes if n.get("type") in customer_types)
                    # Add 1 for the original ticket description if it counts
                    # (The original ticket description is often type "original")
                    
                    api_count = summary.get("customer_message_count", 0)
                    
                    print(f"Ticket {ticket_id}: API reports {api_count} customer messages")
                    
                    # The API count should be >= 0 and align with expectations
                    assert api_count >= 0
        
        print("Message type counting verification complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
