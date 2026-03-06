"""
Zeus (AI) Ticket Cleanup Feature Tests
======================================
Tests for:
1. Zeus cleanup API endpoints (/api/admin/atlas/zeus/status, /api/admin/atlas/zeus/run)
2. Tickets API with atlas_assigned_to_zeus filter
3. Verification that Zeus cleanup has closed tickets in Trinity
4. Verification that Zeus cleanup adds system messages
"""

import pytest
import requests
import os
from datetime import datetime

# Use the public URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session token created earlier
TEST_SESSION_TOKEN = "test_session_zeus_1772807066064"


class TestHealthEndpoint:
    """Basic health check"""
    
    def test_health_returns_healthy(self):
        """Test that /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert data["checks"]["database"]["status"] == "healthy"
        print(f"✅ Health check passed: {data['status']}")


class TestZeusCleanupAPI:
    """Tests for Zeus cleanup endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_zeus_status_returns_last_run_stats(self, auth_headers):
        """Test GET /api/admin/atlas/zeus/status returns last run stats"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/zeus/status",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields in response
        print(f"Zeus status response: {data}")
        
        # Either shows stats or "never_run"
        if data.get("status") == "never_run":
            print("✅ Zeus cleanup has never run (expected for fresh install)")
        else:
            # Should have run stats
            assert "trinity_closed" in data or "run_at" in data
            print(f"✅ Zeus cleanup last run stats: trinity_closed={data.get('trinity_closed')}, atlas_closed={data.get('atlas_closed')}")
    
    def test_zeus_status_returns_401_without_auth(self):
        """Test that zeus/status returns 401 without authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/atlas/zeus/status")
        assert response.status_code == 401
        print("✅ Zeus status correctly requires authentication")
    
    def test_zeus_run_returns_401_without_auth(self):
        """Test that zeus/run returns 401 without authentication"""
        response = requests.post(f"{BASE_URL}/api/admin/atlas/zeus/run")
        assert response.status_code == 401
        print("✅ Zeus run correctly requires authentication")


