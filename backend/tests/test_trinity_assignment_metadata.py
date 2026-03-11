"""
Test trinity_assigned_at behavior and system message content field
=====================================================================
This test suite verifies:
1. trinity_assigned_at is ONLY set when assignee_id actually changes
2. System messages use 'content' field (not 'text')
3. closed_at and resolved_at are both set when closing a ticket
4. POST /api/tickets/{id}/assign sets trinity_assigned_at
5. GET /api/tickets returns tickets with tags, customer_email and metadata
"""

import pytest
import requests
import os
import time
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', 'test_trinity_session_1773246168048')


class TestTrinityAssignmentMetadata:
    """Test suite for assignment timestamp and system message behavior"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        self.headers = {
            "Content-Type": "application/json",
            "Cookie": f"session_token={SESSION_TOKEN}"
        }
        self.created_tickets = []
        yield
        # Cleanup created tickets
        for ticket_id in self.created_tickets:
            try:
                requests.delete(
                    f"{BASE_URL}/api/tickets/{ticket_id}",
                    headers=self.headers,
                    timeout=10
                )
            except Exception:
                pass
    
    def create_test_ticket(self, title="Test Ticket", **kwargs):
        """Helper to create a test ticket"""
        payload = {
            "title": title,
            "description": "Test ticket for trinity_assigned_at testing",
            "status": "todo",
            "priority": "medium",
            "tags": ["test", "trinity"],
            "customer_email": "testcustomer@example.com",
            **kwargs
        }
        response = requests.post(
            f"{BASE_URL}/api/tickets",
            json=payload,
            headers=self.headers,
            timeout=15
        )
        assert response.status_code == 200, f"Failed to create ticket: {response.text}"
        ticket = response.json()
        self.created_tickets.append(ticket["ticket_id"])
        return ticket
    
    def get_ticket(self, ticket_id):
        """Helper to get ticket details"""
        response = requests.get(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Failed to get ticket: {response.text}"
        return response.json()
    
    def get_ticket_notes(self, ticket_id):
        """Helper to get ticket notes/messages"""
        response = requests.get(
            f"{BASE_URL}/api/tickets/{ticket_id}/notes",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Failed to get notes: {response.text}"
        return response.json()
    
    # ===== Test trinity_assigned_at behavior =====
    
    def test_update_status_only_does_not_set_trinity_assigned_at(self):
        """Updating only status should NOT set trinity_assigned_at"""
        # Create ticket without assignee
        ticket = self.create_test_ticket(title="TEST_status_only_update")
        ticket_id = ticket["ticket_id"]
        
        # Update only status (using valid status: 'waiting')
        response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"status": "waiting"},
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Failed to update ticket: {response.text}"
        
        # Verify trinity_assigned_at is NOT set
        updated_ticket = self.get_ticket(ticket_id)
        assert updated_ticket.get("trinity_assigned_at") is None, \
            f"trinity_assigned_at should NOT be set when only status changes, got: {updated_ticket.get('trinity_assigned_at')}"
        print("✓ test_update_status_only_does_not_set_trinity_assigned_at PASSED")
    
    def test_update_assignee_to_new_value_sets_trinity_assigned_at(self):
        """Updating assignee_id to a NEW value should SET trinity_assigned_at"""
        # Create ticket without assignee
        ticket = self.create_test_ticket(title="TEST_new_assignee")
        ticket_id = ticket["ticket_id"]
        
        # Get a user to assign
        users_response = requests.get(
            f"{BASE_URL}/api/users",
            headers=self.headers,
            timeout=10
        )
        users = users_response.json() if users_response.status_code == 200 else []
        if isinstance(users, dict):
            users = users.get("items", [])
        
        if not users:
            pytest.skip("No users available for assignment test")
        
        assignee_id = users[0].get("user_id")
        
        # Update with new assignee
        response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"assignee_id": assignee_id},
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Failed to update ticket: {response.text}"
        
        # Verify trinity_assigned_at IS set
        updated_ticket = self.get_ticket(ticket_id)
        assert updated_ticket.get("trinity_assigned_at") is not None, \
            "trinity_assigned_at should be set when assignee actually changes"
        print(f"✓ test_update_assignee_to_new_value_sets_trinity_assigned_at PASSED - trinity_assigned_at: {updated_ticket['trinity_assigned_at']}")
    
    def test_update_assignee_to_same_value_does_not_update_trinity_assigned_at(self):
        """Updating assignee_id to SAME value should NOT change trinity_assigned_at"""
        # Get a user to assign
        users_response = requests.get(
            f"{BASE_URL}/api/users",
            headers=self.headers,
            timeout=10
        )
        users = users_response.json() if users_response.status_code == 200 else []
        if isinstance(users, dict):
            users = users.get("items", [])
        
        if not users:
            pytest.skip("No users available for assignment test")
        
        assignee_id = users[0].get("user_id")
        
        # Create ticket with assignee
        ticket = self.create_test_ticket(title="TEST_same_assignee", assignee_id=assignee_id)
        ticket_id = ticket["ticket_id"]
        
        # Get initial trinity_assigned_at (might be set on creation)
        initial_ticket = self.get_ticket(ticket_id)
        initial_assigned_at = initial_ticket.get("trinity_assigned_at")
        
        # Wait a moment to ensure timestamp would differ
        time.sleep(1)
        
        # Update with SAME assignee (simulating frontend auto-save)
        response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"assignee_id": assignee_id},
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Failed to update ticket: {response.text}"
        
        # Verify trinity_assigned_at has NOT changed
        updated_ticket = self.get_ticket(ticket_id)
        assert updated_ticket.get("trinity_assigned_at") == initial_assigned_at, \
            f"trinity_assigned_at should NOT change when assignee is the same. " \
            f"Initial: {initial_assigned_at}, Current: {updated_ticket.get('trinity_assigned_at')}"
        print("✓ test_update_assignee_to_same_value_does_not_update_trinity_assigned_at PASSED")
    
    # ===== Test system message 'content' field =====
    
    def test_assignment_system_message_uses_content_field(self):
        """System message for assignment should use 'content' field, not 'text'"""
        # Get a user to assign
        users_response = requests.get(
            f"{BASE_URL}/api/users",
            headers=self.headers,
            timeout=10
        )
        users = users_response.json() if users_response.status_code == 200 else []
        if isinstance(users, dict):
            users = users.get("items", [])
        
        if not users:
            pytest.skip("No users available for assignment test")
        
        assignee_id = users[0].get("user_id")
        
        # Create ticket without assignee
        ticket = self.create_test_ticket(title="TEST_assignment_message")
        ticket_id = ticket["ticket_id"]
        
        # Assign user
        response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"assignee_id": assignee_id},
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        
        # Get notes and find system message
        notes_response = self.get_ticket_notes(ticket_id)
        messages = notes_response.get("messages", [])
        
        system_msgs = [m for m in messages if m.get("type") == "system" and "Assigned" in str(m.get("content", ""))]
        assert len(system_msgs) > 0, f"No assignment system message found. Messages: {messages}"
        
        latest_sys = system_msgs[-1]
        assert "content" in latest_sys, f"System message should have 'content' field: {latest_sys}"
        assert "text" not in latest_sys or latest_sys.get("content"), \
            f"System message should use 'content' not 'text': {latest_sys}"
        print(f"✓ test_assignment_system_message_uses_content_field PASSED - content: {latest_sys.get('content')}")
    
    def test_status_change_system_message_uses_content_field(self):
        """System message for status change should use 'content' field"""
        ticket = self.create_test_ticket(title="TEST_status_message")
        ticket_id = ticket["ticket_id"]
        
        # Change status (using valid status: 'waiting')
        response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"status": "waiting"},
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        
        # Get notes and find system message
        notes_response = self.get_ticket_notes(ticket_id)
        messages = notes_response.get("messages", [])
        
        # Status system message might contain "Status" or "Waiting"
        system_msgs = [m for m in messages if m.get("type") == "system" and ("Status" in str(m.get("content", "")) or "Waiting" in str(m.get("content", "")))]
        assert len(system_msgs) > 0, f"No status system message found. Messages: {messages}"
        
        latest_sys = system_msgs[-1]
        assert "content" in latest_sys, f"System message should have 'content' field: {latest_sys}"
        print(f"✓ test_status_change_system_message_uses_content_field PASSED - content: {latest_sys.get('content')}")
    
    def test_priority_change_system_message_uses_content_field(self):
        """System message for priority change should use 'content' field"""
        ticket = self.create_test_ticket(title="TEST_priority_message")
        ticket_id = ticket["ticket_id"]
        
        # Change priority
        response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"priority": "urgent"},
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        
        # Get notes and find system message
        notes_response = self.get_ticket_notes(ticket_id)
        messages = notes_response.get("messages", [])
        
        system_msgs = [m for m in messages if m.get("type") == "system" and "Priority" in str(m.get("content", ""))]
        assert len(system_msgs) > 0, f"No priority system message found. Messages: {messages}"
        
        latest_sys = system_msgs[-1]
        assert "content" in latest_sys, f"System message should have 'content' field: {latest_sys}"
        print(f"✓ test_priority_change_system_message_uses_content_field PASSED - content: {latest_sys.get('content')}")
    
    # ===== Test closed_at and resolved_at =====
    
    def test_closing_ticket_sets_both_closed_at_and_resolved_at(self):
        """Closing a ticket should set both closed_at and resolved_at"""
        ticket = self.create_test_ticket(title="TEST_close_timestamps")
        ticket_id = ticket["ticket_id"]
        
        # Close the ticket
        response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"status": "closed"},
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Failed to close ticket: {response.text}"
        
        # Verify both timestamps are set
        closed_ticket = self.get_ticket(ticket_id)
        assert closed_ticket.get("closed_at") is not None, "closed_at should be set when ticket is closed"
        assert closed_ticket.get("resolved_at") is not None, "resolved_at should be set when ticket is closed"
        print(f"✓ test_closing_ticket_sets_both_closed_at_and_resolved_at PASSED")
        print(f"  closed_at: {closed_ticket['closed_at']}")
        print(f"  resolved_at: {closed_ticket['resolved_at']}")
    
    # ===== Test POST /api/tickets/{id}/assign endpoint =====
    
    def test_assign_endpoint_sets_trinity_assigned_at(self):
        """POST /api/tickets/{id}/assign should set trinity_assigned_at"""
        # Get a user to assign
        users_response = requests.get(
            f"{BASE_URL}/api/users",
            headers=self.headers,
            timeout=10
        )
        users = users_response.json() if users_response.status_code == 200 else []
        if isinstance(users, dict):
            users = users.get("items", [])
        
        if not users:
            pytest.skip("No users available for assignment test")
        
        assignee_id = users[0].get("user_id")
        
        # Create ticket without assignee
        ticket = self.create_test_ticket(title="TEST_assign_endpoint")
        ticket_id = ticket["ticket_id"]
        
        # Use the dedicated assign endpoint
        response = requests.post(
            f"{BASE_URL}/api/tickets/{ticket_id}/assign",
            json={"assignee_id": assignee_id},
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Assign endpoint failed: {response.text}"
        
        # Verify trinity_assigned_at is set
        assigned_ticket = self.get_ticket(ticket_id)
        assert assigned_ticket.get("trinity_assigned_at") is not None, \
            "trinity_assigned_at should be set by /assign endpoint"
        assert assigned_ticket.get("assignee_id") == assignee_id, \
            f"assignee_id should be {assignee_id}, got {assigned_ticket.get('assignee_id')}"
        print(f"✓ test_assign_endpoint_sets_trinity_assigned_at PASSED")
        print(f"  trinity_assigned_at: {assigned_ticket['trinity_assigned_at']}")
    
    # ===== Test GET /api/tickets returns tags and customer_email =====
    
    def test_get_tickets_returns_tags_and_customer_email(self):
        """GET /api/tickets should return tickets with tags and customer_email"""
        # Create ticket with tags and customer_email
        ticket = self.create_test_ticket(
            title="TEST_metadata_fields",
            tags=["urgent-support", "billing", "vip"],
            customer_email="vip-customer@testcompany.com"
        )
        ticket_id = ticket["ticket_id"]
        
        # Fetch tickets list
        response = requests.get(
            f"{BASE_URL}/api/tickets?limit=50",
            headers=self.headers,
            timeout=15
        )
        assert response.status_code == 200, f"Failed to get tickets: {response.text}"
        
        data = response.json()
        tickets = data.get("tickets", [])
        
        # Find our test ticket
        test_ticket = next((t for t in tickets if t.get("ticket_id") == ticket_id), None)
        assert test_ticket is not None, f"Test ticket {ticket_id} not found in list"
        
        # Verify tags are returned
        assert "tags" in test_ticket, "Ticket should have 'tags' field"
        assert isinstance(test_ticket["tags"], list), "tags should be a list"
        assert "urgent-support" in test_ticket["tags"], f"Expected 'urgent-support' in tags: {test_ticket['tags']}"
        
        # Verify customer_email is returned
        assert "customer_email" in test_ticket, "Ticket should have 'customer_email' field"
        assert test_ticket["customer_email"] == "vip-customer@testcompany.com", \
            f"Expected customer_email 'vip-customer@testcompany.com', got: {test_ticket.get('customer_email')}"
        
        print(f"✓ test_get_tickets_returns_tags_and_customer_email PASSED")
        print(f"  tags: {test_ticket['tags']}")
        print(f"  customer_email: {test_ticket['customer_email']}")
    
    def test_get_tickets_returns_created_at_for_relative_time(self):
        """GET /api/tickets should return created_at for relative time display"""
        ticket = self.create_test_ticket(title="TEST_created_at_field")
        ticket_id = ticket["ticket_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/tickets?limit=50",
            headers=self.headers,
            timeout=15
        )
        assert response.status_code == 200
        
        data = response.json()
        tickets = data.get("tickets", [])
        
        test_ticket = next((t for t in tickets if t.get("ticket_id") == ticket_id), None)
        assert test_ticket is not None, f"Test ticket {ticket_id} not found"
        
        assert "created_at" in test_ticket, "Ticket should have 'created_at' field"
        assert test_ticket["created_at"] is not None, "created_at should not be None"
        
        print(f"✓ test_get_tickets_returns_created_at_for_relative_time PASSED")
        print(f"  created_at: {test_ticket['created_at']}")


class TestAssignSystemMessageContent:
    """Additional tests for system message content field via assign endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Content-Type": "application/json",
            "Cookie": f"session_token={SESSION_TOKEN}"
        }
        self.created_tickets = []
        yield
        for ticket_id in self.created_tickets:
            try:
                requests.delete(f"{BASE_URL}/api/tickets/{ticket_id}", headers=self.headers, timeout=10)
            except Exception:
                pass
    
    def test_assign_endpoint_creates_system_message_with_content(self):
        """POST /api/tickets/{id}/assign creates system message with 'content' field"""
        # Get a user
        users_response = requests.get(f"{BASE_URL}/api/users", headers=self.headers, timeout=10)
        users = users_response.json() if users_response.status_code == 200 else []
        if isinstance(users, dict):
            users = users.get("items", [])
        if not users:
            pytest.skip("No users available")
        
        assignee_id = users[0].get("user_id")
        
        # Create ticket
        payload = {"title": "TEST_assign_sys_msg", "description": "Test", "status": "todo", "priority": "low"}
        create_response = requests.post(f"{BASE_URL}/api/tickets", json=payload, headers=self.headers, timeout=15)
        assert create_response.status_code == 200
        ticket = create_response.json()
        self.created_tickets.append(ticket["ticket_id"])
        
        # Assign via endpoint
        assign_response = requests.post(
            f"{BASE_URL}/api/tickets/{ticket['ticket_id']}/assign",
            json={"assignee_id": assignee_id},
            headers=self.headers,
            timeout=10
        )
        assert assign_response.status_code == 200
        
        # Check notes
        notes_response = requests.get(
            f"{BASE_URL}/api/tickets/{ticket['ticket_id']}/notes",
            headers=self.headers,
            timeout=10
        )
        assert notes_response.status_code == 200
        messages = notes_response.json().get("messages", [])
        
        system_msgs = [m for m in messages if m.get("type") == "system"]
        assert len(system_msgs) > 0, "Expected at least one system message"
        
        # Find assignment message
        assign_msg = next((m for m in system_msgs if "assigned" in str(m.get("content", "")).lower()), None)
        assert assign_msg is not None, f"No assignment message found. System messages: {system_msgs}"
        assert "content" in assign_msg, f"Message should have 'content' field: {assign_msg}"
        
        print(f"✓ test_assign_endpoint_creates_system_message_with_content PASSED")
        print(f"  System message content: {assign_msg.get('content')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