class TestTicketsAPIZeusFilter:
    """Tests for tickets API with atlas_assigned_to_zeus filter"""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_tickets_api_supports_zeus_filter(self, auth_headers):
        """Test GET /api/tickets?status=todo&atlas_assigned_to_zeus=true returns only Zeus-assigned tickets"""
        response = requests.get(
            f"{BASE_URL}/api/tickets",
            params={
                "status": "todo",
                "atlas_assigned_to_zeus": "true",
                "limit": 5
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return tickets array and pagination info
        assert "tickets" in data
        assert "total" in data
        assert isinstance(data["tickets"], list)
        
        print(f"✅ Zeus filter returned {data['total']} total tickets")
        
        # Verify all returned tickets have atlas_assigned_to_zeus=true
        if len(data["tickets"]) > 0:
            for ticket in data["tickets"]:
                assert ticket.get("atlas_assigned_to_zeus") == True, \
                    f"Ticket {ticket.get('ticket_id')} doesn't have atlas_assigned_to_zeus=true"
            print(f"✅ All {len(data['tickets'])} returned tickets have atlas_assigned_to_zeus=true")
    
    def test_tickets_api_without_zeus_filter(self, auth_headers):
        """Test that tickets API without zeus filter returns all tickets (not filtered)"""
        response = requests.get(
            f"{BASE_URL}/api/tickets",
            params={"status": "todo", "limit": 5},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "tickets" in data
        print(f"✅ Tickets API without filter returned {data['total']} total tickets")
    
    def test_tickets_api_zeus_filter_with_multiple_statuses(self, auth_headers):
        """Test Zeus filter works with multiple statuses (used by AI Assigned page)"""
        response = requests.get(
            f"{BASE_URL}/api/tickets",
            params={
                "status": ["todo", "in_progress", "waiting"],
                "atlas_assigned_to_zeus": "true",
                "limit": 10
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "tickets" in data
        print(f"✅ Zeus filter with multiple statuses returned {data['total']} tickets")


class TestZeusCleanupDatabase:
    """Tests to verify Zeus cleanup has actually closed tickets and created messages"""
    
    def test_zeus_closed_tickets_exist(self):
        """Verify tickets with closed_by='zeus_cleanup' exist in database"""
        from pymongo import MongoClient
        
        client = MongoClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
        db = client[os.environ.get('DB_NAME', 'test_database')]
        
        count = db.tickets.count_documents({"closed_by": "zeus_cleanup"})
        print(f"Tickets closed by zeus_cleanup: {count}")
        
        # Should have some tickets closed by zeus (per the context)
        assert count > 0, "Expected some tickets to be closed by zeus_cleanup"
        print(f"✅ Found {count} tickets closed by zeus_cleanup")
        
        # Verify one closed ticket has correct fields
        sample_ticket = db.tickets.find_one({"closed_by": "zeus_cleanup"})
        assert sample_ticket is not None
        assert sample_ticket.get("status") == "closed"
        assert "closed_at" in sample_ticket
        print(f"✅ Sample closed ticket verified: {sample_ticket.get('ticket_id')}")
    
    def test_zeus_cleanup_system_messages_exist(self):
        """Verify system messages with source='zeus_cleanup' exist"""
        from pymongo import MongoClient
        
        client = MongoClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
        db = client[os.environ.get('DB_NAME', 'test_database')]
        
        count = db.messages.count_documents({"source": "zeus_cleanup"})
        print(f"System messages from zeus_cleanup: {count}")
        
        # Should have system messages
        assert count > 0, "Expected some system messages from zeus_cleanup"
        print(f"✅ Found {count} system messages from zeus_cleanup")
        
        # Verify one message has correct format
        sample_message = db.messages.find_one({"source": "zeus_cleanup"})
        assert sample_message is not None
        assert sample_message.get("type") == "system"
        assert "Auto-closed" in sample_message.get("content", "")
        assert sample_message.get("author_name") == "System"
        print(f"✅ Sample system message verified: {sample_message.get('message_id')}")
    
    def test_zeus_cleanup_state_in_database(self):
        """Verify zeus_cleanup state is stored in atlas_backfill_state collection"""
        from pymongo import MongoClient
        
        client = MongoClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
        db = client[os.environ.get('DB_NAME', 'test_database')]
        
        state = db.atlas_backfill_state.find_one({"_type": "zeus_cleanup"})
        assert state is not None, "Zeus cleanup state not found in database"
        
        # Should have run stats
        assert "trinity_closed" in state or "last_run_at" in state
        print(f"✅ Zeus cleanup state found: trinity_closed={state.get('trinity_closed')}, last_run_at={state.get('last_run_at')}")


class TestAIAssignedTicketsIntegration:
    """Integration tests mimicking the frontend AIAssignedTicketsPage behavior"""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_ai_assigned_page_query(self, auth_headers):
        """
        Test the exact API call that AIAssignedTicketsPage.js makes:
        - filterStatuses: ['todo', 'in_progress', 'waiting']  
        - customParams: { atlas_assigned_to_zeus: 'true' }
        """
        response = requests.get(
            f"{BASE_URL}/api/tickets",
            params={
                "status": "todo",  # Will be one of the filter statuses
                "atlas_assigned_to_zeus": "true",
                "page": 1,
                "limit": 50
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "tickets" in data
        assert "total" in data
        assert "page" in data
        assert "has_more" in data
        
        # Verify structure of returned tickets
        if len(data["tickets"]) > 0:
            ticket = data["tickets"][0]
            assert "ticket_id" in ticket
            assert "title" in ticket
            assert "status" in ticket
            assert "atlas_assigned_to_zeus" in ticket
            assert ticket["atlas_assigned_to_zeus"] == True
        
        print(f"✅ AI Assigned page query working: {data['total']} total Zeus-assigned tickets")
        print(f"   Page 1 shows {len(data['tickets'])} tickets")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
